"""Unit tests for the isolated business-model parser, validator and executor."""
import sqlite3
from pathlib import Path

import pytest

from core.business_model import (
    BusinessModelExecutionError,
    BusinessModelExecutor,
    BusinessModelParseError,
    BusinessModelParser,
    BusinessModelValidationError,
    BusinessModelValidator,
)

DEMO_XML = Path(__file__).parents[3] / "rodski-demo" / "DEMO" / "demo_business_model" / "business" / "business.xml"


def _model():
    return BusinessModelParser().parse_file(DEMO_XML)["login_flow"]


def _tables():
    return {
        "login_flow": {
            "OK": {"username": "admin", "password": "good"},
            "BAD": {"username": "admin", "password": "bad"},
        },
        "login_flow_verify": {
            "OK": {"login_status": "success", "message": "登录成功", "expected_path": "open_login>submit_login>validate_login>home"},
            "BAD": {"login_status": "invalid_credentials", "message": "用户名或密码错误", "expected_path": "open_login>submit_login>validate_login>error"},
        },
    }


def _runner(step, context):
    if step.action == "send":
        row = context["Input"]
        if row.get("username") == "locked":
            status, message = "locked", "账号已锁定"
        elif row.get("password") == "good":
            status, message = "success", "登录成功"
        else:
            status, message = "invalid_credentials", "用户名或密码错误"
        return {"login_status": status, "message": message}
    return {}


def test_parse_demo_and_derive_standard_table_names():
    model = _model()
    assert model.input_table == "login_flow"
    assert model.verify_table == "login_flow_verify"
    assert set(model.flows) == {"F_LOGIN_SUCCESS", "F_LOGIN_INVALID", "F_LOGIN_LOCKED"}
    assert len(model.nodes["validate_login"].steps) == 0


def test_actual_data_selects_graph_branch_and_matching_expectation_passes():
    executor = BusinessModelExecutor(_model(), _tables(), step_runner=_runner)
    result = executor.execute("F_LOGIN_SUCCESS", "OK", "OK")
    assert result.passed
    assert result.actual_path[-1] == "home"
    assert result.actual["login_status"] == "success"


def test_flow_is_expectation_not_branch_control_and_mismatch_fails():
    executor = BusinessModelExecutor(_model(), _tables(), step_runner=_runner)
    result = executor.execute("F_LOGIN_SUCCESS", "BAD", "BAD")
    assert not result.passed
    assert result.actual_path[-1] == "error"
    assert any("Path mismatch" in error for error in result.assertion_errors)


def test_actual_field_mismatch_fails_even_when_path_matches():
    executor = BusinessModelExecutor(_model(), _tables(), step_runner=_runner)
    data = _tables()
    data["login_flow_verify"]["WRONG"] = {"login_status": "invalid_credentials", "message": "wrong"}
    result = BusinessModelExecutor(_model(), data, step_runner=_runner).execute("F_LOGIN_SUCCESS", "OK", "WRONG")
    assert not result.passed
    assert any("Field 'message'" in error for error in result.assertion_errors)


def test_missing_ids_and_unknown_flow_are_errors():
    executor = BusinessModelExecutor(_model(), _tables(), step_runner=_runner)
    with pytest.raises(BusinessModelExecutionError, match="not found"):
        executor.execute("F_LOGIN_SUCCESS", "MISSING", "OK")
    with pytest.raises(BusinessModelExecutionError, match="Unknown flow"):
        executor.execute("NO_FLOW", "OK", "OK")


def test_validator_rejects_unsafe_condition_after_xsd_valid_parse():
    xml = '''<business_models version="0.1"><business_model id="m" name="M" version="1">
      <nodes><node id="a"/><node id="b"/></nodes>
      <edges><edge from="a" to="b" condition="__import__('os')"/></edges>
      <flows><flow id="f" type="basic" path="a&gt;b"/></flows>
    </business_model></business_models>'''
    unsafe = BusinessModelParser().parse_string(xml)["m"]
    with pytest.raises(BusinessModelValidationError, match="Unsupported syntax"):
        BusinessModelValidator.validate(unsafe)


def test_parser_rejects_duplicate_ids_and_malformed_xml():
    parser = BusinessModelParser()
    # Duplicate-ID semantic validation is independent of XSD; use parse_element
    # to isolate it from the parser's deliberate XSD validation layer.
    import xml.etree.ElementTree as ET
    with pytest.raises(BusinessModelParseError, match="Duplicate"):
        parser.parse_element(ET.fromstring(
            '<business_models version="0.1">'
            '<business_model id="x" name="X" version="1"><nodes><node id="a"/><node id="b"/></nodes>'
            '<edges><edge from="a" to="b"/></edges><flows><flow id="f" type="basic" path="a&gt;b"/></flows></business_model>'
            '<business_model id="x" name="X2" version="1"><nodes><node id="a"/><node id="b"/></nodes>'
            '<edges><edge from="a" to="b"/></edges><flows><flow id="f" type="basic" path="a&gt;b"/></flows></business_model>'
            '</business_models>'
        ))
    with pytest.raises(BusinessModelParseError):
        parser.parse_string("<business_models>")


def test_sqlite_data_source_requires_ordinary_data_and_verify_tables(tmp_path):
    db = tmp_path / "data.sqlite"
    with sqlite3.connect(db) as conn:
        conn.executescript("""
            CREATE TABLE rs_datatable(table_name TEXT PRIMARY KEY, model_name TEXT, table_kind TEXT, row_mode TEXT, remark TEXT, updated_at TEXT);
            CREATE TABLE rs_datatable_field(table_name TEXT, field_name TEXT, field_order INTEGER);
            CREATE TABLE rs_row(table_name TEXT, data_id TEXT, remark TEXT);
            CREATE TABLE rs_field(table_name TEXT, data_id TEXT, field_name TEXT, field_value TEXT);
            INSERT INTO rs_datatable VALUES('login_flow','login_flow','data','standard','','');
            INSERT INTO rs_datatable VALUES('login_flow_verify','login_flow','verify','standard','','');
            INSERT INTO rs_datatable_field VALUES('login_flow','password',0);
            INSERT INTO rs_row VALUES('login_flow','OK','');
            INSERT INTO rs_field VALUES('login_flow','OK','password','good');
            INSERT INTO rs_datatable_field VALUES('login_flow_verify','login_status',0);
            INSERT INTO rs_row VALUES('login_flow_verify','OK','');
            INSERT INTO rs_field VALUES('login_flow_verify','OK','login_status','success');
        """)
    from core.sqlite_data_source import SQLiteDataSource
    source = SQLiteDataSource(str(db))
    executor = BusinessModelExecutor(_model(), data_source=source, step_runner=_runner)
    assert executor.data_tables["login_flow"]["OK"]["password"] == "good"
    source.close()
