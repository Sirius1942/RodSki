"""视觉定位 LLM 语义识别层单元测试

使用 unittest.mock 隔离所有外部 API 调用，不依赖 pytest。
通过 RodSki 项目约定的 unittest 风格编写。
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import types
import unittest
from unittest.mock import MagicMock, patch, mock_open

# ---------------------------------------------------------------------------
# 路径修正：确保 rodski/ 包在 sys.path 中
# ---------------------------------------------------------------------------
_RODSKI_ROOT = pathlib.Path(__file__).parent.parent.parent  # rodski/
if str(_RODSKI_ROOT) not in sys.path:
    sys.path.insert(0, str(_RODSKI_ROOT))

from vision.llm_analyzer import LLMAnalyzer
from vision.matcher import VisionMatcher, _normalize, _tokenize, _score


# ===========================================================================
# Fixtures / helpers
# ===========================================================================

SAMPLE_ELEMENTS = [
    {"index": 0, "content": "Login", "type": "button", "bbox": [0.1, 0.2, 0.3, 0.4]},
    {"index": 1, "content": "Username", "type": "input", "bbox": [0.1, 0.5, 0.4, 0.6]},
    {"index": 2, "content": "Submit form", "type": "button", "bbox": [0.5, 0.8, 0.9, 0.9]},
]

SAMPLE_LABELS = [
    {"index": 0, "semantic_label": "登录按钮"},
    {"index": 1, "semantic_label": "用户名输入框"},
    {"index": 2, "semantic_label": "提交表单按钮"},
]

LABELED_ELEMENTS = [
    {**e, "semantic_label": SAMPLE_LABELS[e["index"]]["semantic_label"]}
    for e in SAMPLE_ELEMENTS
]


def _make_fake_llm_module(mock_client_class=None):
    """Create a fake rodski.llm module with a mocked LLMClient."""
    mod = types.ModuleType("rodski.llm")
    if mock_client_class is None:
        mock_client_class = MagicMock()
    mod.LLMClient = mock_client_class  # type: ignore[attr-defined]
    return mod


# ===========================================================================
# Tests: LLMAnalyzer
# ===========================================================================

class TestLLMAnalyzerMergeLabels(unittest.TestCase):
    """Test _merge_labels without any API calls."""

    def setUp(self):
        fake_mod = _make_fake_llm_module()
        with patch.dict(sys.modules, {"rodski.llm": fake_mod}):
            self.analyzer = LLMAnalyzer()

    def test_merge_attaches_semantic_labels(self):
        result = self.analyzer._merge_labels(SAMPLE_ELEMENTS, SAMPLE_LABELS)
        self.assertEqual(result[0]["semantic_label"], "登录按钮")
        self.assertEqual(result[1]["semantic_label"], "用户名输入框")
        self.assertEqual(result[2]["semantic_label"], "提交表单按钮")

    def test_merge_preserves_original_fields(self):
        result = self.analyzer._merge_labels(SAMPLE_ELEMENTS, SAMPLE_LABELS)
        self.assertEqual(result[0]["bbox"], [0.1, 0.2, 0.3, 0.4])
        self.assertEqual(result[0]["type"], "button")

    def test_merge_missing_label_falls_back_to_content(self):
        result = self.analyzer._merge_labels(SAMPLE_ELEMENTS, [])
        self.assertEqual(result[0]["semantic_label"], "Login")

    def test_merge_returns_same_length(self):
        result = self.analyzer._merge_labels(SAMPLE_ELEMENTS, SAMPLE_LABELS)
        self.assertEqual(len(result), len(SAMPLE_ELEMENTS))


class TestLLMAnalyzerAnalyze(unittest.TestCase):
    """Test the public analyze() method with mocked LLMClient."""

    def _make_analyzer(self, disabled=False):
        """Create an LLMAnalyzer with mocked LLMClient."""
        if disabled:
            # Simulate LLMClient init failure
            with patch.dict(sys.modules, {"rodski.llm": None}):
                return LLMAnalyzer()
        else:
            mock_capability = MagicMock()
            mock_capability.execute.return_value = LABELED_ELEMENTS
            mock_client_instance = MagicMock()
            mock_client_instance.get_capability.return_value = mock_capability
            mock_client_class = MagicMock(return_value=mock_client_instance)
            fake_mod = _make_fake_llm_module(mock_client_class)
            with patch.dict(sys.modules, {"rodski.llm": fake_mod}):
                analyzer = LLMAnalyzer()
            return analyzer

    def test_analyze_returns_enhanced_elements(self):
        analyzer = self._make_analyzer()
        result = analyzer.analyze("/fake/screenshot.png", SAMPLE_ELEMENTS)
        self.assertEqual(result[0]["semantic_label"], "登录按钮")
        self.assertEqual(len(result), 3)

    def test_analyze_empty_elements_returns_empty(self):
        analyzer = self._make_analyzer()
        result = analyzer.analyze("/fake/screenshot.png", [])
        self.assertEqual(result, [])

    def test_analyze_disabled_returns_original(self):
        analyzer = self._make_analyzer(disabled=True)
        self.assertTrue(analyzer._disabled)
        result = analyzer.analyze("/fake/screenshot.png", SAMPLE_ELEMENTS)
        # Should return original (no semantic_label added)
        self.assertNotIn("semantic_label", result[0])

    def test_analyze_delegates_to_capability(self):
        mock_capability = MagicMock()
        mock_capability.execute.return_value = LABELED_ELEMENTS
        mock_client_instance = MagicMock()
        mock_client_instance.get_capability.return_value = mock_capability
        mock_client_class = MagicMock(return_value=mock_client_instance)
        fake_mod = _make_fake_llm_module(mock_client_class)
        with patch.dict(sys.modules, {"rodski.llm": fake_mod}):
            analyzer = LLMAnalyzer()
        analyzer.analyze("/fake/screenshot.png", SAMPLE_ELEMENTS)
        mock_capability.execute.assert_called_once_with("/fake/screenshot.png", SAMPLE_ELEMENTS)


class TestLLMAnalyzerDisabledFlag(unittest.TestCase):
    """Test that _disabled flag is set correctly."""

    def test_disabled_when_llm_client_fails(self):
        with patch.dict(sys.modules, {"rodski.llm": None}):
            analyzer = LLMAnalyzer()
        self.assertTrue(analyzer._disabled)
        self.assertIsNone(analyzer._client)
        self.assertIsNone(analyzer._capability)

    def test_enabled_when_llm_client_succeeds(self):
        fake_mod = _make_fake_llm_module()
        with patch.dict(sys.modules, {"rodski.llm": fake_mod}):
            analyzer = LLMAnalyzer()
        self.assertFalse(analyzer._disabled)


# ===========================================================================
# Tests: VisionMatcher helpers
# ===========================================================================

class TestNormalize(unittest.TestCase):
    def test_lowercases_and_strips(self):
        self.assertEqual(_normalize("  Hello World  "), "hello world")

    def test_empty_string(self):
        self.assertEqual(_normalize(""), "")


class TestTokenize(unittest.TestCase):
    def test_splits_on_spaces(self):
        tokens = _tokenize("login button")
        self.assertIn("login", tokens)
        self.assertIn("button", tokens)

    def test_chinese_single_chars_included(self):
        tokens = _tokenize("登录")
        self.assertTrue(len(tokens) > 0)

    def test_filters_single_latin_chars(self):
        tokens = _tokenize("a b c login")
        self.assertNotIn("a", tokens)
        self.assertIn("login", tokens)


class TestScore(unittest.TestCase):
    def test_exact_match_returns_1(self):
        self.assertEqual(_score("登录按钮", "登录按钮"), 1.0)

    def test_exact_match_case_insensitive(self):
        self.assertEqual(_score("Login Button", "login button"), 1.0)

    def test_containment_returns_0_8(self):
        self.assertEqual(_score("登录", "登录按钮"), 0.8)

    def test_reverse_containment_returns_0_8(self):
        self.assertEqual(_score("登录按钮", "登录"), 0.8)

    def test_keyword_overlap_returns_0_6(self):
        score = _score("submit form", "form submission button")
        self.assertEqual(score, 0.6)

    def test_no_match_returns_none(self):
        self.assertIsNone(_score("completely unrelated", "xyz abc"))

    def test_empty_target_returns_none(self):
        self.assertIsNone(_score("", "登录按钮"))

# ===========================================================================
# Tests: VisionMatcher
# ===========================================================================

class TestVisionMatcherMatch(unittest.TestCase):
    def setUp(self):
        self.matcher = VisionMatcher()

    def test_match_exact_returns_element(self):
        result = self.matcher.match("登录按钮", LABELED_ELEMENTS)
        self.assertIsNotNone(result)
        self.assertEqual(result["semantic_label"], "登录按钮")
        self.assertEqual(result["confidence"], 1.0)

    def test_match_containment_returns_element(self):
        result = self.matcher.match("登录", LABELED_ELEMENTS)
        self.assertIsNotNone(result)
        self.assertEqual(result["confidence"], 0.8)

    def test_match_no_hit_returns_none(self):
        result = self.matcher.match("不存在的按钮xyz", LABELED_ELEMENTS)
        self.assertIsNone(result)

    def test_match_empty_elements_returns_none(self):
        result = self.matcher.match("登录按钮", [])
        self.assertIsNone(result)

    def test_match_empty_target_returns_none(self):
        result = self.matcher.match("", LABELED_ELEMENTS)
        self.assertIsNone(result)

    def test_match_returns_highest_confidence(self):
        # "登录" matches both "登录按钮" (0.8) via containment
        # should still return the top one
        result = self.matcher.match("登录", LABELED_ELEMENTS)
        self.assertIsNotNone(result)
        # Best confidence is 0.8 (containment in "登录按钮")
        self.assertGreaterEqual(result["confidence"], 0.8)


class TestVisionMatcherMatchAll(unittest.TestCase):
    def setUp(self):
        self.matcher = VisionMatcher()

    def test_match_all_sorted_by_confidence_desc(self):
        results = self.matcher.match_all("登录", LABELED_ELEMENTS)
        self.assertTrue(len(results) > 0)
        confidences = [r["confidence"] for r in results]
        self.assertEqual(confidences, sorted(confidences, reverse=True))

    def test_match_all_contains_confidence_field(self):
        results = self.matcher.match_all("按钮", LABELED_ELEMENTS)
        for r in results:
            self.assertIn("confidence", r)

    def test_match_all_no_match_returns_empty_list(self):
        results = self.matcher.match_all("zzznomatch", LABELED_ELEMENTS)
        self.assertEqual(results, [])

    def test_match_all_preserves_original_fields(self):
        results = self.matcher.match_all("登录按钮", LABELED_ELEMENTS)
        self.assertTrue(len(results) > 0)
        self.assertIn("bbox", results[0])
        self.assertIn("type", results[0])

# ===========================================================================
# Entry point
# ===========================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
