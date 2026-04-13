"""诊断引擎 - 分析异常并生成诊断报告

使用 AI 视觉分析 + 规则映射，对执行过程中出现的异常进行
智能诊断，定位失败点并推荐恢复动作。
"""
import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List

from core.exceptions import DiagnosisTimeoutError

logger = logging.getLogger("rodski")


@dataclass
class DiagnosisReport:
    """诊断报告"""
    failure_point: str = ""
    failure_reason: str = ""
    visual_analysis: str = ""
    suggestion: str = ""
    recovery_action: Dict[str, Any] = field(default_factory=dict)
    # {"action": "wait", "data": "3"}
    ai_model: str = "claude"
    diagnosis_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DiagnosisEngine:
    """诊断引擎

    将异常类型映射到恢复动作，同时支持 AI 视觉辅助分析。

    ERROR_ACTION_MAP 格式:
        "ErrorTypeName": {"action": "action_name", "data": "action_data"}
    """

    # 错误类型 → 恢复动作 映射表
    ERROR_ACTION_MAP: Dict[str, Dict[str, Any]] = {
        "ElementNotFoundError": {"action": "wait", "data": "3"},
        "ElementNotFound":      {"action": "wait", "data": "3"},
        "TimeoutError":         {"action": "refresh", "data": ""},
        "StepTimeout":          {"action": "refresh", "data": ""},
        "StaleElementError":    {"action": "wait", "data": "2"},
        "StaleElement":         {"action": "wait", "data": "2"},
        "AssertionFailedError": {"action": "screenshot", "data": ""},
        "AssertionFailed":      {"action": "screenshot", "data": ""},
        "DriverStoppedError":   {"action": "recycle", "data": ""},
        "DriverStopped":        {"action": "recycle", "data": ""},
    }

    # 无法恢复的错误类型（直接标记为 FAIL，不再重试）
    UNRECOVERABLE_TYPES: List[str] = [
        "UnknownKeywordError",
        "InvalidParameterError",
        "CaseParseError",
        "ModelParseError",
        "ConfigurationError",
    ]

    def __init__(
        self,
        ai_verifier=None,
        ai_model: str = "claude",
        ai_timeout: int = 30,
        llm_client=None,
    ):
        """初始化诊断引擎

        Args:
            ai_verifier: AIScreenshotVerifier 实例，用于 AI 视觉分析
            ai_model: AI 模型名称
            ai_timeout: AI 分析超时（秒）
            llm_client: 统一 LLMClient 实例（可选）。若提供，
                        优先使用其 screenshot_verifier 能力进行视觉分析，
                        否则回退到 ai_verifier。
        """
        self._ai_verifier = ai_verifier
        self.ai_model = ai_model
        self.ai_timeout = ai_timeout
        self._llm_client = llm_client

    def diagnose(
        self,
        error: Exception,
        screenshot_path: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> DiagnosisReport:
        """诊断异常并生成报告

        Args:
            error: 捕获的异常对象
            screenshot_path: 失败时的截图路径（可选）
            context: 额外的执行上下文，如 {
                "step_index": 3,
                "keyword": "verify",
                "case_id": "LOGIN_001",
                "variables": {...},
            }

        Returns:
            DiagnosisReport 诊断报告
        """
        context = context or {}
        error_type = type(error).__name__
        error_msg = str(error)

        start_time = time.time()

        # 1. 规则匹配：直接从 ERROR_ACTION_MAP 获取恢复动作
        recovery_action = self.ERROR_ACTION_MAP.get(error_type, {}).copy()

        # 2. 判断是否为不可恢复错误
        if error_type in self.UNRECOVERABLE_TYPES:
            recovery_action = {"action": "abort", "data": error_type}

        # 3. AI 视觉辅助分析（如果有截图 + AI 分析器）
        visual_analysis = ""
        if screenshot_path and (self._llm_client or self._ai_verifier):
            visual_analysis = self._try_visual_analysis(screenshot_path, error_type, error_msg)

        # 4. 生成诊断报告
        diagnosis_time_ms = (time.time() - start_time) * 1000

        report = DiagnosisReport(
            failure_point=self._format_failure_point(context),
            failure_reason=error_msg,
            visual_analysis=visual_analysis,
            suggestion=self._format_suggestion(error_type, recovery_action),
            recovery_action=recovery_action,
            ai_model=self.ai_model,
            diagnosis_time_ms=diagnosis_time_ms,
        )

        logger.info(
            f"[DiagnosisEngine] {error_type} → action={recovery_action.get('action')}, "
            f"suggestion={report.suggestion[:50]}..."
        )
        return report

    def _try_visual_analysis(
        self,
        screenshot_path: str,
        error_type: str,
        error_msg: str,
    ) -> str:
        """调用 AI verifier 进行视觉分析

        优先使用 llm_client 的 screenshot_verifier 能力；
        若不可用则回退到传统 ai_verifier 实例。
        """
        prompt = (
            f"分析这张截图，找出问题原因。\n"
            f"异常类型: {error_type}\n"
            f"异常信息: {error_msg}\n\n"
            f"请描述你看到了什么，以及最可能的问题原因。"
        )

        # 优先：通过统一 LLMClient 的 screenshot_verifier 能力
        if self._llm_client is not None:
            try:
                verifier = self._llm_client.get_capability("screenshot_verifier")
                is_pass, reason = verifier.verify(
                    screenshot_path=screenshot_path,
                    expected=prompt,
                )
                return reason
            except Exception as e:
                logger.warning(f"[DiagnosisEngine] LLMClient 视觉分析失败: {e}")
                # 继续尝试 fallback

        # 回退：传统 ai_verifier
        if self._ai_verifier is not None:
            try:
                is_pass, reason = self._ai_verifier.verify(
                    screenshot_path=screenshot_path,
                    expected=prompt,
                )
                return reason
            except Exception as e:
                logger.warning(f"[DiagnosisEngine] AI 视觉分析失败: {e}")
                return f"AI 分析不可用: {e}"

        return "AI 分析不可用: 无可用的视觉分析器"

    def _format_failure_point(self, context: Dict[str, Any]) -> str:
        """格式化失败位置描述"""
        parts = []
        if context.get("case_id"):
            parts.append(f"case={context['case_id']}")
        if context.get("step_index") is not None:
            parts.append(f"step={context['step_index']}")
        if context.get("keyword"):
            parts.append(f"keyword={context['keyword']}")
        return ", ".join(parts) if parts else "unknown"

    def _format_suggestion(
        self,
        error_type: str,
        recovery_action: Dict[str, Any],
    ) -> str:
        """生成恢复建议"""
        action = recovery_action.get("action", "unknown")
        data = recovery_action.get("data", "")

        suggestions = {
            "wait":      f"等待 {data}s 后重试",
            "refresh":   "刷新页面后重试",
            "screenshot": "截图已保存，请人工确认",
            "recycle":   "浏览器实例已回收，尝试重建",
            "abort":     "不可恢复错误，标记为失败",
        }
        return suggestions.get(action, f"执行动作: {action} {data}")
