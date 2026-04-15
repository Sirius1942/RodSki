"""Execution Agent LangGraph 图定义。

包含 7 个节点：

    pre_check -> execute -> parse_result --(has failures)--> diagnose -> retry_decide
                                         --(all pass)-----> report

    retry_decide --(retry)--> apply_fix -> execute (loop back)
                 --(give_up)--> report

其中 pre_check 失败时直接跳转到 report（条件边）。
parse_result 后根据是否有失败用例决定是否进入 diagnose。
retry_decide 根据诊断结果和重试计数决定是否重试。

Python 3.9 兼容：使用 ``from __future__ import annotations`` 延迟求值。
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

from langgraph.graph import END, StateGraph

logger = logging.getLogger(__name__)


# ==================================================================
# 条件路由
# ==================================================================


def _pre_check_router(state: Dict[str, Any]) -> str:
    """pre_check 后的条件路由：error 时跳到 report，否则继续 execute。"""
    if state.get("status") == "error":
        return "report"
    return "execute"


def _parse_result_router(state: Dict[str, Any]) -> str:
    """parse_result 后的条件路由：有失败用例时进入 diagnose，否则直接 report。"""
    case_results = state.get("case_results", [])
    has_failures = any(c.get("status") != "PASS" for c in case_results)
    if has_failures:
        return "diagnose"
    return "report"


def _retry_decide_router(state: Dict[str, Any]) -> str:
    """retry_decide 后的条件路由：retry 时进入 apply_fix，否则 report。"""
    decision = state.get("retry_decision", "give_up")
    if decision == "retry":
        return "apply_fix"
    return "report"


# ==================================================================
# 图构建函数
# ==================================================================


def build_execution_graph(
    pre_check_fn: Optional[Callable[..., Any]] = None,
    execute_fn: Optional[Callable[..., Any]] = None,
    parse_result_fn: Optional[Callable[..., Any]] = None,
    diagnose_fn: Optional[Callable[..., Any]] = None,
    report_fn: Optional[Callable[..., Any]] = None,
    retry_decide_fn: Optional[Callable[..., Any]] = None,
    apply_fix_fn: Optional[Callable[..., Any]] = None,
) -> Any:
    """构建 Execution Agent 的执行图。

    节点流：

        pre_check --(ok)--> execute --> parse_result --(has failures)--> diagnose
                  --(error)----------------------------------------------------> report
                                                    --(all pass)--------------> report

        diagnose --> retry_decide --(retry)--> apply_fix --> execute (loop)
                                  --(give_up)--> report

    Parameters
    ----------
    pre_check_fn, execute_fn, parse_result_fn, diagnose_fn, report_fn,
    retry_decide_fn, apply_fix_fn:
        节点函数。允许注入自定义实现（方便测试时 Mock）。
        如果不提供，延迟导入默认实现。

    Returns
    -------
    graph
        编译后的图对象，支持 ``graph.invoke(state_dict)`` 调用。
    """
    # 延迟导入默认节点实现
    if pre_check_fn is None:
        from rodski_agent.execution.nodes import pre_check

        pre_check_fn = pre_check
    if execute_fn is None:
        from rodski_agent.execution.nodes import execute

        execute_fn = execute
    if parse_result_fn is None:
        from rodski_agent.execution.nodes import parse_result

        parse_result_fn = parse_result
    if diagnose_fn is None:
        from rodski_agent.execution.nodes import diagnose

        diagnose_fn = diagnose
    if report_fn is None:
        from rodski_agent.execution.nodes import report

        report_fn = report
    if retry_decide_fn is None:
        from rodski_agent.execution.nodes import retry_decide

        retry_decide_fn = retry_decide
    if apply_fix_fn is None:
        from rodski_agent.execution.fixer import apply_fix

        apply_fix_fn = apply_fix

    from rodski_agent.common.state import ExecutionState

    graph = StateGraph(ExecutionState)

    # 添加节点
    graph.add_node("pre_check", pre_check_fn)
    graph.add_node("execute", execute_fn)
    graph.add_node("parse_result", parse_result_fn)
    graph.add_node("diagnose", diagnose_fn)
    graph.add_node("retry_decide", retry_decide_fn)
    graph.add_node("apply_fix", apply_fix_fn)
    graph.add_node("report", report_fn)

    # 设置入口
    graph.set_entry_point("pre_check")

    # 条件边：pre_check 成功 -> execute，失败 -> report
    graph.add_conditional_edges(
        "pre_check",
        _pre_check_router,
        {"execute": "execute", "report": "report"},
    )

    # 线性边：execute -> parse_result
    graph.add_edge("execute", "parse_result")

    # 条件边：parse_result 有失败 -> diagnose，全通过 -> report
    graph.add_conditional_edges(
        "parse_result",
        _parse_result_router,
        {"diagnose": "diagnose", "report": "report"},
    )

    # diagnose -> retry_decide
    graph.add_edge("diagnose", "retry_decide")

    # 条件边：retry_decide retry -> apply_fix，give_up -> report
    graph.add_conditional_edges(
        "retry_decide",
        _retry_decide_router,
        {"apply_fix": "apply_fix", "report": "report"},
    )

    # apply_fix -> execute (loop back)
    graph.add_edge("apply_fix", "execute")

    graph.add_edge("report", END)

    return graph.compile()
