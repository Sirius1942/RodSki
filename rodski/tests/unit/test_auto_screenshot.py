"""失败自动截图功能单元测试 - XML 版本

使用 RodSki 自有测试执行器，不依赖 pytest。
"""
from pathlib import Path
from unittest.mock import Mock

from core.ski_executor import SKIExecutor
from core.config_manager import ConfigManager
from drivers.base_driver import BaseDriver


def _build_module(tmp_path: Path) -> Path:
    """创建最小化的 XML 测试模块目录结构，返回 module_dir。"""
    module_dir = tmp_path / "test_module"
    (module_dir / "case").mkdir(parents=True)
    (module_dir / "model").mkdir()
    (module_dir / "data").mkdir()
    (module_dir / "result").mkdir()

    (module_dir / "model" / "model.xml").write_text('''\
<?xml version="1.0" encoding="UTF-8"?>
<models>
  <model name="test">
    <element name="input">
      <location type="id">username</location>
    </element>
  </model>
</models>''', encoding="utf-8")

    (module_dir / "data" / "globalvalue.xml").write_text('''\
<?xml version="1.0" encoding="UTF-8"?>
<globalvalue>
  <group name="DefaultValue">
    <var name="WaitTime" value="0"/>
  </group>
</globalvalue>''', encoding="utf-8")

    (module_dir / "case" / "test.xml").write_text('''\
<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="TC001" title="登录测试">
    <test_case>
      <test_step action="wait" model="" data="1"/>
    </test_case>
  </case>
</cases>''', encoding="utf-8")

    return module_dir


def _make_mock_driver() -> Mock:
    driver = Mock(spec=BaseDriver)
    driver.screenshot = Mock(return_value=True)
    driver.click = Mock(return_value=True)
    driver.type = Mock(return_value=True)
    driver.navigate = Mock(return_value=True)
    driver.close = Mock(return_value=True)
    driver.wait = Mock(return_value=True)
    return driver


def _make_config(tmp_path: Path, auto_screenshot: bool = True) -> ConfigManager:
    config = ConfigManager(str(tmp_path / f"config_{auto_screenshot}.json"))
    config.set("auto_screenshot_on_failure", auto_screenshot)
    if auto_screenshot:
        config.set("screenshot_dir", str(tmp_path / "screenshots"))
    return config


class TestScreenshotConfig:
    def test_default_config_has_screenshot_enabled(self):
        config = ConfigManager()
        assert config.get("auto_screenshot_on_failure") == True
        assert config.get("screenshot_dir") == "screenshots"

    def test_config_can_disable_screenshot(self, tmp_path):
        config = ConfigManager(str(tmp_path / "test_config.json"))
        config.set("auto_screenshot_on_failure", False)
        assert config.get("auto_screenshot_on_failure") == False


class TestSKIExecutorScreenshot:
    def test_executor_inits_with_screenshot_config(self, tmp_path):
        module_dir = _build_module(tmp_path)
        case_path = str(module_dir / "case" / "test.xml")
        config = _make_config(tmp_path, True)
        executor = SKIExecutor(case_path, _make_mock_driver(), config)
        assert executor.auto_screenshot == True

    def test_executor_respects_disabled_screenshot(self, tmp_path):
        module_dir = _build_module(tmp_path)
        case_path = str(module_dir / "case" / "test.xml")
        config = _make_config(tmp_path, False)
        executor = SKIExecutor(case_path, _make_mock_driver(), config)
        assert executor.auto_screenshot == False

    def test_screenshot_taken_on_failure(self, tmp_path):
        module_dir = _build_module(tmp_path)
        case_path = str(module_dir / "case" / "test.xml")
        mock_driver = _make_mock_driver()
        mock_driver.wait.side_effect = RuntimeError("Element not found")
        config = _make_config(tmp_path, True)
        executor = SKIExecutor(case_path, mock_driver, config)
        executor.result_writer._init_run_dir()

        case = {
            'case_id': 'TC_FAIL',
            'title': '失败测试',
            'pre_process': [],
            'test_case': [{'action': 'wait', 'model': '', 'data': '1'}],
            'post_process': [],
        }

        result = executor.execute_case(case)
        assert result['status'] == 'FAIL'
        mock_driver.screenshot.assert_called_once()
        assert result['screenshot_path'] is not None
        assert 'TC_FAIL' in result['screenshot_path']

    def test_no_screenshot_on_success(self, tmp_path):
        module_dir = _build_module(tmp_path)
        case_path = str(module_dir / "case" / "test.xml")
        config = _make_config(tmp_path, True)
        executor = SKIExecutor(case_path, _make_mock_driver(), config)

        case = {
            'case_id': 'TC_PASS',
            'title': '成功测试',
            'pre_process': [],
            'test_case': [{'action': 'wait', 'model': '', 'data': '0'}],
            'post_process': [],
        }

        result = executor.execute_case(case)
        assert result['status'] == 'PASS'

    def test_no_screenshot_when_disabled(self, tmp_path):
        module_dir = _build_module(tmp_path)
        case_path = str(module_dir / "case" / "test.xml")
        mock_driver = _make_mock_driver()
        mock_driver.wait.side_effect = RuntimeError("Element not found")
        config = _make_config(tmp_path, False)
        executor = SKIExecutor(case_path, mock_driver, config)

        case = {
            'case_id': 'TC_FAIL_NO_SS',
            'title': '失败但不截图',
            'pre_process': [],
            'test_case': [{'action': 'wait', 'model': '', 'data': '1'}],
            'post_process': [],
        }

        result = executor.execute_case(case)
        assert result['status'] == 'FAIL'
        mock_driver.screenshot.assert_not_called()


class TestAutoScreenshotIntegration:
    def test_full_flow_with_failure_screenshot(self, tmp_path):
        module_dir = _build_module(tmp_path)
        case_path = str(module_dir / "case" / "test.xml")
        mock_driver = _make_mock_driver()
        mock_driver.wait.side_effect = RuntimeError("Timeout waiting for element")
        config = _make_config(tmp_path, True)
        executor = SKIExecutor(case_path, mock_driver, config)
        # ensure run dir is initialized so screenshots can be saved
        executor.result_writer._init_run_dir()

        case = {
            'case_id': 'TC_INTEGRATION',
            'title': '集成测试',
            'pre_process': [],
            'test_case': [{'action': 'wait', 'model': '', 'data': '1'}],
            'post_process': [],
        }

        result = executor.execute_case(case)
        assert result['case_id'] == 'TC_INTEGRATION'
        assert result['status'] == 'FAIL'
        assert 'Timeout' in result['error']
        assert result['screenshot_path'] != ''

    def test_screenshot_failure_does_not_break_execution(self, tmp_path):
        module_dir = _build_module(tmp_path)
        case_path = str(module_dir / "case" / "test.xml")
        mock_driver = _make_mock_driver()
        mock_driver.screenshot.side_effect = Exception("Screenshot failed")
        mock_driver.wait.side_effect = RuntimeError("Test error")
        config = _make_config(tmp_path, True)
        executor = SKIExecutor(case_path, mock_driver, config)

        case = {
            'case_id': 'TC_SCREENSHOT_FAIL',
            'title': '截图失败测试',
            'pre_process': [],
            'test_case': [{'action': 'wait', 'model': '', 'data': '1'}],
            'post_process': [],
        }

        result = executor.execute_case(case)
        assert result['status'] == 'FAIL'
        assert result['screenshot_path'] == ''


class TestPostProcessAlwaysRuns:
    """用例阶段失败时后处理仍执行"""

    def test_close_runs_after_wait_fails_in_test_case(self, tmp_path):
        module_dir = _build_module(tmp_path)
        case_path = str(module_dir / "case" / "test.xml")
        mock_driver = _make_mock_driver()
        mock_driver.wait.side_effect = RuntimeError("用例阶段失败")
        config = _make_config(tmp_path, True)
        executor = SKIExecutor(case_path, mock_driver, config)

        case = {
            'case_id': 'TC_POST',
            'title': '后处理必跑',
            'pre_process': [],
            'test_case': [{'action': 'wait', 'model': '', 'data': '1'}],
            'post_process': [{'action': 'close', 'model': '', 'data': ''}],
        }

        result = executor.execute_case(case)
        assert result['status'] == 'FAIL'
        mock_driver.close.assert_called_once()
