"""data 子命令 — 查询和校验测试数据表"""
import sys
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
    pv.add_argument("--strict", action="store_true", help="启用 XML 列漂移检查")


def _load(module: str):
    from core.data_table_parser import DataTableParser
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
        print("用法: rodski data <list|schema|show|query|validate> ...", file=sys.stderr)
        return 1

    if cmd == "list":
        dm = _load(args.module)
        names = sorted(dm.tables.keys())
        if not names:
            print("(无数据表)")
        else:
            for n in names:
                row_count = len(dm.tables[n])
                print(f"  {n}  ({row_count} 行)")

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
        from core.data_schema_validator import DataSchemaValidator
        from core.exceptions import DataParseError
        try:
            dm = _load(args.module)
        except DataParseError as e:
            print(f"[FAIL] {e}", file=sys.stderr)
            return 1

        if args.strict:
            warnings = DataSchemaValidator.check_xml_column_drift(dm.tables)
            for w in warnings:
                print(f"[WARN] {w}")

        print(f"[OK] {len(dm.tables)} 张逻辑表校验通过")

    return 0
