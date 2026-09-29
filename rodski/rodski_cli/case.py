"""case 子命令 — 用例维护工具（v11.5.0）

提供 lint 子命令，检查用例目录结构与内容的常见问题。
"""
import sys
import re
from pathlib import Path
from typing import List, Dict, Set, Tuple

from rodski.core.case_discovery import discover_case_files, RESERVED_CASE_SUBDIR_NAMES
from rodski.core.exceptions import DuplicateCaseIdInFileError, ReservedCaseSubdirNameError


def setup_parser(subparsers):
    p = subparsers.add_parser("case", help="用例维护工具")
    sub = p.add_subparsers(dest="case_cmd", help="case 子命令")

    # lint
    pl = sub.add_parser("lint", help="检查用例目录结构与内容")
    pl.add_argument("module", help="测试模块目录")


def handle(args):
    cmd = getattr(args, "case_cmd", None)
    if not cmd:
        print("用法: rodski case <lint> ...", file=sys.stderr)
        return 1

    if cmd == "lint":
        return _lint(args.module)

    return 0


def _lint(module: str) -> int:
    """检查用例目录结构与内容的常见问题。

    检查项：
    - ERROR: 同一文件内用例 ID 重复
    - ERROR: 子目录使用保留名
    - WARNING: 目录/文件名不符合 snake_case
    - WARNING: 单文件用例数 > 30
    - INFO: 跨文件同 ID（合法，只提示）
    - v11.6.0 C5 规则见 ``_lint_authoring``

    返回：有 ERROR 时返回 1，否则返回 0
    """
    module_path = Path(module).resolve()
    case_dir = module_path / "case"

    if not case_dir.is_dir():
        print(f"错误: 用例目录不存在: {case_dir}", file=sys.stderr)
        return 1

    errors: List[str] = []
    warnings: List[str] = []
    infos: List[str] = []

    # 递归发现用例文件（会自动检查保留名并抛出 SKI206）
    try:
        case_files = discover_case_files(case_dir)
    except ReservedCaseSubdirNameError as e:
        errors.append(f"[ERROR] {e.message}")
        _print_results(errors, warnings, infos)
        return 1

    if not case_files:
        print("(无用例文件)")

    # 检查文件内 ID 重复、snake_case、单文件用例数
    file_ids: Dict[str, Set[str]] = {}  # {case_file: {id1, id2, ...}}
    cross_file_ids: Dict[str, List[str]] = {}  # {id: [file1, file2, ...]}

    for case_file in case_files:
        rel_path = case_file.relative_to(case_dir).as_posix()
        ids = _extract_case_ids(case_file)
        file_ids[rel_path] = set(ids)

        # 检查文件内重复
        seen = set()
        for case_id in ids:
            if case_id in seen:
                errors.append(f"[ERROR] 文件内 ID 重复: {rel_path} -> {case_id}")
            seen.add(case_id)
            cross_file_ids.setdefault(case_id, []).append(rel_path)

        # 检查单文件用例数
        if len(ids) > 30:
            warnings.append(f"[WARNING] 单文件用例数过多 ({len(ids)}): {rel_path}")

        # 检查文件名 snake_case
        if not _is_snake_case(case_file.stem):
            warnings.append(f"[WARNING] 文件名不符合 snake_case: {rel_path}")

    # 检查目录名 snake_case
    for case_file in case_files:
        for part in case_file.relative_to(case_dir).parts[:-1]:  # 排除文件名本身
            if not _is_snake_case(part):
                warnings.append(f"[WARNING] 目录名不符合 snake_case: {part}")

    # 检查跨文件同 ID（合法，只提示）
    for case_id, files in cross_file_ids.items():
        if len(files) > 1:
            files_str = ", ".join(files)
            infos.append(f"[INFO] 跨文件同 ID（合法）: {case_id} 出现在 {files_str}")

    # v11.6.0 C5：AI 编写契约规则（evaluate 断言/垫片、固定等待、WaitTime、strict BLANK、sql/query）
    _lint_authoring(module_path, case_dir, case_files, errors, warnings, infos)

    # 输出结果
    _print_results(errors, warnings, infos)

    # 有 ERROR 时非 0 退出
    return 1 if errors else 0


_SPECIAL_EMPTY = {"", "BLANK", "NULL", "NONE"}

# evaluate 脚本中的断言模式 → 推荐的原生断言（spec §5 A1）
_EVAL_ASSERT_PATTERNS = [
    (re.compile(r"querySelectorAll\s*\([^)]*\)\s*\.length"),
    "querySelectorAll(...).length", '_verify 字段填 {"$count": N} / {"$count_gte": 1}'),
    (re.compile(r"querySelector\s*\("),
     "querySelector(...)", '_verify 字段填 {"$exists": true} / {"$visible": true}'),
    (re.compile(r"location\s*\.\s*pathname"),
     "location.pathname", '模型声明 <location type="page">path</location> 元素后 verify'),
    (re.compile(r"location\s*\.\s*href"),
     "location.href", '模型声明 <location type="page">url</location> 元素后 verify'),
    (re.compile(r"document\s*\.\s*title"),
     "document.title", '模型声明 <location type="page">title</location> 元素后 verify'),
]
_EVAL_DIALOG_SHIM = re.compile(r"window\s*\.\s*(confirm|alert|prompt)\s*=(?!=)")
_NUMERIC = re.compile(r"^\s*\d+(\.\d+)?\s*$")


def _is_empty_value(value) -> bool:
    return value is None or str(value).strip().upper() in _SPECIAL_EMPTY


def _parse_float(value) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return 0.0


def _load_model_types(module_path: Path) -> Dict[str, str]:
    """{模型名: ui|interface|database}；model.xml 缺失或解析失败时返回空。"""
    import xml.etree.ElementTree as ET

    model_file = module_path / "model" / "model.xml"
    if not model_file.is_file():
        return {}
    try:
        root = ET.parse(model_file).getroot()
    except Exception:
        return {}
    return {m.get("name", ""): (m.get("type") or "ui") for m in root.iter("model")}


def _load_data_tables(module_path: Path) -> Dict[str, Dict[str, Dict[str, str]]]:
    sqlite_file = module_path / "data" / "data.sqlite"
    if not sqlite_file.is_file():
        return {}
    try:
        from rodski.core.sqlite_data_source import SQLiteDataSource

        ds = SQLiteDataSource(str(sqlite_file))
        try:
            return ds.load_tables()
        finally:
            ds.close()
    except Exception:
        return {}


def _load_default_wait_time(module_path: Path):
    """返回 globalvalue.xml 中 DefaultValue.WaitTime 原始字符串（未配置时 None）。"""
    import xml.etree.ElementTree as ET

    gv = module_path / "data" / "globalvalue.xml"
    if not gv.is_file():
        return None
    try:
        root = ET.parse(gv).getroot()
    except Exception:
        return None
    for group in root.iter("group"):
        if group.get("name") != "DefaultValue":
            continue
        for var in group.iter("var"):
            if var.get("name") == "WaitTime":
                return var.get("value", "")
    return None


def _read_evaluate_script(module_path: Path, data: str):
    """evaluate 的 data：以 file: 开头时读取模块内脚本（越界或不存在返回 None）。"""
    if not data.startswith("file:"):
        return data
    rel = data[len("file:"):].strip()
    try:
        target = (module_path / rel).resolve()
        target.relative_to(module_path)
    except (ValueError, OSError):
        return None
    if not target.is_file():
        return None
    try:
        return target.read_text(encoding="utf-8")
    except OSError:
        return None


def _lint_authoring(module_path: Path, case_dir: Path, case_files: List[Path],
                    errors: List[str], warnings: List[str], infos: List[str]) -> None:
    """v11.6.0 C5：拦截 AI 写用例时的典型踩坑写法（规则与 capabilities.pitfalls 同源）。

    - WARNING: evaluate 脚本中出现断言模式（querySelectorAll(...).length / querySelector /
      location.pathname 等）→ 建议改用 verify 原生断言
    - WARNING: evaluate 中出现 window.confirm/alert/prompt 垫片 → 建议 DialogPolicy / page=dialog
    - WARNING: 用例中出现数字字面量 wait（附估算耗时）
    - WARNING: DefaultValue.WaitTime > 0（附估算耗时）
    - INFO:    strict 模式 verify 的 _verify 行 BLANK 字段占比 > 50% → 建议 match_mode="subset"
    - ERROR:   数据行 sql 为 BLANK/NULL/NONE/空，且没有有效 query
    - ERROR:   用例 XML 解析失败（附 && / < 转义提示）
    """
    import xml.etree.ElementTree as ET

    model_types = _load_model_types(module_path)
    tables = _load_data_tables(module_path)

    total_steps = 0
    wait_total = 0.0
    wait_hits = 0
    blank_checked = set()

    for case_file in case_files:
        rel_path = case_file.relative_to(case_dir).as_posix()
        try:
            root = ET.parse(case_file).getroot()
        except ET.ParseError as e:
            errors.append(
                f"[ERROR] 用例 XML 解析失败: {rel_path} -> {e}。若属性值里写了 && 或 <，"
                f"请写成 &amp;&amp; / &lt;，或把脚本移到模块内 fun/js/*.js 并用 data=\"file:fun/js/xxx.js\" 引用"
            )
            continue

        for case_node in root.iter("case"):
            case_id = case_node.get("id", "").strip() or "?"
            executable = case_node.get("execute", "是").strip() != "否"
            for idx, step in enumerate(case_node.iter("test_step"), start=1):
                if executable:
                    total_steps += 1
                action = (step.get("action") or "").strip()
                data = step.get("data") or ""
                where = f"{rel_path} {case_id} 步骤{idx}"

                if action == "wait" and _NUMERIC.match(data):
                    secs = _parse_float(data)
                    wait_hits += 1
                    wait_total += secs
                    warnings.append(
                        f"[WARNING] 固定等待 wait {data.strip()}: {where}；每次运行固定多耗约 {secs:g}s，"
                        f"异步加载请交给 verify 自动重试（DefaultValue.AutoWait 自动等待）或状态断言"
                    )

                elif action == "evaluate":
                    script = _read_evaluate_script(module_path, data.strip())
                    if not script:
                        continue
                    for pattern, label, advice in _EVAL_ASSERT_PATTERNS:
                        if pattern.search(script):
                            warnings.append(
                                f"[WARNING] evaluate 断言模式 {label}: {where}；选择器失效时可能静默通过，"
                                f"建议改用原生断言：{advice}"
                            )
                    m = _EVAL_DIALOG_SHIM.search(script)
                    if m:
                        warnings.append(
                            f"[WARNING] evaluate 弹窗垫片 window.{m.group(1)} = ...: {where}；"
                            f"建议改用 DefaultValue.DialogPolicy=accept|dismiss|fail，或模型声明 "
                            f"<location type=\"page\">dialog</location> 元素并在 type 数据中填 accept/dismiss/accept:文本"
                        )

                elif action in ("verify", "check"):
                    model = (step.get("model") or "").strip()
                    if not model or (step.get("match_mode") or "strict").strip() == "subset":
                        continue
                    if model_types.get(model, "ui") != "ui":
                        continue
                    table = model if model.endswith("_verify") else f"{model}_verify"
                    key = (table, data.strip())
                    if key in blank_checked:
                        continue
                    blank_checked.add(key)
                    row = tables.get(table, {}).get(data.strip())
                    if not row:
                        continue
                    fields = [k for k in row if not k.startswith("__")]
                    blanks = [k for k in fields if str(row[k]).strip().upper() == "BLANK"]
                    if len(fields) >= 2 and len(blanks) * 2 > len(fields):
                        infos.append(
                            f"[INFO] strict verify 的 {table}.{data.strip()} 中 {len(blanks)}/{len(fields)} 个字段为 BLANK: "
                            f"{where}；只校验部分字段时建议在步骤上写 match_mode=\"subset\""
                        )

    if wait_hits > 1:
        warnings.append(f"[WARNING] 共 {wait_hits} 处数字字面量 wait，合计固定等待约 {wait_total:g}s")

    # DefaultValue.WaitTime > 0
    raw_wait = _load_default_wait_time(module_path)
    if raw_wait is not None and _parse_float(raw_wait) > 0:
        value = _parse_float(raw_wait)
        # v11.6.0 起单位为毫秒；≤30 的旧值暂按秒兼容（D3）
        per_step = value if value <= 30 else value / 1000.0
        unit_note = ("按旧写法以秒兼容（v11.6.0 起单位为毫秒，请改写为毫秒或 0）"
                     if value <= 30 else "单位毫秒")
        warnings.append(
            f"[WARNING] globalvalue.xml DefaultValue.WaitTime={raw_wait.strip()} > 0，{unit_note}；"
            f"每步固定等待约 {per_step:g}s，可执行用例共 {total_steps} 步，估算额外耗时 {per_step * total_steps:g}s。"
            f"新模块请设 0，交互等待交给智能等待与 verify 自动重试"
        )

    # 数据行 sql 为空且没有有效 query
    for table_name in sorted(tables):
        if table_name.endswith("_verify"):
            continue
        mtype = model_types.get(table_name)
        if mtype is not None and mtype != "database":
            continue
        for data_id in sorted(tables[table_name]):
            row = tables[table_name][data_id]
            if "sql" not in row:
                continue
            if _is_empty_value(row.get("sql")) and _is_empty_value(row.get("query")):
                errors.append(
                    f"[ERROR] 数据行 {table_name}.{data_id} 既没有有效的 sql 也没有 query"
                    f"（BLANK/NULL/NONE/空 视为未提供）；请填写 sql，或在 query 中填模型里 <query name> 的名称"
                )


def _extract_case_ids(xml_path: Path) -> List[str]:
    """从用例 XML 文件中提取所有 case@id（包括 execute="否" 的用例）。"""
    import xml.etree.ElementTree as ET

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        ids = []
        for case_node in root.findall('case'):
            case_id = case_node.get('id', '').strip()
            if case_id:
                ids.append(case_id)
        return ids
    except Exception as e:
        # XML 解析错误时返回空列表（XSD 校验会在运行时报错）
        return []


def _is_snake_case(name: str) -> bool:
    """检查名称是否符合 snake_case：小写 ASCII + 下划线，正则 ^[a-z][a-z0-9_]*$"""
    return bool(re.match(r'^[a-z][a-z0-9_]*$', name))


def _print_results(errors: List[str], warnings: List[str], infos: List[str]) -> None:
    """打印检查结果，按级别输出。"""
    for err in errors:
        print(err, file=sys.stderr)
    for warn in warnings:
        print(warn)
    for info in infos:
        print(info)

    total = len(errors) + len(warnings) + len(infos)
    if total == 0:
        print("[OK] 未发现问题")
    else:
        summary = []
        if errors:
            summary.append(f"{len(errors)} ERROR")
        if warnings:
            summary.append(f"{len(warnings)} WARNING")
        if infos:
            summary.append(f"{len(infos)} INFO")
        print(f"\n共发现 {', '.join(summary)}")
