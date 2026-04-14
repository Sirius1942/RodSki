"""重试机制单元测试 (Iteration 05)。

覆盖:
  - retry_decide 节点各种诊断结果
  - apply_fix 超时和元素定位修复策略
  - 执行图重试循环（mock execute 先失败再成功）
  - max_retry 限制
  - 非 CASE_DEFECT 类别放弃重试
"""
from __future__ import annotations

import pytest

from rodski_agent.execution.nodes import retry_decide
from rodski_agent.execution.fixer import apply_fix
from rodski_agent.execution.graph import (
    build_execution_graph,
    SimpleGraph,
    _retry_decide_router,
)


# ================================================================
# T05-001: retry_decide 节点测试
# ================================================================


class TestRetryDecide:
    """retry_decide 节点测试。"""

    def test_retry_on_case_defect_high_confidence(self):
        """CASE_DEFECT + confidence > 0.7 应返回 retry。"""
        state = {
            "diagnosis": {"category": "CASE_DEFECT", "confidence": 0.85},
            "retry_count": 0,
            "max_retry": 3,
        }
        result = retry_decide(state)
        assert result["retry_decision"] == "retry"
        assert result["retry_count"] == 1

    def test_give_up_at_max_retry(self):
        """已达最大重试次数时应返回 give_up。"""
        state = {
            "diagnosis": {"category": "CASE_DEFECT", "confidence": 0.9},
            "retry_count": 3,
            "max_retry": 3,
        }
        result = retry_decide(state)
        assert result["retry_decision"] == "give_up"

    def test_give_up_on_env_defect(self):
        """ENV_DEFECT 不可重试，应返回 give_up。"""
        state = {
            "diagnosis": {"category": "ENV_DEFECT", "confidence": 0.9},
            "retry_count": 0,
            "max_retry": 3,
        }
        result = retry_decide(state)
        assert result["retry_decision"] == "give_up"

    def test_give_up_on_product_defect(self):
        """PRODUCT_DEFECT 不可重试，应返回 give_up。"""
        state = {
            "diagnosis": {"category": "PRODUCT_DEFECT", "confidence": 0.9},
            "retry_count": 0,
            "max_retry": 3,
        }
        result = retry_decide(state)
        assert result["retry_decision"] == "give_up"

    def test_give_up_on_unknown(self):
        """UNKNOWN 不可重试，应返回 give_up。"""
        state = {
            "diagnosis": {"category": "UNKNOWN", "confidence": 0.9},
            "retry_count": 0,
            "max_retry": 3,
        }
        result = retry_decide(state)
        assert result["retry_decision"] == "give_up"

    def test_give_up_on_low_confidence(self):
        """CASE_DEFECT 但 confidence <= 0.7 应返回 give_up。"""
        state = {
            "diagnosis": {"category": "CASE_DEFECT", "confidence": 0.7},
            "retry_count": 0,
            "max_retry": 3,
        }
        result = retry_decide(state)
        assert result["retry_decision"] == "give_up"

    def test_give_up_on_confidence_boundary(self):
        """confidence == 0.7 时应返回 give_up（不满足 > 0.7）。"""
        state = {
            "diagnosis": {"category": "CASE_DEFECT", "confidence": 0.7},
            "retry_count": 0,
            "max_retry": 3,
        }
        result = retry_decide(state)
        assert result["retry_decision"] == "give_up"

    def test_retry_increments_count(self):
        """重试时 retry_count 应递增。"""
        state = {
            "diagnosis": {"category": "CASE_DEFECT", "confidence": 0.9},
            "retry_count": 1,
            "max_retry": 3,
        }
        result = retry_decide(state)
        assert result["retry_decision"] == "retry"
        assert result["retry_count"] == 2

    def test_give_up_when_max_retry_zero(self):
        """max_retry = 0 时不重试。"""
        state = {
            "diagnosis": {"category": "CASE_DEFECT", "confidence": 0.9},
            "retry_count": 0,
            "max_retry": 0,
        }
        result = retry_decide(state)
        assert result["retry_decision"] == "give_up"

    def test_missing_diagnosis(self):
        """无 diagnosis 时应返回 give_up。"""
        state = {
            "retry_count": 0,
            "max_retry": 3,
        }
        result = retry_decide(state)
        assert result["retry_decision"] == "give_up"

    def test_empty_diagnosis(self):
        """空 diagnosis dict 时应返回 give_up。"""
        state = {
            "diagnosis": {},
            "retry_count": 0,
            "max_retry": 3,
        }
        result = retry_decide(state)
        assert result["retry_decision"] == "give_up"

    def test_defaults_when_missing_fields(self):
        """缺少 retry_count 和 max_retry 时应使用默认值。"""
        state = {
            "diagnosis": {"category": "CASE_DEFECT", "confidence": 0.9},
        }
        # max_retry defaults to 0, so retry_count(0) >= max_retry(0) -> give_up
        result = retry_decide(state)
        assert result["retry_decision"] == "give_up"


# ================================================================
# T05-002: apply_fix 修复策略测试
# ================================================================


class TestApplyFix:
    """apply_fix 修复策略测试。"""

    def test_timeout_fix(self):
        """timeout root_cause 应添加 wait 修复。"""
        state = {
            "diagnosis": {
                "root_cause": "Timeout waiting for element",
                "suggestion": "increase wait time",
            },
            "fixes_applied": [],
        }
        result = apply_fix(state)
        assert len(result["fixes_applied"]) == 1
        assert "wait" in result["fixes_applied"][0].lower()
        assert result["status"] == "running"

    def test_timeout_fix_chinese(self):
        """中文「超时」root_cause 应添加 wait 修复。"""
        state = {
            "diagnosis": {
                "root_cause": "页面加载超时",
                "suggestion": "增加等待时间",
            },
            "fixes_applied": [],
        }
        result = apply_fix(state)
        assert len(result["fixes_applied"]) == 1
        assert "wait" in result["fixes_applied"][0].lower()

    def test_element_not_found_fix(self):
        """element not found root_cause 应记录 locator 修复建议。"""
        state = {
            "diagnosis": {
                "root_cause": "Element not found: #login-btn",
                "suggestion": "update CSS selector to .login-button",
            },
            "fixes_applied": [],
        }
        result = apply_fix(state)
        assert len(result["fixes_applied"]) == 1
        assert "locator_fix_suggested" in result["fixes_applied"][0]
        assert "update CSS selector" in result["fixes_applied"][0]

    def test_locator_fix(self):
        """locator root_cause 应记录 locator 修复建议。"""
        state = {
            "diagnosis": {
                "root_cause": "Invalid locator type",
                "suggestion": "use css selector instead",
            },
            "fixes_applied": [],
        }
        result = apply_fix(state)
        assert len(result["fixes_applied"]) == 1
        assert "locator_fix_suggested" in result["fixes_applied"][0]

    def test_chinese_element_fix(self):
        """中文「元素」root_cause 应记录 locator 修复建议。"""
        state = {
            "diagnosis": {
                "root_cause": "找不到元素",
                "suggestion": "检查元素定位器",
            },
            "fixes_applied": [],
        }
        result = apply_fix(state)
        assert len(result["fixes_applied"]) == 1
        assert "locator_fix_suggested" in result["fixes_applied"][0]

    def test_unknown_cause_no_fix(self):
        """无法识别的 root_cause 不应添加修复。"""
        state = {
            "diagnosis": {
                "root_cause": "assertion failed",
                "suggestion": "check expected value",
            },
            "fixes_applied": [],
        }
        result = apply_fix(state)
        assert len(result["fixes_applied"]) == 0
        assert result["status"] == "running"

    def test_preserves_existing_fixes(self):
        """应保留已有的修复记录。"""
        state = {
            "diagnosis": {
                "root_cause": "Timeout",
                "suggestion": "wait more",
            },
            "fixes_applied": ["previous_fix_1"],
        }
        result = apply_fix(state)
        assert len(result["fixes_applied"]) == 2
        assert result["fixes_applied"][0] == "previous_fix_1"

    def test_empty_diagnosis(self):
        """空 diagnosis 不应添加修复。"""
        state = {
            "diagnosis": {},
            "fixes_applied": [],
        }
        result = apply_fix(state)
        assert len(result["fixes_applied"]) == 0
        assert result["status"] == "running"


# ================================================================
# T05-003: 执行图重试循环测试
# ================================================================


class TestRetryDecideRouter:
    """retry_decide 路由函数测试。"""

    def test_router_retry(self):
        """retry_decision == retry 应路由到 apply_fix。"""
        assert _retry_decide_router({"retry_decision": "retry"}) == "apply_fix"

    def test_router_give_up(self):
        """retry_decision == give_up 应路由到 report。"""
        assert _retry_decide_router({"retry_decision": "give_up"}) == "report"

    def test_router_missing_decision(self):
        """缺少 retry_decision 时默认路由到 report。"""
        assert _retry_decide_router({}) == "report"


class TestExecutionGraphRetryLoop:
    """执行图重试循环集成测试。"""

    def test_retry_loop_succeed_on_second_try(self):
        """首次执行失败，重试后成功的完整流程。"""
        call_log = []
        execute_count = [0]

        def mock_pre_check(s):
            call_log.append("pre_check")
            return {"status": "running"}

        def mock_execute(s):
            execute_count[0] += 1
            call_log.append(f"execute_{execute_count[0]}")
            if execute_count[0] == 1:
                return {"execution_result": {"exit_code": 1}}
            return {"execution_result": {"exit_code": 0}}

        def mock_parse_result(s):
            call_log.append("parse_result")
            exit_code = s.get("execution_result", {}).get("exit_code", -1)
            if exit_code == 0:
                return {"case_results": [{"id": "c001", "status": "PASS", "time": 1.0}]}
            return {"case_results": [{"id": "c001", "status": "FAIL", "error": "timeout", "time": 1.0}]}

        def mock_diagnose(s):
            call_log.append("diagnose")
            return {
                "diagnosis": {
                    "category": "CASE_DEFECT",
                    "confidence": 0.9,
                    "root_cause": "Timeout waiting for element",
                    "suggestion": "add wait",
                    "cases": [{"case_id": "c001"}],
                    "skipped": False,
                },
            }

        def mock_report(s):
            call_log.append("report")
            cases = s.get("case_results", [])
            passed = sum(1 for c in cases if c.get("status") == "PASS")
            failed = len(cases) - passed
            status = "pass" if failed == 0 else "fail"
            return {"report": {"total": len(cases), "passed": passed, "failed": failed}, "status": status}

        g = build_execution_graph(
            mock_pre_check, mock_execute, mock_parse_result,
            mock_diagnose, mock_report,
        )
        result = g.invoke({"case_path": "/fake", "headless": True, "max_retry": 3})

        # Should have retried
        assert execute_count[0] == 2
        assert result["status"] == "pass"
        assert result["retry_count"] == 1
        assert "execute_1" in call_log
        assert "execute_2" in call_log
        assert "diagnose" in call_log
        assert "report" in call_log

    def test_retry_loop_exhaust_max_retry(self):
        """持续失败直到耗尽重试次数。"""
        execute_count = [0]

        def mock_pre_check(s):
            return {"status": "running"}

        def mock_execute(s):
            execute_count[0] += 1
            return {"execution_result": {"exit_code": 1}}

        def mock_parse_result(s):
            return {"case_results": [{"id": "c001", "status": "FAIL", "error": "timeout", "time": 1.0}]}

        def mock_diagnose(s):
            return {
                "diagnosis": {
                    "category": "CASE_DEFECT",
                    "confidence": 0.9,
                    "root_cause": "Timeout",
                    "suggestion": "add wait",
                    "cases": [{"case_id": "c001"}],
                    "skipped": False,
                },
            }

        def mock_report(s):
            cases = s.get("case_results", [])
            return {"report": {"total": len(cases), "passed": 0, "failed": len(cases)}, "status": "fail"}

        g = build_execution_graph(
            mock_pre_check, mock_execute, mock_parse_result,
            mock_diagnose, mock_report,
        )
        result = g.invoke({"case_path": "/fake", "headless": True, "max_retry": 2})

        # execute 1 (fail) + retry 1 (fail) + retry 2 (fail) = 3 times
        assert execute_count[0] == 3
        assert result["status"] == "fail"
        assert result["retry_count"] == 2

    def test_no_retry_when_all_pass(self):
        """全部通过时不触发重试。"""
        call_log = []

        def mock_pre_check(s):
            call_log.append("pre_check")
            return {"status": "running"}

        def mock_execute(s):
            call_log.append("execute")
            return {"execution_result": {"exit_code": 0}}

        def mock_parse_result(s):
            call_log.append("parse_result")
            return {"case_results": [{"id": "c001", "status": "PASS", "time": 1.0}]}

        def mock_diagnose(s):
            call_log.append("diagnose")
            return {"diagnosis": {"skipped": True}}

        def mock_report(s):
            call_log.append("report")
            return {"report": {"total": 1, "passed": 1, "failed": 0}, "status": "pass"}

        g = build_execution_graph(
            mock_pre_check, mock_execute, mock_parse_result,
            mock_diagnose, mock_report,
        )
        result = g.invoke({"case_path": "/fake", "headless": True, "max_retry": 3})

        assert result["status"] == "pass"
        assert "diagnose" not in call_log
        assert "retry_decide" not in call_log

    def test_no_retry_on_env_defect(self):
        """ENV_DEFECT 不重试，直接 give_up。"""
        execute_count = [0]

        def mock_pre_check(s):
            return {"status": "running"}

        def mock_execute(s):
            execute_count[0] += 1
            return {"execution_result": {"exit_code": 1}}

        def mock_parse_result(s):
            return {"case_results": [{"id": "c001", "status": "FAIL", "error": "env error", "time": 1.0}]}

        def mock_diagnose(s):
            return {
                "diagnosis": {
                    "category": "ENV_DEFECT",
                    "confidence": 0.9,
                    "root_cause": "Browser not installed",
                    "suggestion": "install browser",
                    "cases": [{"case_id": "c001"}],
                    "skipped": False,
                },
            }

        def mock_report(s):
            return {"report": {"total": 1, "passed": 0, "failed": 1}, "status": "fail"}

        g = build_execution_graph(
            mock_pre_check, mock_execute, mock_parse_result,
            mock_diagnose, mock_report,
        )
        result = g.invoke({"case_path": "/fake", "headless": True, "max_retry": 3})

        assert execute_count[0] == 1  # No retry
        assert result["status"] == "fail"

    def test_no_retry_when_max_retry_zero(self):
        """max_retry = 0 时不重试。"""
        execute_count = [0]

        def mock_pre_check(s):
            return {"status": "running"}

        def mock_execute(s):
            execute_count[0] += 1
            return {"execution_result": {"exit_code": 1}}

        def mock_parse_result(s):
            return {"case_results": [{"id": "c001", "status": "FAIL", "error": "timeout", "time": 1.0}]}

        def mock_diagnose(s):
            return {
                "diagnosis": {
                    "category": "CASE_DEFECT",
                    "confidence": 0.9,
                    "root_cause": "Timeout",
                    "suggestion": "add wait",
                    "cases": [{"case_id": "c001"}],
                    "skipped": False,
                },
            }

        def mock_report(s):
            return {"report": {"total": 1, "passed": 0, "failed": 1}, "status": "fail"}

        g = build_execution_graph(
            mock_pre_check, mock_execute, mock_parse_result,
            mock_diagnose, mock_report,
        )
        result = g.invoke({"case_path": "/fake", "headless": True, "max_retry": 0})

        assert execute_count[0] == 1  # No retry
        assert result["status"] == "fail"

    def test_fixes_applied_accumulate(self):
        """多次重试中 fixes_applied 应累积。"""
        execute_count = [0]

        def mock_pre_check(s):
            return {"status": "running"}

        def mock_execute(s):
            execute_count[0] += 1
            if execute_count[0] <= 2:
                return {"execution_result": {"exit_code": 1}}
            return {"execution_result": {"exit_code": 0}}

        def mock_parse_result(s):
            exit_code = s.get("execution_result", {}).get("exit_code", -1)
            if exit_code == 0:
                return {"case_results": [{"id": "c001", "status": "PASS", "time": 1.0}]}
            return {"case_results": [{"id": "c001", "status": "FAIL", "error": "timeout", "time": 1.0}]}

        def mock_diagnose(s):
            return {
                "diagnosis": {
                    "category": "CASE_DEFECT",
                    "confidence": 0.9,
                    "root_cause": "Timeout waiting for element",
                    "suggestion": "add wait",
                    "cases": [{"case_id": "c001"}],
                    "skipped": False,
                },
            }

        def mock_report(s):
            cases = s.get("case_results", [])
            passed = sum(1 for c in cases if c.get("status") == "PASS")
            status = "pass" if passed == len(cases) else "fail"
            return {"report": {"total": len(cases), "passed": passed, "failed": len(cases) - passed}, "status": status}

        g = build_execution_graph(
            mock_pre_check, mock_execute, mock_parse_result,
            mock_diagnose, mock_report,
        )
        result = g.invoke({"case_path": "/fake", "headless": True, "max_retry": 5})

        assert execute_count[0] == 3
        assert result["status"] == "pass"
        assert result["retry_count"] == 2
        assert len(result.get("fixes_applied", [])) == 2


# ================================================================
# T05-005: SimpleGraph 循环保护测试
# ================================================================


class TestSimpleGraphLoopProtection:
    """SimpleGraph 循环保护测试。"""

    def test_max_loop_prevents_infinite_loop(self):
        """max_loop 参数应防止无限循环。"""
        call_count = [0]

        def always_loop(s):
            call_count[0] += 1
            return {"loop": True}

        g = SimpleGraph(
            nodes=[("a", always_loop), ("b", always_loop)],
            conditional_edges={
                "b": (lambda s: "a", {"a": "a"}),
            },
            max_loop=3,
        )
        result = g.invoke({})
        assert result["status"] == "error"
        assert "Max loop count" in result["error"]
        # Should not run indefinitely
        assert call_count[0] <= 10


# ================================================================
# T05-005: build_execution_graph 接受新参数
# ================================================================


class TestBuildExecutionGraphNewParams:
    """验证 build_execution_graph 接受 retry_decide_fn 和 apply_fix_fn。"""

    def test_custom_retry_decide_fn(self):
        """注入自定义 retry_decide_fn。"""
        def mock_pre_check(s): return {"status": "running"}
        def mock_execute(s): return {"execution_result": {"exit_code": 1}}
        def mock_parse_result(s):
            return {"case_results": [{"id": "c001", "status": "FAIL", "error": "err", "time": 1.0}]}
        def mock_diagnose(s):
            return {"diagnosis": {"category": "CASE_DEFECT", "confidence": 0.9, "root_cause": "x", "suggestion": "y"}}
        def mock_report(s):
            return {"report": {"total": 1, "passed": 0, "failed": 1}, "status": "fail"}
        def custom_retry_decide(s):
            return {"retry_decision": "give_up", "custom_marker": True}
        def custom_apply_fix(s):
            return {"fixes_applied": ["custom_fix"], "status": "running"}

        g = build_execution_graph(
            mock_pre_check, mock_execute, mock_parse_result,
            mock_diagnose, mock_report,
            retry_decide_fn=custom_retry_decide,
            apply_fix_fn=custom_apply_fix,
        )
        result = g.invoke({"case_path": "/fake", "headless": True, "max_retry": 3})

        assert result.get("custom_marker") is True
        assert result["status"] == "fail"
