"""断言操作符引擎 (v11.0.0)

支持的操作符:
- 数值比较: $gt, $gte, $lt, $lte
- 包含检查: $contains
- 元素状态（v11.6.0，仅 UI 模型）: $count, $count_gte, $count_lte, $exists, $visible
  实际值由 keyword_engine 读取：$count* / $exists 传入元素匹配数量（int），
  $visible 传入是否可见（bool）。匹配 0 个元素时按实际数量 0 判定，绝不跳过。

用法示例:
    engine = AssertionEngine()
    engine.evaluate(100, {"$gt": 0})  # True
    engine.evaluate([1, 2, 3], {"$contains": 2})  # True
    engine.evaluate("hello world", {"$contains": "world"})  # True
"""

from typing import Any, Dict, Union


class AssertionError(Exception):
    """断言操作符求值失败"""
    pass


class AssertionEngine:
    """断言操作符求值引擎"""

    # v11.6.0: 元素状态操作符 —— 实际值不是元素文本，而是匹配数量 / 可见性
    COUNT_OPERATORS = {'$count', '$count_gte', '$count_lte', '$exists'}
    VISIBILITY_OPERATORS = {'$visible'}
    ELEMENT_OPERATORS = COUNT_OPERATORS | VISIBILITY_OPERATORS

    SUPPORTED_OPERATORS = {'$gt', '$gte', '$lt', '$lte', '$contains'} | ELEMENT_OPERATORS

    @staticmethod
    def is_element_operator(value: Any) -> bool:
        """是否为元素状态操作符字典（$count/$count_gte/$count_lte/$exists/$visible）。"""
        return (AssertionEngine.is_operator_dict(value)
                and next(iter(value)) in AssertionEngine.ELEMENT_OPERATORS)

    @staticmethod
    def is_operator_dict(value: Any) -> bool:
        """检查值是否为操作符字典，如 {"$gt": 100}

        Args:
            value: 待检查的值

        Returns:
            True 如果是单键操作符字典
        """
        if not isinstance(value, dict):
            return False
        if len(value) != 1:
            return False
        key = next(iter(value))
        return key.startswith('$') and key in AssertionEngine.SUPPORTED_OPERATORS

    @staticmethod
    def evaluate(actual: Any, operator_dict: Dict[str, Any]) -> bool:
        """求值断言操作符

        Args:
            actual: 实际值（来自 UI/API/DB）
            operator_dict: 单键操作符字典，如 {"$gt": 100}

        Returns:
            True 如果断言通过

        Raises:
            AssertionError: 断言失败，附带详细信息
            ValueError: 操作符格式错误或不支持
        """
        if not isinstance(operator_dict, dict) or len(operator_dict) != 1:
            raise ValueError(
                f"操作符必须是单键字典，得到: {operator_dict}"
            )

        operator, expected = next(iter(operator_dict.items()))

        if operator == '$gt':
            return AssertionEngine._eval_gt(actual, expected)
        elif operator == '$gte':
            return AssertionEngine._eval_gte(actual, expected)
        elif operator == '$lt':
            return AssertionEngine._eval_lt(actual, expected)
        elif operator == '$lte':
            return AssertionEngine._eval_lte(actual, expected)
        elif operator == '$contains':
            return AssertionEngine._eval_contains(actual, expected)
        elif operator in AssertionEngine.COUNT_OPERATORS:
            return AssertionEngine._eval_count(operator, actual, expected)
        elif operator == '$visible':
            return AssertionEngine._eval_visible(actual, expected)
        else:
            raise ValueError(f"不支持的操作符: {operator}")

    @staticmethod
    def _eval_gt(actual: Any, expected: Any) -> bool:
        """大于: actual > expected"""
        try:
            actual_num = float(actual) if not isinstance(actual, (int, float)) else actual
            expected_num = float(expected) if not isinstance(expected, (int, float)) else expected
            result = actual_num > expected_num
            if not result:
                raise AssertionError(
                    f"$gt 断言失败: {actual} (实际) 不大于 {expected} (期望)"
                )
            return True
        except (ValueError, TypeError) as e:
            raise AssertionError(
                f"$gt 需要数值类型，得到 actual={actual} (类型:{type(actual).__name__}), "
                f"expected={expected} (类型:{type(expected).__name__})"
            ) from e

    @staticmethod
    def _eval_gte(actual: Any, expected: Any) -> bool:
        """大于等于: actual >= expected"""
        try:
            actual_num = float(actual) if not isinstance(actual, (int, float)) else actual
            expected_num = float(expected) if not isinstance(expected, (int, float)) else expected
            result = actual_num >= expected_num
            if not result:
                raise AssertionError(
                    f"$gte 断言失败: {actual} (实际) 不大于等于 {expected} (期望)"
                )
            return True
        except (ValueError, TypeError) as e:
            raise AssertionError(
                f"$gte 需要数值类型，得到 actual={actual} (类型:{type(actual).__name__}), "
                f"expected={expected} (类型:{type(expected).__name__})"
            ) from e

    @staticmethod
    def _eval_lt(actual: Any, expected: Any) -> bool:
        """小于: actual < expected"""
        try:
            actual_num = float(actual) if not isinstance(actual, (int, float)) else actual
            expected_num = float(expected) if not isinstance(expected, (int, float)) else expected
            result = actual_num < expected_num
            if not result:
                raise AssertionError(
                    f"$lt 断言失败: {actual} (实际) 不小于 {expected} (期望)"
                )
            return True
        except (ValueError, TypeError) as e:
            raise AssertionError(
                f"$lt 需要数值类型，得到 actual={actual} (类型:{type(actual).__name__}), "
                f"expected={expected} (类型:{type(expected).__name__})"
            ) from e

    @staticmethod
    def _eval_lte(actual: Any, expected: Any) -> bool:
        """小于等于: actual <= expected"""
        try:
            actual_num = float(actual) if not isinstance(actual, (int, float)) else actual
            expected_num = float(expected) if not isinstance(expected, (int, float)) else expected
            result = actual_num <= expected_num
            if not result:
                raise AssertionError(
                    f"$lte 断言失败: {actual} (实际) 不小于等于 {expected} (期望)"
                )
            return True
        except (ValueError, TypeError) as e:
            raise AssertionError(
                f"$lte 需要数值类型，得到 actual={actual} (类型:{type(actual).__name__}), "
                f"expected={expected} (类型:{type(expected).__name__})"
            ) from e

    @staticmethod
    def _eval_contains(actual: Any, expected: Any) -> bool:
        """包含检查: expected in actual

        支持:
        - 字符串包含: "hello world" contains "world"
        - 数组包含: [1, 2, 3] contains 2
        """
        if isinstance(actual, str):
            expected_str = str(expected)
            result = expected_str in actual
            if not result:
                raise AssertionError(
                    f"$contains 断言失败: '{actual}' (实际) 不包含 '{expected_str}' (期望)"
                )
            return True
        elif isinstance(actual, (list, tuple)):
            result = expected in actual
            if not result:
                raise AssertionError(
                    f"$contains 断言失败: {actual} (实际) 不包含 {expected} (期望)"
                )
            return True
        else:
            raise AssertionError(
                f"$contains 需要字符串或数组，得到 {type(actual).__name__}: {actual}"
            )

    # ── v11.6.0 元素状态操作符 ───────────────────────────────────────

    @staticmethod
    def _to_bool(value: Any, operator: str) -> bool:
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if text in ('true', '1', 'yes', '是'):
            return True
        if text in ('false', '0', 'no', '否'):
            return False
        raise ValueError(f"{operator} 的期望值必须是 true/false，得到: {value!r}")

    @staticmethod
    def _to_count(value: Any, operator: str, role: str) -> int:
        if isinstance(value, bool):
            raise ValueError(f"{operator} 的{role}必须是非负整数，得到布尔值: {value!r}")
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"{operator} 的{role}必须是非负整数，得到: {value!r}")
        if number < 0 or number != int(number):
            raise ValueError(f"{operator} 的{role}必须是非负整数，得到: {value!r}")
        return int(number)

    @staticmethod
    def _eval_count(operator: str, actual: Any, expected: Any) -> bool:
        """元素匹配数量断言。actual 为匹配数量（None 视为 0，绝不跳过）。"""
        actual_n = 0 if actual is None else AssertionEngine._to_count(actual, operator, "实际值")
        if operator == '$exists':
            want = AssertionEngine._to_bool(expected, operator)
            if (actual_n > 0) != want:
                if want:
                    raise AssertionError(
                        f"$exists 断言失败: 期望元素存在，实际匹配 0 个元素"
                    )
                raise AssertionError(
                    f"$exists 断言失败: 期望元素不存在，实际匹配 {actual_n} 个元素"
                )
            return True

        expected_n = AssertionEngine._to_count(expected, operator, "期望值")
        if operator == '$count':
            ok, relation = actual_n == expected_n, "等于"
        elif operator == '$count_gte':
            ok, relation = actual_n >= expected_n, "至少"
        else:  # $count_lte
            ok, relation = actual_n <= expected_n, "至多"
        if not ok:
            raise AssertionError(
                f"{operator} 断言失败: 期望匹配数量{relation} {expected_n}，实际 {actual_n}"
            )
        return True

    @staticmethod
    def _eval_visible(actual: Any, expected: Any) -> bool:
        """元素可见性断言。actual 为是否可见（未匹配到元素视为不可见）。"""
        want = AssertionEngine._to_bool(expected, '$visible')
        got = bool(actual) if isinstance(actual, bool) or actual is None else AssertionEngine._to_bool(actual, '$visible')
        if got != want:
            raise AssertionError(
                f"$visible 断言失败: 期望{'可见' if want else '不可见'}，实际{'可见' if got else '不可见'}"
            )
        return True
