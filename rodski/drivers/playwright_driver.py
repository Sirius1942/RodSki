"""Playwright 驱动封装 - Web 自动化

特性:
- 自动等待元素可见/可点击
- 智能重试机制
- 支持多种定位器格式
- 支持视觉定位器 (vision/ocr/vision_bbox)
- 坐标点击和输入
- 完善的异常处理
"""
from __future__ import annotations

import logging
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional, Tuple
from .base_driver import BaseDriver
from core.exceptions import (
    DriverError,
    DriverStoppedError,
    ElementNotFoundError,
    TimeoutError,
    is_critical_error,
)

logger = logging.getLogger("rodski")

# macOS：Playwright 自带的 Chromium 在 headless=False 时可能 SIGSEGV（与系统/GPU 相关）。
# 若已安装 Google Chrome，使用 channel="chrome" 可稳定跑有界面自动化。
_CHROME_MACOS = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")

# 支持的视觉定位器类型
VISION_LOCATOR_TYPES = {'vision', 'ocr', 'vision_bbox'}


def _launch_channel_chromium(headless: bool, browser: str) -> str | None:
    """返回 chromium.launch(channel=...) 的 channel；无则返回 None。"""
    if browser != "chromium" or headless:
        return None
    env = os.environ.get("RODSKI_PLAYWRIGHT_CHANNEL")
    if env is not None:
        env = env.strip()
        return env if env else None
    if sys.platform != "darwin":
        return None
    if _CHROME_MACOS.is_file():
        return "chrome"
    return None


class PlaywrightDriver(BaseDriver):
    """Playwright 驱动

    自动等待策略:
    - click: 等待元素可见、稳定、可点击
    - type: 等待元素可见、可编辑
    - 默认超时: 10秒

    支持的定位器类型:
    - 传统定位器: id, css, xpath, text 等
    - 视觉定位器: vision, ocr, vision_bbox
    """

    # 默认超时时间（毫秒）
    DEFAULT_TIMEOUT = 10000

    def __init__(self, headless: bool = False, browser: str = "chromium"):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        browser_type = getattr(self._pw, browser, self._pw.chromium)
        launch_kw: dict = {"headless": headless}
        if not headless:
            launch_kw["args"] = ["--start-maximized"]
        ch = _launch_channel_chromium(headless, browser)
        if ch:
            launch_kw["channel"] = ch
            logger.info(
                "Playwright 使用 channel=%s（有界面模式在 macOS 上更稳定；"
                "可设环境变量 RODSKI_PLAYWRIGHT_CHANNEL 覆盖，置空则禁用）",
                ch,
            )
        self.browser = browser_type.launch(**launch_kw)
        # 非 headless 模式使用最大化窗口；headless 使用固定分辨率
        if not headless:
            self.page = self.browser.new_page(no_viewport=True)
        else:
            self.page = self.browser.new_page()
        self._is_closed = False
        self._timeout = self.DEFAULT_TIMEOUT
        # 视觉定位器（延迟加载）
        self._vision_locator = None

    def _check_driver_alive(self):
        """检查驱动是否存活"""
        if self._is_closed:
            raise DriverStoppedError(
                "Playwright 驱动已关闭",
                driver_type="Playwright"
            )

    def _convert_locator(self, locator: str) -> str:
        """转换定位器格式为 CSS 选择器"""
        if locator.startswith('id='):
            return '#' + locator[3:]
        elif locator.startswith('class='):
            return '.' + locator[6:]
        elif locator.startswith('css='):
            return locator[4:]
        elif locator.startswith('xpath='):
            return locator
        elif locator.startswith('text='):
            return locator
        elif locator.startswith('name='):
            return f'[name="{locator[5:]}"]'
        elif locator.startswith('#') or locator.startswith('.'):
            return locator
        else:
            return locator

    def _handle_error(self, operation: str, locator: str, error: Exception) -> None:
        """统一错误处理"""
        error_msg = str(error)
        
        # 严重错误：驱动已停止
        if is_critical_error(error):
            self._is_closed = True
            raise DriverStoppedError(
                f"{operation} 操作失败: {error_msg}",
                driver_type="Playwright"
            )
        
        # 记录日志
        logger.error(f"{operation} 失败: {locator}, 错误: {error_msg}")

    def _wait_for_element_visible(self, locator: str, timeout: int = None) -> bool:
        """等待元素可见
        
        Args:
            locator: CSS 选择器
            timeout: 超时时间（毫秒）
            
        Returns:
            元素是否可见
        """
        timeout = timeout or self._timeout
        try:
            self.page.wait_for_selector(locator, state="visible", timeout=timeout)
            return True
        except Exception as e:
            logger.warning(f"等待元素可见超时: {locator}")
            return False

    def _wait_for_element_editable(self, locator: str, timeout: int = None) -> bool:
        """等待元素可编辑"""
        timeout = timeout or self._timeout
        try:
            self.page.wait_for_selector(locator, state="visible", timeout=timeout)
            return True
        except Exception:
            return False

    def locate_element(self, locator_type: str, locator_value: str) -> Optional[Tuple[int, int, int, int]]:
        """定位元素，返回边界框坐标（BaseDriver 接口）"""
        self._check_driver_alive()
        locator = f"{locator_type}={locator_value}"
        css_locator = self._convert_locator(locator)
        try:
            element = self.page.query_selector(css_locator)
            if element:
                box = element.bounding_box()
                if box:
                    return (int(box['x']), int(box['y']),
                           int(box['x'] + box['width']), int(box['y'] + box['height']))
        except Exception:
            pass
        return None

    def click(self, locator_or_x, y=None, **kwargs) -> bool:
        """点击元素或坐标

        支持两种调用方式：
        - click(locator)     → 旧 API，定位器点击（通过 click_locator）
        - click(x, y)       → BaseDriver 坐标 API
        """
        if y is None and isinstance(locator_or_x, str):
            return self.click_locator(locator_or_x, **kwargs)
        x = locator_or_x
        self._check_driver_alive()
        try:
            self.page.mouse.click(x, y)
            return True
        except Exception as e:
            self._handle_error("click", f"({x}, {y})", e)
            return False

    def type_text(self, x: int, y: int, text: str) -> None:
        """在指定坐标输入文字（BaseDriver 接口）"""
        self._check_driver_alive()
        self.page.mouse.click(x, y)
        self.page.keyboard.type(text)

    def get_text(self, x1: int, y1: int, x2: int, y2: int) -> str:
        """获取指定区域的文字（BaseDriver 接口）"""
        self._check_driver_alive()
        # Playwright 不直接支持坐标区域文本提取，返回空字符串
        logger.warning("PlaywrightDriver.get_text 坐标接口暂不支持")
        return ""

    def double_click(self, x: int, y: int) -> None:
        """双击指定坐标（BaseDriver 接口）"""
        self._check_driver_alive()
        self.page.mouse.dblclick(x, y)

    def right_click(self, x: int, y: int) -> None:
        """右键点击指定坐标（BaseDriver 接口）"""
        self._check_driver_alive()
        self.page.mouse.click(x, y, button="right")

    def hover(self, locator_or_x, y=None) -> bool:
        """悬停

        支持两种调用方式：
        - hover(locator)  → 旧 API，定位器悬停
        - hover(x, y)     → BaseDriver 坐标 API
        """
        if y is None and isinstance(locator_or_x, str):
            return self.hover_locator(locator_or_x)
        x = locator_or_x
        self._check_driver_alive()
        self.page.mouse.move(x, y)

    def scroll(self, x: int, y: int) -> None:
        """滚动指定距离（BaseDriver 接口）"""
        self._check_driver_alive()
        self.page.mouse.wheel(x, y)

    def take_screenshot(self) -> str:
        """截图（BaseDriver 接口）"""
        import tempfile
        import time
        path = tempfile.mktemp(suffix='.png', prefix=f'screenshot_{int(time.time())}_')
        self.page.screenshot(path=path)
        return path

    def click_locator(self, locator: str, **kwargs) -> bool:
        """点击元素（通过定位器）

        自动等待元素可见、稳定、可点击后执行点击
        """
        self._check_driver_alive()
        
        css_locator = self._convert_locator(locator)
        logger.debug(f"点击元素: {locator} -> {css_locator}")
        
        try:
            # 先等待元素可见
            try:
                self.page.wait_for_selector(css_locator, state="visible", timeout=self._timeout)
            except Exception:
                # 等待失败，尝试直接点击
                pass
            
            # 尝试正常点击
            try:
                self.page.click(css_locator, timeout=5000, **kwargs)
                return True
            except Exception as e:
                error_msg = str(e).lower()
                
                # 检查是否为严重错误
                if is_critical_error(e):
                    raise DriverStoppedError(str(e))
                
                # 元素不可见或被遮挡，尝试强制点击
                if "not visible" in error_msg or "attached" in error_msg or "timeout" in error_msg:
                    logger.debug(f"尝试强制点击...")
                    try:
                        self.page.click(css_locator, force=True, timeout=3000)
                        return True
                    except:
                        pass
                    
                    # 尝试 JavaScript 点击，验证元素确实存在
                    logger.debug(f"尝试 JavaScript 点击...")
                    clicked = self.page.evaluate(f"""
                        (() => {{
                            const el = document.querySelector('{css_locator}');
                            if (el) {{ el.click(); return true; }}
                            return false;
                        }})()
                    """)
                    if clicked:
                        return True
                    raise DriverError(f"点击失败: 元素未找到 {locator}", locator=locator)

                # 其他错误
                raise DriverError(f"点击失败: {locator}", locator=locator, cause=e)

        except DriverStoppedError:
            raise
        except DriverError:
            raise
        except Exception as e:
            self._handle_error("click_locator", locator, e)
            raise DriverError(f"点击失败: {locator}", locator=locator, cause=e)

    def type_locator(self, locator: str, text: str, **kwargs) -> bool:
        """输入文本（通过定位器）

        自动等待元素可见、可编辑后执行输入
        """
        self._check_driver_alive()

        css_locator = self._convert_locator(locator)
        logger.debug(f"输入文本: {locator} -> {css_locator}")

        try:
            # 先等待元素可见
            try:
                self.page.wait_for_selector(css_locator, state="visible", timeout=self._timeout)
            except Exception:
                # 等待失败，继续尝试
                pass

            # 尝试正常输入
            try:
                self.page.fill(css_locator, text, timeout=5000, **kwargs)
                return True
            except Exception as e:
                error_msg = str(e).lower()
                
                # 检查是否为严重错误
                if is_critical_error(e):
                    raise DriverStoppedError(str(e))
                
                # 元素不可编辑，尝试先清空再输入
                if "not visible" in error_msg or "editable" in error_msg or "timeout" in error_msg:
                    logger.debug(f"尝试清空后输入...")
                    try:
                        # 先聚焦元素
                        self.page.focus(css_locator, timeout=3000)
                        # 清空
                        self.page.fill(css_locator, "", timeout=3000)
                        # 输入
                        self.page.fill(css_locator, text, timeout=3000)
                        return True
                    except:
                        pass
                    
                    # 尝试 JavaScript 输入，验证元素确实存在
                    logger.debug(f"尝试 JavaScript 输入...")
                    safe_text = text.replace("'", "\\'").replace("\n", "\\n")
                    typed = self.page.evaluate(f"""
                        (() => {{
                            const el = document.querySelector('{css_locator}');
                            if (el) {{ 
                                el.value = '{safe_text}'; 
                                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                return true;
                            }}
                            return false;
                        }})()
                    """)
                    if typed:
                        return True
                    raise DriverError(f"输入失败: 元素未找到 {locator}", locator=locator, cause=e)
                
                # 其他错误
                raise DriverError(f"输入失败: {locator}", locator=locator, cause=e)
                
        except DriverStoppedError:
            raise
        except DriverError:
            raise
        except Exception as e:
            self._handle_error("type", locator, e)
            raise DriverError(f"输入失败: {locator}", locator=locator, cause=e)

    def type(self, locator: str, text: str) -> bool:
        """输入文本（KeywordEngine 旧 API）"""
        return self.type_locator(locator, text)

    def check(self, locator: str, **kwargs) -> bool:
        """检查元素可见"""
        self._check_driver_alive()

        try:
            self.page.wait_for_selector(locator, state="visible", timeout=3000)
            return True
        except Exception:
            return False

    def wait(self, seconds: float) -> None:
        """等待指定秒数"""
        time.sleep(seconds)

    def launch(self, **kwargs) -> None:
        """启动应用或打开页面（BaseDriver 接口）"""
        url = kwargs.get('url')
        if url:
            self.navigate(url)

    def navigate(self, url: str) -> bool:
        """导航到URL，等待页面加载完成"""
        self._check_driver_alive()

        try:
            self.page.goto(url, wait_until="networkidle", timeout=30000)
            logger.debug(f"导航成功: {url}")
            return True
        except Exception as e:
            # 尝试不等待网络空闲
            try:
                self.page.goto(url, timeout=30000)
                return True
            except Exception as e2:
                self._handle_error("navigate", url, e2)
                raise DriverError(f"导航失败: {url}", cause=e2)

    def screenshot(self, path: str) -> bool:
        """截图"""
        self._check_driver_alive()
        
        try:
            self.page.screenshot(path=path)
            logger.debug(f"截图成功: {path}")
            return True
        except Exception as e:
            self._handle_error("screenshot", path, e)
            return False

    def select(self, locator: str, value: str) -> bool:
        """下拉选择"""
        self._check_driver_alive()
        
        try:
            self.page.select_option(locator, value)
            logger.debug(f"选择成功: {locator} = {value}")
            return True
        except Exception as e:
            self._handle_error("select", locator, e)
            raise DriverError(f"选择失败: {locator}", locator=locator, cause=e)

    def hover_locator(self, locator: str) -> bool:
        """悬停（通过定位器）"""
        self._check_driver_alive()

        try:
            self.page.hover(locator)
            logger.debug(f"悬停成功: {locator}")
            return True
        except Exception as e:
            self._handle_error("hover_locator", locator, e)
            raise DriverError(f"悬停失败: {locator}", locator=locator, cause=e)

    def drag(self, from_loc: str, to_loc: str) -> bool:
        """拖拽"""
        self._check_driver_alive()
        
        try:
            self.page.drag_and_drop(from_loc, to_loc)
            logger.debug(f"拖拽成功: {from_loc} -> {to_loc}")
            return True
        except Exception as e:
            self._handle_error("drag", f"{from_loc} -> {to_loc}", e)
            raise DriverError(f"拖拽失败: {from_loc} -> {to_loc}", cause=e)

    def scroll_page(self, x: int = 0, y: int = 300) -> bool:
        """滚动页面（通过像素距离）"""
        self._check_driver_alive()

        try:
            self.page.evaluate(f"window.scrollBy({x}, {y})")
            logger.debug(f"滚动成功: ({x}, {y})")
            return True
        except Exception as e:
            self._handle_error("scroll_page", f"({x}, {y})", e)
            raise DriverError(f"滚动失败", cause=e)

    def scroll(self, x: int = 0, y: int = 300) -> bool:
        """滚动（KeywordEngine 旧 API）"""
        return self.scroll_page(x, y)

    def assert_element(self, locator: str, expected: str) -> bool:
        """断言元素文本包含预期值"""
        self._check_driver_alive()
        
        try:
            text = self.page.text_content(locator) or ""
            if expected in text:
                logger.debug(f"断言成功: {locator} 包含 '{expected}'")
                return True
            else:
                logger.warning(f"断言失败: {locator} 文本 '{text}' 不包含 '{expected}'")
                return False
        except Exception as e:
            self._handle_error("assert", locator, e)
            return False

    def clear(self, locator: str) -> bool:
        """清空输入框"""
        self._check_driver_alive()
        
        css_locator = self._convert_locator(locator)
        try:
            self.page.fill(css_locator, "")
            return True
        except Exception as e:
            self._handle_error("clear", locator, e)
            raise DriverError(f"清空失败: {locator}", locator=locator, cause=e)

    def double_click_locator(self, locator: str) -> bool:
        """双击（通过定位器）"""
        self._check_driver_alive()

        try:
            self.page.dblclick(locator)
            return True
        except Exception as e:
            self._handle_error("double_click_locator", locator, e)
            raise DriverError(f"双击失败: {locator}", locator=locator, cause=e)

    def right_click_locator(self, locator: str) -> bool:
        """右键点击（通过定位器）"""
        self._check_driver_alive()

        try:
            self.page.click(locator, button="right")
            return True
        except Exception as e:
            self._handle_error("right_click_locator", locator, e)
            raise DriverError(f"右键点击失败: {locator}", locator=locator, cause=e)

    def key_press(self, key: str) -> bool:
        """按键"""
        self._check_driver_alive()
        
        try:
            self.page.keyboard.press(key)
            return True
        except Exception as e:
            self._handle_error("key_press", key, e)
            raise DriverError(f"按键失败: {key}", cause=e)

    def get_text_locator(self, locator: str) -> str:
        """获取元素文本（通过定位器）"""
        self._check_driver_alive()

        try:
            return self.page.text_content(locator)
        except Exception as e:
            self._handle_error("get_text_locator", locator, e)
            return None

    def upload_file(self, locator: str, file_path: str) -> bool:
        """上传文件"""
        self._check_driver_alive()
        
        try:
            self.page.set_input_files(locator, file_path)
            return True
        except Exception as e:
            self._handle_error("upload_file", locator, e)
            raise DriverError(f"上传文件失败: {file_path}", cause=e)

    def get_page_text(self) -> str:
        """获取页面所有文本内容"""
        self._check_driver_alive()
        try:
            return self.page.inner_text('body')
        except Exception as e:
            logger.warning(f"获取页面文本失败: {e}")
            return ""

    def close(self) -> None:
        """关闭驱动"""
        if self._is_closed:
            return
            
        self._is_closed = True
        try:
            if self.browser:
                self.browser.close()
        except Exception as e:
            logger.debug(f"关闭浏览器时出错: {e}")
        try:
            if self._pw:
                self._pw.stop()
        except Exception as e:
            logger.debug(f"停止 Playwright 时出错: {e}")