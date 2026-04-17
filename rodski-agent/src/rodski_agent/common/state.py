"""共享状态定义 -- 用于 LangGraph 的 TypedDict State。

每个 Agent 拥有独立的 State 类型，字段以 TypedDict(total=False) 声明，
确保所有 key 均可选——节点只需返回自己负责的字段增量即可。

Python 3.9 兼容：使用 ``from __future__ import annotations`` 延迟求值。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


# ============================================================
# Execution Agent State
# ============================================================

class ExecutionState(TypedDict, total=False):
    """Execution Agent 的运行状态。

    字段分为四组：

    * **输入** -- 由调用方提供，描述执行目标。
    * **执行状态** -- 由 execute / parse_result 节点填充。
    * **诊断** -- V1 使用（MVP 阶段留空占位）。
    * **输出** -- report 节点生成最终报告。
    """

    # -- 输入 ----------------------------------------------------------
    case_path: str                    # 用例文件 / 目录路径
    max_retry: int                    # 最大重试次数（默认由 config 决定）
    headless: bool                    # 是否无头模式
    browser: str                      # 浏览器类型 (chromium / firefox / webkit)

    # -- 执行状态 ------------------------------------------------------
    execution_result: Dict[str, Any]  # rodski 原始执行结果
    case_results: List[Dict[str, Any]]
    # 每个 case 的结构化结果：[{id, title, status, time, error}, ...]
    screenshots: List[str]            # 截图路径列表

    # -- 诊断与重试 ---------------------------------------------------
    diagnosis: Optional[Dict[str, Any]]
    retry_count: int
    retry_decision: str               # "retry" | "give_up"
    fixes_applied: List[str]

    # -- 输出 ----------------------------------------------------------
    report: Dict[str, Any]            # 最终报告
    status: str                       # "running" | "pass" | "fail" | "partial" | "error"
    error: str                        # 错误信息（status == "error" 时有值）


# ============================================================
# Design Agent State (V1 使用，先定义接口)
# ============================================================

class DesignState(TypedDict, total=False):
    """Design Agent 的运行状态（V1 规划，MVP 不使用）。

    字段分为三组：输入、中间状态、控制。
    """

    # -- 输入 ----------------------------------------------------------
    requirement: str                  # 测试需求描述
    target_url: str                   # 被测系统 URL
    output_dir: str                   # 生成文件输出目录
    headless: bool                    # 截图时是否无头模式

    # -- 中间状态 ------------------------------------------------------
    test_scenarios: List[Dict[str, Any]]   # 测试场景列表
    page_elements: List[Dict[str, Any]]    # 页面元素（OmniParser 识别）
    screenshots: List[str]                 # 截图路径列表
    enriched_elements: List[Dict[str, Any]]  # LLM 语义增强后的元素信息
    case_plan: List[Dict[str, Any]]        # 用例编排计划
    test_data: List[Dict[str, Any]]        # 测试数据
    designed_models: Optional[Dict[str, Any]]  # LLM 推断的模型定义 {model_name: elements}
    generated_files: List[str]             # 已生成的文件路径

    # -- Skill 上下文 --------------------------------------------------
    skills_dir: Optional[str]                # skills/ 目录路径
    skill_context: Optional[Dict[str, Any]]  # SkillContext.to_dict() 序列化结果
    gap_report: Optional[Dict[str, Any]]     # {missing_models, missing_data, reusable}

    # -- 控制 ----------------------------------------------------------
    validation_errors: List[str]     # 校验错误列表
    fix_attempt: int                 # 当前修复尝试次数
    status: str                      # "running" | "done" | "error"
    error: str                       # 错误信息
    debug_round: int                 # 当前调试轮次（0=初次，最大3）
    debug_hints: Optional[List[Any]] # 调试建议列表（来自 debugger）
