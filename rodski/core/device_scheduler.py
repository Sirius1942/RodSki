"""多设备计划队列调度 — 设备发现 + 动态领取 + 子进程编排。

设计要点（三条，其余都是推论）：

1. **并行单元 = 计划**。队列里放的对象只有 :class:`PlanTask`（一个计划一个），
   ``claim()`` 是加锁的 ``deque.popleft()``，不存在任何发放 case/scenario/step
   的 API —— 「一个 plan 只用一个 app 设备」是**结构上**成立的，不靠运行时校验。

2. **隔离单元 = 操作系统进程**。每个 worker 拉起一个 ``rodski run @plan_id``
   子进程，复用既有的完整链路（合规检查 → hooks → SKIExecutor → appium →
   ResultWriter → 退出码）。不用线程，因为
   ``DriverFactory._drivers`` / ``_driver_configs`` 是进程级 class dict：
   两个线程用不同 udid 会命中 ``cached_config != kwargs`` 分支 → ``release_driver()``
   → 把另一个线程活着的 Appium session 关掉；playwright 的 sync API 也不是线程安全的。

3. **动态领取**。先跑完计划的设备只是循环回去再 ``claim()`` 一个，代码里没有任何
   轮询表，负载自然均衡。
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

logger = logging.getLogger("rodski")

# 同一设备两次尝试之间的硬上限（重试与掉线重入队共享）
MAX_ATTEMPTS_PER_PLAN = 2

ADB_HINT = "  排查: adb devices            （确认设备已连接且 state=device）"
SIMCTL_HINT = "  排查: xcrun simctl list devices available"

# 子进程引导片段：按「安装态优先、源码树兜底」解析 CLI 入口，避免依赖
# `python -m rodski_cli` 这种只在 dev-install 下成立的调用方式。
_CHILD_BOOTSTRAP = (
    "import sys\n"
    # argv[0] 必须留一个占位程序名：argparse 的 parse_args() 默认读 sys.argv[1:]，
    # 若直接 sys.argv = sys.argv[1:] 会把子命令 'run' 顶成程序名，
    # 真正的 '@plan_id' 就被当成子命令去解析了。
    "sys.argv = ['rodski'] + sys.argv[1:]\n"
    "try:\n"
    "    from rodski.rodski_cli import main\n"
    "except ImportError:\n"
    "    from rodski_cli import main\n"
    "raise SystemExit(main())\n"
)


class DeviceUnavailableError(Exception):
    """按平台找不到任何可用设备。"""


class CrossPlatformPlanError(Exception):
    """计划内同时需要 android 与 ios 设备，无法由单一设备执行。"""


class MixedPlanKindError(Exception):
    """队列里混入了 kind=load 计划（执行模型与设备队列正交）。"""


class DeviceLostError(Exception):
    """子进程报告设备中途掉线。"""


@dataclass(frozen=True)
class Device:
    """一台可用设备。"""

    udid: str
    platform: str          # "android" | "ios"
    name: str = ""
    state: str = ""

    def __str__(self) -> str:
        return f"{self.name or self.udid}({self.platform})"


@dataclass
class PlanTask:
    """队列里的一个整体计划 —— 调度粒度就是它，不可再分。"""

    plan_id: str
    plan_path: Path
    kind: str = "suite"
    attempts: int = 0
    requeued_from: Optional[str] = None
    device_free: bool = False      # 纯 web 计划：不需要设备，队列外先跑

    def __str__(self) -> str:
        return self.plan_id


@dataclass
class PlanOutcome:
    """一个计划的执行结果（父进程侧记录，含时间戳）。"""

    plan_id: str
    plan_path: str
    kind: str
    device_udid: Optional[str]
    attempt: int
    status: str                     # PASS | FAIL | ERROR
    exit_code: int
    pass_rate: str = ""
    claimed_at: str = ""
    started_at: str = ""
    finished_at: str = ""
    duration: float = 0.0
    run_dir: str = ""
    child_pid: int = 0
    output_json: str = ""
    requeued_from: Optional[str] = None
    device_lost: bool = False
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "plan_path": self.plan_path,
            "kind": self.kind,
            "device_udid": self.device_udid,
            "attempt": self.attempt,
            "status": self.status,
            "exit_code": self.exit_code,
            "pass_rate": self.pass_rate,
            "claimed_at": self.claimed_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration": round(self.duration, 3),
            "run_dir": self.run_dir,
            "child_pid": self.child_pid,
            "output_json": self.output_json,
            "requeued_from": self.requeued_from,
            "device_lost": self.device_lost,
            "error": self.error,
        }


class PlanQueue:
    """动态领取队列：加锁 pop，计划整体出队。

    刻意**不**提供任何按 case / scenario / step 发放的接口 —— 计划不拆分是
    由粒度保证的，而不是靠调用方自觉。
    """

    def __init__(self, tasks: Iterable[PlanTask]):
        self._tasks: deque = deque(tasks)
        self._lock = threading.Lock()
        self._claimed: Dict[str, str] = {}     # plan_id → device_udid

    def claim(self, device_udid: str) -> Optional[PlanTask]:
        """原子领取一个计划；队列空时返回 None。"""
        with self._lock:
            if not self._tasks:
                return None
            task = self._tasks.popleft()
            self._claimed[task.plan_id] = device_udid
            return task

    def requeue(self, task: PlanTask, *, front: bool = False) -> None:
        """把计划放回队列（掉线重入队用）。"""
        with self._lock:
            if front:
                self._tasks.appendleft(task)
            else:
                self._tasks.append(task)
            self._claimed.pop(task.plan_id, None)

    def outstanding(self) -> int:
        with self._lock:
            return len(self._tasks)

    def claimed_by(self, plan_id: str) -> Optional[str]:
        with self._lock:
            return self._claimed.get(plan_id)


# ── 设备发现 ─────────────────────────────────────────────────────────────────

def _parse_adb_devices(stdout: str) -> List[Device]:
    """解析 ``adb devices -l`` 输出。

    只保留 state == ``device`` 的行；``unauthorized`` / ``offline`` /
    ``no permissions`` 都会让 Appium 建会话失败，必须提前滤掉。
    友好名取 ``model:`` 限定符（没有则留空）。
    """
    devices: List[Device] = []
    for line in (stdout or "").splitlines():
        line = line.strip()
        if not line or line.startswith("List of devices"):
            continue
        if line.startswith("*"):        # "adb server is out of date" 一类的提示
            continue
        fields = line.split()
        if len(fields) < 2 or fields[1] != "device":
            continue
        name = ""
        for token in fields[2:]:
            if token.startswith("model:"):
                name = token.split(":", 1)[1]
                break
        devices.append(Device(udid=fields[0], platform="android", name=name, state="device"))
    return devices


def _parse_simctl_devices(stdout_json: str) -> List[Device]:
    """解析 ``xcrun simctl list devices available --json`` 输出。

    用 ``available`` 而非 ``booted``：未启动的模拟器也应枚举出来（调用方决定
    是否 boot）。``isAvailable == false`` 的条目（运行时不匹配等）会被滤掉。
    """
    try:
        payload = json.loads(stdout_json or "{}")
    except (ValueError, TypeError):
        return []
    devices: List[Device] = []
    for runtime_devices in (payload.get("devices") or {}).values():
        if not isinstance(runtime_devices, list):
            continue
        for entry in runtime_devices:
            if not isinstance(entry, dict):
                continue
            if not entry.get("isAvailable", True):
                continue
            udid = (entry.get("udid") or "").strip()
            if not udid:
                continue
            devices.append(Device(
                udid=udid,
                platform="ios",
                name=(entry.get("name") or "").strip(),
                state=(entry.get("state") or "").strip(),
            ))
    return devices


def _default_adb_runner() -> str:
    """执行 ``adb devices -l``，返回 stdout（adb 缺失时返回空串）。"""
    adb = shutil.which("adb")
    if not adb:
        logger.warning("未找到 adb，跳过 Android 设备枚举")
        return ""
    try:
        result = subprocess.run([adb, "devices", "-l"], capture_output=True,
                                text=True, timeout=15)
    except (OSError, subprocess.SubprocessError) as e:
        logger.warning(f"adb devices 执行失败: {e}")
        return ""
    return result.stdout or ""


def _default_simctl_runner() -> str:
    """执行 ``xcrun simctl list devices available --json``，返回 stdout。"""
    xcrun = shutil.which("xcrun")
    if not xcrun:
        logger.warning("未找到 xcrun，跳过 iOS 模拟器枚举")
        return ""
    try:
        result = subprocess.run([xcrun, "simctl", "list", "devices", "available", "--json"],
                                capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as e:
        logger.warning(f"xcrun simctl 执行失败: {e}")
        return ""
    return result.stdout or ""


def discover_devices(platform: str, *,
                     adb_runner: Optional[Callable[[], str]] = None,
                     simctl_runner: Optional[Callable[[], str]] = None) -> List[Device]:
    """按平台枚举可用设备。runner 可注入，便于单测不依赖真机。"""
    if platform == "android":
        return _parse_adb_devices((adb_runner or _default_adb_runner)())
    if platform == "ios":
        return _parse_simctl_devices((simctl_runner or _default_simctl_runner)())
    raise ValueError(f"不支持的平台: {platform!r}（可选 android / ios）")


def resolve_platform(module_dir: Path, cli_platform: Optional[str], *,
                     probe: bool = True,
                     adb_runner=None, simctl_runner=None) -> Optional[str]:
    """推导队列平台：CLI 显式指定 > globalvalue.xml 的 Mobile.Platform > 设备探测。

    ``probe=False`` 时不再兜底探测，两者都拿不到就返回 None —— 调用方据此
    显式报错（给用户 ``--devices`` 却不给 ``--platform`` 时，猜平台等于赌命）。
    """
    if cli_platform:
        return cli_platform

    gv_path = module_dir / "data" / "globalvalue.xml"
    if gv_path.exists():
        try:
            root = ET.parse(gv_path).getroot()
            for group in root.findall("group"):
                if group.get("name") != "Mobile":
                    continue
                for var in group.findall("var"):
                    if var.get("name") == "Platform":
                        value = (var.get("value") or "").strip().lower()
                        if value in ("android", "ios"):
                            return value
        except ET.ParseError:
            pass

    if not probe:
        return None

    if _parse_adb_devices((adb_runner or _default_adb_runner)()):
        return "android"
    return "ios"


def platform_hint(platform: str) -> str:
    return ADB_HINT if platform == "android" else SIMCTL_HINT


# ── 计划预检 ─────────────────────────────────────────────────────────────────

def _model_driver_types(model_path: Path) -> Dict[str, str]:
    """读 model.xml 的 name → driver_type 映射（与 run.py 同一语义）。"""
    if not model_path.exists():
        return {}
    try:
        root = ET.parse(model_path).getroot()
    except ET.ParseError:
        return {}
    result: Dict[str, str] = {}
    for model in root.findall("model"):
        name = (model.get("name") or "").strip()
        if not name:
            continue
        model_type = (model.get("type") or "ui").strip()
        driver_type = (model.get("driver_type") or "").strip()
        if driver_type:
            result[name] = driver_type
        elif model_type in {"interface", "database"}:
            result[name] = model_type
        else:
            result[name] = "web"
    return result


def _selected_case_ids(plan: Dict[str, Any]) -> List[str]:
    """计划里选中执行的 case id（尊重 plan 级与 case 级 execute）。"""
    if (plan.get("execute") or "是") == "否":
        return []
    return [c.get("id", "") for c in (plan.get("cases") or [])
            if (c.get("execute") or "是") != "否" and c.get("id")]


def collect_plan_driver_types(plan_path: Path, case_dir: Optional[Path] = None) -> set:
    """汇总一个计划选中用例所涉模型的 driver_type 集合。

    用于跨平台预检：一个计划若同时需要 android 与 ios 模型，任何单台设备都
    跑不完它 —— 必须在入队前拒绝，而不是让它跑到一半失败。
    """
    try:
        from .plan_parser import PlanParser
    except ImportError:                                   # pragma: no cover
        from rodski.core.plan_parser import PlanParser

    try:
        plan = PlanParser(str(plan_path)).parse_plan()
    except Exception as e:
        logger.warning(f"计划 {plan_path.name} 解析失败，跳过 driver_type 预检: {e}")
        return set()

    selected = set(_selected_case_ids(plan))
    if not selected:
        return set()

    case_dir = case_dir or (plan_path.parent.parent / "case")
    driver_types: set = set()
    for xml_file in sorted(case_dir.glob("*.xml")):
        try:
            root = ET.parse(xml_file).getroot()
        except ET.ParseError:
            continue
        models_in_file: set = set()
        for elem in root.iter("case"):
            if (elem.get("id") or "") not in selected:
                continue
            for step in elem.iter("test_step"):
                model_name = (step.get("model") or "").strip()
                if model_name:
                    models_in_file.add(model_name)
        if not models_in_file:
            continue
        model_map = _model_driver_types(case_dir.parent / "model" / "model.xml")
        for model_name in models_in_file:
            driver_types.add(model_map.get(model_name, "web"))
    return driver_types


def check_plan_for_queue(plan_path: Path, platform: str, *,
                         case_dir: Optional[Path] = None,
                         allow_cross_platform: bool = False) -> Tuple[bool, str, bool]:
    """入队前预检。

    Returns:
        (device_free, message, ok) —— device_free 表示这个计划不需要设备。
    """
    driver_types = collect_plan_driver_types(plan_path, case_dir)
    # driver_type="mobile" 是平台无关的移动端模型：真正用哪个平台由运行时
    # Mobile.Platform（子进程的 --platform）决定，故它与任何队列平台都兼容。
    mobile_types = driver_types & {"android", "ios"}
    platform_agnostic = "mobile" in driver_types

    if not mobile_types and not platform_agnostic:
        return True, "无移动端模型，将在设备队列之外执行", True

    if len(mobile_types) > 1:
        if allow_cross_platform:
            return False, f"跨平台计划（{sorted(mobile_types)}）已按 --allow-cross-platform-plan 放行", True
        return False, (f"计划同时需要 {sorted(mobile_types)} 设备，单一设备无法执行；"
                       f"拆分计划或加 --allow-cross-platform-plan"), False

    if mobile_types:
        only = next(iter(mobile_types))
        if only != platform:
            return False, (f"计划面向 {only}，但队列平台是 {platform}；"
                           f"请用 --platform {only} 或从队列中移除"), False

    other = driver_types - {"android", "ios", "mobile", "web"}
    if other:
        logger.warning(f"计划 {plan_path.name} 还包含非移动驱动类型 {sorted(other)}，将一并执行")
    return False, "", True


# ── 调度器 ───────────────────────────────────────────────────────────────────

class DeviceScheduler:
    """按计划建队列，多设备动态领取，每设备一个子进程。

    ``runner`` 可注入：签名 ``(device, task, argv, env) -> PlanOutcome``。
    注入后整个调度器不 spawn 任何进程，单元测试因此完全 hermetic。
    """

    def __init__(self, module_dir: Path, tasks: Sequence[PlanTask],
                 devices: Sequence[Device], *,
                 result_dir: Optional[Path] = None,
                 max_parallel: Optional[int] = None,
                 retry_failed_plans: int = 0,
                 requeue_on_device_loss: bool = True,
                 forward_args: Optional[Sequence[str]] = None,
                 runner: Optional[Callable] = None,
                 log_sink: Optional[Callable[[str], None]] = None):
        self.module_dir = Path(module_dir)
        self.result_dir = Path(result_dir) if result_dir else self.module_dir / "result"
        self.devices = list(devices)
        self.max_parallel = max(1, int(max_parallel or len(self.devices) or 1))
        self.retry_failed_plans = max(0, int(retry_failed_plans))
        self.requeue_on_device_loss = requeue_on_device_loss
        self.forward_args = list(forward_args or [])
        self._runner = runner
        self._log_sink = log_sink
        self._lock = threading.Lock()
        # 条件变量用于「队列暂时为空、但别的 worker 还在跑、随时可能因掉线重入队」
        # 这一窗口：worker 空转时必须等，否则重入队的计划会没人接手而被落下。
        self._cond = threading.Condition()
        self._busy = 0
        self._live = 0
        self._peak_live = 0

        self.queue = PlanQueue(tasks)
        self.outcomes: List[PlanOutcome] = []
        self.device_stats: Dict[str, Dict[str, Any]] = {
            d.udid: {"udid": d.udid, "platform": d.platform, "name": d.name,
                     "plans_executed": [], "lost": False}
            for d in self.devices
        }
        self.queue_dir: Optional[Path] = None

    # -- 生命周期 ---------------------------------------------------------

    def run(self) -> Dict[str, Any]:
        started = time.monotonic()
        self._create_queue_dir()
        self._log(f"[queue] 队列目录: {self.queue_dir}")
        self._log(f"[queue] 计划 {self.queue.outstanding()} 个 / 设备 {len(self.devices)} 台"
                  f" / 最大并行 {min(self.max_parallel, len(self.devices))}")

        workers = self.devices[:self.max_parallel]
        threads = [threading.Thread(target=self._worker, args=(d,), name=f"device-{d.udid[:8]}")
                   for d in workers]
        try:
            for t in threads:
                t.start()
            for t in threads:
                t.join()
        except KeyboardInterrupt:
            self._log("[queue] 收到中断，等待在跑的子进程结束…")
            for t in threads:
                t.join()
            summary = self._build_summary(started)
            summary["exit_code"] = 130
            self._write_summary(summary)
            raise

        summary = self._build_summary(started)
        self._write_summary(summary)
        return summary

    def _worker(self, device: Device) -> None:
        while True:
            task = self.queue.claim(device.udid)
            if task is None:
                if not self._wait_for_more_work():
                    return
                continue
            if self.device_stats.get(device.udid, {}).get("lost"):
                # 设备已掉线：把计划让给别的设备
                self.queue.requeue(task, front=True)
                self._notify_done()
                return

            with self._cond:
                self._busy += 1
            try:
                outcome = self._run_plan(device, task)
            finally:
                with self._cond:
                    self._busy -= 1
                    self._cond.notify_all()

            with self._lock:
                self.outcomes.append(outcome)
            if outcome.status == "PASS":
                self.device_stats[device.udid]["plans_executed"].append(task.plan_id)
                continue

            if outcome.device_lost:
                self.device_stats[device.udid]["lost"] = True
                if self.requeue_on_device_loss and task.attempts < MAX_ATTEMPTS_PER_PLAN:
                    task.requeued_from = device.udid
                    self.queue.requeue(task, front=True)
                    self._log(f"[queue] 设备掉线，计划 {task.plan_id} 重新入队")
                continue

            if task.attempts < MAX_ATTEMPTS_PER_PLAN and self.retry_failed_plans > 0:
                self.retry_failed_plans -= 1
                self.queue.requeue(task, front=True)
                self._log(f"[queue] 计划 {task.plan_id} 失败，重试一次")
                continue
            self.device_stats[device.udid]["plans_executed"].append(task.plan_id)

    def _wait_for_more_work(self) -> bool:
        """队列空时阻塞等待新工作。

        Return True 表示可能有新计划（重试/掉线重入队），False 表示可以退出。
        只有「队列空 且 没有别的 worker 在跑」才真的结束 —— 否则设备掉线导致的
        重入队计划会在窗口里被落下。
        """
        with self._cond:
            while self._busy > 0:
                if self.queue.outstanding() > 0:
                    return True
                self._cond.wait(timeout=0.1)
            return self.queue.outstanding() > 0

    def _notify_done(self) -> None:
        with self._cond:
            self._cond.notify_all()

    # -- 单个计划 ---------------------------------------------------------

    def _run_plan(self, device: Device, task: PlanTask) -> PlanOutcome:
        task.attempts += 1
        claimed_at = _now_iso()
        plan_output = self.queue_dir / "plans" / f"{task.plan_id}.json"
        output_json_rel = ""
        try:
            output_json_rel = str(plan_output.relative_to(self.module_dir))
        except ValueError:
            output_json_rel = str(plan_output)

        argv, env = self._build_child_argv(device, task, plan_output)

        with self._lock:
            self._live += 1
            self._peak_live = max(self._peak_live, self._live)
        started = time.monotonic()
        started_at = _now_iso()
        runner = self._runner or self._subprocess_runner
        try:
            result = runner(device, task, argv, env)
        except DeviceLostError as e:
            result = {"status": "ERROR", "exit_code": 1, "device_lost": True,
                      "pass_rate": "", "run_dir": "", "child_pid": 0, "error": str(e)}
        except Exception as e:                              # noqa: BLE001 - 汇总进 outcome
            result = {"status": "ERROR", "exit_code": 1, "device_lost": False,
                      "pass_rate": "", "run_dir": "", "child_pid": 0, "error": str(e)}
        finally:
            with self._lock:
                self._live -= 1

        finished_at = _now_iso()
        outcome = PlanOutcome(
            plan_id=task.plan_id,
            plan_path=str(task.plan_path),
            kind=task.kind,
            device_udid=device.udid if not task.device_free else None,
            attempt=task.attempts,
            status=result.get("status", "ERROR"),
            exit_code=int(result.get("exit_code", 1)),
            pass_rate=result.get("pass_rate", ""),
            claimed_at=claimed_at,
            started_at=started_at,
            finished_at=finished_at,
            duration=time.monotonic() - started,
            run_dir=result.get("run_dir", ""),
            child_pid=int(result.get("child_pid", 0)),
            output_json=output_json_rel,
            requeued_from=task.requeued_from,
            device_lost=bool(result.get("device_lost", False)),
            error=result.get("error", ""),
        )
        self._log(f"[{device.udid[:8]}] {task.plan_id}: {outcome.status}"
                  f" ({outcome.pass_rate or 'n/a'}, {outcome.duration:.1f}s)")
        return outcome

    def _build_child_argv(self, device: Device, task: PlanTask,
                          plan_output: Path) -> Tuple[List[str], Dict[str, str]]:
        """构造子进程 argv —— 子进程执行的就是完整的 `rodski run @plan_id`。"""
        argv = [sys.executable, "-c", _CHILD_BOOTSTRAP,
                "run", f"@{task.plan_id}",
                "--platform", device.platform,
                "--udid", device.udid,
                "--output", str(plan_output)]
        argv.extend(self.forward_args)

        env = dict(os.environ)
        env["PYTHONUNBUFFERED"] = "1"
        env["RODSKI_RUN_DIR_SUFFIX"] = self._run_dir_suffix(task, device)
        # 让子进程既能 `python -c "from rodski.rodski_cli import main"`（安装态），
        # 也能 `from rodski_cli import main`（源码树 dev-install）。两个根都塞进去。
        pkg_root = Path(__file__).resolve().parents[1]        # .../rodski
        for extra in (str(pkg_root), str(pkg_root.parent)):
            if extra not in env.get("PYTHONPATH", "").split(os.pathsep):
                env["PYTHONPATH"] = extra + (os.pathsep + env["PYTHONPATH"]
                                             if env.get("PYTHONPATH") else "")
        return argv, env

    @staticmethod
    def _run_dir_suffix(task: PlanTask, device: Device) -> str:
        return f"{task.plan_id}_{device.udid[:8]}"

    def _subprocess_runner(self, device: Device, task: PlanTask,
                           argv: List[str], env: Dict[str, str]) -> Dict[str, Any]:
        """默认 runner：真拉子进程，逐行转发输出并加设备前缀。"""
        plan_output = Path(argv[argv.index("--output") + 1])
        plan_output.parent.mkdir(parents=True, exist_ok=True)
        prefix = device.udid[:8]
        proc = subprocess.Popen(argv, cwd=str(self.module_dir), env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, bufsize=1)
        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                self._log(f"[{prefix}] {line.rstrip()}")
            proc.wait()
        except KeyboardInterrupt:
            proc.terminate()
            raise
        return self._collect_child_result(plan_output, proc.returncode,
                                          self.result_dir, env["RODSKI_RUN_DIR_SUFFIX"])

    @staticmethod
    def _collect_child_result(plan_output: Path, returncode: int,
                              result_dir: Optional[Path] = None,
                              run_dir_suffix: str = "") -> Dict[str, Any]:
        """从子进程写出的 JSON 里取通过率；没写出就只凭退出码判断。"""
        status = "PASS" if returncode == 0 else ("FAIL" if returncode == 1 else "ERROR")
        pass_rate = ""
        if plan_output.exists():
            try:
                payload = json.loads(plan_output.read_text(encoding="utf-8"))
                summary = payload.get("summary") or {}
                pass_rate = f"{summary.get('passed', 0)}/{summary.get('total', 0)}"
                if int(summary.get("failed", 0)) > 0:
                    status = "FAIL"
            except (ValueError, OSError):
                pass
        run_dir = ""
        if result_dir and run_dir_suffix:
            # 子进程的结果目录名 = rodski_<ts>_<suffix>，ts 只有子进程知道，用后缀找
            matches = sorted(Path(result_dir).glob(f"rodski_*_{run_dir_suffix}"))
            if matches:
                run_dir = str(matches[-1])
        return {"status": status, "exit_code": returncode, "pass_rate": pass_rate,
                "run_dir": run_dir, "child_pid": 0, "device_lost": False, "error": ""}

    # -- 汇总 -------------------------------------------------------------

    def _create_queue_dir(self) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.queue_dir = self.result_dir / f"rodski_{timestamp}_queue"
        (self.queue_dir / "plans").mkdir(parents=True, exist_ok=True)

    def _build_summary(self, started: float) -> Dict[str, Any]:
        by_status: Dict[str, int] = {}
        for outcome in self.outcomes:
            by_status[outcome.status] = by_status.get(outcome.status, 0) + 1
        unclaimed = self.queue.outstanding()
        failed = by_status.get("FAIL", 0) + by_status.get("ERROR", 0)

        devices = []
        for udid, stats in self.device_stats.items():
            devices.append({
                **stats,
                "plans": len(stats["plans_executed"]),
                "planned_plans": len(stats["plans_executed"]),
            })

        exit_code = 0 if (failed == 0 and unclaimed == 0) else 1
        # 空队列（没有 execute=是 的计划）也退出 0：没有失败，也没有被落下的计划

        return {
            "queue_id": self.queue_dir.name.replace("rodski_", "").replace("_queue", "")
            if self.queue_dir else "",
            "platform": self.devices[0].platform if self.devices else "",
            "max_parallel": min(self.max_parallel, len(self.devices)) if self.devices else 0,
            "peak_parallel": self._peak_live,
            "duration": round(time.monotonic() - started, 3),
            "devices": devices,
            "plans": [o.to_dict() for o in self.outcomes],
            "summary": {
                "total_plans": len(self.outcomes),
                "passed": by_status.get("PASS", 0),
                "failed": by_status.get("FAIL", 0),
                "error": by_status.get("ERROR", 0),
                "unclaimed": unclaimed,
            },
            "exit_code": exit_code,
        }

    def _write_summary(self, summary: Dict[str, Any]) -> None:
        if not self.queue_dir:
            return
        summary["started_at"] = summary.get("started_at") or _now_iso()
        summary["finished_at"] = _now_iso()
        path = self.queue_dir / "summary.json"
        path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        self._log(f"[queue] 汇总: {path}")

    def _log(self, message: str) -> None:
        if self._log_sink:
            self._log_sink(message)
        else:
            print(message, flush=True)


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="milliseconds")


def build_tasks(plans: Sequence[Path], platform: str, *,
                case_dir: Optional[Path] = None,
                allow_cross_platform: bool = False) -> Tuple[List[PlanTask], List[PlanTask]]:
    """把计划路径列表转成 PlanTask，并做入队预检。

    Returns:
        (device_tasks, device_free_tasks)
    Raises:
        MixedPlanKindError / CrossPlatformPlanError
    """
    try:
        from .plan_parser import PlanParser
    except ImportError:                                   # pragma: no cover
        from rodski.core.plan_parser import PlanParser

    device_tasks: List[PlanTask] = []
    free_tasks: List[PlanTask] = []
    for plan_path in plans:
        try:
            kind = (PlanParser(str(plan_path)).parse_plan().get("kind") or "suite")
        except Exception:
            kind = "suite"

        if kind == "load":
            raise MixedPlanKindError(
                f"设备队列不支持 kind=load 计划（{plan_path.stem}），请用 `rodski run @{plan_path.stem}` 单独执行")

        device_free, message, ok = check_plan_for_queue(
            plan_path, platform, case_dir=case_dir,
            allow_cross_platform=allow_cross_platform)
        if not ok:
            raise CrossPlatformPlanError(f"{plan_path.stem}: {message}")
        if device_free:
            free_tasks.append(PlanTask(plan_id=plan_path.stem, plan_path=plan_path,
                                       kind=kind, device_free=True))
        else:
            device_tasks.append(PlanTask(plan_id=plan_path.stem, plan_path=plan_path, kind=kind))
    return device_tasks, free_tasks
