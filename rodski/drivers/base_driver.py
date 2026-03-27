"""RodSki 驱动基类接口

BaseDriver 定义统一的驱动接口，支持：
- Web 自动化 (Playwright)
- 桌面自动化 (Pywinauto)
- 移动端自动化 (Appium)
- 视觉定位自动化

设计原则：
- 两阶段操作：先定位元素获取坐标，再操作坐标
- 统一接口：不同平台/驱动实现相同接口
- 支持视觉定位：通过 locate_element 返回坐标，便于视觉定位集成
"""
from abc import ABC, abstractmethod
from typing import Tuple, Optional, Any


class BaseDriver(ABC):
    """驱动基类，定义统一接口

    所有驱动实现必须继承此类并实现所有抽象方法。

    坐标系统：
    - 坐标原点为屏幕/窗口左上角
    - x 向右递增，y 向下递增
    - 边界框格式：(x1, y1, x2, y2)，其中 (x1, y1) 为左上角，(x2, y2) 为右下角
    """

    @abstractmethod
    def launch(self, **kwargs) -> None:
        """启动应用或打开页面

        Args:
            **kwargs: 平台特定参数
                - Web: url=str (目标网址)
                - Desktop: app_path=str (应用路径)
                - Mobile: app_id=str, activity=str (应用标识)

        Raises:
            DriverError: 启动失败时抛出
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """关闭应用或浏览器

        清理资源，关闭窗口/应用。
        """
        pass

    @abstractmethod
    def locate_element(
        self,
        locator_type: str,
        locator_value: str
    ) -> Optional[Tuple[int, int, int, int]]:
        """定位元素，返回边界框坐标

        Args:
            locator_type: 定位器类型，支持：
                - 'id': 元素 ID
                - 'css': CSS 选择器
                - 'xpath': XPath 表达式
                - 'text': 文本内容
                - 'vision': 视觉定位（图像匹配）
                - 'ocr': OCR 文字定位
                - 'vision_bbox': 视觉边界框
                - 其他平台特定类型
            locator_value: 定位器值

        Returns:
            (x1, y1, x2, y2) 边界框坐标，未找到返回 None

        Example:
            >>> bbox = driver.locate_element('css', '#submit-btn')
            >>> if bbox:
            ...     center_x = (bbox[0] + bbox[2]) // 2
            ...     center_y = (bbox[1] + bbox[3]) // 2
        """
        pass

    @abstractmethod
    def click_at(self, x: int, y: int) -> None:
        """点击指定坐标（视觉定位专用）

        Args:
            x: x 坐标
            y: y 坐标

        Raises:
            DriverError: 点击失败时抛出
        """
        pass

    @abstractmethod
    def type_text_at(self, x: int, y: int, text: str) -> None:
        """在指定坐标输入文字（视觉定位专用）

        先点击坐标位置获取焦点，然后输入文字。

        Args:
            x: x 坐标
            y: y 坐标
            text: 要输入的文字

        Raises:
            DriverError: 输入失败时抛出
        """
        pass

    @abstractmethod
    def get_text_in_bbox(self, x1: int, y1: int, x2: int, y2: int) -> str:
        """获取指定区域的文字（视觉定位专用）

        Args:
            x1: 左上角 x 坐标
            y1: 左上角 y 坐标
            x2: 右下角 x 坐标
            y2: 右下角 y 坐标

        Returns:
            区域内的文字内容，未找到返回空字符串

        Raises:
            DriverError: 获取失败时抛出
        """
        pass

    @abstractmethod
    def take_screenshot(self) -> str:
        """截图，返回截图路径

        Returns:
            截图文件的绝对路径

        Raises:
            DriverError: 截图失败时抛出
        """
        pass

    # ── 扩展方法（非抽象，子类可选覆盖）───────────────────────────────

    def click_element(self, locator_type: str, locator_value: str) -> bool:
        """定位并点击元素（便捷方法）

        Args:
            locator_type: 定位器类型
            locator_value: 定位器值

        Returns:
            成功返回 True，未找到元素返回 False
        """
        bbox = self.locate_element(locator_type, locator_value)
        if bbox is None:
            return False
        center_x = (bbox[0] + bbox[2]) // 2
        center_y = (bbox[1] + bbox[3]) // 2
        self.click_at(center_x, center_y)
        return True

    def type_at_element(
        self,
        locator_type: str,
        locator_value: str,
        text: str
    ) -> bool:
        """定位并在元素位置输入文字（便捷方法）

        Args:
            locator_type: 定位器类型
            locator_value: 定位器值
            text: 要输入的文字

        Returns:
            成功返回 True，未找到元素返回 False
        """
        bbox = self.locate_element(locator_type, locator_value)
        if bbox is None:
            return False
        center_x = (bbox[0] + bbox[2]) // 2
        center_y = (bbox[1] + bbox[3]) // 2
        self.type_text_at(center_x, center_y, text)
        return True

    def get_element_text(
        self,
        locator_type: str,
        locator_value: str
    ) -> Optional[str]:
        """定位并获取元素文字（便捷方法）

        Args:
            locator_type: 定位器类型
            locator_value: 定位器值

        Returns:
            元素文字内容，未找到返回 None
        """
        bbox = self.locate_element(locator_type, locator_value)
        if bbox is None:
            return None
        return self.get_text_in_bbox(bbox[0], bbox[1], bbox[2], bbox[3])

    def wait(self, seconds: float) -> None:
        """等待指定秒数

        Args:
            seconds: 等待秒数
        """
        import time
        time.sleep(seconds)

    def get_viewport_size(self) -> Tuple[int, int]:
        """获取视口/窗口大小

        Returns:
            (width, height) 视口宽高

        Raises:
            NotImplementedError: 子类未实现时抛出
        """
        raise NotImplementedError("子类应实现 get_viewport_size 方法")

    def get_element_center(
        self,
        locator_type: str,
        locator_value: str
    ) -> Optional[Tuple[int, int]]:
        """获取元素中心坐标

        Args:
            locator_type: 定位器类型
            locator_value: 定位器值

        Returns:
            (x, y) 中心坐标，未找到返回 None
        """
        bbox = self.locate_element(locator_type, locator_value)
        if bbox is None:
            return None
        return ((bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2)