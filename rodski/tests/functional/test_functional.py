"""功能测试 - 使用示例 Excel 文件"""
import json
import pytest
import openpyxl
from pathlib import Path
from unittest.mock import MagicMock
from core.keyword_engine import KeywordEngine
from core.task_executor import TaskExecutor
from data.excel_parser import ExcelParser


def _mock_driver():
    driver = MagicMock()
    for method in ['click', 'type', 'check', 'navigate', 'screenshot',
                   'select', 'hover', 'drag', 'scroll']:
        getattr(driver, method).return_value = True
    driver.wait.return_value = None
    driver.assert_element = MagicMock(return_value=True)
    return driver


@pytest.fixture
def demo_xlsx(tmp_path):
    path = tmp_path / "demo_case.xlsx"
    wb = openpyxl.Workbook()

    ws1 = wb.active
    ws1.title = "登录测试"
    ws1.append(["keyword", "name", "locator", "text", "url"])
    ws1.append(["navigate", "打开登录页", None, None, "https://example.com/login"])
    ws1.append(["wait", "等待页面加载", None, None, None])
    ws1.append(["type", "输入用户名", "#username", "admin", None])
    ws1.append(["type", "输入密码", "#password", "password123", None])
    ws1.append(["wait", "等待跳转", None, None, None])
    ws1.append(["assert", "验证登录成功", "#welcome", None, None])
    ws1.append(["screenshot", "截图保存", None, None, None])

    ws2 = wb.create_sheet("搜索测试")
    ws2.append(["keyword", "name", "locator", "text", "url"])
    ws2.append(["navigate", "打开首页", None, None, "https://example.com"])
    ws2.append(["type", "输入搜索词", "#search", "RodSki", None])
    ws2.append(["wait", "等待加载", None, None, None])
    ws2.append(["assert", "验证结果", ".result:first", None, None])
    ws2.append(["wait", "等待加载", None, None, None])
    ws2.append(["assert", "验证排序", "#sort", None, None])
    ws2.append(["screenshot", "截图保存", None, None, None])

    wb.save(path)
    return str(path)


@pytest.fixture
def mock_driver():
    return _mock_driver()


class TestFunctionalLogin:
    def test_login_flow(self, demo_xlsx, mock_driver, tmp_path):
        parser = ExcelParser(demo_xlsx)
        errors = parser.validate()
        assert errors == []

        sheets = parser.get_sheet_names()
        assert "登录测试" in sheets

        raw = parser.parse("登录测试")
        assert len(raw) == 7

        engine = KeywordEngine(mock_driver)
        executor = TaskExecutor(engine)
        steps = executor.load_case(raw)
        assert len(steps) == 7

        success = executor.execute_steps(steps)
        assert success is True

        summary = executor.get_summary()
        assert summary["passed"] == 7
        assert summary["pass_rate"] == 100.0

        results_path = str(tmp_path / "login_results.json")
        executor.save_results(results_path)
        data = json.loads(Path(results_path).read_text())
        assert data["summary"]["total"] == 7

        parser.close()


class TestFunctionalSearch:
    def test_search_flow(self, demo_xlsx, mock_driver):
        parser = ExcelParser(demo_xlsx)
        raw = parser.parse("搜索测试")
        assert len(raw) == 7

        engine = KeywordEngine(mock_driver)
        executor = TaskExecutor(engine)
        steps = executor.load_case(raw)

        success = executor.execute_steps(steps)
        assert success is True
        assert executor.get_summary()["passed"] == 7

        parser.close()


class TestFunctionalMultiSheet:
    def test_all_sheets(self, demo_xlsx, tmp_path):
        parser = ExcelParser(demo_xlsx)
        sheets = parser.get_sheet_names()
        assert len(sheets) == 2

        total_steps = 0
        total_passed = 0

        for sheet in sheets:
            raw = parser.parse(sheet)
            driver = _mock_driver()
            engine = KeywordEngine(driver)
            executor = TaskExecutor(engine)
            steps = executor.load_case(raw)
            executor.execute_steps(steps)
            s = executor.get_summary()
            total_steps += s["total"]
            total_passed += s["passed"]

        assert total_steps == 14
        assert total_passed == 14

        parser.close()
