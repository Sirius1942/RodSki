"""端到端集成测试 - 不依赖真实浏览器"""
import json
import pytest
from unittest.mock import MagicMock
from core.keyword_engine import KeywordEngine
from core.task_executor import TaskExecutor
from core.config_manager import ConfigManager
from core.logger import Logger
from data.data_resolver import DataResolver
from data.model_manager import ModelManager
from data.excel_parser import ExcelParser
import openpyxl


def _mock_driver():
    driver = MagicMock()
    driver.click.return_value = True
    driver.type.return_value = True
    driver.check.return_value = True
    driver.wait.return_value = None
    driver.navigate.return_value = True
    driver.screenshot.return_value = True
    driver.select.return_value = True
    driver.hover.return_value = True
    driver.drag.return_value = True
    driver.scroll.return_value = True
    driver.assert_element = MagicMock(return_value=True)
    return driver


@pytest.fixture
def mock_driver():
    return _mock_driver()


@pytest.fixture
def sample_xlsx(tmp_path):
    path = tmp_path / "case.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "TestCase"
    ws.append(["keyword", "name", "locator", "text", "url"])
    ws.append(["navigate", "Open page", None, None, "https://example.com"])
    ws.append(["click", "Click login", "#login-btn", None, None])
    ws.append(["type", "Enter user", "#user", "admin", None])
    ws.append(["type", "Enter pass", "#pass", "123456", None])
    ws.append(["click", "Submit", "#submit", None, None])
    ws.append(["wait", "Wait load", None, None, None])
    ws.append(["assert", "Verify page", "#dashboard", None, None])
    wb.save(path)
    return str(path)


class TestEndToEnd:
    def test_full_flow_with_mock_driver(self, mock_driver, sample_xlsx, tmp_path):
        parser = ExcelParser(sample_xlsx)
        raw_data = parser.parse()
        assert len(raw_data) == 7

        engine = KeywordEngine(mock_driver)
        executor = TaskExecutor(engine)
        steps = executor.load_case(raw_data)
        assert len(steps) == 7

        success = executor.execute_steps(steps)
        assert success is True

        summary = executor.get_summary()
        assert summary["total"] == 7
        assert summary["passed"] == 7
        assert summary["failed"] == 0

        results_path = str(tmp_path / "results.json")
        executor.save_results(results_path)
        data = json.loads(open(results_path).read())
        assert data["summary"]["pass_rate"] == 100.0

        parser.close()

    def test_flow_with_data_resolver(self, mock_driver):
        resolver = DataResolver({"username": "admin", "password": "secret"})
        steps = [
            {"keyword": "type", "params": {"locator": "#user", "text": "${username}"}, "name": "S1"},
            {"keyword": "type", "params": {"locator": "#pass", "text": "${password}"}, "name": "S2"},
        ]

        engine = KeywordEngine(mock_driver)
        executor = TaskExecutor(engine)

        resolved_steps = []
        for step in steps:
            resolved = dict(step)
            resolved["params"] = resolver.resolve_params(step["params"])
            resolved_steps.append(resolved)

        success = executor.execute_steps(resolved_steps)
        assert success is True

        mock_driver.type.assert_any_call("#user", "admin")
        mock_driver.type.assert_any_call("#pass", "secret")

    def test_flow_with_model_manager(self, mock_driver):
        mm = ModelManager()
        mm.register("login", {
            "name": "login",
            "type": "page",
            "elements": {"btn": "#login-btn", "user": "#user-input"}
        })

        resolver = DataResolver(model_manager=mm)
        locator = resolver.resolve("@{login.btn}")
        assert locator == "#login-btn"

        engine = KeywordEngine(mock_driver)
        engine.execute("click", {"locator": locator})
        mock_driver.click.assert_called_with("#login-btn")

    def test_config_driven_execution(self, tmp_path):
        cfg = ConfigManager(config_path=str(tmp_path / "config.json"))
        cfg.set("driver", "web")
        cfg.set("retry", 2)
        cfg.save()

        cfg2 = ConfigManager(config_path=str(tmp_path / "config.json"))
        assert cfg2.get("driver") == "web"
        assert cfg2.get("retry") == 2

    def test_logger_integration(self, tmp_path):
        log_dir = str(tmp_path / "logs")
        logger = Logger(name="test_e2e", log_dir=log_dir, console=False)
        logger.info("Test message")
        logger.error("Error message")

        files = logger.get_log_files()
        assert len(files) == 1

        content = logger.get_latest_log()
        assert "Test message" in content
        assert "Error message" in content

    def test_partial_failure_flow(self, tmp_path):
        driver = _mock_driver()
        # click is called: S1(attempt1)=True, S3(attempt1)=False, S3(attempt2)=False
        driver.click.side_effect = [True, False, False]
        driver.type.return_value = True

        engine = KeywordEngine(driver)
        executor = TaskExecutor(engine, max_retries=1)

        steps = [
            {"keyword": "click", "params": {"locator": "#a"}, "name": "S1"},
            {"keyword": "type", "params": {"locator": "#b", "text": "hi"}, "name": "S2"},
            {"keyword": "click", "params": {"locator": "#c"}, "name": "S3"},
        ]
        success = executor.execute_steps(steps)
        assert success is False

        summary = executor.get_summary()
        assert summary["passed"] == 2
        assert summary["failed"] == 1
