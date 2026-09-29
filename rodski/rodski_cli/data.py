"""data 子命令 — 查询和校验测试数据表"""
import sys
import json
from pathlib import Path


def setup_parser(subparsers):
    p = subparsers.add_parser("data", help="查询和校验测试数据表")
    sub = p.add_subparsers(dest="data_cmd", help="data 子命令")

    # list
    pl = sub.add_parser("list", help="列出模块中所有逻辑表")
    pl.add_argument("module", help="测试模块目录")

    # schema
    ps = sub.add_parser("schema", help="查看逻辑表字段列表")
    ps.add_argument("module", help="测试模块目录")
    ps.add_argument("table", help="逻辑表名")

    # show
    psh = sub.add_parser("show", help="查看指定数据行")
    psh.add_argument("module", help="测试模块目录")
    psh.add_argument("table", help="逻辑表名")
    psh.add_argument("data_id", help="DataID")

    # query
    pq = sub.add_parser("query", help="列出逻辑表所有行")
    pq.add_argument("module", help="测试模块目录")
    pq.add_argument("table", help="逻辑表名")
    pq.add_argument("--limit", type=int, default=50, help="最多显示行数（默认 50）")

    # validate
    pv = sub.add_parser("validate", help="校验数据层完整性")
    pv.add_argument("module", help="测试模块目录")
    pv.add_argument("--orphans", action="store_true", help="检查孤儿数据（未被引用的逻辑表与 data_id）")

    # import
    pi = sub.add_parser("import", help="将 data.xml / data_verify.xml 迁移至 data.sqlite")
    pi.add_argument("module", help="测试模块目录")
    pi.add_argument("--overwrite", action="store_true", help="已存在的表覆盖写入（默认跳过）")

    # dump: 只读，stdout，稳定排序
    pd = sub.add_parser("dump", help="输出 sqlite 内容（只读，stdout，稳定排序）")
    pd.add_argument("module", help="测试模块目录或 data.sqlite 文件路径")
    pd.add_argument("--format", choices=["yaml", "json"], default="yaml", help="输出格式（默认 yaml）")

    # add-field: 回填字段
    paf = sub.add_parser("add-field", help="为逻辑表添加字段并回填所有行")
    paf.add_argument("module", help="测试模块目录")
    paf.add_argument("table", help="逻辑表名")
    paf.add_argument("field", help="字段名")
    paf.add_argument("--default", default="BLANK", help="默认值（默认 BLANK）")


def _load(module: str):
    try:
        from rodski.core.data_table_parser import DataTableParser
    except ImportError:
        from rodski.core.data_table_parser import DataTableParser
    data_dir = Path(module) / "data"
    if not data_dir.exists():
        print(f"错误: 数据目录不存在: {data_dir}", file=sys.stderr)
        sys.exit(1)
    dm = DataTableParser(str(data_dir))
    dm.parse_all_tables()
    return dm


def handle(args):
    cmd = getattr(args, "data_cmd", None)
    if not cmd:
        print("用法: rodski data <list|schema|show|query|validate|import|dump|add-field> ...", file=sys.stderr)
        return 1

    if cmd == "list":
        dm = _load(args.module)
        names = sorted(dm.tables.keys())
        if not names:
            print("(无数据表)")
        else:
            for n in names:
                print(f"  {n}  ({len(dm.tables[n])} 行)")

    elif cmd == "schema":
        dm = _load(args.module)
        rows = dm.tables.get(args.table)
        if rows is None:
            print(f"错误: 逻辑表 '{args.table}' 不存在", file=sys.stderr)
            return 1
        fields = sorted({f for row in rows.values() for f in row})
        print(f"[{args.table}]")
        for f in fields:
            print(f"  {f}")

    elif cmd == "show":
        dm = _load(args.module)
        row = dm.get_data(args.table, args.data_id)
        if not row:
            print(f"错误: '{args.table}' 中找不到 DataID='{args.data_id}'", file=sys.stderr)
            return 1
        print(f"[{args.table} / {args.data_id}]")
        for k, v in sorted(row.items()):
            print(f"  {k}: {v}")

    elif cmd == "query":
        dm = _load(args.module)
        rows = dm.tables.get(args.table)
        if rows is None:
            print(f"错误: 逻辑表 '{args.table}' 不存在", file=sys.stderr)
            return 1
        items = list(rows.items())[: args.limit]
        for data_id, row in items:
            fields = "  ".join(f"{k}={v}" for k, v in sorted(row.items()))
            print(f"  {data_id}  {fields}")
        if len(rows) > args.limit:
            print(f"  ... (共 {len(rows)} 行，已截断至 {args.limit})")

    elif cmd == "validate":
        try:
            from rodski.core.exceptions import DataParseError
        except ImportError:
            from rodski.core.exceptions import DataParseError
        try:
            dm = _load(args.module)
        except DataParseError as e:
            print(f"[FAIL] {e}", file=sys.stderr)
            return 1

        if getattr(args, "orphans", False):
            return _validate_orphans(args.module, dm)
        else:
            print(f"[OK] {len(dm.tables)} 张逻辑表校验通过")

    elif cmd == "import":
        try:
            from .data_import import run_import
        except ImportError:
            from rodski_cli.data_import import run_import
        return run_import(args.module, overwrite=args.overwrite)

    elif cmd == "dump":
        return _dump(args.module, args.format)

    elif cmd == "add-field":
        return _add_field(args.module, args.table, args.field, args.default)

    return 0


def _validate_orphans(module: str, dm) -> int:
    """检查孤儿数据：未被引用的逻辑表与 data_id。

    只提示不删除；动态拼接的 data_id 无法静态分析，会在输出中说明。
    """
    from pathlib import Path
    from rodski.core.case_discovery import discover_case_files
    import xml.etree.ElementTree as ET

    module_path = Path(module).resolve()
    case_dir = module_path / "case"
    business_dir = module_path / "business"

    referenced_tables = set()
    referenced_data_ids = {}  # {table: {id1, id2, ...}}

    # 扫描用例
    if case_dir.is_dir():
        for case_file in discover_case_files(case_dir):
            try:
                tree = ET.parse(case_file)
                for step in tree.findall('.//test_step'):
                    data = step.get('data', '').strip()
                    if data and not data.startswith('${') and not data.startswith('GlobalValue'):
                        # 简单启发式：Model.DataID 或 DataID
                        parts = data.split('.')
                        if len(parts) == 2:
                            table, data_id = parts
                            referenced_tables.add(table)
                            referenced_data_ids.setdefault(table, set()).add(data_id)
                        elif len(parts) == 1:
                            # 可能是 data_id，但无法确定属于哪个表
                            pass
            except:
                pass

    # 扫描 business
    if business_dir.is_dir():
        for biz_file in business_dir.glob('*.xml'):
            try:
                tree = ET.parse(biz_file)
                for step in tree.findall('.//step'):
                    data = step.get('data', '').strip()
                    if data and not data.startswith('${') and not data.startswith('GlobalValue'):
                        parts = data.split('.')
                        if len(parts) == 2:
                            table, data_id = parts
                            referenced_tables.add(table)
                            referenced_data_ids.setdefault(table, set()).add(data_id)
            except:
                pass

    # 输出未被引用的逻辑表
    orphan_tables = set(dm.tables.keys()) - referenced_tables
    if orphan_tables:
        print("[未被引用的逻辑表]")
        for table in sorted(orphan_tables):
            print(f"  {table}  ({len(dm.tables[table])} 行)")

    # 输出未被引用的 data_id
    orphan_ids = {}
    for table in referenced_tables:
        if table not in dm.tables:
            continue
        defined_ids = set(dm.tables[table].keys())
        used_ids = referenced_data_ids.get(table, set())
        orphan = defined_ids - used_ids
        if orphan:
            orphan_ids[table] = orphan

    if orphan_ids:
        print("\n[未被引用的 data_id]")
        for table in sorted(orphan_ids.keys()):
            print(f"  {table}:")
            for data_id in sorted(orphan_ids[table]):
                print(f"    {data_id}")

    # 提示
    if not orphan_tables and not orphan_ids:
        print("[OK] 未发现孤儿数据")
    else:
        print(f"\n注意：动态拼接的 data_id 无法静态分析，以上结果仅供参考")

    return 0


def _dump(module_or_file: str, format: str) -> int:
    """输出 sqlite 内容，按"表 → 行 → 字段"稳定排序。

    只读，不落盘。支持被 git textconv 调用（接受 sqlite 文件路径作为参数）。
    """
    from pathlib import Path
    from rodski.core.sqlite_data_source import SQLiteDataSource

    path = Path(module_or_file)
    if path.is_file() and path.suffix == '.sqlite':
        sqlite_file = path
    elif path.is_dir():
        sqlite_file = path / "data" / "data.sqlite"
    else:
        sqlite_file = path / "data.sqlite"

    if not sqlite_file.is_file():
        print(f"错误: SQLite 文件不存在: {sqlite_file}", file=sys.stderr)
        return 1

    try:
        ds = SQLiteDataSource(str(sqlite_file))
        tables = ds.load_tables()
        ds.close()
    except Exception as e:
        print(f"错误: 读取 SQLite 失败: {e}", file=sys.stderr)
        return 1

    # 稳定排序：表名 → data_id → 字段名
    sorted_tables = {}
    for table_name in sorted(tables.keys()):
        sorted_rows = {}
        for data_id in sorted(tables[table_name].keys()):
            sorted_fields = dict(sorted(tables[table_name][data_id].items()))
            sorted_rows[data_id] = sorted_fields
        sorted_tables[table_name] = sorted_rows

    # 输出
    if format == "json":
        print(json.dumps(sorted_tables, ensure_ascii=False, indent=2))
    else:  # yaml
        _print_yaml(sorted_tables)

    return 0


def _print_yaml(data: dict) -> None:
    """简单的 YAML 输出（不依赖 PyYAML）。"""
    for table_name, rows in data.items():
        print(f"{table_name}:")
        for data_id, fields in rows.items():
            print(f"  {data_id}:")
            for field_name, field_value in fields.items():
                print(f"    {field_name}: {field_value}")


def _add_field(module: str, table: str, field: str, default: str) -> int:
    """为逻辑表添加字段并回填所有行。"""
    from pathlib import Path
    import sqlite3

    module_path = Path(module).resolve()
    sqlite_file = module_path / "data" / "data.sqlite"

    if not sqlite_file.is_file():
        print(f"错误: SQLite 文件不存在: {sqlite_file}", file=sys.stderr)
        return 1

    try:
        conn = sqlite3.connect(str(sqlite_file))
        cur = conn.cursor()

        # 检查表是否存在
        cur.execute("SELECT COUNT(*) FROM rs_datatable WHERE table_name = ?", (table,))
        if cur.fetchone()[0] == 0:
            print(f"错误: 逻辑表 '{table}' 不存在", file=sys.stderr)
            conn.close()
            return 1

        # 检查字段是否已存在
        cur.execute("SELECT COUNT(*) FROM rs_datatable_field WHERE table_name = ? AND field_name = ?", (table, field))
        if cur.fetchone()[0] > 0:
            print(f"错误: 字段 '{field}' 已存在于表 '{table}'", file=sys.stderr)
            conn.close()
            return 1

        # 获取当前最大 field_order
        cur.execute("SELECT MAX(field_order) FROM rs_datatable_field WHERE table_name = ?", (table,))
        max_order = cur.fetchone()[0] or 0
        new_order = max_order + 1

        # 添加字段定义
        cur.execute(
            "INSERT INTO rs_datatable_field (table_name, field_name, field_order) VALUES (?, ?, ?)",
            (table, field, new_order)
        )

        # 回填所有行
        cur.execute("SELECT data_id FROM rs_row WHERE table_name = ?", (table,))
        data_ids = [row[0] for row in cur.fetchall()]

        for data_id in data_ids:
            cur.execute(
                "INSERT INTO rs_field (table_name, data_id, field_name, field_value) VALUES (?, ?, ?, ?)",
                (table, data_id, field, default)
            )

        conn.commit()
        conn.close()

        print(f"[OK] 已为表 '{table}' 添加字段 '{field}'（默认值 '{default}'），回填 {len(data_ids)} 行")
        return 0

    except Exception as e:
        print(f"错误: 操作失败: {e}", file=sys.stderr)
        return 1
