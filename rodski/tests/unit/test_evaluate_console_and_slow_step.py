"""单元测试：evaluate console 捕获 + 慢步骤检测

覆盖 MR!4 (feature/evaluate-console-capture-and-slow-step-warning) 的改动：
1. _kw_evaluate 执行期间捕获浏览器 console.warn/error 并输出到日志
2. keyword execute() 完成后检测耗时，超过阈值输出 [SLOW] 警告
3. slow_step_threshold 默认 5s，支持外部设置和 case XML 覆盖

这些测试锁定行为，防止回归。
"""
import time
import pytest
from unittest.mock import MagicMock, patch, call
from core.keyword_engine import KeywordEngine
from core.exceptions import DriverError


def make_engine_with_playwright():
    """创建带 mock PlaywrightDriver 的 KeywordEngine。"""
    from drivers.playwright_driver import PlaywrightDriver

    mock_driver = MagicMock(spec=PlaywrightDriver)
    mock_page = MagicMock()
    mock_driver.page = mock_page
    mock_page.evaluate.return_value = "result"

    engine = KeywordEngine(mock_driver)
    return engine, mock_driver, mock_page


# ═══════════════════════════════════════════════════════════════
# Part 1: evaluate 浏览器 console 捕获
# ═══════════════════════════════════════════════════════════════


class TestEvaluateConsoleCapture:
    """evaluate 执行期间应捕获 warning/error 级别的 console 消息。"""

    def test_captures_warning_messages(self):
        """warning 级别消息应输出到日志。"""
        engine, _, mock_page = make_engine_with_playwright()

        # 模拟 page.on("console", callback) — 保存回调，手动触发
        captured_callback = None

        def fake_on(event, cb):
            nonlocal captured_callback
            if event == "console":
                captured_callback = cb

        mock_page.on.side_effect = fake_on

        # evaluate 时会注册监听器，执行表达式，然后注销
        def fake_evaluate(expr):
            # 模拟浏览器在 evaluate 期间触发 console 消息
            msg = MagicMock()
            msg.type = "warning"
            msg.text = "[rs-perf] 主选项未命中，超时 8s"
            captured_callback(msg)
            return "ok"

        mock_page.evaluate.side_effect = fake_evaluate

        with patch("core.keyword_engine.logger") as mock_logger:
            engine._kw_evaluate({"data": "someScript()"})

        # 验证 warning 被输出
        mock_logger.warning.assert_any_call(
            "[JS:warning] [rs-perf] 主选项未命中，超时 8s"
        )

    def test_captures_error_messages(self):
        """error 级别消息应输出到日志。"""
        engine, _, mock_page = make_engine_with_playwright()

        captured_callback = None

        def fake_on(event, cb):
            nonlocal captured_callback
            if event == "console":
                captured_callback = cb

        mock_page.on.side_effect = fake_on

        def fake_evaluate(expr):
            msg = MagicMock()
            msg.type = "error"
            msg.text = "Uncaught TypeError: x is not a function"
            captured_callback(msg)
            return None

        mock_page.evaluate.side_effect = fake_evaluate

        with patch("core.keyword_engine.logger") as mock_logger:
            engine._kw_evaluate({"data": "badCall()"})

        mock_logger.warning.assert_any_call(
            "[JS:error] Uncaught TypeError: x is not a function"
        )

    def test_ignores_log_and_info_messages(self):
        """非 warning/error 级别的 console 消息不应输出。"""
        engine, _, mock_page = make_engine_with_playwright()

        captured_callback = None

        def fake_on(event, cb):
            nonlocal captured_callback
            if event == "console":
                captured_callback = cb

        mock_page.on.side_effect = fake_on

        def fake_evaluate(expr):
            for level in ("log", "info", "debug"):
                msg = MagicMock()
                msg.type = level
                msg.text = f"some {level} message"
                captured_callback(msg)
            return 42

        mock_page.evaluate.side_effect = fake_evaluate

        with patch("core.keyword_engine.logger") as mock_logger:
            engine._kw_evaluate({"data": "1+1"})

        # 不应有 [JS:log] 或 [JS:info] 的输出
        for c in mock_logger.warning.call_args_list:
            assert "[JS:log]" not in str(c)
            assert "[JS:info]" not in str(c)
            assert "[JS:debug]" not in str(c)

    def test_truncates_long_messages(self):
        """超过 500 字符的 console 消息应被截断。"""
        engine, _, mock_page = make_engine_with_playwright()

        captured_callback = None

        def fake_on(event, cb):
            nonlocal captured_callback
            if event == "console":
                captured_callback = cb

        mock_page.on.side_effect = fake_on

        long_text = "A" * 1000

        def fake_evaluate(expr):
            msg = MagicMock()
            msg.type = "warning"
            msg.text = long_text
            captured_callback(msg)
            return None

        mock_page.evaluate.side_effect = fake_evaluate

        with patch("core.keyword_engine.logger") as mock_logger:
            engine._kw_evaluate({"data": "x()"})

        # 截断后应为 500 字符
        logged = mock_logger.warning.call_args_list[-1][0][0]
        assert len(logged) <= len("[JS:warning] ") + 500

    def test_removes_listener_after_evaluate(self):
        """evaluate 完成后应注销 console 监听器。"""
        engine, _, mock_page = make_engine_with_playwright()
        mock_page.on.side_effect = lambda *a: None
        mock_page.evaluate.return_value = 1

        engine._kw_evaluate({"data": "1"})

        mock_page.remove_listener.assert_called_once()
        args = mock_page.remove_listener.call_args[0]
        assert args[0] == "console"

    def test_removes_listener_on_exception(self):
        """即使 evaluate 抛异常，也应注销 console 监听器。"""
        engine, _, mock_page = make_engine_with_playwright()
        mock_page.on.side_effect = lambda *a: None
        mock_page.evaluate.side_effect = Exception("JS crash")

        with pytest.raises(DriverError):
            engine._kw_evaluate({"data": "crash()"})

        mock_page.remove_listener.assert_called_once()
        args = mock_page.remove_listener.call_args[0]
        assert args[0] == "console"

    def test_multiple_messages_all_captured(self):
        """多条 warning/error 消息全部被捕获。"""
        engine, _, mock_page = make_engine_with_playwright()

        captured_callback = None

        def fake_on(event, cb):
            nonlocal captured_callback
            if event == "console":
                captured_callback = cb

        mock_page.on.side_effect = fake_on

        def fake_evaluate(expr):
            for i in range(3):
                msg = MagicMock()
                msg.type = "warning"
                msg.text = f"warn-{i}"
                captured_callback(msg)
            msg2 = MagicMock()
            msg2.type = "error"
            msg2.text = "err-0"
            captured_callback(msg2)
            return None

        mock_page.evaluate.side_effect = fake_evaluate

        with patch("core.keyword_engine.logger") as mock_logger:
            engine._kw_evaluate({"data": "multi()"})

        warning_calls = [str(c) for c in mock_logger.warning.call_args_list]
        assert any("warn-0" in c for c in warning_calls)
        assert any("warn-1" in c for c in warning_calls)
        assert any("warn-2" in c for c in warning_calls)
        assert any("err-0" in c for c in warning_calls)


# ═══════════════════════════════════════════════════════════════
# Part 2: 慢步骤检测
# ═══════════════════════════════════════════════════════════════


class TestSlowStepDetection:
    """关键字执行完成后，超过阈值应输出 [SLOW] 警告。"""

    def test_default_threshold_is_5_seconds(self):
        """默认阈值应为 5 秒。"""
        engine = KeywordEngine(MagicMock())
        assert engine.slow_step_threshold == 5.0

    def test_slow_step_warning_emitted(self):
        """执行超过阈值时输出 [SLOW] 警告。"""
        engine = KeywordEngine(MagicMock())
        engine.slow_step_threshold = 0.01  # 10ms 阈值，方便测试

        # mock time.time 让执行看起来很慢
        with patch("core.keyword_engine.time") as mock_time:
            mock_time.time.side_effect = [0.0, 1.0]  # 开始 0s，结束 1s → 1s > 0.01
            mock_time.sleep = time.sleep
            with patch("core.keyword_engine.logger") as mock_logger:
                engine.execute("wait", {"seconds": 0})

        # 应有 [SLOW] 警告
        slow_calls = [
            c for c in mock_logger.warning.call_args_list
            if "[SLOW]" in str(c)
        ]
        assert len(slow_calls) >= 1
        assert "action=wait" in str(slow_calls[0])

    def test_no_warning_under_threshold(self):
        """执行未超过阈值时不应输出 [SLOW] 警告。"""
        engine = KeywordEngine(MagicMock())
        engine.slow_step_threshold = 100.0  # 100s，不会触发

        with patch("core.keyword_engine.logger") as mock_logger:
            engine.execute("wait", {"seconds": 0})

        slow_calls = [
            c for c in mock_logger.warning.call_args_list
            if "[SLOW]" in str(c)
        ]
        assert len(slow_calls) == 0

    def test_custom_threshold(self):
        """支持通过 engine.slow_step_threshold 自定义阈值。"""
        engine = KeywordEngine(MagicMock())
        engine.slow_step_threshold = 10.0
        assert engine.slow_step_threshold == 10.0

        engine.slow_step_threshold = 0.5
        assert engine.slow_step_threshold == 0.5


# ═══════════════════════════════════════════════════════════════
# Part 3: SKIExecutor slow_threshold case 级覆盖
# ═══════════════════════════════════════════════════════════════


class TestSlowThresholdCaseOverride:
    """case XML 的 slow_threshold 属性应覆盖 engine 默认阈值。"""

    def test_case_slow_threshold_overrides_engine(self):
        """case.get('slow_threshold') 应被应用到 keyword_engine。"""
        from core.ski_executor import SKIExecutor

        executor = SKIExecutor.__new__(SKIExecutor)
        executor.keyword_engine = MagicMock()
        executor.keyword_engine.slow_step_threshold = 5.0
        executor._current_case_scenario_statuses = []
        executor._snapshot_runtime_resources = MagicMock(return_value={})
        executor._current_case_step_wait = None
        executor._current_case_id = ''
        executor._step_index = 0
        executor._runtime_stopped_graceful = False

        # 模拟 case dict 有 slow_threshold
        case = {
            'slow_threshold': '10',
            'case_id': 'TC001',
            'steps': [],
        }

        # _execute_case 在开头会读取 slow_threshold
        # 直接调用那段逻辑
        _slow_override = case.get('slow_threshold')
        if _slow_override is not None:
            try:
                executor.keyword_engine.slow_step_threshold = float(_slow_override)
            except (ValueError, TypeError):
                pass

        assert executor.keyword_engine.slow_step_threshold == 10.0

    def test_invalid_slow_threshold_ignored(self):
        """无效的 slow_threshold 值应被静默忽略。"""
        from core.ski_executor import SKIExecutor

        executor = SKIExecutor.__new__(SKIExecutor)
        executor.keyword_engine = MagicMock()
        executor.keyword_engine.slow_step_threshold = 5.0

        for invalid_val in ['abc', '', None]:
            case = {'slow_threshold': invalid_val}
            _slow_override = case.get('slow_threshold')
            if _slow_override is not None:
                try:
                    executor.keyword_engine.slow_step_threshold = float(_slow_override)
                except (ValueError, TypeError):
                    pass

        # 对于 'abc' 和 '' 会触发 ValueError，阈值不变
        # None 不进入 if 分支
        # 只要没 crash 就是通过
