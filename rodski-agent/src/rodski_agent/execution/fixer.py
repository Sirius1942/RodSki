"""智能修复策略 — 根据诊断结果自动修复测试用例。

当 retry_decide 决定重试时，apply_fix 负责分析诊断结果并应用修复策略：
  - 超时问题：在失败步骤前插入 wait 步骤（修改 case XML）
  - 元素定位问题：更新 model XML 中的 locator（LLM 辅助，降级只记录）
  - 数据问题：更新 data XML 中的测试数据值

所有修复操作均创建备份文件（.bak）以便回滚。

Python 3.9 兼容：使用 ``from __future__ import annotations`` 延迟求值。
"""

from __future__ import annotations

import logging
import os
import shutil
import xml.etree.ElementTree as ET
from typing import Any, Optional

from rodski_agent.common.rodski_knowledge import validate_action, validate_locator_type

logger = logging.getLogger(__name__)


# ==================================================================
# 主入口
# ==================================================================


def apply_fix(state: dict) -> dict:
    """应用修复策略。

    根据 diagnosis 中的 category/root_cause/suggestion 选择修复策略，
    将修复记录追加到 fixes_applied 列表。

    修复策略选择优先级：
    1. timeout/超时 → 插入 wait 步骤
    2. element/元素/locator → 尝试修复 locator
    3. data/数据 → 尝试修复测试数据

    Parameters
    ----------
    state : dict
        当前执行状态，需包含 ``diagnosis`` 和 ``case_path`` 字段。

    Returns
    -------
    dict
        ``{"fixes_applied": [...], "status": "running"}``
    """
    diagnosis = state.get("diagnosis", {})
    suggestion = diagnosis.get("suggestion", "")
    root_cause = diagnosis.get("root_cause", "")
    category = diagnosis.get("category", "")
    fixes = list(state.get("fixes_applied", []))
    case_path = state.get("case_path", "")

    cause_lower = root_cause.lower()

    # Strategy 1: Add wait for timeout issues
    if "timeout" in cause_lower or "超时" in root_cause:
        fix_desc = _apply_wait_fix(case_path, diagnosis)
        if fix_desc:
            fixes.append(fix_desc)

    # Strategy 2: Fix locator in model XML
    elif "element" in cause_lower or "元素" in root_cause or "locator" in cause_lower or "定位" in root_cause:
        fix_desc = _apply_locator_fix(case_path, diagnosis)
        if fix_desc:
            fixes.append(fix_desc)

    # Strategy 3: Fix data values
    elif "data" in cause_lower or "数据" in root_cause or "value" in cause_lower or "值" in root_cause:
        fix_desc = _apply_data_fix(case_path, diagnosis)
        if fix_desc:
            fixes.append(fix_desc)

    return {"fixes_applied": fixes, "status": "running"}


# ==================================================================
# Strategy 1: Wait fix — 在失败步骤前插入 wait
# ==================================================================


def _apply_wait_fix(case_path: str, diagnosis: dict) -> str | None:
    """在失败步骤前插入 wait 步骤。

    如果 case_path 是有效的目录/文件且包含 case XML，
    尝试在第一个 test_case phase 步骤前插入 wait 步骤。

    Parameters
    ----------
    case_path : str
        用例路径（目录或文件）。
    diagnosis : dict
        诊断结果。

    Returns
    -------
    str | None
        修复描述，或 None（如果无法修复）。
    """
    if not validate_action("wait"):
        return None

    case_files = _find_case_xml_files(case_path)
    if not case_files:
        return "added_wait: wait 3s before failed step (no XML found to modify)"

    # Try to modify the first case file
    target_file = case_files[0]
    modified = _insert_wait_step(target_file, wait_seconds=3)
    if modified:
        return f"added_wait: inserted wait 3s step in {os.path.basename(target_file)}"
    return "added_wait: wait 3s before failed step (XML modification skipped)"


def _insert_wait_step(case_file: str, wait_seconds: int = 3) -> bool:
    """在 case XML 的第一个 test_case step 前插入 wait 步骤。

    Parameters
    ----------
    case_file : str
        Case XML 文件路径。
    wait_seconds : int
        等待秒数。

    Returns
    -------
    bool
        是否成功修改。
    """
    try:
        tree = ET.parse(case_file)
        root = tree.getroot()

        # Find testcase elements (may be nested in suite/testcases)
        testcases = root.findall(".//testcase")
        if not testcases:
            testcases = root.findall(".//case")
        if not testcases:
            return False

        modified = False
        for tc in testcases:
            steps = tc.findall("step")
            if not steps:
                continue

            # Find first test_case step
            insert_idx = 0
            for i, step in enumerate(steps):
                phase = step.get("phase", step.findtext("phase", ""))
                if phase == "test_case" or (not phase and i > 0):
                    insert_idx = i
                    break

            # Create wait step element
            wait_step = ET.Element("step")
            action_elem = ET.SubElement(wait_step, "action")
            action_elem.text = "wait"
            data_elem = ET.SubElement(wait_step, "data")
            data_elem.text = str(wait_seconds)

            # Backup and insert
            _backup_file(case_file)
            tc.insert(insert_idx if insert_idx > 0 else len(steps), wait_step)
            modified = True

        if modified:
            tree.write(case_file, encoding="unicode", xml_declaration=True)
        return modified

    except Exception as exc:
        logger.warning("Failed to insert wait step in %s: %s", case_file, exc)
        return False


# ==================================================================
# Strategy 2: Locator fix — 修复 model XML 中的 locator
# ==================================================================


def _apply_locator_fix(case_path: str, diagnosis: dict) -> str | None:
    """修复 model XML 中的定位器。

    优先通过 LLM 获取修复建议，降级时仅记录修复建议。

    Parameters
    ----------
    case_path : str
        用例路径。
    diagnosis : dict
        诊断结果，suggestion 中应包含新的定位器信息。

    Returns
    -------
    str | None
        修复描述。
    """
    suggestion = diagnosis.get("suggestion", "")
    root_cause = diagnosis.get("root_cause", "")

    model_files = _find_model_xml_files(case_path)
    if not model_files:
        return f"locator_fix_suggested: {suggestion}"

    # Try LLM-based locator fix
    fix_result = _llm_locator_fix(model_files[0], root_cause, suggestion)
    if fix_result:
        return fix_result

    # Fallback: just record the suggestion
    return f"locator_fix_suggested: {suggestion}"


def _llm_locator_fix(model_file: str, root_cause: str, suggestion: str) -> str | None:
    """通过 LLM 获取新的 locator 值并修改 model XML。

    Parameters
    ----------
    model_file : str
        Model XML 文件路径。
    root_cause : str
        诊断的根本原因。
    suggestion : str
        修复建议。

    Returns
    -------
    str | None
        修复描述，或 None（如果 LLM 不可用或修复失败）。
    """
    try:
        from rodski_agent.common.llm_bridge import call_llm_text
    except ImportError:
        return None

    try:
        with open(model_file, "r", encoding="utf-8") as f:
            model_content = f.read()
    except Exception:
        return None

    prompt = f"""\
以下是测试用例的 model XML 文件内容，其中一个元素定位器失效。
请分析问题并建议修复。

Model XML:
{model_content}

失败原因: {root_cause}
修复建议: {suggestion}

请输出一行 JSON：{{"element_name": "失效的元素名", "locator_type": "新定位类型", "locator_value": "新定位值"}}
只输出 JSON，不要解释。"""

    try:
        response = call_llm_text(prompt, agent_type="execution")
        import json
        text = response.strip()
        if "```" in text:
            start = text.index("```") + 3
            if text[start:].startswith("json"):
                start += 4
            end = text.index("```", start)
            text = text[start:end].strip()

        fix_data = json.loads(text)
        elem_name = fix_data.get("element_name", "")
        loc_type = fix_data.get("locator_type", "")
        loc_value = fix_data.get("locator_value", "")

        if not elem_name or not loc_type or not loc_value:
            return None

        if not validate_locator_type(loc_type):
            return None

        # Apply the fix
        applied = _update_model_locator(model_file, elem_name, loc_type, loc_value)
        if applied:
            return f"locator_fixed: {elem_name} → {loc_type}={loc_value} in {os.path.basename(model_file)}"
        return None

    except Exception as exc:
        logger.warning("LLM locator fix failed: %s", exc)
        return None


def _update_model_locator(
    model_file: str,
    element_name: str,
    locator_type: str,
    locator_value: str,
) -> bool:
    """更新 model XML 中指定元素的 locator。

    Parameters
    ----------
    model_file : str
        Model XML 文件路径。
    element_name : str
        要修复的元素名称。
    locator_type : str
        新的定位类型。
    locator_value : str
        新的定位值。

    Returns
    -------
    bool
        是否成功修改。
    """
    try:
        tree = ET.parse(model_file)
        root = tree.getroot()

        # Find element by name attribute or text content
        modified = False
        for elem in root.iter():
            name = elem.get("name", "") or elem.findtext("name", "")
            if name == element_name:
                # Look for location sub-elements
                for loc in elem.findall("location"):
                    current_type = loc.get("type", "")
                    if current_type == locator_type or not modified:
                        loc.set("type", locator_type)
                        loc.text = locator_value
                        modified = True
                        break

                # If no location found, create one
                if not modified:
                    loc_elem = ET.SubElement(elem, "location")
                    loc_elem.set("type", locator_type)
                    loc_elem.text = locator_value
                    modified = True
                break

        if modified:
            _backup_file(model_file)
            tree.write(model_file, encoding="unicode", xml_declaration=True)
        return modified

    except Exception as exc:
        logger.warning("Failed to update locator in %s: %s", model_file, exc)
        return False


# ==================================================================
# Strategy 3: Data fix — 修复 data XML 中的数据值
# ==================================================================


def _apply_data_fix(case_path: str, diagnosis: dict) -> str | None:
    """修复 data XML 中的测试数据。

    分析诊断结果，尝试更新不正确的数据值。

    Parameters
    ----------
    case_path : str
        用例路径。
    diagnosis : dict
        诊断结果。

    Returns
    -------
    str | None
        修复描述。
    """
    suggestion = diagnosis.get("suggestion", "")
    root_cause = diagnosis.get("root_cause", "")

    data_files = _find_data_xml_files(case_path)
    if not data_files:
        return f"data_fix_suggested: {suggestion}"

    # Try LLM-based data fix
    fix_result = _llm_data_fix(data_files[0], root_cause, suggestion)
    if fix_result:
        return fix_result

    return f"data_fix_suggested: {suggestion}"


def _llm_data_fix(data_file: str, root_cause: str, suggestion: str) -> str | None:
    """通过 LLM 获取修复后的数据值并修改 data XML。

    Returns
    -------
    str | None
        修复描述，或 None。
    """
    try:
        from rodski_agent.common.llm_bridge import call_llm_text
    except ImportError:
        return None

    try:
        with open(data_file, "r", encoding="utf-8") as f:
            data_content = f.read()
    except Exception:
        return None

    prompt = f"""\
以下是测试用例的 data XML 文件，其中某些数据值导致测试失败。
请分析并建议修复。

Data XML:
{data_content}

失败原因: {root_cause}
修复建议: {suggestion}

请输出一行 JSON：{{"field_name": "字段名", "old_value": "旧值", "new_value": "新值"}}
只输出 JSON，不要解释。"""

    try:
        response = call_llm_text(prompt, agent_type="execution")
        import json
        text = response.strip()
        if "```" in text:
            start = text.index("```") + 3
            if text[start:].startswith("json"):
                start += 4
            end = text.index("```", start)
            text = text[start:end].strip()

        fix_data = json.loads(text)
        field_name = fix_data.get("field_name", "")
        old_value = fix_data.get("old_value", "")
        new_value = fix_data.get("new_value", "")

        if not field_name or not new_value:
            return None

        applied = _update_data_value(data_file, field_name, old_value, new_value)
        if applied:
            return f"data_fixed: {field_name} '{old_value}' → '{new_value}' in {os.path.basename(data_file)}"
        return None

    except Exception as exc:
        logger.warning("LLM data fix failed: %s", exc)
        return None


def _update_data_value(
    data_file: str,
    field_name: str,
    old_value: str,
    new_value: str,
) -> bool:
    """更新 data XML 中指定字段的值。

    Parameters
    ----------
    data_file : str
        Data XML 文件路径。
    field_name : str
        字段名。
    old_value : str
        旧值（用于定位，如果为空则匹配第一个同名字段）。
    new_value : str
        新值。

    Returns
    -------
    bool
        是否成功修改。
    """
    try:
        tree = ET.parse(data_file)
        root = tree.getroot()

        modified = False
        for elem in root.iter():
            if elem.tag == field_name or elem.get("name", "") == field_name:
                if old_value and elem.text and elem.text.strip() != old_value:
                    continue
                _backup_file(data_file)
                elem.text = new_value
                modified = True
                break

        if modified:
            tree.write(data_file, encoding="unicode", xml_declaration=True)
        return modified

    except Exception as exc:
        logger.warning("Failed to update data in %s: %s", data_file, exc)
        return False


# ==================================================================
# 辅助函数
# ==================================================================


def _find_case_xml_files(case_path: str) -> list[str]:
    """查找 case XML 文件。"""
    return _find_xml_files_in_subdir(case_path, "case")


def _find_model_xml_files(case_path: str) -> list[str]:
    """查找 model XML 文件。"""
    return _find_xml_files_in_subdir(case_path, "model")


def _find_data_xml_files(case_path: str) -> list[str]:
    """查找 data XML 文件。"""
    return _find_xml_files_in_subdir(case_path, "data")


def _find_xml_files_in_subdir(case_path: str, subdir: str) -> list[str]:
    """在指定子目录中查找 XML 文件。

    Parameters
    ----------
    case_path : str
        用例根路径（目录或文件）。
    subdir : str
        子目录名称 (case/model/data)。

    Returns
    -------
    list[str]
        XML 文件路径列表。
    """
    if not case_path or not os.path.exists(case_path):
        return []

    # Determine module directory
    if os.path.isfile(case_path):
        parent = os.path.dirname(case_path)
        if os.path.basename(parent) in ("case", "model", "data"):
            module_dir = os.path.dirname(parent)
        else:
            module_dir = parent
    else:
        module_dir = case_path

    target_dir = os.path.join(module_dir, subdir)
    if not os.path.isdir(target_dir):
        return []

    return [
        os.path.join(target_dir, f)
        for f in sorted(os.listdir(target_dir))
        if f.endswith(".xml")
    ]


def _backup_file(file_path: str) -> None:
    """创建文件备份（.bak 后缀），仅在备份不存在时创建。"""
    backup_path = file_path + ".bak"
    if not os.path.exists(backup_path):
        try:
            shutil.copy2(file_path, backup_path)
            logger.info("Backup created: %s", backup_path)
        except Exception as exc:
            logger.warning("Failed to create backup %s: %s", backup_path, exc)
