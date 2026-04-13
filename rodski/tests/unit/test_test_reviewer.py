"""测试 TestReviewerCapability"""
import json
import pytest
from unittest.mock import MagicMock, patch, mock_open

from rodski.llm.capabilities.test_reviewer import TestReviewerCapability


@pytest.fixture
def mock_client():
    """创建带默认配置的 mock LLMClient"""
    client = MagicMock()
    client._config = {
        "capabilities": {
            "test_reviewer": {
                "temperature": 0.1,
                "max_tokens": 2000,
                "enable_vision": True,
                "system_prompt": "你是一个测试审查员。",
            }
        }
    }
    return client


def _make_verdict(verdict="PASS", confidence=0.95, reason="测试通过", issues=None):
    """辅助：生成标准审核结果 JSON 字符串"""
    return json.dumps({
        "verdict": verdict,
        "confidence": confidence,
        "reason": reason,
        "issues": issues or [],
    })


class TestTextReview:
    """纯文本审核路径"""

    def test_text_review_pass(self, mock_client):
        """测试纯文本审核 — 无截图"""
        mock_client.call_text.return_value = _make_verdict()

        cap = TestReviewerCapability(mock_client)
        result = cap.review(
            log="step1: click login\nstep2: verify",
            result_xml="<result status='pass'/>",
            screenshots=[],
        )

        assert result["verdict"] == "PASS"
        assert result["confidence"] == 0.95
        mock_client.call_text.assert_called_once()
        # 确认传递了 temperature 和 max_tokens
        call_kwargs = mock_client.call_text.call_args[1]
        assert call_kwargs["temperature"] == 0.1
        assert call_kwargs["max_tokens"] == 2000

    def test_text_review_with_case_xml(self, mock_client):
        """测试纯文本审核 — 包含测试用例定义"""
        mock_client.call_text.return_value = _make_verdict()

        cap = TestReviewerCapability(mock_client)
        result = cap.review(
            log="some log",
            result_xml="<result/>",
            screenshots=[],
            case_xml="<testcase><step>click</step></testcase>",
        )

        assert result["verdict"] == "PASS"
        prompt_arg = mock_client.call_text.call_args[0][0]
        assert "测试用例定义" in prompt_arg

    def test_text_review_fail_verdict(self, mock_client):
        """测试审核结果为 FAIL"""
        mock_client.call_text.return_value = _make_verdict(
            verdict="FAIL", confidence=0.8, reason="步骤 2 失败",
            issues=["截图不匹配"]
        )

        cap = TestReviewerCapability(mock_client)
        result = cap.review(log="log", result_xml="<r/>", screenshots=[])

        assert result["verdict"] == "FAIL"
        assert "步骤 2 失败" in result["reason"]
        assert len(result["issues"]) == 1


class TestVisionReview:
    """多模态审核路径"""

    def test_vision_review_with_screenshots(self, mock_client):
        """测试带截图的视觉审核"""
        mock_client.call_vision.return_value = _make_verdict()

        cap = TestReviewerCapability(mock_client)
        with patch("builtins.open", mock_open(read_data=b"fake_image")):
            result = cap.review(
                log="some log",
                result_xml="<result/>",
                screenshots=["/tmp/screenshot_001.png"],
            )

        assert result["verdict"] == "PASS"
        mock_client.call_vision.assert_called_once()
        # 第一个位置参数是 base64 编码的图片
        call_args = mock_client.call_vision.call_args
        assert len(call_args[0][0]) > 0  # image_base64 非空

    def test_vision_disabled_falls_back_to_text(self, mock_client):
        """测试 enable_vision=False 时使用纯文本"""
        mock_client._config["capabilities"]["test_reviewer"]["enable_vision"] = False
        mock_client.call_text.return_value = _make_verdict()

        cap = TestReviewerCapability(mock_client)
        result = cap.review(
            log="log",
            result_xml="<r/>",
            screenshots=["/tmp/shot.png"],
        )

        assert result["verdict"] == "PASS"
        mock_client.call_text.assert_called_once()
        mock_client.call_vision.assert_not_called()


class TestKwargsOverride:
    """kwargs 参数覆盖"""

    def test_kwargs_override_temperature(self, mock_client):
        """测试 kwargs 覆盖 temperature"""
        mock_client.call_text.return_value = _make_verdict()

        cap = TestReviewerCapability(mock_client)
        cap.review(
            log="log", result_xml="<r/>", screenshots=[],
            temperature=0.5, max_tokens=4096,
        )

        call_kwargs = mock_client.call_text.call_args[1]
        assert call_kwargs["temperature"] == 0.5
        assert call_kwargs["max_tokens"] == 4096


class TestErrorHandling:
    """错误处理"""

    def test_api_error_returns_suspicious(self, mock_client):
        """测试 API 调用失败时返回 SUSPICIOUS"""
        mock_client.call_text.side_effect = Exception("API timeout")

        cap = TestReviewerCapability(mock_client)
        result = cap.review(log="log", result_xml="<r/>", screenshots=[])

        assert result["verdict"] == "SUSPICIOUS"
        assert result["confidence"] == 0.0
        assert "reviewer_error" in result["issues"]

    def test_invalid_json_response(self, mock_client):
        """测试 LLM 返回非 JSON 时的处理"""
        mock_client.call_text.return_value = "This is not JSON"

        cap = TestReviewerCapability(mock_client)
        result = cap.review(log="log", result_xml="<r/>", screenshots=[])

        assert result["verdict"] == "SUSPICIOUS"
        assert "response_parse_error" in result["issues"]

    def test_vision_encode_error_returns_suspicious(self, mock_client):
        """测试截图编码失败时的处理"""
        cap = TestReviewerCapability(mock_client)
        # 不 mock open，路径不存在会触发 FileNotFoundError
        result = cap.review(
            log="log", result_xml="<r/>",
            screenshots=["/nonexistent/path.png"],
        )

        assert result["verdict"] == "SUSPICIOUS"
        assert "reviewer_error" in result["issues"]


class TestExecuteAlias:
    """测试 execute() 接口兼容 BaseCapability"""

    def test_execute_delegates_to_review(self, mock_client):
        """execute() 调用 review()"""
        mock_client.call_text.return_value = _make_verdict()

        cap = TestReviewerCapability(mock_client)
        result = cap.execute(
            log="log", result_xml="<r/>", screenshots=[]
        )

        assert result["verdict"] == "PASS"


class TestPromptBuilding:
    """提示词构建"""

    def test_log_truncation(self, mock_client):
        """测试日志截断为 3000 字符"""
        mock_client.call_text.return_value = _make_verdict()
        long_log = "x" * 5000

        cap = TestReviewerCapability(mock_client)
        cap.review(log=long_log, result_xml="<r/>", screenshots=[])

        prompt_arg = mock_client.call_text.call_args[0][0]
        # 日志内容应被截断，prompt 中不应包含完整的 5000 字符日志
        assert "x" * 3000 in prompt_arg
        assert "x" * 5000 not in prompt_arg

    def test_system_prompt_included(self, mock_client):
        """测试 system_prompt 包含在文本调用中"""
        mock_client.call_text.return_value = _make_verdict()

        cap = TestReviewerCapability(mock_client)
        cap.review(log="log", result_xml="<r/>", screenshots=[])

        prompt_arg = mock_client.call_text.call_args[0][0]
        assert "你是一个测试审查员" in prompt_arg
