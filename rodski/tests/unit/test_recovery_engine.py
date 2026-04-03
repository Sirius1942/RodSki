"""RecoveryEngine 单元测试 - 覆盖 success / failure / retry 场景"""
import pytest
from unittest.mock import MagicMock

from core.recovery_engine import RecoveryEngine, RecoveryResult
from core.diagnosis_engine import DiagnosisEngine, DiagnosisReport


def make_mock_ke():
    """创建一个 mock KeywordEngine"""
    ke = MagicMock()
    ke.driver = MagicMock()
    return ke


def make_mock_recycler():
    return MagicMock()


class TestRecoveryResult:
    """RecoveryResult 数据类测试"""

    def test_default_values(self):
        result = RecoveryResult()
        assert result.success is False
        assert result.steps_inserted == []
        assert result.attempt_count == 0
        assert result.final_error is None

    def test_to_dict(self):
        result = RecoveryResult(success=True, attempt_count=2)
        d = result.to_dict()
        assert d["success"] is True
        assert d["attempt_count"] == 2
        assert d["steps_inserted"] == []


class TestRecoveryEngineInit:
    """RecoveryEngine 初始化测试"""

    def test_init_with_no_args(self):
        engine = RecoveryEngine()
        assert engine._ke is None
        assert engine._recycler is None
        assert "wait" in engine.RECOVERY_ACTIONS
        assert "refresh" in engine.RECOVERY_ACTIONS
        assert "recycle" in engine.RECOVERY_ACTIONS
        assert "abort" in engine.RECOVERY_ACTIONS

    def test_init_with_ke_and_recycler(self):
        ke = make_mock_ke()
        recycler = make_mock_recycler()
        engine = RecoveryEngine(keyword_engine=ke, browser_recycler=recycler)
        assert engine._ke is ke
        assert engine._recycler is recycler

    def test_register_custom_action(self):
        engine = RecoveryEngine()
        handler = MagicMock(return_value=True)
        engine.register_action("custom", handler)
        assert "custom" in engine.RECOVERY_ACTIONS
        assert engine.RECOVERY_ACTIONS["custom"] is handler


class TestRecoveryWait:
    """wait 恢复动作测试"""

    def test_wait_action_success(self):
        engine = RecoveryEngine()
        context = {}
        # wait 不抛异常，总返回 True
        result = engine._action_wait(None, "2", context)
        assert result is True

    def test_wait_action_default_seconds(self):
        engine = RecoveryEngine()
        context = {}
        result = engine._action_wait(None, "", context)  # 空数据用默认值
        assert result is True


class TestRecoveryRefresh:
    """refresh 恢复动作测试"""

    def test_refresh_success(self):
        ke = make_mock_ke()
        engine = RecoveryEngine(keyword_engine=ke)
        result = engine._action_refresh(ke, "", {})
        assert result is True
        ke.driver.refresh.assert_called_once()

    def test_refresh_no_driver(self):
        engine = RecoveryEngine(keyword_engine=None)
        result = engine._action_refresh(None, "", {})
        assert result is False

    def test_refresh_raises(self):
        ke = make_mock_ke()
        ke.driver.refresh.side_effect = RuntimeError("browser closed")
        engine = RecoveryEngine(keyword_engine=ke)
        result = engine._action_refresh(ke, "", {})
        assert result is False


class TestRecoveryScreenshot:
    """screenshot 恢复动作测试"""

    def test_screenshot_success(self):
        ke = make_mock_ke()
        ke.driver.screenshot.return_value = "screenshots/test.png"
        engine = RecoveryEngine(keyword_engine=ke)
        result = engine._action_screenshot(ke, "", {"case_id": "TEST_001"})
        assert result is True
        ke.driver.screenshot.assert_called()

    def test_screenshot_no_driver(self):
        engine = RecoveryEngine(keyword_engine=None)
        result = engine._action_screenshot(None, "", {})
        assert result is False


class TestRecoveryRecycle:
    """recycle 恢复动作测试"""

    def test_recycle_success(self):
        recycler = make_mock_recycler()
        engine = RecoveryEngine(browser_recycler=recycler)
        driver = MagicMock()
        result = engine._action_recycle(None, "", {"driver": driver})
        assert result is True
        recycler.recycle.assert_called_once_with(driver)

    def test_recycle_no_recycler(self):
        engine = RecoveryEngine(browser_recycler=None)
        result = engine._action_recycle(None, "", {"driver": MagicMock()})
        assert result is False

    def test_recycle_no_driver_in_context(self):
        recycler = make_mock_recycler()
        engine = RecoveryEngine(browser_recycler=recycler)
        result = engine._action_recycle(None, "", {})
        assert result is False


class TestRecoveryAbort:
    """abort 恢复动作测试"""

    def test_abort_always_returns_false(self):
        engine = RecoveryEngine()
        result = engine._action_abort(None, "UnknownKeyword", {})
        assert result is False


class TestTryRecover:
    """try_recover 核心逻辑测试"""

    def test_abort_action_returns_immediately(self):
        """abort 动作直接返回，不重试"""
        engine = RecoveryEngine()
        diagnosis = DiagnosisReport(
            failure_point="step=1",
            failure_reason="unknown keyword",
            recovery_action={"action": "abort", "data": "UnknownKeywordError"},
        )
        result = engine.try_recover(diagnosis, {}, max_attempts=3)
        assert result.success is False
        assert result.attempt_count == 0
        assert "不可恢复" in result.final_error

    def test_unknown_action_returns_failure(self):
        """未知动作直接返回失败"""
        engine = RecoveryEngine()
        diagnosis = DiagnosisReport(
            recovery_action={"action": "nonexistent_action", "data": ""},
        )
        result = engine.try_recover(diagnosis, {})
        assert result.success is False
        assert "未知动作" in result.final_error

    def test_wait_action_single_attempt(self):
        """wait 动作成功（1 次）"""
        engine = RecoveryEngine()
        diagnosis = DiagnosisReport(
            recovery_action={"action": "wait", "data": "1"},
        )
        result = engine.try_recover(diagnosis, {}, max_attempts=1)
        assert result.success is True
        assert result.attempt_count == 1
        assert len(result.steps_inserted) == 1
        assert result.steps_inserted[0]["status"] == "success"

    def test_wait_action_retry_exhausted(self):
        """wait 动作每次都成功，成功后立即返回（不继续重试）"""
        engine = RecoveryEngine()
        diagnosis = DiagnosisReport(
            recovery_action={"action": "wait", "data": "0"},
        )
        result = engine.try_recover(diagnosis, {}, max_attempts=3)
        # wait 动作立即返回 True，第一成功后即退出，不做额外重试
        assert result.success is True
        assert result.attempt_count == 1
        assert len(result.steps_inserted) == 1

    def test_refresh_action_success_with_driver(self):
        """refresh 动作成功"""
        ke = make_mock_ke()
        engine = RecoveryEngine(keyword_engine=ke)
        diagnosis = DiagnosisReport(
            recovery_action={"action": "refresh", "data": ""},
        )
        result = engine.try_recover(diagnosis, {}, max_attempts=1)
        assert result.success is True
        ke.driver.refresh.assert_called_once()

    def test_refresh_action_failure_no_driver(self):
        """refresh 动作失败（无 driver）"""
        engine = RecoveryEngine(keyword_engine=None)
        diagnosis = DiagnosisReport(
            recovery_action={"action": "refresh", "data": ""},
        )
        result = engine.try_recover(diagnosis, {})
        assert result.success is False

    def test_custom_action_registered(self):
        """自定义恢复动作"""
        engine = RecoveryEngine()
        handler = MagicMock(return_value=True)
        engine.register_action("custom", handler)
        diagnosis = DiagnosisReport(
            recovery_action={"action": "custom", "data": "test_data"},
        )
        result = engine.try_recover(diagnosis, {"extra": "ctx"}, max_attempts=1)
        assert result.success is True
        handler.assert_called_once()

    def test_recovery_records_all_attempts(self):
        """记录每次尝试的详情（使用返回 False 的 action 触发多次尝试）"""
        engine = RecoveryEngine()

        # 注册一个前两次失败、第三次成功的 action
        call_count = [0]

        def flaky_handler(ke, data, ctx):
            call_count[0] += 1
            return call_count[0] == 3  # 前两次失败，第三次成功

        engine.register_action("flaky", flaky_handler)
        diagnosis = DiagnosisReport(
            recovery_action={"action": "flaky", "data": ""},
        )
        result = engine.try_recover(diagnosis, {}, max_attempts=3)
        assert result.success is True
        assert len(result.steps_inserted) == 3
        assert result.attempt_count == 3

    def test_context_passed_to_handler(self):
        """context 被正确传递给 handler"""
        engine = RecoveryEngine()
        captured_context = {}
        def capture_ctx(ke, data, ctx):
            captured_context.update(ctx)
            return True
        engine.register_action("capture_ctx", capture_ctx)
        diagnosis = DiagnosisReport(
            recovery_action={"action": "capture_ctx", "data": ""},
        )
        engine.try_recover(diagnosis, {"case_id": "LOGIN_001", "step": 5}, max_attempts=1)
        assert captured_context.get("case_id") == "LOGIN_001"
        assert captured_context.get("step") == 5


class TestDiagnosisEngineIntegration:
    """DiagnosisEngine + RecoveryEngine 集成测试"""

    def test_element_not_found_gets_wait_action(self):
        from core.exceptions import ElementNotFoundError
        from vision.exceptions import ElementNotFoundError as VisionElementNotFound

        engine = DiagnosisEngine()
        err = ElementNotFoundError(locator="#btn", message="元素未找到")
        report = engine.diagnose(err)
        assert report.recovery_action["action"] == "wait"
        assert report.recovery_action["data"] == "3"

    def test_assertion_failed_gets_screenshot_action(self):
        from core.exceptions import AssertionFailedError

        engine = DiagnosisEngine()
        err = AssertionFailedError(message="期望值不匹配", expected="OK", actual="FAIL")
        report = engine.diagnose(err)
        assert report.recovery_action["action"] == "screenshot"

    def test_unknown_keyword_is_unrecoverable(self):
        from core.exceptions import UnknownKeywordError

        engine = DiagnosisEngine()
        err = UnknownKeywordError("bad_keyword", supported=["a", "b"])
        report = engine.diagnose(err)
        assert report.recovery_action["action"] == "abort"
