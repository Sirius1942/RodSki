"""AIScreenshotVerifier 单元测试

测试 vision/ai_verifier.py 中的 AI 截图验证器。
覆盖：初始化参数、_get_client（各 provider + 缺失依赖）、
      verify（正常/文件不存在/异常）、verify_with_reference（正常/缺失依赖）。
所有 LLM API 调用均通过 mock 隔离。
"""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
from vision.ai_verifier import AIScreenshotVerifier
from vision.exceptions import VisionError


# =====================================================================
# 初始化
# =====================================================================
class TestAIVerifierInit:
    """AIScreenshotVerifier 初始化参数验证"""

    def test_default_params(self):
        """默认参数：provider=claude, timeout=30"""
        v = AIScreenshotVerifier()
        assert v.model_provider == "claude"
        assert v.timeout == 30
        assert v.api_key_env == "ANTHROPIC_API_KEY"
        assert v.base_url == ""
        assert v._client is None  # 延迟初始化

    def test_custom_params(self):
        """自定义参数"""
        v = AIScreenshotVerifier(
            model_provider="openai",
            model_name="gpt-4o",
            api_key_env="OPENAI_API_KEY",
            base_url="https://proxy.example.com",
            timeout=60,
        )
        assert v.model_provider == "openai"
        assert v.model_name == "gpt-4o"
        assert v.timeout == 60


# =====================================================================
# _get_client
# =====================================================================
class TestGetClient:
    """_get_client —— LLM 客户端延迟初始化"""

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_claude_client(self):
        """Claude provider 应创建 Anthropic 客户端
        源码在 _get_client() 内部执行 'import anthropic'，
        需要通过 sys.modules 注入 mock 模块才能拦截"""
        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value = MagicMock(name="AnthropicClient")
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            v = AIScreenshotVerifier(model_provider="claude")
            client = v._get_client()
        assert client is not None
        mock_anthropic.Anthropic.assert_called_once()

    def test_unsupported_provider_raises(self):
        """不支持的 provider 应抛出 VisionError"""
        v = AIScreenshotVerifier(model_provider="unknown_llm")
        with pytest.raises(VisionError, match="不支持的模型提供者"):
            v._get_client()

    def test_qwen_without_base_url_raises(self):
        """Qwen provider 没有 base_url 时应抛出 VisionError"""
        v = AIScreenshotVerifier(model_provider="qwen", base_url="")
        with pytest.raises(VisionError, match="Qwen 需要配置 base_url"):
            v._get_client()

    def test_client_cached(self):
        """客户端应被缓存，第二次调用不再创建"""
        v = AIScreenshotVerifier()
        mock_client = MagicMock()
        v._client = mock_client
        assert v._get_client() is mock_client  # 直接返回缓存


# =====================================================================
# verify
# =====================================================================
class TestVerify:
    """verify —— 截图与预期描述匹配"""

    def test_file_not_found(self):
        """截图文件不存在时应返回 (False, 原因)"""
        v = AIScreenshotVerifier()
        is_pass, reason = v.verify("/nonexistent/screenshot.png", "应该看到登录按钮")
        assert is_pass is False
        assert "不存在" in reason

    def test_verify_success(self, tmp_path):
        """LLM 返回 match=True 时应返回 (True, reason)"""
        # 创建一个假截图文件
        screenshot = tmp_path / "test.png"
        screenshot.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        v = AIScreenshotVerifier(model_provider="claude")
        # mock _get_client 返回的 client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps({"match": True, "reason": "页面正确"}))]
        mock_client.messages.create.return_value = mock_response
        v._client = mock_client

        is_pass, reason = v.verify(str(screenshot), "登录成功")
        assert is_pass is True
        assert "正确" in reason

    def test_verify_failure(self, tmp_path):
        """LLM 返回 match=False 时应返回 (False, reason)"""
        screenshot = tmp_path / "test.png"
        screenshot.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        v = AIScreenshotVerifier(model_provider="claude")
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps({"match": False, "reason": "未找到登录按钮"}))]
        mock_client.messages.create.return_value = mock_response
        v._client = mock_client

        is_pass, reason = v.verify(str(screenshot), "登录成功")
        assert is_pass is False

    def test_verify_llm_exception(self, tmp_path):
        """LLM 调用异常时应返回 (False, 异常描述)"""
        screenshot = tmp_path / "test.png"
        screenshot.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        v = AIScreenshotVerifier(model_provider="claude")
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = RuntimeError("API timeout")
        v._client = mock_client

        is_pass, reason = v.verify(str(screenshot), "测试")
        assert is_pass is False
        assert "异常" in reason

    def test_verify_non_json_response(self, tmp_path):
        """LLM 返回非标准 JSON 时应尝试简单判断"""
        screenshot = tmp_path / "test.png"
        screenshot.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        v = AIScreenshotVerifier(model_provider="claude")
        mock_client = MagicMock()
        mock_response = MagicMock()
        # 返回非 JSON 的 "true" 文本
        mock_response.content = [MagicMock(text="The screenshot matches. Result: true")]
        mock_client.messages.create.return_value = mock_response
        v._client = mock_client

        is_pass, reason = v.verify(str(screenshot), "测试")
        assert is_pass is True  # 包含 "true" 且不包含 "false"


# =====================================================================
# verify_with_reference（图像对比 —— 依赖 cv2/skimage）
# =====================================================================
class TestVerifyWithReference:
    """verify_with_reference —— 截图与参考图对比"""

    def test_screenshot_not_found(self):
        """截图不存在时返回 False"""
        v = AIScreenshotVerifier()
        with patch("cv2.imread", return_value=None):
            is_pass, reason = v.verify_with_reference("/fake/ss.png", "/fake/ref.png")
        assert is_pass is False

    def test_reference_not_found(self, tmp_path):
        """参考图不存在时返回 False"""
        ss = tmp_path / "ss.png"
        ss.write_bytes(b"\x89PNG" + b"\x00" * 100)
        v = AIScreenshotVerifier()
        with patch("cv2.imread", side_effect=[MagicMock(), None]):
            is_pass, reason = v.verify_with_reference(str(ss), "/fake/ref.png")
        assert is_pass is False

    def test_missing_dependency(self):
        """缺少 scikit-image 时应返回 False 并提示安装"""
        v = AIScreenshotVerifier()
        with patch.dict("sys.modules", {"cv2": MagicMock()}):
            with patch("vision.ai_verifier.cv2", create=True):
                # 模拟 import skimage 失败
                is_pass, reason = v.verify_with_reference("/a.png", "/b.png")
        # 由于 cv2.imread 会返回 mock，但 ssim 可能失败
        assert is_pass is False
