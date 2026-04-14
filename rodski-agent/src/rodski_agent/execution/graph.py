"""Execution Agent LangGraph 图定义。

包含 7 个节点：

    pre_check -> execute -> parse_result --(has failures)--> diagnose -> retry_decide
                                         --(all pass)-----> report

    retry_decide --(retry)--> apply_fix -> execute (loop back)
                 --(give_up)--> report

其中 pre_check 失败时直接跳转到 report（条件边）。
parse_result 后根据是否有失败用例决定是否进入 diagnose。
retry_decide 根据诊断结果和重试计数决定是否重试。

运行时自动检测 ``langgraph`` 是否可用：
  - 可用时使用 ``StateGraph`` 构建真正的 LangGraph 图；
  - 不可用时使用内置的 ``SimpleGraph`` 替代，保持 ``invoke(state) -> state``
    接口一致。

Python 3.9 兼容：使用 ``from __future__ import annotations`` 延迟求值。
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# 检测 langgraph 可用性
# ------------------------------------------------------------------

try:
    from langgraph.graph import END, StateGraph

    HAS_LANGGRAPH = True
    logger.debug("langgraph detected — using StateGraph backend")
except ImportError:
    HAS_LANGGRAPH = False
    logger.debug("langgraph not found — using SimpleGraph backend")


# ==================================================================
# SimpleGraph — 轻量级替代实现
# ==================================================================

class SimpleGraph:
    """当 ``langgraph`` 不可用时的简化执行图。

    接口与 LangGraph 编译后的图一致：

    .. code-block:: python

        graph = SimpleGraph(nodes=[...], conditional_edges={...})
        result = graph.invoke({"case_path": "...", "headless": True})

    Parameters
    ----------
    nodes:
        有序节点列表，每项为 ``(name, callable)``。
    conditional_edges:
        条件跳转映射，key 为源节点名，value 为
        ``(condition_fn, target_map)``。
        ``condition_fn(state) -> str`` 返回 target_map 中的 key，
        对应的 value 为下一个节点名（``"__end__"`` 表示结束）。
    max_loop:
        最大循环次数，防止无限循环。默认 10。
    """

    _END = "__end__"

    def __init__(
        self,
        nodes: List[Tuple[str, Callable[..., Any]]],
        conditional_edges: Optional[
            Dict[str, Tuple[Callable[..., str], Dict[str, str]]]
        ] = None,
        max_loop: int = 10,
    ) -> None:
        self._nodes: Dict[str, Callable[..., Any]] = {
            name: fn for name, fn in nodes
        }
        self._order: List[str] = [name for name, _ in nodes]
        self._conditional_edges = conditional_edges or {}
        self._max_loop = max_loop

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """按顺序执行节点，遇到异常时标记 error 并终止。

        支持循环：通过条件边跳回前面的节点时，使用 loop_counter
        跟踪循环次数，超过 max_loop 时强制终止。

        Returns
        -------
        dict
            执行完成后的最终状态。
        """
        current: Dict[str, Any] = dict(state)
        idx = 0
        loop_counter = 0

        while idx < len(self._order):
            name = self._order[idx]
            fn = self._nodes[name]

            # 执行节点
            try:
                updates = fn(current)
                if isinstance(updates, dict):
                    current.update(updates)
            except Exception as exc:
                current["status"] = "error"
                current["error"] = f"Node '{name}' failed: {exc}"
                logger.exception("Node '%s' raised an exception", name)
                break

            # 检查条件边
            if name in self._conditional_edges:
                condition_fn, target_map = self._conditional_edges[name]
                try:
                    branch_key = condition_fn(current)
                except Exception as exc:
                    current["status"] = "error"
                    current["error"] = (
                        f"Conditional edge after '{name}' failed: {exc}"
                    )
                    break
                target_node = target_map.get(branch_key)
                if target_node is None or target_node == self._END:
                    break
                # 跳转到目标节点
                if target_node in self._nodes:
                    target_idx = self._order.index(target_node)
                    # 检测循环（跳回前面的节点）
                    if target_idx <= idx:
                        loop_counter += 1
                        if loop_counter > self._max_loop:
                            current["status"] = "error"
                            current["error"] = (
                                f"Max loop count ({self._max_loop}) exceeded "
                                f"at node '{name}'"
                            )
                            break
                    idx = target_idx
                    continue
                else:
                    current["status"] = "error"
                    current["error"] = (
                        f"Conditional edge target '{target_node}' not found"
                    )
                    break

            idx += 1

        return current


# ==================================================================
# 图构建函数
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

    if HAS_LANGGRAPH:
        return _build_langgraph(
            pre_check_fn, execute_fn, parse_result_fn, diagnose_fn, report_fn,
            retry_decide_fn, apply_fix_fn,
        )
    return _build_simple_graph(
        pre_check_fn, execute_fn, parse_result_fn, diagnose_fn, report_fn,
        retry_decide_fn, apply_fix_fn,
    )


# ------------------------------------------------------------------
# SimpleGraph 版本
# ------------------------------------------------------------------

def _build_simple_graph(
    pre_check_fn: Callable[..., Any],
    execute_fn: Callable[..., Any],
    parse_result_fn: Callable[..., Any],
    diagnose_fn: Callable[..., Any],
    report_fn: Callable[..., Any],
    retry_decide_fn: Callable[..., Any],
    apply_fix_fn: Callable[..., Any],
) -> SimpleGraph:
    """使用 SimpleGraph 构建执行图。"""
    return SimpleGraph(
        nodes=[
            ("pre_check", pre_check_fn),
            ("execute", execute_fn),
            ("parse_result", parse_result_fn),
            ("diagnose", diagnose_fn),
            ("retry_decide", retry_decide_fn),
            ("apply_fix", apply_fix_fn),
            ("report", report_fn),
        ],
        conditional_edges={
            "pre_check": (
                _pre_check_router,
                {"execute": "execute", "report": "report"},
            ),
            "parse_result": (
                _parse_result_router,
                {"diagnose": "diagnose", "report": "report"},
            ),
            "retry_decide": (
                _retry_decide_router,
                {"apply_fix": "apply_fix", "report": "report"},
            ),
            # After apply_fix, loop back to execute
            "apply_fix": (
                lambda s: "execute",
                {"execute": "execute"},
            ),
        },
        max_loop=10,
    )


# ------------------------------------------------------------------
# LangGraph 版本
# ------------------------------------------------------------------

def _build_langgraph(
    pre_check_fn: Callable[..., Any],
    execute_fn: Callable[..., Any],
    parse_result_fn: Callable[..., Any],
    diagnose_fn: Callable[..., Any],
    report_fn: Callable[..., Any],
    retry_decide_fn: Callable[..., Any],
    apply_fix_fn: Callable[..., Any],
) -> Any:
    """使用 LangGraph StateGraph 构建执行图。"""
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
