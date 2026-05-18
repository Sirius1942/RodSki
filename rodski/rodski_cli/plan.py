"""plan 子命令 — 管理 RodSki 测试计划 (plan/*.xml)"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional


def setup_parser(subparsers):
    p = subparsers.add_parser("plan", help="管理测试计划 (plan/*.xml)")
    sub = p.add_subparsers(dest="plan_action", help="plan 子命令")

    # init
    init_p = sub.add_parser("init", help="创建 plan/project_full.xml")
    init_p.add_argument("--kind", default="suite", choices=["suite", "scenario_debug", "step_debug"])
    init_p.add_argument("--default-execute", default="是", dest="default_execute", choices=["是", "否"])
    init_p.add_argument("--force", action="store_true")

    # list
    sub.add_parser("list", help="列出 plan/*.xml")

    # show
    show_p = sub.add_parser("show", help="显示 plan 内容")
    show_p.add_argument("plan_id")

    # validate
    validate_p = sub.add_parser("validate", help="校验 plan 引用")
    validate_p.add_argument("plan_id", nargs="?", default=None)

    # preview
    preview_p = sub.add_parser("preview", help="输出最终执行范围")
    preview_p.add_argument("plan_id")

    # create
    create_p = sub.add_parser("create", help="创建新 plan")
    create_p.add_argument("plan_id")
    create_p.add_argument("--kind", default="suite", choices=["suite", "scenario_debug", "step_debug"])
    create_p.add_argument("--default-execute", default="否", dest="default_execute", choices=["是", "否"])
    create_p.add_argument("--title", default="")
    create_p.add_argument("--from-tag", default=None, dest="from_tag")
    create_p.add_argument("--from-group", default=None, dest="from_group")
    create_p.add_argument("--force", action="store_true")

    # add-case
    ac_p = sub.add_parser("add-case", help="添加 case 到 plan")
    ac_p.add_argument("plan_id")
    ac_p.add_argument("case_id")

    # add-scenario
    as_p = sub.add_parser("add-scenario", help="添加 scenario 到 plan")
    as_p.add_argument("plan_id")
    as_p.add_argument("case_id")
    as_p.add_argument("scenario_id")

    # disable-case
    dc_p = sub.add_parser("disable-case", help="设置 case execute=否")
    dc_p.add_argument("plan_id")
    dc_p.add_argument("case_id")

    # disable-scenario
    ds_p = sub.add_parser("disable-scenario", help="设置 scenario execute=否")
    ds_p.add_argument("plan_id")
    ds_p.add_argument("case_id")
    ds_p.add_argument("scenario_id")

    # enable-case
    ec_p = sub.add_parser("enable-case", help="设置 case execute=是")
    ec_p.add_argument("plan_id")
    ec_p.add_argument("case_id")

    # enable-scenario
    es_p = sub.add_parser("enable-scenario", help="设置 scenario execute=是")
    es_p.add_argument("plan_id")
    es_p.add_argument("case_id")
    es_p.add_argument("scenario_id")

    # debug-scenario
    dbgs_p = sub.add_parser("debug-scenario", help="创建 scenario_debug plan")
    dbgs_p.add_argument("plan_id")
    dbgs_p.add_argument("--case", required=True, dest="case_id")
    dbgs_p.add_argument("--scenario", required=True, dest="scenario_id")
    dbgs_p.add_argument("--prepare", default="auto", choices=["auto", "case", "none"])
    dbgs_p.add_argument("--cleanup", default="否", choices=["是", "否"])

    # debug-step
    dbgst_p = sub.add_parser("debug-step", help="创建 step_debug plan")
    dbgst_p.add_argument("plan_id")
    dbgst_p.add_argument("--case", required=True, dest="case_id")
    dbgst_p.add_argument("--scenario", required=True, dest="scenario_id")
    dbgst_p.add_argument("--step", required=True, type=int, dest="step_no")
    dbgst_p.add_argument("--step-mode", default="all", choices=["all", "from", "only"], dest="step_mode")
    dbgst_p.add_argument("--prepare", default="auto", choices=["auto", "case", "none"])
    dbgst_p.add_argument("--cleanup", default="否", choices=["是", "否"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _project_root() -> Path:
    """Resolve project root (cwd)."""
    return Path.cwd()


def _plan_dir() -> Path:
    return _project_root() / "plan"


def _plan_path(plan_id: str) -> Path:
    return _plan_dir() / f"{plan_id}.xml"


def _case_dir() -> Path:
    return _project_root() / "case"


def _indent(elem: ET.Element, level: int = 0) -> None:
    """Add pretty-print indentation to an ElementTree."""
    indent_str = "\n" + "  " * level
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = indent_str + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = indent_str
        for i, child in enumerate(elem):
            _indent(child, level + 1)
            if i < len(elem) - 1:
                if not child.tail or not child.tail.strip():
                    child.tail = indent_str + "  "
        if not child.tail or not child.tail.strip():
            child.tail = indent_str
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = indent_str


def _write_plan_xml(path: Path, root: ET.Element) -> None:
    """Write plan XML with declaration and indentation."""
    _indent(root)
    tree = ET.ElementTree(root)
    with open(path, "wb") as f:
        tree.write(f, encoding="UTF-8", xml_declaration=True)
    # Ensure trailing newline
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n")


def _build_plan_root(
    plan_id: str,
    kind: str = "suite",
    default_execute: str = "否",
    title: str = "",
) -> ET.Element:
    attrs = {"id": plan_id, "kind": kind, "default_execute": default_execute}
    if title:
        attrs["title"] = title
    return ET.Element("test_plan", attrs)


def _load_plan_tree(plan_id: str):
    """Load and return (tree, root, path). Raises SystemExit on missing."""
    path = _plan_path(plan_id)
    if not path.is_file():
        print(f"错误: plan 文件不存在: {path}", file=sys.stderr)
        sys.exit(1)
    tree = ET.parse(path)
    return tree, tree.getroot(), path


def _find_or_create_case_node(root: ET.Element, case_id: str) -> ET.Element:
    for case_node in root.findall("case"):
        if case_node.get("id") == case_id:
            return case_node
    case_node = ET.SubElement(root, "case", {"id": case_id, "execute": "是"})
    return case_node


def _collect_existing_case_ids() -> set:
    """Parse case/*.xml and return set of case_id."""
    case_d = _case_dir()
    ids = set()
    if not case_d.is_dir():
        return ids
    for xml_file in case_d.glob("*.xml"):
        try:
            tree = ET.parse(xml_file)
            for case_node in tree.getroot().findall("case"):
                cid = (case_node.get("id") or "").strip()
                if cid:
                    ids.add(cid)
        except ET.ParseError:
            pass
    return ids


def _collect_existing_scenario_ids() -> Dict[str, set]:
    """Parse case/*.xml and return {case_id: {scenario_id, ...}}."""
    case_d = _case_dir()
    result: Dict[str, set] = {}
    if not case_d.is_dir():
        return result
    for xml_file in case_d.glob("*.xml"):
        try:
            tree = ET.parse(xml_file)
            for case_node in tree.getroot().findall("case"):
                cid = (case_node.get("id") or "").strip()
                if not cid:
                    continue
                scenarios = set()
                tc_node = case_node.find("test_case")
                if tc_node is not None:
                    for sc in tc_node.findall("scenario"):
                        sid = (sc.get("id") or "").strip()
                        if sid:
                            scenarios.add(sid)
                if scenarios:
                    result.setdefault(cid, set()).update(scenarios)
        except ET.ParseError:
            pass
    return result


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

def handle(args):
    action = getattr(args, "plan_action", None)
    if not action:
        print("用法: rodski plan <子命令>  (使用 --help 查看可用子命令)", file=sys.stderr)
        return 1

    dispatch = {
        "init": _handle_init,
        "list": _handle_list,
        "show": _handle_show,
        "validate": _handle_validate,
        "preview": _handle_preview,
        "create": _handle_create,
        "add-case": _handle_add_case,
        "add-scenario": _handle_add_scenario,
        "disable-case": _handle_disable_case,
        "disable-scenario": _handle_disable_scenario,
        "enable-case": _handle_enable_case,
        "enable-scenario": _handle_enable_scenario,
        "debug-scenario": _handle_debug_scenario,
        "debug-step": _handle_debug_step,
    }
    handler = dispatch.get(action)
    if handler is None:
        print(f"未知 plan 子命令: {action}", file=sys.stderr)
        return 1
    return handler(args)


def _handle_init(args):
    plan_d = _plan_dir()
    plan_d.mkdir(parents=True, exist_ok=True)
    path = plan_d / "project_full.xml"
    if path.exists() and not args.force:
        print(f"已存在: {path} (使用 --force 覆盖)")
        return 0
    root = _build_plan_root("project_full", kind=args.kind, default_execute=args.default_execute)
    _write_plan_xml(path, root)
    print(f"创建: {path}")
    return 0


def _handle_list(args):
    plan_d = _plan_dir()
    if not plan_d.is_dir():
        print("plan/ 目录不存在")
        return 0
    files = sorted(plan_d.glob("*.xml"))
    if not files:
        print("无 plan 文件")
        return 0
    for f in files:
        print(f.stem)
    return 0


def _handle_show(args):
    path = _plan_path(args.plan_id)
    if not path.is_file():
        print(f"错误: plan 文件不存在: {path}", file=sys.stderr)
        return 1
    print(path.read_text(encoding="utf-8"))
    return 0


def _handle_validate(args):
    plan_d = _plan_dir()
    if not plan_d.is_dir():
        print("plan/ 目录不存在", file=sys.stderr)
        return 1

    if args.plan_id:
        targets = [_plan_path(args.plan_id)]
        if not targets[0].is_file():
            print(f"错误: plan 文件不存在: {targets[0]}", file=sys.stderr)
            return 1
    else:
        targets = sorted(plan_d.glob("*.xml"))

    if not targets:
        print("无 plan 文件")
        return 0

    case_ids = _collect_existing_case_ids()
    scenario_map = _collect_existing_scenario_ids()
    errors: List[str] = []

    for plan_file in targets:
        try:
            tree = ET.parse(plan_file)
        except ET.ParseError as e:
            errors.append(f"{plan_file.name}: XML 解析错误 - {e}")
            continue
        root = tree.getroot()
        plan_id_attr = (root.get("id") or "").strip()
        if plan_id_attr != plan_file.stem:
            errors.append(f"{plan_file.name}: id={plan_id_attr!r} 与文件名 {plan_file.stem!r} 不一致")
        for case_node in root.findall("case"):
            cid = (case_node.get("id") or "").strip()
            if cid and cid not in case_ids:
                errors.append(f"{plan_file.name}: case '{cid}' 不存在")
            for sc_node in case_node.findall("scenario"):
                sid = (sc_node.get("id") or "").strip()
                if sid and cid in scenario_map and sid not in scenario_map.get(cid, set()):
                    errors.append(f"{plan_file.name}: scenario '{sid}' (case '{cid}') 不存在")

    if errors:
        print("校验失败:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"校验通过: {len(targets)} 个 plan 文件")
    return 0


def _handle_preview(args):
    try:
        from ..core.plan_parser import PlanParser
        from ..core.case_parser import CaseParser
        from ..core.test_plan_selection import TestPlanSelection
    except ImportError:
        from core.plan_parser import PlanParser
        from core.case_parser import CaseParser
        from core.test_plan_selection import TestPlanSelection

    path = _plan_path(args.plan_id)
    if not path.is_file():
        print(f"错误: plan 文件不存在: {path}", file=sys.stderr)
        return 1

    plan = PlanParser(str(path)).parse_plan()
    case_d = _case_dir()
    if not case_d.is_dir():
        print("case/ 目录不存在", file=sys.stderr)
        return 1
    cases = CaseParser(str(case_d)).parse_cases()
    selection = TestPlanSelection(cases, plan)
    result = selection.select()

    selected = result.get("selected", [])
    skipped = result.get("skipped", [])
    stale = result.get("stale_references", [])

    print(f"Plan: {args.plan_id} (kind={plan['kind']})")
    print(f"执行: {len(selected)} 项  跳过: {len(skipped)} 项  失效引用: {len(stale)} 项")
    if selected:
        print("\n将执行:")
        for item in selected:
            if item["type"] == "scenario":
                print(f"  {item['case_id']} / {item['scenario_id']}")
            elif item["type"] == "step":
                print(f"  {item['case_id']} / {item['scenario_id']} step {item['step_no']}")
            else:
                print(f"  {item['case_id']}")
    if stale:
        print("\n失效引用:")
        for item in stale:
            print(f"  {item}")
    return 0


def _handle_create(args):
    plan_d = _plan_dir()
    plan_d.mkdir(parents=True, exist_ok=True)
    path = plan_d / f"{args.plan_id}.xml"
    if path.exists() and not args.force:
        print(f"已存在: {path} (使用 --force 覆盖)")
        return 0

    root = _build_plan_root(
        args.plan_id,
        kind=args.kind,
        default_execute=args.default_execute,
        title=args.title,
    )

    # --from-tag / --from-group: populate cases from selector
    if args.from_tag or args.from_group:
        try:
            from ..core.case_parser import CaseParser
            from ..core.test_plan_selection import compile_from_selector
        except ImportError:
            from core.case_parser import CaseParser
            from core.test_plan_selection import compile_from_selector

        case_d = _case_dir()
        if not case_d.is_dir():
            print("case/ 目录不存在", file=sys.stderr)
            return 1
        cases = CaseParser(str(case_d)).parse_cases()
        metadata = CaseParser.collect_scenario_metadata_from_cases(cases)
        filter_tags = [t.strip() for t in args.from_tag.split(",")] if args.from_tag else None
        result = compile_from_selector(
            metadata,
            filter_tags=filter_tags,
            filter_group=args.from_group,
        )
        # Group selected by case_id
        case_scenarios: Dict[str, List[str]] = {}
        for item in result.get("selected", []):
            cid = item["case_id"]
            sid = item.get("scenario_id", "")
            case_scenarios.setdefault(cid, []).append(sid)
        for cid, sids in case_scenarios.items():
            case_node = ET.SubElement(root, "case", {"id": cid, "execute": "是"})
            for sid in sids:
                ET.SubElement(case_node, "scenario", {"id": sid, "execute": "是"})

    _write_plan_xml(path, root)
    print(f"创建: {path}")
    return 0


def _handle_add_case(args):
    tree, root, path = _load_plan_tree(args.plan_id)
    # Check duplicate
    for case_node in root.findall("case"):
        if case_node.get("id") == args.case_id:
            print(f"case '{args.case_id}' 已存在于 plan")
            return 0
    ET.SubElement(root, "case", {"id": args.case_id, "execute": "是"})
    _write_plan_xml(path, root)
    print(f"添加 case '{args.case_id}' 到 {args.plan_id}")
    return 0


def _handle_add_scenario(args):
    tree, root, path = _load_plan_tree(args.plan_id)
    case_node = _find_or_create_case_node(root, args.case_id)
    # Check duplicate
    for sc_node in case_node.findall("scenario"):
        if sc_node.get("id") == args.scenario_id:
            print(f"scenario '{args.scenario_id}' 已存在于 case '{args.case_id}'")
            return 0
    ET.SubElement(case_node, "scenario", {"id": args.scenario_id, "execute": "是"})
    _write_plan_xml(path, root)
    print(f"添加 scenario '{args.scenario_id}' 到 {args.plan_id}/{args.case_id}")
    return 0


def _handle_disable_case(args):
    tree, root, path = _load_plan_tree(args.plan_id)
    for case_node in root.findall("case"):
        if case_node.get("id") == args.case_id:
            case_node.set("execute", "否")
            _write_plan_xml(path, root)
            print(f"已禁用 case '{args.case_id}'")
            return 0
    print(f"错误: case '{args.case_id}' 不在 plan 中", file=sys.stderr)
    return 1


def _handle_disable_scenario(args):
    tree, root, path = _load_plan_tree(args.plan_id)
    for case_node in root.findall("case"):
        if case_node.get("id") == args.case_id:
            for sc_node in case_node.findall("scenario"):
                if sc_node.get("id") == args.scenario_id:
                    sc_node.set("execute", "否")
                    _write_plan_xml(path, root)
                    print(f"已禁用 scenario '{args.scenario_id}'")
                    return 0
            print(f"错误: scenario '{args.scenario_id}' 不在 case '{args.case_id}' 中", file=sys.stderr)
            return 1
    print(f"错误: case '{args.case_id}' 不在 plan 中", file=sys.stderr)
    return 1


def _handle_enable_case(args):
    tree, root, path = _load_plan_tree(args.plan_id)
    for case_node in root.findall("case"):
        if case_node.get("id") == args.case_id:
            case_node.set("execute", "是")
            _write_plan_xml(path, root)
            print(f"已启用 case '{args.case_id}'")
            return 0
    print(f"错误: case '{args.case_id}' 不在 plan 中", file=sys.stderr)
    return 1


def _handle_enable_scenario(args):
    tree, root, path = _load_plan_tree(args.plan_id)
    for case_node in root.findall("case"):
        if case_node.get("id") == args.case_id:
            for sc_node in case_node.findall("scenario"):
                if sc_node.get("id") == args.scenario_id:
                    sc_node.set("execute", "是")
                    _write_plan_xml(path, root)
                    print(f"已启用 scenario '{args.scenario_id}'")
                    return 0
            print(f"错误: scenario '{args.scenario_id}' 不在 case '{args.case_id}' 中", file=sys.stderr)
            return 1
    print(f"错误: case '{args.case_id}' 不在 plan 中", file=sys.stderr)
    return 1


def _handle_debug_scenario(args):
    plan_d = _plan_dir()
    plan_d.mkdir(parents=True, exist_ok=True)
    path = plan_d / f"{args.plan_id}.xml"

    root = _build_plan_root(args.plan_id, kind="scenario_debug", default_execute="否")
    ET.SubElement(root, "debug", {"prepare": args.prepare, "cleanup": args.cleanup})
    case_node = ET.SubElement(root, "case", {"id": args.case_id, "execute": "是"})
    ET.SubElement(case_node, "scenario", {"id": args.scenario_id, "execute": "是"})
    _write_plan_xml(path, root)
    print(f"创建 scenario_debug plan: {path}")
    return 0


def _handle_debug_step(args):
    plan_d = _plan_dir()
    plan_d.mkdir(parents=True, exist_ok=True)
    path = plan_d / f"{args.plan_id}.xml"

    root = _build_plan_root(args.plan_id, kind="step_debug", default_execute="否")
    ET.SubElement(root, "debug", {
        "prepare": args.prepare,
        "step_mode": args.step_mode,
        "cleanup": args.cleanup,
    })
    case_node = ET.SubElement(root, "case", {"id": args.case_id, "execute": "是"})
    sc_node = ET.SubElement(case_node, "scenario", {"id": args.scenario_id, "execute": "是"})
    ET.SubElement(sc_node, "step", {"no": str(args.step_no), "execute": "是"})
    _write_plan_xml(path, root)
    print(f"创建 step_debug plan: {path}")
    return 0
