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
        with pytest.raises(DataParseError, match="missing="):
            DataSchemaValidator.check_sqlite_schema(tables, schemas)

    def test_extra_field_raises(self):
        tables = {"Login": {"L001": {"username": "a", "extra": "x"}}}
        schemas = {"Login": ["username"]}
        with pytest.raises(DataParseError, match="extra="):
            DataSchemaValidator.check_sqlite_schema(tables, schemas)

    def test_missing_and_extra_both_present_joined_by_comma_space(self):
        """同时缺字段和多字段时，错误信息应用 ', ' 拼接 missing 和 extra 两部分"""
        tables = {"Login": {"L001": {"password": "b", "extra": "x"}}}
        schemas = {"Login": ["username", "password"]}
        with pytest.raises(DataParseError, match=r"missing=\['username'\], extra=\['extra'\]"):
            DataSchemaValidator.check_sqlite_schema(tables, schemas)
