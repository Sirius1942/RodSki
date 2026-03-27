"""视觉定位结果缓存模块

缓存视觉定位结果，减少重复 AI 调用。

- 缓存 key 使用截图内容的 MD5 哈希，支持路径、PIL Image 或 bytes。
- 每条记录独立计时，TTL 到期后惰性清理（get 时检查，也可主动调用 cleanup_expired）。
- 线程安全：使用 threading.Lock 保护内部字典。
"""

from __future__ import annotations

import hashlib
import io
import threading
import time
from typing import Any, Dict, Optional, Union

# 延迟导入 PIL，避免强制依赖
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    Image = None  # type: ignore[assignment]
    HAS_PIL = False

_SENTINEL = object()  # 区分"未命中"和"值为 None"


class _CacheEntry:
    """单条缓存记录，携带值和过期时间戳"""

    __slots__ = ("value", "expires_at")

    def __init__(self, value: Any, expires_at: float):
        self.value = value
        self.expires_at = expires_at

    def is_alive(self) -> bool:
        return time.monotonic() < self.expires_at


# 截图输入类型
ScreenshotInput = Union[str, bytes, "Image.Image"]


class VisionCache:
    """视觉定位结果缓存

    缓存视觉定位结果，避免对同一截图重复调用 AI 服务。

    用法示例::

        cache = VisionCache(ttl=30, enabled=True)

        # 存入结果
        cache.set(screenshot, {"x": 100, "y": 200, "confidence": 0.95})

        # 读取（未命中或已过期返回 None）
        result = cache.get(screenshot)
        if result:
            print(f"缓存命中: {result}")

        # 清空全部缓存
        cache.clear()

        # 清理过期缓存
        removed_count = cache.cleanup_expired()
    """

    def __init__(self, ttl: int = 30, enabled: bool = True):
        """初始化缓存。

        Args:
            ttl: 缓存过期时间（秒），默认 30 秒。
            enabled: 是否启用缓存，默认 True。设为 False 时，get 始终返回 None。
        """
        self._ttl: int = ttl
        self._enabled: bool = enabled
        self._cache: Dict[str, _CacheEntry] = {}
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        """返回缓存是否启用"""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """设置缓存是否启用"""
        self._enabled = value

    @property
    def ttl(self) -> int:
        """返回当前缓存 TTL（秒）"""
        return self._ttl

    # ── 内部工具 ──────────────────────────────────────────────────

    def _get_screenshot_hash(self, screenshot: ScreenshotInput) -> str:
        """计算截图的 hash 值作为缓存 key

        Args:
            screenshot: 截图（路径、PIL Image 或 bytes）

        Returns:
            MD5 hash 字符串
        """
        if isinstance(screenshot, str):
            # 路径：读取文件内容计算 hash
            with open(screenshot, "rb") as f:
                content = f.read()
            return hashlib.md5(content).hexdigest()

        elif isinstance(screenshot, bytes):
            # bytes：直接计算 hash
            return hashlib.md5(screenshot).hexdigest()

        elif HAS_PIL and isinstance(screenshot, Image.Image):
            # PIL Image：转为 bytes 后计算 hash
            buffer = io.BytesIO()
            screenshot.save(buffer, format="PNG")
            return hashlib.md5(buffer.getvalue()).hexdigest()

        else:
            raise TypeError(
                f"不支持的截图类型: {type(screenshot).__name__}。"
                "支持类型: str (路径), bytes, PIL.Image.Image"
            )

    # ── 公共 API ──────────────────────────────────────────────────

    def get(self, screenshot: ScreenshotInput) -> Optional[Dict]:
        """获取缓存结果

        Args:
            screenshot: 截图（路径、PIL Image 或 bytes）

        Returns:
            缓存的结果字典，不存在或已过期返回 None。
            若缓存未启用（enabled=False），也返回 None。
        """
        if not self._enabled:
            return None

        try:
            key = self._get_screenshot_hash(screenshot)
        except (FileNotFoundError, OSError):
            # 文件不存在或读取失败，返回未命中
            return None

        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            if not entry.is_alive():
                del self._cache[key]
                return None
            return entry.value

    def set(self, screenshot: ScreenshotInput, result: Dict) -> None:
        """设置缓存

        Args:
            screenshot: 截图（路径、PIL Image 或 bytes）
            result: 要缓存的结果字典
        """
        if not self._enabled:
            return

        try:
            key = self._get_screenshot_hash(screenshot)
        except (FileNotFoundError, OSError):
            # 文件不存在或读取失败，不缓存
            return

        expires_at = time.monotonic() + self._ttl
        with self._lock:
            self._cache[key] = _CacheEntry(value=result, expires_at=expires_at)

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()

    def cleanup_expired(self) -> int:
        """清理过期缓存

        Returns:
            清理的条目数
        """
        now = time.monotonic()
        removed = 0
        with self._lock:
            expired_keys = [k for k, e in self._cache.items() if now >= e.expires_at]
            for k in expired_keys:
                del self._cache[k]
                removed += 1
        return removed

    # ── 兼容旧 API ──────────────────────────────────────────────────

    def get_parse_result(self, screenshot_path: str) -> Optional[Any]:
        """读取截图对应的解析结果（兼容旧 API）

        Args:
            screenshot_path: 截图文件路径

        Returns:
            缓存的解析结果；未命中或已过期时返回 None
        """
        return self.get(screenshot_path)

    def set_parse_result(self, screenshot_path: str, result: Any) -> None:
        """存入截图对应的解析结果（兼容旧 API）

        Args:
            screenshot_path: 截图文件路径
            result: 解析结果
        """
        self.set(screenshot_path, result if isinstance(result, dict) else {"data": result})

    def get_analyze_result(self, screenshot_path: str) -> Optional[Any]:
        """读取截图对应的分析结果（兼容旧 API）

        Args:
            screenshot_path: 截图文件路径

        Returns:
            缓存的分析结果；未命中或已过期时返回 None
        """
        return self.get(screenshot_path)

    def set_analyze_result(self, screenshot_path: str, result: Any) -> None:
        """存入截图对应的分析结果（兼容旧 API）

        Args:
            screenshot_path: 截图文件路径
            result: 分析结果
        """
        self.set(screenshot_path, result if isinstance(result, dict) else {"data": result})

    # ── 只读统计属性 ─────────────────────────────────────────────

    @property
    def size(self) -> int:
        """返回缓存条目数（含已过期但未清理的条目）"""
        with self._lock:
            return len(self._cache)

    def __repr__(self) -> str:
        return (
            f"VisionCache(ttl={self._ttl}s, enabled={self._enabled}, entries={self.size})"
        )