"""Design Agent 节点实现。

每个节点函数签名: fn(state: dict) -> dict
接收当前 state，返回需要更新的字段增量。

节点列表:
  - analyze_req: 分析需求，提取测试场景
  - plan_cases: 规划用例结构
  - design_data: 设计测试数据
  - generate_xml: 生成 XML 文件
  - validate_xml: 校验 XML 文件

LLM 不可用时直接报错，不做降级。

Python 3.9 兼容：使用 ``from __future__ import annotations`` 延迟求值。
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from rodski_agent.common.rodski_knowledge import (
    validate_action,
    REQUIRED_DIRS,
)

logger = logging.getLogger(__name__)


# ============================================================
# Node: analyze_req
# ============================================================


def analyze_req(state: dict) -> dict:
    """LLM 分析需求 -> test_scenarios.

    Reads: state["requirement"]
    Writes: state["test_scenarios"]
    """
    requirement = state.get("requirement", "")
    if not requirement:
        return {
            "test_scenarios": [],
            "status": "error",
            "error": "No requirement provided",
        }

    from rodski_agent.common.llm_bridge import call_llm_text
    from rodski_agent.design.prompts import ANALYZE_REQ_PROMPT

    full_prompt = ANALYZE_REQ_PROMPT + f"\n\n【需求描述】\n{requirement}"
    response_text = call_llm_text(full_prompt)
    scenarios = _parse_json_response(response_text)
    if isinstance(scenarios, list) and scenarios:
        return {"test_scenarios": scenarios, "status": "running"}

    return {
        "test_scenarios": [],
        "status": "error",
        "error": "LLM returned invalid scenarios format",
    }


# ============================================================
# Node: plan_cases
# ============================================================


def plan_cases(state: dict) -> dict:
    """LLM 规划用例 -> case_plan. Post-validate all actions.

    Reads: state["test_scenarios"]
    Writes: state["case_plan"]
    """
    scenarios = state.get("test_scenarios", [])
    if not scenarios:
        return {
            "case_plan": [],
            "status": "error",
            "error": "No test scenarios to plan",
        }

    from rodski_agent.common.llm_bridge import call_llm_text
    from rodski_agent.design.prompts import PLAN_CASES_PROMPT

    scenarios_json = json.dumps(scenarios, ensure_ascii=False)
    full_prompt = (
        PLAN_CASES_PROMPT
        + f"\n\n【测试场景】\n{scenarios_json}"
    )
    response_text = call_llm_text(full_prompt)
    case_plan = _parse_json_response(response_text)
    if isinstance(case_plan, list) and case_plan:
        case_plan = _validate_case_plan_actions(case_plan)
        return {"case_plan": case_plan, "status": "running"}

    return {
        "case_plan": [],
        "status": "error",
        "error": "LLM returned invalid case plan format",
    }


def _validate_case_plan_actions(case_plan: list[dict]) -> list[dict]:
    """Post-validate all actions in case plan. Remove invalid actions."""
    validated: list[dict] = []
    for case in case_plan:
        valid_steps: list[dict] = []
        for step in case.get("steps", []):
            action = step.get("action", "")
            if validate_action(action):
                valid_steps.append(step)
            else:
                logger.warning(
                    "Removed invalid action '%s' from case '%s'",
                    action,
                    case.get("id", "?"),
                )
        if valid_steps:
            case["steps"] = valid_steps
            validated.append(case)
    return validated


MOBILE_ALLOWED_ACTIONS = {"navigate", "type", "verify", "run", "close"}
MOBILE_FORBIDDEN_CASE_ACTIONS = {
    "swipe",
    "long_press",
    "press_keycode",
    "hide_keyboard",
    "tap",
    "click",
    "double_click",
    "right_click",
    "hover",
    "select",
    "key_press",
    "drag",
    "scroll",
}
MOBILE_DRIVER_TYPES = {"android", "ios"}


# ============================================================
# Node: design_data
# ============================================================


def design_data(state: dict) -> dict:
    """LLM 设计数据 -> test_data. Post-validate field consistency.

    Reads: state["case_plan"]
    Writes: state["test_data"]
    """
    case_plan = state.get("case_plan", [])
    if not case_plan:
        return {
            "test_data": {},
            "status": "error",
            "error": "No case plan to design data for",
        }

    from rodski_agent.common.llm_bridge import call_llm_text
    from rodski_agent.design.prompts import DESIGN_DATA_PROMPT

    case_plan_json = json.dumps(case_plan, ensure_ascii=False)
    full_prompt = (
        DESIGN_DATA_PROMPT
        + f"\n\n【用例计划】\n{case_plan_json}"
    )
    response_text = call_llm_text(full_prompt)
    test_data = _parse_json_response(response_text)
    if isinstance(test_data, dict) and test_data:
        return {"test_data": test_data, "status": "running"}

    return {
        "test_data": {},
        "status": "error",
        "error": "LLM returned invalid test data format",
    }


# ============================================================
# Node: design_model
# ============================================================


def design_model(state: dict) -> dict:
    """LLM 推断模型元素和 locator -> designed_models.

    Reads: state["case_plan"], state.get("skill_context")
    Writes: state["designed_models"]
    Falls back silently on LLM failure.
    """
    case_plan = state.get("case_plan", [])
    if not case_plan:
        return {"designed_models": {}}

    model_names: list[str] = []
    seen: set[str] = set()
    for case in case_plan:
        for step in case.get("steps", []):
            name = step.get("model", "")
            if name and name not in seen:
                model_names.append(name)
                seen.add(name)

    if not model_names:
        return {"designed_models": {}}

    try:
        from rodski_agent.common.llm_bridge import call_llm_text
        from rodski_agent.design.prompts import DESIGN_MODEL_PROMPT

        skill_context = state.get("skill_context", "")
        context_section = f"\n\n【流程描述】\n{skill_context}" if skill_context else ""
        full_prompt = (
            DESIGN_MODEL_PROMPT
            + f"\n\n【需要设计的模型】\n{json.dumps(model_names, ensure_ascii=False)}"
            + context_section
        )
        response_text = call_llm_text(full_prompt)
        models_list = _parse_json_response(response_text)
        if isinstance(models_list, list) and models_list:
            designed_models = {}
            for model in models_list:
                if "name" not in model or "elements" not in model:
                    continue
                metadata_keys = {"driver_type", "model_type", "category"}
                if any(key in model for key in metadata_keys):
                    model_def = dict(model)
                    model_def.pop("name", None)
                    designed_models[model["name"]] = model_def
                else:
                    designed_models[model["name"]] = model["elements"]
            return {"designed_models": designed_models}
    except Exception:
        logger.warning("design_model LLM call failed, falling back to stub", exc_info=True)

    return {"designed_models": {}}


# ============================================================
# Node: generate_xml
# ============================================================


def generate_xml(state: dict) -> dict:
    """调用 xml_builder 生成文件。

    Creates the directory structure (case/model/data) under output_dir
    and writes the generated XML files.

    Reads: state["case_plan"], state["test_data"], state["output_dir"],
           state.get("debug_hints")
    Writes: state["generated_files"]
    """
    output_dir = state.get("output_dir", "")
    if not output_dir:
        return {
            "status": "error",
            "error": "No output_dir specified",
        }

    case_plan = state.get("case_plan", [])
    test_data = state.get("test_data", {})
    mobile_mode = _is_mobile_app_mode(state)

    # If debug_hints are present, regenerate case_plan via LLM with hints appended
    debug_hints = state.get("debug_hints")
    if debug_hints:
        try:
            from rodski_agent.common.llm_bridge import call_llm_text
            from rodski_agent.design.prompts import PLAN_CASES_PROMPT

            hints_text = json.dumps(debug_hints, ensure_ascii=False, indent=2)
            scenarios = state.get("test_scenarios", [])
            full_prompt = (
                PLAN_CASES_PROMPT
                + f"\n\n【测试场景】\n{json.dumps(scenarios, ensure_ascii=False)}"
                + f"\n\n【调试建议（请根据以下建议修正用例）】\n{hints_text}"
            )
            response_text = call_llm_text(full_prompt)
            new_plan = _parse_json_response(response_text)
            if isinstance(new_plan, list) and new_plan:
                case_plan = _validate_case_plan_actions(new_plan)
        except Exception:
            logger.warning("generate_xml: debug hint re-plan failed, using existing case_plan", exc_info=True)

    from rodski_agent.common.xml_builder import (
        build_case_xml,
        build_model_xml,
        build_data_xml,
        build_verify_xml,
        build_globalvalue_xml,
        build_plan_xml,
        write_data_sqlite,
    )

    generated_files: list[str] = []

    try:
        if mobile_mode:
            driver_type = _mobile_driver_type(state)
            if not driver_type:
                return {
                    "generated_files": generated_files,
                    "validation_errors": [
                        "Mobile App generation requires explicit platform: android or ios"
                    ],
                    "status": "error",
                    "error": "Mobile App generation requires explicit platform: android or ios",
                }
            case_plan = _normalize_mobile_case_plan(case_plan, state)
            test_data = _normalize_mobile_test_data(case_plan, test_data)

        # Create directory structure
        case_dir = os.path.join(output_dir, "case")
        model_dir = os.path.join(output_dir, "model")
        data_dir = os.path.join(output_dir, "data")
        plan_dir = os.path.join(output_dir, "plan")

        module_dirs = [case_dir, model_dir, data_dir]
        if mobile_mode:
            module_dirs.extend([
                os.path.join(output_dir, "fun"),
                plan_dir,
                os.path.join(output_dir, "result"),
            ])

        for d in module_dirs:
            os.makedirs(d, exist_ok=True)

        # Generate case XML
        if case_plan:
            case_xml = build_case_xml(case_plan)
            case_file = os.path.join(case_dir, "test_case.xml")
            _write_file(case_file, case_xml)
            generated_files.append(case_file)

        # Generate model XML — prefer LLM-designed models, fallback to stub
        designed_models = state.get("designed_models") or {}
        if designed_models:
            models = []
            for name, elements in designed_models.items():
                model_def = dict(elements) if isinstance(elements, dict) else {"name": name, "elements": elements}
                model_def.setdefault("name", name)
                models.append(_normalize_model_definition(model_def, state, mobile_mode))
        else:
            models = _extract_models_from_plan(case_plan, test_data, state=state, mobile_mode=mobile_mode)
        if models:
            model_xml = build_model_xml(models)
            model_file = os.path.join(model_dir, "model.xml")
            _write_file(model_file, model_xml)
            generated_files.append(model_file)

        datatables = test_data.get("datatables", [])
        verify_tables = test_data.get("verify_tables", [])
        if mobile_mode:
            test_data = _align_mobile_test_data_to_models(test_data, models)
            datatables = test_data.get("datatables", [])
            verify_tables = test_data.get("verify_tables", [])
            if datatables or verify_tables:
                sqlite_file = os.path.join(data_dir, "data.sqlite")
                write_data_sqlite(sqlite_file, datatables, verify_tables)
                generated_files.append(sqlite_file)
            globalvalue_xml = build_globalvalue_xml(_build_mobile_globalvalue_groups(state, case_plan))
            globalvalue_file = os.path.join(data_dir, "globalvalue.xml")
            _write_file(globalvalue_file, globalvalue_xml)
            generated_files.append(globalvalue_file)
        elif datatables:
            data_xml = build_data_xml(datatables)
            data_file = os.path.join(data_dir, "data.xml")
            _write_file(data_file, data_xml)
            generated_files.append(data_file)

        if not mobile_mode and verify_tables:
            verify_xml = build_verify_xml(verify_tables)
            verify_file = os.path.join(data_dir, "data_verify.xml")
            _write_file(verify_file, verify_xml)
            generated_files.append(verify_file)

        if mobile_mode and case_plan:
            plan_xml = build_plan_xml(
                case_plan,
                plan_id="project_full",
                title="Mobile App Full Plan",
                execute="是",
                default_execute="是",
            )
            plan_file = os.path.join(plan_dir, "project_full.xml")
            _write_file(plan_file, plan_xml)
            generated_files.append(plan_file)

        return {
            "generated_files": generated_files,
            "status": "running",
        }

    except (ValueError, OSError) as exc:
        logger.error("XML generation failed: %s", exc)
        fix_attempt = state.get("fix_attempt", 0)
        return {
            "generated_files": generated_files,
            "validation_errors": [str(exc)],
            "fix_attempt": fix_attempt + 1,
            "status": "running",
        }


def _extract_models_from_plan(
    case_plan: list[dict], test_data: dict, state: dict | None = None, mobile_mode: bool = False
) -> list[dict]:
    """Extract model definitions from case plan and test data.

    Builds stub models: each unique model name in the case plan
    gets an element list derived from the data tables.
    """
    model_names: list[str] = []
    seen: set[str] = set()
    for case in case_plan:
        for step in case.get("steps", []):
            name = step.get("model", "")
            if name and name not in seen:
                model_names.append(name)
                seen.add(name)

    models: list[dict] = []
    datatables = test_data.get("datatables", [])
    verify_tables = test_data.get("verify_tables", [])
    dt_map: dict[str, list[dict]] = {
        dt["name"]: dt.get("rows", []) for dt in datatables
    }
    verify_map: dict[str, list[dict]] = {
        vt["name"][:-len("_verify")]: vt.get("rows", []) for vt in verify_tables if vt.get("name", "").endswith("_verify")
    }

    for model_name in model_names:
        elements: list[dict] = []
        # Try to get field names from data
        rows = dt_map.get(model_name, []) + verify_map.get(model_name, [])
        field_names: list[str] = []
        if rows:
            for f in rows[0].get("fields", []):
                fn = f.get("name", "")
                if fn and fn not in field_names:
                    field_names.append(fn)

        if not field_names:
            field_names = ["field1"]

        for fn in field_names:
            locator_type = "id" if mobile_mode else "css"
            locator_value = f"com.example:id/{fn}" if mobile_mode else f"#{fn}"
            elements.append({
                "name": fn,
                "type": "input",
                "locators": [{"type": locator_type, "value": locator_value}],
            })

        model = {"name": model_name, "elements": elements}
        models.append(_normalize_model_definition(model, state or {}, mobile_mode))

    return models


def _is_mobile_app_mode(state: dict) -> bool:
    mode = str(state.get("mode") or state.get("target_type") or state.get("platform") or "").lower()
    if mode in {"mobile", "mobile_app", "app", "android", "ios"}:
        return True
    target_url = str(state.get("target_url") or state.get("app_target") or "").lower()
    if target_url.startswith("app://android/") or target_url.startswith("app://ios/"):
        return True
    requirement = str(state.get("requirement") or "").lower()
    mobile_tokens = ("android", "ios", "移动端", "手机", "app ", "app登录", "原生app")
    if any(token in requirement for token in mobile_tokens):
        return True
    designed_models = state.get("designed_models") or {}
    for model_def in designed_models.values():
        if isinstance(model_def, dict):
            driver_type = str(model_def.get("driver_type", "")).lower()
            elements = model_def.get("elements", [])
        else:
            driver_type = ""
            elements = model_def
        if driver_type in MOBILE_DRIVER_TYPES:
            return True
        for element in elements or []:
            if str(element.get("type", "")).lower() in MOBILE_DRIVER_TYPES:
                return True
    return False


def _mobile_driver_type(state: dict) -> str:
    for key in ("driver_type", "platform", "target_type", "mode"):
        value = str(state.get(key, "")).lower()
        if value in MOBILE_DRIVER_TYPES:
            return value
    target_url = str(state.get("target_url") or state.get("app_target") or "").lower()
    if target_url.startswith("app://android/"):
        return "android"
    if target_url.startswith("app://ios/"):
        return "ios"
    requirement = str(state.get("requirement") or "").lower()
    if "android" in requirement or "安卓" in requirement:
        return "android"
    if "ios" in requirement or "iphone" in requirement:
        return "ios"
    designed_models = state.get("designed_models") or {}
    for model_def in designed_models.values():
        if isinstance(model_def, dict):
            driver_type = str(model_def.get("driver_type", "")).lower()
            if driver_type in MOBILE_DRIVER_TYPES:
                return driver_type
            elements = model_def.get("elements", [])
        else:
            elements = model_def
        for element in elements or []:
            element_type = str(element.get("type", "")).lower()
            if element_type in MOBILE_DRIVER_TYPES:
                return element_type
    return ""


def _mobile_app_target(state: dict) -> str:
    target = str(state.get("app_target") or state.get("target_url") or "").strip()
    if target.startswith(("app://android/", "app://ios/", "GlobalValue.")):
        return target
    driver_type = _mobile_driver_type(state)
    if not driver_type:
        return ""
    return f"app://{driver_type}/com.example/.MainActivity"


def _normalize_mobile_case_plan(case_plan: list[dict], state: dict) -> list[dict]:
    app_target = _mobile_app_target(state)
    normalized_cases: list[dict] = []
    for case in case_plan:
        new_case = dict(case)
        steps = []
        has_navigate = False
        for step in case.get("steps", []):
            action = step.get("action", "")
            if action in MOBILE_FORBIDDEN_CASE_ACTIONS:
                continue
            if action not in MOBILE_ALLOWED_ACTIONS:
                continue
            new_step = dict(step)
            if action == "navigate":
                new_step["model"] = ""
                new_step["data"] = new_step.get("data") or "GlobalValue.Mobile.AppTarget"
                has_navigate = True
            steps.append(new_step)

        if not has_navigate:
            steps.insert(0, {
                "phase": "pre_process",
                "action": "navigate",
                "model": "",
                "data": "GlobalValue.Mobile.AppTarget" if app_target else _mobile_app_target(state),
            })

        if not any(step.get("phase", "test_case") == "test_case" for step in steps):
            model_name = _first_model_name(case_plan) or "AppScreen"
            steps.append({"phase": "test_case", "action": "type", "model": model_name, "data": "L001"})

        if not any(step.get("action") == "close" for step in steps):
            steps.append({"phase": "post_process", "action": "close", "model": "", "data": ""})

        new_case["component_type"] = new_case.get("component_type") or "界面"
        new_case["steps"] = steps
        normalized_cases.append(new_case)
    return normalized_cases


def _normalize_mobile_test_data(case_plan: list[dict], test_data: dict) -> dict:
    normalized = {
        "datatables": list(test_data.get("datatables", [])),
        "verify_tables": list(test_data.get("verify_tables", [])),
    }
    table_names = {table.get("name") for table in normalized["datatables"]}
    verify_names = {table.get("name") for table in normalized["verify_tables"]}

    for case in case_plan:
        for step in case.get("steps", []):
            model_name = step.get("model", "")
            data_id = step.get("data", "")
            if not model_name or not data_id or data_id.startswith("GlobalValue."):
                continue
            if step.get("action") == "type" and model_name not in table_names:
                normalized["datatables"].append({
                    "name": model_name,
                    "rows": [{"id": data_id, "fields": [{"name": "primary_action", "value": "click"}]}],
                })
                table_names.add(model_name)
            if step.get("action") == "verify":
                verify_name = f"{model_name}_verify"
                if verify_name not in verify_names:
                    normalized["verify_tables"].append({
                        "name": verify_name,
                        "rows": [{"id": data_id, "fields": [{"name": "status_text", "value": "OK"}]}],
                    })
                    verify_names.add(verify_name)
    return normalized


def _normalize_model_definition(model: dict, state: dict, mobile_mode: bool) -> dict:
    if not mobile_mode:
        return model
    normalized = dict(model)
    normalized["model_type"] = normalized.get("model_type", "ui")
    normalized["driver_type"] = normalized.get("driver_type") or _mobile_driver_type(state)
    elements = []
    for element in normalized.get("elements", []):
        elem = dict(element)
        if str(elem.get("type", "")).lower() in MOBILE_DRIVER_TYPES:
            elem["type"] = "input"
        elem.setdefault("type", "input")
        locators = []
        for locator in elem.get("locators", []):
            loc_type = locator.get("type", "")
            if loc_type == "accessibility_id":
                loc_type = "name"
            locators.append({"type": loc_type, "value": locator.get("value", "")})
        if not locators:
            locators = [{"type": "id", "value": f"com.example:id/{elem.get('name', 'element')}"}]
        elem["locators"] = locators
        elements.append(elem)
    normalized["elements"] = elements
    return normalized


def _align_mobile_test_data_to_models(test_data: dict, models: list[dict]) -> dict:
    model_fields = {
        model.get("name", ""): [
            element.get("name", "")
            for element in model.get("elements", [])
            if element.get("name")
        ]
        for model in models
    }

    datatables = [
        _align_table_fields(table, model_fields.get(table.get("name", ""), []), "BLANK")
        for table in test_data.get("datatables", [])
    ]
    verify_tables = []
    for table in test_data.get("verify_tables", []):
        table_name = table.get("name", "")
        model_name = table_name[:-len("_verify")] if table_name.endswith("_verify") else table_name
        verify_tables.append(_align_table_fields(table, model_fields.get(model_name, []), "BLANK"))
    return {"datatables": datatables, "verify_tables": verify_tables}


def _align_table_fields(table: dict, field_names: list[str], default_value: str) -> dict:
    if not field_names:
        return table
    aligned = dict(table)
    rows = []
    for row in table.get("rows", []):
        row_copy = dict(row)
        existing = {
            field.get("name", ""): str(field.get("value", ""))
            for field in row.get("fields", [])
            if field.get("name")
        }
        row_copy["fields"] = [
            {"name": field_name, "value": existing.get(field_name, default_value)}
            for field_name in field_names
        ]
        rows.append(row_copy)
    aligned["rows"] = rows
    return aligned


def _build_mobile_globalvalue_groups(state: dict, case_plan: list[dict]) -> list[dict]:
    app_target = _mobile_app_target(state)
    for case in case_plan:
        for step in case.get("steps", []):
            if step.get("action") == "navigate" and str(step.get("data", "")).startswith("app://"):
                app_target = step["data"]
    driver_type = _mobile_driver_type(state)
    return [{
        "name": "Mobile",
        "vars": [
            {"name": "Platform", "value": driver_type},
            {"name": "AppTarget", "value": app_target},
        ],
    }]


def _first_model_name(case_plan: list[dict]) -> str:
    for case in case_plan:
        for step in case.get("steps", []):
            model_name = step.get("model", "")
            if model_name:
                return model_name
    return ""


def _write_file(path: str, content: str) -> None:
    """Write content to file."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# ============================================================
# Node: validate_xml
# ============================================================


def validate_xml(state: dict) -> dict:
    """调用 rodski validate 校验生成的 XML 文件。

    If errors: increment fix_attempt, store validation_errors.
    If pass: status = "success".

    Reads: state["output_dir"], state["generated_files"], state["fix_attempt"]
    Writes: state["validation_errors"], state["fix_attempt"], state["status"]
    """
    output_dir = state.get("output_dir", "")
    if not output_dir:
        return {"status": "error", "error": "No output_dir for validation"}

    generated_files = state.get("generated_files", [])
    if not generated_files:
        return {"status": "error", "error": "No files to validate"}

    fix_attempt = state.get("fix_attempt", 0)

    from rodski_agent.common.rodski_tools import rodski_validate

    result = rodski_validate(output_dir)
    if result.success:
        return {
            "validation_errors": [],
            "status": "success",
        }
    else:
        errors = [e for e in result.stderr.split("\n") if e.strip()]
        return {
            "validation_errors": errors,
            "fix_attempt": fix_attempt + 1,
            "status": "running",
        }


# ============================================================
# Helpers
# ============================================================


# ============================================================
# Node: gap_analysis
# ============================================================


def gap_analysis(state: dict) -> dict:
    """扫描 output_dir 下已有资产，对比 case_plan 中引用的 model/data，生成 gap_report。

    Reads: state["case_plan"], state["output_dir"]
    Writes: state["gap_report"]
    """
    import xml.etree.ElementTree as ET

    case_plan = state.get("case_plan", [])
    output_dir = state.get("output_dir", "")

    # 1. 从 case_plan 提取引用的 model 名和 data 表名
    ref_models: set[str] = set()
    ref_data: set[str] = set()
    for case in case_plan:
        for step in case.get("steps", []):
            model = step.get("model", "")
            if model:
                ref_models.add(model)
            data = step.get("data", "")
            if data and "." in data:
                ref_data.add(data.split(".")[0])

    # 2. 扫描 output_dir 中已有资产
    existing_models: set[str] = set()
    existing_data: set[str] = set()

    if output_dir:
        model_file = Path(output_dir) / "model" / "model.xml"
        if model_file.exists():
            try:
                tree = ET.parse(str(model_file))
                for elem in tree.getroot().findall("model"):
                    name = elem.get("name", "")
                    if name:
                        existing_models.add(name)
            except ET.ParseError as exc:
                logger.warning("Failed to parse model.xml: %s", exc)

        data_dir = Path(output_dir) / "data"
        if data_dir.exists():
            for xml_file in data_dir.glob("*.xml"):
                try:
                    tree = ET.parse(str(xml_file))
                    for dt in tree.getroot().findall("datatable"):
                        name = dt.get("name", "")
                        if name:
                            existing_data.add(name)
                except ET.ParseError as exc:
                    logger.warning("Failed to parse %s: %s", xml_file, exc)

    # 3. 计算差异
    gap_report = {
        "missing_models": sorted(ref_models - existing_models),
        "missing_data": sorted(ref_data - existing_data),
        "reusable_models": sorted(ref_models & existing_models),
        "reusable_data": sorted(existing_data),
    }

    return {"gap_report": gap_report}


def _parse_json_response(text: str) -> Any:
    """Parse JSON from LLM response, handling markdown code blocks."""
    stripped = text.strip()

    # Try extracting from markdown code block
    if "```json" in stripped:
        start = stripped.index("```json") + len("```json")
        end = stripped.index("```", start)
        stripped = stripped[start:end].strip()
    elif "```" in stripped:
        start = stripped.index("```") + len("```")
        end = stripped.index("```", start)
        stripped = stripped[start:end].strip()

    return json.loads(stripped)
