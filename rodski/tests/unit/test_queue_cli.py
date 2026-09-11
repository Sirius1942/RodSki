"""`rodski queue` 子命令单元测试

覆盖参数解析、CSV 归一、模块目录推导、plan 解析、子进程参数转发，
以及最关键的一条兼容性约束：**不给 --devices 时单设备路径不受影响**。
"""
import sys
from pathlib import Path

import pytest

try:
    from rodski.rodski_cli import queue as queue_cli
    from rodski.rodski_cli import main as cli_main
except ImportError:
    from rodski_cli import queue as queue_cli
    from rodski_cli import main as cli_main


def build_parser():
    import argparse
    parser = argparse.ArgumentParser(prog="rodski")
    subparsers = parser.add_subparsers(dest="command")
    queue_cli.setup_parser(subparsers)
    return parser


class TestParser:
    def test_registered_in_main_parser(self):
        import argparse
        parser = argparse.ArgumentParser(prog="rodski")
        subparsers = parser.add_subparsers(dest="command")
        queue_cli.setup_parser(subparsers)
        args = parser.parse_args(["queue", "--platform", "ios"])

        assert args.command == "queue"
        assert args.platform == "ios"

    def test_all_flags_parse(self):
        args = build_parser().parse_args([
            "queue", "--module", "/tmp/m", "--plans", "@a,@b",
            "--devices", "U1,U2", "--platform", "ios", "--max-parallel", "2",
            "--retry-failed-plans", "1", "--no-requeue-on-device-loss",
            "--allow-cross-platform-plan", "--dry-run",
        ])

        assert args.module == "/tmp/m"
        assert args.max_parallel == 2
        assert args.retry_failed_plans == 1
        assert args.no_requeue_on_device_loss is True
        assert args.allow_cross_platform_plan is True
        assert args.dry_run is True

    def test_list_devices_flag(self):
        args = build_parser().parse_args(["queue", "--list-devices"])
        assert args.list_devices is True


class TestSplit:
    def test_comma_separated(self):
        assert queue_cli._split(["A,B"]) == ["A", "B"]

    def test_repeated_flags(self):
        assert queue_cli._split(["A", "B"]) == ["A", "B"]

    def test_dedupes_preserving_order(self):
        assert queue_cli._split(["A,B", "A"]) == ["A", "B"]

    def test_none_and_empty(self):
        assert queue_cli._split(None) is None
        assert queue_cli._split(["", "  "]) is None


class TestResolveModuleDir:
    def test_explicit_path(self, tmp_path):
        assert queue_cli._resolve_module_dir(str(tmp_path)) == tmp_path.resolve()

    def test_cwd_subdir_walks_up(self, tmp_path, monkeypatch):
        (tmp_path / "plan").mkdir()
        monkeypatch.chdir(tmp_path / "plan")
        assert queue_cli._resolve_module_dir(None) == tmp_path

    def test_cwd_as_module(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert queue_cli._resolve_module_dir(None) == tmp_path


class TestForwardArgs:
    def test_report_and_trace_forwarded(self):
        class A:
            report = "html"
            trace = True
            verbose = False
            coverage = False

        assert queue_cli._forward_run_args(A()) == ["--report", "html", "--trace"]

    def test_nothing_forwarded_by_default(self):
        class A:
            report = None
            trace = False
            verbose = False
            coverage = False

        assert queue_cli._forward_run_args(A()) == []


class TestDefaultPlans:
    def _write(self, plan_dir, plan_id, execute):
        (plan_dir / f"{plan_id}.xml").write_text(
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<test_plan id="{plan_id}" title="t" kind="suite" execute="{execute}">\n'
            f'  <case id="C1" execute="是"/>\n</test_plan>\n', encoding="utf-8")

    def test_only_execute_yes_plans_sorted(self, tmp_path):
        plan_dir = tmp_path / "plan"
        plan_dir.mkdir()
        self._write(plan_dir, "b_plan", "是")
        self._write(plan_dir, "a_plan", "是")
        self._write(plan_dir, "c_plan", "否")

        names = [p.stem for p in queue_cli._default_plans(plan_dir)]
        assert names == ["a_plan", "b_plan"]

    def test_empty_plan_dir(self, tmp_path):
        plan_dir = tmp_path / "plan"
        plan_dir.mkdir()
        assert queue_cli._default_plans(plan_dir) == []


class TestResolvePlans:
    def test_missing_plan_reports_error(self, tmp_path, capsys):
        (tmp_path / "plan").mkdir()
        assert queue_cli._resolve_plans(tmp_path, ["@nope"]) is None
        assert "测试计划不存在" in capsys.readouterr().err

    def test_plan_ref_with_and_without_at(self, tmp_path):
        plan_dir = tmp_path / "plan"
        plan_dir.mkdir()
        (plan_dir / "p1.xml").write_text("<test_plan/>", encoding="utf-8")

        assert queue_cli._resolve_plans(tmp_path, ["@p1"]) == [plan_dir / "p1.xml"]
        assert queue_cli._resolve_plans(tmp_path, ["p1"]) == [plan_dir / "p1.xml"]


class TestHandleErrors:
    def test_missing_module_dir_exits_one(self, capsys):
        class A:
            module = "/definitely/not/here"
            platform = None
            devices = None
            list_devices = False

        assert queue_cli.handle(A()) == 1
        assert "模块目录不存在" in capsys.readouterr().err

    def test_explicit_devices_without_platform_fails_loudly(self, tmp_path, capsys):
        """显式给设备却不给平台 → 报错，而不是探测/猜一个平台。"""
        (tmp_path / "plan").mkdir()

        class A:
            module = str(tmp_path)
            platform = None
            devices = ["UDID-A,UDID-B"]
            list_devices = False

        assert queue_cli.handle(A()) == 1
        assert "--platform" in capsys.readouterr().err

    def test_no_devices_found_prints_platform_hint(self, tmp_path, capsys, monkeypatch):
        (tmp_path / "plan").mkdir()
        monkeypatch.setattr(queue_cli, "discover_devices", lambda _p: [])

        class A:
            module = str(tmp_path)
            platform = "android"
            devices = None
            list_devices = False

        assert queue_cli.handle(A()) == 1
        err = capsys.readouterr().err
        assert "未发现任何可用 android 设备" in err
        assert "adb devices" in err

    def test_no_plans_exits_one(self, tmp_path, capsys, monkeypatch):
        (tmp_path / "plan").mkdir()
        monkeypatch.setattr(queue_cli, "discover_devices",
                            lambda _p: [queue_cli.Device(udid="U1", platform="ios")])

        class A:
            module = str(tmp_path)
            platform = "ios"
            devices = None
            list_devices = False

        assert queue_cli.handle(A()) == 1
        assert "没有 execute=是 的计划" in capsys.readouterr().err


class TestSingleDeviceCompatibility:
    """默认单设备路径不得改变：不开并行、不构造调度器之外的东西。"""

    def test_run_command_has_no_devices_flag(self):
        """`rodski run` 只加 --udid，不加任何队列参数。"""
        import argparse
        from rodski.rodski_cli import run as run_cli
        parser = argparse.ArgumentParser(prog="rodski")
        subparsers = parser.add_subparsers(dest="command")
        run_cli.setup_parser(subparsers)

        args = parser.parse_args(["run", "case/foo.xml"])

        assert args.udid is None
        assert not hasattr(args, "devices")
        assert not hasattr(args, "max_parallel")

    def test_udid_parsed_on_run(self):
        import argparse
        from rodski.rodski_cli import run as run_cli
        parser = argparse.ArgumentParser(prog="rodski")
        subparsers = parser.add_subparsers(dest="command")
        run_cli.setup_parser(subparsers)

        args = parser.parse_args(["run", "@p1", "--udid", "ABC"])

        assert args.udid == "ABC"

    def test_queue_dry_run_does_not_construct_scheduler(self, tmp_path, capsys, monkeypatch):
        """--dry-run 只预检，绝不拉起任何子进程。"""
        plan_dir = tmp_path / "plan"
        case_dir = tmp_path / "case"
        model_dir = tmp_path / "model"
        data_dir = tmp_path / "data"
        for d in (plan_dir, case_dir, model_dir, data_dir):
            d.mkdir()
        (model_dir / "model.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n<models>\n'
            '  <model name="MobileScreen" type="ui" driver_type="mobile"/>\n'
            '</models>\n', encoding="utf-8")
        (case_dir / "C1.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n<cases>\n'
            '  <case execute="是" id="C1" title="t" component_type="界面" priority="P0">\n'
            '    <test_case><test_step action="verify" model="MobileScreen" data="D1"/></test_case>\n'
            '  </case>\n</cases>\n', encoding="utf-8")
        (plan_dir / "p1.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<test_plan id="p1" title="t" kind="suite" execute="是" default_execute="否">\n'
            '  <case id="C1" execute="是"/>\n</test_plan>\n', encoding="utf-8")

        def boom(*_args, **_kwargs):
            raise AssertionError("dry-run 不应构造调度器")

        monkeypatch.setattr(queue_cli, "DeviceScheduler", boom)

        class A:
            module = str(tmp_path)
            platform = "ios"
            devices = ["UDID-A,UDID-B"]
            list_devices = False
            plans = None
            max_parallel = None
            retry_failed_plans = 0
            no_requeue_on_device_loss = False
            allow_cross_platform_plan = False
            dry_run = True
            report = None
            trace = False
            verbose = False
            coverage = False

        assert queue_cli.handle(A()) == 0
        assert "dry-run" in capsys.readouterr().out


class TestListDevices:
    def test_lists_and_exits_zero(self, tmp_path, capsys, monkeypatch):
        monkeypatch.setattr(queue_cli, "discover_devices", lambda _p: [
            queue_cli.Device(udid="U1", platform="ios", name="iPhone 16", state="Booted"),
        ])

        class A:
            module = str(tmp_path)
            platform = "ios"
            devices = None
            list_devices = True

        assert queue_cli.handle(A()) == 0
        assert "U1" in capsys.readouterr().out

    def test_exits_one_when_none_available(self, tmp_path, capsys, monkeypatch):
        monkeypatch.setattr(queue_cli, "discover_devices", lambda _p: [])

        class A:
            module = str(tmp_path)
            platform = "ios"
            devices = None
            list_devices = True

        assert queue_cli.handle(A()) == 1
        assert "xcrun simctl" in capsys.readouterr().err
