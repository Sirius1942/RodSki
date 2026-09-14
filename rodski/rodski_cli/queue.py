"""queue 子命令 — 多设备计划队列调度。

把若干计划放进一个队列，由多台设备**动态领取**：先跑完的设备回去领下一个，
而不是预先分配。计划是调度的最小单元，任何一个计划都只会在一台设备上整体执行
（「一个 plan 只用一个 app 设备」），不存在把计划拆到多台设备的方式。

    rodski queue --module product/demo --plans @p1,@p2,@p3 \
                 --devices <UDID-A>,<UDID-B> --platform ios

默认单设备场景**不受影响**：`rodski run` 的行为完全不变，本命令只在显式给出
`--devices`（≥2 台）时才真正并行。
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional, Tuple

try:
    from ..core.device_scheduler import (
        Device,
        DeviceScheduler,
        DeviceSelection,
        DeviceSelectionError,
        DeviceUnavailableError,
        MixedPlanKindError,
        PlanTask,
        CrossPlatformPlanError,
        build_tasks,
        discover_devices,
        format_device_selection,
        load_mobile_group,
        parse_device_selection,
        platform_hint,
        resolve_explicit_devices,
        resolve_platform,
        select_devices,
    )
except ImportError:                                      # pragma: no cover
    from core.device_scheduler import (                   # type: ignore[no-redef]
        Device,
        DeviceScheduler,
        DeviceSelection,
        DeviceSelectionError,
        DeviceUnavailableError,
        MixedPlanKindError,
        PlanTask,
        CrossPlatformPlanError,
        build_tasks,
        discover_devices,
        format_device_selection,
        load_mobile_group,
        parse_device_selection,
        platform_hint,
        resolve_explicit_devices,
        resolve_platform,
        select_devices,
    )


def setup_parser(subparsers):
    p = subparsers.add_parser(
        "queue",
        help="多设备计划队列调度（一个计划只在一台设备上执行）",
        description="按计划建队列，多台设备动态领取；先跑完的设备领下一个计划",
    )
    p.add_argument("--module", default=None,
                   help="测试模块目录（默认取当前目录，自动向上兼容 case/model/plan 子目录）")
    p.add_argument("--plans", action="append", dest="plans", default=None,
                   help="计划引用列表（@plan_id，逗号分隔或多次传入）；"
                        "缺省取 plan/ 下所有 execute=是 的计划")
    p.add_argument("--devices", action="append", dest="devices", default=None,
                   help="显式设备池（UDID 或设备名，逗号分隔或多次传入）；"
                        "给定时跳过自动发现与 globalvalue 里的 Device* 配置")
    p.add_argument("--platform", choices=["android", "ios"], default=None,
                   help="设备平台（android/ios），缺省读 globalvalue.xml 的 Mobile.Platform")
    p.add_argument("--max-parallel", type=int, default=None, dest="max_parallel",
                   help="最大并行 worker 数（默认 = 设备数）")
    p.add_argument("--list-devices", action="store_true", dest="list_devices",
                   help="枚举可用设备后退出")
    p.add_argument("--retry-failed-plans", type=int, default=0, dest="retry_failed_plans",
                   help="计划失败后的重试次数（默认 0，不重试）")
    p.add_argument("--no-requeue-on-device-loss", action="store_true",
                   dest="no_requeue_on_device_loss",
                   help="设备掉线时不把未完成的计划重新入队（默认重新入队一次）")
    p.add_argument("--allow-cross-platform-plan", action="store_true",
                   dest="allow_cross_platform_plan",
                   help="放行同时需要 android 与 ios 模型的计划（默认拒绝）")
    p.add_argument("--dry-run", action="store_true", dest="dry_run",
                   help="只打印队列与设备分配预检，不实际执行")


def _split(raw_values) -> Optional[List[str]]:
    """逗号分隔 / 多次传入 → 去重保序的列表（与 run.py 的 --tag 语义一致）。"""
    if raw_values is None:
        return None
    values = [raw_values] if isinstance(raw_values, str) else list(raw_values)
    parsed: List[str] = []
    for value in values:
        if not value:
            continue
        for part in str(value).split(","):
            part = part.strip()
            if part and part not in parsed:
                parsed.append(part)
    return parsed or None


def _resolve_module_dir(raw: Optional[str]) -> Path:
    """解析模块目录：显式路径优先，否则从当前目录向上兼容 case/model/plan 子目录。"""
    if raw:
        return Path(raw).expanduser().resolve()
    current = Path.cwd()
    if current.name in {"case", "model", "data", "plan"}:
        return current.parent
    return current


def handle(args) -> int:
    module_dir = _resolve_module_dir(getattr(args, "module", None))
    if not module_dir.is_dir():
        print(f"错误: 模块目录不存在: {module_dir}", file=sys.stderr)
        return 1

    cli_platform = getattr(args, "platform", None)
    explicit_devices = _split(getattr(args, "devices", None))

    # platform 推导：显式 > globalvalue.xml；显式给了设备但推不出平台时**必须**报错，
    # 猜平台等于拿错设备去跑（Android 的 UDID 给 iOS 用不会报错，只会建会话失败或打错机器）
    platform = resolve_platform(module_dir, cli_platform, probe=not explicit_devices)
    if platform is None:
        print("错误: 显式指定 --devices 时必须给出 --platform（android/ios）", file=sys.stderr)
        return 1

    if getattr(args, "list_devices", False):
        return _list_devices(module_dir, platform)

    # 设备选择：执行配置（globalvalue 的 Mobile 组）为主，--devices 为 CLI 覆盖。
    # 优先级：--devices > DeviceList > 自动发现 + DeviceCount/DeviceMix/DeviceScope
    selection = parse_device_selection(load_mobile_group(module_dir, platform))
    if explicit_devices:
        selection.explicit = explicit_devices
        selection.count = len(explicit_devices)

    # 零设备是唯一的硬失败；数量/类别不足一律降级并告警（「至少一台能跑就自动执行」）
    try:
        devices, selection_warnings = _resolve_devices(platform, selection)
    except DeviceSelectionError:
        print(f"错误: 未发现任何可用 {platform} 设备", file=sys.stderr)
        print(platform_hint(platform), file=sys.stderr)
        return 1
    for line in format_device_selection(devices, selection, selection_warnings):
        print(line)

    plans = _resolve_plans(module_dir, _split(getattr(args, "plans", None)))
    if plans is None:
        return 1
    if not plans:
        print(f"错误: {module_dir}/plan/ 下没有 execute=是 的计划", file=sys.stderr)
        return 1

    try:
        device_tasks, _free_tasks = build_tasks(
            plans, platform,
            case_dir=module_dir / "case",
            allow_cross_platform=getattr(args, "allow_cross_platform_plan", False),
        )
    except MixedPlanKindError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except CrossPlatformPlanError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    print(f"设备队列: {len(device_tasks)} 个计划 / {len(devices)} 台设备 ({platform})")
    for t in device_tasks:
        print(f"  计划: @{t.plan_id}")

    if getattr(args, "dry_run", False):
        print("\n[dry-run] 仅预检，未执行")
        return 0

    if len(devices) == 1:
        # 单设备：语义退化，但仍走队列（顺序执行），保持输出与并行路径一致
        print("提示: 只有 1 台设备，计划将顺序执行")

    scheduler = DeviceScheduler(
        module_dir, device_tasks, devices,
        max_parallel=getattr(args, "max_parallel", None),
        retry_failed_plans=getattr(args, "retry_failed_plans", 0),
        requeue_on_device_loss=not getattr(args, "no_requeue_on_device_loss", False),
        forward_args=_forward_run_args(args),
    )
    summary = scheduler.run()

    stats = summary["summary"]
    print(f"\n队列完成: {stats['passed']}/{stats['total_plans']} 计划通过"
          f"（失败 {stats['failed']}，错误 {stats['error']}，未领取 {stats['unclaimed']}）"
          f"，峰值并行 {summary['peak_parallel']}，耗时 {summary['duration']:.1f}s")
    return int(summary["exit_code"])


def _list_devices(module_dir: Path, platform: Optional[str]) -> int:
    discovered = platform or resolve_platform(module_dir, None)
    devices = discover_devices(discovered)
    if not devices:
        print(f"未发现可用 {discovered} 设备", file=sys.stderr)
        print(platform_hint(discovered), file=sys.stderr)
        return 1
    labels = {"real": "真机", "simulator": "模拟器"}
    print(f"可用 {discovered} 设备 ({len(devices)}):")
    for d in devices:
        tag = labels.get(d.kind, "未知")
        print(f"  [{tag}] {d.udid}  {d.name or '-'}  [{d.state or 'unknown'}]")
    return 0


def _resolve_devices(platform: str, selection: DeviceSelection) -> Tuple[List[Device], List[str]]:
    """按执行层配置选出设备。

    - `DeviceList` / `--devices` 非空 → 直接采用给定设备池（条目可为 UDID 或设备名）
    - 否则自动发现后用 DeviceCount/DeviceMix/DeviceScope 排序与截断

    只有「一台都没有」才抛 `DeviceSelectionError`；不足一律降级并返回告警。
    """
    discovered = discover_devices(platform)
    if selection.explicit:
        selected, warnings = resolve_explicit_devices(platform, selection.explicit, discovered)
        if not selected:
            raise DeviceSelectionError("未发现任何可用设备")
        return selected, warnings
    return select_devices(discovered, selection)


def _resolve_plans(module_dir: Path, refs: Optional[List[str]]) -> Optional[List[Path]]:
    """把 --plans 归一为计划 XML 路径；缺省取 plan/ 下 execute=是 的全部。"""
    plan_dir = module_dir / "plan"
    if refs:
        resolved: List[Path] = []
        for ref in refs:
            plan_id = ref[1:] if ref.startswith("@") else ref
            path = plan_dir / f"{plan_id}.xml"
            if not path.exists():
                print(f"错误: 测试计划不存在: {path}", file=sys.stderr)
                return None
            resolved.append(path)
        return resolved

    if not plan_dir.is_dir():
        return []
    return _default_plans(plan_dir)


def _default_plans(plan_dir: Path) -> List[Path]:
    """plan/*.xml 中 plan 级 execute=是 的计划，按文件名排序。"""
    import xml.etree.ElementTree as ET

    plans: List[Path] = []
    for xml_file in sorted(plan_dir.glob("*.xml")):
        try:
            root = ET.parse(xml_file).getroot()
        except ET.ParseError:
            continue
        if (root.get("execute") or "是").strip() != "是":
            continue
        plans.append(xml_file)
    return plans


def _forward_run_args(args) -> List[str]:
    """把可透传给子进程 `rodski run` 的执行类参数原样转发。"""
    forwarded: List[str] = []
    for attr, flag in (("report", "--report"), ("trace", "--trace"),
                       ("verbose", "--verbose"), ("coverage", "--coverage")):
        value = getattr(args, attr, None)
        if attr == "report":
            if value:
                forwarded.extend([flag, str(value)])
        elif value:
            forwarded.append(flag)
    return forwarded
