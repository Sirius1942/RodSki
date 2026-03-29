"""Desktop 驱动 - 支持 Windows 和 macOS 的桌面自动化

特性:
- 使用 pyautogui 实现跨平台截图、点击、输入
- 支持视觉定位器 (vision/ocr/vision_bbox)
- 支持启动和关闭桌面应用
- 自动检测当前平台
"""
from __future__ import annotations

import logging
import os
import platform
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional, Tuple, Any

from .base_driver import BaseDriver
from core.exceptions import (
    DriverError,
    DriverStoppedError,
    ElementNotFoundError,
)

logger = logging.getLogger("rodski")


class DesktopDriver(BaseDriver):
    """Desktop 驱动 - 支持 Windows 和 macOS

    使用 pyautogui 实现跨平台桌面自动化。

    坐标系统:
    - 坐标原点为屏幕左上角
    - x 向右递增，y 向下递增
    - 边界框格式: (x1, y1, x2, y2)
    """

    # 支持的定位器类型
    SUPPORTED_LOCATORS = {'vision', 'ocr', 'vision_bbox'}

    def __init__(self, target_platform: str = None):
        """初始化 Desktop 驱动

        Args:
            target_platform: 目标平台 ("windows" 或 "macos")，默认自动检测

        Raises:
            DriverError: 不支持的平台
        """
        self.platform = target_platform or self._detect_platform()
        self._app_process: Optional[subprocess.Popen] = None
        self._screenshot_cache: Optional[str] = None
        self._screenshot_cache_time: float = 0
        self._is_closed = False
        self._pyautogui = None
        self._vision_provider = None  # 视觉定位器，延迟加载

        # 截图缓存有效期（秒）
        self._screenshot_cache_ttl = 0.5

        logger.info(f"DesktopDriver 初始化完成，平台: {self.platform}")

    def _detect_platform(self) -> str:
        """检测当前平台"""
        system = platform.system().lower()
        if system == "windows":
            return "windows"
        elif system == "darwin":
            return "macos"
        else:
            raise DriverError(
                f"不支持的平台: {system}，DesktopDriver 仅支持 Windows 和 macOS"
            )

    def _get_pyautogui(self):
        """延迟加载 pyautogui"""
        if self._pyautogui is None:
            try:
                import pyautogui
                self._pyautogui = pyautogui
                # 设置安全措施
                pyautogui.FAILSAFE = True
                pyautogui.PAUSE = 0.1
            except ImportError:
                raise DriverError(
                    "pyautogui 未安装，请运行: pip install pyautogui",
                    cause=ImportError("pyautogui not installed")
                )
        return self._pyautogui

    def _check_driver_alive(self) -> None:
        """检查驱动是否存活"""
        if self._is_closed:
            raise DriverStoppedError(
                "Desktop 驱动已关闭",
                driver_type="Desktop"
            )

    def _invalidate_screenshot_cache(self) -> None:
        """使截图缓存失效"""
        self._screenshot_cache = None
        self._screenshot_cache_time = 0

    # ── BaseDriver 抽象方法实现 ─────────────────────────────────────────────

    def launch(self, **kwargs) -> None:
        """启动应用

        Args:
            app_path: 应用路径 (如 "C:\\Apps\\Notepad.exe")
            app_name: 应用名称 (macOS 使用，如 "TextEdit")
            **kwargs: 其他平台特定参数

        Raises:
            DriverError: 启动失败
        """
        self._check_driver_alive()

        app_path = kwargs.get('app_path')
        app_name = kwargs.get('app_name')

        if not app_path and not app_name:
            raise DriverError("必须提供 app_path 或 app_name 参数")

        try:
            if self.platform == "windows":
                self._launch_windows(app_path)
            elif self.platform == "macos":
                self._launch_macos(app_path, app_name)

            # 等待应用启动
            time.sleep(1.0)
            logger.info(f"应用启动成功: {app_path or app_name}")

        except Exception as e:
            raise DriverError(
                f"启动应用失败: {app_path or app_name}",
                cause=e
            )

    def _launch_windows(self, app_path: str) -> None:
        """Windows 平台启动应用"""
        if not app_path:
            raise DriverError("Windows 平台需要提供 app_path 参数")

        # 检查路径是否存在
        if not os.path.exists(app_path):
            raise DriverError(f"应用路径不存在: {app_path}")

        self._app_process = subprocess.Popen(
            [app_path],
            shell=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    def _launch_macos(self, app_path: str, app_name: str) -> None:
        """macOS 平台启动应用"""
        if app_path:
            # 使用应用路径
            if not os.path.exists(app_path):
                raise DriverError(f"应用路径不存在: {app_path}")
            self._app_process = subprocess.Popen(
                ['open', app_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        elif app_name:
            # 使用应用名称
            self._app_process = subprocess.Popen(
                ['open', '-a', app_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

    def close(self) -> None:
        """关闭应用和驱动"""
        if self._is_closed:
            return

        self._is_closed = True

        # 关闭启动的应用进程
        if self._app_process:
            try:
                self._app_process.terminate()
                self._app_process.wait(timeout=5)
            except Exception as e:
                logger.debug(f"关闭应用进程时出错: {e}")
                try:
                    self._app_process.kill()
                except Exception:
                    pass
            self._app_process = None

        # 清理截图缓存
        self._invalidate_screenshot_cache()
        logger.info("DesktopDriver 已关闭")

    def take_screenshot(self, path: str) -> None:
        """截图到指定路径

        Args:
            path: 截图保存路径

        Raises:
            DriverError: 截图失败
        """
        self._check_driver_alive()

        pyautogui = self._get_pyautogui()

        try:
            # 截图并保存到指定路径
            screenshot = pyautogui.screenshot()
            screenshot.save(path)

            # 更新缓存
            self._screenshot_cache = path
            self._screenshot_cache_time = time.time()

            logger.debug(f"截图成功: {path}")

        except Exception as e:
            raise DriverError(f"截图失败: {e}", cause=e)

    def locate_element(
        self,
        locator_type: str,
        locator_value: str
    ) -> Optional[Tuple[int, int, int, int]]:
        """定位元素（仅支持视觉定位器）

        Args:
            locator_type: 定位器类型
                - 'vision': 图像匹配
                - 'ocr': OCR 文字定位
                - 'vision_bbox': 视觉边界框
            locator_value: 定位器值

        Returns:
            (x1, y1, x2, y2) 边界框坐标，未找到返回 None

        Raises:
            DriverError: 不支持的定位器类型
        """
        self._check_driver_alive()

        # 验证定位器类型
        if locator_type not in self.SUPPORTED_LOCATORS:
            raise DriverError(
                f"DesktopDriver 不支持定位器类型: {locator_type}，"
                f"支持的类型: {', '.join(self.SUPPORTED_LOCATORS)}"
            )

        # 获取最新截图
        screenshot_path = self._get_fresh_screenshot()

        # 委托给视觉定位器处理
        if self._vision_provider is None:
            self._init_vision_provider()

        try:
            bbox = self._vision_provider.locate(
                locator_type,
                locator_value,
                screenshot_path
            )
            return bbox
        except Exception as e:
            logger.warning(f"元素定位失败: {locator_type}={locator_value}, 错误: {e}")
            return None

    def _get_fresh_screenshot(self) -> str:
        """获取有效的截图路径

        如果缓存有效则返回缓存，否则重新截图。
        """
        current_time = time.time()
        cache_valid = (
            self._screenshot_cache and
            (current_time - self._screenshot_cache_time) < self._screenshot_cache_ttl and
            os.path.exists(self._screenshot_cache)
        )

        if cache_valid:
            return self._screenshot_cache
        return self.take_screenshot()

    def _init_vision_provider(self) -> None:
        """初始化视觉定位器

        注意: 这是占位实现，实际视觉定位器将在后续任务中实现。
        当前版本抛出 DriverError 提示用户。
        """
        # 尝试导入视觉定位器
        try:
            from rodski.vision.locator import VisionLocator
            self._vision_provider = VisionLocator()
        except ImportError:
            # 视觉定位器未实现，使用占位实现
            self._vision_provider = _PlaceholderVisionProvider()
            logger.warning(
                "视觉定位器未安装，视觉定位功能不可用。"
                "请等待 RodSki 视觉定位模块发布。"
            )

    def click_at(self, x: int, y: int) -> None:
        """点击指定坐标（视觉定位专用）

        Args:
            x: x 坐标
            y: y 坐标

        Raises:
            DriverError: 点击失败
        """
        self._check_driver_alive()

        pyautogui = self._get_pyautogui()

        try:
            pyautogui.click(x, y)
            logger.debug(f"点击坐标: ({x}, {y})")
        except Exception as e:
            raise DriverError(f"点击失败: ({x}, {y})", cause=e)

    def type_text_at(self, x: int, y: int, text: str) -> None:
        """在指定坐标输入文字（视觉定位专用）

        先点击坐标位置获取焦点，然后输入文字。

        Args:
            x: x 坐标
            y: y 坐标
            text: 要输入的文字

        Raises:
            DriverError: 输入失败
        """
        self._check_driver_alive()

        pyautogui = self._get_pyautogui()

        try:
            # 先点击获取焦点
            pyautogui.click(x, y)
            time.sleep(0.1)

            # 输入文字
            # 注意: pyautogui.typewrite 不支持中文
            # 中文输入需要使用 pyperclip 或其他方式
            if self._contains_chinese(text):
                self._type_chinese(text)
            else:
                pyautogui.typewrite(text)

            logger.debug(f"输入文字: '{text}' at ({x}, {y})")

        except Exception as e:
            raise DriverError(f"输入文字失败: ({x}, {y})", cause=e)

    def _contains_chinese(self, text: str) -> bool:
        """检查文本是否包含中文字符"""
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                return True
        return False

    def _type_chinese(self, text: str) -> None:
        """输入中文文字

        使用剪贴板实现中文输入。
        """
        try:
            import pyperclip
            pyperclip.copy(text)
            # 使用快捷键粘贴
            if self.platform == "macos":
                self._get_pyautogui().hotkey('command', 'v')
            else:
                self._get_pyautogui().hotkey('ctrl', 'v')
            time.sleep(0.1)
        except ImportError:
            logger.warning(
                "pyperclip 未安装，中文输入可能不正常。"
                "请运行: pip install pyperclip"
            )
            # 回退到 pyautogui，虽然不支持中文但至少尝试
            self._get_pyautogui().typewrite(text)

    def get_text_in_bbox(self, x1: int, y1: int, x2: int, y2: int) -> str:
        """获取指定区域的文字（视觉定位专用）

        使用 OCR 提取区域内的文字。

        Args:
            x1: 左上角 x 坐标
            y1: 左上角 y 坐标
            x2: 右下角 x 坐标
            y2: 右下角 y 坐标

        Returns:
            区域内的文字内容

        Raises:
            DriverError: 获取失败
        """
        self._check_driver_alive()

        # 初始化视觉定位器（包含 OCR 功能）
        if self._vision_provider is None:
            self._init_vision_provider()

        try:
            # 获取截图
            screenshot_path = self._get_fresh_screenshot()

            # 调用 OCR
            text = self._vision_provider.ocr_region(
                screenshot_path,
                (x1, y1, x2, y2)
            )
            return text

        except Exception as e:
            logger.error(f"OCR 获取文字失败: {e}")
            raise DriverError(
                f"获取文字失败: 区域 ({x1}, {y1}, {x2}, {y2})",
                cause=e
            )

    # ── 扩展方法 ─────────────────────────────────────────────────────

    def get_viewport_size(self) -> Tuple[int, int]:
        """获取屏幕大小

        Returns:
            (width, height) 屏幕宽高
        """
        pyautogui = self._get_pyautogui()
        return pyautogui.size()

    def move_to(self, x: int, y: int) -> None:
        """移动鼠标到指定坐标

        Args:
            x: x 坐标
            y: y 坐标
        """
        self._check_driver_alive()
        pyautogui = self._get_pyautogui()
        pyautogui.moveTo(x, y)
        logger.debug(f"移动鼠标到: ({x}, {y})")

    def double_click(self, x: int, y: int) -> None:
        """双击指定坐标

        Args:
            x: x 坐标
            y: y 坐标
        """
        self._check_driver_alive()
        pyautogui = self._get_pyautogui()
        pyautogui.doubleClick(x, y)
        logger.debug(f"双击坐标: ({x}, {y})")

    def right_click(self, x: int, y: int) -> None:
        """右键点击指定坐标

        Args:
            x: x 坐标
            y: y 坐标
        """
        self._check_driver_alive()
        pyautogui = self._get_pyautogui()
        pyautogui.rightClick(x, y)
        logger.debug(f"右键点击坐标: ({x}, {y})")

    def drag(
        self,
        from_x: int,
        from_y: int,
        to_x: int,
        to_y: int,
        duration: float = 0.5
    ) -> None:
        """拖拽操作

        Args:
            from_x: 起点 x 坐标
            from_y: 起点 y 坐标
            to_x: 终点 x 坐标
            to_y: 终点 y 坐标
            duration: 拖拽持续时间（秒）
        """
        self._check_driver_alive()
        pyautogui = self._get_pyautogui()
        pyautogui.drag(
            to_x - from_x,
            to_y - from_y,
            duration=duration,
            _pause=False
        )
        logger.debug(f"拖拽: ({from_x}, {from_y}) -> ({to_x}, {to_y})")

    def scroll(self, clicks: int, x: int = None, y: int = None) -> None:
        """滚轮滚动

        Args:
            clicks: 滚动次数，正数向上，负数向下
            x: x 坐标（可选，默认当前位置）
            y: y 坐标（可选，默认当前位置）
        """
        self._check_driver_alive()
        pyautogui = self._get_pyautogui()
        pyautogui.scroll(clicks, x, y)
        logger.debug(f"滚轮滚动: {clicks} 次")

    def press_key(self, key: str) -> None:
        """按下按键

        Args:
            key: 按键名称 (如 'enter', 'escape', 'tab')

        支持的按键:
            - 字母: a-z
            - 数字: 0-9
            - 功能键: f1-f12
            - 特殊键: enter, escape, tab, space, backspace, delete,
                     up, down, left, right, home, end, pageup, pagedown
        """
        self._check_driver_alive()
        pyautogui = self._get_pyautogui()
        pyautogui.press(key)
        logger.debug(f"按键: {key}")

    def hotkey(self, *keys: str) -> None:
        """组合键

        Args:
            *keys: 按键序列 (如 'ctrl', 'c' 表示 Ctrl+C)

        Examples:
            driver.hotkey('ctrl', 'c')  # 复制
            driver.hotkey('command', 'v')  # macOS 粘贴
        """
        self._check_driver_alive()
        pyautogui = self._get_pyautogui()
        pyautogui.hotkey(*keys)
        logger.debug(f"组合键: {'+'.join(keys)}")

    def get_mouse_position(self) -> Tuple[int, int]:
        """获取当前鼠标位置

        Returns:
            (x, y) 鼠标坐标
        """
        pyautogui = self._get_pyautogui()
        return pyautogui.position()


class _PlaceholderVisionProvider:
    """占位视觉定位器

    在视觉定位模块未实现时使用。
    所有方法抛出 NotImplementedError。
    """

    def locate(
        self,
        locator_type: str,
        locator_value: str,
        screenshot_path: str
    ) -> Optional[Tuple[int, int, int, int]]:
        """定位元素"""
        raise NotImplementedError(
            "视觉定位功能尚未实现。"
            "请等待 RodSki 视觉定位模块发布。"
        )

    def ocr_region(
        self,
        screenshot_path: str,
        region: Tuple[int, int, int, int]
    ) -> str:
        """OCR 识别区域文字"""
        raise NotImplementedError(
            "OCR 功能尚未实现。"
            "请等待 RodSki 视觉定位模块发布。"
        )