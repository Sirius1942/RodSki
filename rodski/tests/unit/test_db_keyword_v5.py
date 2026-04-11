"""DB 关键字 v5.0 单元测试

测试新语法的 DB 关键字实现：
- 模型解析（database 类型）
- 参数化查询（:param 替换）
- 大数据量截断
- 旧语法报错
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# 添加 rodski 到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.keyword_engine import KeywordEngine
from core.exceptions import InvalidParameterError, DriverError


class TestDBKeywordV5:
    """DB 关键字 v5.0 测试"""

    def setup_method(self):
        """每个测试前的准备"""
        self.driver = Mock()
        self.model_parser = Mock()
        self.data_manager = Mock()

        self.engine = KeywordEngine(
            driver=self.driver,
            model_parser=self.model_parser,
            data_manager=self.data_manager,
            global_vars={}
        )

    def test_replace_params_string(self):
        """测试字符串参数替换"""
        sql = "SELECT * FROM orders WHERE status = :status"
        params = {"status": "completed"}

        result = self.engine._replace_sql_params(sql, params)

        assert result == "SELECT * FROM orders WHERE status = 'completed'"

    def test_replace_params_number(self):
        """测试数字参数替换"""
        sql = "SELECT * FROM orders LIMIT :limit"
        params = {"limit": 10}

        result = self.engine._replace_sql_params(sql, params)

        assert result == "SELECT * FROM orders LIMIT 10"

    def test_replace_params_multiple(self):
        """测试多个参数替换"""
        sql = "SELECT * FROM orders WHERE status = :status AND price > :price LIMIT :limit"
        params = {"status": "completed", "price": 100.5, "limit": 5}

        result = self.engine._replace_sql_params(sql, params)

        assert result == "SELECT * FROM orders WHERE status = 'completed' AND price > 100.5 LIMIT 5"

    def test_replace_params_null(self):
        """测试 NULL 参数替换"""
        sql = "SELECT * FROM orders WHERE note = :note"
        params = {"note": None}

        result = self.engine._replace_sql_params(sql, params)

        assert result == "SELECT * FROM orders WHERE note = NULL"

    def test_replace_params_missing(self):
        """测试缺少参数时报错"""
        sql = "SELECT * FROM orders WHERE status = :status"
        params = {}

        with pytest.raises(InvalidParameterError) as exc_info:
            self.engine._replace_sql_params(sql, params)

        assert "status" in str(exc_info.value)

    def test_replace_params_escape_quotes(self):
        """测试单引号转义"""
        sql = "SELECT * FROM orders WHERE note = :note"
        params = {"note": "It's a test"}

        result = self.engine._replace_sql_params(sql, params)

        assert result == "SELECT * FROM orders WHERE note = 'It''s a test'"

    def test_truncate_under_limit(self):
        """测试小于 1000 行不截断"""
        result = [{"id": i} for i in range(100)]

        truncated = self.engine._truncate_result(result)

        assert truncated == result
        assert len(truncated) == 100

    def test_truncate_over_limit(self):
        """测试超过 1000 行自动截断"""
        result = [{"id": i} for i in range(1500)]

        truncated = self.engine._truncate_result(result)

        assert isinstance(truncated, dict)
        assert truncated['_truncated'] is True
        assert truncated['_total_rows'] == 1500
        assert truncated['_limit'] == 1000
        assert len(truncated['data']) == 1000

    def test_truncate_exactly_limit(self):
        """测试正好 1000 行不截断"""
        result = [{"id": i} for i in range(1000)]

        truncated = self.engine._truncate_result(result)

        assert truncated == result
        assert len(truncated) == 1000

    def test_old_syntax_error(self):
        """测试旧语法直接报错"""
        params = {
            "model": "OrderQuery",
            "data": "QuerySQL.Q001"  # 旧语法格式
        }

        with pytest.raises(InvalidParameterError) as exc_info:
            self.engine._kw_db(params)

        error_msg = str(exc_info.value)
        assert "旧语法" in error_msg or "v5.0" in error_msg
        assert "迁移" in error_msg

    def test_missing_model(self):
        """测试缺少 model 参数"""
        params = {"data": "Q001"}

        with pytest.raises(InvalidParameterError) as exc_info:
            self.engine._kw_db(params)

        assert "model" in str(exc_info.value).lower()

    def test_missing_data(self):
        """测试缺少 data 参数"""
        params = {"model": "OrderQuery"}

        with pytest.raises(InvalidParameterError) as exc_info:
            self.engine._kw_db(params)

        assert "data" in str(exc_info.value).lower()

    def test_model_not_found(self):
        """测试模型不存在"""
        params = {"model": "NonExistModel", "data": "Q001"}
        self.model_parser.get_database_model.return_value = None
        self.model_parser.get_model_type.return_value = None

        with pytest.raises(InvalidParameterError) as exc_info:
            self.engine._kw_db(params)

        assert "NonExistModel" in str(exc_info.value)

    def test_model_wrong_type(self):
        """测试模型类型错误"""
        params = {"model": "LoginPage", "data": "Q001"}
        self.model_parser.get_database_model.return_value = None
        self.model_parser.get_model_type.return_value = "ui"

        with pytest.raises(InvalidParameterError) as exc_info:
            self.engine._kw_db(params)

        error_msg = str(exc_info.value)
        assert "ui" in error_msg
        assert "database" in error_msg

    def test_missing_connection(self):
        """测试模型缺少 connection 属性"""
        params = {"model": "OrderQuery", "data": "Q001"}
        self.model_parser.get_database_model.return_value = {
            "type": "database",
            "connection": "",
            "queries": {}
        }

        with pytest.raises(InvalidParameterError) as exc_info:
            self.engine._kw_db(params)

        assert "connection" in str(exc_info.value).lower()

    @patch.object(KeywordEngine, '_get_db_connection')
    @patch.object(KeywordEngine, '_execute_db_sql')
    def test_query_with_template(self, mock_execute, mock_get_conn):
        """测试使用模型查询模板"""
        params = {"model": "OrderQuery", "data": "Q001"}

        # Mock 模型
        self.model_parser.get_database_model.return_value = {
            "type": "database",
            "connection": "sqlite_db",
            "queries": {
                "list": {
                    "sql": "SELECT * FROM orders WHERE status = :status LIMIT :limit",
                    "remark": "查询列表"
                }
            }
        }

        # Mock 数据表
        self.data_manager.get_data.return_value = {
            "query": "list",
            "status": "completed",
            "limit": 10
        }

        # Mock 连接和执行
        mock_conn = Mock()
        mock_get_conn.return_value = mock_conn
        mock_execute.return_value = [{"id": 1}, {"id": 2}]

        result = self.engine._kw_db(params)

        assert result is True
        mock_execute.assert_called_once()
        call_args = mock_execute.call_args
        assert "status = 'completed'" in call_args[0][2]
        assert "LIMIT 10" in call_args[0][2]

    @patch.object(KeywordEngine, '_get_db_connection')
    @patch.object(KeywordEngine, '_execute_db_sql')
    def test_query_with_direct_sql(self, mock_execute, mock_get_conn):
        """测试数据表直接写 SQL"""
        params = {"model": "OrderQuery", "data": "Q001"}

        # Mock 模型
        self.model_parser.get_database_model.return_value = {
            "type": "database",
            "connection": "sqlite_db",
            "queries": {}
        }

        # Mock 数据表（直接写 SQL）
        self.data_manager.get_data.return_value = {
            "sql": "SELECT * FROM orders LIMIT 5",
            "operation": "query"
        }

        # Mock 连接和执行
        mock_conn = Mock()
        mock_get_conn.return_value = mock_conn
        mock_execute.return_value = [{"id": 1}]

        result = self.engine._kw_db(params)

        assert result is True
        mock_execute.assert_called_once()

    def test_data_row_not_found(self):
        """测试数据行不存在"""
        params = {"model": "OrderQuery", "data": "Q999"}

        self.model_parser.get_database_model.return_value = {
            "type": "database",
            "connection": "sqlite_db",
            "queries": {}
        }
        self.data_manager.get_data.return_value = None

        with pytest.raises(InvalidParameterError) as exc_info:
            self.engine._kw_db(params)

        assert "Q999" in str(exc_info.value)

    def test_query_not_found_in_model(self):
        """测试查询名称在模型中不存在"""
        params = {"model": "OrderQuery", "data": "Q001"}

        self.model_parser.get_database_model.return_value = {
            "type": "database",
            "connection": "sqlite_db",
            "queries": {
                "list": {"sql": "SELECT * FROM orders", "remark": ""}
            }
        }
        self.data_manager.get_data.return_value = {
            "query": "get_by_id"  # 不存在的查询
        }

        with pytest.raises(InvalidParameterError) as exc_info:
            self.engine._kw_db(params)

        error_msg = str(exc_info.value)
        assert "get_by_id" in error_msg
        assert "list" in error_msg


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
