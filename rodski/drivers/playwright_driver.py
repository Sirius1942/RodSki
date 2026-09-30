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
from typing import Optional, Tuple, Union, Dict, Any
try:
    from .base_driver import BaseDriver
    from ..core.exceptions import (
        DriverError,
        DriverStoppedError,
        ElementNotFoundError,
        ElementNotInteractableError,
        StaleElementError,
        TimeoutError,
        is_critical_error,
    )
except ImportError:
    from rodski.drivers.base_driver import BaseDriver
    from core.exceptions import (
        DriverError,
        DriverStoppedError,
        ElementNotFoundError,
        ElementNotInteractableError,
        StaleElementError,
        TimeoutError,
        is_critical_error,
    )

logger = logging.getLogger("rodski")

# macOS：Playwright 自带的 Chromium 在 headless=False 时可能 SIGSEGV（与系统/GPU 相关）。
# 若已安装 Google Chrome，使用 channel="chrome" 可稳定跑有界面自动化。
_CHROME_MACOS = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")

# 支持的视觉定位器类型
VISION_LOCATOR_TYPES = {'vision', 'ocr', 'vision_bbox'}


def _resolve_video_size(value: str) -> dict:
    """将录制分辨率配置值解析为 Playwright record_video_size 字典。

    Args:
        value: 分辨率配置值，支持:
            - "screen": 可用屏幕区域（macOS 排除菜单栏/Dock，其他平台用全屏）
            - "2k": 2560x1440
            - "hd": 1920x1080
            - "WxH": 自定义宽高，如 "1920x1080"

    Returns:
        {"width": int, "height": int}

    Raises:
        ValueError: 无效的分辨率值
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"无效的录制分辨率值: {value!r}")

    value = value.strip().lower()

    if value == "screen":
        # macOS: 使用 visibleFrame（排除菜单栏和 Dock），避免录像底部出现空白
        if sys.platform == "darwin":
            try:
                from AppKit import NSScreen
                vf = NSScreen.mainScreen().visibleFrame()
                w = int(vf.size.width)
                h = int(vf.size.height)
                if w > 0 and h > 0:
                    return {"width": w, "height": h}
            except Exception:
                pass
        # 其他平台或 AppKit 不可用：使用 mss 全屏尺寸
        try:
            import mss
            with mss.mss() as sct:
                monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                return {"width": monitor["width"], "height": monitor["height"]}
        except Exception:
            return {"width": 1920, "height": 1080}

    if value == "2k":
        return {"width": 2560, "height": 1440}

    if value == "hd":
        return {"width": 1920, "height": 1080}

    # 尝试解析 WxH 格式
    import re as _re
    match = _re.match(r"^(\d+)x(\d+)$", value)
    if match:
        w, h = int(match.group(1)), int(match.group(2))
        if w > 0 and h > 0:
            return {"width": w, "height": h}
        raise ValueError(f"无效的录制分辨率值（宽高必须大于 0）: {value!r}")

    raise ValueError(f"无效的录制分辨率值: {value!r}，支持: screen, 2k, hd, WxH")


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

    自动等待策略（v11.7.0）:
    - 查找元素的轮询与上限由公共层 core/auto_wait.py 按 DefaultValue.AutoWait（毫秒；不设置 = 不自动等待）控制
    - 本驱动 probe() 即时探测；动作的可操作性等待（可见 / 稳定 / 可用 / 未遮挡）只用传入的 timeout_ms
    - 截图超时 SCREENSHOT_TIMEOUT_MS；navigate 页面加载超时不属于元素查找

    支持的定位器类型:
    - 传统定位器: id, css, xpath, text 等
    - 视觉定位器: vision, ocr, vision_bbox
    """

    # 默认超时时间（毫秒）
    DEFAULT_TIMEOUT = 10000

    def __init__(self, config: Union['ConfigManager', Dict[str, Any], None] = None,
                 headless: bool = False, browser: str = "chromium",
                 cdp_endpoint: Optional[str] = None):
        """初始化 PlaywrightDriver

        Args:
            config: 配置对象或字典。支持三种方式：
                1. ConfigManager 对象（传统方式，向后兼容）
                2. 配置字典（探索测试场景，避免序列化问题）
                3. None（使用 headless/browser 参数）
            headless: 无头模式（当 config=None 时生效）
            browser: 浏览器类型（当 config=None 时生效）
            cdp_endpoint: CDP 附加模式（v11.1.0）。给定时不自行 launch 浏览器，
                而是 connect_over_cdp 到已启动的远程调试浏览器（如
                http://127.0.0.1:9222），复用其默认 context 与页面状态。
                适用于「暂停→Agent 接管→继续」工作流：多个 driver / Agent 顺序
                附加同一个浏览器会话，彼此能看到对方的操作结果。
                attached 模式下 headless/browser 参数不生效，close() 只断连、
                不关闭用户浏览器或其 context。
        """
        # 解析配置
        if config is None:
            # 方式3：使用参数
            self._config_dict = {
                'headless': headless,
                'browser': browser,
                'timeout': self.DEFAULT_TIMEOUT,
            }
            if cdp_endpoint:
                self._config_dict['cdp_endpoint'] = cdp_endpoint
        elif isinstance(config, dict):
            # 方式2：字典配置（探索测试场景）
            self._config_dict = config
        else:
            # 方式1：ConfigManager 对象（传统场景，向后兼容）
            try:
                self._config_dict = config.to_dict()
            except AttributeError:
                # 旧版 ConfigManager 没有 to_dict()，回退到直接访问
                self._config_dict = {
                    'headless': getattr(config, 'headless', headless),
                    'browser': getattr(config, 'browser', browser),
                    'timeout': getattr(config, 'timeout', self.DEFAULT_TIMEOUT),
                }

        # 从配置字典提取参数
        self.headless = self._config_dict.get('headless', headless)
        self.browser_name = self._config_dict.get('browser', browser)
        # 保留兼容字段；v11.7.0 起元素查找超时由 AutoWait（set_auto_wait / timeout_ms）决定，不再读取它
        self._timeout = self._config_dict.get('timeout', self.DEFAULT_TIMEOUT)
        # CDP 附加模式：driver 不拥有浏览器，只断连不关闭（close() 语义见下）
        self.attached = bool(self._config_dict.get('cdp_endpoint'))
        self._cdp_endpoint = self._config_dict.get('cdp_endpoint') or ""

        # 初始化内部状态
        self._pw = None
        self.browser = None
        self.context = None
        self.page = None
        self._is_closed = False
        self._vision_locator = None
        self._recording_context = None
        self._recording_video = None
        self._recording_target_path: Optional[Path] = None
        self._recording_saved_path: Optional[str] = None
        # 录像后端标识：供 SKIExecutor._select_recording_backend 区分驱动类型
        self.recording_backend = "playwright"
        # JS 覆盖率采集状态位：跟踪是否已通过 start_js_coverage 开始过采集
        self._coverage_started = False
        # 覆盖率采集用的 CDP session（Python Playwright 无 page.coverage API，
        # 需直接驱动 CDP Profiler domain，详见 start_js_coverage 的说明）
        self._coverage_cdp_session = None
        # close() 关闭浏览器前抓取的覆盖率快照：case 的 post_process 常以 close
        # 结束用例（浏览器在 CLI 调用 stop_js_coverage 前已关闭，CDP session 失效），
        # 因此需要在 close() 时提前取一次快照，stop_js_coverage 优先返回该快照
        self._coverage_cached_entries: Optional[list] = None
        # 页面异常监控器（v0.1）：懒加载，仅在 inject_monitor() 后生效
        self._browser_monitor = None
        # v11.6.0 SessionMode=shared_browser：run 级共享浏览器（由执行器挂接）
        self._shared_browser = None
        # v11.6.0 (C1) 原生弹窗：全局策略 accept|dismiss|fail、一次性处理器、最近弹窗文本
        self._dialog_policy = "fail"
        self._dialog_once: Optional[Tuple[str, Optional[str]]] = None
        self._last_dialog_text: Optional[str] = None
        self._unexpected_dialog: Optional[str] = None
        self._dialog_hooked_page = None

    def _ensure_browser(self):
        """懒加载：首次需要浏览器时才启动 Playwright 和浏览器实例"""
        if self.browser is not None:
            # v11.6.0 (C1)：录像等场景会重建 page，每次取用时确保弹窗处理器挂在当前 page 上
            self._ensure_dialog_handler()
            return
        if self.attached:
            self._attach_cdp_browser()
            self._ensure_dialog_handler()
            return
        if getattr(self, "_shared_browser", None) is not None:
            # v11.6.0 SessionMode=shared_browser：复用 run 级浏览器进程，本驱动只拥有自己的 context
            self.browser = self._shared_browser.acquire(self._launch_browser)
            context_kw = {"no_viewport": True} if not self.headless else {}
            self.context = self.browser.new_context(**context_kw)
            self.page = self.context.new_page()
            self.inject_monitor()
            self._ensure_dialog_handler()
            return
        self._pw, self.browser = self._launch_browser()
        if not self.headless:
            self.page = self.browser.new_page(no_viewport=True)
        else:
            self.page = self.browser.new_page()
        # 浏览器启动后立即注入监控（若已初始化则重注入）
        self.inject_monitor()
        self._ensure_dialog_handler()

    def attach_shared_browser(self, shared_browser) -> None:
        """v11.6.0：挂接 run 级共享浏览器（SessionMode=shared_browser，须在浏览器懒启动前调用）。

        挂接后本驱动在共享浏览器上新建独立 BrowserContext；close() 只关闭该 context，
        浏览器进程由执行器在 run 结束时统一关闭。CDP 附加模式下忽略。
        """
        if self.attached or self.browser is not None:
            return
        self._shared_browser = shared_browser

    def _launch_browser(self):
        """启动 Playwright 与浏览器进程，返回 (playwright, browser)。"""
        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start()
        browser_type = getattr(pw, self.browser_name, pw.chromium)
        _args = [
            "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding",
            "--disable-backgrounding-occluded-windows",
        ]
        if not self.headless:
            _args.append("--start-maximized")
        launch_kw: dict = {"headless": self.headless, "args": _args}
        ch = _launch_channel_chromium(self.headless, self.browser_name)
        if ch:
            launch_kw["channel"] = ch
            logger.info(
                "Playwright 使用 channel=%s（有界面模式在 macOS 上更稳定；"
                "可设环境变量 RODSKI_PLAYWRIGHT_CHANNEL 覆盖，置空则禁用）",
                ch,
            )
        browser = browser_type.launch(**launch_kw)
        logger.info("启动浏览器: %s（headless=%s）", self.browser_name, self.headless)
        return pw, browser

    def _attach_cdp_browser(self):
        """CDP 附加模式：连接到已启动的远程调试浏览器，复用其默认 context 与页面。

        适用于「暂停→Agent 接管→继续」：外部（Agent / 另一个 rodski run）已用
        --remote-debugging-port 启动浏览器并保留了登录态等页面状态；本 driver 顺序
        附加到同一浏览器，即可读到、操作、验证对方的操作结果。

        与 launch 模式的关键差异：
        - 不 launch，connect_over_cdp 返回的对象“拥有”浏览器但 close() 仅断连；
        - context 取自远端默认 context（browser.contexts[0]），**不得 close**，
          否则会把用户/上一个 run 保留的页面状态关掉；
        - page 复用该 context 首个已有页面；context 无页时新建（浏览器重启场景）。
        """
        from playwright.sync_api import sync_playwright
        endpoint = self._cdp_endpoint
        logger.info("Playwright 附加 CDP 浏览器: %s", endpoint)
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.connect_over_cdp(endpoint)
        contexts = self.browser.contexts
        if contexts:
            self.context = contexts[0]
            self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        else:
            self.context = self.browser.new_context()
            self.page = self.context.new_page()
        # 附加模式下不存在 launch 注入的录制 context；有页面即重注入监控（幂等）
        self.inject_monitor()

    # ── 页面异常监控（v0.1）────────────────────────────────────────────

    def inject_monitor(self) -> None:
        """注入浏览器异常监控脚本。在 launch / navigate 后调用一次。

        幂等；浏览器未启动时静默跳过。
        """
        try:
            from ..core.browser_monitor import BrowserMonitor
        except ImportError:
            from rodski.core.browser_monitor import BrowserMonitor
        if self._browser_monitor is None:
            self._browser_monitor = BrowserMonitor(self)
        self._browser_monitor.inject()

    def set_monitor_step(self, step_id: str) -> None:
        """标记当前执行的步骤 ID，后续捕获的异常会附带此标记。"""
        if self._browser_monitor is not None:
            self._browser_monitor.set_step(step_id)

    def collect_monitor_errors(self) -> list:
        """读取并清空页面异常缓冲区，返回本 step 内捕获的异常列表。

        返回格式参见 BrowserMonitor.collect() 的文档。
        """
        if self._browser_monitor is None:
            return []
        return self._browser_monitor.collect()

    def _check_driver_alive(self):
        """检查驱动是否存活"""
        if self._is_closed:
            raise DriverStoppedError(
                "Playwright 驱动已关闭",
                driver_type="Playwright"
            )

    def _convert_locator(self, locator: str) -> str:
        """转换定位器格式为 Playwright 支持的选择器"""
        if locator.startswith('id='):
            return '#' + locator[3:]
        elif locator.startswith('class='):
            return '.' + locator[6:]
        elif locator.startswith('css='):
            return locator[4:]
        elif locator.startswith('xpath='):
            # 移除 xpath= 前缀，Playwright 原生支持 XPath
            return locator[6:]  # 返回纯 XPath 字符串
        elif locator.startswith('text='):
            # Playwright text locator: text=内容
            return locator  # 保持原格式
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

    def _collect_failure_evidence(self, error: Exception, context: dict) -> dict:
        """失败时采集完整证据（v9.2.3+）

        Args:
            error: 异常对象
            context: 操作上下文（包含 operation, locator 等信息）

        Returns:
            证据字典，包含 screenshot, url, browser_errors, dom_snapshot 等
        """
        evidence = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'timestamp': time.time(),
            'context': context,
        }

        try:
            if self.page:
                # 截图（安全执行，失败不抛异常）
                screenshot_b64 = self._safe_screenshot()
                if screenshot_b64:
                    evidence['screenshot'] = screenshot_b64

                # 当前 URL
                try:
                    evidence['url'] = self.page.url
                except Exception:
                    pass

                # 页面标题
                try:
                    evidence['title'] = self.page.title()
                except Exception:
                    pass

                # Console errors（从 BrowserMonitor）
                try:
                    browser_errors = self.collect_monitor_errors()
                    if browser_errors:
                        evidence['browser_errors'] = browser_errors
                except Exception:
                    pass

                # DOM 快照（失败元素附近）
                if 'locator' in context:
                    try:
                        dom_snapshot = self._capture_dom_snapshot(context['locator'])
                        if dom_snapshot:
                            evidence['dom_snapshot'] = dom_snapshot
                    except Exception:
                        pass

        except Exception as e:
            evidence['evidence_collection_error'] = str(e)

        return evidence

    def _safe_screenshot(self) -> Optional[str]:
        """安全截图：即使失败也不抛异常

        Returns:
            Base64 编码的截图，失败返回 None
        """
        try:
            if not self.page:
                return None
            screenshot_bytes = self.page.screenshot(timeout=self.SCREENSHOT_TIMEOUT_MS)
            import base64
            return base64.b64encode(screenshot_bytes).decode()
        except Exception as e:
            logger.debug(f"截图失败: {e}")
            return None

    def _capture_dom_snapshot(self, locator: str) -> dict:
        """捕获失败定位器附近的 DOM 快照

        Args:
            locator: 失败的定位器

        Returns:
            DOM 快照字典
        """
        try:
            script = """
            (locator) => {
                // 尝试多种定位方式
                let elem = null;
                if (locator.startsWith('#')) {
                    elem = document.getElementById(locator.slice(1));
                } else if (locator.startsWith('.')) {
                    elem = document.querySelector(locator);
                } else {
                    elem = document.querySelector(locator);
                }

                if (!elem) {
                    return {
                        found: false,
                        locator: locator,
                        possible_matches: document.querySelectorAll('*').length
                    };
                }

                return {
                    found: true,
                    tag: elem.tagName,
                    id: elem.id,
                    classes: elem.className,
                    text: elem.textContent?.slice(0, 100),
                    parent_tag: elem.parentElement?.tagName,
                    parent_html: elem.parentElement?.outerHTML.slice(0, 500),
                    siblings_count: elem.parentElement?.children.length
                };
            }
            """
            return self.page.evaluate(script, locator) or {}
        except Exception as e:
            logger.debug(f"DOM 快照捕获失败: {e}")
            return {}

    def locate_element(self, locator_type: str, locator_value: str) -> Optional[Tuple[int, int, int, int]]:
        """定位元素，返回边界框坐标（BaseDriver 接口）"""
        self._check_driver_alive()
        self._ensure_browser()
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
        self._ensure_browser()
        try:
            self.page.mouse.click(x, y)
            return True
        except Exception as e:
            self._handle_error("click", f"({x}, {y})", e)
            return False

    def type_text(self, x: int, y: int, text: str) -> None:
        """在指定坐标输入文字（BaseDriver 接口）"""
        self._check_driver_alive()
        self._ensure_browser()
        self.page.mouse.click(x, y)
        self.page.keyboard.type(text)

    def get_text(self, x1: int, y1: int, x2: int, y2: int) -> str:
        """获取指定区域的文字（BaseDriver 接口）"""
        self._check_driver_alive()
        self._ensure_browser()
        # Playwright 不直接支持坐标区域文本提取，返回空字符串
        logger.warning("PlaywrightDriver.get_text 坐标接口暂不支持")
        return ""

    def double_click(self, x: int, y: int) -> None:
        """双击指定坐标（BaseDriver 接口）"""
        self._check_driver_alive()
        self._ensure_browser()
        self.page.mouse.dblclick(x, y)

    def right_click(self, x: int, y: int) -> None:
        """右键点击指定坐标（BaseDriver 接口）"""
        self._check_driver_alive()
        self._ensure_browser()
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
        self._ensure_browser()
        self.page.mouse.move(x, y)

    def scroll(self, x: int, y: int) -> None:
        """滚动指定距离（BaseDriver 接口）"""
        self._check_driver_alive()
        self._ensure_browser()
        self.page.mouse.wheel(x, y)

    def take_screenshot(self) -> str:
        """截图（BaseDriver 接口）"""
        import tempfile
        import time
        self._ensure_browser()
        path = tempfile.mktemp(suffix='.png', prefix=f'screenshot_{int(time.time())}_')
        self.page.screenshot(path=path, timeout=self.SCREENSHOT_TIMEOUT_MS)
        return path

    def current_url(self) -> Optional[str]:
        """返回当前页面真实 URL，采集失败或无效前缀时返回 None。"""
        if self.page is None:
            return None
        try:
            url = self.page.url
        except Exception:
            return None
        if not isinstance(url, str):
            return None
        for prefix in ("about:", "data:", "chrome-error:", "chrome://"):
            if url.startswith(prefix):
                return None
        return url or None

    # ── v11.7.0 自动等待（AutoWait）驱动契约 ─────────────────────────
    # 轮询与 deadline 由公共层（core/auto_wait.py）掌握；本驱动只提供：
    #   probe()                 —— 即时探测（locator.count()，不等待）
    #   动作方法的 timeout_ms     —— Playwright actionability 只用这段剩余预算
    # 所有失败以异常表示（不返回 False），原生异常按 _translate_error 转换：
    #   未匹配到元素 → ElementNotFoundError；已匹配但超时不可操作 → ElementNotInteractableError；
    #   元素脱离 DOM / 页面跳转中 → StaleElementError；浏览器已关闭 → DriverStoppedError；
    #   选择器语法错误等 → DriverError（不在自动等待白名单内，立即失败）。
    # 不再有 wait_for_selector 吞异常、硬编码 5000/3000、force 点击、JS 点击、JS 赋值等降级。

    # 截图超时（毫秒）：截图不是查找元素，不跟随 AutoWait；避免默认 30s 阻塞
    SCREENSHOT_TIMEOUT_MS = 10000

    def _element(self, locator: str, frame: Optional[str] = None):
        """返回定位器对应的 Playwright Locator（首个匹配；frame 为 CSS，">>" 串联多层 iframe）。"""
        return self._verify_scope(frame).locator(self._convert_locator(locator)).first

    def _translate_error(self, operation: str, locator: str, error: Exception,
                         frame: Optional[str] = None) -> Exception:
        """把 Playwright 原生异常转换为 rodski 异常（决定自动等待是否重试）。"""
        if isinstance(error, DriverError):
            return error
        where = f"{locator}（frame={frame}）" if frame else locator
        msg = str(error)
        if is_critical_error(error):
            self._is_closed = True
            return DriverStoppedError(f"{operation}失败: {msg}", driver_type="Playwright")
        low = msg.lower()
        if type(error).__name__ == "TimeoutError" or ("timeout" in low and "exceeded" in low):
            try:
                present = self._verify_scope(frame).locator(self._convert_locator(locator)).count() > 0
            except Exception:
                present = False
            if present:
                return ElementNotInteractableError(
                    f"{operation}: 元素 {where} 已找到但不可操作（不可见 / 禁用 / 被遮挡 / 不稳定）",
                    locator=locator, cause=error)
            hint = "；请确认 frame 选择器指向 <iframe> 元素本身，多层 iframe 用 >> 串联" if frame else ""
            return ElementNotFoundError(f"{operation}: 元素 {where} 未找到{hint}", locator=locator, cause=error)
        if "failed to find frame" in low:
            return ElementNotFoundError(
                f"{operation}: iframe {frame} 尚未出现（元素 {locator}）；请确认 frame 选择器指向 <iframe> 元素本身，"
                f"多层 iframe 用 >> 串联", locator=locator, cause=error)
        if ("not attached" in low or "detached" in low or "context was destroyed" in low
                or "navigation" in low or "frame was detached" in low):
            return StaleElementError(f"{operation}: 元素 {where} 已失效（页面变化中）: {msg}",
                                     locator=locator, cause=error)
        if "not visible" in low or "not enabled" in low or "intercepts pointer events" in low \
                or "not editable" in low or "outside of the viewport" in low:
            return ElementNotInteractableError(f"{operation}: 元素 {where} 不可操作: {msg}",
                                               locator=locator, cause=error)
        return DriverError(f"{operation}失败: {where}: {msg}", locator=locator, cause=error)

    def _element_action(self, operation: str, locator: str, fn, frame: Optional[str] = None,
                        timeout_ms: Optional[float] = None) -> bool:
        """在元素上执行一次动作 fn(locator_obj, timeout_ms)，失败抛转换后的异常。"""
        self._check_driver_alive()
        self._ensure_browser()
        timeout = self._action_timeout_ms(timeout_ms)
        try:
            fn(self._element(locator, frame), timeout)
            logger.debug(f"{operation}成功: {locator}" + (f"（frame={frame}）" if frame else ""))
            return True
        except Exception as e:
            raise self._translate_error(operation, locator, e, frame) from e

    def probe(self, locator: str, frame: Optional[str] = None) -> bool:
        """即时探测元素当前是否存在（不等待）。"""
        self._check_driver_alive()
        self._ensure_browser()
        try:
            return self._verify_scope(frame).locator(self._convert_locator(locator)).count() > 0
        except Exception as e:
            raise self._translate_error("查找", locator, e, frame) from e

    def click_locator(self, locator: str, frame: Optional[str] = None,
                      timeout_ms: Optional[float] = None, **kwargs) -> bool:
        """点击元素：Playwright 等待可见 / 稳定 / 可用 / 未被遮挡，上限为 timeout_ms（默认 AutoWait）。"""
        return self._element_action("点击", locator, lambda el, t: el.click(timeout=t, **kwargs),
                                    frame, timeout_ms)

    def type_locator(self, locator: str, text: str, frame: Optional[str] = None,
                     timeout_ms: Optional[float] = None, **kwargs) -> bool:
        """输入文本（fill：先清空再输入），等待可编辑，上限为 timeout_ms（默认 AutoWait）。"""
        return self._element_action("输入", locator, lambda el, t: el.fill(text, timeout=t, **kwargs),
                                    frame, timeout_ms)

    def type(self, locator: str, text: str) -> bool:
        """输入文本（KeywordEngine 旧 API）"""
        return self.type_locator(locator, text)

    def check(self, locator: str, timeout_ms: Optional[float] = None, **kwargs) -> bool:
        """检查元素可见（等待上限 AutoWait）；不可见返回 False。"""
        self._check_driver_alive()
        self._ensure_browser()
        try:
            self._element(locator).wait_for(state="visible", timeout=self._action_timeout_ms(timeout_ms))
            return True
        except Exception as e:
            err = self._translate_error("检查", locator, e)
            if isinstance(err, (DriverStoppedError,)):
                raise err from e
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
        self._ensure_browser()

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
        """截图（超时 SCREENSHOT_TIMEOUT_MS，失败返回 False 不阻塞）"""
        self._check_driver_alive()
        self._ensure_browser()

        try:
            self.page.screenshot(path=path, timeout=self.SCREENSHOT_TIMEOUT_MS)
            logger.debug(f"截图成功: {path}")
            return True
        except Exception as e:
            self._handle_error("screenshot", path, e)
            return False

    def select(self, locator: str, value: str, frame: Optional[str] = None,
               timeout_ms: Optional[float] = None) -> bool:
        """下拉选择：等待元素可用且目标选项出现，上限为 timeout_ms（默认 AutoWait）。"""
        return self._element_action("选择", locator, lambda el, t: el.select_option(value, timeout=t),
                                    frame, timeout_ms)

    def hover_locator(self, locator: str, frame: Optional[str] = None,
                      timeout_ms: Optional[float] = None) -> bool:
        """悬停（通过定位器），上限为 timeout_ms（默认 AutoWait）。"""
        return self._element_action("悬停", locator, lambda el, t: el.hover(timeout=t), frame, timeout_ms)

    def drag(self, from_loc: str, to_loc: str, timeout_ms: Optional[float] = None) -> bool:
        """拖拽：两端元素均需可操作，上限为 timeout_ms（默认 AutoWait）。"""
        return self._element_action(
            "拖拽", from_loc, lambda el, t: el.drag_to(self._element(to_loc), timeout=t), None, timeout_ms)

    def scroll_page(self, x: int = 0, y: int = 300) -> bool:
        """滚动页面（通过像素距离）"""
        self._check_driver_alive()
        self._ensure_browser()

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

    def assert_element(self, locator: str, expected: str, timeout_ms: Optional[float] = None) -> bool:
        """断言元素文本包含预期值（元素出现等待上限 AutoWait）"""
        self._check_driver_alive()
        self._ensure_browser()
        try:
            text = self._element(locator).text_content(timeout=self._action_timeout_ms(timeout_ms)) or ""
        except Exception as e:
            raise self._translate_error("断言", locator, e) from e
        if expected in text:
            logger.debug(f"断言成功: {locator} 包含 '{expected}'")
            return True
        logger.warning(f"断言失败: {locator} 文本 '{text}' 不包含 '{expected}'")
        return False

    def clear(self, locator: str, frame: Optional[str] = None, timeout_ms: Optional[float] = None) -> bool:
        """清空输入框，上限为 timeout_ms（默认 AutoWait）。"""
        return self._element_action("清空", locator, lambda el, t: el.fill("", timeout=t), frame, timeout_ms)

    def double_click_locator(self, locator: str, frame: Optional[str] = None,
                             timeout_ms: Optional[float] = None) -> bool:
        """双击（通过定位器），上限为 timeout_ms（默认 AutoWait）。"""
        return self._element_action("双击", locator, lambda el, t: el.dblclick(timeout=t), frame, timeout_ms)

    def right_click_locator(self, locator: str, frame: Optional[str] = None,
                            timeout_ms: Optional[float] = None) -> bool:
        """右键点击（通过定位器），上限为 timeout_ms（默认 AutoWait）。"""
        return self._element_action("右键点击", locator,
                                    lambda el, t: el.click(button="right", timeout=t), frame, timeout_ms)

    def key_press(self, key: str) -> bool:
        """按键"""
        self._check_driver_alive()
        self._ensure_browser()
        
        try:
            self.page.keyboard.press(key)
            return True
        except Exception as e:
            self._handle_error("key_press", key, e)
            raise DriverError(f"按键失败: {key}", cause=e)

    def get_text_locator(self, locator: str, frame: Optional[str] = None,
                         timeout_ms: Optional[float] = None) -> Optional[str]:
        """获取元素文本（通过定位器）；frame（v11.6.0）指定所在 iframe，">>" 串联多层。

        - verify 轮询期间（instant reads）：元素不在 DOM 中立即返回 None，不等待；
        - 其余：等待元素出现，上限为 timeout_ms（默认 AutoWait），失败抛转换后的异常。
        """
        self._check_driver_alive()
        self._ensure_browser()
        if getattr(self, "_instant_reads", False):
            # v11.6.0 (A2): 总等待只由 DefaultValue.AutoWait（自动等待）的 verify 轮询控制（CORE §4.6.5）
            try:
                loc = self._verify_scope(frame).locator(self._convert_locator(locator))
                if loc.count() == 0:
                    return None
                return loc.first.text_content(timeout=self.INSTANT_READ_TIMEOUT_MS)
            except Exception as e:
                raise self._translate_error("读取文本", locator, e, frame) from e
        try:
            return self._element(locator, frame).text_content(
                timeout=self._action_timeout_ms(timeout_ms))
        except Exception as e:
            raise self._translate_error("读取文本", locator, e, frame) from e

    # v11.6.0 (A2): 无等待读取模式下，元素已计数存在后读取文本的兜底超时（毫秒；防止读取瞬间元素被移除时挂起）
    INSTANT_READ_TIMEOUT_MS = 500

    def set_instant_reads(self, enabled: bool) -> None:
        """v11.6.0 (A2): 开/关无等待读取模式（verify 轮询期间开启，结束后关闭）。"""
        self._instant_reads = bool(enabled)

    # ── v11.6.0 (A1) 原生断言：元素数量 / 可见性 / 页面属性 ─────────────

    def _verify_scope(self, frame: Optional[str] = None):
        """返回断言读取的作用域：顶层 page，或按 frame（CSS，">>" 串联多层）进入 iframe。"""
        scope = self.page
        if frame:
            for part in (p.strip() for p in str(frame).split(">>")):
                if part:
                    scope = scope.frame_locator(part)
        return scope

    def count_elements(self, locator: str, frame: Optional[str] = None) -> int:
        """返回选择器当前匹配的元素数量（不等待；0 匹配返回 0，供 $count/$exists 判定）。"""
        self._check_driver_alive()
        self._ensure_browser()
        try:
            return int(self._verify_scope(frame).locator(locator).count())
        except Exception as e:
            # 选择器语法错误等不能按 0 处理（否则 {"$count": 0} 会假绿）
            self._handle_error("count_elements", locator, e)
            raise DriverError(f"统计元素数量失败: {locator}", locator=locator, cause=e)

    def is_element_visible(self, locator: str, frame: Optional[str] = None) -> bool:
        """元素是否可见（不等待；未匹配到元素视为不可见，多个匹配时任一可见即为可见）。"""
        self._check_driver_alive()
        self._ensure_browser()
        try:
            loc = self._verify_scope(frame).locator(locator)
            return any(loc.nth(i).is_visible() for i in range(loc.count()))
        except Exception as e:
            self._handle_error("is_element_visible", locator, e)
            raise DriverError(f"读取元素可见性失败: {locator}", locator=locator, cause=e)

    def get_page_property(self, name: str) -> Optional[str]:
        """读取页面级属性（<location type="page">）：url / title / path / dialog。

        dialog 返回最近一次原生弹窗的文本（由弹窗处理逻辑写入 ``_last_dialog_text``），
        从未出现弹窗时返回 None。
        """
        from urllib.parse import urlparse
        self._check_driver_alive()
        if name == "dialog":
            getter = getattr(self, "get_last_dialog_text", None)
            if callable(getter):
                return getter()
            return getattr(self, "_last_dialog_text", None)
        self._ensure_browser()
        if name == "url":
            return self.page.url
        if name == "path":
            return urlparse(self.page.url).path
        if name == "title":
            return self.page.title()
        raise DriverError(f"不支持的 page 属性: {name}（只能是 url / title / path / dialog）")

    # ── v11.6.0 (C1) 原生弹窗 alert / confirm / prompt ─────────────────

    DIALOG_POLICIES = ("accept", "dismiss", "fail")

    def set_dialog_policy(self, policy: str) -> None:
        """设置未注册一次性处理器时的全局弹窗策略（DefaultValue.DialogPolicy）。"""
        value = str(policy or "fail").strip().lower()
        if value not in self.DIALOG_POLICIES:
            raise DriverError(
                f"DialogPolicy 只能是 accept / dismiss / fail，得到: '{policy}'"
            )
        self._dialog_policy = value

    def register_dialog_handler(self, action: str, prompt_text: Optional[str] = None) -> None:
        """为下一次出现的弹窗注册一次性处理器（type 批量中 page=dialog 字段）。

        action: accept / dismiss；prompt_text 仅对 accept 有效（prompt 输入值）。
        """
        action = str(action or "").strip().lower()
        if action not in ("accept", "dismiss"):
            raise DriverError(f"弹窗一次性处理只能是 accept / dismiss，得到: '{action}'")
        if action == "dismiss":
            prompt_text = None
        self._check_driver_alive()
        self._ensure_browser()
        self._dialog_once = (action, prompt_text)
        logger.debug(f"已为下一次弹窗注册一次性处理: {action}"
                     + (f" (输入 '{prompt_text}')" if prompt_text is not None else ""))

    def get_last_dialog_text(self) -> Optional[str]:
        """最近一次出现的原生弹窗文本；从未出现弹窗时返回 None。"""
        return self._last_dialog_text

    def consume_unexpected_dialog(self) -> Optional[str]:
        """取出并清除 DialogPolicy=fail 下出现的未预期弹窗文本（无则返回 None）。"""
        text, self._unexpected_dialog = self._unexpected_dialog, None
        return text

    def reset_case_dialog_state(self) -> None:
        """用例开始时清除上一个用例遗留的弹窗状态（CORE §2.5.6 第 4 条）：
        未用上的一次性处理器、最近弹窗文本、未预期弹窗记录。驱动跨用例复用时必须调用。"""
        self._dialog_once = None
        self._last_dialog_text = None
        self._unexpected_dialog = None

    def _ensure_dialog_handler(self) -> None:
        """在当前 page 上挂接弹窗监听（幂等；page 重建后重新挂接）。"""
        page = self.page
        if page is None or self._dialog_hooked_page is page:
            return
        try:
            page.on("dialog", self._on_dialog)
            self._dialog_hooked_page = page
        except Exception as e:
            logger.debug(f"挂接弹窗监听失败（忽略）: {e}")

    def _on_dialog(self, dialog) -> None:
        """弹窗事件：优先使用一次性处理器，否则按全局策略；fail 时关闭弹窗并记录，由步骤报错。"""
        message = ""
        dialog_type = ""
        try:
            message = dialog.message
            dialog_type = dialog.type
        except Exception:
            pass
        self._last_dialog_text = message
        pending, self._dialog_once = self._dialog_once, None
        if pending is not None:
            action, prompt_text = pending
        else:
            action, prompt_text = self._dialog_policy, None
        handled = False
        try:
            if action == "accept":
                if prompt_text is not None:
                    dialog.accept(prompt_text)
                else:
                    dialog.accept()
                handled = True
                logger.info(f"弹窗[{dialog_type}] '{message}' → accept")
            elif action == "dismiss":
                dialog.dismiss()
                handled = True
                logger.info(f"弹窗[{dialog_type}] '{message}' → dismiss")
            else:
                # DialogPolicy=fail：先关闭弹窗避免页面卡住，再由当前步骤报错
                self._unexpected_dialog = f"[{dialog_type}] {message}" if dialog_type else message
                logger.error(f"出现未预期的弹窗[{dialog_type}]: '{message}'（DialogPolicy=fail）")
        except Exception as e:
            # 事件回调里不能抛出（会打断 Playwright 事件分发）；兜底关闭弹窗
            logger.warning(f"处理弹窗 '{message}' 失败，改为关闭: {e}")
        finally:
            if not handled:
                try:
                    dialog.dismiss()
                except Exception as e:
                    logger.debug(f"关闭弹窗失败（忽略）: {e}")

    def upload_file(self, locator: str, file_path: str, timeout_ms: Optional[float] = None) -> bool:
        """上传文件：等待 file input 出现，上限为 timeout_ms（默认 AutoWait）。"""
        return self._element_action("上传文件", locator,
                                    lambda el, t: el.set_input_files(file_path, timeout=t), None, timeout_ms)

    def get_page_text(self) -> str:
        """获取页面所有文本内容"""
        self._check_driver_alive()
        self._ensure_browser()
        try:
            return self.page.inner_text('body')
        except Exception as e:
            logger.warning(f"获取页面文本失败: {e}")
            return ""

    def get_cookies(self, domain: str = "") -> dict:
        """获取浏览器 cookies，返回 {name: value} 字典

        Args:
            domain: 可选，只获取指定域名的 cookies
        """
        if self.browser is None or not self.page:
            return {}
        try:
            context = self.page.context
            cookies = context.cookies()
            result = {}
            for c in cookies:
                if domain and domain not in c.get("domain", ""):
                    continue
                result[c["name"]] = c["value"]
            return result
        except Exception as e:
            logger.warning(f"获取 cookies 失败: {e}")
            return {}

    # ── v11.6.0 (P3) 登录态复用：save_auth_state / use_auth_state ──────────

    def get_storage_state(self) -> dict:
        """返回当前 context 的 storage state（cookies + 各 origin 的 localStorage）。"""
        self._check_driver_alive()
        if self.page is None:
            raise DriverError("当前没有打开的页面，无法读取登录态（请在登录成功、close 之前调用 save_auth_state）")
        return self.page.context.storage_state()

    def apply_storage_state(self, state: dict) -> None:
        """把已保存的 storage state 加载到当前用例的 context（须在 navigate 之前）。

        cookie 直接写入 context；localStorage 通过 init script 在首次进入对应 origin 时写入
        （每个标签页只写一次，不覆盖应用后续的修改）。不重建 context，因此与按 context
        分段的用例录像兼容。
        """
        self._check_driver_alive()
        self._ensure_browser()
        url = ""
        try:
            url = self.page.url or ""
        except Exception:
            url = ""
        if url and url != "about:blank":
            raise DriverError(
                f"use_auth_state 必须在本用例的 navigate 之前调用（当前页面已打开 {url}）。"
                f"修复: 把 run use_auth_state(...) 放到 pre_process 的第一步，并确保上一用例已 close；"
                f"SessionMode=shared_session 下用例间本就共用会话，无需 use_auth_state"
            )
        try:
            from ..builtin_ops.auth_state_ops import build_local_storage_init_script
        except ImportError:
            from builtin_ops.auth_state_ops import build_local_storage_init_script
        context = self.page.context
        cookies = list((state or {}).get("cookies") or [])
        if cookies:
            context.add_cookies(cookies)
        origins = list((state or {}).get("origins") or [])
        if origins:
            context.add_init_script(build_local_storage_init_script(origins))

    def start_case_recording(self, output_dir: str, case_id: str, target_path: str, video_size: str = None) -> Optional[str]:
        if self._is_closed:
            return None
        self._ensure_browser()
        record_dir = Path(output_dir)
        record_dir.mkdir(parents=True, exist_ok=True)
        self._recording_target_path = Path(target_path)
        self._recording_target_path.parent.mkdir(parents=True, exist_ok=True)
        self._recording_saved_path = None

        try:
            # 在关闭旧 page 之前，先测量有界面浏览器的真实内容区尺寸（CSS 像素）。
            # headed + no_viewport=True 时 page.viewport_size 通常为 None；若回退到屏幕
            # 可用区尺寸，录制画布会比网页内容区高出标签栏/地址栏的高度，底部出现灰带。
            content_size = None
            use_screen_size = (not video_size) or str(video_size).strip().lower() == "screen"
            if not self.headless and use_screen_size and self.browser is not None:
                measure_page = self.page
                temp_page = None
                try:
                    if measure_page is None:
                        temp_page = self.browser.new_page(no_viewport=True)
                        measure_page = temp_page
                    if measure_page is not None:
                        inner = measure_page.evaluate(
                            "()=>({width:Math.round(window.innerWidth),"
                            "height:Math.round(window.innerHeight)})"
                        )
                        if inner and inner.get("width") and inner.get("height"):
                            content_size = {
                                "width": int(inner["width"]),
                                "height": int(inner["height"]),
                            }
                except Exception:
                    content_size = None
                finally:
                    if temp_page is not None:
                        try:
                            temp_page.close()
                        except Exception:
                            pass

            if self.page is not None:
                try:
                    self.page.close()
                except Exception:
                    pass
            if self.context is not None:
                try:
                    self.context.close()
                except Exception:
                    pass

            context_options = {"record_video_dir": str(record_dir)}
            # 动态确定录制分辨率，使录像与页面内容完全匹配
            if video_size and str(video_size).strip().lower() != "screen":
                # 用户显式指定了分辨率（hd/2k/WxH），尊重用户设置
                resolved_size = _resolve_video_size(video_size)
            else:
                # 默认：有界面模式优先使用真实内容区尺寸；失败再回退到 viewport/screen。
                resolved_size = content_size
                if resolved_size is None and self.page is not None:
                    try:
                        vp = self.page.viewport_size
                        if vp and vp.get("width") and vp.get("height"):
                            resolved_size = {"width": vp["width"], "height": vp["height"]}
                    except Exception:
                        pass
                if resolved_size is None:
                    resolved_size = _resolve_video_size("screen")
            context_options["record_video_size"] = resolved_size
            if self.headless:
                # 无头模式没有真实窗口，固定 viewport 即录制分辨率，不会闪屏
                context_options["viewport"] = resolved_size
            else:
                # 有界面模式：给录制上下文设置固定 viewport 会让 Chromium 进入设备模拟
                # (Emulation.setDeviceMetricsOverride，dpr 被强制为 1)，把模拟画面持续
                # 缩放适配真实的最大化窗口，叠加每步自动截图后产生肉眼可见的闪屏/抖动。
                # 改用 no_viewport 保留原生窗口（dpr/尺寸与系统一致），录制分辨率仍由
                # record_video_size 独立控制，视频尺寸不变。
                context_options["no_viewport"] = True
            self.context = self.browser.new_context(**context_options)
            self._recording_context = self.context
            self.page = self.context.new_page()
            self._recording_video = getattr(self.page, "video", None)
            logger.info(f"Playwright 原生录制已启动: {self._recording_target_path} (分辨率: {resolved_size})")
            return str(self._recording_target_path)
        except Exception as e:
            logger.warning(f"Playwright 原生录制启动失败: {e}")
            self._recording_context = None
            self._recording_video = None
            self._recording_target_path = None
            return None

    def stop_case_recording(self, case_id: str = "", target_path: Optional[str] = None) -> Optional[str]:
        if self._recording_saved_path:
            return self._recording_saved_path
        if target_path:
            self._recording_target_path = Path(target_path)
        return self._finalize_case_recording()

    def _finalize_case_recording(self) -> Optional[str]:
        if self._recording_saved_path:
            return self._recording_saved_path
        if not self._recording_target_path:
            return None

        target_path = self._recording_target_path
        video = self._recording_video or getattr(self.page, "video", None)
        try:
            if self.page is not None:
                try:
                    self.page.close()
                except Exception:
                    pass
                self.page = None
            if self._recording_context is not None:
                try:
                    self._recording_context.close()
                except Exception:
                    pass
                if self.context is self._recording_context:
                    self.context = None
            if video is not None:
                original_path = None
                try:
                    original_path = Path(video.path())
                except Exception:
                    pass
                video.save_as(str(target_path))
                self._cleanup_original_recording(original_path, target_path)
            self._recording_saved_path = str(target_path)
            logger.info(f"Playwright 原生录制已保存: {target_path}")
            return self._recording_saved_path
        except Exception as e:
            logger.warning(f"Playwright 原生录制保存失败: {e}")
            return None
        finally:
            self._recording_context = None
            self._recording_video = None
            self._recording_target_path = None

    @staticmethod
    def _cleanup_original_recording(original_path: Optional[Path], target_path: Path) -> None:
        if not original_path:
            return
        try:
            if original_path.exists() and original_path.resolve() != target_path.resolve():
                original_path.unlink()
        except Exception as e:
            logger.debug(f"清理 Playwright 原始录制文件失败: {e}")

    def start_js_coverage(self) -> bool:
        """开启 JS 覆盖率采集（基于 Chrome DevTools Protocol 的 Profiler domain）。

        注意：Python 版 Playwright 未提供 JS 版独有的 `page.coverage` 封装
        （见 https://github.com/microsoft/playwright/issues/10137），因此这里
        直接通过 `context.new_cdp_session` 驱动底层 CDP 协议
        （Profiler.enable / Debugger.enable / Profiler.startPreciseCoverage），
        效果与 JS 版 `page.coverage.startJSCoverage()` 一致。

        仅 Chromium 支持该能力（Firefox/WebKit 无对应 CDP 接口）。若浏览器尚未启动，
        会先触发 `_ensure_browser` 懒加载启动；若当前浏览器不是 chromium，
        记录 warning 日志并返回 False，不抛出异常。

        Returns:
            True 表示已成功开始采集；False 表示不支持或启动失败。
        """
        if self.browser_name != "chromium":
            logger.warning(
                f"JS 覆盖率采集仅支持 chromium，当前浏览器: {self.browser_name}，已跳过"
            )
            return False

        self._ensure_browser()
        if self.page is None:
            logger.warning("JS 覆盖率采集启动失败: page 未初始化")
            return False

        try:
            cdp = self.page.context.new_cdp_session(self.page)
            cdp.send("Profiler.enable")
            cdp.send("Debugger.enable")
            cdp.send("Profiler.startPreciseCoverage", {"callCount": True, "detailed": True})
            self._coverage_cdp_session = cdp
            self._coverage_started = True
            logger.debug("JS 覆盖率采集已开始 (CDP Profiler)")
            return True
        except Exception as e:
            logger.warning(f"JS 覆盖率采集启动失败: {e}")
            return False

    @staticmethod
    def _coverage_ranges_to_disjoint(nested_ranges: list) -> list:
        """将 V8 嵌套的函数级覆盖 range 转换为字节级不重叠 range 列表。

        复刻 Playwright JS 版 `convertToDisjointRanges` 的扫描线算法：
        CDP `Profiler.takePreciseCoverage` 返回的 range 按函数嵌套（父函数
        range 包含子函数 range），需要展平为按 count>0 合并的不重叠区间，
        才能与 JS 版 `page.coverage.stopJSCoverage()` 的 `ranges` 字段等价。

        Args:
            nested_ranges: 同一脚本内所有函数的 range 列表，每项含
                startOffset/endOffset/count

        Returns:
            list[dict]: 不重叠 range 列表，每项 {"start": int, "end": int}，
                仅包含 count > 0（即被执行到）的区间
        """
        points = []
        for r in nested_ranges:
            points.append((r["startOffset"], 0, r))
            points.append((r["endOffset"], 1, r))

        def sort_key(point):
            offset, kind, r = point
            length = r["endOffset"] - r["startOffset"]
            return (offset, kind, -length if kind == 0 else length)

        points.sort(key=sort_key)

        hit_stack: list = []
        merged: list = []
        last_offset = 0
        for offset, kind, r in points:
            if hit_stack and last_offset < offset and hit_stack[-1] > 0:
                if merged and merged[-1]["end"] == last_offset:
                    merged[-1]["end"] = offset
                else:
                    merged.append({"start": last_offset, "end": offset})
            last_offset = offset
            if kind == 0:
                hit_stack.append(r["count"])
            else:
                hit_stack.pop()

        return [r for r in merged if r["end"] > r["start"]]

    def _capture_coverage_snapshot(self) -> list:
        """通过 CDP 取一次覆盖率快照（不改动 `_coverage_started` 状态位）。

        供 `stop_js_coverage()` 和 `close()` 共用：case 的 `post_process` 常以
        `close` 结束用例，浏览器可能在 CLI 层调用 `stop_js_coverage()` 之前就
        已经关闭（此时 CDP session 早已失效），因此 `close()` 会在真正关闭浏览器
        前调用本方法先抓一次快照缓存到 `_coverage_cached_entries`。

        Returns:
            list[dict]: [{"url": str, "source": str, "ranges": [...]}, ...]；
                失败或 cdp 不可用时返回 []
        """
        cdp = self._coverage_cdp_session
        if cdp is None:
            return []

        try:
            raw = cdp.send("Profiler.takePreciseCoverage")
            script_coverages = raw.get("result", []) or []

            entries = []
            for script_cov in script_coverages:
                url = script_cov.get("url") or ""
                if not url:
                    continue
                script_id = script_cov.get("scriptId")
                try:
                    src_result = cdp.send("Debugger.getScriptSource", {"scriptId": script_id})
                    source = src_result.get("scriptSource", "") or ""
                except Exception as e:
                    logger.debug(f"覆盖率: 获取脚本源码失败 (url={url}): {e}")
                    continue

                nested_ranges = [
                    rr for fn in script_cov.get("functions", []) or [] for rr in fn.get("ranges", [])
                ]
                ranges = self._coverage_ranges_to_disjoint(nested_ranges)
                entries.append({"url": url, "source": source, "ranges": ranges})

            return entries
        except Exception as e:
            logger.warning(f"JS 覆盖率快照采集失败: {e}")
            return []

    def stop_js_coverage(self) -> list:
        """停止 JS 覆盖率采集并返回覆盖率数据。

        返回格式与 JS 版 `page.coverage.stopJSCoverage()` 一致：

            [{"url": str, "source": str, "ranges": [{"start": int, "end": int}, ...]}, ...]

        若 `close()` 已先于本方法被调用（浏览器已关闭），直接返回 `close()` 时
        缓存的快照；否则实时通过 CDP 取快照。

        若未曾调用 start_js_coverage 成功开启过采集、当前浏览器非 chromium，
        或 page 不可用，均返回空列表，不抛出异常。

        Returns:
            list[dict]: 覆盖率数据；不支持或未开启时为 []
        """
        if not self._coverage_started:
            return self._coverage_cached_entries or []

        try:
            if self._coverage_cached_entries is not None:
                # close() 已抓取过快照（浏览器可能已关闭），直接复用
                return self._coverage_cached_entries

            if self.browser_name != "chromium" or self.page is None or self._coverage_cdp_session is None:
                return []

            entries = self._capture_coverage_snapshot()
            try:
                self._coverage_cdp_session.send("Profiler.stopPreciseCoverage")
            except Exception:
                pass
            return entries
        finally:
            self._coverage_started = False
            self._coverage_cdp_session = None
            self._coverage_cached_entries = None

    def close(self) -> None:
        """关闭驱动"""
        if self._is_closed:
            return

        self._is_closed = True
        self._finalize_case_recording()
        # 覆盖率采集仍在进行中：case 的 post_process 常以 close 结束用例，
        # 此时需在浏览器真正关闭前抓一次快照缓存，否则 stop_js_coverage()
        # 拿到的 CDP session 已随浏览器关闭失效
        if self._coverage_started and self._coverage_cdp_session is not None:
            self._coverage_cached_entries = self._capture_coverage_snapshot()
        if self.attached:
            # CDP 附加模式：本 driver 不拥有浏览器。browser.close() 在
            # connect_over_cdp 语义下仅是断连；绝不关闭远端 context/页面，
            # 否则会毁掉上一个 run / Agent 保留的状态（见 _attach_cdp_browser）。
            try:
                if self.browser:
                    self.browser.close()
            except Exception as e:
                logger.debug(f"断开 CDP 浏览器时出错: {e}")
            try:
                if self._pw:
                    self._pw.stop()
            except Exception as e:
                logger.debug(f"停止 Playwright 时出错: {e}")
            return
        if getattr(self, "_shared_browser", None) is not None:
            # SessionMode=shared_browser：只关闭本用例的 context（cookie/storage/页面随之销毁），
            # 浏览器进程由执行器在 run 结束时统一关闭（SharedBrowser.close）。
            contexts = []
            if self.context is not None:
                contexts.append(self.context)
            try:
                if self.page is not None and self.page.context not in contexts:
                    contexts.append(self.page.context)
            except Exception:
                pass
            for ctx in contexts:
                try:
                    ctx.close()
                except Exception as e:
                    logger.debug(f"关闭浏览器上下文时出错: {e}")
            self.page = None
            self.context = None
            self.browser = None
            return
        try:
            if self.context:
                self.context.close()
        except Exception as e:
            logger.debug(f"关闭浏览器上下文时出错: {e}")
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