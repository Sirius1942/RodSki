"""CaseResolver — 解析 RodSki 测试用例 XML，将 model/data 引用替换为实际值。

从 case 文件路径自动推断项目根目录（case/ 的上一级），加载：
- model/model.xml  — 元素定义
- data/data.xml    — 测试数据行
- data/globalvalue.xml — 全局变量

Python 3.9 兼容：使用 ``from __future__ import annotations`` 延迟求值。
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


# ============================================================
# 数据结构
# ============================================================

@dataclass
class ResolvedElement:
    name: str
    locator_type: str
    locator_value: str
    description: str = ""
    element_type: str = ""  # input / button / database / etc.


@dataclass
class ResolvedStep:
    action: str
    phase: str                              # pre_process | test_case | post_process
    model_name: str
    data_id: str                            # 原始 data 属性，用于 model/data 查表
    display_data: str = ""                  # 展示给评审人员的已解析参数
    elements: list[ResolvedElement] = field(default_factory=list)
    data_fields: dict[str, str] = field(default_factory=dict)
    raw_data: str = ""                      # 原始 data 属性（navigate/wait 等无 model 步骤）
    log_info: dict[str, Any] | None = None  # 由 LogCorrelator 注入
    db_info: dict[str, Any] = field(default_factory=dict)


@dataclass
class ResolvedCase:
    id: str
    title: str
    description: str
    component_type: str
    steps: list[ResolvedStep] = field(default_factory=list)


# ============================================================
# CaseResolver
# ============================================================

class CaseResolver:
    """解析 RodSki case XML，将 model/data 引用替换为实际值。"""

    def __init__(self, case_path: str) -> None:
        self.case_path = Path(case_path).resolve()
        # case/ 的上一级即项目根目录
        self.project_root = self.case_path.parent.parent
        self._models: dict[str, list[ResolvedElement]] = {}
        self._model_meta: dict[str, dict[str, Any]] = {}
        self._data: dict[str, dict[str, dict[str, str]]] = {}  # {table: {row_id: {field: value}}}
        self._table_meta: dict[str, dict[str, Any]] = {}
        self._global_values: dict[str, str] = {}
        self._global_groups: dict[str, dict[str, str]] = {}
        self._loaded = False

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def resolve(self, case_ids: list[str] | None = None) -> list[ResolvedCase]:
        """解析 case 文件，返回已解析的用例列表。

        Parameters
        ----------
        case_ids:
            指定要解析的用例 ID 列表；None 表示全部。
        """
        self._ensure_loaded()
        tree = ET.parse(self.case_path)
        root = tree.getroot()

        results: list[ResolvedCase] = []
        for case_elem in root.findall("case"):
            case_id = case_elem.get("id", "")
            if case_ids and case_id not in case_ids:
                continue
            results.append(self._resolve_case(case_elem))
        return results

    # ------------------------------------------------------------------
    # 内部：加载辅助文件
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._load_global_values()
        self._load_models()
        self._load_data()
        self._loaded = True

    def _load_global_values(self) -> None:
        gv_path = self.project_root / "data" / "globalvalue.xml"
        if not gv_path.exists():
            return
        tree = ET.parse(gv_path)
        for group in tree.getroot().findall("group"):
            group_name = group.get("name", "")
            group_values: dict[str, str] = {}
            for var in group.findall("var"):
                var_name = var.get("name", "")
                var_value = var.get("value", "")
                key = f"GlobalValue.{group_name}.{var_name}"
                self._global_values[key] = var_value
                group_values[var_name] = var_value
            self._global_groups[group_name] = group_values

        for group_name, group_values in list(self._global_groups.items()):
            self._global_groups[group_name] = {
                key: self._resolve_global(value)
                for key, value in group_values.items()
            }

    def _load_models(self) -> None:
        model_path = self.project_root / "model" / "model.xml"
        if not model_path.exists():
            return
        tree = ET.parse(model_path)
        for model_elem in tree.getroot().findall("model"):
            model_name = model_elem.get("name", "")
            model_type = model_elem.get("type", "").strip()
            self._model_meta[model_name] = {
                "name": model_name,
                "type": model_type,
                "connection": model_elem.get("connection", "").strip(),
                "servicename": model_elem.get("servicename", "").strip(),
                "queries": self._parse_database_queries(model_elem),
            }
            elements: list[ResolvedElement] = []
            for elem in model_elem.findall("element"):
                loc = elem.find("location")
                desc_elem = elem.find("desc")
                type_elem = elem.find("type")
                elements.append(ResolvedElement(
                    name=elem.get("name", ""),
                    locator_type=loc.get("type", "") if loc is not None else "",
                    locator_value=loc.text.strip() if loc is not None and loc.text else "",
                    description=desc_elem.text.strip() if desc_elem is not None and desc_elem.text else "",
                    element_type=(
                        type_elem.text.strip()
                        if type_elem is not None and type_elem.text
                        else elem.get("type", "")
                    ),
                ))
            self._models[model_name] = elements

    def _parse_database_queries(self, model_elem: ET.Element) -> dict[str, dict[str, str]]:
        queries: dict[str, dict[str, str]] = {}
        for query_elem in model_elem.findall("query"):
            query_name = query_elem.get("name", "").strip()
            if not query_name:
                continue
            sql_elem = query_elem.find("sql")
            sql = sql_elem.text.strip() if sql_elem is not None and sql_elem.text else ""
            queries[query_name] = {
                "name": query_name,
                "remark": query_elem.get("remark", "").strip(),
                "sql": sql,
            }
        return queries

    def _load_data(self) -> None:
        # SQLite 优先，回退到 XML
        sqlite_path = self.project_root / "data" / "data.sqlite"
        if sqlite_path.exists():
            self._load_data_sqlite(sqlite_path)
        else:
            self._load_data_xml()

    def _load_data_sqlite(self, db_path: Path) -> None:
        conn = sqlite3.connect(str(db_path))
        try:
            try:
                cur = conn.execute(
                    "SELECT table_name, model_name, table_kind, row_mode, remark "
                    "FROM rs_datatable"
                )
                table_rows = cur.fetchall()
            except sqlite3.OperationalError:
                cur = conn.execute("SELECT table_name FROM rs_datatable")
                table_rows = [(row[0], "", "", "", "") for row in cur.fetchall()]

            table_names = []
            for row in table_rows:
                table_name = row[0]
                table_names.append(table_name)
                self._table_meta[table_name] = {
                    "table_name": table_name,
                    "model_name": row[1] if len(row) > 1 else "",
                    "table_kind": row[2] if len(row) > 2 else "",
                    "row_mode": row[3] if len(row) > 3 else "",
                    "remark": row[4] if len(row) > 4 else "",
                    "fields": [],
                }

                try:
                    cur = conn.execute(
                        "SELECT field_name FROM rs_datatable_field "
                        "WHERE table_name = ? ORDER BY field_order, field_name",
                        (table_name,),
                    )
                    self._table_meta[table_name]["fields"] = [r[0] for r in cur.fetchall()]
                except sqlite3.OperationalError:
                    pass

            for table_name in table_names:
                cur = conn.execute(
                    "SELECT data_id FROM rs_row WHERE table_name = ?",
                    (table_name,),
                )
                data_ids = [row[0] for row in cur.fetchall()]

                for data_id in data_ids:
                    cur = conn.execute(
                        "SELECT f.field_name, f.field_value "
                        "FROM rs_field f "
                        "LEFT JOIN rs_datatable_field df "
                        "  ON df.table_name = f.table_name "
                        " AND df.field_name = f.field_name "
                        "WHERE f.table_name = ? AND f.data_id = ? "
                        "ORDER BY COALESCE(df.field_order, 0), f.field_name",
                        (table_name, data_id),
                    )
                    row_data = {r[0]: self._resolve_global(r[1]) for r in cur.fetchall()}
                    if row_data:
                        self._data.setdefault(table_name, {})[data_id] = row_data
        finally:
            conn.close()

    def _load_data_xml(self) -> None:
        for data_file in ["data.xml", "data_verify.xml"]:
            data_path = self.project_root / "data" / data_file
            if not data_path.exists():
                continue
            tree = ET.parse(data_path)
            for table in tree.getroot().findall("datatable"):
                table_name = table.get("name", "")
                if table_name not in self._data:
                    self._data[table_name] = {}
                for row in table.findall("row"):
                    row_id = row.get("id", "")
                    fields: dict[str, str] = {}
                    for f in row.findall("field"):
                        raw_val = f.text or ""
                        fields[f.get("name", "")] = self._resolve_global(raw_val.strip())
                    self._data[table_name][row_id] = fields

    # ------------------------------------------------------------------
    # 内部：解析单个 case
    # ------------------------------------------------------------------

    def _resolve_case(self, case_elem: ET.Element) -> ResolvedCase:
        case = ResolvedCase(
            id=case_elem.get("id", ""),
            title=case_elem.get("title", ""),
            description=case_elem.get("description", ""),
            component_type=case_elem.get("component_type", ""),
        )
        for phase_tag in ("pre_process", "test_case", "post_process"):
            phase_elem = case_elem.find(phase_tag)
            if phase_elem is None:
                continue
            for step_elem, step_phase in self._iter_phase_steps(phase_elem, phase_tag):
                case.steps.append(self._resolve_step(step_elem, step_phase))
        return case

    def _iter_phase_steps(self, phase_elem: ET.Element, phase_tag: str):
        """Yield steps in execution order, including v6.3 scenario groups."""
        if phase_tag != "test_case":
            for step_elem in phase_elem.findall("test_step"):
                yield step_elem, phase_tag
            return

        for child in list(phase_elem):
            if child.tag == "test_step":
                yield child, phase_tag
            elif child.tag == "scenario":
                scenario_id = child.get("id", "").strip()
                scenario_title = child.get("title", "").strip()
                suffix = " ".join(x for x in (scenario_id, scenario_title) if x)
                step_phase = f"{phase_tag}/{suffix}" if suffix else phase_tag
                for step_elem in child.iter("test_step"):
                    yield step_elem, step_phase

    def _resolve_step(self, step_elem: ET.Element, phase: str) -> ResolvedStep:
        action = step_elem.get("action", "")
        model_name = step_elem.get("model", "")
        data_id = step_elem.get("data", "")

        elements = self._models.get(model_name, []) if model_name else []
        data_fields = self._data.get(model_name, {}).get(data_id, {}) if model_name and data_id else {}
        if action in {"verify", "check"} and model_name and data_id and not data_fields:
            data_fields = self._data.get(f"{model_name}_verify", {}).get(data_id, {})
        db_info = self._resolve_db_info(action, model_name, data_id, data_fields)

        raw = data_id if not model_name else ""
        if raw:
            raw = self._resolve_global(raw)
            if action != "evaluate":
                raw = self._resolve_data_reference(raw)

        return ResolvedStep(
            action=action,
            phase=phase,
            model_name=model_name,
            data_id=data_id,
            display_data=raw if raw else data_id,
            elements=elements,
            data_fields=data_fields,
            raw_data=raw,
            db_info=db_info,
        )

    def _resolve_db_info(
        self,
        action: str,
        model_name: str,
        data_id: str,
        data_fields: dict[str, str],
    ) -> dict[str, Any]:
        if action != "DB" or not model_name:
            return {}

        model_meta = self._model_meta.get(model_name, {})
        if model_meta.get("type") != "database":
            return {}

        connection_name = model_meta.get("connection", "")
        connection = dict(self._global_groups.get(connection_name, {}))
        db_type = connection.get("type", "")
        database_value = connection.get("database", "")
        database_path = self._resolve_database_path(database_value, db_type)

        query_name = (data_fields.get("query") or data_fields.get("Query") or "").strip()
        queries = model_meta.get("queries", {})
        query_meta = queries.get(query_name, {}) if query_name else {}
        sql_template = (
            data_fields.get("sql")
            or data_fields.get("SQL")
            or query_meta.get("sql", "")
        )
        operation = (
            data_fields.get("operation")
            or data_fields.get("Operation")
            or self._infer_sql_operation(sql_template)
        )
        resolved_sql = self._replace_sql_params(sql_template, data_fields)
        verify_info = self._infer_verify_info(model_name, data_id)

        return {
            "model_type": "database",
            "service_name": model_meta.get("servicename", ""),
            "connection_name": connection_name,
            "connection": connection,
            "database_type": db_type,
            "database": database_value,
            "database_path": database_path,
            "data_table": model_name,
            "data_table_meta": self._table_meta.get(model_name, {}),
            "verify_table": f"{model_name}_verify" if f"{model_name}_verify" in self._data else "",
            "verify_table_meta": self._table_meta.get(f"{model_name}_verify", {}),
            "query_name": query_name,
            "query_remark": query_meta.get("remark", ""),
            "operation": operation,
            "sql_template": sql_template,
            "resolved_sql": resolved_sql,
            "sql_tables": self._extract_sql_tables(sql_template),
            "parameters": self._db_parameters(data_fields),
            "verify": verify_info,
        }

    def _resolve_database_path(self, database: str, db_type: str) -> str:
        if not database or db_type.lower() != "sqlite":
            return database
        path = Path(database)
        if path.is_absolute():
            return str(path)
        return str((self.project_root / path).resolve())

    @staticmethod
    def _infer_sql_operation(sql: str) -> str:
        if not sql:
            return ""
        return "query" if sql.lstrip().upper().startswith("SELECT") else "execute"

    @staticmethod
    def _replace_sql_params(sql: str, params: dict[str, str]) -> str:
        if not sql:
            return ""

        def replace_param(match: re.Match[str]) -> str:
            param_name = match.group(1)
            if param_name not in params:
                return match.group(0)
            value = params[param_name]
            if value is None or str(value).upper() == "NULL":
                return "NULL"
            if isinstance(value, (int, float)):
                return str(value)
            return "'" + str(value).replace("'", "''") + "'"

        return re.sub(r"(?<!:):(\w+)", replace_param, sql)

    @staticmethod
    def _db_parameters(data_fields: dict[str, str]) -> dict[str, str]:
        skip_fields = {"query", "Query", "sql", "SQL", "operation", "Operation"}
        return {
            key: value
            for key, value in data_fields.items()
            if key not in skip_fields and str(value).strip().upper() != "NONE"
        }

    @staticmethod
    def _extract_sql_tables(sql: str) -> list[str]:
        if not sql:
            return []
        tables: list[str] = []
        for match in re.finditer(
            r"\b(?:FROM|JOIN|UPDATE|INTO)\s+([`\"\[]?[\w.]+[`\"\]]?)",
            sql,
            re.IGNORECASE,
        ):
            table_name = match.group(1).strip("`\"[]")
            if table_name and table_name not in tables:
                tables.append(table_name)
        return tables

    def _infer_verify_info(self, model_name: str, data_id: str) -> dict[str, Any]:
        verify_table = f"{model_name}_verify"
        verify_rows = self._data.get(verify_table, {})
        if not verify_rows:
            return {}

        candidates: list[str] = []
        if data_id:
            match = re.search(r"(\d+)$", data_id)
            if match:
                candidates.append(f"V{match.group(1)}")
            if len(data_id) > 1:
                candidates.append(f"V{data_id[1:]}")
            candidates.append(data_id)

        for candidate in candidates:
            fields = verify_rows.get(candidate)
            if fields:
                return {
                    "table_name": verify_table,
                    "data_id": candidate,
                    "fields": fields,
                    "table_meta": self._table_meta.get(verify_table, {}),
                }
        return {
            "table_name": verify_table,
            "data_id": "",
            "fields": {},
            "table_meta": self._table_meta.get(verify_table, {}),
        }

    # ------------------------------------------------------------------
    # 内部：GlobalValue 替换
    # ------------------------------------------------------------------

    def _resolve_global(self, value: str) -> str:
        """将 GlobalValue.group.var 引用替换为实际值。"""
        if not value or "GlobalValue." not in value:
            return value
        for key in sorted(self._global_values, key=len, reverse=True):
            resolved = self._global_values[key]
            if value == key:
                return resolved
            if value.startswith(key):
                return resolved + value[len(key):]
            if key in value:
                value = value.replace(key, resolved)
        return value

    def _resolve_data_reference(self, value: str) -> str:
        """解析 Model.DataID.Field 形式的数据字段引用。"""
        if not value or value.count(".") < 2:
            return value
        table_name, row_id, field_name = value.split(".", 2)
        field_value = self._data.get(table_name, {}).get(row_id, {}).get(field_name)
        if field_value is None:
            return value
        return self._resolve_global(field_value)

    # ------------------------------------------------------------------
    # 序列化（供 LangGraph state 传递）
    # ------------------------------------------------------------------

    @staticmethod
    def to_dict(case: ResolvedCase) -> dict[str, Any]:
        return {
            "id": case.id,
            "title": case.title,
            "description": case.description,
            "component_type": case.component_type,
            "steps": [
                {
                    "action": s.action,
                    "phase": s.phase,
                    "model_name": s.model_name,
                    "data_id": s.data_id,
                    "display_data": s.display_data,
                    "elements": [
                        {
                            "name": e.name,
                            "locator_type": e.locator_type,
                            "locator_value": e.locator_value,
                            "description": e.description,
                            "element_type": e.element_type,
                        }
                        for e in s.elements
                    ],
                    "data_fields": s.data_fields,
                    "raw_data": s.raw_data,
                    "log_info": s.log_info,
                    "db_info": s.db_info,
                }
                for s in case.steps
            ],
        }
