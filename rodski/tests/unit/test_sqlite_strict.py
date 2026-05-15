"""SQLite 严格字段一致性校验 — T42-001

验证 DataSchemaValidator.check_sqlite_schema() 对缺失字段和多余字段的检测。
CORE_DESIGN_CONSTRAINTS.md 要求：同一逻辑表所有行字段集合必须与 schema 完全一致。
"""
import pytest
from core.data_schema_validator import DataSchemaValidator
from core.exceptions import DataParseError


class TestStrictFieldConsistency:
    """严格模式：缺失字段和多余字段均报错"""

    def test_exact_match_passes(self):
        """行字段与 schema 完全一致 → 通过"""
        tables = {
            "Order": {
                "O001": {"product": "Widget", "qty": "10", "price": "9.99"},
                "O002": {"product": "Gadget", "qty": "5", "price": "19.99"},
            }
        }
        schemas = {"Order": ["product", "qty", "price"]}
        # 不应抛异常
        DataSchemaValidator.check_sqlite_schema(tables, schemas)

    def test_missing_fields_raises(self):
        """行缺少 schema 中声明的字段 → 报错，列出缺失字段"""
        tables = {
            "Login": {
                "L001": {"username": "admin"},  # 缺少 password, captcha
            }
        }
        schemas = {"Login": ["username", "password", "captcha"]}
        with pytest.raises(DataParseError, match=r"missing=\['captcha', 'password'\]"):
            DataSchemaValidator.check_sqlite_schema(tables, schemas)

    def test_extra_fields_raises(self):
        """行包含 schema 中未定义的字段 → 报错，列出多余字段"""
        tables = {
            "Login": {
                "L001": {"username": "admin", "password": "pw", "token": "abc"},
            }
        }
        schemas = {"Login": ["username", "password"]}
        with pytest.raises(DataParseError, match=r"extra=\['token'\]"):
            DataSchemaValidator.check_sqlite_schema(tables, schemas)

    def test_both_missing_and_extra_raises(self):
        """同时存在缺失和多余字段 → 报错，两者都列出"""
        tables = {
            "Login": {
                "L001": {"username": "admin", "unknown": "x"},
            }
        }
        schemas = {"Login": ["username", "password"]}
        with pytest.raises(DataParseError) as exc_info:
            DataSchemaValidator.check_sqlite_schema(tables, schemas)
        msg = str(exc_info.value)
        assert "missing=['password']" in msg
        assert "extra=['unknown']" in msg

    def test_error_contains_table_name_and_row_id(self):
        """错误信息包含表名和行 ID"""
        tables = {
            "UserProfile": {
                "UP003": {"name": "test"},  # 缺少 email
            }
        }
        schemas = {"UserProfile": ["name", "email"]}
        with pytest.raises(DataParseError) as exc_info:
            DataSchemaValidator.check_sqlite_schema(tables, schemas)
        msg = str(exc_info.value)
        assert "UserProfile.UP003" in msg

    def test_error_contains_guidance_message(self):
        """错误信息包含填写 BLANK/NULL/NONE 的提示"""
        tables = {
            "Login": {
                "L001": {"username": "admin"},
            }
        }
        schemas = {"Login": ["username", "password"]}
        with pytest.raises(DataParseError, match="缺字段必须显式填 BLANK/NULL/NONE，不能省略"):
            DataSchemaValidator.check_sqlite_schema(tables, schemas)

    def test_multiple_rows_first_bad_row_reported(self):
        """多行中第一个不一致的行被报告"""
        tables = {
            "Login": {
                "L001": {"username": "admin", "password": "pw"},  # OK
                "L002": {"username": "user"},  # 缺少 password
            }
        }
        schemas = {"Login": ["username", "password"]}
        with pytest.raises(DataParseError, match="Login.L002"):
            DataSchemaValidator.check_sqlite_schema(tables, schemas)
