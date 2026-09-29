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
        return 0

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

    # 输出结果
    _print_results(errors, warnings, infos)

    # 有 ERROR 时非 0 退出
    return 1 if errors else 0


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
