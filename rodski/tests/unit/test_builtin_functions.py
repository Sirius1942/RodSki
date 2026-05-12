"""内置函数 builtin_functions 单元测试（TDD — 先写测试再实现）

测试 data/builtin_functions.py 中的 random() 和 date() 函数。
覆盖：每个 type 的基本调用、参数边界、字符串拼接场景。
"""
import re
import time
from datetime import datetime, timedelta

import pytest

from data.builtin_functions import call_function


class TestRandom:
    """${random(type, ...)} 函数测试"""

    def test_random_int_range(self):
        """random(int, min, max) 返回范围内整数"""
        result = call_function("random", ["int", "100", "200"])
        val = int(result)
        assert 100 <= val <= 200

    def test_random_int_length(self):
        """random(int, N) 单参数表示 N 位数"""
        result = call_function("random", ["int", "4"])
        assert len(result) == 4
        assert result.isdigit()

    def test_random_int_no_extra_args(self):
        """random(int) 无参数返回 0~9999"""
        result = call_function("random", ["int"])
        val = int(result)
        assert 0 <= val <= 9999

    def test_random_float_range(self):
        """random(float, min, max) 返回范围内浮点数"""
        result = call_function("random", ["float", "10.00", "99.99"])
        val = float(result)
        assert 10.00 <= val <= 99.99

    def test_random_float_precision(self):
        """random(float, min, max, precision) 控制小数位"""
        result = call_function("random", ["float", "1.0", "9.0", "3"])
        parts = result.split(".")
        assert len(parts) == 2
        assert len(parts[1]) == 3

    def test_random_str_length(self):
        """random(str, N) 返回 N 位字母数字"""
        result = call_function("random", ["str", "12"])
        assert len(result) == 12
        assert result.isalnum()

    def test_random_str_default(self):
        """random(str) 默认 8 位"""
        result = call_function("random", ["str"])
        assert len(result) == 8

    def test_random_digits_length(self):
        """random(digits, N) 返回 N 位纯数字"""
        result = call_function("random", ["digits", "6"])
        assert len(result) == 6
        assert result.isdigit()

    def test_random_digits_default(self):
        """random(digits) 默认 6 位"""
        result = call_function("random", ["digits"])
        assert len(result) == 6

    def test_random_phone_format(self):
        """random(phone) 返回 11 位中国手机号"""
        result = call_function("random", ["phone"])
        assert len(result) == 11
        assert result.isdigit()
        assert result[0:2] in ("13", "15", "18")

    def test_random_email_format(self):
        """random(email) 返回含 @ 的邮箱"""
        result = call_function("random", ["email"])
        assert "@" in result
        assert result.endswith("@test.com")

    def test_random_choice_in_candidates(self):
        """random(choice, a, b, c) 返回候选值之一"""
        result = call_function("random", ["choice", "apple", "banana", "cherry"])
        assert result in ("apple", "banana", "cherry")

    def test_random_choice_single(self):
        """random(choice, x) 单候选值直接返回"""
        result = call_function("random", ["choice", "only"])
        assert result == "only"

    def test_random_uuid_format(self):
        """random(uuid) 返回合法 UUID 格式"""
        result = call_function("random", ["uuid"])
        uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')
        assert uuid_pattern.match(result)

    def test_random_unknown_type_raises(self):
        """random(xxx) 未知 type 抛出 ValueError"""
        with pytest.raises(ValueError, match="不支持类型"):
            call_function("random", ["xxx"])

    def test_random_uniqueness(self):
        """连续调用 random 应产生不同值（概率性，多次验证）"""
        results = {call_function("random", ["str", "16"]) for _ in range(10)}
        assert len(results) > 1


class TestDate:
    """${date(type, ...)} 函数测试"""

    def test_date_now_default_format(self):
        """date(now) 返回 YYYY-MM-DD HH:MM:SS 格式"""
        result = call_function("date", ["now"])
        dt = datetime.strptime(result, "%Y-%m-%d %H:%M:%S")
        assert (datetime.now() - dt).total_seconds() < 2

    def test_date_now_custom_format(self):
        """date(now, format) 自定义格式"""
        result = call_function("date", ["now", "%Y%m%d"])
        assert result == datetime.now().strftime("%Y%m%d")

    def test_date_today_default(self):
        """date(today) 返回 YYYY-MM-DD"""
        result = call_function("date", ["today"])
        assert result == datetime.now().strftime("%Y-%m-%d")

    def test_date_today_compact(self):
        """date(today, %Y%m%d) 紧凑格式"""
        result = call_function("date", ["today", "%Y%m%d"])
        assert result == datetime.now().strftime("%Y%m%d")

    def test_date_time_default(self):
        """date(time) 返回 HH:MM:SS"""
        result = call_function("date", ["time"])
        datetime.strptime(result, "%H:%M:%S")

    def test_date_timestamp(self):
        """date(timestamp) 返回 Unix 时间戳（秒）"""
        result = call_function("date", ["timestamp"])
        ts = int(result)
        assert abs(ts - int(time.time())) <= 1

    def test_date_timestamp_ms(self):
        """date(timestamp_ms) 返回毫秒时间戳"""
        result = call_function("date", ["timestamp_ms"])
        ts = int(result)
        assert abs(ts - int(time.time() * 1000)) < 1000

    def test_date_offset_days_positive(self):
        """date(offset, 30) 返回 30 天后日期"""
        result = call_function("date", ["offset", "30"])
        expected = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        assert result == expected

    def test_date_offset_days_negative(self):
        """date(offset, -7) 返回 7 天前日期"""
        result = call_function("date", ["offset", "-7"])
        expected = (datetime.now() + timedelta(days=-7)).strftime("%Y-%m-%d")
        assert result == expected

    def test_date_offset_days_with_format(self):
        """date(offset, 1, %Y%m%d) 偏移+自定义格式"""
        result = call_function("date", ["offset", "1", "%Y%m%d"])
        expected = (datetime.now() + timedelta(days=1)).strftime("%Y%m%d")
        assert result == expected

    def test_date_offset_hours(self):
        """date(offset, -2h) 返回 2 小时前"""
        result = call_function("date", ["offset", "-2h"])
        dt = datetime.strptime(result, "%Y-%m-%d %H:%M:%S")
        expected = datetime.now() + timedelta(hours=-2)
        assert abs((dt - expected).total_seconds()) < 2

    def test_date_offset_hours_with_format(self):
        """date(offset, -1h, %H:%M) 小时偏移+自定义格式"""
        result = call_function("date", ["offset", "-1h", "%H:%M"])
        expected = (datetime.now() + timedelta(hours=-1)).strftime("%H:%M")
        assert result == expected

    def test_date_unknown_type_raises(self):
        """date(xxx) 未知 type 抛出 ValueError"""
        with pytest.raises(ValueError, match="不支持类型"):
            call_function("date", ["xxx"])


class TestCallFunctionErrors:
    """call_function 错误处理"""

    def test_unknown_function_raises(self):
        """未注册的函数名抛出 ValueError"""
        with pytest.raises(ValueError, match="未知内置函数"):
            call_function("nonexistent", ["int"])


class TestDataResolverIntegration:
    """DataResolver 集成内置函数解析测试"""

    def test_resolve_random_in_text(self):
        """resolve_with_return 解析 ${random(int, 1, 9)}"""
        from data.data_resolver import DataResolver
        resolver = DataResolver()
        result = resolver.resolve_with_return("user_${random(int, 1000, 9999)}")
        assert result.startswith("user_")
        assert result[5:].isdigit()
        assert 1000 <= int(result[5:]) <= 9999

    def test_resolve_date_in_text(self):
        """resolve_with_return 解析 ${date(today)}"""
        from data.data_resolver import DataResolver
        resolver = DataResolver()
        result = resolver.resolve_with_return("day_${date(today)}")
        assert result == f"day_{datetime.now().strftime('%Y-%m-%d')}"

    def test_resolve_multiple_functions(self):
        """多个函数串联拼接"""
        from data.data_resolver import DataResolver
        resolver = DataResolver()
        result = resolver.resolve_with_return("${random(str, 3)}_${date(today, %Y%m%d)}")
        parts = result.split("_")
        assert len(parts[0]) == 3
        assert parts[1] == datetime.now().strftime("%Y%m%d")

    def test_resolve_function_with_static_text(self):
        """函数前后拼接静态文本"""
        from data.data_resolver import DataResolver
        resolver = DataResolver()
        result = resolver.resolve_with_return("prefix_${random(digits, 4)}_suffix")
        assert result.startswith("prefix_")
        assert result.endswith("_suffix")
        middle = result[7:-7]
        assert len(middle) == 4
        assert middle.isdigit()

    def test_resolve_unknown_function_kept(self):
        """未知函数保持原样不解析"""
        from data.data_resolver import DataResolver
        resolver = DataResolver()
        result = resolver.resolve_with_return("${unknown_func(abc)}")
        assert result == "${unknown_func(abc)}"

    def test_resolve_return_priority_over_function(self):
        """${Return[N]} 优先于函数解析"""
        from data.data_resolver import DataResolver
        resolver = DataResolver(return_provider=lambda idx: "returned_value")
        result = resolver.resolve_with_return("${Return[-1]}")
        assert result == "returned_value"

    def test_resolve_escape(self):
        """$${...} 转义为字面量 ${...}"""
        from data.data_resolver import DataResolver
        resolver = DataResolver()
        result = resolver.resolve_with_return("$${random(int, 1, 9)}")
        assert result == "${random(int, 1, 9)}"

    def test_resolve_no_function_unchanged(self):
        """无函数表达式的文本不变"""
        from data.data_resolver import DataResolver
        resolver = DataResolver()
        result = resolver.resolve_with_return("plain text 123")
        assert result == "plain text 123"
