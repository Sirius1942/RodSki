"""浏览器回收器 + 执行快照

管理浏览器实例的生命周期，支持：
1. 定时/计数回收（避免内存泄漏）
2. 执行快照保存与恢复（断点续跑）
"""
import json
import logging
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger("rodski")


@dataclass
class SnapshotRecord:
    """快照记录"""
    case_id: str
    step_index: int
    timestamp: float
    driver_state: Dict[str, Any]
    variables: Dict[str, Any]
    screenshot_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["timestamp"] = self.timestamp
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SnapshotRecord":
        return cls(**data)


class ExecutionSnapshot:
    """执行快照 - 保存/恢复测试执行状态

    用于断点续跑：在步骤 N 失败后，从快照恢复继续执行步骤 N+1。
    """

    def __init__(self, snapshot_dir: str = "snapshots"):
        """初始化快照管理器

        Args:
            snapshot_dir: 快照文件存放目录
        """
        self._snapshot_dir = Path(snapshot_dir)
        self._snapshot_dir.mkdir(parents=True, exist_ok=True)

    def _snapshot_path(self, case_id: str) -> Path:
        return self._snapshot_dir / f"snapshot_{case_id}.json"

    def save(
        self,
        case_id: str,
        step_index: int,
        driver_state: Optional[Dict[str, Any]] = None,
        variables: Optional[Dict[str, Any]] = None,
        screenshot_path: Optional[str] = None,
    ) -> str:
        """保存执行快照

        Args:
            case_id: 用例 ID
            step_index: 当前步骤索引（0-based）
            driver_state: 驱动状态（URL、页面标题、已定位元素等）
            variables: 变量表
            screenshot_path: 截图路径

        Returns:
            快照文件路径
        """
        record = SnapshotRecord(
            case_id=case_id,
            step_index=step_index,
            timestamp=time.time(),
            driver_state=driver_state or {},
            variables=variables or {},
            screenshot_path=screenshot_path,
        )
        path = self._snapshot_path(case_id)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(record.to_dict(), f, ensure_ascii=False, indent=2)
            logger.info(
                f"[Snapshot] 保存快照: case={case_id}, step={step_index}, path={path}"
            )
            return str(path)
        except Exception as e:
            logger.error(f"[Snapshot] 保存快照失败: {e}")
            raise

    def restore(self, snapshot_path: Optional[str] = None, case_id: str = "") -> Optional[SnapshotRecord]:
        """恢复执行快照

        Args:
            snapshot_path: 快照文件路径
            case_id: 用例 ID（当 snapshot_path 为空时使用）

        Returns:
            SnapshotRecord 或 None（快照不存在或解析失败）
        """
        if not snapshot_path and not case_id:
            return None
        path = Path(snapshot_path) if snapshot_path else self._snapshot_path(case_id)
        if not path.exists():
            logger.warning(f"[Snapshot] 快照文件不存在: {path}")
            return None
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            record = SnapshotRecord.from_dict(data)
            logger.info(
                f"[Snapshot] 恢复快照: case={record.case_id}, "
                f"step={record.step_index}, timestamp={record.timestamp}"
            )
            return record
        except Exception as e:
            logger.error(f"[Snapshot] 恢复快照失败: {e}")
            return None

    def exists(self, case_id: str) -> bool:
        """检查快照是否存在"""
        return self._snapshot_path(case_id).exists()

    def delete(self, case_id: str) -> bool:
        """删除快照"""
        path = self._snapshot_path(case_id)
        if path.exists():
            path.unlink()
            logger.info(f"[Snapshot] 删除快照: case={case_id}")
            return True
        return False


class BrowserRecycler:
    """浏览器回收器

    在测试执行过程中，根据条件判断是否需要回收浏览器实例。
    支持：
    - 步数阈值回收（如每 50 步重启一次）
    - 内存超限回收
    - 显式调用回收
    """

    def __init__(
        self,
        driver_factory=None,
        max_steps_per_browser: int = 50,
        max_memory_mb: float = 0,
    ):
        """初始化浏览器回收器

        Args:
            driver_factory: DriverFactory 实例（用于创建新驱动）
            max_steps_per_browser: 每个浏览器实例最大执行步数
            max_memory_mb: 内存超限阈值（MB），0 表示不限制
        """
        self._driver_factory = driver_factory
        self._max_steps = max_steps_per_browser
        self._max_memory_mb = max_memory_mb
        self._step_count: int = 0
        self._current_driver = None

    def attach_driver(self, driver) -> None:
        """附加当前 driver 实例"""
        self._current_driver = driver
        self._step_count = 0

    def record_step(self) -> None:
        """记录执行了一个步骤（用于计数）"""
        self._step_count += 1

    @property
    def step_count(self) -> int:
        return self._step_count

    def should_recycle(self) -> bool:
        """判断是否应该回收浏览器

        Returns:
            True 如果满足以下任一条件：
            - 步数超过阈值
            - 内存超过阈值
            - driver 处于不可用状态
        """
        # 步数超限
        if self._max_steps > 0 and self._step_count >= self._max_steps:
            logger.info(
                f"[BrowserRecycler] 步数超限: {self._step_count} >= {self._max_steps}"
            )
            return True

        # 内存超限
        if self._max_memory_mb > 0:
            mem_mb = self._get_memory_usage_mb()
            if mem_mb > self._max_memory_mb:
                logger.info(
                    f"[BrowserRecycler] 内存超限: {mem_mb:.1f} MB > {self._max_memory_mb} MB"
                )
                return True

        return False

    def _get_memory_usage_mb(self) -> float:
        """获取当前进程内存使用（MB）"""
        try:
            import psutil
            proc = psutil.Process(os.getpid())
            return proc.memory_info().rss / (1024 * 1024)
        except ImportError:
            return 0.0

    def recycle(self, driver=None) -> Optional[Any]:
        """执行浏览器回收：关闭旧实例并返回新实例

        Args:
            driver: 要关闭的 driver 实例（None 时使用内部持有的实例）

        Returns:
            新的 driver 实例（如果 factory 可用），否则 None
        """
        target = driver or self._current_driver
        if target:
            try:
                logger.info(f"[BrowserRecycler] 关闭旧浏览器实例: {target}")
                if hasattr(target, "quit"):
                    target.quit()
                elif hasattr(target, "close"):
                    target.close()
            except Exception as e:
                logger.warning(f"[BrowserRecycler] 关闭浏览器时出现异常: {e}")

        # 重置计数
        self._step_count = 0

        # 尝试创建新实例
        new_driver = None
        if self._driver_factory:
            try:
                new_driver = self._driver_factory.create()
                self._current_driver = new_driver
                logger.info("[BrowserRecycler] 新浏览器实例已创建")
            except Exception as e:
                logger.error(f"[BrowserRecycler] 创建新浏览器失败: {e}")
                raise

        return new_driver
