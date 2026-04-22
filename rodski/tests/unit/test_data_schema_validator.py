"""DataSchemaValidator 单元测试"""
import pytest
from core.data_schema_validator import DataSchemaValidator
from core.exceptions import DataParseError


class TestCrossSourceConflict:
    def test_no_conflict(self):
        DataSchemaValidator.check_cross_source_conflict({"Login"}, {"Order"})

    def test_conflict_raises(self):
        with pytest.raises(DataParseError, match="Login"):
            DataSchemaValidator.check_cross_source_conflict({"Login"}, {"Login"})

    def test_empty_sets(self):
        DataSchemaValidator.check_cross_source_conflict(set(), set())


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


class TestXmlColumnDrift:
    def test_no_drift(self):
        tables = {"Login": {"L001": {"a": "1"}, "L002": {"a": "2"}}}
        assert DataSchemaValidator.check_xml_column_drift(tables) == []

    def test_drift_detected(self):
        tables = {"Login": {"L001": {"a": "1"}, "L002": {"a": "1", "b": "2"}}}
        warnings = DataSchemaValidator.check_xml_column_drift(tables)
        assert len(warnings) == 1
        assert "Login" in warnings[0]
