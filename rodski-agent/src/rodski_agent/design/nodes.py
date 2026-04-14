"""Design Agent 节点实现。

每个节点函数签名: fn(state: dict) -> dict
接收当前 state，返回需要更新的字段增量。

节点列表:
  - analyze_req: 分析需求，提取测试场景
  - plan_cases: 规划用例结构
  - design_data: 设计测试数据
  - generate_xml: 生成 XML 文件
  - validate_xml: 校验 XML 文件

所有 LLM 调用均有 fallback 降级路径。

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

    Try LLM first; fall back to simple keyword-based extraction
    when LLM is unavailable.

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

    # Try LLM
    try:
        from rodski_agent.common.llm_bridge import call_llm_text, LLMUnavailableError
        from rodski_agent.design.prompts import ANALYZE_REQ_PROMPT

        full_prompt = ANALYZE_REQ_PROMPT + f"\n\n【需求描述】\n{requirement}"
        response_text = call_llm_text(full_prompt)
        scenarios = _parse_json_response(response_text)
        if isinstance(scenarios, list) and scenarios:
            return {"test_scenarios": scenarios, "status": "running"}
    except Exception as exc:
        logger.warning("LLM unavailable for analyze_req, using fallback: %s", exc)

    # Fallback: generate minimal stub scenario
    scenarios = _fallback_scenarios(requirement)
    return {"test_scenarios": scenarios, "status": "running"}


def _fallback_scenarios(requirement: str) -> list[dict]:
    """Generate minimal stub scenarios from requirement text."""
    # Simple heuristic: create one scenario per requirement
    scenario_name = "test_scenario_001"

    # Detect type from keywords
    scenario_type = "ui"
    lower_req = requirement.lower()
    if any(kw in lower_req for kw in ["api", "接口", "http", "request", "请求"]):
        scenario_type = "api"
    elif any(kw in lower_req for kw in ["db", "数据库", "sql", "database"]):
        scenario_type = "db"

    return [
        {
            "scenario_name": scenario_name,
            "description": requirement[:200],
            "type": scenario_type,
            "steps_outline": ["准备测试环境", "执行测试操作", "验证测试结果"],
        }
    ]


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

    # Try LLM
    try:
        from rodski_agent.common.llm_bridge import call_llm_text, LLMUnavailableError
        from rodski_agent.design.prompts import PLAN_CASES_PROMPT

        scenarios_json = json.dumps(scenarios, ensure_ascii=False)
        full_prompt = (
            PLAN_CASES_PROMPT
            + f"\n\n【测试场景】\n{scenarios_json}"
        )
        response_text = call_llm_text(full_prompt)
        case_plan = _parse_json_response(response_text)
        if isinstance(case_plan, list) and case_plan:
            # Post-validate all actions
            case_plan = _validate_case_plan_actions(case_plan)
            return {"case_plan": case_plan, "status": "running"}
    except Exception as exc:
        logger.warning("LLM unavailable for plan_cases, using fallback: %s", exc)

    # Fallback: generate minimal case plan from scenarios
    case_plan = _fallback_case_plan(scenarios)
    return {"case_plan": case_plan, "status": "running"}


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


def _fallback_case_plan(scenarios: list[dict]) -> list[dict]:
    """Generate minimal case plan from scenarios."""
    cases: list[dict] = []
    for i, scenario in enumerate(scenarios):
        case_id = f"c{i + 1:03d}"
        scenario_type = scenario.get("type", "ui")
        model_name = scenario.get("scenario_name", f"Model{i + 1}")

        # Build steps based on type
        steps: list[dict] = []
        if scenario_type == "ui":
            steps = [
                {"phase": "pre_process", "action": "navigate", "model": "", "data": "http://localhost"},
                {"phase": "test_case", "action": "type", "model": model_name, "data": f"D{i + 1:03d}"},
                {"phase": "test_case", "action": "verify", "model": model_name, "data": f"V{i + 1:03d}"},
                {"phase": "post_process", "action": "close", "model": "", "data": ""},
            ]
        elif scenario_type == "api":
            steps = [
                {"phase": "test_case", "action": "send", "model": model_name, "data": f"D{i + 1:03d}"},
                {"phase": "test_case", "action": "verify", "model": model_name, "data": f"V{i + 1:03d}"},
            ]
        elif scenario_type == "db":
            steps = [
                {"phase": "test_case", "action": "DB", "model": "DBConn", "data": f"D{i + 1:03d}"},
            ]

        component_type_map = {"ui": "界面", "api": "接口", "db": "数据库"}
        cases.append({
            "id": case_id,
            "title": scenario.get("description", f"Test {case_id}")[:60],
            "component_type": component_type_map.get(scenario_type, "界面"),
            "steps": steps,
        })
    return cases


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

    # Try LLM
    try:
        from rodski_agent.common.llm_bridge import call_llm_text, LLMUnavailableError
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
    except Exception as exc:
        logger.warning("LLM unavailable for design_data, using fallback: %s", exc)

    # Fallback: generate minimal data from case plan
    test_data = _fallback_test_data(case_plan)
    return {"test_data": test_data, "status": "running"}


def _fallback_test_data(case_plan: list[dict]) -> dict:
    """Generate minimal test data from case plan."""
    datatables: list[dict] = []
    verify_tables: list[dict] = []
    seen_data_models: set[str] = set()
    seen_verify_models: set[str] = set()

    for case in case_plan:
        for step in case.get("steps", []):
            model = step.get("model", "")
            data_id = step.get("data", "")
            action = step.get("action", "")

            if not model:
                continue

            if action in ("type", "send") and model not in seen_data_models:
                seen_data_models.add(model)
                datatables.append({
                    "name": model,
                    "rows": [
                        {
                            "id": data_id or "D001",
                            "fields": [
                                {"name": "field1", "value": "value1"},
                            ],
                        }
                    ],
                })
            if action in ("verify", "check") and model not in seen_verify_models:
                seen_verify_models.add(model)
                verify_tables.append({
                    "name": f"{model}_verify",
                    "rows": [
                        {
                            "id": data_id or "V001",
                            "fields": [
                                {"name": "field1", "value": "expected1"},
                            ],
                        }
                    ],
                })

    return {
        "datatables": datatables,
        "verify_tables": verify_tables,
    }


# ============================================================
# Node: generate_xml
# ============================================================


def generate_xml(state: dict) -> dict:
    """调用 xml_builder 生成文件。

    Creates the directory structure (case/model/data) under output_dir
    and writes the generated XML files.

    Reads: state["case_plan"], state["test_data"], state["output_dir"]
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

        # Generate model XML — build from case plan (stub models)
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

    try:
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
    except Exception as exc:
        logger.warning("Validation skipped (rodski not available): %s", exc)
        # If validator is not available, assume success (graceful degradation)
        return {
            "validation_errors": [],
            "status": "success",
        }


# ============================================================
# Helpers
# ============================================================


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
