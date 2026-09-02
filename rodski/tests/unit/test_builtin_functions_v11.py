"""v11.0.0 内置函数单元测试"""

import pytest
from rodski.data.builtin_functions import call_function


class TestBuiltinFunctionsV11:
    """测试 v11.0.0 新增的 5 个内置函数"""

    def test_encodeURI_basic(self):
        """测试 encodeURI 基本功能"""
        result = call_function("encodeURI", ["hello world"])
        assert result == "hello%20world"

    def test_encodeURI_special_chars(self):
        """测试 encodeURI 特殊字符"""
        result = call_function("encodeURI", ["hello&world=123"])
        assert "hello%26world%3D123" in result

    def test_decodeURI_basic(self):
        """测试 decodeURI 基本功能"""
        result = call_function("decodeURI", ["hello%20world"])
        assert result == "hello world"

    def test_encodeURI_decodeURI_roundtrip(self):
        """测试 encodeURI/decodeURI 往返"""
        original = "hello world & test=123"
        encoded = call_function("encodeURI", [original])
        decoded = call_function("decodeURI", [encoded])
        assert decoded == original

    def test_toUpperCase_basic(self):
        """测试 toUpperCase 基本功能"""
        result = call_function("toUpperCase", ["hello"])
        assert result == "HELLO"

    def test_toUpperCase_mixed_case(self):
        """测试 toUpperCase 混合大小写"""
        result = call_function("toUpperCase", ["Hello World"])
        assert result == "HELLO WORLD"

    def test_toLowerCase_basic(self):
        """测试 toLowerCase 基本功能"""
        result = call_function("toLowerCase", ["HELLO"])
        assert result == "hello"

    def test_toLowerCase_mixed_case(self):
        """测试 toLowerCase 混合大小写"""
        result = call_function("toLowerCase", ["Hello World"])
        assert result == "hello world"

    def test_toString36_zero(self):
        """测试 toString36 零值"""
        result = call_function("toString36", ["0"])
        assert result == "0"

    def test_toString36_positive(self):
        """测试 toString36 正数"""
        result = call_function("toString36", ["1234567890"])
        assert result == "KF12OI"

    def test_toString36_small_number(self):
        """测试 toString36 小数"""
        result = call_function("toString36", ["35"])
        assert result == "Z"

        result = call_function("toString36", ["36"])
        assert result == "10"

    def test_toString36_negative(self):
        """测试 toString36 负数"""
        result = call_function("toString36", ["-100"])
        assert result.startswith("-")

    def test_toString36_invalid_input(self):
        """测试 toString36 非法输入"""
        with pytest.raises(ValueError, match="toString36 需要整数参数"):
            call_function("toString36", ["not_a_number"])

    def test_backward_compatibility_upper(self):
        """测试向后兼容：upper 别名仍可用"""
        result = call_function("upper", ["hello"])
        assert result == "HELLO"

    def test_backward_compatibility_lower(self):
        """测试向后兼容：lower 别名仍可用"""
        result = call_function("lower", ["HELLO"])
        assert result == "hello"

    def test_backward_compatibility_timestamp36(self):
        """测试向后兼容：timestamp36 仍可用"""
        result = call_function("timestamp36", [])
        assert len(result) > 0
        assert result.isupper()
        assert all(c in "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ" for c in result)
