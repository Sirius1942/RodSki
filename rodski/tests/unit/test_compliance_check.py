"""合规检查聚合函数测试（v8.2.0 Hooks 机制，on_run_start 前置检查）"""
import sqlite3

import pytest

from core.compliance_check import (
    check_directory_structure,
    scan_return_ref_violations,
    run_compliance_checks,
    ComplianceReport,
)


def _make_sqlite(module_dir, table_name, schema_fields, row_fields):
    data_dir = module_dir / "data"
    data_dir.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(data_dir / "data.sqlite"))
    conn.executescript("""
        CREATE TABLE rs_datatable (table_name TEXT PRIMARY KEY, model_name TEXT NOT NULL,
            table_kind TEXT NOT NULL, row_mode TEXT NOT NULL, remark TEXT DEFAULT '', updated_at TEXT DEFAULT '');
        CREATE TABLE rs_datatable_field (table_name TEXT NOT NULL, field_name TEXT NOT NULL,
            field_order INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (table_name, field_name));
        CREATE TABLE rs_row (table_name TEXT NOT NULL, data_id TEXT NOT NULL,
            remark TEXT DEFAULT '', PRIMARY KEY (table_name, data_id));
        CREATE TABLE rs_field (table_name TEXT NOT NULL, data_id TEXT NOT NULL,
            field_name TEXT NOT NULL, field_value TEXT NOT NULL,
            PRIMARY KEY (table_name, data_id, field_name));
    """)
    conn.execute(
        "INSERT INTO rs_datatable VALUES (?,?,?,?,?,?)",
        (table_name, table_name, "verify", "standard", "", ""),
    )
    for order, field_name in enumerate(schema_fields):
        conn.execute(
            "INSERT INTO rs_datatable_field VALUES (?,?,?)",
            (table_name, field_name, order),
        )
    conn.execute("INSERT INTO rs_row VALUES (?,?,?)", (table_name, "V001", ""))
    for field_name, field_value in row_fields.items():
        conn.execute(
            "INSERT INTO rs_field VALUES (?,?,?,?)",
            (table_name, "V001", field_name, field_value),
        )
    conn.commit()
    conn.close()


def _make_module_dirs(module_dir):
    (module_dir / "case").mkdir()
    (module_dir / "model").mkdir()
    (module_dir / "data").mkdir()


# ---------------------------------------------------------------------------
# check_directory_structure
# ---------------------------------------------------------------------------


def test_directory_structure_missing(tmp_path):
    missing = check_directory_structure(tmp_path)
    assert missing == ["case", "model", "data"]


def test_directory_structure_complete(tmp_path):
    (tmp_path / "case").mkdir()
    (tmp_path / "model").mkdir()
    (tmp_path / "data").mkdir()
    missing = check_directory_structure(tmp_path)
    assert missing == []


def test_directory_structure_partial(tmp_path):
    (tmp_path / "case").mkdir()
    missing = check_directory_structure(tmp_path)
    assert missing == ["model", "data"]


# ---------------------------------------------------------------------------
# scan_return_ref_violations
# ---------------------------------------------------------------------------


def test_return_ref_violation_detected_for_interface_model():
    tables = {"LoginAPI_verify": {"V001": {"token": "${Return[-1].token}"}}}
    model_types = {"LoginAPI": "interface"}
    violations = scan_return_ref_violations(tables, model_types)
    assert violations == ["LoginAPI_verify.V001.token"]


def test_return_ref_violation_detected_for_database_model():
    tables = {"UserDB_verify": {"V001": {"name": "${Return[-1].name}"}}}
    model_types = {"UserDB": "database"}
    violations = scan_return_ref_violations(tables, model_types)
    assert violations == ["UserDB_verify.V001.name"]


def test_return_ref_allowed_for_ui_model():
    tables = {"Login_verify": {"V001": {"welcomeMsg": "${Return[-2].token}"}}}
    model_types = {"Login": "ui"}
    violations = scan_return_ref_violations(tables, model_types)
    assert violations == []


def test_return_ref_ignores_non_verify_tables():
    tables = {"LoginAPI": {"D001": {"token": "${Return[-1].token}"}}}
    model_types = {"LoginAPI": "interface"}
    violations = scan_return_ref_violations(tables, model_types)
    assert violations == []


def test_return_ref_no_violation_when_no_return_ref():
    tables = {"LoginAPI_verify": {"V001": {"token": "demo_token_123"}}}
    model_types = {"LoginAPI": "interface"}
    violations = scan_return_ref_violations(tables, model_types)
    assert violations == []


# ---------------------------------------------------------------------------
# run_compliance_checks — 整体聚合
# ---------------------------------------------------------------------------


def test_run_compliance_checks_all_pass(tmp_path):
    (tmp_path / "case").mkdir()
    (tmp_path / "model").mkdir()
    (tmp_path / "data").mkdir()
    report = run_compliance_checks(
        module_dir=str(tmp_path),
        plan_path=None,
        selector_filters={"filter_tags": ["smoke"]},
        tables={"Login_verify": {"V001": {"msg": "ok"}}},
        schemas={"Login_verify": ["msg"]},
        model_types={"Login": "ui"},
    )
    assert report.passed is True
    assert report.failed_checks == []


def test_run_compliance_checks_directory_missing(tmp_path):
    report = run_compliance_checks(module_dir=str(tmp_path))
    assert report.passed is False
    names = [c["check_name"] for c in report.failed_checks]
    assert "directory_structure" in names


def test_run_compliance_checks_plan_selector_conflict(tmp_path):
    (tmp_path / "case").mkdir()
    (tmp_path / "model").mkdir()
    (tmp_path / "data").mkdir()
    report = run_compliance_checks(
        module_dir=str(tmp_path),
        plan_path="@my_plan",
        selector_filters={"filter_tags": ["smoke"]},
    )
    assert report.passed is False
    names = [c["check_name"] for c in report.failed_checks]
    assert "plan_selector_conflict" in names


def test_run_compliance_checks_data_schema_inconsistent(tmp_path):
    (tmp_path / "case").mkdir()
    (tmp_path / "model").mkdir()
    (tmp_path / "data").mkdir()
    report = run_compliance_checks(
        module_dir=str(tmp_path),
        tables={"Login": {"L001": {"username": "admin"}}},
        schemas={"Login": ["username", "password"]},
    )
    assert report.passed is False
    names = [c["check_name"] for c in report.failed_checks]
    assert "data_schema_consistency" in names


def test_run_compliance_checks_return_ref_self_check(tmp_path):
    (tmp_path / "case").mkdir()
    (tmp_path / "model").mkdir()
    (tmp_path / "data").mkdir()
    report = run_compliance_checks(
        module_dir=str(tmp_path),
        tables={"LoginAPI_verify": {"V001": {"token": "${Return[-1].token}"}}},
        model_types={"LoginAPI": "interface"},
    )
    assert report.passed is False
    names = [c["check_name"] for c in report.failed_checks]
    assert "return_ref_self_check" in names


def test_run_compliance_checks_multiple_failures_aggregated(tmp_path):
    report = run_compliance_checks(
        module_dir=str(tmp_path),  # 目录全缺
        plan_path="@my_plan",
        selector_filters={"filter_tags": ["smoke"]},  # 冲突
        tables={"LoginAPI_verify": {"V001": {"token": "${Return[-1].token}"}}},
        model_types={"LoginAPI": "interface"},  # 自引用
    )
    assert report.passed is False
    assert len(report.failed_checks) == 3


def test_compliance_report_to_dict():
    report = ComplianceReport()
    report.add_failure("check_a", "reason_a")
    d = report.to_dict()
    assert d["passed"] is False
    assert d["failed_checks"] == [{"check_name": "check_a", "reason": "reason_a"}]


def test_run_compliance_checks_loads_sqlite_schema_from_module(tmp_path):
    _make_module_dirs(tmp_path)
    _make_sqlite(
        tmp_path,
        table_name="Login",
        schema_fields=["username", "password"],
        row_fields={"username": "admin"},
    )

    report = run_compliance_checks(module_dir=str(tmp_path))

    failures = {item["check_name"]: item["reason"] for item in report.failed_checks}
    assert "data_schema_consistency" in failures
    assert "missing=['password']" in failures["data_schema_consistency"]


def test_run_compliance_checks_loads_model_types_for_return_scan(tmp_path):
    _make_module_dirs(tmp_path)
    (tmp_path / "model" / "model.xml").write_text(
        '<?xml version="1.0"?><models><model name="LoginAPI" type="interface"/></models>',
        encoding="utf-8",
    )
    _make_sqlite(
        tmp_path,
        table_name="LoginAPI_verify",
        schema_fields=["token"],
        row_fields={"token": "${Return[-1].token}"},
    )

    report = run_compliance_checks(module_dir=str(tmp_path))

    failures = {item["check_name"]: item["reason"] for item in report.failed_checks}
    assert "return_ref_self_check" in failures
    assert "LoginAPI_verify.V001.token" in failures["return_ref_self_check"]
