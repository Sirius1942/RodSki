"""Design Agent LangGraph 图定义。

包含 5 个节点：

    analyze_req -> plan_cases -> design_data -> generate_xml -> validate_xml
                                                     ^                |
                                                     |-- (fail, <3) --+
                                                                      |
                                                              (pass) --> END

运行时自动检测 ``langgraph`` 是否可用：
  - 可用时使用 ``StateGraph`` 构建真正的 LangGraph 图；
  - 不可用时使用 ``SimpleGraph`` 替代，保持 ``invoke(state) -> state``
    接口一致。

Python 3.9 兼容：使用 ``from __future__ import annotations`` 延迟求值。
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

from rodski_agent.execution.graph import SimpleGraph

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# 检测 langgraph 可用性
# ------------------------------------------------------------------

try:
    from langgraph.graph import END, StateGraph

    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False


# ==================================================================
# 条件路由
# ==================================================================


def _validate_router(state: Dict[str, Any]) -> str:
    """validate_xml 后的条件路由。

    pass (status == "success") -> END
    fail + fix_attempt < 3 -> generate_xml (retry)
    fail + fix_attempt >= 3 -> END (give up)
    """
    status = state.get("status", "")
    if status == "success":
        return "end"

    fix_attempt = state.get("fix_attempt", 0)
    if fix_attempt < 3:
        return "generate_xml"
    return "end"


# ==================================================================
# 图构建函数
# ==================================================================


def build_design_graph(
    analyze_req_fn: Optional[Callable[..., Any]] = None,
    plan_cases_fn: Optional[Callable[..., Any]] = None,
    design_data_fn: Optional[Callable[..., Any]] = None,
    generate_xml_fn: Optional[Callable[..., Any]] = None,
    validate_xml_fn: Optional[Callable[..., Any]] = None,
) -> Any:
    """构建 Design Agent 的设计图。

    节点流：

        analyze_req -> plan_cases -> design_data -> generate_xml -> validate_xml
                                                         ^               |
                                                         +-- (fail) -----+
                                                                         |
                                                             (pass) --> END

    Parameters
    ----------
    analyze_req_fn, plan_cases_fn, design_data_fn, generate_xml_fn, validate_xml_fn:
        节点函数。允许注入自定义实现（方便测试时 Mock）。
        如果不提供，延迟导入 ``rodski_agent.design.nodes`` 中的默认实现。

    Returns
    -------
    graph
        编译后的图对象，支持 ``graph.invoke(state_dict)`` 调用。
    """
    # 延迟导入默认节点实现
    if analyze_req_fn is None:
        from rodski_agent.design.nodes import analyze_req

        analyze_req_fn = analyze_req
    if plan_cases_fn is None:
        from rodski_agent.design.nodes import plan_cases

        plan_cases_fn = plan_cases
    if design_data_fn is None:
        from rodski_agent.design.nodes import design_data

        design_data_fn = design_data
    if generate_xml_fn is None:
        from rodski_agent.design.nodes import generate_xml

        generate_xml_fn = generate_xml
    if validate_xml_fn is None:
        from rodski_agent.design.nodes import validate_xml

        validate_xml_fn = validate_xml

    if HAS_LANGGRAPH:
        return _build_langgraph(
            analyze_req_fn, plan_cases_fn, design_data_fn,
            generate_xml_fn, validate_xml_fn,
        )
    return _build_simple_graph(
        analyze_req_fn, plan_cases_fn, design_data_fn,
        generate_xml_fn, validate_xml_fn,
    )


# ------------------------------------------------------------------
# SimpleGraph 版本
# ------------------------------------------------------------------


def _build_simple_graph(
    analyze_req_fn: Callable[..., Any],
    plan_cases_fn: Callable[..., Any],
    design_data_fn: Callable[..., Any],
    generate_xml_fn: Callable[..., Any],
    validate_xml_fn: Callable[..., Any],
) -> SimpleGraph:
    """使用 SimpleGraph 构建设计图。"""
    return SimpleGraph(
        nodes=[
            ("analyze_req", analyze_req_fn),
            ("plan_cases", plan_cases_fn),
            ("design_data", design_data_fn),
            ("generate_xml", generate_xml_fn),
            ("validate_xml", validate_xml_fn),
        ],
        conditional_edges={
            "validate_xml": (
                _validate_router,
                {
                    "end": "__end__",
                    "generate_xml": "generate_xml",
                },
            ),
        },
    )


# ------------------------------------------------------------------
# LangGraph 版本
# ------------------------------------------------------------------


def _build_langgraph(
    analyze_req_fn: Callable[..., Any],
    plan_cases_fn: Callable[..., Any],
    design_data_fn: Callable[..., Any],
    generate_xml_fn: Callable[..., Any],
    validate_xml_fn: Callable[..., Any],
) -> Any:
    """使用 LangGraph StateGraph 构建设计图。"""
    from rodski_agent.common.state import DesignState

    graph = StateGraph(DesignState)

    # 添加节点
    graph.add_node("analyze_req", analyze_req_fn)
    graph.add_node("plan_cases", plan_cases_fn)
    graph.add_node("design_data", design_data_fn)
    graph.add_node("generate_xml", generate_xml_fn)
    graph.add_node("validate_xml", validate_xml_fn)

    # 设置入口
    graph.set_entry_point("analyze_req")

    # 线性边
    graph.add_edge("analyze_req", "plan_cases")
    graph.add_edge("plan_cases", "design_data")
    graph.add_edge("design_data", "generate_xml")
    graph.add_edge("generate_xml", "validate_xml")

    # 条件边：validate_xml 成功 -> END, 失败 -> generate_xml
    graph.add_conditional_edges(
        "validate_xml",
        _validate_router,
        {"end": END, "generate_xml": "generate_xml"},
    )

    return graph.compile()
