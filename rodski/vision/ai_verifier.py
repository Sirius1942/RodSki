"""AI 截图验证器 - 使用视觉大模型验证截图内容

将截图内容与自然语言描述进行匹配，判断是否符合预期。
"""
import logging
from pathlib import Path
from typing import Optional

from .exceptions import VisionError

logger = logging.getLogger("rodski")


class AIScreenshotVerifier:
    """AI 截图验证器

    使用视觉大模型（Vision LLM）分析截图内容，与预期描述进行匹配验证。
    适用于 UI 测试结果验证、登录状态检查、错误提示检测等场景。

    Args:
        model_provider: 模型提供者，"claude" / "openai" / "qwen"，默认 "claude"
        model_name: 模型名称，默认 None（使用提供者默认值）
        api_key_env: API 密钥环境变量名，默认 "ANTHROPIC_API_KEY"
        base_url: API 代理地址，默认 ""（使用官方地址）
        timeout: 请求超时（秒），默认 30

    Example:
        >>> verifier = AIScreenshotVerifier()
        >>> is_pass, reason = verifier.verify(
        ...     screenshot_path="screenshots/login_success.png",
        ...     expected="登录成功，显示用户名张三"
        ... )
        >>> print(f"验证{'通过' if is_pass else '失败'}: {reason}")
    """

    def __init__(
        self,
        model_provider: str = "claude",
        model_name: Optional[str] = None,
        api_key_env: str = "ANTHROPIC_API_KEY",
        base_url: str = "",
        timeout: int = 30,
        llm_client=None,
    ):
        self.model_provider = model_provider
        self.model_name = model_name
        self.api_key_env = api_key_env
        self.base_url = base_url
        self.timeout = timeout
        self._client = None
        self._llm_client = llm_client

    def _get_client(self):
        """获取 LLM 客户端（延迟初始化）"""
        if self._client is not None:
            return self._client

        import os
        api_key = os.environ.get(self.api_key_env)

        if self.model_provider == "claude":
            try:
                import anthropic
                self._client = anthropic.Anthropic(
                    api_key=api_key,
                    base_url=self.base_url or None,
                    timeout=self.timeout,
                )
                return self._client
            except ImportError:
                raise VisionError(
                    "Claude 客户端未安装，请安装: pip install anthropic"
                )

        elif self.model_provider == "openai":
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=api_key,
                    base_url=self.base_url or "https://api.openai.com/v1",
                    timeout=self.timeout,
                )
                return self._client
            except ImportError:
                raise VisionError(
                    "OpenAI 客户端未安装，请安装: pip install openai"
                )

        elif self.model_provider == "qwen":
            if not self.base_url:
                raise VisionError(
                    "Qwen 需要配置 base_url，请设置代理服务器地址"
                )
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=api_key or "dummy",
                    base_url=self.base_url,
                    timeout=self.timeout,
                )
                return self._client
            except ImportError:
                raise VisionError("OpenAI 客户端未安装")

        raise VisionError(f"不支持的模型提供者: {self.model_provider}")

    def verify(self, screenshot_path: str, expected: str) -> tuple[bool, str]:
        """验证截图是否与预期描述一致

        Args:
            screenshot_path: 截图文件路径
            expected: 预期描述（自然语言），例如：
                - "登录成功，显示用户名张三"
                - "出现红色错误提示：操作失败"
                - "页面包含搜索框和提交按钮"

        Returns:
            (is_pass, reason) - 验证是否通过及原因说明
        """
        # 优先使用统一 LLMClient 能力（新路径）
        if self._llm_client is not None:
            return self._verify_via_capability(screenshot_path, expected)

        # 回退到直接 SDK 调用（旧路径，过渡期保留）
        return self._verify_via_direct_sdk(screenshot_path, expected)

    def _verify_via_capability(self, screenshot_path: str, expected: str) -> tuple[bool, str]:
        """通过 LLMClient screenshot_verifier 能力执行验证"""
        try:
            capability = self._llm_client.get_capability("screenshot_verifier")
            return capability.verify(screenshot_path, expected)
        except Exception as e:
            logger.warning(f"LLMClient 能力调用失败，回退到直接 SDK: {e}")
            return self._verify_via_direct_sdk(screenshot_path, expected)

    def _verify_via_direct_sdk(self, screenshot_path: str, expected: str) -> tuple[bool, str]:
        """直接使用 SDK 执行验证（旧路径）"""
        import os
        from pathlib import Path

        screenshot_path = Path(screenshot_path)
        if not screenshot_path.exists():
            return False, f"截图文件不存在: {screenshot_path}"

        try:
            client = self._get_client()
            image_data = screenshot_path.read_bytes()
            import base64
            image_b64 = base64.b64encode(image_data).decode("utf-8")

            prompt = (
                f"你是一个 UI 测试结果验证助手。请仔细分析这张截图，判断是否符合以下预期描述。\n\n"
                f"预期描述: {expected}\n\n"
                f"请返回 JSON 格式结果:\n"
                f'{{"match": true/false, "reason": "判断原因"}}'
            )

            if self.model_provider == "claude":
                response = client.messages.create(
                    model=self.model_name or "claude-3-5-sonnet-20241022",
                    max_tokens=512,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/png",
                                        "data": image_b64,
                                    },
                                },
                                {"type": "text", "text": prompt},
                            ],
                        }
                    ],
                )
                result_text = response.content[0].text

            else:  # openai / qwen
                response = client.chat.completions.create(
                    model=self.model_name or "gpt-4o",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{image_b64}"
                                    },
                                },
                                {"type": "text", "text": prompt},
                            ],
                        }
                    ],
                    max_tokens=512,
                )
                result_text = response.choices[0].message.content

            # 解析 JSON 结果
            import json

            try:
                result = json.loads(result_text)
                is_pass = result.get("match", False)
                reason = result.get("reason", "未提供原因")
            except json.JSONDecodeError:
                # 解析失败，尝试简单判断
                is_pass = "true" in result_text.lower() and "false" not in result_text.lower()
                reason = f"模型返回非标准 JSON: {result_text[:200]}"

            logger.info(
                f"AI 截图验证: {'通过' if is_pass else '失败'} - {reason}"
            )
            return is_pass, reason

        except Exception as e:
            logger.error(f"AI 截图验证异常: {e}")
            return False, f"验证异常: {str(e)}"

    def verify_with_reference(
        self,
        screenshot_path: str,
        reference_image_path: str,
        threshold: float = 0.8,
    ) -> tuple[bool, str]:
        """对比截图与参考图相似度

        Args:
            screenshot_path: 待验证截图
            reference_image_path: 参考图路径
            threshold: 相似度阈值 (0-1)，默认 0.8

        Returns:
            (is_pass, reason)
        """
        try:
            import cv2
            import numpy as np

            img1 = cv2.imread(str(screenshot_path))
            img2 = cv2.imread(str(reference_image_path))

            if img1 is None:
                return False, f"无法读取截图: {screenshot_path}"
            if img2 is None:
                return False, f"无法读取参考图: {reference_image_path}"

            # 调整为相同尺寸
            h, w = img2.shape[:2]
            img1 = cv2.resize(img1, (w, h))

            # 计算 SSIM
            from skimage.metrics import structural_similarity as ssim

            gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

            score = ssim(gray1, gray2)
            is_pass = score >= threshold

            reason = f"相似度 {score:.2%}，阈值 {threshold:.2%}"
            logger.info(f"图像对比验证: {'通过' if is_pass else '失败'} - {reason}")
            return is_pass, reason

        except ImportError:
            return False, "需要安装 scikit-image: pip install scikit-image"
        except Exception as e:
            return False, f"图像对比异常: {str(e)}"


def analyze_recording(recording_path: str, question: str) -> str:
    """分析录像内容，提取关键帧并用视觉大模型分析

    用于测试失败后分析录像，定位问题根因。

    Args:
        recording_path: 录像文件路径 (.mp4)
        question: 分析问题，例如：
            - "找出测试失败的画面"
            - "分析鼠标点击的位置是否正确"
            - "检测是否有弹窗或错误提示"

    Returns:
        分析结果描述

    Raises:
        RuntimeError: 录像分析失败时抛出
    """
    import os
    import cv2
    import tempfile
    from pathlib import Path

    path = Path(recording_path)
    if not path.exists():
        raise RuntimeError(f"录像文件不存在: {recording_path}")

    try:
        import mss
        import numpy as np
    except ImportError:
        raise RuntimeError("分析录像需要安装: pip install mss opencv-python")

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"无法打开录像文件: {recording_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps if fps > 0 else 0

    # 每隔 N 帧采样一帧进行快速扫描
    sample_interval = max(1, int(fps * 5))  # 每 5 秒采一帧
    key_frames = []
    timestamps = []

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % sample_interval == 0:
            # 保存临时帧
            with tempfile.NamedTemporaryFile(
                suffix=".png", delete=False
            ) as f:
                cv2.imwrite(f.name, frame)
                key_frames.append(f.name)
                timestamps.append(frame_idx / fps)

        frame_idx += 1

    cap.release()

    if not key_frames:
        return "录像中未提取到关键帧（录像可能为空）"

    # 调用 AI 分析关键帧
    try:
        verifier = AIScreenshotVerifier()

        # 最多分析前 10 帧
        analysis_results = []
        for i, (frame_path, ts) in enumerate(
            zip(key_frames[:10], timestamps[:10])
        ):
            is_pass, reason = verifier.verify(
                screenshot_path=frame_path,
                expected=question,
            )
            analysis_results.append(
                f"[{int(ts)}s] {'✓' if is_pass else '✗'} {reason}"
            )
            # 清理临时文件
            try:
                os.unlink(frame_path)
            except Exception:
                pass

        summary = (
            f"录像分析完成 ({duration:.1f}s, {frame_count} 帧, "
            f"采样 {len(key_frames)} 帧):\n"
        )
        summary += "\n".join(analysis_results)
        return summary

    except Exception as e:
        # 清理临时文件
        for fp in key_frames:
            try:
                os.unlink(fp)
            except Exception:
                pass
        raise RuntimeError(f"录像 AI 分析失败: {e}")
