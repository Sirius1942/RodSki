"""init 子命令 — 创建 RodSki 测试模块骨架"""
import sys
import sqlite3
from pathlib import Path

from ..core.sqlite_schema import SQLITE_DDL


_MODEL_XML = '<?xml version="1.0" encoding="UTF-8"?>\n<models>\n</models>\n'
_GLOBALVALUE_XML = '<?xml version="1.0" encoding="UTF-8"?>\n<globalvalue>\n</globalvalue>\n'


def setup_parser(subparsers):
    p = subparsers.add_parser("init", help="创建 RodSki 测试模块骨架")
    p.add_argument("target", help="目标目录路径")
    p.add_argument("--no-sqlite", action="store_true", help="不创建 data.sqlite（不推荐）")
    p.add_argument("--force", action="store_true", help="覆盖已有模板文件")


def _write(path: Path, content: str, force: bool) -> bool:
    if path.exists() and not force:
        print(f"  跳过 (已存在): {path}")
        return False
    path.write_text(content, encoding="utf-8")
    print(f"  创建: {path}")
    return True


def handle(args):
    target = Path(args.target).expanduser().resolve()

    dirs = ["case", "model", "fun", "data", "result"]
    for d in dirs:
        (target / d).mkdir(parents=True, exist_ok=True)
        print(f"  目录: {target / d}")

    _write(target / "model" / "model.xml", _MODEL_XML, args.force)
    _write(target / "data" / "globalvalue.xml", _GLOBALVALUE_XML, args.force)

    if not args.no_sqlite:
        db_path = target / "data" / "data.sqlite"
        if db_path.exists() and not args.force:
            print(f"  跳过 (已存在): {db_path}")
        else:
            conn = sqlite3.connect(str(db_path))
            conn.executescript(SQLITE_DDL)
            conn.close()
            print(f"  创建: {db_path}")

    print(f"\n初始化完成: {target}")
    return 0
