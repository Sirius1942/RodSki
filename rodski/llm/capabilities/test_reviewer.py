"""测试结果审核能力 — 使用 LLM 审核测试结果真实性。"""
import base64
import json
import logging
from typing import Dict, List, Optional
from .base import BaseCapability

logger = logging.getLogger(__name__)


class TestReviewerCapability(BaseCapability):
    """使用 LLM 审核测试结果的真实性"""

    def execute(self, log: str, result_xml: str, screenshots: list = None,
                case_xml: str = None, **kwargs) -> dict:
        """执行测试结果审核

        Args:
            log: 执行日志内容
            result_xml: 测试结果 XML 内容
            screenshots: 截图文件路径列表
            case_xml: 测试用例 XML 内容（可选）
            **kwargs: 可覆盖 temperature、max_tokens 等配置

        Returns:
            审核结果字典，包含 verdict / confidence / reason / issues
        """
        return self.review(log, result_xml, screenshots or [], case_xml, **kwargs)

    def review(self, log: str, result_xml: str, screenshots: list,
               case_xml: str = None, **kwargs) -> dict:
        """审核测试结果

        Args:
            log: 执行日志内容
            result_xml: 测试结果 XML 内容
            screenshots: 截图文件路径列表
            case_xml: 测试用例 XML 内容（可选）
            **kwargs: 可覆盖 temperature、max_tokens 等配置

        Returns:
            审核结果字典，包含 verdict / confidence / reason / issues
        """
        try:
            user_prompt = self._build_user_prompt(log, result_xml, case_xml)

            # 从能力配置中获取默认参数
            cap_config = self.client._config.get("capabilities", {}).get(
                "test_reviewer", {}
            )
            call_kwargs = {
                "temperature": kwargs.get("temperature",
                                          cap_config.get("temperature", 0.1)),
                "max_tokens": kwargs.get("max_tokens",
                                         cap_config.get("max_tokens", 2000)),
            }

            # 获取 system_prompt
            system_prompt = cap_config.get("system_prompt", "")

            enable_vision = cap_config.get("enable_vision", True)

            if screenshots and enable_vision:
                # 多模态调用：将第一张截图编码后调用 vision
                # 构建含文本 + 图片的完整 prompt
                combined_prompt = self._build_vision_prompt(
                    user_prompt, system_prompt
                )
                image_base64 = self._encode_image(screenshots[0])
                response = self.client.call_vision(
                    image_base64, combined_prompt, **call_kwargs
                )
            else:
                # 纯文本调用
                full_prompt = f"{system_prompt}\n\n{user_prompt}" if system_prompt else user_prompt
                response = self.client.call_text(full_prompt, **call_kwargs)

            return json.loads(response)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return {
                "verdict": "SUSPICIOUS",
                "confidence": 0.0,
                "reason": f"LLM 返回结果无法解析为 JSON: {e}",
                "issues": ["response_parse_error"],
            }
        except Exception as e:
            logger.error(f"Test reviewer failed: {e}")
            return {
                "verdict": "SUSPICIOUS",
                "confidence": 0.0,
                "reason": f"审核过程出错: {e}",
                "issues": ["reviewer_error"],
            }

    def _build_user_prompt(self, log: str, result_xml: str,
                           case_xml: Optional[str]) -> str:
        """构建用户提示词（复用 llm_reviewer.py 逻辑）"""
        prompt = f"""请审查以下测试结果：

## 测试结果 XML
```xml
{result_xml}
```

## 执行日志（前 3000 字符）
```
{log[:3000]}
```
"""
        if case_xml:
            prompt += f"\n## 测试用例定义\n```xml\n{case_xml}\n```\n"

        prompt += "\n请根据以上信息和截图，判断测试是否真正成功。"
        return prompt

    def _build_vision_prompt(self, user_prompt: str,
                             system_prompt: str) -> str:
        """构建视觉审核提示词"""
        parts = []
        if system_prompt:
            parts.append(system_prompt)
        parts.append(user_prompt)
        parts.append("请同时参考附带的截图进行判断。")
        return "\n\n".join(parts)

    def _encode_image(self, path: str) -> str:
        """Base64 编码图片"""
        with open(path, "rb") as f:
            return base64.standard_b64encode(f.read()).decode()
