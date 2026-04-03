"""BaseDriver 单元测试"""
from typing import Optional, Tuple
from drivers.base_driver import BaseDriver
from core.test_runner import assert_raises


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
        super().__init__()  # 初始化 BaseDriver，获取 config 和 logger
        self.actions = []
        # 智能等待测试支持
        self._locate_result_set = False  # 标记是否设置了 locate_result
        self._locate_result = None  # 单次返回结果
        self.locate_results = []  # 多次返回结果列表
        self.locate_call_count = 0  # 调用计数器

    @property
    def locate_result(self):
        return self._locate_result

    @locate_result.setter
    def locate_result(self, value):
        self._locate_result = value
        self._locate_result_set = True

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

        # 支持多次调用返回不同结果（用于智能等待测试）
        if self.locate_results:
            if self.locate_call_count < len(self.locate_results):
                result = self.locate_results[self.locate_call_count]
                self.locate_call_count += 1
                return result
            # 超出列表范围，返回最后一个结果
            return self.locate_results[-1]

        # 支持单次结果设置
        if self._locate_result_set:
            return self._locate_result

        # 默认行为
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

    def double_click(self, x: int, y: int) -> None:
        self.actions.append(("double_click", x, y))

    def right_click(self, x: int, y: int) -> None:
        self.actions.append(("right_click", x, y))

    def hover(self, x: int, y: int) -> None:
        self.actions.append(("hover", x, y))

    def scroll(self, x: int, y: int) -> None:
        self.actions.append(("scroll", x, y))


class TestBaseDriver:
    """测试 BaseDriver 基类"""

    def setup_method(self):
        """初始化测试环境"""
        self.driver = ConcreteDriver()

    def test_launch(self):
        self.driver.launch(url="https://example.com")
        assert ("launch", {"url": "https://example.com"}) in self.driver.actions

    def test_close(self):
        self.driver.close()
        assert ("close",) in self.driver.actions

    def test_locate_element(self):
        result = self.driver.locate_element("css", "#button")
        assert result == (10, 20, 110, 50)
        assert ("locate_element", "css", "#button") in self.driver.actions

    def test_locate_element_not_found(self):
        result = self.driver.locate_element("css", "not_found")
        assert result is None

    def test_click(self):
        self.driver.click(100, 200)
        assert ("click", 100, 200) in self.driver.actions

    def test_type_text(self):
        self.driver.type_text(100, 200, "hello")
        assert ("type_text", 100, 200, "hello") in self.driver.actions

    def test_get_text(self):
        result = self.driver.get_text(10, 20, 110, 50)
        assert result == "sample text"
        assert ("get_text", 10, 20, 110, 50) in self.driver.actions

    def test_take_screenshot(self):
        result = self.driver.take_screenshot()
        assert result == "/tmp/screenshot.png"
        assert ("take_screenshot",) in self.driver.actions

    def test_click_element(self):
        """测试便捷方法 click_element"""
        result = self.driver.click_element("css", "#button")
        assert result is True
        # 应该点击元素中心点 (60, 35)
        assert ("click", 60, 35) in self.driver.actions

    def test_click_element_not_found(self):
        """测试元素未找到时 click_element 返回 False"""
        result = self.driver.click_element("css", "not_found")
        assert result is False

    def test_type_at_element(self):
        """测试便捷方法 type_at_element"""
        result = self.driver.type_at_element("css", "#input", "test")
        assert result is True
        # 应该在元素中心点输入
        assert ("type_text", 60, 35, "test") in self.driver.actions

    def test_get_element_text(self):
        """测试便捷方法 get_element_text"""
        result = self.driver.get_element_text("css", "#title")
        assert result == "sample text"

    def test_get_element_text_not_found(self):
        """测试元素未找到时 get_element_text 返回 None"""
        result = self.driver.get_element_text("css", "not_found")
        assert result is None

    def test_wait(self):
        self.driver.wait(2.5)
        # wait 是 BaseDriver 提供的默认实现

    def test_get_element_center(self):
        """测试获取元素中心坐标"""
        result = self.driver.get_element_center("css", "#button")
        assert result == (60, 35)

    def test_get_element_center_not_found(self):
        """测试元素未找到时返回 None"""
        result = self.driver.get_element_center("css", "not_found")
        assert result is None

    def test_is_abstract(self):
        """验证 BaseDriver 不能直接实例化"""
        assert_raises(TypeError, BaseDriver)


class TestSmartWait:
    """测试智能等待机制"""

    def setup_method(self):
        """初始化测试环境"""
        self.driver = ConcreteDriver()

    def test_element_found_immediately(self):
        """测试元素立即找到"""
        # 设置元素立即找到
        self.driver.locate_result = (100, 200, 300, 400)

        bbox = self.driver.locate_element_with_retry("css", "#button")

        assert bbox == (100, 200, 300, 400)
        # 应该只调用一次 locate_element
        locate_calls = [a for a in self.driver.actions if a[0] == "locate_element"]
        assert len(locate_calls) == 1

    def test_element_found_after_retries(self):
        """测试重试后找到元素"""
        # 前两次返回 None，第三次返回坐标
        self.driver.locate_results = [None, None, (100, 200, 300, 400)]

        bbox = self.driver.locate_element_with_retry("css", "#button")

        assert bbox == (100, 200, 300, 400)
        # 应该调用 3 次 locate_element
        locate_calls = [a for a in self.driver.actions if a[0] == "locate_element"]
        assert len(locate_calls) == 3

    def test_element_not_found_after_max_retries(self):
        """测试达到最大重试次数后仍未找到"""
        # 设置超时时间为 1 秒，重试间隔 0.2 秒
        self.driver.config.set('element_wait_timeout', 1)
        self.driver.config.set('element_retry_interval', 0.2)

        # 始终返回 None
        self.driver.locate_result = None

        bbox = self.driver.locate_element_with_retry("css", "#not-exist")

        assert bbox is None
        # 应该有多次重试
        locate_calls = [a for a in self.driver.actions if a[0] == "locate_element"]
        assert len(locate_calls) >= 4  # 至少 1 次初始 + 3 次重试

    def test_smart_wait_disabled(self):
        """测试禁用智能等待（超时设为 0）"""
        # 设置超时为 0，相当于禁用智能等待
        self.driver.config.set('element_wait_timeout', 0)

        # 元素未找到
        self.driver.locate_result = None

        bbox = self.driver.locate_element_with_retry("css", "#button")

        assert bbox is None
        # 只应该调用一次（不重试）
        locate_calls = [a for a in self.driver.actions if a[0] == "locate_element"]
        assert len(locate_calls) == 1

    def test_custom_retry_config(self):
        """测试自定义重试配置"""
        import time

        # 设置较短的超时和重试间隔
        self.driver.config.set('element_wait_timeout', 0.5)
        self.driver.config.set('element_retry_interval', 0.1)

        # 始终返回 None
        self.driver.locate_result = None

        start_time = time.time()
        bbox = self.driver.locate_element_with_retry("css", "#button")
        elapsed = time.time() - start_time

        assert bbox is None
        # 总耗时应该接近 0.5 秒
        assert 0.4 <= elapsed <= 0.7
        # 应该有多次重试
        locate_calls = [a for a in self.driver.actions if a[0] == "locate_element"]
        assert len(locate_calls) >= 3

