"""DataSchemaValidator 单元测试"""
import pytest
from core.data_schema_validator import DataSchemaValidator
from core.exceptions import DataParseError


class TestCheckSqliteSchema:
    def test_valid(self):
        tables = {"Login": {"L001": {"username": "a", "password": "b"}}}
        schemas = {"Login": ["username", "password"]}
        DataSchemaValidator.check_sqlite_schema(tables, schemas)

    def test_missing_schema_raises(self):
        tables = {"Login": {"L001": {"username": "a"}}}
        with pytest.raises(DataParseError, match="缺少 schema"):
            DataSchemaValidator.check_sqlite_schema(tables, {})

    def test_missing_field_raises(self):
        tables = {"Login": {"L001": {"username": "a"}}}
        schemas = {"Login": ["username", "password"]}
        with pytest.raises(DataParseError, match="缺少字段"):
            DataSchemaValidator.check_sqlite_schema(tables, schemas)

    def test_extra_field_raises(self):
        tables = {"Login": {"L001": {"username": "a", "extra": "x"}}}
        schemas = {"Login": ["username"]}
        with pytest.raises(DataParseError, match="多余字段"):
            DataSchemaValidator.check_sqlite_schema(tables, schemas)
