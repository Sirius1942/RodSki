"""视觉定位结果缓存模块

缓存 OmniParser 和 LLM 分析结果，避免对同一截图重复调用远程服务。

- 缓存 key 使用截图路径的 MD5 哈希，避免路径含特殊字符时的问题。
- 每条记录独立计时，TTL 到期后惰性清理（get 时检查，也可主动调用 _cleanup_expired）。
- 线程安全：使用 threading.Lock 保护内部字典。
"""
import hashlib
import threading
import time
from typing import Dict, List, Optional, Tuple, Any


_SENTINEL = object()  # 区分"未命中"和"值为 None"


class _CacheEntry:
    """单条缓存记录，携带值和过期时间戳"""

    __slots__ = ("value", "expires_at")

    def __init__(self, value: Any, expires_at: float):
        self.value = value
        self.expires_at = expires_at

    def is_alive(self) -> bool:
        return time.monotonic() < self.expires_at


class VisionCache:
    """缓存 OmniParser 和 LLM 分析结果，避免重复调用

    用法示例::

        cache = VisionCache(ttl=30)

        # 存入 OmniParser 结果
        cache.set_parse_result("/tmp/screen.png", parsed_elements)

        # 读取（未命中或已过期返回 None）
        result = cache.get_parse_result("/tmp/screen.png")

        # 清空全部缓存
        cache.clear()
    """

    def __init__(self, ttl: int = 30):
        """初始化缓存。

        Args:
            ttl: 缓存存活秒数，默认 30 秒。
        """
        self._ttl: int = ttl
        self._parse_store: Dict[str, _CacheEntry] = {}
        self._analyze_store: Dict[str, _CacheEntry] = {}
        self._lock = threading.Lock()

    # ── 内部工具 ──────────────────────────────────────────────────

    @staticmethod
    def _make_key(screenshot_path: str) -> str:
        """将截图路径转为 MD5 哈希字符串作为缓存 key。"""
        return hashlib.md5(screenshot_path.encode("utf-8")).hexdigest()

    def _get(self, store: Dict[str, _CacheEntry], key: str) -> Any:
        """从指定 store 中读取，过期则删除并返回哨兵值。"""
        entry = store.get(key)
        if entry is None:
            return _SENTINEL
        if not entry.is_alive():
            del store[key]
            return _SENTINEL
        return entry.value

    def _set(self, store: Dict[str, _CacheEntry], key: str, value: Any) -> None:
        """向指定 store 写入一条带 TTL 的记录。"""
        expires_at = time.monotonic() + self._ttl
        store[key] = _CacheEntry(value=value, expires_at=expires_at)

    # ── OmniParser 结果缓存 ───────────────────────────────────────

    def get_parse_result(self, screenshot_path: str) -> Optional[List]:
        """读取截图对应的 OmniParser 解析结果。

        Args:
            screenshot_path: 截图文件路径（用于生成缓存 key）。

        Returns:
            缓存的解析结果列表；未命中或已过期时返回 None。
        """
        key = self._make_key(screenshot_path)
        with self._lock:
            result = self._get(self._parse_store, key)
        return None if result is _SENTINEL else result

    def set_parse_result(self, screenshot_path: str, result: List) -> None:
        """存入截图对应的 OmniParser 解析结果。

        Args:
            screenshot_path: 截图文件路径。
            result: OmniParser 返回的元素列表。
        """
        key = self._make_key(screenshot_path)
        with self._lock:
            self._set(self._parse_store, key, result)

    # ── LLM 分析结果缓存 ─────────────────────────────────────────

    def get_analyze_result(self, screenshot_path: str) -> Optional[List]:
        """读取截图对应的 LLM 分析结果。

        Args:
            screenshot_path: 截图文件路径。

        Returns:
            缓存的分析结果列表；未命中或已过期时返回 None。
        """
        key = self._make_key(screenshot_path)
        with self._lock:
            result = self._get(self._analyze_store, key)
        return None if result is _SENTINEL else result

    def set_analyze_result(self, screenshot_path: str, result: List) -> None:
        """存入截图对应的 LLM 分析结果。

        Args:
            screenshot_path: 截图文件路径。
            result: LLM 返回的坐标/元素列表。
        """
        key = self._make_key(screenshot_path)
        with self._lock:
            self._set(self._analyze_store, key, result)

    # ── 维护操作 ─────────────────────────────────────────────────

    def clear(self) -> None:
        """清空全部缓存（parse 和 analyze）。"""
        with self._lock:
            self._parse_store.clear()
            self._analyze_store.clear()

    def _cleanup_expired(self) -> Tuple[int, int]:
        """主动清除全部已过期的缓存条目。

        Returns:
            (parse_removed, analyze_removed) 分别清除的条目数。
        """
        now = time.monotonic()
        with self._lock:
            parse_keys = [k for k, e in self._parse_store.items() if now >= e.expires_at]
            for k in parse_keys:
                del self._parse_store[k]

            analyze_keys = [k for k, e in self._analyze_store.items() if now >= e.expires_at]
            for k in analyze_keys:
                del self._analyze_store[k]

        return len(parse_keys), len(analyze_keys)

    # ── 只读统计属性 ─────────────────────────────────────────────

    @property
    def size(self) -> Tuple[int, int]:
        """返回 (parse_store条目数, analyze_store条目数)，含已过期但未清理的条目。"""
        with self._lock:
            return len(self._parse_store), len(self._analyze_store)

    @property
    def ttl(self) -> int:
        """当前缓存 TTL（秒）。"""
        return self._ttl

    def __repr__(self) -> str:
        p, a = self.size
        return f"VisionCache(ttl={self._ttl}s, parse_entries={p}, analyze_entries={a})"
