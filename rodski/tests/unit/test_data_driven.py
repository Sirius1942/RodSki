"""v11.9.0 计划级数据驱动（REQ-013 / CORE §7.8）单元测试。

验收测试在 rodski-demo/demosite/data_driven、mock_api/business_model、mobile/app 中落地；
这里只覆盖纯逻辑：字面 DataID 扫描、驱动表读取与校验、实例展开与替换、过滤、旧库迁移、计划解析。
"""
import sqlite3
from pathlib import Path

import pytest

from core import data_driven as dd
from core.plan_parser import PlanParser
from core.sqlite_schema import SQLITE_DDL


def _step(action, model, data):
    return {"action": action, "model": model, "data": data}


def _case():
    return {
        "case_id": "C1",
        "case_file": "flow.xml",
        "case_uid": "flow.xml::C1",
        "title": "流程",
        "pre_process": [_step("navigate", "", "GlobalValue.Demo.URL"), _step("type", "Login", "L001")],
        "test_case": [
            {"type": "scenario", "id": "S1", "steps": [
                _step("type", "Form", "T001"),
                {"type": "if", "condition": "x", "steps": [_step("verify", "Form", "V001")], "else_steps": [],
                 "elif_chain": [{"condition": "y", "steps": [_step("send", "Api", "D001")]}]},
            ]},
            {"type": "loop", "var": "i", "range": "1-2", "steps": [_step("type", "Form", "T00${i}")]},
            {"type": "business_call", "ref": "biz", "flow": "F1", "input": "IN1", "expect": "EX1"},
            _step("run", "proj", "do_it()"),
            _step("set", "", "k=v"),
        ],
        "post_process": [_step("close", "", "")],
    }


def _db(tmp_path: Path, drivers=(), old_schema=False) -> Path:
    db = tmp_path / "data" / "data.sqlite"
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    ddl = SQLITE_DDL.replace("'data', 'verify', 'driver'", "'data', 'verify'") if old_schema else SQLITE_DDL
    conn.executescript(ddl)
    tables = {
        ("Login", "data"): {"L001": "管理员", "L002": ""},
        ("Form", "data"): {"T001": "基础", "T101": "alice"},
        ("Form_verify", "verify"): {"V001": "基础", "V101": "alice"},
        ("Api", "data"): {"D001": "x"},
        ("biz", "data"): {"IN1": "x", "IN2": "y"},
        ("biz_verify", "verify"): {"EX1": "x", "EX2": "y"},
    }
    for (name, kind), rows in tables.items():
        conn.execute("INSERT INTO rs_datatable VALUES (?,?,?,'standard','',CURRENT_TIMESTAMP)",
                     (name, name.replace("_verify", ""), kind))
        conn.execute("INSERT INTO rs_datatable_field VALUES (?,?,0)", (name, "f"))
        for data_id, remark in rows.items():
            conn.execute("INSERT INTO rs_row VALUES (?,?,?)", (name, data_id, remark))
            conn.execute("INSERT INTO rs_field VALUES (?,?,?,?)", (name, data_id, "f", "v"))
    for name, uid, remark, columns, rows in drivers:
        conn.execute("INSERT INTO rs_datatable VALUES (?,?,'driver','standard',?,CURRENT_TIMESTAMP)", (name, uid, remark))
        for i, c in enumerate(columns):
            conn.execute("INSERT INTO rs_datatable_field VALUES (?,?,?)", (name, c, i))
        for data_id, row_remark, cells in rows:
            conn.execute("INSERT INTO rs_row VALUES (?,?,?)", (name, data_id, row_remark))
            for c, v in zip(columns, cells):
                conn.execute("INSERT INTO rs_field VALUES (?,?,?,?)", (name, data_id, c, v))
    conn.commit()
    conn.close()
    return db


MATRIX = ("M", "flow.xml::C1", "目的；计划 p", ["Form.T001", "Form_verify.V001", "Login.L001", "biz.IN1"],
          [("a", "实例 a", ["T101", "V101", "BLANK", "IN2"]), ("b", "", ["BLANK", "BLANK", "L002", "BLANK"])])


class TestLiteralRefs:
    def test_step_table(self):
        assert dd.step_table(_step("verify", "Form", "V1")) == "Form_verify"
        assert dd.step_table(_step("check", "Form_verify", "V1")) == "Form_verify"
        assert dd.step_table(_step("DB", "Q", "Q1")) == "Q"
        assert dd.step_table(_step("run", "proj", "f()")) is None
        assert dd.step_table(_step("type", "", "#x")) is None

    def test_literal_data_id(self):
        assert dd.is_literal_data_id("L001")
        assert dd.is_literal_data_id("LOGIN_OK_01")
        for bad in ("", "T00${i}", "GlobalValue.A.B", "a.b", "http://x", "#id", "f(1)"):
            assert not dd.is_literal_data_id(bad), bad

    def test_iter_refs_covers_nested_and_business_call(self):
        refs = {(r.table, r.data_id) for r in dd.iter_literal_refs(_case())}
        assert refs == {("Login", "L001"), ("Form", "T001"), ("Form_verify", "V001"), ("Api", "D001"),
                        ("biz", "IN1"), ("biz_verify", "EX1")}


class TestValidation:
    def _check(self, tmp_path, driver, case=None, uid="flow.xml::C1"):
        db = _db(tmp_path, [driver])
        catalog = dd.load_catalog(db)
        return dd.check_driver_reference(driver[0], _case() if case is None else case, uid, catalog,
                                         {"Login", "Form", "Api", "biz"}, "计划 p")[1]

    def test_valid(self, tmp_path):
        assert self._check(tmp_path, MATRIX) == []

    @pytest.mark.parametrize("mutate,keyword", [
        (lambda m: (m[0], "flow.xml::OTHER", *m[2:]), "绑定"),
        (lambda m: (m[0], m[1], " ", *m[3:]), "表备注为空"),
        (lambda m: (*m[:4], []), "没有任何行"),
        (lambda m: (m[0], m[1], m[2], ["Form"], [("a", "", ["T101"])]), "列名"),
        (lambda m: (m[0], m[1], m[2], ["Form.T00${i}"], [("a", "", ["T101"])]), "列名"),
        (lambda m: (m[0], m[1], m[2], ["Nope.T001"], [("a", "", ["T101"])]), "不存在"),
        (lambda m: (m[0], m[1], m[2], ["Form.T101"], [("a", "", ["T001"])]), "未被用例"),
        (lambda m: (m[0], m[1], m[2], ["Form.T001"], [("a", "", ["T999"])]), "不存在"),
        (lambda m: (m[0], m[1], m[2], ["Form.T001"], [("a", "", ["${x}"])]), "只能是 DataID"),
        (lambda m: ("Form_verify2", *m[1:]), None),
    ])
    def test_invalid(self, tmp_path, mutate, keyword):
        errors = self._check(tmp_path, mutate(MATRIX))
        if keyword is None:
            assert errors == []
        else:
            assert any(keyword in e for e in errors), errors

    def test_same_name_as_model(self, tmp_path):
        errors = self._check(tmp_path, ("Login_verify", *MATRIX[1:]))
        assert any("同名" in e for e in errors)

    def test_reference_errors(self, tmp_path):
        db = _db(tmp_path, [MATRIX])
        catalog = dd.load_catalog(db)
        assert "数据驱动表不存在" in dd.check_driver_reference("X", _case(), "u", catalog, set(), "p")[1][0]
        assert "不是数据驱动表" in dd.check_driver_reference("Form", _case(), "u", catalog, set(), "p")[1][0]
        assert "不存在或未启用" in dd.check_driver_reference("M", None, "u", catalog, set(), "p")[1][0]

    def test_plan_kind(self):
        plan = {"id": "p", "kind": "scenario_debug", "cases": [{"id": "C1", "data_driven": "M"}]}
        assert "suite" in dd.check_plan_kind(plan)[0]
        assert dd.check_plan_kind({"kind": "suite", "cases": [{"id": "C1", "data_driven": "M"}]}) == []


class TestExpand:
    def test_build_instances_replaces_only_listed_literal_refs(self, tmp_path):
        db = _db(tmp_path, [MATRIX])
        catalog = dd.load_catalog(db)
        case = _case()
        a, b = dd.build_instances(case, catalog.driver("M"), catalog)
        assert [a["case_id"], b["case_id"]] == ["C1[a]", "C1[b]"]
        scenario = a["test_case"][0]
        assert scenario["steps"][0]["data"] == "T101"
        assert scenario["steps"][1]["steps"][0]["data"] == "V101"
        assert a["pre_process"][1]["data"] == "L001"          # BLANK：沿用基础 DataID
        assert a["test_case"][1]["steps"][0]["data"] == "T00${i}"  # 动态 DataID 不替换
        bc = a["test_case"][2]
        assert (bc["input"], bc["expect"], bc["flow"]) == ("IN2", "EX1", "F1")
        assert a["_data_driven"]["replacements"] == "Form.T001=T101; Form_verify.V001=V101; biz.IN1=IN2"
        assert a["_data_driven"]["instance_title"] == "实例 a"
        assert scenario["steps"][0]["_dd_replaced"] == [("Form", "T001", "T101", "M[a]")]
        assert b["pre_process"][1]["data"] == "L002"
        assert b["_data_driven"]["missing_remarks"] == ["Login.L002"]
        # 模板用例不被修改
        assert case["test_case"][0]["steps"][0]["data"] == "T001"
        assert "_dd_replaced" not in case["test_case"][0]["steps"][0]

    def test_expand_plan_cases_and_filters(self, tmp_path):
        _db(tmp_path, [MATRIX])
        (tmp_path / "model").mkdir()
        (tmp_path / "model" / "model.xml").write_text('<models><model name="Form"/></models>', encoding="utf-8")
        other = dict(_case(), case_id="C2", case_uid="flow.xml::C2")
        plan = {"id": "p", "kind": "suite", "cases": [{"id": "C1", "file": "flow.xml", "data_driven": "M"},
                                                      {"id": "C2", "file": "flow.xml"}]}
        ids = [c["case_id"] for c in dd.expand_plan_cases(plan, [_case(), other], {}, tmp_path)]
        assert ids == ["C1[a]", "C1[b]", "C2"]
        ids = [c["case_id"] for c in dd.expand_plan_cases(plan, [_case(), other], {}, tmp_path, include=["C1[b]"])]
        assert ids == ["C1[b]", "C2"]
        ids = [c["case_id"] for c in dd.expand_plan_cases(plan, [_case(), other], {}, tmp_path, exclude=["a"])]
        assert ids == ["C1[b]", "C2"]
        # 模板被计划 SKIP 时不展开
        ids = [c["case_id"] for c in dd.expand_plan_cases(plan, [_case()], {"flow.xml::C1": "plan_skipped"}, tmp_path)]
        assert ids == ["C1"]

    def test_expand_raises_before_side_effects(self, tmp_path):
        _db(tmp_path, [])
        plan = {"id": "p", "kind": "suite", "cases": [{"id": "C1", "file": "flow.xml", "data_driven": "Missing"}]}
        with pytest.raises(dd.DataDrivenError) as exc:
            dd.expand_plan_cases(plan, [_case()], {}, tmp_path)
        assert "数据驱动表不存在" in str(exc.value)

    def test_parse_id_list(self):
        assert dd.parse_id_list("a, LOGIN[x,y] ,b") == ["a", "LOGIN[x,y]", "b"]
        assert dd.parse_id_list(None) == []


class TestStorage:
    def test_data_source_excludes_driver_tables(self, tmp_path):
        from core.data_table_parser import DataTableParser
        from core.exceptions import DataParseError
        _db(tmp_path, [MATRIX])
        parser = DataTableParser(str(tmp_path / "data"))
        tables = parser.parse_all_tables()
        assert "M" not in tables and "Form" in tables
        with pytest.raises(DataParseError, match="数据驱动表"):
            parser.get_data("M", "a")

    def test_migrate_old_schema(self, tmp_path):
        db = _db(tmp_path, old_schema=True)
        assert dd.migrate_driver_kind(db) is True
        assert (db.parent / "data.sqlite.bak").is_file()
        conn = sqlite3.connect(db)
        conn.execute("INSERT INTO rs_datatable VALUES ('M','u','driver','standard','r',CURRENT_TIMESTAMP)")
        conn.commit()
        fk = conn.execute("SELECT sql FROM sqlite_master WHERE name='rs_row'").fetchone()[0]
        assert "REFERENCES rs_datatable(" in fk
        assert conn.execute("SELECT COUNT(*) FROM rs_datatable").fetchone()[0] == 7
        conn.close()
        assert dd.migrate_driver_kind(db) is False


class TestPlanParser:
    def test_data_driven_attribute(self, tmp_path):
        path = tmp_path / "p_suite.xml"
        path.write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
                        '<test_plan id="p_suite" kind="suite">'
                        '<case file="a.xml" id="C1" data_driven="M"/><case file="a.xml" id="C2"/></test_plan>',
                        encoding="utf-8")
        cases = PlanParser(str(path)).parse_plan()["cases"]
        assert cases[0]["data_driven"] == "M"
        assert "data_driven" not in cases[1]


class TestReviewFixes:
    """独立评审后的修复：重复挂载、实例过滤校验、navigate 不参与替换、实例 DataID 校验、queue 转发。"""

    def test_navigate_launch_not_replaceable(self):
        assert dd.step_table(_step("navigate", "Home", "H001")) is None
        assert dd.step_table(_step("launch", "App", "A001")) is None

    def test_duplicate_entries(self):
        plan = {"id": "p", "kind": "suite", "cases": [
            {"id": "C1", "file": "flow.xml", "data_driven": "M"},
            {"id": "C1", "file": "flow.xml", "data_driven": "M2"}]}
        errors = dd.check_duplicate_entries(plan, [_case()])
        assert errors and "只能挂一张" in errors[0]

    def test_instance_filters(self, tmp_path):
        _db(tmp_path, [MATRIX])
        plan = {"id": "p", "kind": "suite", "cases": [{"id": "C1", "file": "flow.xml", "data_driven": "M"}]}
        assert dd.check_instance_filters(plan, [_case()], tmp_path, ["a", "C1[b]"], []) == ([], [])
        errors, _ = dd.check_instance_filters(plan, [_case()], tmp_path, ["typo"], [])
        assert "typo" in errors[0]
        _, warnings = dd.check_instance_filters(plan, [_case()], tmp_path, [], ["typo"])
        assert "typo" in warnings[0]
        errors, _ = dd.check_instance_filters({"id": "p", "kind": "suite", "cases": [{"id": "C1"}]},
                                               [_case()], tmp_path, ["a"], [])
        assert "没有数据驱动用例" in errors[0]

    def test_invalid_instance_data_id(self, tmp_path):
        bad = (*MATRIX[:4], [("a,b", "", ["T101", "V101", "BLANK", "IN2"])])
        db = _db(tmp_path, [bad])
        catalog = dd.load_catalog(db)
        errors = dd.check_driver_reference("M", _case(), "flow.xml::C1", catalog, set(), "p")[1]
        assert any("实例 DataID" in e for e in errors)

    def test_expand_skips_filtered_out_case(self, tmp_path):
        _db(tmp_path, [MATRIX])
        plan = {"id": "p", "kind": "suite", "cases": [{"id": "C1", "file": "flow.xml", "data_driven": "M"}]}
        other = dict(_case(), case_id="C2", case_uid="flow.xml::C2")
        assert [c["case_id"] for c in dd.expand_plan_cases(plan, [other], {}, tmp_path)] == ["C2"]

    def test_queue_forwards_data_id(self):
        import argparse
        from rodski_cli.queue import _forward_run_args
        ns = argparse.Namespace(report=None, trace=False, verbose=False, coverage=False,
                                data_id="a,C1[b]", exclude_data_id="c")
        assert _forward_run_args(ns) == ["--data-id", "a,C1[b]", "--exclude-data-id", "c"]
