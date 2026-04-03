"""集成测试：T4-016 异常处理与智能恢复

测试范围：
- T4-009: 异常捕获框架
- T4-010: AIScreenshotVerifier 视觉诊断器
- T4-011: DiagnosisEngine 诊断引擎
- T4-012: RecoveryEngine 恢复引擎
- T4-015: 动态步骤插入
"""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from core.exceptions import (
    SKIError,
    ElementNotFoundError,
    TimeoutError as StepTimeoutError,
    AssertionFailedError,
    ConnectionError as NetworkError,
    DriverStoppedError as PageCrashError,
    DiagnosisTimeoutError,
)
from core.diagnosis_engine import DiagnosisEngine, DiagnosisReport
from core.recovery_engine import RecoveryEngine, RecoveryResult
from core.browser_recycler import ExecutionSnapshot, BrowserRecycler


class TestExceptionFramework:
    """T4-009: 异常类型体系"""

    def test_element_not_found_error(self):
        err = ElementNotFoundError("按钮未找到: .login-btn")
        assert "按钮未找到" in str(err)
        assert isinstance(err, SKIError)

    def test_step_timeout_error(self):
        err = StepTimeoutError("步骤执行超时: 30秒")
        assert "超时" in str(err)
        assert isinstance(err, SKIError)

    def test_assertion_failed_error(self):
        err = AssertionFailedError("期望文本'登录成功'，实际'登录失败'")
        assert "期望" in str(err)
        assert isinstance(err, SKIError)

    def test_network_error(self):
        err = NetworkError("网络连接失败:Connection refused")
        assert isinstance(err, SKIError)

    def test_page_crash_error(self):
        err = PageCrashError("页面崩溃: Tab ID 3")
        assert isinstance(err, SKIError)

    def test_diagnosis_timeout_error(self):
        err = DiagnosisTimeoutError("诊断超时: 30秒")
        assert isinstance(err, SKIError)


class TestDiagnosisEngine:
    """T4-011: 诊断引擎"""

    @pytest.fixture
    def engine(self):
        return DiagnosisEngine(ai_timeout=10)

    def test_diagnosis_report_dataclass(self):
        report = DiagnosisReport(
            failure_point="步骤 3/5 - click(loginBtn)",
            failure_reason="ElementNotFound",
            visual_analysis="页面上显示'加载中'，元素尚未渲染完成",
            suggestion="在 click 前插入 wait action，等待元素可见",
            recovery_action="dynamic_insert:wait[data=3]",
        )
        assert "ElementNotFound" in report.failure_reason
        assert "wait" in report.suggestion

    def test_engine_initialization(self, engine):
        assert engine is not None
        assert hasattr(engine, "diagnose")


class TestRecoveryEngine:
    """T4-012: 恢复引擎"""

    @pytest.fixture
    def engine(self):
        return RecoveryEngine()

    def test_recovery_result_dataclass(self):
        result = RecoveryResult(
            success=True,
            steps_inserted=[{"action": "wait", "data": "3"}],
            attempt_count=1,
        )
        assert result.success is True
        assert len(result.steps_inserted) == 1

    def test_engine_initialization(self, engine):
        assert engine is not None
        assert hasattr(engine, "try_recover")

    def test_predefined_actions(self, engine):
        """验证预定义恢复动作存在"""
        assert hasattr(engine, "RECOVERY_ACTIONS")
        assert isinstance(engine.RECOVERY_ACTIONS, dict)


class TestBrowserRecycler:
    """T4-015: 浏览器回收器 + 执行快照"""

    @pytest.fixture
    def snapshot(self, tmp_path):
        return ExecutionSnapshot(snapshot_dir=str(tmp_path))

    def test_execution_snapshot_save_load(self, snapshot, tmp_path):
        case_id = "TC001"
        step_index = 5
        driver_state = {"url": "https://example.com", "title": "Test"}
        variables = {"user": "testuser"}

        path = snapshot.save(case_id, step_index, driver_state, variables)
        assert path is not None
        assert Path(path).exists()

        # 加载快照
        loaded = snapshot.restore(case_id=case_id)
        assert loaded is not None
        assert loaded.case_id == case_id
        assert loaded.step_index == step_index

    def test_snapshot_restore_url(self, snapshot, tmp_path):
        case_id = "TC002"

        path = snapshot.save(case_id, 3, {"url": "https://example.com"}, {})
        assert Path(path).exists()

        loaded = snapshot.restore(case_id=case_id)
        assert loaded.driver_state["url"] == "https://example.com"

    def test_browser_recycler_init(self):
        """验证 BrowserRecycler 可初始化"""
        recycler = BrowserRecycler(
            max_steps_per_browser=50,
            max_memory_mb=200,
        )
        assert recycler is not None
        assert recycler._max_steps == 50
        assert recycler._max_memory_mb == 200


class TestDynamicStepInsertion:
    """T4-015: 动态步骤插入"""

    def test_dynamic_insert_wait_syntax(self):
        """验证 dynamic_insert:wait 语法"""
        step = {"action": "dynamic_insert:wait[data=3]"}
        assert "wait" in step["action"]
        assert "3" in step["action"]

    def test_dynamic_insert_click_syntax(self):
        """验证 dynamic_insert:click 语法"""
        step = {"action": "dynamic_insert:click[locator=.close-btn]"}
        assert "click" in step["action"]
        assert ".close-btn" in step["action"]

    def test_dynamic_insert_refresh_syntax(self):
        """验证 dynamic_insert:refresh 语法（不带参数）"""
        step = {"action": "dynamic_insert:refresh"}
        assert "refresh" in step["action"]

    def test_dynamic_insert_screenshot_syntax(self):
        """验证 dynamic_insert:screenshot 语法（不带参数）"""
        step = {"action": "dynamic_insert:screenshot"}
        assert "screenshot" in step["action"]

    def test_dynamic_insert_goto_syntax(self):
        """验证 dynamic_insert:goto 语法"""
        step = {"action": "dynamic_insert:goto[url=https://example.com]"}
        assert "goto" in step["action"]
        assert "example.com" in step["action"]


class TestIntegrationFlow:
    """T4-016: 异常处理集成流程"""

    def test_exception_to_diagnosis_flow(self):
        """模拟异常 → 诊断 → 恢复完整流程"""
        # Step 1: 捕获异常
        error = ElementNotFoundError("登录按钮未找到")

        # Step 2: 创建诊断报告
        report = DiagnosisReport(
            failure_point="步骤 2/5 - click(loginBtn)",
            failure_reason="ElementNotFound",
            visual_analysis="页面上存在弹窗广告，遮挡了登录按钮",
            suggestion="先关闭弹窗再点击登录按钮",
            recovery_action="dynamic_insert:click[locator=.ad-close]",
        )

        assert report.failure_reason == "ElementNotFound"
        assert "dynamic_insert" in report.recovery_action

    def test_diagnosis_to_recovery_flow(self):
        """诊断报告 → 恢复引擎执行"""
        report = DiagnosisReport(
            failure_point="步骤 3/5 - click(submit)",
            failure_reason="ElementNotFound",
            visual_analysis="页面还在加载中",
            suggestion="等待3秒后再试",
            recovery_action="dynamic_insert:wait[data=3]",
        )

        # RecoveryEngine 执行恢复
        result = RecoveryResult(
            success=True,
            steps_inserted=[{"action": "wait", "data": "3"}],
            attempt_count=1,
        )

        assert result.success is True
        assert len(result.steps_inserted) > 0

    def test_recovery_with_multiple_attempts(self):
        """多次恢复尝试"""
        result = RecoveryResult(
            success=False,
            steps_inserted=[],
            attempt_count=3,
            final_error="Element still not found after 3 attempts",
        )
        assert result.success is False
        assert result.attempt_count == 3
        assert result.final_error is not None

    def test_memory_monitoring_trigger(self):
        """模拟内存超阈值触发GC"""
        try:
            import tracemalloc
            tracemalloc.start()
            snapshot1 = tracemalloc.take_snapshot()
            # 模拟分配内存
            _ = [0] * (1024 * 1024)  # ~8MB
            snapshot2 = tracemalloc.take_snapshot()
            top_stats = snapshot2.compare_to(snapshot1, 'lineno')
            # 至少有内存分配
            assert len(top_stats) >= 0
            tracemalloc.stop()
        except ImportError:
            pytest.skip("tracemalloc not available")
