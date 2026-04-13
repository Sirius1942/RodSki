"""ScreenshotVerifierCapability 单元测试

测试 llm/capabilities/screenshot_verifier.py 截图验证能力。
覆盖：verify 正常流程、文件不存在、LLM 异常、非标准 JSON 回退解析。
所有 LLM API 调用均通过 mock 隔离。
"""
import json
import pytest
from unittest.mock import MagicMock, patch, mock_open

from rodski.llm.capabilities.screenshot_verifier import ScreenshotVerifierCapability


# =====================================================================
# verify — 正常流程
# =====================================================================
class TestScreenshotVerifierVerify:
    """ScreenshotVerifierCapability.verify 各场景"""

    def test_verify_pass(self, tmp_path):
        """LLM 返回 match=True 时应返回 (True, reason)"""
        screenshot = tmp_path / "test.png"
        screenshot.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        mock_client = MagicMock()
        mock_client.call_vision.return_value = json.dumps(
            {"match": True, "reason": "页面显示正确"}
        )

        cap = ScreenshotVerifierCapability(mock_client)
        is_pass, reason = cap.verify(str(screenshot), "登录成功")

        assert is_pass is True
        assert "正确" in reason
        mock_client.call_vision.assert_called_once()

    def test_verify_fail(self, tmp_path):
        """LLM 返回 match=False 时应返回 (False, reason)"""
        screenshot = tmp_path / "test.png"
        screenshot.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        mock_client = MagicMock()
        mock_client.call_vision.return_value = json.dumps(
            {"match": False, "reason": "未找到登录按钮"}
        )

        cap = ScreenshotVerifierCapability(mock_client)
        is_pass, reason = cap.verify(str(screenshot), "登录成功")

        assert is_pass is False
        assert "未找到" in reason

    def test_verify_file_not_found(self):
        """截图文件不存在时应返回 (False, 原因)"""
        mock_client = MagicMock()
        cap = ScreenshotVerifierCapability(mock_client)

        is_pass, reason = cap.verify("/nonexistent/screenshot.png", "测试")

        assert is_pass is False
        assert "不存在" in reason
        mock_client.call_vision.assert_not_called()

    def test_verify_llm_exception(self, tmp_path):
        """LLM 调用异常时应返回 (False, 异常描述)"""
        screenshot = tmp_path / "test.png"
        screenshot.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        mock_client = MagicMock()
        mock_client.call_vision.side_effect = RuntimeError("API timeout")

        cap = ScreenshotVerifierCapability(mock_client)
        is_pass, reason = cap.verify(str(screenshot), "测试")

        assert is_pass is False
        assert "异常" in reason

    def test_verify_non_json_response_true(self, tmp_path):
        """LLM 返回非标准 JSON 但含 'true' 时应判断为通过"""
        screenshot = tmp_path / "test.png"
        screenshot.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        mock_client = MagicMock()
        mock_client.call_vision.return_value = "The screenshot matches. Result: true"

        cap = ScreenshotVerifierCapability(mock_client)
        is_pass, reason = cap.verify(str(screenshot), "测试")

        assert is_pass is True

    def test_verify_non_json_response_false(self, tmp_path):
        """LLM 返回非标准 JSON 且含 'false' 时应判断为不通过"""
        screenshot = tmp_path / "test.png"
        screenshot.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        mock_client = MagicMock()
        mock_client.call_vision.return_value = "Result is false, page mismatch"

        cap = ScreenshotVerifierCapability(mock_client)
        is_pass, reason = cap.verify(str(screenshot), "测试")

        assert is_pass is False


# =====================================================================
# execute — BaseCapability 接口
# =====================================================================
class TestScreenshotVerifierExecute:
    """execute() 应委托给 verify()"""

    def test_execute_delegates_to_verify(self, tmp_path):
        """execute() 返回与 verify() 一致的结果"""
        screenshot = tmp_path / "test.png"
        screenshot.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        mock_client = MagicMock()
        mock_client.call_vision.return_value = json.dumps(
            {"match": True, "reason": "OK"}
        )

        cap = ScreenshotVerifierCapability(mock_client)
        result = cap.execute(str(screenshot), "测试")

        assert result == (True, "OK")


# =====================================================================
# prompt 构建
# =====================================================================
class TestBuildPrompt:
    """_build_prompt 验证"""

    def test_prompt_contains_expected(self):
        """提示词应包含预期描述"""
        mock_client = MagicMock()
        cap = ScreenshotVerifierCapability(mock_client)
        prompt = cap._build_prompt("页面应显示欢迎文字")

        assert "页面应显示欢迎文字" in prompt
        assert "JSON" in prompt
        assert "match" in prompt


# =====================================================================
# AIScreenshotVerifier 通过 LLMClient 能力验证
# =====================================================================
class TestAIVerifierWithLLMClient:
    """AIScreenshotVerifier 使用 llm_client 参数时委托给能力"""

    def test_verify_delegates_to_capability(self, tmp_path):
        """传入 llm_client 时，verify() 应调用 screenshot_verifier 能力"""
        from rodski.vision.ai_verifier import AIScreenshotVerifier

        screenshot = tmp_path / "test.png"
        screenshot.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        mock_capability = MagicMock()
        mock_capability.verify.return_value = (True, "通过能力验证")

        mock_llm_client = MagicMock()
        mock_llm_client.get_capability.return_value = mock_capability

        verifier = AIScreenshotVerifier(llm_client=mock_llm_client)
        is_pass, reason = verifier.verify(str(screenshot), "登录成功")

        assert is_pass is True
        assert "能力验证" in reason
        mock_llm_client.get_capability.assert_called_once_with("screenshot_verifier")
        mock_capability.verify.assert_called_once_with(str(screenshot), "登录成功")

    def test_verify_fallback_on_capability_error(self, tmp_path):
        """LLMClient 能力调用失败时应回退到直接 SDK"""
        from rodski.vision.ai_verifier import AIScreenshotVerifier

        screenshot = tmp_path / "test.png"
        screenshot.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        mock_llm_client = MagicMock()
        mock_llm_client.get_capability.side_effect = RuntimeError("capability error")

        # mock 直接 SDK 路径
        mock_sdk_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text=json.dumps({"match": True, "reason": "SDK 回退成功"}))
        ]
        mock_sdk_client.messages.create.return_value = mock_response

        verifier = AIScreenshotVerifier(
            model_provider="claude", llm_client=mock_llm_client
        )
        verifier._client = mock_sdk_client

        is_pass, reason = verifier.verify(str(screenshot), "测试")

        assert is_pass is True
        assert "SDK 回退成功" in reason

    def test_verify_without_llm_client_uses_direct_sdk(self, tmp_path):
        """不传 llm_client 时使用直接 SDK 路径"""
        from rodski.vision.ai_verifier import AIScreenshotVerifier

        screenshot = tmp_path / "test.png"
        screenshot.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        mock_sdk_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text=json.dumps({"match": False, "reason": "直接 SDK 验证"}))
        ]
        mock_sdk_client.messages.create.return_value = mock_response

        verifier = AIScreenshotVerifier(model_provider="claude")
        verifier._client = mock_sdk_client

        is_pass, reason = verifier.verify(str(screenshot), "测试")

        assert is_pass is False
        assert "直接 SDK" in reason


# =====================================================================
# LLMClient.get_capability 注册测试
# =====================================================================
class TestLLMClientRegistration:
    """LLMClient 能正确获取 screenshot_verifier 能力"""

    def test_get_screenshot_verifier_capability(self):
        """get_capability('screenshot_verifier') 应返回 ScreenshotVerifierCapability"""
        from rodski.llm.client import LLMClient

        mock_config = {
            "provider": "claude",
            "providers": {
                "claude": {"model": "test", "api_key": "test-key"}
            },
        }

        with patch("rodski.llm.client.load_config", return_value=mock_config):
            client = LLMClient(config=mock_config)
            cap = client.get_capability("screenshot_verifier")

        assert isinstance(cap, ScreenshotVerifierCapability)
        assert cap.client is client
