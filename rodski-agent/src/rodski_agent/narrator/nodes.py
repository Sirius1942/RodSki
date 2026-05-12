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
from datetime import datetime
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
    from langchain_core.messages import HumanMessage, SystemMessage
    from rodski_agent.common.llm_bridge import get_chat_model
    from rodski_agent.narrator.prompts import SYSTEM_PROMPT, build_narrate_prompt

    resolved_cases = state.get("resolved_cases", [])
    case_path = state.get("case_path", "")
    log_path = state.get("log_path")

    if not resolved_cases:
        return {"status": "error", "error": "没有可解读的用例"}

    try:
        model = get_chat_model("execution")  # 低温度，忠实输出
    except Exception as exc:
        return {"status": "error", "error": f"LLM 初始化失败: {exc}"}

    narratives: list[dict[str, Any]] = []
    for case_dict in resolved_cases:
        try:
            user_prompt = build_narrate_prompt(case_dict, case_path, log_path)
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ]
            response = model.invoke(messages)
            markdown = response.content if hasattr(response, "content") else str(response)
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
