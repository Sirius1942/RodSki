"""Design Agent LangGraph 图定义。

包含 7 个节点（含可选视觉探索）：

    analyze_req -> explore_page -> identify_elem -> plan_cases -> design_data
                                                       -> generate_xml -> validate_xml
                                                             ^                |
                                                             |-- (fail, <3) --+
                                                                              |
                                                                      (pass) --> END

当不提供 target_url 时，explore_page 和 identify_elem 返回空列表。

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
    explore_page_fn: Optional[Callable[..., Any]] = None,
    identify_elem_fn: Optional[Callable[..., Any]] = None,
    plan_cases_fn: Optional[Callable[..., Any]] = None,
    design_data_fn: Optional[Callable[..., Any]] = None,
    design_model_fn: Optional[Callable[..., Any]] = None,
    generate_xml_fn: Optional[Callable[..., Any]] = None,
    validate_xml_fn: Optional[Callable[..., Any]] = None,
    load_skills_fn: Optional[Callable[..., Any]] = None,
    gap_analysis_fn: Optional[Callable[..., Any]] = None,
) -> Any:
    """构建 Design Agent 的设计图。

    节点流（含视觉探索）：

        analyze_req -> explore_page -> identify_elem -> plan_cases
            -> design_data -> generate_xml -> validate_xml
                                   ^               |
                                   +-- (fail) -----+
                                                    |
                                        (pass) --> END

    Parameters
    ----------
    analyze_req_fn, explore_page_fn, identify_elem_fn, plan_cases_fn,
    design_data_fn, design_model_fn, generate_xml_fn, validate_xml_fn:
        节点函数。允许注入自定义实现（方便测试时 Mock）。
        如果不提供，延迟导入默认实现。

    Returns
    -------
    graph
        编译后的图对象，支持 ``graph.invoke(state_dict)`` 调用。
    """
    # 延迟导入默认节点实现
    if analyze_req_fn is None:
        from rodski_agent.design.nodes import analyze_req

        analyze_req_fn = analyze_req
    if explore_page_fn is None:
        from rodski_agent.design.visual import explore_page

        explore_page_fn = explore_page
    if identify_elem_fn is None:
        from rodski_agent.design.visual import identify_elem

        identify_elem_fn = identify_elem
    if plan_cases_fn is None:
        from rodski_agent.design.nodes import plan_cases

        plan_cases_fn = plan_cases
    if design_data_fn is None:
        from rodski_agent.design.nodes import design_data

        design_data_fn = design_data
    if design_model_fn is None:
        from rodski_agent.design.nodes import design_model

        design_model_fn = design_model
    if generate_xml_fn is None:
        from rodski_agent.design.nodes import generate_xml

        generate_xml_fn = generate_xml
    if validate_xml_fn is None:
        from rodski_agent.design.nodes import validate_xml

        validate_xml_fn = validate_xml

    if load_skills_fn is None:
        def load_skills_fn(state: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore[misc]
            skills_dir = state.get("skills_dir")
            if not skills_dir:
                return {}
            from rodski_agent.design.skill_loader import load_skill_docs
            ctx = load_skill_docs(skills_dir)
            return {"skill_context": ctx.to_dict()}

    if gap_analysis_fn is None:
        from rodski_agent.design.nodes import gap_analysis

        gap_analysis_fn = gap_analysis

    from rodski_agent.common.state import DesignState

    graph = StateGraph(DesignState)

    # 添加节点
    graph.add_node("load_skills", load_skills_fn)
    graph.add_node("analyze_req", analyze_req_fn)
    graph.add_node("explore_page", explore_page_fn)
    graph.add_node("identify_elem", identify_elem_fn)
    graph.add_node("plan_cases", plan_cases_fn)
    graph.add_node("design_data", design_data_fn)
    graph.add_node("design_model", design_model_fn)
    graph.add_node("generate_xml", generate_xml_fn)
    graph.add_node("gap_analysis", gap_analysis_fn)
    graph.add_node("validate_xml", validate_xml_fn)

    # 设置入口
    graph.set_entry_point("load_skills")

    # 线性边
    graph.add_edge("load_skills", "analyze_req")
    graph.add_edge("analyze_req", "explore_page")
    graph.add_edge("explore_page", "identify_elem")
    graph.add_edge("identify_elem", "plan_cases")
    graph.add_edge("plan_cases", "design_data")
    graph.add_edge("design_data", "design_model")
    graph.add_edge("design_model", "generate_xml")
    graph.add_edge("generate_xml", "gap_analysis")
    graph.add_edge("gap_analysis", "validate_xml")

    # 条件边：validate_xml 成功 -> END, 失败 -> generate_xml
    graph.add_conditional_edges(
        "validate_xml",
        _validate_router,
        {"end": END, "generate_xml": "generate_xml"},
    )

    return graph.compile()
