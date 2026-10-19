"""计划级数据驱动（v11.9.0，CORE §7.8）。

数据驱动只在测试计划中声明（plan.xsd `<case data_driven="表名">`）。数据驱动表存放在
`data/data.sqlite`，`table_kind='driver'`，是计划 / 用例 / 步骤三者的对应关系表：

- `rs_datatable.model_name` = 绑定用例 `case_file::case_id`，`remark` 必填
- 列（`rs_datatable_field`）= `表名.基础DataID`
- 行（`rs_row`）= 实例，`data_id` 为实例 DataID，`remark` 为实例标题
- 单元格（`rs_field`）= 替换后的 DataID 或 `BLANK`

用例 XML 只带基础 DataID；展开实例时深拷贝用例，把字面 DataID 按 `(表名, 基础DataID) → 新DataID`
替换。替换只改变读取的行，不改变读取的表（一个模型对应一张数据表不变）。

本模块不依赖驱动与执行器：`rodski run` 在创建浏览器之前用它完成全部校验（校验先于副作用），
执行器展开实例时复用同一份缓存（每张驱动表在一次运行中只从 SQLite 读取一次）。
"""
from __future__ import annotations

import copy
import logging
import re
import shutil
import sqlite3
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence, Set, Tuple

logger = logging.getLogger("rodski")

DRIVER_KIND = "driver"
BLANK = "BLANK"

# 读取 `模型名` 表的关键字（data 为字面 DataID 时）；verify / check 读取 `模型名_verify`
_MODEL_TABLE_ACTIONS = {"type", "send", "db", "launch", "navigate"}
_VERIFY_ACTIONS = {"verify", "check"}
# 字面 DataID：不含变量、表名前缀、URL / 选择器 / 函数调用等字符
_LITERAL_DATA_ID = re.compile(r"^[^\s$.{}()\[\]=,:/#'\"【】<>]+$")
_PHASES = ("pre_process", "test_case", "post_process")


class DataDrivenError(Exception):
    """数据驱动配置错误（执行前报出，不产生任何外部副作用）。"""

    def __init__(self, errors: Sequence[str]):
        self.errors = list(errors)
        super().__init__("\n".join(self.errors))


def is_literal_data_id(value: str) -> bool:
    value = (value or "").strip()
    return bool(value) and not value.startswith("GlobalValue") and bool(_LITERAL_DATA_ID.match(value))


def step_table(step: Dict[str, Any]) -> Optional[str]:
    """该步骤 `data` 作为 DataID 时读取的数据表名；不读数据表的步骤返回 None。"""
    action = str(step.get("action", "")).strip().lower()
    model = str(step.get("model", "")).strip()
    if not model:
        return None
    if action in _VERIFY_ACTIONS:
        return model if model.endswith("_verify") else f"{model}_verify"
    if action in _MODEL_TABLE_ACTIONS:
        return model
    return None


# ------------------------------------------------------------------ 用例中的数据引用
@dataclass
class DataRef:
    table: str
    data_id: str
    holder: Dict[str, Any]
    key: str          # "data"（test_step）/ "input" / "expect"（business_call）


def _iter_step_list(steps: Any) -> Iterator[Dict[str, Any]]:
    for step in steps or []:
        if not isinstance(step, dict):
            continue
        yield step
        stype = step.get("type")
        if stype in ("if", "loop", "scenario"):
            yield from _iter_step_list(step.get("steps"))
            yield from _iter_step_list(step.get("else_steps"))
            for branch in step.get("elif_chain") or []:
                yield from _iter_step_list(branch.get("steps"))


def iter_literal_refs(case: Dict[str, Any]) -> Iterator[DataRef]:
    """遍历用例三阶段（含 scenario / if / loop 内）的字面 DataID 引用与 business_call 输入 / 期望。

    动态 DataID（`${...}`、`L00${i}`、GlobalValue）不是字面引用，不会被列出也不会被替换。
    """
    for phase in _PHASES:
        for step in _iter_step_list(case.get(phase)):
            if step.get("type") == "business_call":
                ref = str(step.get("ref", "")).strip()
                if not ref:
                    continue
                for key, table in (("input", ref), ("expect", f"{ref}_verify")):
                    value = str(step.get(key, "")).strip()
                    if is_literal_data_id(value):
                        yield DataRef(table, value, step, key)
                continue
            if step.get("type"):
                continue
            table = step_table(step)
            value = str(step.get("data", "")).strip()
            if table and is_literal_data_id(value):
                yield DataRef(table, value, step, "data")


# ------------------------------------------------------------------ SQLite 读取（带缓存）
@dataclass
class DriverRow:
    data_id: str
    remark: str
    cells: Dict[str, str]


@dataclass
class DriverTable:
    name: str
    case_uid: str
    remark: str
    columns: List[str]
    rows: List[DriverRow]


@dataclass
class DataCatalog:
    """一个 data.sqlite 的元信息：表类型、DataID 集合、行备注；驱动表按需整表读取。"""
    db_path: Path
    kinds: Dict[str, str] = field(default_factory=dict)
    table_meta: Dict[str, Tuple[str, str]] = field(default_factory=dict)   # name -> (model_name, remark)
    row_ids: Dict[str, Set[str]] = field(default_factory=dict)
    row_remarks: Dict[Tuple[str, str], str] = field(default_factory=dict)
    _drivers: Dict[str, DriverTable] = field(default_factory=dict)

    def driver(self, name: str) -> DriverTable:
        if name not in self._drivers:
            conn = sqlite3.connect(str(self.db_path))
            try:
                columns = [r[0] for r in conn.execute(
                    "SELECT field_name FROM rs_datatable_field WHERE table_name = ? "
                    "ORDER BY field_order, field_name", (name,))]
                rows: Dict[str, DriverRow] = {}
                order: List[str] = []
                for data_id, remark in conn.execute(
                        "SELECT data_id, COALESCE(remark, '') FROM rs_row WHERE table_name = ? ORDER BY rowid", (name,)):
                    rows[data_id] = DriverRow(data_id, remark, {})
                    order.append(data_id)
                for data_id, field_name, value in conn.execute(
                        "SELECT data_id, field_name, field_value FROM rs_field WHERE table_name = ?", (name,)):
                    if data_id in rows:
                        rows[data_id].cells[field_name] = value
            finally:
                conn.close()
            model_name, remark = self.table_meta.get(name, ("", ""))
            self._drivers[name] = DriverTable(name, model_name, remark, columns, [rows[d] for d in order])
        return self._drivers[name]


_CATALOG_CACHE: Dict[Tuple[str, int], DataCatalog] = {}


def load_catalog(db_path: Path) -> DataCatalog:
    db_path = Path(db_path).resolve()
    if not db_path.is_file():
        raise DataDrivenError([f"数据文件不存在: {db_path}"])
    key = (str(db_path), db_path.stat().st_mtime_ns)
    cached = _CATALOG_CACHE.get(key)
    if cached is not None:
        return cached
    catalog = DataCatalog(db_path)
    conn = sqlite3.connect(str(db_path))
    try:
        for name, model_name, kind, remark in conn.execute(
                "SELECT table_name, model_name, table_kind, COALESCE(remark, '') FROM rs_datatable"):
            catalog.kinds[name] = kind
            catalog.table_meta[name] = (model_name, remark)
        for table, data_id, remark in conn.execute(
                "SELECT table_name, data_id, COALESCE(remark, '') FROM rs_row"):
            catalog.row_ids.setdefault(table, set()).add(data_id)
            catalog.row_remarks[(table, data_id)] = remark
    finally:
        conn.close()
    _CATALOG_CACHE[key] = catalog
    return catalog


def module_model_names(module_dir: Path) -> Set[str]:
    """model.xml 中的模型名与 business/*.xml 中的业务模型 ID（驱动表不得与其同名）。"""
    names: Set[str] = set()
    model_file = Path(module_dir) / "model" / "model.xml"
    if model_file.is_file():
        try:
            for node in ET.parse(model_file).getroot().iter("model"):
                if node.get("name"):
                    names.add(node.get("name").strip())
        except ET.ParseError:
            pass
    business_dir = Path(module_dir) / "business"
    if business_dir.is_dir():
        for xml_file in sorted(business_dir.glob("*.xml")):
            try:
                for node in ET.parse(xml_file).getroot().iter("business_model"):
                    if node.get("id"):
                        names.add(node.get("id").strip())
            except ET.ParseError:
                pass
    return names


# ------------------------------------------------------------------ 校验
def parse_column(column: str) -> Optional[Tuple[str, str]]:
    if "." not in column:
        return None
    table, base = column.split(".", 1)
    table, base = table.strip(), base.strip()
    if not table or not is_literal_data_id(base) or not is_literal_data_id(table):
        return None
    return table, base


def validate_columns(name: str, columns: Sequence[str], case: Optional[Dict[str, Any]], case_uid: str,
                     catalog: DataCatalog) -> List[str]:
    """列名格式、列的表存在且为模型数据表、基础 DataID 被用例字面引用。"""
    errors: List[str] = []
    refs = {(r.table, r.data_id) for r in iter_literal_refs(case)} if case is not None else set()
    for column in columns:
        parsed = parse_column(column)
        if parsed is None:
            errors.append(f"数据驱动表 {name} 列名 {column!r} 不合法：列名必须是 `表名.基础DataID`（基础 DataID 为字面值）")
            continue
        table, base = parsed
        kind = catalog.kinds.get(table)
        if kind is None:
            errors.append(f"数据驱动表 {name} 列 {column}：数据表 {table} 不存在")
            continue
        if kind == DRIVER_KIND:
            errors.append(f"数据驱动表 {name} 列 {column}：{table} 是数据驱动表，列只能指向模型数据表")
            continue
        if case is not None and (table, base) not in refs:
            errors.append(f"数据驱动表 {name} 列 {column}：基础 DataID {base} 未被用例 {case_uid} 字面引用"
                          f"（检查列名或用例是否已修改）")
    return errors


def validate_driver(driver: DriverTable, case: Dict[str, Any], case_uid: str, catalog: DataCatalog,
                    model_names: Set[str]) -> List[str]:
    name = driver.name
    errors: List[str] = []
    collide = {m for m in model_names} | {f"{m}_verify" for m in model_names}
    if name in collide:
        errors.append(f"数据驱动表 {name} 与模型 / 业务模型（或其 _verify 表）同名，驱动表不能与模型数据表同名")
    if driver.case_uid != case_uid:
        errors.append(f"数据驱动表 {name} 绑定用例 {driver.case_uid}，与计划中的用例 {case_uid} 不一致（绑定不符）")
        return errors
    if not driver.remark.strip():
        errors.append(f"数据驱动表 {name} 的表备注为空（表备注必填：目的、所属计划）")
    if not driver.rows:
        errors.append(f"数据驱动表 {name} 没有任何行（至少需要 1 个实例，不允许 0 个实例静默通过）")
    errors.extend(validate_columns(name, driver.columns, case, case_uid, catalog))
    if errors:
        return errors
    for row in driver.rows:
        for column in driver.columns:
            value = str(row.cells.get(column, "")).strip()
            if value == BLANK:
                continue
            if not is_literal_data_id(value):
                errors.append(f"数据驱动表 {name} 实例 {row.data_id} 列 {column}：单元格 {value!r} 只能是 DataID 或 BLANK")
                continue
            table = column.split(".", 1)[0]
            if value not in catalog.row_ids.get(table, set()):
                errors.append(f"数据驱动表 {name} 实例 {row.data_id} 列 {column}：DataID {value} 在表 {table} 中不存在")
    return errors


def check_driver_reference(name: str, case: Optional[Dict[str, Any]], case_uid: str, catalog: DataCatalog,
                           model_names: Set[str], plan_label: str) -> Tuple[Optional[DriverTable], List[str]]:
    kind = catalog.kinds.get(name)
    if kind is None:
        return None, [f"数据驱动表不存在: {name}（{plan_label}，用例 {case_uid}）"]
    if kind != DRIVER_KIND:
        return None, [f"{name} 不是数据驱动表（table_kind={kind}），data_driven 只能引用 table_kind='driver' 的表"
                      f"（{plan_label}，用例 {case_uid}）"]
    if case is None:
        return None, [f"数据驱动表 {name}：计划引用的用例 {case_uid} 不存在或未启用（execute=\"否\"）"]
    driver = catalog.driver(name)
    return driver, validate_driver(driver, case, case_uid, catalog, model_names)


# ------------------------------------------------------------------ 计划级入口
def plan_data_driven_entries(plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [c for c in plan.get("cases", []) or [] if c.get("data_driven")]


def check_plan_kind(plan: Dict[str, Any]) -> List[str]:
    entries = plan_data_driven_entries(plan)
    kind = plan.get("kind", "")
    if entries and kind != "suite":
        ids = ", ".join(e.get("id", "") for e in entries)
        return [f"data_driven 只能用于 kind=\"suite\" 的测试计划（计划 {plan.get('id', '')} 的 kind={kind!r}，用例 {ids}）"]
    return []


def _case_uid(case: Dict[str, Any]) -> str:
    return case.get("case_uid") or f"{case.get('case_file', '')}::{case.get('case_id', '')}"


def find_plan_case(cases: Sequence[Dict[str, Any]], entry: Dict[str, Any]) -> Tuple[str, Optional[Dict[str, Any]]]:
    case_id = entry.get("id", "")
    case_file = entry.get("file", "")
    if not case_file:
        files = {c.get("case_file", "") for c in cases if c.get("case_id") == case_id}
        if len(files) == 1:
            case_file = files.pop()
    uid = f"{case_file}::{case_id}"
    for case in cases:
        if case.get("case_id") == case_id and case.get("case_file", "") == case_file:
            return uid, case
    return uid, None


def precheck_plan(plan: Dict[str, Any], cases: Sequence[Dict[str, Any]], module_dir: Path) -> List[str]:
    """计划中全部数据驱动配置的执行前校验；返回错误列表（空 = 通过）。"""
    errors = check_plan_kind(plan)
    entries = plan_data_driven_entries(plan)
    if errors or not entries:
        return errors
    catalog = load_catalog(Path(module_dir) / "data" / "data.sqlite")
    model_names = module_model_names(Path(module_dir))
    label = f"计划 {plan.get('id', '')}"
    for entry in entries:
        uid, case = find_plan_case(cases, entry)
        _, errs = check_driver_reference(entry["data_driven"], case, uid, catalog, model_names, label)
        errors.extend(errs)
    return errors


# ------------------------------------------------------------------ 实例展开
def instance_id(case_id: str, data_id: str) -> str:
    return f"{case_id}[{data_id}]"


def build_instances(case: Dict[str, Any], driver: DriverTable, catalog: DataCatalog) -> List[Dict[str, Any]]:
    """把一个用例按驱动表展开为实例（深拷贝 + 字面 DataID 替换）。调用前须已通过 validate_driver。"""
    instances: List[Dict[str, Any]] = []
    case_id = case.get("case_id", "")
    for index, row in enumerate(driver.rows):
        mapping: Dict[Tuple[str, str], str] = {}
        applied: List[str] = []
        for column in driver.columns:
            value = str(row.cells.get(column, "")).strip()
            table, base = column.split(".", 1)
            if value == BLANK or value == base:
                continue
            mapping[(table, base)] = value
            applied.append(f"{column}={value}")
        inst = copy.deepcopy(case)
        tag = f"{driver.name}[{row.data_id}]"
        for ref in iter_literal_refs(inst):
            new = mapping.get((ref.table, ref.data_id))
            if new is None:
                continue
            ref.holder[ref.key] = new
            ref.holder.setdefault("_dd_replaced", []).append((ref.table, ref.data_id, new, tag))
        inst["case_id"] = instance_id(case_id, row.data_id)
        inst["case_uid"] = f"{inst.get('case_file', '')}::{inst['case_id']}"
        inst["_data_driven"] = {
            "template_case_id": case_id,
            "template_uid": _case_uid(case),
            "driver": driver.name,
            "data_id": row.data_id,
            "instance_title": row.remark,
            "replacements": "; ".join(applied),
            "index": index,
            "missing_remarks": [
                f"{table}.{new}" for (table, _), new in mapping.items()
                if not catalog.row_remarks.get((table, new), "").strip()
            ],
        }
        instances.append(inst)
    return instances


def _match_filter(inst: Dict[str, Any], values: Sequence[str]) -> bool:
    dd = inst["_data_driven"]
    return dd["data_id"] in values or inst["case_id"] in values


def filter_instances(instances: List[Dict[str, Any]], include: Sequence[str], exclude: Sequence[str]) -> List[Dict[str, Any]]:
    kept = []
    for inst in instances:
        if include and not _match_filter(inst, include):
            continue
        if exclude and _match_filter(inst, exclude):
            continue
        kept.append(inst)
    return kept


def parse_id_list(raw: Optional[str]) -> List[str]:
    """`a,b,LOGIN[user]` → ['a', 'b', 'LOGIN[user]']（方括号内的逗号不切分）。"""
    if not raw:
        return []
    items, buf, depth = [], "", 0
    for ch in raw:
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            if buf.strip():
                items.append(buf.strip())
            buf = ""
        else:
            buf += ch
    if buf.strip():
        items.append(buf.strip())
    return items


def expand_plan_cases(plan: Dict[str, Any], cases: List[Dict[str, Any]], case_skips: Dict[str, str],
                      module_dir: Path, include: Sequence[str] = (), exclude: Sequence[str] = ()) -> List[Dict[str, Any]]:
    """按计划展开数据驱动用例；其余用例原样保留。配置错误抛 DataDrivenError。"""
    errors = check_plan_kind(plan)
    if errors:
        raise DataDrivenError(errors)
    entries = plan_data_driven_entries(plan)
    if not entries:
        return cases
    catalog = load_catalog(Path(module_dir) / "data" / "data.sqlite")
    model_names = module_model_names(Path(module_dir))
    label = f"计划 {plan.get('id', '')}"
    drivers: Dict[str, DriverTable] = {}
    for entry in entries:
        uid, case = find_plan_case(cases, entry)
        driver, errs = check_driver_reference(entry["data_driven"], case, uid, catalog, model_names, label)
        errors.extend(errs)
        if driver is not None and not errs:
            drivers[uid] = driver
    if errors:
        raise DataDrivenError(errors)

    expanded: List[Dict[str, Any]] = []
    for case in cases:
        uid = _case_uid(case)
        driver = drivers.get(uid)
        if driver is None or uid in case_skips:
            expanded.append(case)
            continue
        instances = filter_instances(build_instances(case, driver, catalog), include, exclude)
        if not instances:
            logger.info(f"数据驱动用例 {uid}：--data-id / --exclude-data-id 过滤后没有实例，不执行")
        expanded.extend(instances)
    return expanded


# ------------------------------------------------------------------ 结构迁移
def migrate_driver_kind(db_path: Path) -> bool:
    """旧版 data.sqlite（table_kind CHECK 只允许 data/verify）迁移为允许 driver。

    SQLite 不能修改 CHECK：在事务内新建表、复制、删除旧表、改名；迁移前备份为 data.sqlite.bak。
    已是新结构时不做任何事并返回 False。
    """
    db_path = Path(db_path)
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='rs_datatable'").fetchone()
        if row is None or f"'{DRIVER_KIND}'" in (row[0] or ""):
            return False
    finally:
        conn.close()
    shutil.copy2(db_path, db_path.with_name(db_path.name + ".bak"))
    conn = sqlite3.connect(str(db_path), isolation_level=None)
    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("BEGIN")
        conn.execute("""
            CREATE TABLE rs_datatable__v119 (
                table_name TEXT PRIMARY KEY,
                model_name TEXT NOT NULL,
                table_kind TEXT NOT NULL CHECK (table_kind IN ('data', 'verify', 'driver')),
                row_mode TEXT NOT NULL CHECK (row_mode IN ('standard', 'db_query', 'db_sql')),
                remark TEXT DEFAULT '',
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )""")
        conn.execute("INSERT INTO rs_datatable__v119 (table_name, model_name, table_kind, row_mode, remark, updated_at) "
                     "SELECT table_name, model_name, table_kind, row_mode, remark, updated_at FROM rs_datatable")
        conn.execute("DROP TABLE rs_datatable")
        conn.execute("ALTER TABLE rs_datatable__v119 RENAME TO rs_datatable")
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    return True
