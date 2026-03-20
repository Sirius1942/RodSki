"""BaseDriver 单元测试"""
import pytest
from drivers.base_driver import BaseDriver


class ConcreteDriver(BaseDriver):
    """具体实现类用于测试"""

    def __init__(self):
        self.actions = []

    def click(self, locator: str, **kwargs) -> bool:
        self.actions.append(("click", locator))
        return True

    def type(self, locator: str, text: str, **kwargs) -> bool:
        self.actions.append(("type", locator, text))
        return True

    def check(self, locator: str, **kwargs) -> bool:
        self.actions.append(("check", locator))
        return True

    def wait(self, seconds: float) -> None:
        self.actions.append(("wait", seconds))

    def navigate(self, url: str) -> bool:
        self.actions.append(("navigate", url))
        return True

    def screenshot(self, path: str) -> bool:
        self.actions.append(("screenshot", path))
        return True

    def select(self, locator: str, value: str) -> bool:
        self.actions.append(("select", locator, value))
        return True

    def hover(self, locator: str) -> bool:
        self.actions.append(("hover", locator))
        return True

    def drag(self, from_loc: str, to_loc: str) -> bool:
        self.actions.append(("drag", from_loc, to_loc))
        return True

    def scroll(self, x: int = 0, y: int = 300) -> bool:
        self.actions.append(("scroll", x, y))
        return True

    def assert_element(self, locator: str, expected: str) -> bool:
        self.actions.append(("assert_element", locator, expected))
        return True

    def close(self) -> None:
        self.actions.append(("close",))


@pytest.fixture
def driver():
    return ConcreteDriver()


class TestBaseDriver:
    """测试 BaseDriver 基类"""

    def test_click(self, driver):
        result = driver.click("#button")
        assert result is True
        assert ("click", "#button") in driver.actions

    def test_type(self, driver):
        result = driver.type("#input", "test text")
        assert result is True
        assert ("type", "#input", "test text") in driver.actions

    def test_check(self, driver):
        result = driver.check("#checkbox")
        assert result is True
        assert ("check", "#checkbox") in driver.actions

    def test_wait(self, driver):
        driver.wait(2.5)
        assert ("wait", 2.5) in driver.actions

    def test_navigate(self, driver):
        result = driver.navigate("https://example.com")
        assert result is True
        assert ("navigate", "https://example.com") in driver.actions

    def test_screenshot(self, driver):
        result = driver.screenshot("/tmp/test.png")
        assert result is True
        assert ("screenshot", "/tmp/test.png") in driver.actions

    def test_select(self, driver):
        result = driver.select("#dropdown", "option1")
        assert result is True
        assert ("select", "#dropdown", "option1") in driver.actions

    def test_hover(self, driver):
        result = driver.hover("#menu")
        assert result is True
        assert ("hover", "#menu") in driver.actions

    def test_drag(self, driver):
        result = driver.drag("#source", "#target")
        assert result is True
        assert ("drag", "#source", "#target") in driver.actions

    def test_scroll(self, driver):
        result = driver.scroll(100, 500)
        assert result is True
        assert ("scroll", 100, 500) in driver.actions

    def test_scroll_default_params(self, driver):
        result = driver.scroll()
        assert result is True
        assert ("scroll", 0, 300) in driver.actions

    def test_assert_element(self, driver):
        result = driver.assert_element("#title", "Welcome")
        assert result is True
        assert ("assert_element", "#title", "Welcome") in driver.actions

    def test_close(self, driver):
        driver.close()
        assert ("close",) in driver.actions

    def test_upload_file(self, driver):
        result = driver.upload_file("#file-input", "/tmp/file.pdf")
        assert result is True

    def test_clear(self, driver):
        result = driver.clear("#input")
        assert result is True

    def test_double_click(self, driver):
        result = driver.double_click("#item")
        assert result is True

    def test_right_click(self, driver):
        result = driver.right_click("#context-menu")
        assert result is True

    def test_key_press(self, driver):
        result = driver.key_press("Enter")
        assert result is True

    def test_get_text(self, driver):
        result = driver.get_text("#title")
        assert result == ""

    def test_is_abstract(self):
        """验证 BaseDriver 不能直接实例化"""
        with pytest.raises(TypeError):
            BaseDriver()

