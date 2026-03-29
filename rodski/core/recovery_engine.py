"""恢复引擎 - 执行动态恢复步骤

根据 DiagnosisEngine 生成的诊断报告，执行对应的恢复动作，
包括等待、刷新页面、重试关键字、回收浏览器等。
"""
import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List, Callable

logger = logging.getLogger("rodski")


@dataclass
class RecoveryResult:
    """恢复结果"""
    success: bool = False
    steps_inserted: List[Dict[str, Any]] = field(default_factory=list)
    attempt_count: int = 0
    final_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RecoveryEngine:
    """恢复引擎

    将诊断报告中的 recovery_action 转换为可执行的步骤序列，
    并驱动 KeywordEngine 执行这些步骤。

    RECOVERY_ACTIONS 格式:
        "action_name": lambda(ke, data): ...
    """

    # 恢复动作 → 执行函数
    # ke: KeywordEngine 实例
    # data: 动作参数（如等待秒数）
    RECOVERY_ACTIONS: Dict[str, Callable] = {}

    def __init__(
        self,
        keyword_engine=None,
        browser_recycler=None,
    ):
        """初始化恢复引擎

        Args:
            keyword_engine: KeywordEngine 实例（用于执行 wait 等步骤）
            browser_recycler: BrowserRecycler 实例（用于回收浏览器）
        """
        self._ke = keyword_engine
        self._recycler = browser_recycler

        # 注册默认恢复动作
        self._register_default_actions()

    def _register_default_actions(self) -> None:
        """注册内置恢复动作"""
        self.RECOVERY_ACTIONS = {
            "wait": self._action_wait,
            "refresh": self._action_refresh,
            "screenshot": self._action_screenshot,
            "recycle": self._action_recycle,
            "retry_step": self._action_retry_step,
            "abort": self._action_abort,
        }

    def register_action(self, name: str, handler: Callable) -> None:
        """注册自定义恢复动作

        Args:
            name: 动作名称
            handler: Callable(ke, data) -> bool
        """
        self.RECOVERY_ACTIONS[name] = handler

    def try_recover(
        self,
        diagnosis,  # DiagnosisReport
        context: Optional[Dict[str, Any]] = None,
        max_attempts: int = 2,
    ) -> RecoveryResult:
        """尝试恢复执行

        Args:
            diagnosis: DiagnosisEngine 生成的 DiagnosisReport
            context: 执行上下文 {
                "case_id": "LOGIN_001",
                "step_index": 3,
                "variables": {},
                ...
            }
            max_attempts: 最大恢复尝试次数

        Returns:
            RecoveryResult {
                success: bool,
                steps_inserted: [...],
                attempt_count: int,
                final_error: Optional[str],
            }
        """
        context = context or {}
        result = RecoveryResult()

        recovery_action = diagnosis.recovery_action
        action_name = recovery_action.get("action", "")
        action_data = recovery_action.get("data", "")

        logger.info(
            f"[RecoveryEngine] 开始恢复: action={action_name}, "
            f"data={action_data}, max_attempts={max_attempts}"
        )

        # abort 动作：直接返回失败，不重试
        if action_name == "abort":
            logger.warning(f"[RecoveryEngine] 检测到不可恢复错误: {action_name}")
            result.final_error = f"不可恢复: {action_data}"
            result.attempt_count = 0
            return result

        # 检查是否注册了该动作
        handler = self.RECOVERY_ACTIONS.get(action_name)
        if not handler:
            logger.error(f"[RecoveryEngine] 未知的恢复动作: {action_name}")
            result.final_error = f"未知动作: {action_name}"
            return result

        # 执行恢复动作（最多 max_attempts 次）
        for attempt in range(1, max_attempts + 1):
            result.attempt_count = attempt
            logger.info(
                f"[RecoveryEngine] 恢复尝试 {attempt}/{max_attempts}: {action_name}"
            )

            try:
                success = handler(self._ke, action_data, context)
                if success:
                    result.success = True
                    result.steps_inserted.append({
                        "attempt": attempt,
                        "action": action_name,
                        "data": action_data,
                        "status": "success",
                    })
                    logger.info(
                        f"[RecoveryEngine] ✅ 恢复成功 (尝试 {attempt})"
                    )
                    return result
                else:
                    result.steps_inserted.append({
                        "attempt": attempt,
                        "action": action_name,
                        "data": action_data,
                        "status": "failed",
                    })
                    logger.warning(
                        f"[RecoveryEngine] ❌ 恢复失败 (尝试 {attempt})"
                    )

            except Exception as e:
                result.steps_inserted.append({
                    "attempt": attempt,
                    "action": action_name,
                    "data": action_data,
                    "status": "error",
                    "error": str(e),
                })
                result.final_error = str(e)
                logger.error(
                    f"[RecoveryEngine] ❌ 恢复异常 (尝试 {attempt}): {e}"
                )

            # 尝试之间稍作等待
            if attempt < max_attempts:
                time.sleep(1)

        logger.warning(
            f"[RecoveryEngine] ❌ 恢复耗尽 ({max_attempts} 次): {result.final_error}"
        )
        return result

    # ── 内置恢复动作 ───────────────────────────────────────────────

    def _action_wait(
        self,
        ke,
        data: str,
        context: Dict,
    ) -> bool:
        """等待指定秒数后重试"""
        seconds = float(data) if data else 3.0
        logger.info(f"[RecoveryEngine] wait: 等待 {seconds}s")
        time.sleep(seconds)
        return True  # 等待本身总视为成功，实际重试由调用方处理

    def _action_refresh(
        self,
        ke,
        data: str,
        context: Dict,
    ) -> bool:
        """刷新当前页面"""
        if ke is None or not hasattr(ke, "driver"):
            logger.warning("[RecoveryEngine] refresh: 无有效 driver，跳过")
            return False
        try:
            ke.driver.refresh()
            logger.info("[RecoveryEngine] refresh: 页面已刷新")
            return True
        except Exception as e:
            logger.error(f"[RecoveryEngine] refresh 失败: {e}")
            return False

    def _action_screenshot(
        self,
        ke,
        data: str,
        context: Dict,
    ) -> bool:
        """截图保存"""
        if ke is None or not hasattr(ke, "driver"):
            logger.warning("[RecoveryEngine] screenshot: 无有效 driver，跳过")
            return False
        try:
            case_id = context.get("case_id", "unknown")
            step_idx = context.get("step_index", 0)
            path = ke.driver.screenshot(
                f"screenshot_recovery_{case_id}_step{step_idx}"
            )
            logger.info(f"[RecoveryEngine] screenshot: {path}")
            return True
        except Exception as e:
            logger.error(f"[RecoveryEngine] screenshot 失败: {e}")
            return False

    def _action_recycle(
        self,
        ke,
        data: str,
        context: Dict,
    ) -> bool:
        """回收浏览器实例"""
        if self._recycler is None:
            logger.warning("[RecoveryEngine] recycle: 无 recycler，跳过")
            return False
        try:
            driver = context.get("driver")
            if driver:
                self._recycler.recycle(driver)
                logger.info("[RecoveryEngine] recycle: 浏览器已回收")
                return True
            return False
        except Exception as e:
            logger.error(f"[RecoveryEngine] recycle 失败: {e}")
            return False

    def _action_retry_step(
        self,
        ke,
        data: str,
        context: Dict,
    ) -> bool:
        """重试当前步骤"""
        if ke is None:
            return False
        keyword = context.get("keyword", "")
        params = context.get("params", {})
        if not keyword:
            return False
        try:
            result = ke.execute(keyword, params)
            return bool(result)
        except Exception as e:
            logger.error(f"[RecoveryEngine] retry_step 失败: {e}")
            return False

    def _action_abort(
        self,
        ke,
        data: str,
        context: Dict,
    ) -> bool:
        """中止执行"""
        logger.warning(f"[RecoveryEngine] abort: {data}")
        return False
