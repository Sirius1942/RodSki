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
    data_id: str
    elements: list[ResolvedElement] = field(default_factory=list)
    data_fields: dict[str, str] = field(default_factory=dict)
    raw_data: str = ""                      # 原始 data 属性（navigate/wait 等无 model 步骤）
    log_info: dict[str, Any] | None = None  # 由 LogCorrelator 注入


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
        self._data: dict[str, dict[str, dict[str, str]]] = {}  # {table: {row_id: {field: value}}}
        self._global_values: dict[str, str] = {}
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
            for var in group.findall("var"):
                key = f"GlobalValue.{group_name}.{var.get('name', '')}"
                self._global_values[key] = var.get("value", "")

    def _load_models(self) -> None:
        model_path = self.project_root / "model" / "model.xml"
        if not model_path.exists():
            return
        tree = ET.parse(model_path)
        for model_elem in tree.getroot().findall("model"):
            model_name = model_elem.get("name", "")
            elements: list[ResolvedElement] = []
            for elem in model_elem.findall("element"):
                loc = elem.find("location")
                desc_elem = elem.find("desc")
                elements.append(ResolvedElement(
                    name=elem.get("name", ""),
                    locator_type=loc.get("type", "") if loc is not None else "",
                    locator_value=loc.text.strip() if loc is not None and loc.text else "",
                    description=desc_elem.text.strip() if desc_elem is not None and desc_elem.text else "",
                    element_type=elem.get("type", ""),
                ))
            self._models[model_name] = elements

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
            cur = conn.execute("SELECT table_name FROM rs_datatable")
            table_names = [row[0] for row in cur.fetchall()]

            for table_name in table_names:
                cur = conn.execute(
                    "SELECT data_id FROM rs_row WHERE table_name = ?",
                    (table_name,),
                )
                data_ids = [row[0] for row in cur.fetchall()]

                for data_id in data_ids:
                    cur = conn.execute(
                        "SELECT field_name, field_value FROM rs_field "
                        "WHERE table_name = ? AND data_id = ?",
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
            for step_elem in phase_elem.findall("test_step"):
                case.steps.append(self._resolve_step(step_elem, phase_tag))
        return case

    def _resolve_step(self, step_elem: ET.Element, phase: str) -> ResolvedStep:
        action = step_elem.get("action", "")
        model_name = step_elem.get("model", "")
        data_id = step_elem.get("data", "")

        elements = self._models.get(model_name, []) if model_name else []
        data_fields = self._data.get(model_name, {}).get(data_id, {}) if model_name and data_id else {}

        return ResolvedStep(
            action=action,
            phase=phase,
            model_name=model_name,
            data_id=data_id,
            elements=elements,
            data_fields=data_fields,
            raw_data=data_id if not model_name else "",
        )

    # ------------------------------------------------------------------
    # 内部：GlobalValue 替换
    # ------------------------------------------------------------------

    def _resolve_global(self, value: str) -> str:
        """将 GlobalValue.group.var 引用替换为实际值。"""
        if not value.startswith("GlobalValue."):
            return value
        return self._global_values.get(value, value)

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
                }
                for s in case.steps
            ],
        }
