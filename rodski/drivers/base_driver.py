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
import time
import logging
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

    def __init__(self):
        """初始化驱动基类"""
        from rodski.core.config_manager import ConfigManager
        from rodski.core.logger import Logger

        self.config = ConfigManager()
        self.logger = Logger(name=self.__class__.__name__)

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
    def click(self, x: int, y: int) -> None:
        """点击指定坐标

        Args:
            x: x 坐标
            y: y 坐标

        Raises:
            DriverError: 点击失败时抛出
        """
        pass

    @abstractmethod
    def type_text(self, x: int, y: int, text: str) -> None:
        """在指定坐标输入文字

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
    def get_text(self, x1: int, y1: int, x2: int, y2: int) -> str:
        """获取指定区域的文字

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

    def current_url(self) -> Optional[str]:
        """返回当前页面 URL（仅 Web 驱动有意义）。

        默认实现返回 None，PlaywrightDriver 覆盖此方法。
        其他驱动（Appium、Desktop、Load）继承默认实现即可。
        """
        return None

    @abstractmethod
    def double_click(self, x: int, y: int) -> None:
        """双击指定坐标

        Args:
            x: x 坐标
            y: y 坐标

        Raises:
            DriverError: 双击失败时抛出
        """
        pass

    @abstractmethod
    def right_click(self, x: int, y: int) -> None:
        """右键点击指定坐标

        Args:
            x: x 坐标
            y: y 坐标

        Raises:
            DriverError: 右键点击失败时抛出
        """
        pass

    @abstractmethod
    def hover(self, x: int, y: int) -> None:
        """悬停在指定坐标

        Args:
            x: x 坐标
            y: y 坐标

        Raises:
            DriverError: 悬停失败时抛出
        """
        pass

    @abstractmethod
    def scroll(self, x: int, y: int) -> None:
        """滚动指定距离

        Args:
            x: 水平滚动距离（正值向右，负值向左）
            y: 垂直滚动距离（正值向下，负值向上）

        Raises:
            DriverError: 滚动失败时抛出
        """
        pass

    # ── v11.7.0 自动等待（AutoWait）驱动契约 ─────────────────────────────
    #
    # 设计文档: .pb/specs/v11.7.0-autowait-unified-design.md §3.1/§3.2
    # 驱动契约: .pb/iterations/iteration-65/driver-contract.md
    #
    # 轮询与 deadline 由公共层（rodski/core/auto_wait.py + KeywordEngine）掌握；驱动只提供：
    #   1. set_auto_wait(ms)            —— 接收 DefaultValue.AutoWait（毫秒），仅作兜底默认值
    #   2. probe(locator, frame=None)   —— 即时探测：元素当前是否存在，**不等待**
    #   3. 动作方法的 timeout_ms 可选参数 —— 可操作性等待只能用这个剩余预算
    # 驱动内部不得再有自己的等待/重试（WebDriverWait(10)、wait_for_selector 吞异常、
    # force/JS 降级、implicit wait 等），否则会与公共层轮询叠加。

    #: 未收到 set_auto_wait 时的 AutoWait（毫秒）：0 = 不自动等待，与 core.auto_wait.DEFAULT_AUTO_WAIT_MS 一致
    DEFAULT_AUTO_WAIT_MS = 0

    def set_auto_wait(self, ms: float) -> None:
        """接收 ``DefaultValue.AutoWait``（毫秒，0 = 不等待）。

        KeywordEngine 在每次 ``execute()`` 前、以及懒创建驱动时调用。驱动用它作为
        **调用方没有传 timeout_ms 时**的动作超时兜底（例如外部代码直接调用
        ``click_locator(loc)``）。关键字层的调用总会显式传 ``timeout_ms``。

        注意：Playwright 的 ``timeout=0`` 表示无限等待，驱动换算时必须保证下限 1ms。
        """
        try:
            value = float(ms)
        except (TypeError, ValueError):
            value = float(self.DEFAULT_AUTO_WAIT_MS)
        self._auto_wait_ms = max(0.0, value)

    def get_auto_wait(self) -> float:
        """返回当前 AutoWait（毫秒）；未下发时为 DEFAULT_AUTO_WAIT_MS。"""
        return getattr(self, "_auto_wait_ms", float(self.DEFAULT_AUTO_WAIT_MS))

    def _action_timeout_ms(self, timeout_ms: Optional[float] = None) -> int:
        """动作超时（毫秒，整数，下限 1ms，永不为 0）：优先调用方给的 timeout_ms，否则 AutoWait。"""
        value = self.get_auto_wait() if timeout_ms is None else timeout_ms
        try:
            value = float(value)
        except (TypeError, ValueError):
            value = float(self.DEFAULT_AUTO_WAIT_MS)
        # 下限与 core.auto_wait.MIN_ACTION_TIMEOUT_MS 一致（500ms）：永不为 0，且足够完成一次真实动作
        return max(500, int(value))

    @staticmethod
    def split_locator(locator: str) -> Tuple[str, str]:
        """把 ``"type=value"`` 拆成 (type, value)。

        无已知前缀时（如 ``"#id"`` / ``".cls"`` / ``"//div"``）按 css / xpath 处理。
        """
        text = str(locator or "")
        if "=" in text:
            head, value = text.split("=", 1)
            if head and head.replace("_", "").isalnum():
                return head.strip().lower(), value
        if text.startswith("//") or text.startswith("(/"):
            return "xpath", text
        return "css", text

    def probe(self, locator: str, frame: Optional[str] = None) -> bool:
        """即时探测元素当前是否存在（**不等待**）。

        Args:
            locator: ``"type=value"`` 定位器（与 click_locator/type_locator 同格式），
                如 ``"id=loginBtn"``、``"css=.row"``、``"xpath=//a"``、``"ocr=登录"``；
                兼容裸 ``"#id"`` / ``".cls"`` / ``"//xpath"``。
            frame: v11.6.0 location@frame（仅 Web 有意义）。

        Returns:
            True = 元素已存在（进入可操作阶段）；False = 暂未出现（公共层稍后再探测）。

        Raises:
            NotImplementedError: 驱动不支持该定位器类型（公共层跳过该定位器）。
            PerceptionUnavailableError / DriverStoppedError: 立即失败，不重试。

        语义要求（驱动覆盖时必须满足）：
            - 耗时应接近一次查询（Web ``locator.count()``、Appium ``find_elements``），
              绝不能内部等待 / 重试 / implicit wait；
            - "存在"即可（attached），可见 / 可用 / 未遮挡属于可操作阶段，由带 timeout_ms 的动作负责；
            - 视觉定位器（vision/ocr/vision_bbox）每次调用必须用**新截图**（绕过截图缓存）。

        默认实现（坐标型驱动）：``locate_element(type, value) is not None``；带 frame 时无法通用判断，
            返回 True，交给带 timeout 的动作决定。异常不在这里吞掉：由公共层按白名单处理。
        """
        if frame:
            return True
        locator_type, locator_value = self.split_locator(locator)
        return self.locate_element(locator_type, locator_value) is not None

    def get_text_locator(self, locator: str, frame: Optional[str] = None,
                         timeout_ms: Optional[float] = None) -> Optional[str]:
        """读取元素文本（通过定位器）。

        默认实现（坐标型驱动，如桌面 vision/ocr）：``locate_element`` → ``get_text(bbox)``；
        元素不存在返回 None。Web / 移动端驱动应覆盖（timeout_ms 为可读取等待的剩余预算）。
        """
        locator_type, locator_value = self.split_locator(locator)
        bbox = self.locate_element(locator_type, locator_value)
        if bbox is None:
            return None
        return self.get_text(bbox[0], bbox[1], bbox[2], bbox[3])

    # ── 扩展方法（非抽象，子类可选覆盖）───────────────────────────────

    def locate_element_with_retry(
        self,
        locator_type: str,
        locator_value: str
    ) -> Optional[Tuple[int, int, int, int]]:
        """按 AutoWait（自动等待）定位元素（v11.7.0 起不再读取 element_wait_timeout / smart_wait_*）

        try 定位 → 未找到则等待 → 再定位；找到即返回，超过 AutoWait 返回 None。
        轮询由公共层 core.auto_wait.run_element 负责，与关键字层同一套语义。

        Returns:
            (x1, y1, x2, y2) 边界框坐标，AutoWait 内未找到返回 None
        """
        try:
            from ..core import auto_wait as _aw
        except ImportError:  # pragma: no cover - 以 rodski/ 为根运行
            from core import auto_wait as _aw
        locator = f"{locator_type}={locator_value}"
        try:
            _, bbox = _aw.run_element(
                locator, [locator],
                probe=lambda _l: self.locate_element(locator_type, locator_value),
                act=lambda _l, hit, _d: hit,
                deadline=_aw.Deadline(self.get_auto_wait()),
                interval_s=_aw.poll_interval_for([locator_type]),
            )
            return bbox
        except _aw.ElementWaitTimeoutError as e:
            logging.getLogger("rodski").warning(str(getattr(e, "message", e)))
            return None

    def click_element(self, locator_type: str, locator_value: str) -> bool:
        """定位并点击元素（便捷方法）

        Args:
            locator_type: 定位器类型
            locator_value: 定位器值

        Returns:
            成功返回 True，未找到元素返回 False
        """
        bbox = self.locate_element_with_retry(locator_type, locator_value)
        if bbox is None:
            return False
        center_x = (bbox[0] + bbox[2]) // 2
        center_y = (bbox[1] + bbox[3]) // 2
        self.click(center_x, center_y)
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
        bbox = self.locate_element_with_retry(locator_type, locator_value)
        if bbox is None:
            return False
        center_x = (bbox[0] + bbox[2]) // 2
        center_y = (bbox[1] + bbox[3]) // 2
        self.type_text(center_x, center_y, text)
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
        bbox = self.locate_element_with_retry(locator_type, locator_value)
        if bbox is None:
            return None
        return self.get_text(bbox[0], bbox[1], bbox[2], bbox[3])

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
        bbox = self.locate_element_with_retry(locator_type, locator_value)
        if bbox is None:
            return None
        return ((bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2)