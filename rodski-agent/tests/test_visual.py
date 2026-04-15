"""视觉探索模块单元测试。

测试 OmniParser 客户端和 Design Agent 视觉节点（explore_page / identify_elem）。
所有外部依赖均 Mock，确保测试无网络或文件系统副作用。
"""
from __future__ import annotations

import json
import os
from unittest.mock import patch, MagicMock

import pytest


# ============================================================
# OmniParser client tests
# ============================================================


class TestOmniParserGetUrl:
    """_get_omniparser_url 配置读取测试。"""

    def test_default_url_when_config_import_fails(self):
        """AgentConfig import fails → default localhost:8000."""
        from rodski_agent.common.omniparser_client import _get_omniparser_url

        with patch("rodski_agent.common.config.AgentConfig") as MockConfig:
            MockConfig.load.side_effect = Exception("no config")
            url = _get_omniparser_url()
        assert url == "http://localhost:8000"

    def test_url_from_config(self):
        """Config with omniparser.url → use that URL."""
        from rodski_agent.common.omniparser_client import _get_omniparser_url

        mock_cfg = MagicMock()
        mock_cfg.to_dict.return_value = {
            "omniparser": {"url": "http://omni.example.com:9000"}
        }
        with patch("rodski_agent.common.config.AgentConfig") as MockConfig:
            MockConfig.load.return_value = mock_cfg
            url = _get_omniparser_url()
        assert url == "http://omni.example.com:9000"

    def test_empty_url_in_config(self):
        """Config with empty omniparser.url → default."""
        from rodski_agent.common.omniparser_client import _get_omniparser_url

        mock_cfg = MagicMock()
        mock_cfg.to_dict.return_value = {"omniparser": {"url": ""}}
        with patch("rodski_agent.common.config.AgentConfig") as MockConfig:
            MockConfig.load.return_value = mock_cfg
            url = _get_omniparser_url()
        assert url == "http://localhost:8000"

    def test_no_omniparser_key_in_config(self):
        """Config without omniparser key → default."""
        from rodski_agent.common.omniparser_client import _get_omniparser_url

        mock_cfg = MagicMock()
        mock_cfg.to_dict.return_value = {}
        with patch("rodski_agent.common.config.AgentConfig") as MockConfig:
            MockConfig.load.return_value = mock_cfg
            url = _get_omniparser_url()
        assert url == "http://localhost:8000"


class TestParseScreenshot:
    """parse_screenshot HTTP 调用测试。"""

    def test_successful_parse(self, tmp_path):
        """Valid screenshot → parsed elements."""
        from rodski_agent.common.omniparser_client import parse_screenshot

        img_file = tmp_path / "test.png"
        img_file.write_bytes(b"\x89PNG\r\n\x1a\n")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "elements": [
                {"label": "Submit", "bbox": [10, 20, 100, 50], "type": "button", "confidence": 0.95},
                {"label": "Username", "bbox": [10, 60, 200, 80], "type": "input", "confidence": 0.88},
            ]
        }

        with patch("requests.post", return_value=mock_resp):
            elements = parse_screenshot(str(img_file), server_url="http://test:8000")

        assert len(elements) == 2
        assert elements[0]["id"] == 0
        assert elements[0]["label"] == "Submit"
        assert elements[0]["type"] == "button"
        assert elements[0]["confidence"] == 0.95
        assert elements[1]["id"] == 1
        assert elements[1]["label"] == "Username"

    def test_file_not_found(self):
        """Missing screenshot → OmniParserUnavailableError."""
        from rodski_agent.common.omniparser_client import (
            parse_screenshot,
            OmniParserUnavailableError,
        )

        with pytest.raises(OmniParserUnavailableError, match="Screenshot not found"):
            parse_screenshot("/nonexistent/image.png")

    def test_connection_error(self, tmp_path):
        """Connection refused → OmniParserUnavailableError."""
        from rodski_agent.common.omniparser_client import (
            parse_screenshot,
            OmniParserUnavailableError,
        )
        import requests

        img_file = tmp_path / "test.png"
        img_file.write_bytes(b"\x89PNG")

        with patch("requests.post", side_effect=requests.exceptions.ConnectionError("refused")):
            with pytest.raises(OmniParserUnavailableError, match="Cannot connect"):
                parse_screenshot(str(img_file), server_url="http://bad:8000")

    def test_timeout_error(self, tmp_path):
        """Request timeout → OmniParserUnavailableError."""
        from rodski_agent.common.omniparser_client import (
            parse_screenshot,
            OmniParserUnavailableError,
        )
        import requests

        img_file = tmp_path / "test.png"
        img_file.write_bytes(b"\x89PNG")

        with patch("requests.post", side_effect=requests.exceptions.Timeout("timed out")):
            with pytest.raises(OmniParserUnavailableError, match="timed out"):
                parse_screenshot(str(img_file), server_url="http://slow:8000")

    def test_generic_request_error(self, tmp_path):
        """Generic exception from requests → OmniParserUnavailableError."""
        from rodski_agent.common.omniparser_client import (
            parse_screenshot,
            OmniParserUnavailableError,
        )

        img_file = tmp_path / "test.png"
        img_file.write_bytes(b"\x89PNG")

        with patch("requests.post", side_effect=Exception("weird")):
            with pytest.raises(OmniParserUnavailableError, match="request failed"):
                parse_screenshot(str(img_file), server_url="http://test:8000")

    def test_empty_elements(self, tmp_path):
        """Server returns no elements → empty list."""
        from rodski_agent.common.omniparser_client import parse_screenshot

        img_file = tmp_path / "test.png"
        img_file.write_bytes(b"\x89PNG")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"elements": []}

        with patch("requests.post", return_value=mock_resp):
            elements = parse_screenshot(str(img_file), server_url="http://test:8000")

        assert elements == []

    def test_custom_timeout(self, tmp_path):
        """Custom timeout is passed to requests."""
        from rodski_agent.common.omniparser_client import parse_screenshot

        img_file = tmp_path / "test.png"
        img_file.write_bytes(b"\x89PNG")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"elements": []}

        with patch("requests.post", return_value=mock_resp) as mock_post:
            parse_screenshot(str(img_file), server_url="http://test:8000", timeout=60)

        assert mock_post.call_args.kwargs["timeout"] == 60

    def test_missing_fields_default(self, tmp_path):
        """Server returns elements with missing fields → defaults applied."""
        from rodski_agent.common.omniparser_client import parse_screenshot

        img_file = tmp_path / "test.png"
        img_file.write_bytes(b"\x89PNG")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"elements": [{}]}

        with patch("requests.post", return_value=mock_resp):
            elements = parse_screenshot(str(img_file), server_url="http://test:8000")

        assert elements[0]["label"] == ""
        assert elements[0]["type"] == "unknown"
        assert elements[0]["confidence"] == 0.0
        assert elements[0]["bbox"] == [0, 0, 0, 0]


class TestCaptureScreenshot:
    """capture_screenshot Playwright 调用测试。"""

    def test_successful_capture(self, tmp_path):
        """Successful screenshot → returns output path."""
        from rodski_agent.common.omniparser_client import capture_screenshot

        output_path = str(tmp_path / "screenshot.png")

        mock_page = MagicMock()
        mock_browser = MagicMock()
        mock_browser.new_page.return_value = mock_page
        mock_browser_type = MagicMock()
        mock_browser_type.launch.return_value = mock_browser

        mock_playwright = MagicMock()
        mock_playwright.chromium = mock_browser_type

        mock_pw_ctx = MagicMock()
        mock_pw_ctx.__enter__ = MagicMock(return_value=mock_playwright)
        mock_pw_ctx.__exit__ = MagicMock(return_value=False)

        with patch("playwright.sync_api.sync_playwright", return_value=mock_pw_ctx):
            result = capture_screenshot("https://example.com", output_path)

        assert result == output_path
        mock_page.goto.assert_called_once_with("https://example.com", wait_until="networkidle")
        mock_page.screenshot.assert_called_once()
        mock_browser.close.assert_called_once()

    def test_browser_launch_failure(self):
        """Browser launch fails → OmniParserUnavailableError."""
        from rodski_agent.common.omniparser_client import (
            capture_screenshot,
            OmniParserUnavailableError,
        )

        mock_browser_type = MagicMock()
        mock_browser_type.launch.side_effect = Exception("no browser")
        mock_playwright = MagicMock()
        mock_playwright.chromium = mock_browser_type

        mock_pw_ctx = MagicMock()
        mock_pw_ctx.__enter__ = MagicMock(return_value=mock_playwright)
        mock_pw_ctx.__exit__ = MagicMock(return_value=False)

        with patch("playwright.sync_api.sync_playwright", return_value=mock_pw_ctx):
            with pytest.raises(OmniParserUnavailableError, match="Screenshot capture failed"):
                capture_screenshot("https://example.com", "/tmp/out.png")

    def test_headless_false(self, tmp_path):
        """headless=False is passed to browser launch."""
        from rodski_agent.common.omniparser_client import capture_screenshot

        output_path = str(tmp_path / "screenshot.png")

        mock_page = MagicMock()
        mock_browser = MagicMock()
        mock_browser.new_page.return_value = mock_page
        mock_browser_type = MagicMock()
        mock_browser_type.launch.return_value = mock_browser
        mock_playwright = MagicMock()
        mock_playwright.chromium = mock_browser_type

        mock_pw_ctx = MagicMock()
        mock_pw_ctx.__enter__ = MagicMock(return_value=mock_playwright)
        mock_pw_ctx.__exit__ = MagicMock(return_value=False)

        with patch("playwright.sync_api.sync_playwright", return_value=mock_pw_ctx):
            capture_screenshot("https://example.com", output_path, headless=False)

        mock_browser_type.launch.assert_called_once_with(headless=False)


# ============================================================
# Design visual node tests — explore_page
# ============================================================


class TestExplorePage:
    """explore_page 节点测试。"""

    def test_no_target_url(self):
        """No target_url → empty elements and screenshots."""
        from rodski_agent.design.visual import explore_page

        result = explore_page({"output_dir": "/tmp"})
        assert result == {"page_elements": [], "screenshots": []}

    def test_empty_target_url(self):
        """Empty target_url → skip."""
        from rodski_agent.design.visual import explore_page

        result = explore_page({"target_url": "", "output_dir": "/tmp"})
        assert result == {"page_elements": [], "screenshots": []}

    def test_successful_exploration(self, tmp_path):
        """Screenshot + OmniParser → elements and screenshot path."""
        from rodski_agent.design.visual import explore_page

        output_dir = str(tmp_path / "output")

        mock_elements = [
            {"id": 0, "label": "Login", "bbox": [10, 20, 100, 50], "type": "button", "confidence": 0.9},
        ]

        with patch("rodski_agent.common.omniparser_client.capture_screenshot") as mock_capture, \
             patch("rodski_agent.common.omniparser_client.parse_screenshot", return_value=mock_elements):
            result = explore_page({
                "target_url": "https://example.com",
                "output_dir": output_dir,
            })

        assert result["page_elements"] == mock_elements
        assert len(result["screenshots"]) == 1
        assert "page_screenshot.png" in result["screenshots"][0]
        mock_capture.assert_called_once()

    def test_screenshot_failure_raises(self, tmp_path):
        """Screenshot capture fails → error propagated."""
        from rodski_agent.design.visual import explore_page
        from rodski_agent.common.omniparser_client import OmniParserUnavailableError

        with patch(
            "rodski_agent.common.omniparser_client.capture_screenshot",
            side_effect=OmniParserUnavailableError("no browser"),
        ):
            with pytest.raises(OmniParserUnavailableError):
                explore_page({
                    "target_url": "https://example.com",
                    "output_dir": str(tmp_path),
                })

    def test_omniparser_failure_raises(self, tmp_path):
        """OmniParser fails → error propagated."""
        from rodski_agent.design.visual import explore_page
        from rodski_agent.common.omniparser_client import OmniParserUnavailableError

        output_dir = str(tmp_path / "output")

        with patch("rodski_agent.common.omniparser_client.capture_screenshot"), \
             patch(
                 "rodski_agent.common.omniparser_client.parse_screenshot",
                 side_effect=OmniParserUnavailableError("omni down"),
             ):
            with pytest.raises(OmniParserUnavailableError):
                explore_page({
                    "target_url": "https://example.com",
                    "output_dir": output_dir,
                })

    def test_uses_tempdir_when_no_output_dir(self):
        """No output_dir → uses tempfile.mkdtemp for screenshots."""
        from rodski_agent.design.visual import explore_page

        with patch("rodski_agent.common.omniparser_client.capture_screenshot"), \
             patch("rodski_agent.common.omniparser_client.parse_screenshot", return_value=[]), \
             patch("rodski_agent.design.visual.tempfile") as mock_tempfile:
            mock_tempfile.mkdtemp.return_value = "/tmp/test_screenshots"
            result = explore_page({
                "target_url": "https://example.com",
                "output_dir": "",
            })

        assert len(result["screenshots"]) == 1

    def test_creates_screenshot_dir(self, tmp_path):
        """Screenshot directory is created if it doesn't exist."""
        from rodski_agent.design.visual import explore_page

        output_dir = str(tmp_path / "new_output")

        with patch("rodski_agent.common.omniparser_client.capture_screenshot"), \
             patch("rodski_agent.common.omniparser_client.parse_screenshot", return_value=[]):
            explore_page({
                "target_url": "https://example.com",
                "output_dir": output_dir,
            })

        assert os.path.isdir(os.path.join(output_dir, "screenshots"))

    def test_headless_passed_to_capture(self, tmp_path):
        """headless state is passed to capture_screenshot."""
        from rodski_agent.design.visual import explore_page

        with patch("rodski_agent.common.omniparser_client.capture_screenshot") as mock_cap, \
             patch("rodski_agent.common.omniparser_client.parse_screenshot", return_value=[]):
            explore_page({
                "target_url": "https://example.com",
                "output_dir": str(tmp_path),
                "headless": False,
            })

        call_kwargs = mock_cap.call_args
        assert call_kwargs.kwargs.get("headless") is False or \
               (len(call_kwargs.args) >= 3 and call_kwargs.args[2] is False) or \
               call_kwargs[1].get("headless") is False


# ============================================================
# Design visual node tests — identify_elem
# ============================================================


class TestIdentifyElem:
    """identify_elem 节点测试。"""

    def test_no_elements(self):
        """No page_elements → empty enriched_elements."""
        from rodski_agent.design.visual import identify_elem

        result = identify_elem({"page_elements": [], "screenshots": []})
        assert result == {"enriched_elements": []}

    def test_llm_enrichment_success(self):
        """LLM enrichment succeeds → enriched elements returned."""
        from rodski_agent.design.visual import identify_elem

        elements = [
            {"id": 0, "label": "Login Button", "type": "button"},
            {"id": 1, "label": "Username", "type": "input"},
        ]

        llm_response = json.dumps([
            {
                "id": 0,
                "semantic_name": "login_button",
                "purpose": "Submits login form",
                "suggested_locator_type": "css",
                "original_label": "Login Button",
            },
            {
                "id": 1,
                "semantic_name": "username_input",
                "purpose": "Username text field",
                "suggested_locator_type": "id",
                "original_label": "Username",
            },
        ])

        with patch("rodski_agent.common.llm_bridge.call_llm_text", return_value=llm_response):
            result = identify_elem({
                "page_elements": elements,
                "screenshots": ["/tmp/screenshot.png"],
            })

        assert len(result["enriched_elements"]) == 2
        assert result["enriched_elements"][0]["semantic_name"] == "login_button"
        assert result["enriched_elements"][1]["semantic_name"] == "username_input"

    def test_llm_response_with_code_fence(self):
        """LLM returns JSON in ```json ... ``` → correctly parsed."""
        from rodski_agent.design.visual import identify_elem

        elements = [{"id": 0, "label": "OK", "type": "button"}]

        llm_response = '```json\n[{"id": 0, "semantic_name": "ok_btn", "purpose": "confirm", "suggested_locator_type": "css", "original_label": "OK"}]\n```'

        with patch("rodski_agent.common.llm_bridge.call_llm_text", return_value=llm_response):
            result = identify_elem({
                "page_elements": elements,
                "screenshots": [],
            })

        assert len(result["enriched_elements"]) == 1
        assert result["enriched_elements"][0]["semantic_name"] == "ok_btn"

    def test_llm_failure_raises(self):
        """LLM fails → error propagated."""
        from rodski_agent.design.visual import identify_elem
        from rodski_agent.common.errors import LLMError

        elements = [
            {"id": 0, "label": "Submit Form", "type": "button"},
        ]

        with patch("rodski_agent.common.llm_bridge.call_llm_text", side_effect=LLMError("LLM down", code="E_LLM")):
            with pytest.raises(LLMError):
                identify_elem({
                    "page_elements": elements,
                    "screenshots": [],
                })

    def test_llm_returns_non_list(self):
        """LLM returns non-list JSON → ValueError."""
        from rodski_agent.design.visual import identify_elem

        elements = [{"id": 0, "label": "Test", "type": "text"}]

        with patch("rodski_agent.common.llm_bridge.call_llm_text", return_value='{"not": "a list"}'):
            with pytest.raises(ValueError, match="invalid enrichment format"):
                identify_elem({
                    "page_elements": elements,
                    "screenshots": [],
                })

    def test_llm_returns_invalid_json(self):
        """LLM returns garbage text → json.JSONDecodeError."""
        from rodski_agent.design.visual import identify_elem

        elements = [{"id": 0, "label": "Hello", "type": "text"}]

        with patch("rodski_agent.common.llm_bridge.call_llm_text", return_value="not json at all"):
            with pytest.raises(json.JSONDecodeError):
                identify_elem({
                    "page_elements": elements,
                    "screenshots": [],
                })


# ============================================================
# Design graph integration with visual nodes
# ============================================================


class TestDesignGraphWithVisual:
    """测试视觉节点集成到设计图中。"""

    def test_build_design_graph_with_visual(self):
        """Design graph with visual nodes can be built and invoked."""
        from rodski_agent.design.graph import build_design_graph

        def stub_node(state):
            return {}

        graph = build_design_graph(
            analyze_req_fn=stub_node,
            explore_page_fn=stub_node,
            identify_elem_fn=stub_node,
            plan_cases_fn=stub_node,
            design_data_fn=stub_node,
            generate_xml_fn=lambda s: {"status": "success"},
            validate_xml_fn=stub_node,
        )

        result = graph.invoke({"requirement": "test"})
        assert result.get("status") == "success"

    def test_build_design_graph_without_visual(self):
        """Design graph without visual nodes uses defaults from visual module."""
        from rodski_agent.design.graph import build_design_graph

        def stub_node(state):
            return {}

        graph = build_design_graph(
            analyze_req_fn=stub_node,
            plan_cases_fn=stub_node,
            design_data_fn=stub_node,
            generate_xml_fn=lambda s: {"status": "success"},
            validate_xml_fn=stub_node,
        )

        result = graph.invoke({"requirement": "test"})
        assert result.get("status") == "success"

    def test_visual_nodes_default_import(self):
        """Default visual node functions are imported from visual module."""
        from rodski_agent.design.graph import build_design_graph

        def stub_node(state):
            return {}

        graph = build_design_graph(
            analyze_req_fn=stub_node,
            plan_cases_fn=stub_node,
            design_data_fn=stub_node,
            generate_xml_fn=lambda s: {"status": "success"},
            validate_xml_fn=stub_node,
        )

        # Should invoke successfully with visual defaults (graceful degradation)
        result = graph.invoke({"requirement": "test", "target_url": ""})
        assert result is not None

    def test_visual_nodes_in_flow_order(self):
        """Visual nodes execute in correct order: analyze → explore → identify → plan."""
        from rodski_agent.design.graph import build_design_graph

        call_order = []

        def make_node(name, updates=None):
            def node(state):
                call_order.append(name)
                return updates or {}
            return node

        graph = build_design_graph(
            analyze_req_fn=make_node("analyze_req"),
            explore_page_fn=make_node("explore_page"),
            identify_elem_fn=make_node("identify_elem"),
            plan_cases_fn=make_node("plan_cases"),
            design_data_fn=make_node("design_data"),
            generate_xml_fn=make_node("generate_xml", {"status": "success"}),
            validate_xml_fn=make_node("validate_xml"),
        )

        graph.invoke({"requirement": "test"})

        assert call_order == [
            "analyze_req",
            "explore_page",
            "identify_elem",
            "plan_cases",
            "design_data",
            "generate_xml",
            "validate_xml",
        ]
