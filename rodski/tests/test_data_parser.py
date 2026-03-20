"""测试数据引用解析器"""
import pytest
from pathlib import Path
from core.data_parser import DataParser
from unittest.mock import Mock, patch
import tempfile
import openpyxl


@pytest.fixture
def temp_data_dir():
    """创建临时数据目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_excel(temp_data_dir):
    """创建示例Excel数据文件"""
    excel_path = temp_data_dir / "LoginData.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active

    # 添加表头
    ws.append(["id", "username", "password", "email"])
    # 添加数据行
    ws.append(["L001", "admin", "admin123", "admin@test.com"])
    ws.append(["L002", "user1", "pass456", "user1@test.com"])
    ws.append(["L003", "guest", "guest789", "guest@test.com"])

    wb.save(excel_path)
    wb.close()
    return excel_path


class TestDataParser:
    def test_init_default_dir(self):
        """测试默认初始化"""
        parser = DataParser()
        assert parser.data_dir == Path.cwd() / "data"
        assert parser._cache == {}

    def test_init_custom_dir(self, temp_data_dir):
        """测试自定义数据目录"""
        parser = DataParser(temp_data_dir)
        assert parser.data_dir == temp_data_dir

    def test_resolve_simple_reference(self, temp_data_dir, sample_excel):
        """测试简单数据引用"""
        parser = DataParser(temp_data_dir)
        result = parser.resolve("${LoginData.L001.username}")
        assert result == "admin"

    def test_resolve_multiple_references(self, temp_data_dir, sample_excel):
        """测试多个数据引用"""
        parser = DataParser(temp_data_dir)
        text = "User: ${LoginData.L001.username}, Pass: ${LoginData.L001.password}"
        result = parser.resolve(text)
        assert result == "User: admin, Pass: admin123"

    def test_resolve_nested_references(self, temp_data_dir, sample_excel):
        """测试嵌套引用"""
        parser = DataParser(temp_data_dir)
        text = "Login with ${LoginData.L002.username} and email ${LoginData.L002.email}"
        result = parser.resolve(text)
        assert result == "Login with user1 and email user1@test.com"

    def test_resolve_invalid_table(self, temp_data_dir):
        """测试无效的数据表"""
        parser = DataParser(temp_data_dir)
        result = parser.resolve("${InvalidTable.ID001.field}")
        assert result == "${InvalidTable.ID001.field}"

    def test_resolve_invalid_id(self, temp_data_dir, sample_excel):
        """测试无效的数据ID"""
        parser = DataParser(temp_data_dir)
        result = parser.resolve("${LoginData.L999.username}")
        assert result == "${LoginData.L999.username}"

    def test_resolve_invalid_field(self, temp_data_dir, sample_excel):
        """测试无效的字段名"""
        parser = DataParser(temp_data_dir)
        result = parser.resolve("${LoginData.L001.invalid_field}")
        assert result == "${LoginData.L001.invalid_field}"

    def test_resolve_non_string(self, temp_data_dir):
        """测试非字符串输入"""
        parser = DataParser(temp_data_dir)
        assert parser.resolve(123) == "123"
        assert parser.resolve(None) == ""

    def test_get_value(self, temp_data_dir, sample_excel):
        """测试直接获取值"""
        parser = DataParser(temp_data_dir)
        value = parser.get_value("LoginData", "L001", "username")
        assert value == "admin"

    def test_get_value_cache(self, temp_data_dir, sample_excel):
        """测试缓存机制"""
        parser = DataParser(temp_data_dir)
        # 第一次调用会加载数据
        value1 = parser.get_value("LoginData", "L001", "username")
        # 第二次调用应该使用缓存
        value2 = parser.get_value("LoginData", "L001", "password")
        assert value1 == "admin"
        assert value2 == "admin123"
        assert "LoginData" in parser._cache

    def test_resolve_params_simple(self, temp_data_dir, sample_excel):
        """测试解析简单参数字典"""
        parser = DataParser(temp_data_dir)
        params = {
            "username": "${LoginData.L001.username}",
            "password": "${LoginData.L001.password}"
        }
        result = parser.resolve_params(params)
        assert result["username"] == "admin"
        assert result["password"] == "admin123"

    def test_resolve_params_nested_dict(self, temp_data_dir, sample_excel):
        """测试解析嵌套字典"""
        parser = DataParser(temp_data_dir)
        params = {
            "user": {
                "name": "${LoginData.L002.username}",
                "email": "${LoginData.L002.email}"
            }
        }
        result = parser.resolve_params(params)
        assert result["user"]["name"] == "user1"
        assert result["user"]["email"] == "user1@test.com"

    def test_resolve_params_list(self, temp_data_dir, sample_excel):
        """测试解析列表参数"""
        parser = DataParser(temp_data_dir)
        params = {
            "users": [
                "${LoginData.L001.username}",
                "${LoginData.L002.username}",
                "${LoginData.L003.username}"
            ]
        }
        result = parser.resolve_params(params)
        assert result["users"] == ["admin", "user1", "guest"]

    def test_resolve_params_mixed_types(self, temp_data_dir, sample_excel):
        """测试混合类型参数"""
        parser = DataParser(temp_data_dir)
        params = {
            "text": "${LoginData.L001.username}",
            "number": 123,
            "boolean": True,
            "none": None
        }
        result = parser.resolve_params(params)
        assert result["text"] == "admin"
        assert result["number"] == 123
        assert result["boolean"] is True
        assert result["none"] is None

    def test_clear_cache(self, temp_data_dir, sample_excel):
        """测试清空缓存"""
        parser = DataParser(temp_data_dir)
        parser.get_value("LoginData", "L001", "username")
        assert len(parser._cache) > 0
        parser.clear_cache()
        assert len(parser._cache) == 0

    def test_load_table_error_handling(self, temp_data_dir):
        """测试加载表时的错误处理"""
        parser = DataParser(temp_data_dir)
        # 不存在的文件不应该抛出异常
        result = parser.get_value("NonExistent", "ID", "field")
        assert result is None



