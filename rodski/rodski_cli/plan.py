"""plan 子命令 — 管理 RodSki 测试计划 (plan/*.xml)"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


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
    ac_p.add_argument("case_file", help="用例文件路径(相对case/目录)")
    ac_p.add_argument("case_id")

    # add-dir
    ad_p = sub.add_parser("add-dir", help="添加目录到 plan")
    ad_p.add_argument("plan_id")
    ad_p.add_argument("path", help="目录路径(相对case/目录,空字符串表示整个case/)")

    # migrate
    mg_p = sub.add_parser("migrate", help="为缺少file的plan case自动补充file属性")
    mg_p.add_argument("module", help="模块目录路径")

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
    """Parse case/ 下所有嵌套 XML，返回 case_id 集合。"""
    case_d = _case_dir()
    ids = set()
    if not case_d.is_dir():
        return ids
    try:
        from ..core.case_discovery import discover_case_files
    except ImportError:
        from rodski.core.case_discovery import discover_case_files
    for xml_file in discover_case_files(case_d):
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
    """Parse case/ 下所有嵌套 XML，返回 {case_id: {scenario_id, ...}}。"""
    case_d = _case_dir()
    result: Dict[str, set] = {}
    if not case_d.is_dir():
        return result
    try:
        from ..core.case_discovery import discover_case_files
    except ImportError:
        from rodski.core.case_discovery import discover_case_files
    for xml_file in discover_case_files(case_d):
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
        "add-dir": _handle_add_dir,
        "migrate": _handle_migrate,
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
        try:
            tree = ET.parse(f)
            root = tree.getroot()
            kind = root.get("kind", "")
            title = root.get("title", "")
            case_count = len(root.findall("case"))
            case_dir_count = len(root.findall("case_dir"))
            info = f"{f.stem} [{kind}]"
            if title:
                info += f" {title}"
            info += f" ({case_count} cases"
            if case_dir_count > 0:
                info += f", {case_dir_count} dirs"
            info += ")"
            print(info)
        except ET.ParseError:
            print(f"{f.stem} (解析错误)")
    return 0


def _handle_show(args):
    path = _plan_path(args.plan_id)
    if not path.is_file():
        print(f"错误: plan 文件不存在: {path}", file=sys.stderr)
        return 1
    print(path.read_text(encoding="utf-8"))
    return 0


def _handle_validate(args):
    plan_id = args.plan_id
    if plan_id:
        paths = [_plan_path(plan_id)]
    else:
        plan_d = _plan_dir()
        if not plan_d.is_dir():
            print("plan/ 目录不存在")
            return 0
        paths = sorted(plan_d.glob("*.xml"))

    if not paths:
        print("无 plan 文件")
        return 0

    try:
        from ..core.case_discovery import discover_case_files
    except ImportError:
        from rodski.core.case_discovery import discover_case_files

    all_stale = []
    for path in paths:
        if not path.is_file():
            print(f"跳过: {path}")
            continue

        tree, root, _ = _load_plan_tree(path.stem)
        plan_id = root.get("id", "")

        # Build case_file -> [case_id, ...] and case_id -> [case_file, ...] indices
        case_d = _case_dir()
        if not case_d.is_dir():
            print(f"{plan_id}: case/ 目录不存在")
            continue

        case_file_to_ids: Dict[str, set] = {}
        case_id_to_files: Dict[str, set] = {}
        scenario_index: Dict[Tuple[str, str], set] = {}
        case_files = discover_case_files(case_d)
        # Owner decision C2: file may be omitted only when the module has exactly one case file
        multi_file_module = len(case_files) > 1
        for xml_file in case_files:
            try:
                from ..core.case_discovery import relative_case_file, resolve_module_dir
            except ImportError:
                from rodski.core.case_discovery import relative_case_file, resolve_module_dir

            module_dir = resolve_module_dir(xml_file)
            case_file = relative_case_file(module_dir, xml_file)

            tree_c = ET.parse(xml_file)
            for case_node in tree_c.getroot().findall("case"):
                cid = (case_node.get("id") or "").strip()
                if cid:
                    case_file_to_ids.setdefault(case_file, set()).add(cid)
                    case_id_to_files.setdefault(cid, set()).add(case_file)
                    scenarios: set = set()
                    tc_node = case_node.find("test_case")
                    if tc_node is not None:
                        for sc in tc_node.findall("scenario"):
                            sid = (sc.get("id") or "").strip()
                            if sid:
                                scenarios.add(sid)
                    scenario_index[(case_file, cid)] = scenarios

        stale = []
        for case_node in root.findall("case"):
            case_id = (case_node.get("id") or "").strip()
            file_attr = case_node.get("file")

            resolved_file = None
            if file_attr:
                # Explicit file specified
                file_attr = file_attr.strip()
                if file_attr not in case_file_to_ids:
                    stale.append(f"  case id={case_id} file={file_attr}: 文件不存在")
                elif case_id not in case_file_to_ids.get(file_attr, set()):
                    stale.append(f"  case id={case_id} file={file_attr}: 文件内无此ID")
                else:
                    resolved_file = file_attr
            else:
                # No file: check existence and the single-case-file rule
                candidate_files = case_id_to_files.get(case_id, set())
                if not candidate_files:
                    stale.append(f"  case id={case_id}: ID不存在")
                elif multi_file_module:
                    candidates_str = ", ".join(sorted(candidate_files))
                    stale.append(f"  case id={case_id}: 多用例文件模块需补充file属性 [SKI207] (候选: {candidates_str})")
                else:
                    resolved_file = next(iter(candidate_files))

            if resolved_file is not None:
                known_scenarios = scenario_index.get((resolved_file, case_id), set())
                for scenario_node in case_node.findall("scenario"):
                    sid = (scenario_node.get("id") or "").strip()
                    if sid and sid not in known_scenarios:
                        stale.append(
                            f"  case id={case_id} file={resolved_file}: scenario '{sid}' 不存在"
                        )

        for case_dir_node in root.findall("case_dir"):
            dir_path = (case_dir_node.get("path") or "").strip()
            if dir_path == "":
                target_dir = case_d
            else:
                target_dir = case_d / dir_path
            if not target_dir.is_dir():
                stale.append(f"  case_dir path={dir_path}: 目录不存在")

        if stale:
            print(f"{plan_id}: {len(stale)} 个stale引用")
            for s in stale:
                print(s)
            all_stale.extend(stale)
        else:
            print(f"{plan_id}: OK")

    if all_stale:
        print(f"校验失败: {len(all_stale)} 个问题")
        return 1
    print(f"校验通过: {len(paths)} 个 plan 文件")
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
    selection = TestPlanSelection(cases, plan, module_dir=case_d.parent)
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
    case_file = args.case_file.strip()
    case_id = args.case_id.strip()

    # Check if already exists (by case_uid)
    for case_node in root.findall("case"):
        existing_id = (case_node.get("id") or "").strip()
        existing_file = (case_node.get("file") or "").strip()
        if existing_id == case_id and existing_file == case_file:
            print(f"已存在: case file={case_file} id={case_id}")
            return 0

    case_node = ET.SubElement(root, "case", {"id": case_id, "file": case_file, "execute": "是"})
    _write_plan_xml(path, root)
    print(f"添加: case file={case_file} id={case_id}")
    return 0


def _handle_add_dir(args):
    tree, root, path = _load_plan_tree(args.plan_id)
    dir_path = args.path.strip()

    # Check if already exists
    for case_dir_node in root.findall("case_dir"):
        existing_path = (case_dir_node.get("path") or "").strip()
        if existing_path == dir_path:
            print(f"已存在: case_dir path={dir_path}")
            return 0

    case_dir_node = ET.SubElement(root, "case_dir", {"path": dir_path, "execute": "是"})
    _write_plan_xml(path, root)
    print(f"添加: case_dir path={dir_path}")
    return 0


def _handle_migrate(args):
    """为缺少file的plan case自动补充file属性。"""
    from pathlib import Path
    module_dir = Path(args.module).resolve()
    case_d = module_dir / "case"
    plan_d = module_dir / "plan"

    if not case_d.is_dir():
        print(f"错误: case/ 目录不存在: {case_d}", file=sys.stderr)
        return 1
    if not plan_d.is_dir():
        print(f"错误: plan/ 目录不存在: {plan_d}", file=sys.stderr)
        return 1

    try:
        from ..core.case_discovery import discover_case_files, relative_case_file, resolve_module_dir
    except ImportError:
        from rodski.core.case_discovery import discover_case_files, relative_case_file, resolve_module_dir

    # Build case_id -> [case_file, ...] index
    case_id_to_files: Dict[str, List[str]] = {}
    for xml_file in discover_case_files(case_d):
        mod_dir = resolve_module_dir(xml_file)
        case_file = relative_case_file(mod_dir, xml_file)

        tree_c = ET.parse(xml_file)
        for case_node in tree_c.getroot().findall("case"):
            cid = (case_node.get("id") or "").strip()
            if cid:
                case_id_to_files.setdefault(cid, []).append(case_file)

    # Check if single-file module (can skip migration)
    all_files = set()
    for files in case_id_to_files.values():
        all_files.update(files)
    if len(all_files) <= 1:
        print(f"单文件模块，无需迁移: {module_dir}")
        return 0

    # Process each plan
    plan_files = sorted(plan_d.glob("*.xml"))
    modified_count = 0
    ambiguous_count = 0

    for plan_path in plan_files:
        tree = ET.parse(plan_path)
        root = tree.getroot()
        modified = False

        for case_node in root.findall("case"):
            case_id = (case_node.get("id") or "").strip()
            file_attr = case_node.get("file")

            if file_attr:
                # Already has file attribute
                continue

            candidate_files = case_id_to_files.get(case_id, [])
            if len(candidate_files) == 0:
                print(f"  {plan_path.stem}: case id={case_id} 不存在，跳过")
            elif len(candidate_files) == 1:
                # Unique: auto-fill
                case_node.set("file", candidate_files[0])
                print(f"  {plan_path.stem}: case id={case_id} 补充 file={candidate_files[0]}")
                modified = True
            else:
                # Ambiguous: list candidates
                candidates_str = ", ".join(candidate_files)
                print(f"  {plan_path.stem}: case id={case_id} 有歧义，候选: {candidates_str}")
                ambiguous_count += 1

        if modified:
            _write_plan_xml(plan_path, root)
            modified_count += 1

    print(f"\n迁移完成: {modified_count} 个plan已更新")
    if ambiguous_count > 0:
        print(f"警告: {ambiguous_count} 个歧义引用需要手动处理")
        return 1
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
