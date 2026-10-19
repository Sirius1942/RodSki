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

    # v11.6.0 E2：行级编辑（修改期望值无需「改 XML → 重新 import」）
    pst = sub.add_parser("set", help="修改已有数据行的字段值（field=value ...）")
    pst.add_argument("module", help="测试模块目录")
    pst.add_argument("table", help="逻辑表名")
    pst.add_argument("data_id", help="DataID")
    pst.add_argument("assignments", nargs="*", metavar="field=value", help="要修改的字段，可多个")
    pst.add_argument("--remark", default=None, help="修改行备注（v11.9.0；可单独使用）")

    par = sub.add_parser("add-row", help="新增数据行（必须提供表的完整字段集合）")
    par.add_argument("module", help="测试模块目录")
    par.add_argument("table", help="逻辑表名")
    par.add_argument("data_id", help="新行的 DataID")
    par.add_argument("assignments", nargs="*", metavar="field=value", help="全部字段的值")
    par.add_argument("--remark", default="", help="行备注")

    # v11.9.0 计划级数据驱动（CORE §7.8）
    pcd = sub.add_parser("create-driver", help="新建数据驱动表（table_kind=driver，计划 / 用例 / 步骤对应关系表）")
    pcd.add_argument("module", help="测试模块目录")
    pcd.add_argument("table", help="数据驱动表名（不得与模型同名）")
    pcd.add_argument("--case", required=True, dest="case_uid", metavar="CASE_FILE::CASE_ID",
                     help="绑定的用例，如 login/flow.xml::LOGIN_FLOW")
    pcd.add_argument("--remark", required=True, help="表备注（必填）：目的、所属计划")
    pcd.add_argument("--columns", required=True, help="驱动列，逗号分隔，每列为 表名.基础DataID")

    pdr = sub.add_parser("delete-row", help="删除数据行")
    pdr.add_argument("module", help="测试模块目录")
    pdr.add_argument("table", help="逻辑表名")
    pdr.add_argument("data_id", help="DataID")


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
        print("用法: rodski data <list|schema|show|query|validate|import|dump|add-field|set|add-row|delete-row|create-driver> ...", file=sys.stderr)
        return 1

    if cmd == "list":
        dm = _load(args.module)
        names = sorted(dm.tables.keys())
        drivers = _driver_tables_meta(args.module)
        if not names and not drivers:
            print("(无数据表)")
        else:
            for n in names:
                print(f"  {n}  ({len(dm.tables[n])} 行)")
            for n, (case_uid, remark, count) in sorted(drivers.items()):
                print(f"  {n}  ({count} 行)  driver  绑定 {case_uid}  {remark}")

    elif cmd == "schema":
        dm = _load(args.module)
        if args.table in dm.driver_tables:
            meta = _driver_tables_meta(args.module)[args.table]
            print(f"[{args.table}]  driver  绑定 {meta[0]}")
            for column in _driver_columns(args.module, args.table):
                print(f"  {column}")
            return 0
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
        if args.table in dm.driver_tables:
            row = _driver_row(args.module, args.table, args.data_id)
        else:
            row = dm.get_data(args.table, args.data_id)
        if not row:
            print(f"错误: '{args.table}' 中找不到 DataID='{args.data_id}'", file=sys.stderr)
            return 1
        print(f"[{args.table} / {args.data_id}]")
        remark = _row_remark(args.module, args.table, args.data_id)
        if remark:
            print(f"  备注: {remark}")
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

        driver_errors = _validate_driver_tables(args.module)
        if driver_errors:
            for line in driver_errors:
                print(f"[FAIL] {line}", file=sys.stderr)
            return 1
        if getattr(args, "orphans", False):
            return _validate_orphans(args.module, dm)
        drivers = len(_driver_tables_meta(args.module))
        print(f"[OK] {len(dm.tables)} 张逻辑表校验通过" + (f"，{drivers} 张数据驱动表校验通过" if drivers else ""))

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

    elif cmd == "set":
        return _set_row(args.module, args.table, args.data_id, args.assignments, args.remark)

    elif cmd == "create-driver":
        return _create_driver(args.module, args.table, args.case_uid, args.remark, args.columns)

    elif cmd == "add-row":
        return _add_row(args.module, args.table, args.data_id, args.assignments, args.remark)

    elif cmd == "delete-row":
        return _delete_row(args.module, args.table, args.data_id)

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
        try:
            drivers = ds.load_driver_tables()
        except Exception:  # 非 RodSki 结构或缺字段的 sqlite：只输出普通逻辑表
            drivers = {}
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
    # v11.9.0 数据驱动表：键名带 driver: 前缀，与模型数据表区分（git textconv 也能看到驱动表的改动）
    for name in sorted(drivers):
        meta = drivers[name]
        sorted_tables[f"driver:{name}"] = {
            "_meta": {"bound_case": meta["model_name"], "remark": meta["remark"]},
            **{data_id: {"_remark": row["remark"], **dict(sorted(row["cells"].items()))}
               for data_id, row in sorted(meta["rows"].items())},
        }

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

        # v11.9.0：数据驱动表新增的是驱动列（表名.基础DataID），须通过列校验
        err = _check_driver_column(module, cur, table, field, default)
        if err:
            print(f"错误: {err}", file=sys.stderr)
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


# ---------------------------------------------------------------- v11.6.0 E2 行级编辑
_EMPTY_HINT = "不校验/不使用的字段请显式填 BLANK/NULL/NONE（v6.7.6 字段集合一致约束）"


def _parse_assignments(assignments):
    """解析 field=value 列表；返回 (dict, 错误信息或 None)。按第一个 '=' 切分，值里可以再含 '='。"""
    values = {}
    for item in assignments:
        if "=" not in item:
            return None, f"参数 '{item}' 不是 field=value 格式"
        field, value = item.split("=", 1)
        field = field.strip()
        if not field:
            return None, f"参数 '{item}' 缺少字段名"
        if field in values:
            return None, f"字段 '{field}' 重复赋值"
        if value == "":
            return None, f"字段 '{field}' 的值为空；{_EMPTY_HINT}"
        values[field] = value
    return values, None


def _open_module_sqlite(module: str):
    import sqlite3

    sqlite_file = Path(module).resolve() / "data" / "data.sqlite"
    if not sqlite_file.is_file():
        print(f"错误: SQLite 文件不存在: {sqlite_file}", file=sys.stderr)
        return None
    return sqlite3.connect(str(sqlite_file))


def _table_fields(cur, table: str):
    """返回逻辑表字段列表（按 field_order）；表不存在返回 None。"""
    cur.execute("SELECT COUNT(*) FROM rs_datatable WHERE table_name = ?", (table,))
    if cur.fetchone()[0] == 0:
        return None
    cur.execute(
        "SELECT field_name FROM rs_datatable_field WHERE table_name = ? ORDER BY field_order, field_name",
        (table,),
    )
    return [r[0] for r in cur.fetchall()]


def _missing_table_msg(cur, table: str) -> str:
    cur.execute("SELECT table_name FROM rs_datatable ORDER BY table_name")
    names = [r[0] for r in cur.fetchall()]
    return f"错误: 逻辑表 '{table}' 不存在；现有逻辑表: {', '.join(names) or '(无)'}"


def _check_return_self_ref(module: str, table: str, values) -> str:
    """接口/DB 模型的 _verify 表禁止 ${Return[-1]}（v6.7.6）；UI 模型允许。返回错误信息或空串。"""
    if not table.endswith("_verify"):
        return ""
    try:
        from .case import _load_model_types
    except ImportError:
        from rodski_cli.case import _load_model_types
    model = table[: -len("_verify")]
    mtype = _load_model_types(Path(module).resolve()).get(model, "ui")
    if mtype == "ui":
        return ""
    for field, value in values.items():
        if "${Return[-1]" in value:
            return (f"字段 '{field}': 接口/DB 模型的 _verify 期望值不能使用 ${{Return[-1]}}"
                    f"（实际值已自动取自 Return[-1]），请写字面值或 GlobalValue")
    return ""


def _set_row(module: str, table: str, data_id: str, assignments, remark=None) -> int:
    """修改已有行的字段值 / 行备注：先校验（表/行/字段均存在、值非空）再写入。"""
    if not assignments and remark is None:
        print("错误: 至少提供一个 field=value 或 --remark", file=sys.stderr)
        return 1
    values, err = _parse_assignments(assignments)
    if err:
        print(f"错误: {err}", file=sys.stderr)
        return 1
    conn = _open_module_sqlite(module)
    if conn is None:
        return 1
    try:
        cur = conn.cursor()
        fields = _table_fields(cur, table)
        if fields is None:
            print(_missing_table_msg(cur, table), file=sys.stderr)
            return 1
        cur.execute("SELECT COUNT(*) FROM rs_row WHERE table_name = ? AND data_id = ?", (table, data_id))
        if cur.fetchone()[0] == 0:
            print(f"错误: '{table}' 中找不到 DataID='{data_id}'；新增行请用 rodski data add-row", file=sys.stderr)
            return 1
        unknown = [f for f in values if f not in fields]
        if unknown:
            print(f"错误: 表 '{table}' 没有字段 {', '.join(unknown)}；现有字段: {', '.join(fields)}"
                  f"（新增字段请用 rodski data add-field）", file=sys.stderr)
            return 1
        err = _check_return_self_ref(module, table, values) or _check_driver_cells(cur, table, data_id, values)
        if err:
            print(f"错误: {err}", file=sys.stderr)
            return 1

        if remark is not None:
            cur.execute("UPDATE rs_row SET remark = ? WHERE table_name = ? AND data_id = ?", (remark, table, data_id))
        for field, value in values.items():
            cur.execute(
                "UPDATE rs_field SET field_value = ? WHERE table_name = ? AND data_id = ? AND field_name = ?",
                (value, table, data_id, field),
            )
            if cur.rowcount == 0:
                cur.execute(
                    "INSERT INTO rs_field (table_name, data_id, field_name, field_value) VALUES (?, ?, ?, ?)",
                    (table, data_id, field, value),
                )
        cur.execute("UPDATE rs_datatable SET updated_at = CURRENT_TIMESTAMP WHERE table_name = ?", (table,))
        conn.commit()
        changes = ", ".join([f"{k}={v}" for k, v in values.items()] + ([f"备注={remark}"] if remark is not None else []))
        print(f"[OK] 已更新 {table}.{data_id}: {changes}")
        return 0
    except Exception as e:
        conn.rollback()
        print(f"错误: 操作失败: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()


def _add_row(module: str, table: str, data_id: str, assignments, remark: str = "") -> int:
    """新增行：必须提供表的完整字段集合（v6.7.6），不允许未知字段。"""
    values, err = _parse_assignments(assignments)
    if err:
        print(f"错误: {err}", file=sys.stderr)
        return 1
    if not data_id.strip():
        print("错误: DataID 不能为空", file=sys.stderr)
        return 1
    conn = _open_module_sqlite(module)
    if conn is None:
        return 1
    try:
        cur = conn.cursor()
        fields = _table_fields(cur, table)
        if fields is None:
            print(_missing_table_msg(cur, table), file=sys.stderr)
            return 1
        cur.execute("SELECT COUNT(*) FROM rs_row WHERE table_name = ? AND data_id = ?", (table, data_id))
        if cur.fetchone()[0] > 0:
            print(f"错误: '{table}' 中已存在 DataID='{data_id}'；修改请用 rodski data set", file=sys.stderr)
            return 1
        if _table_kind(cur, table) == "driver" and not _dd().is_literal_data_id(data_id):
            print(f"错误: 数据驱动表的实例 DataID {data_id!r} 不合法（不能含空格、逗号、方括号、点等字符），"
                  f"实例 ID 为 用例ID[DataID]，需能被 --data-id 选中", file=sys.stderr)
            return 1
        unknown = [f for f in values if f not in fields]
        if unknown:
            print(f"错误: 表 '{table}' 没有字段 {', '.join(unknown)}；现有字段: {', '.join(fields)}", file=sys.stderr)
            return 1
        missing = [f for f in fields if f not in values]
        if missing:
            print(f"错误: 新增行缺少字段 {', '.join(missing)}；{_EMPTY_HINT}", file=sys.stderr)
            return 1
        err = _check_return_self_ref(module, table, values) or _check_driver_cells(cur, table, data_id, values)
        if err:
            print(f"错误: {err}", file=sys.stderr)
            return 1

        cur.execute("INSERT INTO rs_row (table_name, data_id, remark) VALUES (?, ?, ?)", (table, data_id, remark))
        for field in fields:
            cur.execute(
                "INSERT INTO rs_field (table_name, data_id, field_name, field_value) VALUES (?, ?, ?, ?)",
                (table, data_id, field, values[field]),
            )
        cur.execute("UPDATE rs_datatable SET updated_at = CURRENT_TIMESTAMP WHERE table_name = ?", (table,))
        conn.commit()
        print(f"[OK] 已新增 {table}.{data_id}（{len(fields)} 个字段）")
        return 0
    except Exception as e:
        conn.rollback()
        print(f"错误: 操作失败: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()


def _delete_row(module: str, table: str, data_id: str) -> int:
    """删除行（字段值与行记录一并删除）。"""
    conn = _open_module_sqlite(module)
    if conn is None:
        return 1
    try:
        cur = conn.cursor()
        if _table_fields(cur, table) is None:
            print(_missing_table_msg(cur, table), file=sys.stderr)
            return 1
        cur.execute("SELECT COUNT(*) FROM rs_row WHERE table_name = ? AND data_id = ?", (table, data_id))
        if cur.fetchone()[0] == 0:
            print(f"错误: '{table}' 中找不到 DataID='{data_id}'", file=sys.stderr)
            return 1
        cur.execute("DELETE FROM rs_field WHERE table_name = ? AND data_id = ?", (table, data_id))
        cur.execute("DELETE FROM rs_row WHERE table_name = ? AND data_id = ?", (table, data_id))
        cur.execute("UPDATE rs_datatable SET updated_at = CURRENT_TIMESTAMP WHERE table_name = ?", (table,))
        conn.commit()
        print(f"[OK] 已删除 {table}.{data_id}")
        return 0
    except Exception as e:
        conn.rollback()
        print(f"错误: 操作失败: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()


# ---------------------------------------------------------------- v11.9.0 数据驱动表（CORE §7.8）
def _dd():
    try:
        from ..core import data_driven
    except ImportError:
        from rodski.core import data_driven
    return data_driven


def _sqlite_path(module: str) -> Path:
    return Path(module).resolve() / "data" / "data.sqlite"


def _driver_tables_meta(module: str):
    """{驱动表名: (绑定用例, 表备注, 行数)}"""
    import sqlite3

    db = _sqlite_path(module)
    if not db.is_file():
        return {}
    conn = sqlite3.connect(str(db))
    try:
        rows = conn.execute(
            "SELECT t.table_name, t.model_name, COALESCE(t.remark, ''), "
            "(SELECT COUNT(*) FROM rs_row r WHERE r.table_name = t.table_name) "
            "FROM rs_datatable t WHERE t.table_kind = 'driver'").fetchall()
    finally:
        conn.close()
    return {name: (uid, remark, count) for name, uid, remark, count in rows}


def _driver_row(module: str, table: str, data_id: str):
    import sqlite3

    conn = sqlite3.connect(str(_sqlite_path(module)))
    try:
        return {f: v for f, v in conn.execute(
            "SELECT field_name, field_value FROM rs_field WHERE table_name = ? AND data_id = ?", (table, data_id))}
    finally:
        conn.close()


def _row_remark(module: str, table: str, data_id: str) -> str:
    import sqlite3

    db = _sqlite_path(module)
    if not db.is_file():
        return ""
    conn = sqlite3.connect(str(db))
    try:
        row = conn.execute("SELECT COALESCE(remark, '') FROM rs_row WHERE table_name = ? AND data_id = ?",
                           (table, data_id)).fetchone()
    finally:
        conn.close()
    return row[0] if row else ""


def _table_kind(cur, table: str) -> str:
    cur.execute("SELECT table_kind FROM rs_datatable WHERE table_name = ?", (table,))
    row = cur.fetchone()
    return row[0] if row else ""


def _check_driver_cells(cur, table: str, data_id: str, values) -> str:
    """数据驱动表单元格只能是该列所指表中存在的 DataID 或 BLANK。"""
    if _table_kind(cur, table) != "driver":
        return ""
    dd = _dd()
    for column, value in values.items():
        value = value.strip()
        if value == dd.BLANK:
            continue
        if not dd.is_literal_data_id(value):
            return f"数据驱动表 {table} 实例 {data_id} 列 {column}：单元格 {value!r} 只能是 DataID 或 BLANK"
        target = column.split(".", 1)[0]
        cur.execute("SELECT COUNT(*) FROM rs_row WHERE table_name = ? AND data_id = ?", (target, value))
        if cur.fetchone()[0] == 0:
            return f"数据驱动表 {table} 实例 {data_id} 列 {column}：DataID {value} 在表 {target} 中不存在"
    return ""


def _module_case(module: str, case_uid: str):
    dd = _dd()
    try:
        from ..core.case_parser import CaseParser
    except ImportError:
        from rodski.core.case_parser import CaseParser
    case_dir = Path(module).resolve() / "case"
    if "::" not in case_uid:
        return None, f"--case 必须写成 case_file::case_id（如 login/flow.xml::LOGIN_FLOW），实际: {case_uid!r}"
    case_file, case_id = case_uid.split("::", 1)
    cases = CaseParser(str(case_dir)).parse_cases() if case_dir.is_dir() else []
    _, case = dd.find_plan_case(cases, {"id": case_id, "file": case_file})
    if case is None:
        return None, f"用例 {case_uid} 不存在或未启用（execute=\"否\"）"
    return case, ""


def _check_driver_column(module: str, cur, table: str, column: str, default: str) -> str:
    if _table_kind(cur, table) != "driver":
        return ""
    dd = _dd()
    cur.execute("SELECT model_name FROM rs_datatable WHERE table_name = ?", (table,))
    case_uid = cur.fetchone()[0]
    case, err = _module_case(module, case_uid)
    if err:
        return f"数据驱动表 {table} 绑定的{err}"
    catalog = dd.load_catalog(_sqlite_path(module))
    errors = dd.validate_columns(table, [column], case, case_uid, catalog)
    if errors:
        return errors[0]
    if default.strip() != dd.BLANK:
        return _check_driver_cells(cur, table, "*", {column: default})
    return ""


def _create_driver(module: str, table: str, case_uid: str, remark: str, columns_raw: str) -> int:
    """新建数据驱动表：校验全部通过后才写入（必要时先迁移旧库结构）。"""
    import sqlite3

    dd = _dd()
    db = _sqlite_path(module)
    if not db.is_file():
        print(f"错误: SQLite 文件不存在: {db}", file=sys.stderr)
        return 1
    errors = []
    if not remark.strip():
        errors.append(f"数据驱动表 {table} 的表备注为空（--remark 必填：目的、所属计划）")
    if not dd.is_literal_data_id(table):
        errors.append(f"数据驱动表名 {table!r} 不合法")
    model_names = dd.module_model_names(Path(module).resolve())
    if table in model_names or table in {f"{m}_verify" for m in model_names}:
        errors.append(f"数据驱动表 {table} 与模型 / 业务模型（或其 _verify 表）同名，驱动表不能与模型数据表同名")
    catalog = dd.load_catalog(db)
    if table in catalog.kinds:
        errors.append(f"逻辑表 {table} 已存在（table_kind={catalog.kinds[table]}）")
    columns = [c.strip() for c in columns_raw.split(",") if c.strip()]
    if not columns:
        errors.append("--columns 至少需要 1 列（表名.基础DataID）")
    if len(set(columns)) != len(columns):
        errors.append("--columns 中有重复列")
    case, err = _module_case(module, case_uid)
    if err:
        errors.append(err)
    elif columns:
        errors.extend(dd.validate_columns(table, columns, case, case_uid, catalog))
    if errors:
        for line in errors:
            print(f"错误: {line}", file=sys.stderr)
        return 1

    if dd.migrate_driver_kind(db):
        print(f"[INFO] 已迁移 {db.name} 结构（table_kind 增加 driver），原文件备份为 {db.name}.bak")
    conn = sqlite3.connect(str(db))
    try:
        conn.execute("INSERT INTO rs_datatable (table_name, model_name, table_kind, row_mode, remark) "
                     "VALUES (?, ?, 'driver', 'standard', ?)", (table, case_uid, remark))
        conn.executemany("INSERT INTO rs_datatable_field (table_name, field_name, field_order) VALUES (?, ?, ?)",
                         [(table, c, i) for i, c in enumerate(columns)])
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"错误: 操作失败: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    print(f"[OK] 已新建数据驱动表 {table}（绑定 {case_uid}，{len(columns)} 列）；"
          f"用 rodski data add-row 添加实例，在计划中写 <case ... data_driven=\"{table}\"/>")
    return 0


def _validate_driver_tables(module: str):
    """数据驱动表结构校验：绑定用例存在、表备注、列、单元格（不含计划相关检查）。"""
    dd = _dd()
    meta = _driver_tables_meta(module)
    if not meta:
        return []
    catalog = dd.load_catalog(_sqlite_path(module))
    model_names = dd.module_model_names(Path(module).resolve())
    errors = []
    for name, (case_uid, _, _) in sorted(meta.items()):
        case, err = _module_case(module, case_uid)
        if err:
            errors.append(f"数据驱动表 {name} 绑定的{err}")
            continue
        errors.extend(dd.validate_driver(catalog.driver(name), case, case_uid, catalog, model_names))
    return errors


def _driver_columns(module: str, table: str):
    import sqlite3

    conn = sqlite3.connect(str(_sqlite_path(module)))
    try:
        return [r[0] for r in conn.execute(
            "SELECT field_name FROM rs_datatable_field WHERE table_name = ? ORDER BY field_order, field_name", (table,))]
    finally:
        conn.close()
