"""Appium 移动端自动化驱动基类"""
from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
from typing import Any, Callable, Dict, Optional, Tuple
from .base_driver import BaseDriver
try:
    from ..core import auto_wait as _aw
    from ..core.exceptions import (
        DriverError, DriverStoppedError, ElementNotFoundError, ElementNotInteractableError,
        StaleElementError, TimeoutError as DriverTimeoutError, is_critical_error,
    )
except ImportError:  # pragma: no cover - 以 rodski/ 为根运行
    from core import auto_wait as _aw
    from core.exceptions import (
        DriverError, DriverStoppedError, ElementNotFoundError, ElementNotInteractableError,
        StaleElementError, TimeoutError as DriverTimeoutError, is_critical_error,
    )
import time
import logging

logger = logging.getLogger("rodski")

_VISION_TYPES = {"vision", "ocr", "vision_bbox"}

# `am start` 失败时 stderr 里的标记。用它而不是裸的 "Error" 子串：`am start` 在
# 「目标 Activity 已在最前」时会打 `Warning: Activity not started, ...` 且 exit=0，
# 那是正常情况，宽判据会把成功的启动误判成失败。
_AM_START_FAILURE_MARKERS = (
    "Error type",              # Error type 3 / Error type 1（Activity/包不存在）
    "does not exist",
    "Permission Denial",
    "SecurityException",
    "Exception occurred while executing",
)

# 定位器类型到 AppiumBy 的映射
_LOCATOR_MAP = {
    "id":    AppiumBy.ID,
    "name":  AppiumBy.ACCESSIBILITY_ID,
    "class": AppiumBy.CLASS_NAME,
    "xpath": AppiumBy.XPATH,
    "text":  None,  # 特殊处理：构造 XPath
    "css":   AppiumBy.CSS_SELECTOR,  # 仅 WebView 上下文
    "accessibility_id": AppiumBy.ACCESSIBILITY_ID,
}

# Android keycode 映射
_ANDROID_KEYCODES = {
    "BACK": 4, "HOME": 3, "ENTER": 66, "DELETE": 67,
    "MENU": 82, "SEARCH": 84, "VOLUME_UP": 24, "VOLUME_DOWN": 25,
    "TAB": 61, "ESCAPE": 111,
}


class AppiumDriver(BaseDriver):
    """Appium 驱动基类，支持 Android 和 iOS"""

    def __init__(self, capabilities: dict = None, server_url: str = "http://localhost:4723", options=None,
                 udid: str = None):
        logger.info(f"初始化 Appium 驱动: server={server_url}")
        if options is not None:
            self.driver = webdriver.Remote(server_url, options=options)
        else:
            self.driver = webdriver.Remote(server_url, capabilities)
        # v11.7.0: 元素等待统一由 DefaultValue.AutoWait（公共层 core/auto_wait.py）控制。
        # 显式关闭 implicit wait，避免与自动等待叠加（每次查找都额外阻塞）。
        try:
            self.driver.implicitly_wait(0)
        except Exception as e:  # pragma: no cover - 个别 server 不支持
            logger.debug(f"implicitly_wait(0) 设置失败（忽略）: {e}")
        # 目标设备标识（Android = adb serial，iOS = UDID）。Appium 自己用它选设备，
        # 但驱动内的 adb 直调（start_app）必须自己带上，否则多设备时 adb 直接拒绝执行。
        self.udid = udid
        # 录像后端标识：供 SKIExecutor._select_recording_backend 区分驱动类型
        self.recording_backend = "appium"
        # 录像状态
        self._recording_active = False
        self._recording_target_path: Optional[str] = None
        logger.info("Appium 驱动初始化成功")

    def launch(self, **kwargs) -> None:
        """启动应用"""
        pass

    def close(self) -> None:
        if self.driver:
            logger.info("关闭 Appium 驱动")
            self.driver.quit()

    def locate_element(self, locator_type: str, locator_value: str) -> Optional[Tuple[int, int, int, int]]:
        """定位元素，按 locator_type 映射到正确的 AppiumBy"""
        if locator_type.lower() in _VISION_TYPES:
            return self._locate_with_vision(locator_type, locator_value)
        try:
            by, value = self._resolve_locator(locator_type, locator_value)
            element = self.driver.find_element(by, value)
            rect = element.rect
            bbox = (rect['x'], rect['y'], rect['x'] + rect['width'], rect['y'] + rect['height'])
            logger.debug(f"元素定位成功: {locator_type}={locator_value}, bbox={bbox}")
            return bbox
        except Exception as e:
            logger.warning(f"元素定位失败: {locator_type}={locator_value}, error={e}")
            return None

    def _locate_with_vision(self, locator_type: str, locator_value: str) -> Optional[Tuple[int, int, int, int]]:
        """视觉定位：优先 Accessibility Tree 匹配，降级到 PerceptionBackend / OCR / bbox。

        v7.1.0 起：``vision`` 通过 ``PerceptionRegistry`` 取 backend；
        backend 不可用时抛 ``PerceptionUnavailableError``（含安装指引），
        不再被 except 吞掉。
        """
        import tempfile, os
        # 先尝试 Accessibility Tree 文本匹配（快速路径，仅对自然语言描述类有意义）
        if locator_type.lower() == "vision":
            tree_bbox = self._locate_by_accessibility_tree(locator_value)
            if tree_bbox:
                return tree_bbox
        # 降级到截图 + VisionLocator（vision 经 PerceptionBackend；ocr / vision_bbox 走内置实现）
        from rodski.vision.locator import VisionLocator
        from rodski.vision.perception_interface import PerceptionUnavailableError
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.close()
        try:
            self.driver.save_screenshot(tmp.name)
            locator = VisionLocator(getattr(self, '_cfg', None))
            return locator.locate(locator_type.lower(), locator_value, tmp.name)
        except PerceptionUnavailableError:
            # 明确的 perception 不可用错误必须向上传播，让用例失败信息清晰
            raise
        except Exception as e:
            logger.warning(f"视觉定位失败: {locator_type}={locator_value}, error={e}")
            return None
        finally:
            os.unlink(tmp.name)

    def _locate_by_accessibility_tree(self, semantic_label: str) -> Optional[Tuple[int, int, int, int]]:
        """通过 Accessibility Tree 文本匹配定位元素"""
        try:
            tree_text, index_map = self.get_accessibility_tree()
        except Exception as e:
            logger.debug(f"获取 Accessibility Tree 失败: {e}")
            return None
        if len(index_map) < 10:
            logger.debug("Tree 节点不足 10 个，跳过 Tree 匹配")
            return None
        # 精确文本匹配
        label = semantic_label.strip().lower()
        for idx, line in enumerate(tree_text.split('\n')):
            content = line.split('>')[-1].replace('</>', '').strip().lower()
            if label in content or content in label:
                if idx in index_map:
                    logger.info(f"Accessibility Tree 匹配成功: '{semantic_label}' -> index {idx}")
                    return index_map[idx]
        return None

    def get_accessibility_tree(self) -> Tuple[str, dict]:
        """序列化 View Hierarchy，返回 (文本, {index: (x1,y1,x2,y2)})"""
        import xml.etree.ElementTree as ET
        import re
        root = ET.fromstring(self.driver.page_source)
        lines, index_map, idx = [], {}, 0
        for elem in root.iter():
            text = (elem.get('text') or elem.get('label') or
                    elem.get('content-desc') or '').strip()
            rid = (elem.get('resource-id') or elem.get('name') or '').strip()
            cls = (elem.get('class') or elem.get('type') or '').split('.')[-1]
            clickable = elem.get('clickable') == 'true'
            bounds = elem.get('bounds', '')
            if not (text or (clickable and rid)):
                continue
            nums = re.findall(r'\d+', bounds)
            if len(nums) == 4:
                index_map[idx] = tuple(int(v) for v in nums)
            lines.append(f"[{idx}]<{cls} clickable={clickable}>{text or rid}</>")
            idx += 1
        return '\n'.join(lines), index_map

    def _text_xpath(self, value):
        """text 定位器转 XPath，子类可重写（Android: @text，iOS: @label/@name）"""
        return f"//*[@text='{value}']"

    def _get_locator_map(self):
        """返回定位器类型映射，子类可重写（如 iOS: id->ACCESSIBILITY_ID）"""
        return _LOCATOR_MAP

    def _resolve_locator(self, locator_type: str, locator_value: str) -> tuple:
        """将 locator_type/locator_value 解析为 (AppiumBy, value) 元组"""
        lt = locator_type.lower()
        if lt == "text":
            xpath = self._text_xpath(locator_value)
            return AppiumBy.XPATH, xpath
        by = self._get_locator_map().get(lt)
        if by is None:
            # 未知类型回退到 ID
            logger.debug(f"未知定位器类型 '{locator_type}'，回退到 AppiumBy.ID")
            return AppiumBy.ID, locator_value
        return by, locator_value

    def get_element_text_by_locator(self, locator_type: str, locator_value: str) -> str:
        """通过定位器找到元素（即时，不等待），按优先级读取文本属性（移动端 verify / get 读取）"""
        locator = f"{locator_type}={locator_value}"
        try:
            element = self._find(locator)
        except Exception as e:
            raise self._translate_error("读取文本", locator, e) from e

        # 按优先级读取文本属性（Android: text/content-desc，iOS: label/value/name）
        for attr in ["text", "value", "label", "name", "content-desc"]:
            val = element.text if attr == "text" else element.get_attribute(attr)
            if val:
                return val

        raise ElementNotFoundError(
            f"元素文本为空: {locator_type}={locator_value}",
            locator=locator_value
        )

    # ── v11.7.0 自动等待（AutoWait）驱动契约 ─────────────────────────
    # 公共层（core/auto_wait.py）负责 "try 查找+执行 → catch 未找到/不可操作 → 等待 → 再执行"；
    # 本驱动每次调用只做一次即时查找 + 一次动作，失败按 _translate_error 抛异常（不返回 False，
    # 不内部等待，不设 implicit wait）。外部代码直接调用（未传 timeout_ms）时，驱动自己按
    # AutoWait 走同一个公共循环。

    def _split(self, locator: str) -> Tuple[str, str]:
        if "=" in locator:
            strategy, value = locator.split("=", 1)
            return strategy.strip().lower(), value
        return "id", locator

    def _translate_error(self, operation: str, locator: str, error: Exception) -> Exception:
        """Selenium / Appium 原生异常 → rodski 异常（决定自动等待是否重试）。"""
        if isinstance(error, DriverError):
            return error
        name = type(error).__name__
        msg = str(error).strip().splitlines()[0] if str(error).strip() else name
        if is_critical_error(error) or "session" in msg.lower() and ("terminated" in msg.lower()
                                                                     or "not started" in msg.lower()):
            return DriverStoppedError(f"{operation}失败: {msg}", driver_type="Appium")
        if name == "NoSuchElementException":
            return ElementNotFoundError(f"{operation}: 元素 {locator} 未找到", locator=locator, cause=error)
        if name == "StaleElementReferenceException":
            return StaleElementError(f"{operation}: 元素 {locator} 已失效", locator=locator, cause=error)
        if name in ("ElementNotInteractableException", "ElementClickInterceptedException",
                    "InvalidElementStateException", "ElementNotVisibleException"):
            return ElementNotInteractableError(f"{operation}: 元素 {locator} 不可操作: {msg}",
                                               locator=locator, cause=error)
        if name == "TimeoutException":
            return DriverTimeoutError(f"{operation}: {locator} 超时: {msg}", locator=locator, cause=error)
        return DriverError(f"{operation}失败: {locator}: {msg}", locator=locator, cause=error)

    def _find(self, locator: str):
        """即时查找一次（不等待）；未找到抛 ElementNotFoundError。"""
        strategy, value = self._split(locator)
        by, val = self._resolve_locator(strategy, value)
        elements = self.driver.find_elements(by, val)
        if not elements:
            raise ElementNotFoundError(f"元素 {locator} 未找到", locator=locator)
        return elements[0]

    def _vision_center(self, locator: str) -> Tuple[int, int]:
        strategy, value = self._split(locator)
        bbox = self._locate_with_vision(strategy, value)
        if not bbox:
            raise ElementNotFoundError(f"视觉定位未匹配: {locator}", locator=locator)
        return (bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2

    def _attempt(self, operation: str, locator: str, fn: Callable[[], Any],
                 timeout_ms: Optional[float] = None) -> Any:
        """执行一次 fn()（原生异常转换后抛出）。

        timeout_ms 为 None（外部直接调用、未经关键字层）时，按 AutoWait 走公共自动等待循环。
        """
        def once():
            try:
                return fn()
            except Exception as e:
                raise self._translate_error(operation, locator, e) from e

        if timeout_ms is not None:
            return once()
        _, result = _aw.run_element(
            locator, [locator], probe=lambda _l: True, act=lambda _l, _h, _d: once(),
            deadline=_aw.Deadline(self.get_auto_wait()),
            interval_s=_aw.poll_interval_for([self._split(locator)[0]]),
        )
        return result

    def probe(self, locator: str, frame: Optional[str] = None) -> bool:
        """即时探测元素当前是否存在（find_elements，不等待；视觉定位器每次新截图）。"""
        strategy, value = self._split(locator)
        try:
            if strategy in _VISION_TYPES:
                return self._locate_with_vision(strategy, value) is not None
            by, val = self._resolve_locator(strategy, value)
            return len(self.driver.find_elements(by, val)) > 0
        except Exception as e:
            err = self._translate_error("查找", locator, e)
            if isinstance(err, (ElementNotFoundError, StaleElementError)):
                return False
            raise err from e

    def set_instant_reads(self, enabled: bool) -> None:
        """verify 轮询期间的无等待读取开关（本驱动读取本就不等待，仅记录状态）。"""
        self._instant_reads = bool(enabled)

    def type_locator(self, locator: str, text: str, timeout_ms: Optional[float] = None, **kwargs) -> bool:
        """输入文本（通过定位器）：一次查找 + clear + send_keys；失败抛异常。"""
        def do():
            if self._split(locator)[0] in _VISION_TYPES:
                x, y = self._vision_center(locator)
                self.type_text(x, y, text)
            else:
                element = self._find(locator)
                element.clear()
                element.send_keys(text)
            logger.debug(f"type_locator 成功: {locator} <- '{text}'")
            return True
        return self._attempt("输入", locator, do, timeout_ms)



    def clear_locator(self, locator: str, timeout_ms: Optional[float] = None, **kwargs) -> bool:
        """清空输入框（通过定位器）。"""
        def do():
            self._find(locator).clear()
            return True
        return self._attempt("清空", locator, do, timeout_ms)

    def get_text_locator(self, locator: str, frame: Optional[str] = None,
                         timeout_ms: Optional[float] = None) -> Optional[str]:
        """读取元素文本（text / value / label / name / content-desc 依次取第一个非空）。"""
        strategy, value = self._split(locator)
        return self._attempt("读取文本", locator,
                             lambda: self.get_element_text_by_locator(strategy, value), timeout_ms)

    def click_locator(self, locator: str, timeout_ms: Optional[float] = None, **kwargs) -> bool:
        """点击元素（通过定位器）：一次查找 + click；失败抛异常。"""
        def do():
            if self._split(locator)[0] in _VISION_TYPES:
                x, y = self._vision_center(locator)
                self.driver.tap([(x, y)])
            else:
                self._find(locator).click()
            logger.debug(f"click_locator 成功: {locator}")
            return True
        return self._attempt("点击", locator, do, timeout_ms)

    # ── BaseDriver 坐标接口（两阶段 API）───────────────────────────

    def click(self, locator_or_x, y=None) -> bool:
        """点击元素

        支持两种调用方式：
        - click(locator_str)     → 旧 API，定位器点击
        - click(x, y)            → BaseDriver 坐标 API
        """
        if y is None and isinstance(locator_or_x, str):
            # 旧 API: click("id=test") → 定位器点击（按 AutoWait 自动等待）
            return self.click_locator(locator_or_x)
        else:
            # BaseDriver API: click(x, y) → 坐标点击
            x = locator_or_x
            logger.debug(f"点击坐标: ({x}, {y})")
            self.driver.tap([(x, y)])

    def type_text(self, x: int, y: int, text: str) -> None:
        """输入文字（先 tap 获取焦点，再通过 active_element.send_keys 输入）"""
        logger.debug(f"输入文字: ({x}, {y}), text={text}")
        self.driver.tap([(x, y)])
        time.sleep(0.3)
        try:
            active = self.driver.switch_to.active_element
            if active is not None:
                try:
                    active.clear()
                except Exception:
                    pass
                active.send_keys(text)
                return
        except Exception:
            pass
        self.driver.execute_script("mobile: type", {"text": text})

    def key_press(self, key: str) -> bool:
        """按下按键，支持 Android keycode 名称（大小写不敏感）"""
        keycode = _ANDROID_KEYCODES.get(key.upper())
        if keycode is not None:
            self.driver.press_keycode(keycode)
            return True
        logger.warning(f"未知按键: {key}，跳过")
        return False

    def start_app(self, package_or_bundle: str, activity: str = None) -> bool:
        """启动 App（Appium 2.x）

        Android: adb am start 强制跳转到指定 Activity（noReset 场景下也生效）
        iOS:     activate_app(bundle_id)

        并发约束：本类持有 Appium session，但 adb 是**独立于 session 的第二条通道**，
        它不知道 session 绑定的是哪台设备。多设备（真机 + 模拟器）同时在线时，
        不带 -s 的 adb 会直接报 `more than one device/emulator` 而拒绝执行 ——
        于是 Appium 那边会话建得好好的，只有这一个跳转静默失效。
        故必须用驱动自己的 udid 显式指定设备（self.udid 由各平台驱动写入）。
        """
        try:
            if activity:
                import subprocess
                import shutil
                adb = shutil.which("adb") or "adb"
                short = activity if activity.startswith(".") else f".{activity.split('.')[-1]}"
                cmd = [adb]
                if self.udid:
                    cmd += ["-s", self.udid]
                cmd += ["shell", "am", "start", "-n", f"{package_or_bundle}/{short}"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                # am start 的退出码不可靠：Activity 不存在时它照样返回 0，只在 stderr
                # 打印 `Error type 3`。故两条都查。判据取具体标记而非裸的 "Error"
                # ——「已在最前的 Activity 再 start」会打 `Warning: ...` 且 exit=0，
                # 那是正常情况，不能因此判失败。
                stderr = (result.stderr or "").strip()
                failed = result.returncode != 0 or any(
                    marker in stderr for marker in _AM_START_FAILURE_MARKERS
                )
                if failed:
                    logger.error(f"adb am start 失败: {stderr or result.returncode}")
                    return False
                logger.info(f"adb am start 成功: {package_or_bundle}/{short}"
                            + (f" (device={self.udid})" if self.udid else ""))
                return True
            else:
                self.driver.activate_app(package_or_bundle)
                return True
        except Exception as e:
            logger.error(f"启动 App 失败: {package_or_bundle}/{activity}, {e}")
            return False

    def get_text(self, x1: int, y1: int, x2: int, y2: int) -> str:
        """获取指定区域内元素的文字"""
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        try:
            elems = self.driver.find_elements(
                AppiumBy.XPATH, '//*[@text!="" or @content-desc!=""]'
            )
            for e in elems:
                r = e.rect
                if (r['x'] <= cx <= r['x'] + r['width'] and
                        r['y'] <= cy <= r['y'] + r['height']):
                    return e.text or e.get_attribute('content-desc') or ''
        except Exception as ex:
            logger.warning(f"get_text 失败: ({x1},{y1},{x2},{y2}), {ex}")
        return ''

    def take_screenshot(self) -> str:
        """截图"""
        import tempfile
        path = tempfile.mktemp(suffix='.png')
        self.driver.save_screenshot(path)
        return path

    def double_click(self, x: int, y: int) -> None:
        """双击"""
        self.driver.tap([(x, y)], 2)

    def right_click(self, x: int, y: int) -> None:
        """右键点击（移动端不支持）"""
        pass

    def hover(self, locator_or_x, y=None) -> bool:
        """悬停

        支持两种调用方式：
        - hover(locator_str)  → 旧 API，定位器悬停
        - hover(x, y)         → BaseDriver 坐标 API（移动端不支持，直接 pass）
        """
        if y is None and isinstance(locator_or_x, str):
            return self.hover_locator(locator_or_x)
        # 移动端悬停不支持，直接 pass

    def scroll(self, x: int, y: int) -> bool:
        """滚动（Appium 2.x W3C Actions — mobile: scrollGesture）"""
        try:
            size = self.driver.get_window_size()
            w, h = size['width'], size['height']
            cx, cy = w // 2, h // 2

            if abs(y) >= abs(x):
                direction = "down" if y > 0 else "up"
                percent = min(abs(y) / h, 0.9)
            else:
                direction = "right" if x > 0 else "left"
                percent = min(abs(x) / w, 0.9)

            self.driver.execute_script("mobile: scrollGesture", {
                "left": cx - 100, "top": cy - 200,
                "width": 200, "height": 400,
                "direction": direction,
                "percent": max(percent, 0.1)
            })
            return True
        except Exception as e:
            logger.warning(f"scroll 失败: {e}")
            return False

    # ── 旧 API（定位器接口，保留用于兼容性和测试）───────────────────

    def _parse_locator(self, locator: str) -> tuple:
        """解析 "type=value" 定位符（v11.7.0 起与 _resolve_locator 同一套映射）"""
        strategy, value = self._split(locator)
        return self._resolve_locator(strategy, value)

    def hover_locator(self, locator: str, timeout_ms: Optional[float] = None, **kwargs) -> bool:
        """通过定位器悬停（移动端用 longClick 模拟）"""
        def do():
            element = self._find(locator)
            self.driver.execute_script("mobile: longClick", {"elementId": element.id})
            return True
        return self._attempt("悬停", locator, do, timeout_ms)

    def drag(self, from_locator: str, to_locator: str, timeout_ms: Optional[float] = None) -> bool:
        """拖拽（Appium 2.x W3C Actions — mobile: dragGesture）；两端元素一次查找，失败抛异常"""
        def do():
            fr = self._find(from_locator).rect
            to = self._find(to_locator).rect
            self.driver.execute_script("mobile: dragGesture", {
                "startX": fr['x'] + fr['width'] // 2, "startY": fr['y'] + fr['height'] // 2,
                "endX": to['x'] + to['width'] // 2, "endY": to['y'] + to['height'] // 2,
            })
            return True
        return self._attempt("拖拽", f"{from_locator} -> {to_locator}", do, timeout_ms)

    def assert_element(self, locator: str, expected: str, timeout_ms: Optional[float] = None) -> bool:
        """断言元素文本（旧 API；元素出现等待上限 AutoWait）"""
        text = self._attempt("断言", locator, lambda: self._find(locator).text or "", timeout_ms)
        return expected in text

    def click_element(self, locator: str) -> bool:
        """通过定位器点击元素（旧 API）"""
        return self.click_locator(locator)

    def type(self, locator: str, text: str) -> bool:
        """通过定位器输入文字（旧 API）"""
        return self.type_locator(locator, text)

    def check(self, locator: str, timeout_ms: Optional[float] = None) -> bool:
        """检查元素是否可见（旧 API；等待上限 AutoWait）"""
        def do():
            if not self._find(locator).is_displayed():
                raise ElementNotInteractableError(f"元素 {locator} 不可见", locator=locator)
            return True
        try:
            return self._attempt("检查", locator, do, timeout_ms)
        except (ElementNotFoundError, ElementNotInteractableError, StaleElementError):
            return False

    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: int = 500) -> bool:
        """滑动操作（旧 API）"""
        try:
            self.driver.swipe(start_x, start_y, end_x, end_y, duration)
            return True
        except Exception:
            return False

    def tap(self, x: int, y: int) -> bool:
        """点击坐标（旧 API）"""
        try:
            self.driver.tap([(x, y)])
            return True
        except Exception:
            return False

    def screenshot(self, path: str = None) -> bool:
        """截图（旧 API）"""
        try:
            if path is None:
                self.take_screenshot()
            else:
                self.driver.save_screenshot(path)
            return True
        except Exception:
            return False

    def navigate(self, url: str) -> bool:
        """导航到 URL（旧 API）"""
        try:
            self.driver.get(url)
            return True
        except Exception:
            return False

    def select(self, locator: str, value: str, timeout_ms: Optional[float] = None, **kwargs) -> bool:
        """下拉选择（仅 WebView 上下文的 <select>）"""
        def do():
            from selenium.webdriver.support.ui import Select
            Select(self._find(locator)).select_by_value(value)
            return True
        return self._attempt("选择", locator, do, timeout_ms)

    def long_press(self, locator: str, timeout_ms: Optional[float] = None) -> bool:
        """长按元素（旧 API）"""
        def do():
            element = self._find(locator)
            self.driver.execute_script("mobile: longClick", {"elementId": element.id})
            return True
        return self._attempt("长按", locator, do, timeout_ms)

    def hide_keyboard(self) -> bool:
        """隐藏键盘（旧 API）"""
        try:
            self.driver.hide_keyboard()
            return True
        except Exception:
            return False

    def get_supported_keywords(self) -> list:
        """返回支持的关键字列表（旧 API）"""
        return ["click", "type", "check", "swipe", "tap", "screenshot",
                "navigate", "select", "long_press", "hide_keyboard",
                "launch", "close", "locate_element"]

    # ── 用例级录屏（Appium 原生 screenrecord）─────────────────────
    # 与 PlaywrightDriver.start_case_recording / stop_case_recording 同契约，
    # SKIExecutor 的录像分段机器对二者通用（仅 recording_backend 标识不同）。

    def start_case_recording(self, output_dir: str, case_id: str,
                             target_path: str, video_size: str = None) -> Optional[str]:
        """开始用例录屏，调用 Appium 原生 start_recording_screen。

        Args:
            output_dir: 录像输出目录
            case_id: 用例 ID（仅日志）
            target_path: 目标文件路径（建议 .mp4）
            video_size: 分辨率（如 "1280x720"），None 用设备默认

        Returns:
            目标文件路径；启动失败返回 None
        """
        try:
            from pathlib import Path as _Path
            _Path(output_dir).mkdir(parents=True, exist_ok=True)
            target = target_path
            # Appium Android 原生录屏产物为 mp4，统一后缀
            if target and not str(target).lower().endswith(".mp4"):
                target = str(_Path(target).with_suffix(".mp4"))
            self._recording_target_path = target

            options: Dict[str, Any] = {}
            if video_size and str(video_size).lower() not in ("screen", ""):
                options["videoSize"] = str(video_size)
            self.driver.start_recording_screen(**options)
            self._recording_active = True
            logger.info(f"Appium 原生录屏已启动: {target}")
            return target
        except Exception as e:
            logger.warning(f"Appium 录屏启动失败: {e}")
            self._recording_active = False
            self._recording_target_path = None
            return None

    def stop_case_recording(self, case_id: str = "",
                            target_path: Optional[str] = None) -> Optional[str]:
        """停止用例录屏，base64 解码落盘为 mp4。

        Returns:
            实际保存的文件路径；失败返回 None
        """
        if not self._recording_active:
            return self._recording_target_path
        try:
            import base64
            from pathlib import Path as _Path
            b64 = self.driver.stop_recording_screen()
            self._recording_active = False
            target = target_path or self._recording_target_path
            if not target:
                logger.warning("Appium 录屏停止：无目标路径")
                return None
            target = str(target)
            if not target.lower().endswith(".mp4"):
                target = str(_Path(target).with_suffix(".mp4"))
            _Path(target).parent.mkdir(parents=True, exist_ok=True)
            with open(target, "wb") as f:
                f.write(base64.b64decode(b64))
            logger.info(f"Appium 录屏已保存: {target}")
            self._recording_target_path = None
            return target
        except Exception as e:
            logger.warning(f"Appium 录屏停止失败: {e}")
            self._recording_active = False
            return self._recording_target_path

