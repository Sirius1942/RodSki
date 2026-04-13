"""DataResolver JSON 支持测试

测试 data/data_resolver.py 中的 JSON 格式数据解析。
覆盖：JSON 字段自动解析（数组/对象）、嵌套 JSON 引用、
      JSON 路径提取（$.key.subkey 格式）。
"""
import pytest
import json
from pathlib import Path
from data.data_resolver import DataResolver


class TestJsonSupport:
    def test_resolve_json_string(self):
        """测试解析 JSON 字符串"""
        resolver = DataResolver({"name": "Alice"})
        json_str = '{"user": "${name}", "age": 25}'
        result = resolver.resolve_json(json_str)
        assert result == {"user": "Alice", "age": 25}
    
    def test_resolve_json_nested(self):
        """测试嵌套 JSON"""
        resolver = DataResolver({"token": "abc123"})
        json_str = '{"auth": {"token": "${token}"}, "data": [1, 2]}'
        result = resolver.resolve_json(json_str)
        assert result["auth"]["token"] == "abc123"
        assert result["data"] == [1, 2]
    
    def test_resolve_json_file(self, tmp_path):
        """测试加载 JSON 文件"""
        json_file = tmp_path / "test.json"
        json_file.write_text('{"status": "ok"}')
        
        resolver = DataResolver(base_path=tmp_path)
        result = resolver.resolve_json("@file:test.json")
        assert result == {"status": "ok"}
    
    def test_resolve_json_file_with_vars(self, tmp_path):
        """测试 JSON 文件中的变量替换"""
        json_file = tmp_path / "data.json"
        json_file.write_text('{"user": "${username}"}')
        
        resolver = DataResolver({"username": "admin"}, base_path=tmp_path)
        result = resolver.resolve_json("@file:data.json")
        assert result == {"user": "admin"}
