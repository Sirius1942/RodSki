"""case/ 目录多级嵌套发现 —— 唯一入口（v11.5.0）

设计文档: .pb/specs/v11.5.0-nested-case-directory-design.md §4
所有需要枚举 case XML 文件、或从 case 路径推导测试模块目录的代码都应调用本
模块的函数，禁止在别处直接写 ``glob("*.xml")`` / ``parent.parent`` 等等价逻辑
——那样在多级嵌套下会得到错误或不一致的结果。

提供三个函数：

- :func:`discover_case_files`：递归发现一个目录下的所有用例 XML，
  按相对路径逐段排序，忽略 ``.`` 前缀条目，不跟随目录符号链接，
  子目录不得使用保留名（否则报 SKI206）。
- :func:`resolve_module_dir`：从 case 文件/目录路径向上查找最近的 ``case``
  祖先目录，返回其父目录（= 测试模块目录）；若路径不在任何 ``case`` 祖先
  之下，则视为已经是模块目录，原样返回。
- :func:`relative_case_file`：把一个 case 文件路径转换为相对模块
  ``case/`` 目录的 POSIX 路径（用作 ``case_file`` / ``case_uid`` 的组成部分）。
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from .exceptions import ReservedCaseSubdirNameError

# case/ 下的子目录不得使用的名称——这些是测试模块层级下的固定文件夹名
# （CORE §6.4），冲突会让"向上查找最近的 case 祖先"无法唯一确定模块目录。
RESERVED_CASE_SUBDIR_NAMES = frozenset({
    "case", "model", "fun", "data", "plan", "result", "business", "perf", "knowledge",
})

__all__ = [
    "RESERVED_CASE_SUBDIR_NAMES",
    "discover_case_files",
    "resolve_module_dir",
    "relative_case_file",
]


def discover_case_files(root: Path) -> List[Path]:
    """递归返回 ``root`` 下所有用例 XML 文件，按相对路径逐段排序。

    规则（详见设计文档 §4.1）：

    - 递归任意层级，不限制深度；
    - 忽略以 ``.`` 开头的目录或文件（``.git``、``.DS_Store``、草稿目录等）；
    - 忽略非 ``.xml`` 文件（README.md 等）；
    - ``root`` 下（任意深度）的子目录不得使用保留名，否则抛出
      :class:`ReservedCaseSubdirNameError` (SKI206)；
    - 不跟随目录符号链接（防止循环引用、防止跨模块引用）；
    - 排序按相对 ``root`` 的 POSIX 路径**逐段**比较（而非整串比较），
      保证跨平台结果确定，且与扁平目录下的现状排序一致。

    Args:
        root: 起始扫描目录（可以是模块的 ``case/`` 目录，也可以是其任意子目录）。

    Returns:
        按逐段路径排序后的用例文件路径列表；``root`` 不存在或不是目录时返回空列表。
    """
    root = Path(root)
    if not root.is_dir():
        return []

    entries: List[tuple] = []

    def _walk(directory: Path, is_root: bool) -> None:
        try:
            children = sorted(directory.iterdir(), key=lambda p: p.name)
        except (FileNotFoundError, NotADirectoryError, PermissionError):
            return
        for child in children:
            name = child.name
            if name.startswith('.'):
                continue
            if child.is_dir():
                if child.is_symlink():
                    # 不跟随目录符号链接：既不报错也不递归，直接跳过。
                    continue
                if not is_root and name in RESERVED_CASE_SUBDIR_NAMES:
                    rel = child.relative_to(root).as_posix()
                    raise ReservedCaseSubdirNameError(path=rel, name=name)
                _walk(child, is_root=False)
            elif child.is_file():
                if child.suffix.lower() == '.xml':
                    rel_parts = tuple(child.relative_to(root).as_posix().split('/'))
                    entries.append((rel_parts, child))

    _walk(root, is_root=True)
    entries.sort(key=lambda item: item[0])
    return [path for _, path in entries]


def resolve_module_dir(path: Path) -> Path:
    """从 case 文件/目录路径推导测试模块目录。

    向上查找最近的名为 ``case`` 的祖先目录（含路径本身），其父目录即为
    测试模块目录：

    - 传入 case 目录本身（``.../case``）→ 返回其父目录；
    - 传入 case 下任意深度的文件或子目录（``.../case/order/refund/x.xml``）
      → 返回最近的 ``case`` 祖先的父目录；
    - 传入模块目录本身（路径中没有任何 ``case`` 祖先）→ 原样返回。

    这是纯路径名推导，不依赖文件系统是否真实存在——与旧版
    ``ski_executor.resolve_module_dir`` 的浅层实现（只处理一层 ``parent.parent``）
    不同，本函数支持任意嵌套深度。
    """
    p = Path(path)
    if p.name == 'case':
        return p.parent
    for ancestor in p.parents:
        if ancestor.name == 'case':
            return ancestor.parent
    return p


def relative_case_file(module_dir: Path, path: Path) -> str:
    """把 ``path`` 转换为相对模块 ``case/`` 目录的 POSIX 路径。

    用于生成 ``case_file`` / ``case_uid``（``f"{case_file}::{case_id}"``）。

    Args:
        module_dir: 测试模块目录（通常来自 :func:`resolve_module_dir` 的返回值）。
        path: case 文件路径。

    Returns:
        相对 ``{module_dir}/case`` 的 POSIX 路径字符串，如 ``"order/refund/refund_apply.xml"``。

    Raises:
        ValueError: ``path`` 不在 ``{module_dir}/case`` 之下（即便按绝对路径兜底比较后仍不在）。
    """
    module_dir = Path(module_dir)
    path = Path(path)
    case_root = module_dir / 'case'
    try:
        return path.relative_to(case_root).as_posix()
    except ValueError:
        # 调用方可能传入了一边绝对一边相对的路径；用绝对路径再兜底比较一次。
        return path.resolve().relative_to(case_root.resolve()).as_posix()
