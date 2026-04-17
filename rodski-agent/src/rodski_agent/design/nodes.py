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
            designed_models = {
                m["name"]: m["elements"]
                for m in models_list
                if "name" in m and "elements" in m
            }
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
    )

    generated_files: list[str] = []

    try:
        # Create directory structure
        case_dir = os.path.join(output_dir, "case")
        model_dir = os.path.join(output_dir, "model")
        data_dir = os.path.join(output_dir, "data")

        for d in [case_dir, model_dir, data_dir]:
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
            models = [
                {"name": name, "elements": elements}
                for name, elements in designed_models.items()
            ]
        else:
            models = _extract_models_from_plan(case_plan, test_data)
        if models:
            model_xml = build_model_xml(models)
            model_file = os.path.join(model_dir, "model.xml")
            _write_file(model_file, model_xml)
            generated_files.append(model_file)

        # Generate data XML
        datatables = test_data.get("datatables", [])
        if datatables:
            data_xml = build_data_xml(datatables)
            data_file = os.path.join(data_dir, "data.xml")
            _write_file(data_file, data_xml)
            generated_files.append(data_file)

        # Generate verify data XML
        verify_tables = test_data.get("verify_tables", [])
        if verify_tables:
            verify_xml = build_verify_xml(verify_tables)
            verify_file = os.path.join(data_dir, "data_verify.xml")
            _write_file(verify_file, verify_xml)
            generated_files.append(verify_file)

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
    case_plan: list[dict], test_data: dict
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
    dt_map: dict[str, list[dict]] = {
        dt["name"]: dt.get("rows", []) for dt in datatables
    }

    for model_name in model_names:
        elements: list[dict] = []
        # Try to get field names from data
        rows = dt_map.get(model_name, [])
        field_names: list[str] = []
        if rows:
            for f in rows[0].get("fields", []):
                fn = f.get("name", "")
                if fn and fn not in field_names:
                    field_names.append(fn)

        if not field_names:
            field_names = ["field1"]

        for fn in field_names:
            elements.append({
                "name": fn,
                "type": "web",
                "locators": [{"type": "css", "value": f"#{fn}"}],
            })

        models.append({"name": model_name, "elements": elements})

    return models


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
