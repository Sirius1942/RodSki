"""对象池管理器 - 管理运行时对象（浏览器、数据库连接等）

支持功能：
- 对象注册和查询
- 对象生命周期管理
- 对象命名（与 Case ID 关联）
- 多对象并发支持
"""
import logging
from typing import Any, Dict, Optional, List
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger("rodski")


@dataclass
class RuntimeObject:
    """运行时对象"""
    id: str  # 对象 ID（如 AC-029.buyer_browser）
    type: str  # 对象类型（如 WebDriver, DBConnection）
    object: Any  # 实际对象引用
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "alive"  # alive, closed, error
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_lifetime_seconds(self) -> int:
        """获取对象存活时长（秒）"""
        delta = datetime.now() - self.created_at
        return int(delta.total_seconds())


class ObjectPool:
    """对象池管理器"""

    def __init__(self):
        self.objects: Dict[str, RuntimeObject] = {}
        self._auto_counter: Dict[str, int] = {}  # 自动命名计数器

    def register_object(
        self,
        object: Any,
        object_type: str,
        object_id: Optional[str] = None,
        case_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """注册一个运行时对象

        Args:
            object: 实际对象（如 WebDriver 实例）
            object_type: 对象类型（如 "browser", "db_connection"）
            object_id: 用户指定的对象 ID（如 "buyer_browser"）
            case_id: 所属 Case ID
            metadata: 附加元数据

        Returns:
            完整的对象 ID（如 "AC-029.buyer_browser" 或 "AC-001.browser_obj_1"）
        """
        # 生成完整对象 ID
        if case_id:
            if object_id:
                # 用户命名：case_id.object_id
                full_id = f"{case_id}.{object_id}"
            else:
                # 自动命名：case_id.{type}_obj_N
                counter_key = f"{case_id}.{object_type}"
                self._auto_counter[counter_key] = self._auto_counter.get(counter_key, 0) + 1
                full_id = f"{case_id}.{object_type}_obj_{self._auto_counter[counter_key]}"
        else:
            # 无 case_id，使用全局自动命名
            if object_id:
                full_id = object_id
            else:
                self._auto_counter[object_type] = self._auto_counter.get(object_type, 0) + 1
                full_id = f"{object_type}_obj_{self._auto_counter[object_type]}"

        # 检查 ID 冲突
        if full_id in self.objects:
            logger.warning(f"[ObjectPool] Object ID {full_id} already exists, replacing")

        # 注册对象
        runtime_obj = RuntimeObject(
            id=full_id,
            type=object_type,
            object=object,
            metadata=metadata or {},
        )
        self.objects[full_id] = runtime_obj
        logger.info(f"[ObjectPool] Registered object: {full_id} (type: {object_type})")

        return full_id

    def get_object(self, object_id: str) -> Optional[Any]:
        """获取对象实例"""
        runtime_obj = self.objects.get(object_id)
        if runtime_obj:
            if runtime_obj.status != "alive":
                logger.warning(f"[ObjectPool] Object {object_id} is not alive (status: {runtime_obj.status})")
                return None
            return runtime_obj.object
        return None

    def get_runtime_object(self, object_id: str) -> Optional[RuntimeObject]:
        """获取完整的运行时对象信息"""
        return self.objects.get(object_id)

    def has_object(self, object_id: str) -> bool:
        """检查对象是否存在且存活"""
        runtime_obj = self.objects.get(object_id)
        return runtime_obj is not None and runtime_obj.status == "alive"

    def close_object(self, object_id: str) -> bool:
        """关闭对象"""
        runtime_obj = self.objects.get(object_id)
        if not runtime_obj:
            logger.warning(f"[ObjectPool] Object {object_id} not found")
            return False

        if runtime_obj.status != "alive":
            logger.warning(f"[ObjectPool] Object {object_id} already closed")
            return False

        # 尝试关闭对象
        try:
            obj = runtime_obj.object
            if hasattr(obj, "close"):
                obj.close()
            elif hasattr(obj, "quit"):
                obj.quit()
            runtime_obj.status = "closed"
            lifetime = runtime_obj.get_lifetime_seconds()
            logger.info(f"[ObjectPool] Closed object {object_id} (lifetime: {lifetime}s)")
            return True
        except Exception as e:
            runtime_obj.status = "error"
            logger.error(f"[ObjectPool] Failed to close object {object_id}: {e}")
            return False

    def close_all(self) -> int:
        """关闭所有对象"""
        count = 0
        for object_id in list(self.objects.keys()):
            if self.close_object(object_id):
                count += 1
        return count

    def list_objects(self) -> List[RuntimeObject]:
        """列出所有对象"""
        return list(self.objects.values())

    def get_objects_by_type(self, object_type: str) -> List[RuntimeObject]:
        """根据类型获取对象列表"""
        return [obj for obj in self.objects.values() if obj.type == object_type]

    def get_alive_objects(self) -> List[RuntimeObject]:
        """获取所有存活的对象"""
        return [obj for obj in self.objects.values() if obj.status == "alive"]

    def to_text(self) -> str:
        """生成文本格式的对象池内容（用于 CLI 显示）"""
        if not self.objects:
            return "Runtime Objects: (empty)\n"

        lines = ["Runtime Objects:\n"]
        for obj in self.objects.values():
            status_icon = "✅" if obj.status == "alive" else "❌"
            lifetime = obj.get_lifetime_seconds()
            lines.append(f"  {status_icon} {obj.id}: <{obj.type}> - {obj.status}\n")
            lines.append(f"     Created: {lifetime}s ago\n")

            # 显示元数据
            if obj.metadata:
                for key, value in obj.metadata.items():
                    lines.append(f"     {key}: {value}\n")

        return "".join(lines)

    def get_summary(self) -> Dict[str, Any]:
        """获取对象池摘要"""
        total = len(self.objects)
        alive = len(self.get_alive_objects())
        by_type: Dict[str, int] = {}
        for obj in self.objects.values():
            by_type[obj.type] = by_type.get(obj.type, 0) + 1

        return {
            "total": total,
            "alive": alive,
            "closed": total - alive,
            "by_type": by_type,
        }
