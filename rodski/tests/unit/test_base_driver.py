"""BaseDriver 单元测试"""
import pytest
from typing import Optional, Tuple
from drivers.base_driver import BaseDriver


class ConcreteDriver(BaseDriver):
    """具体实现类用于测试

    实现新的 BaseDriver 接口：
    - launch: 启动应用
    - close: 关闭应用
    - locate_element: 定位元素返回坐标
    - click: 点击坐标
    - type_text: 在坐标输入文字
    - get_text: 获取区域文字
    - take_screenshot: 截图
    """

    def __init__(self):
        self.actions = []

    def launch(self, **kwargs) -> None:
        self.actions.append(("launch", kwargs))

    def close(self) -> None:
        self.actions.append(("close",))

    def locate_element(
        self,
        locator_type: str,
        locator_value: str
    ) -> Optional[Tuple[int, int, int, int]]:
        self.actions.append(("locate_element", locator_type, locator_value))
        # 返回模拟的边界框
        if locator_value == "not_found":
            return None
        return (10, 20, 110, 50)

    def click(self, x: int, y: int) -> None:
        self.actions.append(("click", x, y))

    def type_text(self, x: int, y: int, text: str) -> None:
        self.actions.append(("type_text", x, y, text))

    def get_text(self, x1: int, y1: int, x2: int, y2: int) -> str:
        self.actions.append(("get_text", x1, y1, x2, y2))
        return "sample text"

    def take_screenshot(self) -> str:
        self.actions.append(("take_screenshot",))
        return "/tmp/screenshot.png"


@pytest.fixture
def driver():
    return ConcreteDriver()


class TestBaseDriver:
    """测试 BaseDriver 基类"""

    def test_launch(self, driver):
        driver.launch(url="https://example.com")
        assert ("launch", {"url": "https://example.com"}) in driver.actions

    def test_close(self, driver):
        driver.close()
        assert ("close",) in driver.actions

    def test_locate_element(self, driver):
        result = driver.locate_element("css", "#button")
        assert result == (10, 20, 110, 50)
        assert ("locate_element", "css", "#button") in driver.actions

    def test_locate_element_not_found(self, driver):
        result = driver.locate_element("css", "not_found")
        assert result is None

    def test_click(self, driver):
        driver.click(100, 200)
        assert ("click", 100, 200) in driver.actions

    def test_type_text(self, driver):
        driver.type_text(100, 200, "hello")
        assert ("type_text", 100, 200, "hello") in driver.actions

    def test_get_text(self, driver):
        result = driver.get_text(10, 20, 110, 50)
        assert result == "sample text"
        assert ("get_text", 10, 20, 110, 50) in driver.actions

    def test_take_screenshot(self, driver):
        result = driver.take_screenshot()
        assert result == "/tmp/screenshot.png"
        assert ("take_screenshot",) in driver.actions

    def test_click_element(self, driver):
        """测试便捷方法 click_element"""
        result = driver.click_element("css", "#button")
        assert result is True
        # 应该点击元素中心点 (60, 35)
        assert ("click", 60, 35) in driver.actions

    def test_click_element_not_found(self, driver):
        """测试元素未找到时 click_element 返回 False"""
        result = driver.click_element("css", "not_found")
        assert result is False

    def test_type_at_element(self, driver):
        """测试便捷方法 type_at_element"""
        result = driver.type_at_element("css", "#input", "test")
        assert result is True
        # 应该在元素中心点输入
        assert ("type_text", 60, 35, "test") in driver.actions

    def test_get_element_text(self, driver):
        """测试便捷方法 get_element_text"""
        result = driver.get_element_text("css", "#title")
        assert result == "sample text"

    def test_get_element_text_not_found(self, driver):
        """测试元素未找到时 get_element_text 返回 None"""
        result = driver.get_element_text("css", "not_found")
        assert result is None

    def test_wait(self, driver):
        driver.wait(2.5)
        # wait 是 BaseDriver 提供的默认实现

    def test_get_element_center(self, driver):
        """测试获取元素中心坐标"""
        result = driver.get_element_center("css", "#button")
        assert result == (60, 35)

    def test_get_element_center_not_found(self, driver):
        """测试元素未找到时返回 None"""
        result = driver.get_element_center("css", "not_found")
        assert result is None

    def test_is_abstract(self):
        """验证 BaseDriver 不能直接实例化"""
        with pytest.raises(TypeError):
            BaseDriver()

