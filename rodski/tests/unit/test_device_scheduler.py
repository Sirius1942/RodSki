"""DeviceScheduler / PlanQueue 单元测试

全部 hermetic：runner 注入后调度器不 spawn 任何进程、不碰真设备。
重点验证四条不变量：
    1. 计划不被拆分、不被重复领取；
    2. 动态领取（先跑完的设备领下一个，而不是静态分配）；
    3. 掉线重入队一次、普通失败不重试；
    4. 退出码聚合（有失败/有计划被落下 → 非 0）。
"""
import threading
import time
from pathlib import Path

import pytest

try:
    from rodski.core.device_scheduler import (
        MAX_ATTEMPTS_PER_PLAN,
        CrossPlatformPlanError,
        Device,
        DeviceLostError,
        DeviceScheduler,
        MixedPlanKindError,
        PlanOutcome,
        PlanQueue,
        PlanTask,
        build_tasks,
        check_plan_for_queue,
    )
except ImportError:
    from core.device_scheduler import (
        MAX_ATTEMPTS_PER_PLAN,
        CrossPlatformPlanError,
        Device,
        DeviceLostError,
        DeviceScheduler,
        MixedPlanKindError,
        PlanOutcome,
        PlanQueue,
        PlanTask,
        build_tasks,
        check_plan_for_queue,
    )


DEV_A = Device(udid="AAAA1111-aaaa", platform="ios", name="iPhone 16")
DEV_B = Device(udid="BBBB2222-bbbb", platform="ios", name="iPhone 16 Pro")


def make_tasks(*plan_ids):
    return [PlanTask(plan_id=pid, plan_path=Path(f"/tmp/plan/{pid}.xml")) for pid in plan_ids]


class RecordingRunner:
    """记录每个计划被哪台设备执行、执行了几次；可注入每计划的耗时与结果。"""

    def __init__(self, durations=None, results=None, raise_for=None):
        self.durations = durations or {}
        self.results = results or {}
        self.raise_for = raise_for or {}
        self.calls = []            # (plan_id, device_udid)
        self.lock = threading.Lock()

    def __call__(self, device, task, argv, env):
        with self.lock:
            self.calls.append((task.plan_id, device.udid))
        time.sleep(self.durations.get(task.plan_id, 0.01))
        if task.plan_id in self.raise_for:
            raise self.raise_for[task.plan_id]
        return self.results.get(task.plan_id, {
            "status": "PASS", "exit_code": 0, "pass_rate": "1/1",
            "run_dir": "", "child_pid": 1234, "device_lost": False, "error": "",
        })


def run_scheduler(tmp_path, tasks, devices, runner, **kwargs):
    scheduler = DeviceScheduler(tmp_path, tasks, devices,
                                result_dir=tmp_path / "result",
                                runner=runner,
                                log_sink=lambda _m: None, **kwargs)
    return scheduler, scheduler.run()


class TestPlanQueue:
    def test_claim_never_double_books(self):
        queue = PlanQueue(make_tasks("p1", "p2", "p3", "p4", "p5", "p6"))
        claimed = []
        lock = threading.Lock()

        def worker():
            while True:
                task = queue.claim("dev")
                if task is None:
                    return
                with lock:
                    claimed.append(task.plan_id)

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert sorted(claimed) == ["p1", "p2", "p3", "p4", "p5", "p6"]
        assert len(set(claimed)) == 6

    def test_claim_returns_none_when_empty(self):
        queue = PlanQueue([])
        assert queue.claim("dev") is None

    def test_requeue_front_puts_task_back_first(self):
        queue = PlanQueue(make_tasks("p1", "p2"))
        task = queue.claim("dev")
        queue.requeue(task, front=True)
        assert queue.claim("dev").plan_id == "p1"

    def test_has_no_case_level_api(self):
        """计划不可拆分是**结构性**保证：队列不提供任何按 case/step 发放的接口。"""
        queue = PlanQueue(make_tasks("p1"))
        public = {name for name in dir(queue) if not name.startswith("_")}
        assert public == {"claim", "requeue", "outstanding", "claimed_by"}


class TestScheduling:
    def test_plan_never_split_across_devices(self, tmp_path):
        runner = RecordingRunner(durations={"p1": 0.05, "p2": 0.02, "p3": 0.02})
        scheduler, summary = run_scheduler(tmp_path, make_tasks("p1", "p2", "p3"),
                                           [DEV_A, DEV_B], runner)

        per_plan_devices = {}
        for plan_id, udid in runner.calls:
            per_plan_devices.setdefault(plan_id, set()).add(udid)
        assert all(len(v) == 1 for v in per_plan_devices.values())

        plan_ids = [p["plan_id"] for p in summary["plans"]]
        assert len(plan_ids) == len(set(plan_ids)) == 3

    def test_dynamic_claiming_fast_device_takes_more(self, tmp_path):
        """p1 很长、p2/p3 很短：短的那个跑完后必须回去再领一个。"""
        runner = RecordingRunner(durations={"p1": 0.30, "p2": 0.01, "p3": 0.01})
        scheduler, summary = run_scheduler(tmp_path, make_tasks("p1", "p2", "p3"),
                                           [DEV_A, DEV_B], runner)

        per_device = {}
        for plan_id, udid in runner.calls:
            per_device.setdefault(udid, []).append(plan_id)
        assert any(len(v) >= 2 for v in per_device.values())
        assert sum(len(v) for v in per_device.values()) == 3

    def test_every_plan_claimed_exactly_once_on_success(self, tmp_path):
        runner = RecordingRunner()
        _, summary = run_scheduler(tmp_path, make_tasks("p1", "p2", "p3"),
                                   [DEV_A, DEV_B], runner)

        assert len(runner.calls) == 3
        assert summary["summary"] == {"total_plans": 3, "passed": 3, "failed": 0,
                                      "error": 0, "unclaimed": 0}
        assert summary["exit_code"] == 0

    def test_max_parallel_caps_concurrent_children(self, tmp_path):
        peak = {"value": 0}
        live = {"value": 0}
        lock = threading.Lock()

        def runner(device, task, argv, env):
            with lock:
                live["value"] += 1
                peak["value"] = max(peak["value"], live["value"])
            time.sleep(0.03)
            with lock:
                live["value"] -= 1
            return {"status": "PASS", "exit_code": 0, "pass_rate": "1/1",
                    "run_dir": "", "child_pid": 0, "device_lost": False, "error": ""}

        devices = [DEV_A, DEV_B, Device(udid="CCCC3333", platform="ios", name="iPhone 16e")]
        _, summary = run_scheduler(tmp_path, make_tasks("p1", "p2", "p3"), devices,
                                   runner, max_parallel=2)

        assert peak["value"] <= 2
        assert summary["max_parallel"] == 2

    def test_parallel_intervals_overlap(self, tmp_path):
        """两个计划在两台设备上同时跑 —— 区间重叠，串行不可能产生。"""
        runner = RecordingRunner(durations={"p1": 0.15, "p2": 0.15})
        _, summary = run_scheduler(tmp_path, make_tasks("p1", "p2"), [DEV_A, DEV_B], runner)

        assert summary["peak_parallel"] == 2
        p1 = next(p for p in summary["plans"] if p["plan_id"] == "p1")
        p2 = next(p for p in summary["plans"] if p["plan_id"] == "p2")
        assert p1["started_at"] < p2["finished_at"]
        assert p2["started_at"] < p1["finished_at"]
        assert p1["device_udid"] != p2["device_udid"]


class TestFailurePolicy:
    def test_no_retry_on_ordinary_failure(self, tmp_path):
        runner = RecordingRunner(results={"p1": {
            "status": "FAIL", "exit_code": 1, "pass_rate": "0/1",
            "run_dir": "", "child_pid": 0, "device_lost": False, "error": "断言失败"}})
        _, summary = run_scheduler(tmp_path, make_tasks("p1", "p2"), [DEV_A, DEV_B], runner)

        assert len([c for c in runner.calls if c[0] == "p1"]) == 1
        p1 = next(p for p in summary["plans"] if p["plan_id"] == "p1")
        assert p1["status"] == "FAIL" and p1["attempt"] == 1
        assert summary["exit_code"] == 1

    def test_retry_failed_plans_when_requested(self, tmp_path):
        runner = RecordingRunner(results={"p1": {
            "status": "FAIL", "exit_code": 1, "pass_rate": "0/1",
            "run_dir": "", "child_pid": 0, "device_lost": False, "error": ""}})
        _, summary = run_scheduler(tmp_path, make_tasks("p1"), [DEV_A], runner,
                                   retry_failed_plans=1)

        assert len(runner.calls) == 2
        assert summary["plans"][-1]["attempt"] == 2

    def test_requeue_once_on_device_loss(self, tmp_path):
        runner = RecordingRunner(raise_for={"p1": DeviceLostError("设备掉线")})
        _, summary = run_scheduler(tmp_path, make_tasks("p1"), [DEV_A, DEV_B], runner,
                                   requeue_on_device_loss=True)

        # 掉线后计划被重新入队，由另一台设备接手；尝试次数上限 2
        assert len(runner.calls) == MAX_ATTEMPTS_PER_PLAN
        assert len({udid for _pid, udid in runner.calls}) == 2
        assert summary["plans"][-1]["status"] == "ERROR"
        assert summary["exit_code"] == 1

    def test_no_requeue_when_disabled(self, tmp_path):
        runner = RecordingRunner(raise_for={"p1": DeviceLostError("设备掉线")})
        _, summary = run_scheduler(tmp_path, make_tasks("p1"), [DEV_A, DEV_B], runner,
                                   requeue_on_device_loss=False)

        assert len(runner.calls) == 1
        assert summary["plans"][0]["device_lost"] is True

    def test_lost_device_is_not_reused(self, tmp_path):
        """掉线设备被摘除，后续计划不再落到它身上。"""
        def runner(device, task, argv, env):
            if device.udid == DEV_A.udid:
                raise DeviceLostError("掉线")
            return {"status": "PASS", "exit_code": 0, "pass_rate": "1/1",
                    "run_dir": "", "child_pid": 0, "device_lost": False, "error": ""}

        _, summary = run_scheduler(tmp_path, make_tasks("p1", "p2", "p3"),
                                   [DEV_A, DEV_B], runner, requeue_on_device_loss=False)

        dev_a = next(d for d in summary["devices"] if d["udid"] == DEV_A.udid)
        assert dev_a["lost"] is True
        # A 掉线后不再领新计划：A 上只有那一个失败的计划
        assert len([p for p in summary["plans"] if p["device_udid"] == DEV_A.udid]) == 1
        assert summary["summary"]["passed"] == 2


class TestSummaryAndExitCodes:
    def test_summary_shape(self, tmp_path):
        runner = RecordingRunner()
        _, summary = run_scheduler(tmp_path, make_tasks("p1"), [DEV_A], runner)

        assert set(summary) >= {"queue_id", "platform", "max_parallel", "peak_parallel",
                                "duration", "devices", "plans", "summary", "exit_code",
                                "started_at", "finished_at"}
        plan = summary["plans"][0]
        assert set(plan) >= {"plan_id", "plan_path", "kind", "device_udid", "attempt",
                             "status", "exit_code", "pass_rate", "claimed_at",
                             "started_at", "finished_at", "duration", "run_dir",
                             "child_pid", "output_json", "requeued_from", "error"}

    def test_summary_json_written_to_queue_dir(self, tmp_path):
        import json
        runner = RecordingRunner()
        scheduler, summary = run_scheduler(tmp_path, make_tasks("p1"), [DEV_A], runner)

        path = scheduler.queue_dir / "summary.json"
        assert path.exists()
        assert json.loads(path.read_text(encoding="utf-8"))["summary"]["passed"] == 1

    def test_scheduler_never_reports_success_with_unclaimed_plans(self, tmp_path):
        """所有设备掉线导致计划被落下 → 必须退出 1，不能静默通过。"""
        def runner(device, task, argv, env):
            raise DeviceLostError("掉线")

        _, summary = run_scheduler(tmp_path, make_tasks("p1", "p2"), [DEV_A],
                                   runner, requeue_on_device_loss=False)

        assert summary["summary"]["unclaimed"] == 1
        assert summary["exit_code"] == 1

    def test_empty_queue_exits_zero(self, tmp_path):
        _, summary = run_scheduler(tmp_path, [], [DEV_A], RecordingRunner())

        assert summary["summary"]["total_plans"] == 0
        assert summary["exit_code"] == 0

    def test_mixed_status_aggregation(self, tmp_path):
        runner = RecordingRunner(results={
            "p1": {"status": "PASS", "exit_code": 0, "pass_rate": "1/1", "run_dir": "",
                   "child_pid": 0, "device_lost": False, "error": ""},
            "p2": {"status": "FAIL", "exit_code": 1, "pass_rate": "0/1", "run_dir": "",
                   "child_pid": 0, "device_lost": False, "error": ""},
        })
        _, summary = run_scheduler(tmp_path, make_tasks("p1", "p2"), [DEV_A, DEV_B], runner)

        assert summary["summary"]["passed"] == 1
        assert summary["summary"]["failed"] == 1
        assert summary["exit_code"] == 1


class TestChildArgv:
    def test_argv_carries_plan_platform_udid_output(self, tmp_path):
        scheduler = DeviceScheduler(tmp_path, [], [DEV_A], result_dir=tmp_path / "result",
                                    log_sink=lambda _m: None)
        scheduler._create_queue_dir()
        task = PlanTask(plan_id="p1", plan_path=Path("/tmp/plan/p1.xml"))

        argv, env = scheduler._build_child_argv(DEV_A, task, Path("/tmp/out/p1.json"))

        assert "@p1" in argv
        assert argv[argv.index("--platform") + 1] == "ios"
        assert argv[argv.index("--udid") + 1] == DEV_A.udid
        assert argv[argv.index("--output") + 1] == "/tmp/out/p1.json"
        # 运行目录后缀消除「同秒两个子进程撞同一目录」的隐患
        assert env["RODSKI_RUN_DIR_SUFFIX"] == "p1_AAAA1111"

    def test_forward_args_appended(self, tmp_path):
        scheduler = DeviceScheduler(tmp_path, [], [DEV_A], result_dir=tmp_path / "result",
                                    forward_args=["--report", "html", "--trace"],
                                    log_sink=lambda _m: None)
        task = PlanTask(plan_id="p1", plan_path=Path("/tmp/plan/p1.xml"))

        argv, _env = scheduler._build_child_argv(DEV_A, task, Path("/tmp/out/p1.json"))

        assert argv[-3:] == ["--report", "html", "--trace"]


class TestPlanPreflight:
    """入队预检：跨平台计划与 load 计划必须被挡在队列之外。"""

    @pytest.fixture
    def module(self, tmp_path):
        (tmp_path / "plan").mkdir()
        (tmp_path / "case").mkdir()
        (tmp_path / "model").mkdir()
        (tmp_path / "model" / "model.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n<models>\n'
            '  <model name="MobileScreen" type="ui" driver_type="mobile"/>\n'
            '  <model name="WebPage" type="ui"/>\n'
            '  <model name="IosScreen" type="ui" driver_type="ios"/>\n'
            '  <model name="AndroidScreen" type="ui" driver_type="android"/>\n'
            '</models>\n', encoding="utf-8")
        return tmp_path

    def _write_plan(self, module, plan_id, case_ids, kind="suite"):
        (module / "plan" / f"{plan_id}.xml").write_text(
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<test_plan id="{plan_id}" title="t" kind="{kind}" execute="是" default_execute="否">\n'
            + "".join(f'  <case id="{c}" execute="是"/>\n' for c in case_ids)
            + '</test_plan>\n', encoding="utf-8")
        return module / "plan" / f"{plan_id}.xml"

    def _write_case(self, module, case_id, models):
        (module / "case" / f"{case_id}.xml").write_text(
            f'<?xml version="1.0" encoding="UTF-8"?>\n<cases>\n'
            f'  <case execute="是" id="{case_id}" title="{case_id}" component_type="界面" priority="P0">\n'
            f'    <test_case>\n'
            + "".join(f'      <test_step action="verify" model="{m}" data="D1"/>\n' for m in models)
            + '    </test_case>\n  </case>\n</cases>\n', encoding="utf-8")

    def test_mobile_driver_type_is_platform_agnostic(self, module):
        """driver_type="mobile" 靠运行时 Mobile.Platform 决定平台，两种队列平台都兼容。"""
        self._write_case(module, "C1", ["MobileScreen"])
        plan = self._write_plan(module, "p1", ["C1"])

        device_free, _msg, ok = check_plan_for_queue(plan, "ios", case_dir=module / "case")
        assert (device_free, ok) == (False, True)

    def test_web_only_plan_is_device_free(self, module):
        self._write_case(module, "C1", ["WebPage"])
        plan = self._write_plan(module, "p1", ["C1"])

        device_free, _msg, ok = check_plan_for_queue(plan, "ios", case_dir=module / "case")
        assert (device_free, ok) == (True, True)

    def test_cross_platform_plan_rejected(self, module):
        self._write_case(module, "C1", ["IosScreen", "AndroidScreen"])
        plan = self._write_plan(module, "p1", ["C1"])

        _free, msg, ok = check_plan_for_queue(plan, "ios", case_dir=module / "case")
        assert ok is False
        assert "android" in msg and "ios" in msg

    def test_cross_platform_plan_allowed_with_flag(self, module):
        self._write_case(module, "C1", ["IosScreen", "AndroidScreen"])
        plan = self._write_plan(module, "p1", ["C1"])

        _free, _msg, ok = check_plan_for_queue(plan, "ios", case_dir=module / "case",
                                               allow_cross_platform=True)
        assert ok is True

    def test_wrong_platform_plan_rejected(self, module):
        self._write_case(module, "C1", ["AndroidScreen"])
        plan = self._write_plan(module, "p1", ["C1"])

        _free, msg, ok = check_plan_for_queue(plan, "ios", case_dir=module / "case")
        assert ok is False
        assert "android" in msg

    def test_load_plan_rejected_from_device_queue(self, module):
        self._write_case(module, "C1", ["MobileScreen"])
        self._write_plan(module, "load_plan", ["C1"], kind="load")

        with pytest.raises(MixedPlanKindError, match="kind=load"):
            build_tasks([module / "plan" / "load_plan.xml"], "ios",
                        case_dir=module / "case")

    def test_build_tasks_separates_device_free_plans(self, module):
        self._write_case(module, "C1", ["MobileScreen"])
        self._write_case(module, "C2", ["WebPage"])
        self._write_plan(module, "device_plan", ["C1"])
        self._write_plan(module, "web_plan", ["C2"])

        device_tasks, free_tasks = build_tasks(
            [module / "plan" / "device_plan.xml", module / "plan" / "web_plan.xml"],
            "ios", case_dir=module / "case")

        assert [t.plan_id for t in device_tasks] == ["device_plan"]
        assert [t.plan_id for t in free_tasks] == ["web_plan"]
        assert free_tasks[0].device_free is True

    def test_cross_platform_raises_from_build_tasks(self, module):
        self._write_case(module, "C1", ["IosScreen", "AndroidScreen"])
        self._write_plan(module, "p1", ["C1"])

        with pytest.raises(CrossPlatformPlanError):
            build_tasks([module / "plan" / "p1.xml"], "ios", case_dir=module / "case")
