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
import tempfile
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
    """一台可用设备。

    ``kind`` 区分模拟器与真机。平台相同、Appium 路径不同（真机走真实设备
    XCUITest，需要签名并部署 WDA），故「要几台什么设备」必须在选择阶段就能表达，
    不能等到建会话才失败。
    """

    udid: str
    platform: str          # "android" | "ios"
    name: str = ""
    state: str = ""
    kind: str = "simulator"    # "simulator" | "real" | "unknown"

    @property
    def is_real(self) -> bool:
        return self.kind == "real"

    def __str__(self) -> str:
        label = {"real": "真机", "simulator": "模拟器"}.get(self.kind, "")
        return f"{self.name or self.udid}({self.platform}{'/' + label if label else ''})"


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

def _is_adb_emulator(serial: str, fields: Sequence[str]) -> bool:
    """adb 里的这台是不是模拟器。

    判据用 serial 前缀 ``emulator-``：这是 adb 自己为 AVD 分配的固定形式
    （``emulator-5554``），也是 ``adb devices`` 唯一稳定可依赖的区分方式。
    限定符里的 ``device:emu`` / ``product:sdk`` 只是**附加**佐证，不作为主判据 ——
    它们由设备端上报，改名或换镜像就没了，而 serial 由 adb 生成。
    """
    if (serial or "").startswith("emulator-"):
        return True
    for token in fields:
        if token in ("device:emu", "product:sdk"):
            return True
    return False


def _parse_adb_devices(stdout: str) -> List[Device]:
    """解析 ``adb devices -l`` 输出。

    只保留 state == ``device`` 的行；``unauthorized`` / ``offline`` /
    ``no permissions`` 都会让 Appium 建会话失败，必须提前滤掉。
    友好名取 ``model:`` 限定符（没有则留空）。

    **模拟器与真机必须分开标注**：``adb`` 对两者用的是同一套通道，早期实现把
    每一台都标成 ``kind="real"`` —— 于是 AVD 在 ``--list-devices`` 里显示成
    ``[真机]``，``DeviceMix=real,simulator`` 也失去意义（两台都算 real，
    混跑配置永远凑不出「一台真机一台模拟器」）。Android 混跑能力正是建立在这
    个区分上，故按 serial 前缀判定。
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
        devices.append(Device(
            udid=fields[0], platform="android", name=name, state="device",
            kind="simulator" if _is_adb_emulator(fields[0], fields) else "real"))
    return devices


def _parse_simctl_devices(stdout_json: str) -> List[Device]:
    """解析 ``xcrun simctl list devices available --json`` 输出。

    用 ``available`` 而非 ``booted``：未启动的模拟器也应枚举出来（调用方决定
    是否 boot）。``isAvailable == false`` 的条目（运行时不匹配等）会被滤掉。

    **只保留 iOS 运行时**：同一份 ``simctl list`` 里还有 watchOS / tvOS 模拟器
    （本机就有十几台 Apple Watch），它们装不了 iOS 应用，混进设备池只会让
    「DeviceMix=simulator」选中一台注定建不起会话的设备。
    """
    try:
        payload = json.loads(stdout_json or "{}")
    except (ValueError, TypeError):
        return []
    devices: List[Device] = []
    for runtime, runtime_devices in (payload.get("devices") or {}).items():
        if "SimRuntime.iOS-" not in str(runtime):
            continue
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
                kind="simulator",
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


def _parse_devicectl_devices(stdout_json: str) -> List[Device]:
    """解析 ``xcrun devicectl list devices --json-output <file>`` 的 JSON。

    只保留**已连接的真机**：``platform == iOS`` + ``reality == physical`` +
    ``transportType == wired`` + ``pairingState == paired``。

    刻意**不**用 ``tunnelState`` 作为可用性判据：开发者模式刚打开、CoreDevice
    隧道尚未建立时它是 ``disconnected``，拿它过滤会把一台完全正常的设备误杀。
    （开发者模式**关闭**时隧道同样是 disconnected —— 两者无法靠 tunnelState 区分。）
    ``watchOS`` / 未连接的设备（``transportType`` 为 null）都会被滤掉。
    """
    try:
        payload = json.loads(stdout_json or "{}")
    except (ValueError, TypeError):
        return []
    devices: List[Device] = []
    for entry in (payload.get("result") or {}).get("devices") or []:
        if not isinstance(entry, dict):
            continue
        hardware = entry.get("hardwareProperties") or {}
        props = entry.get("deviceProperties") or {}
        conn = entry.get("connectionProperties") or {}
        if (hardware.get("platform") or "").lower() != "ios":
            continue
        if (hardware.get("reality") or "").lower() != "physical":
            continue
        if conn.get("transportType") != "wired" or conn.get("pairingState") != "paired":
            continue
        udid = (hardware.get("udid") or "").strip()
        if not udid:
            continue
        devices.append(Device(
            udid=udid,
            platform="ios",
            name=(props.get("name") or "").strip(),
            state="connected",
            kind="real",
        ))
    return devices


def _default_devicectl_runner() -> str:
    """执行 ``xcrun devicectl list devices``，返回 **JSON 文件内容**。

    必须用 ``--json-output`` 而不是 stdout：Apple 明确说明 stdout 面向人眼、
    不保证跨版本稳定，JSON 输出到文件才是脚本接口。
    """
    xcrun = shutil.which("xcrun")
    if not xcrun:
        logger.warning("未找到 xcrun，跳过 iOS 真机枚举")
        return ""
    handle = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    out_path = handle.name
    handle.close()
    try:
        subprocess.run([xcrun, "devicectl", "list", "devices", "--json-output", out_path],
                       capture_output=True, text=True, timeout=30)
        try:
            return Path(out_path).read_text(encoding="utf-8")
        except OSError:
            return ""
    except (OSError, subprocess.SubprocessError) as e:
        logger.warning(f"xcrun devicectl 执行失败: {e}")
        return ""
    finally:
        try:
            os.unlink(out_path)
        except OSError:
            pass


def discover_devices(platform: str, *,
                     adb_runner: Optional[Callable[[], str]] = None,
                     simctl_runner: Optional[Callable[[], str]] = None,
                     devicectl_runner: Optional[Callable[[], str]] = None) -> List[Device]:
    """按平台枚举可用设备。runner 可注入，便于单测不依赖真机。

    iOS 会同时枚举**模拟器**（simctl）与**真机**（devicectl）：一台电脑上
    真机与模拟器混跑是常规用法，只列模拟器会让真机必须由调用方手动给 UDID。
    devicectl 不可用（未装 / 无真机）时静默降级为「只有模拟器」，不影响既有行为。
    """
    if platform == "android":
        return _parse_adb_devices((adb_runner or _default_adb_runner)())
    if platform == "ios":
        simulators = _parse_simctl_devices((simctl_runner or _default_simctl_runner)())
        real_devices = _parse_devicectl_devices(
            (devicectl_runner or _default_devicectl_runner)())
        return simulators + real_devices
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


# ── 设备选择（用例执行层配置）────────────────────────────────────────────────
#
# 「用几台、什么类别的设备」是**执行配置**，不是调用方每次手敲的 UDID 列表。
# 配置写在 data/globalvalue.xml（或平台专属 globalvalue_<platform>.xml）的
# Mobile 组里，随用例/计划一起版本化：
#
#   <var name="DeviceCount" value="2"/>           期望设备数（不写 = 用上全部发现的设备）
#   <var name="DeviceMix"   value="real,simulator"/>  组合偏好（默认不限制）
#   <var name="DeviceScope" value="all"/>         all | real | simulator
#   <var name="DeviceList"  value="UDID-A,UDID-B"/> 可选，显式设备池（跳过发现）
#
# 三条语义约束（与 §11.5 一致）：
#   1. **零设备即失败**：任何情况下发现 0 台设备都必须硬报错，不得回落到
#      「没 udid 也照跑」—— 那正是 devices[0] 抢占的来源。
#   2. **不足则降级，降级必告警**：要 2 台只找到 1 台、或凑不出 real，
#      按实际可用设备继续执行（用户明确要求「至少有一个可以执行就自动执行」），
#      但必须打印告警说明少用了什么。绝不静默降级。
#   3. **不得为凑组合而拒绝执行**：DeviceMix 是偏好不是门槛；只有当发现结果
#      为空时才报错。

VALID_DEVICE_SCOPES = ("all", "real", "simulator")


@dataclass
class DeviceSelection:
    """设备选择配置（来自 globalvalue 的 Mobile 组）。"""

    count: Optional[int] = None                       # None = 不限制（全部发现设备）
    mix: List[str] = field(default_factory=list)     # 组合偏好，保序去重
    scope: str = "all"                                # all | real | simulator
    explicit: List[str] = field(default_factory=list)  # DeviceList

    @property
    def is_default(self) -> bool:
        """是否等同「不限制」——用于判断是否需要打印配置来源、是否转队列。"""
        return (self.count is None and not self.mix
                and self.scope == "all" and not self.explicit)


def _split_csv(raw) -> List[str]:
    """逗号分隔 → 去重保序列表（空串与空白项丢弃）。"""
    result: List[str] = []
    for part in str(raw or "").split(","):
        part = part.strip()
        if part and part not in result:
            result.append(part)
    return result


def parse_device_selection(mobile_group: Optional[Dict[str, Any]]) -> DeviceSelection:
    """从 globalvalue 的 Mobile 组读设备选择配置。

    缺省值刻意是「不限制」：不写任何 Device* 变量时行为与 v11.2.0 逐字节相同
    （用上全部发现的设备，队列动态领取）。
    """
    group = mobile_group or {}

    raw_count = str(group.get("DeviceCount") or "").strip()
    count: Optional[int] = None
    if raw_count:
        try:
            count = int(raw_count)
        except ValueError:
            logger.warning(f"DeviceCount 不是整数: {raw_count!r}，按「不限制」处理")
            count = None
        if count is not None and count < 1:
            logger.warning(f"DeviceCount={count} 小于 1，按 1 处理")
            count = 1

    scope = str(group.get("DeviceScope") or "all").strip().lower()
    if scope not in VALID_DEVICE_SCOPES:
        logger.warning(f"DeviceScope={scope!r} 不是 {VALID_DEVICE_SCOPES} 之一，按 all 处理")
        scope = "all"

    return DeviceSelection(
        count=count,
        mix=_split_csv(group.get("DeviceMix")),
        scope=scope,
        explicit=_split_csv(group.get("DeviceList")),
    )


class DeviceSelectionError(Exception):
    """设备数量/类别与用例执行层配置不符，且无法降级。"""


def _device_readiness_rank(device: Device) -> int:
    """同类设备里的「就绪度」排序键：已启动/已连接排在未启动前面。

    自动发现在本机常常能看到 30+ 台 Shutdown 的模拟器。若按枚举顺序取前 N 台，
    会优先选中需要先 boot 才能用的设备，而把已经跑着的晾在一边 —— 既慢又反直觉。
    """
    state = (device.state or "").strip().lower()
    if device.is_real:
        return 0 if state in ("connected", "available", "paired") else 1
    return 0 if state in ("booted", "connected") else 1


def _apply_mix_preference(devices: List[Device], mix: List[str], scope: str) -> List[Device]:
    """按 scope + mix 重排设备，让「最想用」的排在前面（不改成员、不报错）。

    选择阶段只做**排序与截断**，不做拒绝：数量不足由调用方降级并告警。
    mix 点名的类别优先取，同类内已就绪的优先。
    """
    if scope == "real":
        devices = [d for d in devices if d.is_real]
    elif scope == "simulator":
        devices = [d for d in devices if not d.is_real]

    if not mix:
        # 没写 DeviceMix 时**真机优先**：真机是更稀缺、更接近真实用户的资源，
        # 插上就该用上。若按发现顺序取前 N 台，本机 20+ 台模拟器会把真机挤到
        # 队尾 —— 配置里明明有一台真机可用，实际却一台都没用上（用户实测到）。
        # 同类内仍按就绪度排（已 Booted 的模拟器优先于要现 boot 的）。
        return sorted(devices, key=lambda d: (0 if d.is_real else 1,
                                              _device_readiness_rank(d)))

    remaining = list(devices)
    ordered: List[Device] = []
    for wanted in mix:
        if wanted == "real":
            pick = [d for d in remaining if d.is_real]
        elif wanted == "simulator":
            pick = [d for d in remaining if not d.is_real]
        else:
            logger.warning(f"DeviceMix 含未知取值 {wanted!r}（可选 real / simulator），已忽略")
            continue
        pick.sort(key=_device_readiness_rank)          # 稳定排序：同类内已就绪的在前
        for d in pick:
            if d not in ordered:
                ordered.append(d)
        remaining = [d for d in remaining if d not in ordered]
    ordered.extend(remaining)      # 未在 mix 里点名的设备排在后面，仍可被用上
    return ordered


def resolve_explicit_devices(platform: str, entries: Sequence[str],
                             discovered: Sequence[Device]) -> Tuple[List[Device], List[str]]:
    """把显式设备条目解析成 :class:`Device`（条目可以是 UDID，也可以是设备名）。

    支持设备名是为了让配置/命令行不必写死 UDID —— UDID 换台机器就失效，设备名
    在同一个 target 上稳定（``--devices Tars2,iPhone 16`` 比一串十六进制可读得多）。

    能匹配到发现结果时沿用其 ``kind``/``state``（真机/模拟器标注才准确）；
    匹配不到则按原样当 UDID 采用 —— 用户可能刻意给一台当前发现不到的设备
    （刚 boot 还没被枚举到，或不在自动发现范围内）。
    """
    by_udid = {d.udid: d for d in discovered}
    by_name = {(d.name or "").strip().casefold(): d for d in discovered if (d.name or "").strip()}

    resolved: List[Device] = []
    warnings: List[str] = []
    for entry in entries:
        hit = by_udid.get(entry) or by_name.get(entry.strip().casefold())
        if hit is not None:
            resolved.append(hit)
        else:
            warnings.append(f"设备 {entry!r} 不在当前发现结果里，按显式 UDID 直接采用")
            resolved.append(Device(udid=entry, platform=platform, name="",
                                   state="explicit", kind="unknown"))
    return resolved, warnings


def select_devices(devices: Sequence[Device], selection: DeviceSelection) -> Tuple[List[Device], List[str]]:
    """按配置从已发现设备里挑出实际要用的那些。

    Returns:
        (selected, warnings) —— warnings 是要打印给用户的降级说明，绝不静默。

    Raises:
        DeviceSelectionError: 发现结果为空（零设备是唯一的硬失败）。
    """
    if not devices:
        raise DeviceSelectionError("未发现任何可用设备")

    warnings: List[str] = []
    pool = _apply_mix_preference(list(devices), selection.mix, selection.scope)
    if selection.scope != "all" and len(pool) < len(devices):
        warnings.append(
            f"DeviceScope={selection.scope} 过滤掉 {len(devices) - len(pool)} 台设备"
            f"（可用 {len(devices)} → {len(pool)}）")
    if not pool:
        # scope 过滤把设备清空了：这是配置与现状矛盾，按 scope 无法执行。
        # 但「至少有一台能跑就自动执行」优先 —— 退回过滤前的设备池并告警。
        warnings.append(
            f"DeviceScope={selection.scope} 下没有任何设备，已忽略该过滤条件继续执行")
        pool = list(devices)

    # 组合偏好：mix 点名的类别若一台都没有，明确告警（不拒绝执行）
    if selection.mix:
        available_kinds = {("real" if d.is_real else "simulator") for d in pool}
        for wanted in selection.mix:
            if wanted in ("real", "simulator") and wanted not in available_kinds:
                warnings.append(f"DeviceMix 要求 {wanted}，但当前没有可用的 {wanted} 设备")

    # count 是期望值：不足要降级告警（用户可据此判断「真机没插上」这类现场问题），
    # 富余则按配置截断 —— 那是用户点名要的，不必打扰。
    if selection.count is None:
        selected = pool
    elif len(pool) < selection.count:
        warnings.append(
            f"DeviceCount={selection.count}，实际可用 {len(pool)} 台，降级为 {len(pool)} 台执行")
        selected = pool
    else:
        selected = pool[:selection.count]

    return selected, warnings


def format_device_selection(selected: Sequence[Device], selection: DeviceSelection,
                            warnings: Sequence[str]) -> List[str]:
    """把选择结果渲染成可直接打印的几行（调用方决定往 stdout 还是 logger）。"""
    lines: List[str] = []
    if not selection.is_default:
        desc = []
        if selection.count is not None:
            desc.append(f"DeviceCount={selection.count}")
        if selection.mix:
            desc.append(f"DeviceMix={'+'.join(selection.mix)}")
        if selection.scope != "all":
            desc.append(f"DeviceScope={selection.scope}")
        if selection.explicit:
            desc.append(f"DeviceList={len(selection.explicit)} 台")
        lines.append(f"设备选择（执行配置）：{', '.join(desc)}")

    kinds: Dict[str, int] = {}
    for d in selected:
        key = {"real": "真机", "simulator": "模拟器"}.get(d.kind, "未知类别")
        kinds[key] = kinds.get(key, 0) + 1
    summary = "、".join(f"{v} 台{k}" for k, v in kinds.items())
    lines.append(f"实际选用 {len(selected)} 台设备（{summary}）：")
    for d in selected:
        tag = {"real": "真机", "simulator": "模拟器"}.get(d.kind, "未知")
        lines.append(f"  - [{tag}] {d.udid}  {d.name or '-'}")

    for w in warnings:
        lines.append(f"  [WARN] {w}")
    return lines


def load_mobile_group(module_dir: Path, platform: Optional[str] = None) -> Dict[str, Any]:
    """读模块 globalvalue 里的 **Mobile 组**（含平台专属文件的深合并）。

    与 `rodski run --platform` 的合并语义一致：`globalvalue_<platform>.xml` 的
    group/var 覆盖 `globalvalue.xml`。设备选择配置就读这里，故配置与用例、
    计划放在一起版本化。

    返回的是 Mobile 组本身（``{var_name: value}``），不是整个 group 映射 ——
    调用方拿到的就是能直接喂给 :func:`parse_device_selection` 的那层。
    """
    try:
        from .global_value_parser import GlobalValueParser
    except ImportError:                                   # pragma: no cover
        from rodski.core.global_value_parser import GlobalValueParser

    merged: Dict[str, Any] = {}
    data_dir = Path(module_dir) / "data"
    candidates = [data_dir / "globalvalue.xml"]
    if platform:
        candidates.append(data_dir / f"globalvalue_{platform}.xml")

    for path in candidates:
        if not path.exists():
            continue
        try:
            for group, vars_ in GlobalValueParser(str(path)).parse().items():
                if group != "Mobile":
                    continue
                merged.update(vars_)
        except Exception as e:                            # noqa: BLE001 - 配置读不出不该让调度崩
            logger.warning(f"读取 {path.name} 失败，跳过: {e}")
    return merged


def is_multi_device_configured(mobile_group: Optional[Dict[str, Any]]) -> bool:
    """模块配置是否要求**多设备/特定组合**（`rodski run` 据此决定是否转队列）。

    只有真正表达「不止一台」或「限定类别」的配置才算数：
    `DeviceCount>=2`、`DeviceMix`、`DeviceScope`、`DeviceList`。
    显式写 `DeviceCount=1` 是「就要一台」，与不写等价 —— 不得因此转队列。
    """
    selection = parse_device_selection(mobile_group)
    if selection.mix or selection.explicit or selection.scope != "all":
        return True
    return selection.count is not None and selection.count > 1


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
        self._started_at: str = ""

    # -- 生命周期 ---------------------------------------------------------

    def run(self) -> Dict[str, Any]:
        started = time.monotonic()
        self._started_at = _now_iso()
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
            # 队列级起止时刻由父进程记录（与 per-plan 时间戳同源）。缺了它
            # summary.json 里 started_at 得靠 _write_summary 兜底填成「写完的瞬间」，
            # 于是与 finished_at 相等 —— 看起来像「队列耗时 0 秒」。
            "started_at": self._started_at or _now_iso(),
            "finished_at": _now_iso(),
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
