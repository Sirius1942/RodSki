"""Narrator Agent LLM Prompts。"""

from __future__ import annotations

import re

SYSTEM_PROMPT = """你是一名资深测试工程师，擅长把自动化 XML 用例转换成给测试、评审和业务人员快速沟通的 Markdown 说明。

最高准则：内容优先，步骤清晰，少样式，少重复。不要为了形式把每一步拆成“操作/数据/预期结果”三段；能在一行讲清楚就一行讲清楚。

硬约束：
1. 使用中文。
2. 正文聚焦业务意图、操作对象、操作动作、关键输入数据、页面跳转/等待条件、预期结果/检查点。
3. 不要把 RodSki XML 的 action/model/data 直接当成正文步骤内容输出。
4. 正文禁止出现“对应 XML”、“action=”、“model=”、“data_id”、“数据行”、“RodSki action”等自动化实现表述。
5. 不要输出自动化实现映射表；叙述文档优先服务沟通，不服务代码走查。
6. 不要暴露 xpath、css、JS 源码、DOM 查询、变量名等技术细节。
7. GlobalValue 引用必须显示为已解析的实际值，禁止输出任何 GlobalValue.xxx 表达式。
8. 不要发明输入中没有的账号、地址、零件号、供应商、状态、验证码或期望文本。
9. 动态引用只有输入中确实出现 `${...}` 时才允许输出；禁止自行编造 `${Return[-1]}` 等表达式。
10. 步骤顺序必须与 XML 顺序一致。默认一条 XML 步骤对应一条精简步骤；只有连续的纯确认步骤与前一步表达完全重复时，才允许合并到同一行的“确认：...”中。
11. 关键实际值必须保留，包括用户名、密码、验证码、URL、VIN、零件号、供应商、状态和期望文案；禁止用“对应密码”“正确密码”等泛化占位替代实际值。
12. 如果 evaluate 步骤里包含供应商、状态、数量、零件号组合、SPD/左右属性、订单号、支付结果等关键业务断言，必须把这些业务期望写清楚，不要写“执行脚本”或“校验成功”。
13. 如果输入中出现“结构化verify建议”，不要输出专门附录；只把其中对业务理解有价值的校验点合并到“关键校验”或相关步骤中。

正文表达规则：
- navigate：写成“打开/进入某页面：{完整地址}”。
- type：根据 model/data 解析成“点击、输入、勾选、选择”等具体操作；过滤 NONE；不要写字段 key。
- verify：写成“确认/检查：{具体文本、状态或结果}”。
- evaluate：根据“脚本摘要”翻译成人能理解的业务动作、等待条件或校验；不要贴 JS。
- screenshot：写成“保存截图：{文件名}”。
- close：写成“关闭浏览器，结束测试”。

每个步骤使用一条编号列表，推荐格式：
```
1. {动作或检查点}；{关键数据}；结果：{页面变化或检查点}。
```
如果没有结果，不要硬写“结果”。不要在每一步下方重复“操作：”“数据：”“预期结果：”。

输出结构必须严格使用：
```
## {用例ID}: {用例标题}

**测试目标**: {一句话描述测试目的}

**依赖前置**: {依赖前置；无则写“无”}

**关键数据**
- {只列最影响理解和执行的数据，如账号、VIN、零件号、供应商、验证码、目标状态}

**步骤**

前置处理：
1. ...
2. ...
（如无前置处理，省略“前置处理”）

测试执行：
1. ...
2. ...

后置处理：
1. ...
（如无后置处理，省略“后置处理”）

**关键校验**
- {最终业务验证点，包含具体期望值}

*来源: {case_file}*{log_line}
```
"""

NARRATE_PROMPT_TEMPLATE = """请将以下 RodSki 测试用例转换为人类可读的 Markdown 文档。

## 用例基本信息
- ID: {case_id}
- 标题: {title}
- 描述: {description}
- 类型: {component_type}
- 来源文件: {case_file}
{log_info_section}

## 用例步骤（已解析实际值）

{steps_text}

{verify_suggestions_text}

请按照系统提示中的精简格式模板输出 Markdown 文档。"""


def build_narrate_prompt(case_dict: dict, case_file: str, log_path: str | None = None) -> str:
    """构建单个用例的 narrate prompt。"""
    steps_lines: list[str] = []
    verify_suggestions: list[dict] = []
    steps = case_dict.get("steps", [])
    for i, step in enumerate(steps, 1):
        phase = step["phase"]
        action = step["action"]
        model = step["model_name"]
        data_id = step["data_id"]
        raw_data = step["raw_data"]
        display_data = step.get("display_data") or raw_data or data_id
        elements = step.get("elements", [])
        data_fields = step.get("data_fields", {})
        log_info = step.get("log_info")
        next_step = steps[i] if i < len(steps) else {}

        # 构建元素类型映射 {name: element_type}
        elem_type_map = {e["name"]: e["element_type"] for e in elements}
        elem_desc_map = {e["name"]: e.get("description", "") for e in elements}

        # 构建步骤描述
        parts = [f"[{phase}] 步骤{i}: action={action}"]
        parts.append(f"  映射阶段: {_phase_label(phase)}")
        parts.append(f"  映射action: {action}")
        if model:
            parts.append(f"  映射model: {model}")
        trace_data = _mapping_data(data_id, raw_data, display_data)
        if trace_data:
            parts.append(f"  映射data: {trace_data}")
        if action == "navigate" and display_data:
            nav_hint = _navigation_hint(display_data)
            if nav_hint:
                parts.append(f"  导航目的: {nav_hint}")
            parts.append(f"  导航地址: {display_data}")
        elif action == "screenshot" and display_data:
            parts.append(f"  输出文件: {display_data}")
        elif action == "evaluate":
            script_hint = _evaluate_script_hint(data_id, raw_data, display_data)
            if script_hint:
                parts.append(f"  脚本摘要: {script_hint}")
            elif display_data and display_data != trace_data and len(display_data) <= 120:
                parts.append(f"  展示参数: {display_data}")
            verify_hint = _evaluate_verify_recommendation(
                i,
                data_id,
                raw_data,
                display_data,
                next_step,
                log_info,
            )
            if verify_hint:
                verify_suggestions.append(verify_hint)
                parts.append(f"  隐藏业务断言: {verify_hint['assertion_summary']}")
                parts.append("  结构化verify建议:")
                parts.append(
                    f"    - verify {verify_hint['model']} {verify_hint['data_id']}"
                )
                parts.append(
                    "    - 字段: "
                    + ", ".join(field["name"] for field in verify_hint["fields"])
                )
        elif display_data and (not model or display_data != trace_data):
            parts.append(f"  展示参数: {display_data}")
        elif data_id and not trace_data and not model:
            parts.append("  展示参数: （无）")

        if data_fields:
            data_lines: list[str] = []
            ordered_field_names = _ordered_field_names(data_fields, elements)
            for field_name in ordered_field_names:
                field_value = data_fields[field_name]
                if str(field_value).strip().upper() == "NONE":
                    continue
                elem_type = elem_type_map.get(field_name, "")
                field_label = elem_desc_map.get(field_name) or field_name
                type_label = _element_type_label(elem_type)
                dynamic_tag = " [动态引用]" if _is_dynamic_ref(field_value) else ""
                data_lines.append(f"    - {field_label} ({type_label}): {field_value}{dynamic_tag}")
            if data_lines:
                parts.append("  操作数据:")
                parts.extend(data_lines)
        elif elements:
            elem_desc = ", ".join(
                f"{e['name']}({e['description'] or e['element_type']})"
                for e in elements
            )
            parts.append(f"  元素: {elem_desc}")

        if log_info:
            if log_info.get("sql"):
                parts.append(f"  执行SQL: {log_info['sql']}")
            if log_info.get("return_value"):
                rv = log_info["return_value"]
                if len(rv) > 100:
                    rv = rv[:100] + "..."
                parts.append(f"  返回值: {rv}")
            if log_info.get("status"):
                parts.append(f"  执行结果: {log_info['status']}")

        steps_lines.append("\n".join(parts))

    steps_text = "\n\n".join(steps_lines) if steps_lines else "（无步骤）"
    verify_suggestions_text = _format_verify_suggestions(verify_suggestions)

    log_info_section = ""
    if log_path:
        log_info_section = f"- 执行日志: {log_path}"

    log_line = f"\n*执行日志: {log_path}*" if log_path else ""

    return NARRATE_PROMPT_TEMPLATE.format(
        case_id=case_dict["id"],
        title=case_dict["title"],
        description=case_dict.get("description", ""),
        component_type=case_dict.get("component_type", ""),
        case_file=case_file,
        log_info_section=log_info_section,
        steps_text=steps_text,
        verify_suggestions_text=verify_suggestions_text,
        log_line=log_line,
    )


def _element_type_label(elem_type: str) -> str:
    """将 element type 转换为中文业务标签。"""
    labels = {
        "input": "输入框",
        "button": "按钮",
        "select": "下拉框",
        "link": "链接",
        "text": "文本",
        "web": "页面元素",
        "div": "页面元素",
        "span": "页面元素",
        "checkbox": "复选框",
        "radio": "单选框",
        "textarea": "文本域",
        "field": "字段",
        "http_method": "请求方法",
        "http_url": "请求地址",
        "database": "数据库",
    }
    return labels.get(elem_type, elem_type or "字段")


def _phase_label(phase: str) -> str:
    labels = {
        "pre_process": "前置处理",
        "test_case": "测试执行",
        "post_process": "后置处理",
    }
    if phase.startswith("test_case/"):
        return "测试执行"
    return labels.get(phase, phase)


def _is_dynamic_ref(value: str) -> bool:
    """判断字段值是否为动态引用（运行时求值，不能替换为具体值）。"""
    if not value:
        return False
    return (
        "${Return[" in value
        or "${random(" in value
        or "${date(" in value
    )


def _trace_data_id(data_id: str, raw_data: str, display_data: str) -> str:
    """返回适合放入对应 XML 行的数据引用。"""
    if not data_id:
        return ""
    if data_id.startswith("GlobalValue."):
        return ""
    if raw_data and raw_data != data_id:
        return ""
    if display_data and display_data != data_id and data_id.startswith("GlobalValue."):
        return ""
    if len(data_id) > 120:
        return ""
    return data_id


def _mapping_data(data_id: str, raw_data: str, display_data: str) -> str:
    """返回适合附录展示的数据，不泄漏 GlobalValue 或大段脚本。"""
    if data_id.startswith("GlobalValue."):
        return display_data
    return _trace_data_id(data_id, raw_data, display_data)


def _ordered_field_names(data_fields: dict[str, str], elements: list[dict]) -> list[str]:
    """按 model.xml 元素顺序输出字段，剩余字段保持数据源顺序。"""
    ordered: list[str] = []
    for elem in elements:
        name = elem.get("name", "")
        if name in data_fields and name not in ordered:
            ordered.append(name)
    for name in data_fields:
        if name not in ordered:
            ordered.append(name)
    return ordered


def _evaluate_script_hint(data_id: str, raw_data: str, display_data: str) -> str:
    """把 evaluate 的脚本引用或 JS 代码压缩成业务目标线索。"""
    text = "\n".join(x for x in (data_id, raw_data, display_data) if x)

    if "open_info_maintain" in text:
        return "打开 SPD 配件信息维护页面，并等待零件号搜索输入框可用"

    match = re.search(r"set_(\d+)_(left|right)", text)
    if match:
        side = "左" if match.group(2) == "left" else "右"
        return f"查询零件号 {match.group(1)}，进入配件信息编辑页，将“左右”字段设置为“{side}”并保存"

    part_no = _first_match(text, r"partNo\s*=\s*['\"](\d+)['\"]")
    side_label = _first_match(text, r"sideLabel\s*=\s*['\"]([^'\"]+)['\"]")
    if part_no and side_label:
        return f"查询零件号 {part_no}，进入配件信息编辑页，将“左右”字段设置为“{side_label}”并保存"

    vin = _first_match(text, r"vin\s*=\s*['\"]([^'\"]+)['\"]")
    part = _first_match(text, r"part\s*=\s*['\"]([^'\"]+)['\"]")

    if "__dualWiperTargetQuoteNo" in text and "target_quote_finished_ready" in text:
        suffix = f"（VIN={vin}，零件号={part}）" if vin and part else ""
        return f"在报价列表中翻页查找状态为“报价完成”的目标询价单{suffix}，并记录报价单号供后续步骤使用"

    if "target_quote_opened" in text or "target_quote_opened_by_direct_url" in text:
        suffix = f"（VIN={vin}，零件号={part}）" if vin and part else ""
        return f"点击目标询价单行的“查看”入口打开报价详情页；若页面入口不可用，则用报价单号直接跳转{suffix}"

    if "order_detail_ready" in text and "选购" in text:
        return "等待报价详情页加载完成，确认页面出现“选购”按钮且不再显示“加载中”"

    if "dual_wipers_selected_same_store_spd" in text or "571513,571518" in text:
        return "校验已选中的两条雨刮均来自“小泽供应商1-店铺1”，SPD 信息非空，零件号组合为 571513 和 571518，且页面摘要显示共 2 件"

    if len(text) > 120:
        return "执行页面脚本完成当前步骤的页面准备、定位或业务校验"

    return ""


def _evaluate_verify_recommendation(
    step_index: int,
    data_id: str,
    raw_data: str,
    display_data: str,
    next_step: dict,
    log_info: dict | None = None,
) -> dict:
    """识别 evaluate 中隐藏的关键业务断言，转成 verify 外提建议。

    narrate 不直接修改 case/model/data；这里把可执行的结构化建议交给 LLM，
    让 Markdown 明确指出后续生成或修复用例时应补的 verify 模型和数据字段。
    """
    text = "\n".join(x for x in (data_id, raw_data, display_data) if x)
    log_return = (log_info or {}).get("return_value", "")
    all_text = "\n".join(x for x in (text, log_return) if x)

    if not _looks_like_business_assertion(all_text):
        return {}

    model = ""
    verify_data_id = ""
    if next_step and next_step.get("action") in {"verify", "check"}:
        model = next_step.get("model_name", "") or next_step.get("model", "")
        verify_data_id = next_step.get("data_id", "") or next_step.get("data", "")

    if "dual_wipers_selected_same_store_spd" in all_text or "571513,571518" in all_text:
        fields = [
            {"name": "selectedSupplier", "expected": "小泽供应商1 - 店铺1"},
            {"name": "selectedParts", "expected": "571513,571518"},
            {"name": "selectedCount", "expected": "2"},
            {"name": "selectedSummary", "expected": "已选择1种(共2件)商品，"},
            {"name": "leftPartNo", "expected": "571513"},
            {"name": "leftSpdStatus", "expected": "非空"},
            {"name": "rightPartNo", "expected": "571518"},
            {"name": "rightSpdStatus", "expected": "非空"},
        ]
        left_spd = _first_match(log_return, r"571513:([^|']+)")
        right_spd = _first_match(log_return, r"571518:([^|']+)")
        if left_spd:
            fields.append({"name": "leftSpdText", "expected": left_spd})
        if right_spd:
            fields.append({"name": "rightSpdText", "expected": right_spd})

        return {
            "step_index": step_index,
            "assertion_summary": (
                "两条雨刮均来自小泽供应商1 - 店铺1，零件号组合为 "
                "571513/571518，SPD 信息非空，页面摘要为共 2 件"
            ),
            "model": model or "OrderSelectionCheck",
            "data_id": verify_data_id or "dual_wipers_selected",
            "fields": fields,
        }

    expected_texts = _extract_expected_texts(all_text)
    fields = [
        {"name": _suggest_field_name(value, idx), "expected": value}
        for idx, value in enumerate(expected_texts, 1)
    ]
    if not fields:
        return {}

    return {
        "step_index": step_index,
        "assertion_summary": "evaluate 中包含关键业务文本断言，应外提为 verify 字段",
        "model": model or "BusinessAssertionCheck",
        "data_id": verify_data_id or "business_assertion",
        "fields": fields,
    }


def _looks_like_business_assertion(text: str) -> bool:
    if "throw new Error" not in text and "Error(" not in text:
        return False
    keywords = [
        "供应商",
        "报价完成",
        "已选择",
        "共2件",
        "零件号",
        "SPD",
        "spd",
        "productPartsNum",
        "payment",
        "支付成功",
        "订单",
        "VIN",
    ]
    return any(keyword in text for keyword in keywords)


def _extract_expected_texts(text: str) -> list[str]:
    """从常见 JS includes/正则中提取可读的期望文本，供通用建议使用。"""
    values: list[str] = []
    for pattern in (
        r"\.includes\(['\"]([^'\"]{2,80})['\"]\)",
        r"includes\(['\"]([^'\"]{2,80})['\"]\)",
        r"normalize-space\(\.\),['\"]([^'\"]{2,80})['\"]",
    ):
        for value in re.findall(pattern, text):
            if value not in values and not value.startswith(("data:", "http")):
                values.append(value)
    return values[:8]


def _suggest_field_name(value: str, idx: int) -> str:
    if "支付成功" in value:
        return "paymentSuccessText"
    if "报价完成" in value:
        return "quoteFinishedStatus"
    if "已选择" in value or "共" in value:
        return "selectedSummary"
    if "供应商" in value:
        return "selectedSupplier"
    if "VIN" in value:
        return "vinText"
    return f"businessExpectedText{idx}"


def _format_verify_suggestions(suggestions: list[dict]) -> str:
    if not suggestions:
        return ""
    lines = ["## evaluate 隐藏业务断言外提建议"]
    for suggestion in suggestions:
        fields = suggestion.get("fields", [])
        field_names = ", ".join(field["name"] for field in fields)
        expected_pairs = "; ".join(
            f"{field['name']}={field['expected']}" for field in fields
        )
        lines.extend([
            "",
            f"- 来源步骤: 步骤{suggestion.get('step_index')}",
            f"- 断言摘要: {suggestion.get('assertion_summary')}",
            f"- 建议 verify: verify {suggestion.get('model')} {suggestion.get('data_id')}",
            f"- 建议模型字段: {field_names}",
            f"- 建议验证数据: {expected_pairs}",
        ])
    return "\n".join(lines)


def _first_match(text: str, pattern: str) -> str:
    match = re.search(pattern, text)
    return match.group(1) if match else ""


def _navigation_hint(url: str) -> str:
    """为常见业务 URL 提供自然语言名称。"""
    if "spd/index/#/info-maintain" in url:
        return "SPD 维护平台地址"
    if url.rstrip("/").endswith("/logout"):
        return "退出当前 EC 平台登录状态"
    if "agentBuy" in url:
        return "EC 代买平台地址"
    if "market/inquirys" in url:
        return "报价列表页地址"
    return ""
