"""桌面坐标驱动器 (Task 3.3)

基于屏幕绝对坐标操作桌面 UI，支持 Windows 和 macOS。
视觉定位流水线的执行层：接收坐标后完成鼠标/键盘动作。

依赖 pyautogui（可选）。若未安装，实例化时给出清晰提示。
"""
import os
import subprocess
import sys
import time
from typing import Optional, Tuple

from rodski.vision.exceptions import CoordinateError


def _require_pyautogui():
    """尝试导入 pyautogui，失败时给出安装提示并抛出 ImportError。"""
    try:
        import pyautogui
        return pyautogui
    except ImportError as exc:
        raise ImportError(
            "pyautogui 未安装，桌面驱动不可用。\n"
            "请运行：pip install pyautogui\n"
            "macOS 额外需要：pip install pyobjc-framework-Quartz\n"
            "Linux 额外需要：pip install python3-xlib"
        ) from exc


class DesktopVisionDriver:
    """基于屏幕绝对坐标的桌面驱动，视觉定位主驱动。

    支持平台：windows (win32) / macos (darwin)。
    操作均以屏幕像素坐标为基准，配合视觉定位层使用。

    Args:
        platform: 强制指定平台（'windows' 或 'macos'）；
                  默认 None，自动检测。

    Raises:
        ImportError: pyautogui 未安装时抛出，含安装说明。
        RuntimeError: 运行在不支持的平台（非 Windows/macOS）时抛出。
    """

    _SUPPORTED = {"darwin": "macos", "win32": "windows"}

    def __init__(self, platform: Optional[str] = None):
        # 检测平台
        if platform is not None:
            self._platform = platform.lower()
        else:
            raw = sys.platform
            self._platform = self._SUPPORTED.get(raw, raw)

        if self._platform not in ("windows", "macos"):
            raise RuntimeError(
                f"DesktopVisionDriver 仅支持 Windows / macOS，"
                f"当前平台：{self._platform}（sys.platform={sys.platform}）"
            )

        # 延迟导入，给出清晰错误
        self._pyautogui = _require_pyautogui()

        # 关闭 pyautogui 安全防护（防止移到角落时抛异常，由驱动自行校验坐标）
        self._pyautogui.FAILSAFE = True
        self._pyautogui.PAUSE = 0.05  # 每次操作后短暂停顿，提高稳定性

    # ── 内部工具 ──────────────────────────────────────────────────

    def _validate_coords(self, x: int, y: int) -> None:
        """校验坐标合法性，不合法则抛出 CoordinateError。"""
        if x < 0 or y < 0:
            raise CoordinateError(
                x=x, y=y,
                message=f"坐标 ({x}, {y}) 含负值，必须为非负整数。"
            )
        w, h = self.get_screen_size()
        if x >= w or y >= h:
            raise CoordinateError(
                x=x, y=y,
                screen_size=(w, h),
                message=(
                    f"坐标 ({x}, {y}) 超出屏幕范围 ({w}x{h})。"
                    "建议：检查分辨率配置或多显示器布局。"
                ),
            )

    # ── 点击操作 ─────────────────────────────────────────────────

    def click_at(self, x: int, y: int) -> bool:
        """在屏幕绝对坐标 (x, y) 处单击鼠标左键。

        Args:
            x: 横坐标（像素）。
            y: 纵坐标（像素）。

        Returns:
            成功返回 True。

        Raises:
            CoordinateError: 坐标超出屏幕范围时抛出。
        """
        self._validate_coords(x, y)
        self._pyautogui.click(x, y)
        return True

    def double_click_at(self, x: int, y: int) -> bool:
        """在屏幕绝对坐标 (x, y) 处双击鼠标左键。

        Args:
            x: 横坐标（像素）。
            y: 纵坐标（像素）。

        Returns:
            成功返回 True。

        Raises:
            CoordinateError: 坐标超出屏幕范围时抛出。
        """
        self._validate_coords(x, y)
        self._pyautogui.doubleClick(x, y)
        return True

    def right_click_at(self, x: int, y: int) -> bool:
        """在屏幕绝对坐标 (x, y) 处单击鼠标右键。

        Args:
            x: 横坐标（像素）。
            y: 纵坐标（像素）。

        Returns:
            成功返回 True。

        Raises:
            CoordinateError: 坐标超出屏幕范围时抛出。
        """
        self._validate_coords(x, y)
        self._pyautogui.rightClick(x, y)
        return True

    def type_at(self, x: int, y: int, text: str) -> bool:
        """点击坐标 (x, y) 后输入文本。

        Args:
            x: 横坐标（像素）。
            y: 纵坐标（像素）。
            text: 要输入的字符串。

        Returns:
            成功返回 True。

        Raises:
            CoordinateError: 坐标超出屏幕范围时抛出。
        """
        self._validate_coords(x, y)
        self._pyautogui.click(x, y)
        time.sleep(0.1)  # 等待焦点切换
        self._pyautogui.typewrite(text, interval=0.02)
        return True

    # ── 截图 / 屏幕信息 ──────────────────────────────────────────

    def screenshot(self, output_path: str) -> str:
        """截取全屏并保存为图片文件。

        Args:
            output_path: 输出文件路径（如 '/tmp/screen.png'）。

        Returns:
            实际保存的文件路径字符串。

        Raises:
            RuntimeError: 截图失败时抛出。
        """
        try:
            img = self._pyautogui.screenshot()
            img.save(output_path)
            return output_path
        except Exception as exc:
            raise RuntimeError(
                f"全屏截图失败，保存路径：{output_path}。原因：{exc}"
            ) from exc

    def get_screen_size(self) -> Tuple[int, int]:
        """返回主屏幕分辨率 (width, height)。"""
        return self._pyautogui.size()

    # ── 应用启动 ─────────────────────────────────────────────────

    def launch_app(self, app_path: str) -> bool:
        """启动一个桌面应用程序。

        - macOS: 调用 ``open`` 命令（支持 .app 包路径）。
        - Windows: 使用 ``subprocess.Popen`` 直接启动可执行文件；
          若 Popen 失败则回退到 ``os.startfile``。

        Args:
            app_path: 应用路径（macOS: /Applications/xxx.app，
                      Windows: C:\\path\\to\\app.exe）。

        Returns:
            成功启动返回 True，失败返回 False。
        """
        try:
            if self._platform == "macos":
                subprocess.Popen(["open", app_path])
            else:  # windows
                try:
                    subprocess.Popen([app_path])
                except (OSError, FileNotFoundError):
                    os.startfile(app_path)  # type: ignore[attr-defined]
            return True
        except Exception:
            return False

    # ── 窗口聚焦 ─────────────────────────────────────────────────

    def focus_window(self, title: str) -> bool:
        """将包含指定标题的窗口切换到前台。

        - macOS: 使用 AppleScript ``activate`` 命令。
        - Windows: 使用 pyautogui 的 ``getWindowsWithTitle`` + ``activate``。

        Args:
            title: 窗口标题（支持部分匹配，实际匹配由平台决定）。

        Returns:
            成功聚焦返回 True，未找到窗口或操作失败返回 False。
        """
        try:
            if self._platform == "macos":
                script = (
                    f'tell application "{title}" to activate'
                )
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    timeout=5,
                )
                return result.returncode == 0
            else:  # windows
                windows = self._pyautogui.getWindowsWithTitle(title)
                if not windows:
                    return False
                windows[0].activate()
                return True
        except Exception:
            return False

    # ── dunder ───────────────────────────────────────────────────

    def __repr__(self) -> str:
        w, h = self.get_screen_size()
        return (
            f"DesktopVisionDriver(platform={self._platform!r}, "
            f"screen={w}x{h})"
        )
