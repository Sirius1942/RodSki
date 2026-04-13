"""截图验证能力 — 使用 LLM 验证截图是否匹配预期描述。"""
import base64
import json
import logging
from .base import BaseCapability

logger = logging.getLogger(__name__)


class ScreenshotVerifierCapability(BaseCapability):
    """截图验证能力

    通过视觉大模型分析截图，判断是否符合预期描述。
    """

    def execute(self, screenshot_path: str, expected: str) -> tuple[bool, str]:
        """执行截图验证（BaseCapability 接口）

        Args:
            screenshot_path: 截图文件路径
            expected: 预期描述（自然语言）

        Returns:
            (is_pass, reason) - 验证是否通过及原因说明
        """
        return self.verify(screenshot_path, expected)

    def verify(self, screenshot_path: str, expected: str) -> tuple[bool, str]:
        """验证截图是否匹配预期描述

        Args:
            screenshot_path: 截图文件路径
            expected: 预期描述（自然语言），例如：
                - "登录成功，显示用户名张三"
                - "出现红色错误提示：操作失败"
                - "页面包含搜索框和提交按钮"

        Returns:
            (is_pass, reason) - 验证是否通过及原因说明
        """
        try:
            image_base64 = self._encode_image(screenshot_path)
            prompt = self._build_prompt(expected)
            response = self.client.call_vision(image_base64, prompt)
            return self._parse_response(response)
        except FileNotFoundError:
            return False, f"截图文件不存在: {screenshot_path}"
        except Exception as e:
            logger.error(f"Screenshot verification failed: {e}")
            return False, f"验证异常: {str(e)}"

    def _encode_image(self, path: str) -> str:
        """Base64 编码图片"""
        with open(path, "rb") as f:
            return base64.standard_b64encode(f.read()).decode()

    def _build_prompt(self, expected: str) -> str:
        """构建验证提示词"""
        return (
            f"你是一个 UI 测试结果验证助手。请仔细分析这张截图，判断是否符合以下预期描述。\n\n"
            f"预期描述: {expected}\n\n"
            f"请返回 JSON 格式结果:\n"
            f'{{"match": true/false, "reason": "判断原因"}}'
        )

    def _parse_response(self, response: str) -> tuple[bool, str]:
        """解析 LLM 响应，提取验证结果"""
        try:
            result = json.loads(response)
            is_pass = result.get("match", False)
            reason = result.get("reason", "未提供原因")
        except json.JSONDecodeError:
            # 解析失败，尝试简单判断
            is_pass = "true" in response.lower() and "false" not in response.lower()
            reason = f"模型返回非标准 JSON: {response[:200]}"

        logger.info(f"AI 截图验证: {'通过' if is_pass else '失败'} - {reason}")
        return is_pass, reason
