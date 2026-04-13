"""诊断引擎单元测试

测试 DiagnosisEngine 的规则映射、AI 视觉分析和 LLMClient 集成。
"""

from __future__ import annotations

import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# 路径修正：确保 rodski/ 包在 sys.path 中
# ---------------------------------------------------------------------------
_RODSKI_ROOT = pathlib.Path(__file__).parent.parent.parent  # rodski/
if str(_RODSKI_ROOT) not in sys.path:
    sys.path.insert(0, str(_RODSKI_ROOT))

from core.diagnosis_engine import DiagnosisEngine, DiagnosisReport


# ===========================================================================
# Tests: DiagnosisReport
# ===========================================================================

class TestDiagnosisReport(unittest.TestCase):
    def test_to_dict_returns_all_fields(self):
        report = DiagnosisReport(
            failure_point="case=TC001, step=3",
            failure_reason="Element not found",
            visual_analysis="页面加载中",
            suggestion="等待 3s 后重试",
            recovery_action={"action": "wait", "data": "3"},
        )
        d = report.to_dict()
        self.assertEqual(d["failure_point"], "case=TC001, step=3")
        self.assertEqual(d["failure_reason"], "Element not found")
        self.assertEqual(d["recovery_action"]["action"], "wait")

    def test_defaults(self):
        report = DiagnosisReport()
        self.assertEqual(report.failure_point, "")
        self.assertEqual(report.ai_model, "claude")
        self.assertEqual(report.recovery_action, {})


# ===========================================================================
# Tests: DiagnosisEngine — rule mapping
# ===========================================================================

class TestDiagnosisEngineRuleMapping(unittest.TestCase):
    def setUp(self):
        self.engine = DiagnosisEngine()

    def test_element_not_found_maps_to_wait(self):
        class ElementNotFoundError(Exception):
            pass

        report = self.engine.diagnose(ElementNotFoundError("btn not found"))
        self.assertEqual(report.recovery_action["action"], "wait")
        self.assertEqual(report.recovery_action["data"], "3")

    def test_timeout_maps_to_refresh(self):
        report = self.engine.diagnose(TimeoutError("page timeout"))
        self.assertEqual(report.recovery_action["action"], "refresh")

    def test_unknown_error_maps_to_empty(self):
        report = self.engine.diagnose(RuntimeError("something random"))
        self.assertEqual(report.recovery_action, {})

    def test_unrecoverable_error_maps_to_abort(self):
        class UnknownKeywordError(Exception):
            pass

        report = self.engine.diagnose(UnknownKeywordError("bad keyword"))
        self.assertEqual(report.recovery_action["action"], "abort")

    def test_context_formats_failure_point(self):
        report = self.engine.diagnose(
            RuntimeError("err"),
            context={"case_id": "TC001", "step_index": 5, "keyword": "click"},
        )
        self.assertIn("TC001", report.failure_point)
        self.assertIn("step=5", report.failure_point)
        self.assertIn("keyword=click", report.failure_point)

    def test_no_context_returns_unknown(self):
        report = self.engine.diagnose(RuntimeError("err"))
        self.assertEqual(report.failure_point, "unknown")


# ===========================================================================
# Tests: DiagnosisEngine — __init__ llm_client parameter
# ===========================================================================

class TestDiagnosisEngineInit(unittest.TestCase):
    def test_default_no_llm_client(self):
        engine = DiagnosisEngine()
        self.assertIsNone(engine._llm_client)

    def test_llm_client_stored(self):
        mock_client = MagicMock()
        engine = DiagnosisEngine(llm_client=mock_client)
        self.assertIs(engine._llm_client, mock_client)

    def test_ai_verifier_stored(self):
        mock_verifier = MagicMock()
        engine = DiagnosisEngine(ai_verifier=mock_verifier)
        self.assertIs(engine._ai_verifier, mock_verifier)


# ===========================================================================
# Tests: DiagnosisEngine — visual analysis with llm_client
# ===========================================================================

class TestDiagnosisEngineVisualAnalysis(unittest.TestCase):
    def test_llm_client_used_when_available(self):
        mock_verifier_cap = MagicMock()
        mock_verifier_cap.verify.return_value = (False, "页面显示 404 错误")
        mock_client = MagicMock()
        mock_client.get_capability.return_value = mock_verifier_cap

        engine = DiagnosisEngine(llm_client=mock_client)
        report = engine.diagnose(
            TimeoutError("page timeout"),
            screenshot_path="/fake/screenshot.png",
        )

        mock_client.get_capability.assert_called_with("screenshot_verifier")
        mock_verifier_cap.verify.assert_called_once()
        self.assertEqual(report.visual_analysis, "页面显示 404 错误")

    def test_fallback_to_ai_verifier_when_llm_client_fails(self):
        mock_client = MagicMock()
        mock_client.get_capability.side_effect = RuntimeError("LLM unavailable")

        mock_ai_verifier = MagicMock()
        mock_ai_verifier.verify.return_value = (False, "页面空白")

        engine = DiagnosisEngine(
            ai_verifier=mock_ai_verifier,
            llm_client=mock_client,
        )
        report = engine.diagnose(
            TimeoutError("page timeout"),
            screenshot_path="/fake/screenshot.png",
        )

        # Should fall back to ai_verifier
        mock_ai_verifier.verify.assert_called_once()
        self.assertEqual(report.visual_analysis, "页面空白")

    def test_ai_verifier_used_when_no_llm_client(self):
        mock_ai_verifier = MagicMock()
        mock_ai_verifier.verify.return_value = (True, "页面正常")

        engine = DiagnosisEngine(ai_verifier=mock_ai_verifier)
        report = engine.diagnose(
            RuntimeError("err"),
            screenshot_path="/fake/screenshot.png",
        )

        mock_ai_verifier.verify.assert_called_once()
        self.assertEqual(report.visual_analysis, "页面正常")

    def test_no_visual_analysis_without_screenshot(self):
        mock_client = MagicMock()
        engine = DiagnosisEngine(llm_client=mock_client)
        report = engine.diagnose(RuntimeError("err"))
        self.assertEqual(report.visual_analysis, "")
        mock_client.get_capability.assert_not_called()

    def test_no_visual_analysis_without_any_analyzer(self):
        engine = DiagnosisEngine()
        report = engine.diagnose(
            RuntimeError("err"),
            screenshot_path="/fake/screenshot.png",
        )
        self.assertEqual(report.visual_analysis, "")

    def test_both_fail_returns_error_message(self):
        mock_client = MagicMock()
        mock_client.get_capability.side_effect = RuntimeError("LLM down")

        mock_ai_verifier = MagicMock()
        mock_ai_verifier.verify.side_effect = RuntimeError("AI verifier down")

        engine = DiagnosisEngine(
            ai_verifier=mock_ai_verifier,
            llm_client=mock_client,
        )
        report = engine.diagnose(
            RuntimeError("err"),
            screenshot_path="/fake/screenshot.png",
        )
        self.assertIn("AI 分析不可用", report.visual_analysis)


# ===========================================================================
# Entry point
# ===========================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
