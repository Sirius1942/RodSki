"""视觉定位 LLM 语义识别层单元测试

使用 unittest.mock 隔离所有外部 API 调用，不依赖 pytest。
通过 RodSki 项目约定的 unittest 风格编写。
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch, mock_open

# ---------------------------------------------------------------------------
# 路径修正：确保 rodski/ 包在 sys.path 中
# ---------------------------------------------------------------------------
_RODSKI_ROOT = pathlib.Path(__file__).parent.parent.parent  # rodski/
if str(_RODSKI_ROOT) not in sys.path:
    sys.path.insert(0, str(_RODSKI_ROOT))

from vision.llm_analyzer import (
    LLMAnalyzer,
    _load_llm_config,
    _resolve_api_key,
    _build_prompt,
    _encode_image,
    _DEFAULT_LLM_CONFIG,
)
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

# ===========================================================================
# Tests: helper functions
# ===========================================================================

class TestLoadLLMConfig(unittest.TestCase):
    def test_defaults_when_no_yaml(self):
        with patch("vision.llm_analyzer._CONFIG_PATH") as mock_path:
            mock_path.exists.return_value = False
            cfg = _load_llm_config(None)
        self.assertEqual(cfg["provider"], "claude")
        self.assertEqual(cfg["timeout"], 10)

    def test_yaml_overrides_defaults(self):
        import importlib
        import types
        # Provide a fake yaml module so _load_llm_config can call safe_load
        fake_yaml = types.ModuleType("yaml")
        fake_yaml.safe_load = MagicMock(  # type: ignore[attr-defined]
            return_value={"llm": {"provider": "openai", "timeout": 20}}
        )
        with patch.dict(sys.modules, {"yaml": fake_yaml}):
            # Reload so vision.llm_analyzer picks up the fake yaml
            import vision.llm_analyzer as _mod
            importlib.reload(_mod)
            from vision.llm_analyzer import _load_llm_config as _lc
            with patch.object(_mod, "_CONFIG_PATH") as mock_path:
                mock_path.exists.return_value = True
                mock_path.open.return_value.__enter__ = lambda s: s
                mock_path.open.return_value.__exit__ = MagicMock(return_value=False)
                cfg = _lc(None)
        self.assertEqual(cfg["provider"], "openai")
        self.assertEqual(cfg["timeout"], 20)
        # Reload without fake yaml to restore module state
        importlib.reload(_mod)

    def test_explicit_config_overrides_yaml(self):
        with patch("vision.llm_analyzer._CONFIG_PATH") as mock_path:
            mock_path.exists.return_value = False
            cfg = _load_llm_config({"provider": "qwen", "model": "qwen-vl-plus"})
        self.assertEqual(cfg["provider"], "qwen")
        self.assertEqual(cfg["model"], "qwen-vl-plus")

class TestResolveApiKey(unittest.TestCase):
    def test_vision_llm_api_key_takes_priority(self):
        env = {"VISION_LLM_API_KEY": "override-key", "ANTHROPIC_API_KEY": "other-key"}
        with patch.dict(os.environ, env, clear=False):
            key = _resolve_api_key({"provider": "claude", "api_key_env": "ANTHROPIC_API_KEY"})
        self.assertEqual(key, "override-key")

    def test_api_key_env_fallback(self):
        env = {"ANTHROPIC_API_KEY": "anthro-key"}
        with patch.dict(os.environ, env, clear=False):
            # Remove VISION_LLM_API_KEY if present
            os.environ.pop("VISION_LLM_API_KEY", None)
            key = _resolve_api_key({"provider": "claude", "api_key_env": "ANTHROPIC_API_KEY"})
        self.assertEqual(key, "anthro-key")

    def test_returns_none_when_no_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("pathlib.Path.exists", return_value=False):
                key = _resolve_api_key({"provider": "claude", "api_key_env": "ANTHROPIC_API_KEY"})
        self.assertIsNone(key)


class TestBuildPrompt(unittest.TestCase):
    def test_contains_element_content(self):
        prompt = _build_prompt(SAMPLE_ELEMENTS)
        self.assertIn("Login", prompt)
        self.assertIn("Username", prompt)

    def test_instructs_json_output(self):
        prompt = _build_prompt(SAMPLE_ELEMENTS)
        self.assertIn("semantic_label", prompt)
        self.assertIn("JSON", prompt)

    def test_empty_elements(self):
        prompt = _build_prompt([])
        self.assertIsInstance(prompt, str)

# ===========================================================================
# Tests: LLMAnalyzer
# ===========================================================================

class TestLLMAnalyzerMergeLabels(unittest.TestCase):
    """Test _merge_labels without any API calls."""

    def setUp(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
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
    """Test the public analyze() method with mocked LLM calls."""

    def _make_analyzer(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
            return LLMAnalyzer()

    def test_analyze_returns_enhanced_elements(self):
        analyzer = self._make_analyzer()
        with patch.object(analyzer, "_call_llm", return_value=SAMPLE_LABELS):
            result = analyzer.analyze("/fake/screenshot.png", SAMPLE_ELEMENTS)
        self.assertEqual(result[0]["semantic_label"], "登录按钮")
        self.assertEqual(len(result), 3)

    def test_analyze_empty_elements_returns_empty(self):
        analyzer = self._make_analyzer()
        result = analyzer.analyze("/fake/screenshot.png", [])
        self.assertEqual(result, [])

    def test_analyze_no_api_key_returns_original(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("pathlib.Path.exists", return_value=False):
                analyzer = LLMAnalyzer()
        result = analyzer.analyze("/fake/screenshot.png", SAMPLE_ELEMENTS)
        # Should return original (no semantic_label added)
        self.assertNotIn("semantic_label", result[0])

    def test_analyze_llm_exception_returns_original(self):
        analyzer = self._make_analyzer()
        with patch.object(analyzer, "_call_llm", side_effect=RuntimeError("API down")):
            result = analyzer.analyze("/fake/screenshot.png", SAMPLE_ELEMENTS)
        self.assertEqual(result, SAMPLE_ELEMENTS)

    def test_call_llm_unsupported_provider_raises(self):
        analyzer = self._make_analyzer()
        analyzer._cfg["provider"] = "unknown_provider"
        with self.assertRaises(ValueError):
            analyzer._call_llm("/fake/screenshot.png", SAMPLE_ELEMENTS)

class TestLLMAnalyzerClaudeIntegration(unittest.TestCase):
    """Test _call_llm dispatches correctly to Claude, mocking anthropic library."""

    def test_call_llm_claude_dispatches_and_parses(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
            analyzer = LLMAnalyzer({"provider": "claude"})

        fake_response_text = json.dumps(SAMPLE_LABELS)
        mock_content = MagicMock()
        mock_content.text = fake_response_text
        mock_response = MagicMock()
        mock_response.content = [mock_content]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        with patch("vision.llm_analyzer._encode_image", return_value=("b64data", "image/png")):
            with patch.dict(sys.modules, {"anthropic": mock_anthropic}):
                result = analyzer._call_llm("/fake/screen.png", SAMPLE_ELEMENTS)

        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["semantic_label"], "登录按钮")
        mock_client.messages.create.assert_called_once()

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
