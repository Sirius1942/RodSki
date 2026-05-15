"""Narrator Agent 节点实现。

节点：
- resolve_case  — 解析 case XML，替换 model/data 引用
- narrate       — LLM 生成 Markdown 叙述
- write_files   — 写入 narrative/ 目录

Python 3.9 兼容：使用 ``from __future__ import annotations`` 延迟求值。
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================
# resolve_case
# ============================================================

def resolve_case(state: dict[str, Any]) -> dict[str, Any]:
    """解析 case XML，将 model/data 引用替换为实际值。

    可选：若 log_path 存在，调用 LogCorrelator 注入运行时数据。
    """
    from rodski_agent.narrator.case_resolver import CaseResolver
    from rodski_agent.narrator.log_correlator import LogCorrelator

    case_path = state.get("case_path", "")
    log_path = state.get("log_path")
    case_ids = state.get("case_ids")

    if not case_path or not Path(case_path).exists():
        return {"status": "error", "error": f"case 文件不存在: {case_path}"}

    try:
        resolver = CaseResolver(case_path)
        cases = resolver.resolve(case_ids=case_ids)
    except Exception as exc:
        return {"status": "error", "error": f"解析 case 文件失败: {exc}"}

    # 可选：注入日志信息
    log_data: dict[str, Any] = {}
    if log_path and Path(log_path).exists():
        try:
            correlator = LogCorrelator(log_path)
            log_data = correlator.correlate()
        except Exception as exc:
            logger.warning("解析执行日志失败，跳过日志增强: %s", exc)

    # 序列化，并注入 log_info
    resolved_dicts = []
    for case in cases:
        case_dict = CaseResolver.to_dict(case)
        case_log = log_data.get(case.id)
        if case_log:
            log_steps = case_log.steps
            # 按顺序对齐：log 步骤与 case 步骤一一对应（跳过 pre/post 中的 navigate/wait）
            log_idx = 0
            for step in case_dict["steps"]:
                if log_idx < len(log_steps):
                    from rodski_agent.narrator.log_correlator import LogCorrelator as LC
                    step["log_info"] = {
                        "action": log_steps[log_idx].action,
                        "status": log_steps[log_idx].status,
                        "sql": log_steps[log_idx].sql,
                        "return_value": log_steps[log_idx].return_value,
                    }
                    log_idx += 1
        resolved_dicts.append(case_dict)

    # 推断输出目录
    project_root = Path(case_path).resolve().parent.parent
    output_dir = str(project_root / "narrative")

    return {
        "resolved_cases": resolved_dicts,
        "output_dir": output_dir,
        "status": "running",
    }


# ============================================================
# narrate
# ============================================================

def narrate(state: dict[str, Any]) -> dict[str, Any]:
    """调用 LLM，为每个已解析的用例生成 Markdown 叙述。"""
    resolved_cases = state.get("resolved_cases", [])
    case_path = state.get("case_path", "")
    log_path = state.get("log_path")

    if not resolved_cases:
        return {"status": "error", "error": "没有可解读的用例"}

    llm_model = None

    narratives: list[dict[str, Any]] = []
    for case_dict in resolved_cases:
        try:
            if _is_database_case(case_dict):
                markdown = _render_database_case(case_dict, case_path, log_path)
            else:
                if llm_model is None:
                    from rodski_agent.common.llm_bridge import get_chat_model

                    llm_model = get_chat_model("execution")  # 低温度，忠实输出
                markdown = _render_llm_case(case_dict, case_path, log_path, llm_model)
            narratives.append({
                "case_id": case_dict["id"],
                "title": case_dict["title"],
                "markdown": markdown,
            })
            logger.info("已生成叙述: %s - %s", case_dict["id"], case_dict["title"])
        except Exception as exc:
            logger.error("生成叙述失败 [%s]: %s", case_dict.get("id", "?"), exc)
            narratives.append({
                "case_id": case_dict["id"],
                "title": case_dict["title"],
                "markdown": f"## {case_dict['id']}: {case_dict['title']}\n\n> 生成失败: {exc}\n",
            })

    return {"narratives": narratives}


def _render_llm_case(
    case_dict: dict[str, Any],
    case_path: str,
    log_path: str | None,
    model: Any,
) -> str:
    from langchain_core.messages import HumanMessage, SystemMessage
    from rodski_agent.narrator.prompts import SYSTEM_PROMPT, build_narrate_prompt

    user_prompt = build_narrate_prompt(case_dict, case_path, log_path)
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]
    response = model.invoke(messages)
    return response.content if hasattr(response, "content") else str(response)


def _is_database_case(case_dict: dict[str, Any]) -> bool:
    if case_dict.get("component_type") == "数据库":
        return True
    return any(step.get("db_info") for step in case_dict.get("steps", []))


def _render_database_case(
    case_dict: dict[str, Any],
    case_path: str,
    log_path: str | None,
) -> str:
    case_file = Path(case_path).name
    db_steps = [step for step in case_dict.get("steps", []) if step.get("db_info")]
    all_steps = case_dict.get("steps", [])
    primary = db_steps[0] if db_steps else (all_steps[0] if all_steps else {})
    db_info = primary.get("db_info", {})
    data_fields = primary.get("data_fields", {})
    parameters = db_info.get("parameters") or {
        key: value
        for key, value in data_fields.items()
        if key not in {"query", "Query", "sql", "SQL", "operation", "Operation"}
        and str(value).strip().upper() != "NONE"
    }
    sql_tables = db_info.get("sql_tables") or []
    verify = db_info.get("verify") or {}
    verify_fields = verify.get("fields") or {}

    lines: list[str] = [
        f"## {case_dict.get('id', '')}: {case_dict.get('title', '')}",
        "",
        f"**测试目标**: {case_dict.get('description') or case_dict.get('title') or '验证数据库查询结果'}",
        "",
        "**依赖前置**: 数据库连接配置可用，测试数据已写入 `data/data.sqlite`",
        "",
        "**数据库信息**",
    ]

    if db_info.get("service_name"):
        lines.append(f"- 服务/库说明: {db_info['service_name']}")
    if db_info.get("connection_name"):
        lines.append(f"- 连接配置: {db_info['connection_name']}")
    if db_info.get("database_type"):
        lines.append(f"- 数据库类型: {db_info['database_type']}")
    if db_info.get("database"):
        lines.append(f"- 数据库: {db_info['database']}")
    if db_info.get("database_path") and db_info.get("database_path") != db_info.get("database"):
        lines.append(f"- 解析路径: {db_info['database_path']}")
    if sql_tables:
        lines.append(f"- 业务数据表: {', '.join(sql_tables)}")

    lines.extend(["", "**关键数据**"])
    if db_info.get("data_table"):
        lines.append(f"- 查询数据表: {db_info['data_table']}")
    if primary.get("data_id"):
        lines.append(f"- 查询数据ID: {primary['data_id']}")
    if db_info.get("query_name"):
        query_label = db_info["query_name"]
        if db_info.get("query_remark"):
            query_label += f"（{db_info['query_remark']}）"
        lines.append(f"- 查询模板: {query_label}")
    for key, value in parameters.items():
        lines.append(f"- 参数 `{key}`: {value}")
    if verify.get("table_name"):
        verify_label = verify["table_name"]
        if verify.get("data_id"):
            verify_label += f" / {verify['data_id']}"
        lines.append(f"- 校验数据表: {verify_label}")
    for key, value in verify_fields.items():
        lines.append(f"- 期望 `{key}`: {value}")

    lines.extend(["", "**SQL语句**", ""])
    sql_template = (db_info.get("sql_template") or "").strip()
    resolved_sql = (db_info.get("resolved_sql") or "").strip()
    if sql_template:
        lines.extend(["模板SQL:", "```sql", sql_template, "```"])
    if resolved_sql and resolved_sql != sql_template:
        lines.extend(["", "带入参数后的SQL:", "```sql", resolved_sql, "```"])
    elif not sql_template:
        lines.append("未解析到 SQL。")

    lines.extend(["", "**步骤**", "", "测试执行："])
    if db_steps:
        for idx, step in enumerate(db_steps, 1):
            step_db = step.get("db_info", {})
            step_params = step_db.get("parameters") or {}
            action = _db_operation_label(step_db.get("operation", ""))
            target = step_db.get("query_remark") or step_db.get("query_name") or step.get("model_name", "")
            param_text = _format_inline_params(step_params)
            table_text = ", ".join(step_db.get("sql_tables") or [])
            sentence = f"{idx}. 执行数据库{action}"
            if target:
                sentence += f"：{target}"
            if table_text:
                sentence += f"；表：{table_text}"
            if param_text:
                sentence += f"；参数：{param_text}"
            log_info = step.get("log_info") or {}
            if log_info.get("status"):
                sentence += f"；执行结果：{log_info['status']}"
            sentence += "。"
            lines.append(sentence)
    else:
        lines.append("1. 执行数据库步骤。")

    lines.extend(["", "**关键校验**"])
    if verify_fields:
        table_text = ", ".join(sql_tables) if sql_tables else "查询结果"
        for key, value in verify_fields.items():
            lines.append(f"- {table_text} 中 `{key}` 应包含/等于 `{value}`")
    elif db_info.get("operation") == "query":
        lines.append("- 数据库查询应正常返回结果集")
    else:
        lines.append("- 数据库操作应执行成功")

    for step in db_steps:
        log_info = step.get("log_info") or {}
        if log_info.get("return_value"):
            lines.extend(["", "**运行返回摘要**", "```text", _truncate_text(log_info["return_value"], 1000), "```"])
            break

    source_line = f"*来源: {case_file}*"
    if log_path:
        source_line += f"\n*执行日志: {log_path}*"
    lines.extend(["", source_line])
    return "\n".join(lines).rstrip() + "\n"


def _db_operation_label(operation: str) -> str:
    labels = {
        "query": "查询",
        "execute": "执行",
        "insert": "插入",
        "update": "更新",
        "delete": "删除",
    }
    return labels.get(operation, operation or "操作")


def _format_inline_params(params: dict[str, Any]) -> str:
    return "，".join(f"{key}={value}" for key, value in params.items())


def _truncate_text(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + "..."


# ============================================================
# write_files
# ============================================================

def write_files(state: dict[str, Any]) -> dict[str, Any]:
    """将叙述写入 narrative/ 目录，每个用例一个 Markdown 文件。"""
    narratives = state.get("narratives", [])
    output_dir = state.get("output_dir", "")

    if not output_dir:
        return {"status": "error", "error": "output_dir 未设置"}

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    written: list[str] = []
    for item in narratives:
        case_id = item.get("case_id", "unknown")
        title = item.get("title", "")
        markdown = item.get("markdown", "")

        filename = _safe_filename(f"{case_id}_{title}") + ".md"
        file_path = out_path / filename
        file_path.write_text(markdown, encoding="utf-8")
        written.append(str(file_path))
        logger.info("已写入: %s", file_path)

    return {
        "written_files": written,
        "status": "success",
    }


# ============================================================
# 工具函数
# ============================================================

def _safe_filename(name: str) -> str:
    """将字符串转换为安全的文件名，替换非法字符为 _。"""
    # 替换 Windows/Unix 文件名非法字符及空格
    safe = re.sub(r'[/\\:*?"<>|\s]', "_", name)
    # 合并连续下划线
    safe = re.sub(r"_+", "_", safe)
    return safe.strip("_")
