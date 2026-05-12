"""Narrator Agent LangGraph 图定义。

3 个节点，error 时短路到 END：

    resolve_case --(ok)--> narrate --(ok)--> write_files → END
                 --(error)-----------------------------> END

Python 3.9 兼容：使用 ``from __future__ import annotations`` 延迟求值。
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from langgraph.graph import END, StateGraph


def _error_router(state: dict[str, Any]) -> str:
    return "end" if state.get("status") == "error" else "continue"


def build_narrator_graph(
    resolve_case_fn: Optional[Callable[..., Any]] = None,
    narrate_fn: Optional[Callable[..., Any]] = None,
    write_files_fn: Optional[Callable[..., Any]] = None,
) -> Any:
    """构建 Narrator Agent 的执行图。

    Parameters
    ----------
    resolve_case_fn, narrate_fn, write_files_fn:
        节点函数，允许注入自定义实现（方便测试时 Mock）。
        不提供时延迟导入默认实现。
    """
    if resolve_case_fn is None:
        from rodski_agent.narrator.nodes import resolve_case
        resolve_case_fn = resolve_case
    if narrate_fn is None:
        from rodski_agent.narrator.nodes import narrate
        narrate_fn = narrate
    if write_files_fn is None:
        from rodski_agent.narrator.nodes import write_files
        write_files_fn = write_files

    from rodski_agent.common.state import NarratorState

    graph = StateGraph(NarratorState)

    graph.add_node("resolve_case", resolve_case_fn)
    graph.add_node("narrate", narrate_fn)
    graph.add_node("write_files", write_files_fn)

    graph.set_entry_point("resolve_case")
    graph.add_conditional_edges(
        "resolve_case",
        _error_router,
        {"end": END, "continue": "narrate"},
    )
    graph.add_conditional_edges(
        "narrate",
        _error_router,
        {"end": END, "continue": "write_files"},
    )
    graph.add_edge("write_files", END)

    return graph.compile()

