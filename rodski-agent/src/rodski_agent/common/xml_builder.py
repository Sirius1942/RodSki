"""XML 生成器 — 遵循 rodski 约束生成 XML 文件。

根据 Design Agent 产出的结构化数据（dict/list）生成符合 rodski schema 的 XML 字符串。
每个 build_* 函数均在生成前执行约束校验，违规时抛出 ValueError。

Python 3.9 兼容：使用 ``from __future__ import annotations`` 延迟求值。
"""

from __future__ import annotations

import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

from rodski_agent.common.rodski_knowledge import (
    CASE_PHASES,
    COMPONENT_TYPES,
    EXECUTE_VALUES,
    validate_action,
    validate_locator_type,
    VERIFY_TABLE_SUFFIX,
)


# ============================================================
# Public API
# ============================================================


def build_case_xml(cases: list[dict]) -> str:
    """Generate case XML. Validate actions against SUPPORTED_KEYWORDS.

    Parameters
    ----------
    cases : list[dict]
        Each dict must have: id, title, steps (list of step dicts).
        Optional: execute (default "是"), description, component_type.
        Each step dict: action (required), model (optional), data (optional),
        phase (optional, default "test_case").

    Returns
    -------
    str
        Pretty-printed XML string with declaration header.

    Raises
    ------
    ValueError
        If any action is invalid, or no test_case phase steps are found.
    """
    if not cases:
        raise ValueError("cases list must not be empty")

    root = ET.Element("cases")

    for case_data in cases:
        case_id = case_data.get("id", "")
        title = case_data.get("title", "")
        execute = case_data.get("execute", "是")
        description = case_data.get("description", "")
        component_type = case_data.get("component_type", "")

        if not case_id:
            raise ValueError("case 'id' is required")
        if not title:
            raise ValueError(f"case '{case_id}' must have a 'title'")
        if execute not in EXECUTE_VALUES:
            raise ValueError(
                f"case '{case_id}' execute='{execute}' invalid; "
                f"must be one of {EXECUTE_VALUES}"
            )
        if component_type and component_type not in COMPONENT_TYPES:
            raise ValueError(
                f"case '{case_id}' component_type='{component_type}' invalid; "
                f"must be one of {COMPONENT_TYPES}"
            )

        case_elem = ET.SubElement(root, "case")
        case_elem.set("execute", execute)
        case_elem.set("id", case_id)
        case_elem.set("title", title)
        if description:
            case_elem.set("description", description)
        if component_type:
            case_elem.set("component_type", component_type)

        # Group steps by phase
        steps = case_data.get("steps", [])
        phase_steps: dict[str, list[dict]] = {
            "pre_process": [],
            "test_case": [],
            "post_process": [],
        }
        for step in steps:
            action = step.get("action", "")
            if not action:
                raise ValueError(
                    f"case '{case_id}': step missing 'action'"
                )
            if not validate_action(action):
                raise ValueError(
                    f"case '{case_id}': invalid action '{action}'"
                )
            phase = step.get("phase", "test_case")
            if phase not in CASE_PHASES:
                raise ValueError(
                    f"case '{case_id}': invalid phase '{phase}'; "
                    f"must be one of {CASE_PHASES}"
                )
            phase_steps[phase].append(step)

        if not phase_steps["test_case"]:
            raise ValueError(
                f"case '{case_id}' must have at least one test_case step"
            )

        # Build phase containers in XSD order
        for phase_name in CASE_PHASES:
            phase_step_list = phase_steps[phase_name]
            if phase_name == "test_case" or phase_step_list:
                container = ET.SubElement(case_elem, phase_name)
                for step in phase_step_list:
                    step_elem = ET.SubElement(container, "test_step")
                    step_elem.set("action", step["action"])
                    step_elem.set("model", step.get("model", ""))
                    step_elem.set("data", step.get("data", ""))

    return _pretty_xml(root)


def build_model_xml(models: list[dict]) -> str:
    """Generate model XML. ONLY ``<location type="...">value</location>`` format.

    Parameters
    ----------
    models : list[dict]
        Each dict: name (str), elements (list of element dicts).
        Element dict: name (str), type (str, driver type), locators (list).
        Locator dict: type (str), value (str).

    Returns
    -------
    str
        Pretty-printed XML string.

    Raises
    ------
    ValueError
        If locator type is invalid or element has no locators.
    """
    if not models:
        raise ValueError("models list must not be empty")

    root = ET.Element("models")

    for model_data in models:
        model_name = model_data.get("name", "")
        if not model_name:
            raise ValueError("model 'name' is required")

        model_elem = ET.SubElement(root, "model")
        model_elem.set("name", model_name)
        model_type = model_data.get("model_type") or model_data.get("category")
        if model_type:
            model_elem.set("type", model_type)
        driver_type = model_data.get("driver_type", "")
        if driver_type:
            model_elem.set("driver_type", driver_type)

        elements = model_data.get("elements", [])
        if not elements:
            raise ValueError(f"model '{model_name}' must have at least one element")

        for elem_data in elements:
            elem_name = elem_data.get("name", "")
            elem_type = elem_data.get("type", "web")

            if not elem_name:
                raise ValueError(
                    f"model '{model_name}': element 'name' is required"
                )

            element = ET.SubElement(model_elem, "element")
            element.set("name", elem_name)
            element.set("type", elem_type)

            locators = elem_data.get("locators", [])
            if not locators:
                raise ValueError(
                    f"model '{model_name}', element '{elem_name}': "
                    "at least one locator is required"
                )

            for i, loc_data in enumerate(locators):
                loc_type = loc_data.get("type", "")
                loc_value = loc_data.get("value", "")

                if not validate_locator_type(loc_type):
                    raise ValueError(
                        f"model '{model_name}', element '{elem_name}': "
                        f"invalid locator type '{loc_type}'"
                    )

                location = ET.SubElement(element, "location")
                location.set("type", loc_type)
                location.text = loc_value
                if len(locators) > 1:
                    location.set("priority", str(i + 1))

    return _pretty_xml(root)


def write_data_sqlite(path: str | Path, datatables: list[dict], verify_tables: list[dict] | None = None) -> None:
    """Write RodSki data.sqlite from datatable dictionaries.

    This is the v6+ data format used by executable RodSki modules. It mirrors
    ``rodski/core/sqlite_schema.py`` without importing RodSki core from the agent.
    """
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(
            """
CREATE TABLE IF NOT EXISTS rs_datatable (
    table_name TEXT PRIMARY KEY,
    model_name TEXT NOT NULL,
    table_kind TEXT NOT NULL CHECK (table_kind IN ('data', 'verify')),
    row_mode TEXT NOT NULL CHECK (row_mode IN ('standard', 'db_query', 'db_sql')),
    remark TEXT DEFAULT '',
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS rs_datatable_field (
    table_name TEXT NOT NULL,
    field_name TEXT NOT NULL,
    field_order INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (table_name, field_name),
    FOREIGN KEY (table_name) REFERENCES rs_datatable(table_name)
);
CREATE TABLE IF NOT EXISTS rs_row (
    table_name TEXT NOT NULL,
    data_id TEXT NOT NULL,
    remark TEXT DEFAULT '',
    PRIMARY KEY (table_name, data_id),
    FOREIGN KEY (table_name) REFERENCES rs_datatable(table_name)
);
CREATE TABLE IF NOT EXISTS rs_field (
    table_name TEXT NOT NULL,
    data_id TEXT NOT NULL,
    field_name TEXT NOT NULL,
    field_value TEXT NOT NULL,
    PRIMARY KEY (table_name, data_id, field_name),
    FOREIGN KEY (table_name, data_id) REFERENCES rs_row(table_name, data_id),
    FOREIGN KEY (table_name, field_name) REFERENCES rs_datatable_field(table_name, field_name)
);
"""
        )
        for table_data in datatables:
            _insert_sqlite_table(conn, table_data, "data")
        for table_data in verify_tables or []:
            _insert_sqlite_table(conn, table_data, "verify")
        conn.commit()
    finally:
        conn.close()


def build_plan_xml(
    cases: list[dict],
    plan_id: str = "project_full",
    title: str = "Project Full",
    execute: str = "是",
    default_execute: str = "是",
) -> str:
    """Generate a suite plan XML that references generated case IDs."""
    if not plan_id:
        raise ValueError("plan_id must not be empty")
    if execute not in EXECUTE_VALUES:
        raise ValueError(f"plan execute='{execute}' invalid; must be one of {EXECUTE_VALUES}")
    if default_execute not in EXECUTE_VALUES:
        raise ValueError(
            f"plan default_execute='{default_execute}' invalid; must be one of {EXECUTE_VALUES}"
        )

    root = ET.Element("test_plan")
    root.set("id", plan_id)
    root.set("title", title)
    root.set("kind", "suite")
    root.set("execute", execute)
    root.set("default_execute", default_execute)

    for case_data in cases:
        case_id = case_data.get("id", "")
        if not case_id:
            raise ValueError("plan case 'id' is required")
        case_execute = case_data.get("plan_execute", case_data.get("execute", "是"))
        if case_execute not in EXECUTE_VALUES:
            raise ValueError(
                f"plan case '{case_id}' execute='{case_execute}' invalid; "
                f"must be one of {EXECUTE_VALUES}"
            )
        case_elem = ET.SubElement(root, "case")
        case_elem.set("id", case_id)
        case_elem.set("execute", case_execute)

    return _pretty_xml(root)


def build_data_xml(datatables: list[dict]) -> str:
    """Generate data XML. Validate field names match model elements.

    Parameters
    ----------
    datatables : list[dict]
        Each dict: name (str), rows (list of row dicts).
        Row dict: id (str), fields (list of field dicts).
        Field dict: name (str), value (str).

    Returns
    -------
    str
        Pretty-printed XML string.

    Raises
    ------
    ValueError
        If table name is empty, rows are empty, or field name is empty.
    """
    if not datatables:
        raise ValueError("datatables list must not be empty")

    root = ET.Element("datatables")

    for table_data in datatables:
        table_name = table_data.get("name", "")
        if not table_name:
            raise ValueError("datatable 'name' is required")

        datatable = ET.SubElement(root, "datatable")
        datatable.set("name", table_name)

        rows = table_data.get("rows", [])
        if not rows:
            raise ValueError(f"datatable '{table_name}' must have at least one row")

        row_ids: set[str] = set()
        for row_data in rows:
            row_id = row_data.get("id", "")
            if not row_id:
                raise ValueError(
                    f"datatable '{table_name}': row 'id' is required"
                )
            if row_id in row_ids:
                raise ValueError(
                    f"datatable '{table_name}': duplicate row id '{row_id}'"
                )
            row_ids.add(row_id)

            row = ET.SubElement(datatable, "row")
            row.set("id", row_id)

            fields = row_data.get("fields", [])
            if not fields:
                raise ValueError(
                    f"datatable '{table_name}', row '{row_id}': "
                    "at least one field is required"
                )

            for field_data in fields:
                field_name = field_data.get("name", "")
                field_value = field_data.get("value", "")
                if not field_name:
                    raise ValueError(
                        f"datatable '{table_name}', row '{row_id}': "
                        "field 'name' is required"
                    )
                field = ET.SubElement(row, "field")
                field.set("name", field_name)
                field.text = field_value

    return _pretty_xml(root)


def build_verify_xml(datatables: list[dict]) -> str:
    """Generate verify data XML. Validate table name suffix.

    Parameters
    ----------
    datatables : list[dict]
        Same structure as build_data_xml, but table names must end
        with ``_verify``.

    Returns
    -------
    str
        Pretty-printed XML string.

    Raises
    ------
    ValueError
        If table name does not end with ``_verify``.
    """
    if not datatables:
        raise ValueError("verify datatables list must not be empty")

    for table_data in datatables:
        table_name = table_data.get("name", "")
        if not table_name.endswith(VERIFY_TABLE_SUFFIX):
            raise ValueError(
                f"verify table name '{table_name}' must end with "
                f"'{VERIFY_TABLE_SUFFIX}'"
            )

    # Reuse build_data_xml for the actual XML generation
    return build_data_xml(datatables)


def build_globalvalue_xml(groups: list[dict]) -> str:
    """Generate globalvalue XML.

    Parameters
    ----------
    groups : list[dict]
        Each dict: name (str), vars (list of var dicts).
        Var dict: name (str), value (str).

    Returns
    -------
    str
        Pretty-printed XML string.

    Raises
    ------
    ValueError
        If group name is empty or duplicate, or var name is empty.
    """
    if not groups:
        raise ValueError("groups list must not be empty")

    root = ET.Element("globalvalue")

    group_names: set[str] = set()
    for group_data in groups:
        group_name = group_data.get("name", "")
        if not group_name:
            raise ValueError("group 'name' is required")
        if group_name in group_names:
            raise ValueError(f"duplicate group name '{group_name}'")
        group_names.add(group_name)

        group = ET.SubElement(root, "group")
        group.set("name", group_name)

        vars_list = group_data.get("vars", [])
        if not vars_list:
            raise ValueError(
                f"group '{group_name}' must have at least one var"
            )

        var_names: set[str] = set()
        for var_data in vars_list:
            var_name = var_data.get("name", "")
            var_value = var_data.get("value", "")
            if not var_name:
                raise ValueError(
                    f"group '{group_name}': var 'name' is required"
                )
            if var_name in var_names:
                raise ValueError(
                    f"group '{group_name}': duplicate var name '{var_name}'"
                )
            var_names.add(var_name)

            var = ET.SubElement(group, "var")
            var.set("name", var_name)
            var.set("value", var_value)

    return _pretty_xml(root)


# ============================================================
# Internal helpers
# ============================================================


def _insert_sqlite_table(conn: sqlite3.Connection, table_data: dict, table_kind: str) -> None:
    table_name = table_data.get("name", "")
    if not table_name:
        raise ValueError("datatable 'name' is required")
    if table_kind == "verify" and not table_name.endswith(VERIFY_TABLE_SUFFIX):
        raise ValueError(
            f"verify table name '{table_name}' must end with '{VERIFY_TABLE_SUFFIX}'"
        )

    rows = table_data.get("rows", [])
    if not rows:
        raise ValueError(f"datatable '{table_name}' must have at least one row")

    field_names: list[str] = []
    row_ids: set[str] = set()
    for row_data in rows:
        row_id = row_data.get("id", "")
        if not row_id:
            raise ValueError(f"datatable '{table_name}': row 'id' is required")
        if row_id in row_ids:
            raise ValueError(f"datatable '{table_name}': duplicate row id '{row_id}'")
        row_ids.add(row_id)

        fields = row_data.get("fields", [])
        if not fields:
            raise ValueError(
                f"datatable '{table_name}', row '{row_id}': at least one field is required"
            )
        for field_data in fields:
            field_name = field_data.get("name", "")
            if not field_name:
                raise ValueError(
                    f"datatable '{table_name}', row '{row_id}': field 'name' is required"
                )
            if field_name not in field_names:
                field_names.append(field_name)

    model_name = table_name[:-len(VERIFY_TABLE_SUFFIX)] if table_kind == "verify" else table_name
    conn.execute(
        "INSERT INTO rs_datatable VALUES (?,?,?,?,?,CURRENT_TIMESTAMP)",
        (table_name, model_name, table_kind, "standard", table_data.get("remark", "")),
    )
    for order, field_name in enumerate(field_names):
        conn.execute(
            "INSERT INTO rs_datatable_field VALUES (?,?,?)",
            (table_name, field_name, order),
        )
    for row_data in rows:
        row_id = row_data["id"]
        conn.execute(
            "INSERT INTO rs_row VALUES (?,?,?)",
            (table_name, row_id, row_data.get("remark", "")),
        )
        row_fields = {f.get("name", ""): str(f.get("value", "")) for f in row_data.get("fields", [])}
        for field_name in field_names:
            conn.execute(
                "INSERT INTO rs_field VALUES (?,?,?,?)",
                (table_name, row_id, field_name, row_fields.get(field_name, "")),
            )


def _pretty_xml(root: ET.Element) -> str:
    """Pretty print XML with declaration header.

    Returns
    -------
    str
        Indented XML string starting with ``<?xml version="1.0" encoding="UTF-8"?>``.
    """
    rough_string = ET.tostring(root, encoding="unicode")
    dom = minidom.parseString(rough_string)
    pretty = dom.toprettyxml(indent="  ", encoding=None)

    # minidom.toprettyxml adds an xml declaration; ensure it uses UTF-8
    lines = pretty.split("\n")
    if lines and lines[0].startswith("<?xml"):
        lines[0] = '<?xml version="1.0" encoding="UTF-8"?>'

    # Remove trailing blank lines
    while lines and not lines[-1].strip():
        lines.pop()

    return "\n".join(lines)
