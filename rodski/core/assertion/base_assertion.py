"""断言基类 - 定义断言接口"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from pathlib import Path


class BaseAssertion(ABC):
    """视觉断言基类

    所有断言实现必须继承此类并实现 match 方法。
    """

    @abstractmethod
    def match(self, *args, **kwargs) -> Dict[str, Any]:
        """执行断言匹配

        Returns:
            结构化结果字典，至少包含:
            - matched: bool  是否匹配成功
            - similarity: float  匹配度
            - threshold: float  阈值
        """
        pass

    @staticmethod
    def resolve_reference_path(reference: str, module_dir: Path) -> Path:
        """将相对路径解析为绝对路径

        预期图片路径相对于 `images/assert/` 目录。
        """
        images_dir = module_dir / "images" / "assert"
        ref_path = Path(reference)
        if ref_path.is_absolute():
            return ref_path
        return images_dir / reference
