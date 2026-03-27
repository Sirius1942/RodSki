"""BBoxLocator - 坐标定位器，直接解析坐标字符串。

用于处理显式坐标格式的定位器，如 "100,200,150,250"。
"""

from __future__ import annotations

from typing import Tuple

from .exceptions import InvalidBBoxError


class BBoxLocator:
    """坐标定位器 - 直接解析坐标字符串。

    解析 "x1,y1,x2,y2" 格式的坐标字符串，并验证坐标有效性。

    Examples:
        >>> locator = BBoxLocator()
        >>> locator.locate("100,200,150,250")
        (100, 200, 150, 250)
        >>> locator.locate("100, 200, 150, 250")  # 支持空格容错
        (100, 200, 150, 250)
    """

    def __init__(self):
        """初始化坐标定位器。"""
        pass

    def locate(self, bbox_str: str) -> Tuple[int, int, int, int]:
        """解析坐标字符串并返回边界框。

        Args:
            bbox_str: "x1,y1,x2,y2" 格式的坐标字符串。
                     例如: "100,200,150,250"
                     支持空格容错: "100, 200, 150, 250"

        Returns:
            (x1, y1, x2, y2) 边界框坐标，均为整数。

        Raises:
            InvalidBBoxError: 坐标格式无效或坐标值不合法。

        Examples:
            >>> locator = BBoxLocator()
            >>> locator.locate("100,200,150,250")
            (100, 200, 150, 250)
            >>> locator.locate("0, 0, 1920, 1080")
            (0, 0, 1920, 1080)
        """
        if not bbox_str or not isinstance(bbox_str, str):
            raise InvalidBBoxError(
                bbox_str=str(bbox_str),
                reason="坐标字符串不能为空且必须为字符串类型",
            )

        # 分割并去除空格
        parts = bbox_str.strip().split(",")

        if len(parts) != 4:
            raise InvalidBBoxError(
                bbox_str=bbox_str,
                reason=f"需要4个坐标值，但得到{len(parts)}个",
            )

        # 解析各坐标值（支持空格容错）
        try:
            coords = [int(float(p.strip())) for p in parts]
        except (ValueError, TypeError) as e:
            raise InvalidBBoxError(
                bbox_str=bbox_str,
                reason=f"坐标值包含非数字字符: {e}",
            ) from e

        x1, y1, x2, y2 = coords

        # 验证坐标有效性
        if not self.validate(x1, y1, x2, y2):
            raise InvalidBBoxError(
                bbox_str=bbox_str,
                reason=f"坐标值无效: x2({x2}) 必须 > x1({x1})，y2({y2}) 必须 > y1({y1})，且所有坐标 >= 0",
            )

        return (x1, y1, x2, y2)

    def validate(self, x1: int, y1: int, x2: int, y2: int) -> bool:
        """验证坐标是否有效。

        验证规则:
        - x2 > x1 (宽度必须为正)
        - y2 > y1 (高度必须为正)
        - 所有坐标 >= 0 (不能为负)

        Args:
            x1: 左上角 x 坐标
            y1: 左上角 y 坐标
            x2: 右下角 x 坐标
            y2: 右下角 y 坐标

        Returns:
            True 如果坐标有效，否则 False。

        Examples:
            >>> locator = BBoxLocator()
            >>> locator.validate(100, 200, 150, 250)
            True
            >>> locator.validate(150, 200, 100, 250)  # x2 < x1
            False
            >>> locator.validate(-10, 200, 150, 250)  # 负坐标
            False
        """
        # 检查所有坐标非负
        if x1 < 0 or y1 < 0 or x2 < 0 or y2 < 0:
            return False

        # 检查 x2 > x1 且 y2 > y1
        if x2 <= x1 or y2 <= y1:
            return False

        return True

    def get_center(self, bbox_str: str) -> Tuple[int, int]:
        """解析坐标字符串并返回中心点坐标。

        这是一个便捷方法，用于获取边界框的中心点。

        Args:
            bbox_str: "x1,y1,x2,y2" 格式的坐标字符串。

        Returns:
            (cx, cy) 中心点坐标。

        Raises:
            InvalidBBoxError: 坐标格式无效。

        Examples:
            >>> locator = BBoxLocator()
            >>> locator.get_center("100,200,200,300")
            (150, 250)
        """
        x1, y1, x2, y2 = self.locate(bbox_str)
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        return (cx, cy)

    def __repr__(self) -> str:
        return "BBoxLocator()"