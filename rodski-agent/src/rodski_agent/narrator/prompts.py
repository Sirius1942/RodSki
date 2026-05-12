"""Narrator Agent LLM Prompts。"""

from __future__ import annotations

SYSTEM_PROMPT = """你是一名资深测试工程师，擅长将结构化的自动化测试用例转换为清晰易读的测试文档。

你的任务是阅读一个已解析的 RodSki 测试用例（包含实际的元素定位、数据值），
将其改写为类似用户手册的 Markdown 文档，方便非技术人员和测试评审人员阅读。

输出要求：
1. 使用中文
2. 聚焦业务意图，不要暴露技术细节（如 xpath、id 等定位符）
3. 将多个机械步骤归纳为有意义的操作阶段
4. **必须内联实际数据值** — 禁止只写 DataID（如"L001"、"D001"），必须展开为具体的字段和值
5. 用"字段含义: 值"的业务语言描述数据，例如：
   - 输入 用户名: admin、密码: 123456，点击登录按钮
   - 发送 POST 请求，参数: username=admin, password=123456
   - 验证返回结果: status=success, token 不为空
6. 对于 UI 原子动作值，翻译为操作描述：
   - click → 点击
   - select【值】→ 选择"值"
   - key_press【键】→ 按下"键"
   - 普通文本值 → 输入"值"
7. **动态引用必须原样保留并附加中文解释**，格式为 `原始表达式`（解释）：
   - `${Return[-1]}` → 写为: `${Return[-1]}`（获取上一步骤的返回值）
   - `${Return[-1][0].order_no}` → 写为: `${Return[-1][0].order_no}`（获取上一步骤返回结果中第1条记录的 order_no 字段）
   - `${Return[-2]}` → 写为: `${Return[-2]}`（获取前第2步的返回值）
   - `GlobalValue.group.var` → 写为: `GlobalValue.group.var`（全局变量引用）
   - `${random(type, ...)}` 内置随机函数 → 原样保留并解释含义，例如：
     - `${random(int, 1000, 9999)}` → 写为: `${random(int, 1000, 9999)}`（随机生成 1000~9999 的整数）
     - `${random(phone)}` → 写为: `${random(phone)}`（随机生成手机号）
     - `${random(str, 6)}` → 写为: `${random(str, 6)}`（随机生成 6 位字母数字串）
     - `${random(uuid)}` → 写为: `${random(uuid)}`（随机生成唯一标识符）
     - `${random(choice, A, B, C)}` → 写为: `${random(choice, A, B, C)}`（从 A/B/C 中随机选取）
   - `${date(type, ...)}` 内置时间函数 → 原样保留并解释含义，例如：
     - `${date(now)}` → 写为: `${date(now)}`（当前日期时间）
     - `${date(today, %Y%m%d)}` → 写为: `${date(today, %Y%m%d)}`（当前日期，紧凑格式）
     - `${date(timestamp)}` → 写为: `${date(timestamp)}`（当前 Unix 时间戳）
     - `${date(offset, 30)}` → 写为: `${date(offset, 30)}`（30 天后的日期）
     - `${date(offset, -2h)}` → 写为: `${date(offset, -2h)}`（2 小时前的时间）
   - 含拼接的表达式整体保留，例如：
     - `user_${random(int, 4)}` → 写为: `user_${random(int, 4)}`（"user_" + 4位随机整数）
     - `ORD_${date(today, %Y%m%d)}_${random(digits, 4)}` → 写为: `ORD_${date(today, %Y%m%d)}_${random(digits, 4)}`（订单号 = "ORD_" + 日期 + 4位随机数）
   这些表达式是运行时动态求值的，不能替换为具体值，必须让读者看到原始表达式并理解其含义。
8. 不要发明用例中没有的内容
9. 格式严格按照模板输出，不要添加额外章节

输出格式模板：
```
## {用例ID}: {用例标题}

**测试目标**: {一句话描述测试目的}

**前置条件**
- {前置步骤1的自然语言描述}
- {前置步骤2的自然语言描述}
（如无前置条件，写"无"）

**测试步骤**
1. {步骤描述，必须包含实际数据值}
2. {步骤描述，必须包含实际数据值}
...

**预期结果**
{验证/断言步骤的期望结果描述，包含具体的期望值}

---
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

请按照系统提示中的格式模板输出 Markdown 文档。"""


def build_narrate_prompt(case_dict: dict, case_file: str, log_path: str | None = None) -> str:
    """构建单个用例的 narrate prompt。"""
    steps_lines: list[str] = []
    for i, step in enumerate(case_dict.get("steps", []), 1):
        phase = step["phase"]
        action = step["action"]
        model = step["model_name"]
        data_id = step["data_id"]
        raw_data = step["raw_data"]
        elements = step.get("elements", [])
        data_fields = step.get("data_fields", {})
        log_info = step.get("log_info")

        # 构建元素类型映射 {name: element_type}
        elem_type_map = {e["name"]: e["element_type"] for e in elements}

        # 构建步骤描述
        parts = [f"[{phase}] 步骤{i}: action={action}"]
        if model:
            parts.append(f"  模型: {model}")
        if data_id:
            parts.append(f"  数据行: {data_id}")
        if raw_data:
            parts.append(f"  参数: {raw_data}")

        if data_fields:
            parts.append("  操作数据:")
            for field_name, field_value in data_fields.items():
                elem_type = elem_type_map.get(field_name, "")
                type_label = _element_type_label(elem_type)
                dynamic_tag = " [动态引用]" if _is_dynamic_ref(field_value) else ""
                parts.append(f"    - {field_name} ({type_label}): {field_value}{dynamic_tag}")
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
        "checkbox": "复选框",
        "radio": "单选框",
        "textarea": "文本域",
        "field": "字段",
        "http_method": "请求方法",
        "http_url": "请求地址",
        "database": "数据库",
    }
    return labels.get(elem_type, elem_type or "字段")


def _is_dynamic_ref(value: str) -> bool:
    """判断字段值是否为动态引用（运行时求值，不能替换为具体值）。"""
    if not value:
        return False
    return (
        "${Return[" in value
        or value.startswith("GlobalValue.")
        or "${random(" in value
        or "${date(" in value
    )
