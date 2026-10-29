"""设备队列按测试套分发（v11.11.0，CORE §7.9）。"""
from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from rodski.core.device_scheduler import (
    CrossPlatformPlanError,
    Device,
    DeviceScheduler,
    PlanQueue,
    PlanTask,
    build_tasks,
    check_plan_for_queue,
)
from rodski.rodski_cli import queue as queue_cli

DEV_A = Device(udid="AAAA1111-aaaa", platform="android", name="emu-a")
DEV_B = Device(udid="BBBB2222-bbbb", platform="android", name="emu-b")

MODELS = (
    '<?xml version="1.0" encoding="UTF-8"?>\n<models>\n'
    '  <model name="WebPage" type="ui"/>\n'
    '  <model name="AndroidScreen" type="ui" driver_type="android"/>\n'
    '  <model name="IosScreen" type="ui" driver_type="ios"/>\n'
    '</models>\n'
)


def _case(case_id, models):
    steps = "".join(f'      <test_step action="verify" model="{m}" data="D1"/>\n' for m in models)
    return (f'  <case execute="是" id="{case_id}" title="{case_id}" component_type="界面" priority="P0">\n'
            f'    <test_case>\n{steps}    </test_case>\n  </case>\n')


@pytest.fixture
def module(tmp_path):
    for name in ("plan", "case", "model", "data"):
        (tmp_path / name).mkdir()
    (tmp_path / "model" / "model.xml").write_text(MODELS, encoding="utf-8")
    (tmp_path / "case" / "web").mkdir()
    (tmp_path / "case" / "app").mkdir()
    (tmp_path / "case" / "web" / "w.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<cases>\n'
        + _case("W1", ["WebPage"]) + _case("W2", ["WebPage"]) + '</cases>\n', encoding="utf-8")
    (tmp_path / "case" / "app" / "a.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<cases>\n'
        + _case("A1", ["AndroidScreen", "WebPage"]) + _case("A2", ["AndroidScreen"]) + '</cases>\n',
        encoding="utf-8")
    (tmp_path / "case" / "ios.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<cases>\n' + _case("I1", ["IosScreen"]) + '</cases>\n',
        encoding="utf-8")
    return tmp_path


def _plan(module, plan_id, body, max_parallel=None):
    attr = f' max_parallel="{max_parallel}"' if max_parallel else ""
    (module / "plan" / f"{plan_id}.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<test_plan id="{plan_id}" title="t" kind="suite" execute="是" default_execute="否"{attr}>\n'
        f'{body}</test_plan>\n', encoding="utf-8")
    return module / "plan" / f"{plan_id}.xml"


SUITES = (
    '  <suite id="web" title="Web"><case_dir path="web"/></suite>\n'
    '  <suite id="app"><case_dir path="app"/></suite>\n'
    '  <suite id="off" execute="否"><case file="ios.xml" id="I1"/></suite>\n'
)


class TestBuildTasksBySuite:
    def test_one_task_per_enabled_suite(self, module):
        plan = _plan(module, "p", SUITES, max_parallel=2)

        device_tasks, free_tasks = build_tasks([plan], "android", case_dir=module / "case")

        assert [(t.plan_id, t.suite_id) for t in device_tasks] == [("p", "app")]
        assert [(t.plan_id, t.suite_id) for t in free_tasks] == [("p", "web")]
        assert free_tasks[0].device_free is True
        for t in device_tasks + free_tasks:
            assert t.digest.startswith("sha256:")
            assert t.plan_max_parallel == 2
        assert device_tasks[0].key == "p/app"

    def test_disabled_suite_with_other_platform_is_not_an_error(self, module):
        """停用套不入队，自然也不参与平台预检（off 套是 iOS）。"""
        plan = _plan(module, "p", SUITES)
        ok = check_plan_for_queue(plan, "android", case_dir=module / "case")
        assert ok == (False, "", True)

    def test_suite_on_wrong_platform_names_the_suite(self, module):
        plan = _plan(module, "p", SUITES.replace('id="off" execute="否"', 'id="ios"'))

        with pytest.raises(CrossPlatformPlanError, match="测试套 ios 面向 ios"):
            build_tasks([plan], "android", case_dir=module / "case")

    def test_web_only_plan_is_device_free(self, module):
        plan = _plan(module, "p", '  <suite id="web"><case_dir path="web"/></suite>\n')
        assert check_plan_for_queue(plan, "android", case_dir=module / "case")[0] is True

    def test_implicit_plan_is_single_unit(self, module):
        plan = _plan(module, "p", '  <case_dir path="app"/>\n')

        device_tasks, free_tasks = build_tasks([plan], "android", case_dir=module / "case")

        assert [(t.plan_id, t.suite_id) for t in device_tasks] == [("p", None)]
        assert free_tasks == []
        assert device_tasks[0].key == "p"

    def test_mixed_web_and_app_case_needs_device(self, module):
        """A1 同时用 web + android：整条用例必须在有设备的执行器上执行，不能拆。"""
        plan = _plan(module, "p", '  <suite id="mix"><case file="app/a.xml" id="A1"/></suite>\n')
        device_tasks, free_tasks = build_tasks([plan], "android", case_dir=module / "case")
        assert [t.suite_id for t in device_tasks] == ["mix"] and free_tasks == []

    def test_structure_error_rejected_before_queue(self, module):
        plan = _plan(module, "p", '  <suite id="a"><case_dir path="web"/></suite>\n'
                                  '  <suite id="a"><case_dir path="app"/></suite>\n')
        with pytest.raises(CrossPlatformPlanError, match="测试套 id 重复"):
            build_tasks([plan], "android", case_dir=module / "case")


def _task(plan_id, suite_id, *, free=False, limit=None):
    return PlanTask(plan_id=plan_id, plan_path=Path(f"/tmp/plan/{plan_id}.xml"),
                    suite_id=suite_id, device_free=free, plan_max_parallel=limit)


class TestPlanQueueConstraints:
    def test_device_and_local_workers_only_take_their_kind(self):
        queue = PlanQueue([_task("p", "web", free=True), _task("p", "app")])
        assert queue.claim("dev", device_free=False).suite_id == "app"
        assert queue.claim("dev", device_free=False) is None
        assert queue.claim("local-1", device_free=True).suite_id == "web"

    def test_plan_max_parallel_caps_running_suites(self):
        queue = PlanQueue([_task("p", "a", limit=1), _task("p", "b", limit=1), _task("q", "c", limit=1)])
        first = queue.claim("d1")
        assert first.key == "p/a"
        # p 的名额已满 → 跳过 p/b，领到 q/c
        assert queue.claim("d2").key == "q/c"
        assert queue.claim("d3") is None
        assert queue.has_claimable() is False
        queue.release(first)
        assert queue.has_claimable() is True
        assert queue.claim("d3").key == "p/b"

    def test_claimed_by_uses_task_key(self):
        queue = PlanQueue([_task("p", "a"), _task("p", "b")])
        queue.claim("d1")
        queue.claim("d2")
        assert queue.claimed_by("p/a") == "d1"
        assert queue.claimed_by("p/b") == "d2"


class _Runner:
    def __init__(self, duration=0.05):
        self.duration = duration
        self.calls = []
        self.live = {}
        self.peak = {}
        self.lock = threading.Lock()

    def __call__(self, device, task, argv, env):
        with self.lock:
            self.calls.append((task.key, device.udid, list(argv)))
            self.live[task.plan_id] = self.live.get(task.plan_id, 0) + 1
            self.peak[task.plan_id] = max(self.peak.get(task.plan_id, 0), self.live[task.plan_id])
        time.sleep(self.duration)
        with self.lock:
            self.live[task.plan_id] -= 1
        return {"status": "PASS", "exit_code": 0, "pass_rate": "1/1", "run_dir": "",
                "child_pid": 1, "device_lost": False, "error": ""}


def _scheduler(tmp_path, tasks, devices, runner, **kw):
    return DeviceScheduler(tmp_path, tasks, devices, result_dir=tmp_path / "result",
                           runner=runner, log_sink=lambda _m: None, **kw)


class TestSchedulerSuites:
    def test_local_slots_run_device_free_units(self, tmp_path):
        runner = _Runner()
        tasks = [_task("p", "web", free=True), _task("p", "app")]
        summary = _scheduler(tmp_path, tasks, [DEV_A], runner, local_slots=1).run()

        by_key = {key: udid for key, udid, _argv in runner.calls}
        assert by_key == {"p/web": "local-1", "p/app": DEV_A.udid}
        assert summary["summary"]["passed"] == 2 and summary["exit_code"] == 0
        web = next(p for p in summary["plans"] if p["suite_id"] == "web")
        assert web["device_udid"] is None
        # 设备统计里只有真实设备
        assert [d["udid"] for d in summary["devices"]] == [DEV_A.udid]
        assert summary["devices"][0]["plans_executed"] == ["p/app"]

    def test_free_units_unclaimed_without_local_slots(self, tmp_path):
        summary = _scheduler(tmp_path, [_task("p", "web", free=True)], [DEV_A], _Runner()).run()
        assert summary["summary"]["unclaimed"] == 1 and summary["exit_code"] == 1

    def test_plan_max_parallel_respected_across_devices(self, tmp_path):
        runner = _Runner(duration=0.1)
        tasks = [_task("p", s, limit=1) for s in ("a", "b", "c")]
        summary = _scheduler(tmp_path, tasks, [DEV_A, DEV_B], runner).run()

        assert runner.peak["p"] == 1
        assert summary["summary"]["passed"] == 3

    def test_suites_of_one_plan_spread_over_devices(self, tmp_path):
        runner = _Runner(duration=0.1)
        tasks = [_task("p", s) for s in ("a", "b")]
        _scheduler(tmp_path, tasks, [DEV_A, DEV_B], runner).run()

        assert runner.peak["p"] == 2
        assert {udid for _k, udid, _a in runner.calls} == {DEV_A.udid, DEV_B.udid}

    def test_child_argv_for_device_suite(self, tmp_path):
        scheduler = _scheduler(tmp_path, [], [DEV_A], _Runner())
        task = _task("p", "app")
        task.digest = "sha256:abc"
        argv, env = scheduler._build_child_argv(DEV_A, task, Path("/tmp/out/p__app.json"))

        assert argv[argv.index("run") + 1] == "@p"
        assert argv[argv.index("--suite") + 1] == "app"
        assert argv[argv.index("--expect-digest") + 1] == "sha256:abc"
        assert argv[argv.index("--udid") + 1] == DEV_A.udid
        assert "--no-queue" not in argv
        assert env["RODSKI_RUN_DIR_SUFFIX"] == "p__app_AAAA1111"

    def test_child_argv_for_local_unit(self, tmp_path):
        scheduler = _scheduler(tmp_path, [], [DEV_A], _Runner())
        local = Device(udid="local-1", platform="local", kind="local")
        argv, _env = scheduler._build_child_argv(local, _task("p", "web", free=True),
                                                 Path("/tmp/out/p__web.json"))
        assert "--no-queue" in argv
        assert "--udid" not in argv and "--platform" not in argv

    def test_output_json_named_by_suite(self, tmp_path):
        summary = _scheduler(tmp_path, [_task("p", "app")], [DEV_A], _Runner()).run()
        assert summary["plans"][0]["output_json"].endswith("p__app.json")


class TestQueueCliSuites:
    def _args(self, module, **over):
        a = type("A", (), {})()
        defaults = dict(module=str(module), platform="android", devices=None, list_devices=False,
                        plans=["@p"], max_parallel=None, retry_failed_plans=0,
                        no_requeue_on_device_loss=False, allow_cross_platform_plan=False,
                        dry_run=True, report=None, trace=False, verbose=False, coverage=False,
                        suites=None, local_slots=None)
        defaults.update(over)
        a.__dict__.update(defaults)
        return a

    def test_dry_run_lists_device_and_local_units(self, module, capsys, monkeypatch):
        _plan(module, "p", SUITES)
        monkeypatch.setattr(queue_cli, "discover_devices", lambda _p: [DEV_A])

        assert queue_cli.handle(self._args(module)) == 0
        out = capsys.readouterr().out
        assert "计划: @p  测试套: app" in out
        assert "本地执行（不需要设备）: 1 个调度单元" in out
        assert "计划: @p  测试套: web" in out
        assert "测试套: off" not in out

    def test_suite_filter(self, module, capsys, monkeypatch):
        _plan(module, "p", SUITES)
        monkeypatch.setattr(queue_cli, "discover_devices", lambda _p: [DEV_A])

        assert queue_cli.handle(self._args(module, suites=["app"])) == 0
        out = capsys.readouterr().out
        assert "测试套: app" in out and "测试套: web" not in out

    def test_unknown_or_disabled_suite_rejected(self, module, capsys, monkeypatch):
        _plan(module, "p", SUITES)
        monkeypatch.setattr(queue_cli, "discover_devices", lambda _p: [DEV_A])

        assert queue_cli.handle(self._args(module, suites=["off,nope"])) == 1
        assert "off, nope" in capsys.readouterr().err

    def test_free_units_handed_to_scheduler(self, module, monkeypatch):
        """v11.10 的队列把纯 web 计划丢掉了；现在由本地 worker 执行。"""
        _plan(module, "p", SUITES)
        monkeypatch.setattr(queue_cli, "discover_devices", lambda _p: [DEV_A])
        captured = {}

        class FakeScheduler:
            def __init__(self, _module_dir, tasks, devices, **kw):
                captured["keys"] = [t.key for t in tasks]
                captured["local_slots"] = kw.get("local_slots")

            def run(self):
                return {"summary": {"passed": 2, "total_plans": 2, "failed": 0, "error": 0,
                                    "unclaimed": 0}, "peak_parallel": 2, "duration": 0.1,
                        "exit_code": 0}

        monkeypatch.setattr(queue_cli, "DeviceScheduler", FakeScheduler)
        assert queue_cli.handle(self._args(module, dry_run=False)) == 0
        assert captured == {"keys": ["p/app", "p/web"], "local_slots": 1}

    def test_implicit_plan_suite_default(self, module, capsys, monkeypatch):
        """隐式计划的唯一套是 default，queue --suite default 与 run --suite default 一致。"""
        _plan(module, "p", '  <case_dir path="app"/>\n')
        monkeypatch.setattr(queue_cli, "discover_devices", lambda _p: [DEV_A])

        assert queue_cli.handle(self._args(module, suites=["default"])) == 0
        assert "计划: @p" in capsys.readouterr().out

    def test_cross_platform_flag_forwarded_to_child(self, module):
        """子进程 run 的预检同样会拦跨平台套，必须一起放行。"""
        args = self._args(module, allow_cross_platform_plan=True)
        assert "--allow-cross-platform-plan" in queue_cli._forward_run_args(args)
        assert "--allow-cross-platform-plan" not in queue_cli._forward_run_args(self._args(module))
