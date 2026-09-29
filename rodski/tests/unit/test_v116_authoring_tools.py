"""v11.6.0 WI-64-06：case lint C5 规则、data set/add-row/delete-row、capabilities.pitfalls 与 skill 契约速查。"""
import argparse
import json
import sqlite3
from pathlib import Path

import pytest

try:
    from rodski.rodski_cli import case as case_cli
    from rodski.rodski_cli import data as data_cli
    from rodski.rodski_cli.capabilities import get_capabilities
    from rodski.rodski_cli.pitfalls import PITFALLS
    from rodski.core.sqlite_schema import SQLITE_DDL
except ImportError:  # pragma: no cover
    from rodski_cli import case as case_cli
    from rodski_cli import data as data_cli
    from rodski_cli.capabilities import get_capabilities
    from rodski_cli.pitfalls import PITFALLS
    from core.sqlite_schema import SQLITE_DDL

REPO = Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------- 夹具
def _make_sqlite(path: Path, tables):
    """tables: {table: (kind, [fields], {data_id: {field: value}})}"""
    conn = sqlite3.connect(str(path))
    conn.executescript(SQLITE_DDL)
    for table, (kind, fields, rows) in tables.items():
        conn.execute(
            "INSERT INTO rs_datatable (table_name, model_name, table_kind, row_mode) VALUES (?, ?, ?, 'standard')",
            (table, table, kind),
        )
        for i, f in enumerate(fields):
            conn.execute("INSERT INTO rs_datatable_field VALUES (?, ?, ?)", (table, f, i))
        for data_id, row in rows.items():
            conn.execute("INSERT INTO rs_row (table_name, data_id) VALUES (?, ?)", (table, data_id))
            for f, v in row.items():
                conn.execute("INSERT INTO rs_field VALUES (?, ?, ?, ?)", (table, data_id, f, v))
    conn.commit()
    conn.close()


MODEL_XML = """<?xml version="1.0" encoding="UTF-8"?>
<models>
  <model name="OrderDB" type="database" connection="db">
    <query name="count_all"><sql>SELECT 1 AS n</sql></query>
    <element name="n" type="database"><location type="field">n</location></element>
  </model>
  <model name="Page" type="ui">
    <element name="a" type="web"><location type="id">a</location></element>
    <element name="b" type="web"><location type="id">b</location></element>
    <element name="c" type="web"><location type="id">c</location></element>
  </model>
  <model name="Api" type="interface">
    <element name="x" type="interface"><location type="field">x</location></element>
  </model>
</models>
"""


def _module(tmp_path: Path, case_xml: str, wait_time="0", tables=None) -> Path:
    mod = tmp_path / "mod"
    (mod / "case").mkdir(parents=True)
    (mod / "model").mkdir()
    (mod / "data").mkdir()
    (mod / "fun" / "js").mkdir(parents=True)
    (mod / "case" / "flow.xml").write_text(case_xml, encoding="utf-8")
    (mod / "model" / "model.xml").write_text(MODEL_XML, encoding="utf-8")
    gv = '<?xml version="1.0" encoding="UTF-8"?>\n<globalvalue><group name="DefaultValue">'
    if wait_time is not None:
        gv += f'<var name="WaitTime" value="{wait_time}"/>'
    gv += "</group></globalvalue>"
    (mod / "data" / "globalvalue.xml").write_text(gv, encoding="utf-8")
    _make_sqlite(mod / "data" / "data.sqlite", tables or {
        "OrderDB": ("data", ["operation", "query", "sql"], {
            "Q_OK": {"operation": "BLANK", "query": "count_all", "sql": "BLANK"},
            "Q_SQL": {"operation": "BLANK", "query": "BLANK", "sql": "SELECT 1 AS n"},
        }),
        "OrderDB_verify": ("verify", ["n"], {"V1": {"n": "1"}}),
        "Page_verify": ("verify", ["a", "b", "c"], {
            "V_MOSTLY_BLANK": {"a": "x", "b": "BLANK", "c": "BLANK"},
            "V_FULL": {"a": "x", "b": "y", "c": "BLANK"},
        }),
        "Api_verify": ("verify", ["x"], {"V1": {"x": "1"}}),
    })
    return mod


def _cases(*steps: str, execute="是") -> str:
    body = "\n".join(steps)
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<cases>\n<case execute="{execute}" id="TC001" title="t">'
            f"<test_case>\n{body}\n</test_case></case>\n</cases>")


def _lint(mod: Path, capsys):
    rc = case_cli._lint(str(mod))
    out = capsys.readouterr()
    return rc, out.out + out.err


# ---------------------------------------------------------------- lint
class TestCaseLintAuthoringRules:
    def test_clean_module_has_no_issue(self, tmp_path, capsys):
        mod = _module(tmp_path, _cases('<test_step action="DB" model="OrderDB" data="Q_OK"/>',
                                       '<test_step action="verify" model="OrderDB" data="V1"/>'))
        rc, out = _lint(mod, capsys)
        assert rc == 0
        assert "[OK] 未发现问题" in out

    def test_evaluate_assertion_patterns_warn(self, tmp_path, capsys):
        mod = _module(tmp_path, _cases(
            '<test_step action="evaluate" model="" data="document.querySelectorAll(\'tr\').length === 3"/>',
            '<test_step action="evaluate" model="" data="location.pathname === \'/x\'"/>',
            '<test_step action="evaluate" model="" data="!!document.querySelector(\'#a\')"/>',
            '<test_step action="evaluate" model="" data="document.title"/>',
        ))
        rc, out = _lint(mod, capsys)
        assert rc == 0
        assert "[WARNING] evaluate 断言模式 querySelectorAll(...).length" in out
        assert "location.pathname" in out and "page" in out
        assert "querySelector(...)" in out
        assert "document.title" in out
        assert '"$count"' in out

    def test_bare_query_selector_all_without_length_not_flagged(self, tmp_path, capsys):
        mod = _module(tmp_path, _cases(
            '<test_step action="evaluate" model="" data="document.querySelectorAll(\'tr\').forEach(r =&gt; r.remove())"/>'))
        rc, out = _lint(mod, capsys)
        assert "evaluate 断言模式" not in out

    def test_evaluate_file_script_is_scanned_and_escape_rejected(self, tmp_path, capsys):
        mod = _module(tmp_path, _cases('<test_step action="evaluate" model="" data="file:fun/js/a.js"/>',
                                       '<test_step action="evaluate" model="" data="file:../outside.js"/>'))
        (mod / "fun" / "js" / "a.js").write_text("if (a && b) { window.alert = () => 1 }", encoding="utf-8")
        (tmp_path / "outside.js").write_text("location.pathname", encoding="utf-8")
        rc, out = _lint(mod, capsys)
        assert "window.alert" in out and "DialogPolicy" in out
        assert "location.pathname" not in out  # 模块外脚本不读取

    def test_dialog_shim_warns_but_comparison_does_not(self, tmp_path, capsys):
        mod = _module(tmp_path, _cases(
            '<test_step action="evaluate" model="" data="window.confirm = () =&gt; true"/>',
            '<test_step action="evaluate" model="" data="window.prompt == null"/>',
        ))
        rc, out = _lint(mod, capsys)
        assert "window.confirm" in out
        assert "window.prompt" not in out

    def test_numeric_wait_warns_with_estimate(self, tmp_path, capsys):
        mod = _module(tmp_path, _cases('<test_step action="wait" model="" data="2"/>',
                                       '<test_step action="wait" model="" data="1.5"/>',
                                       '<test_step action="wait" model="" data="${Return[-1]}"/>'))
        rc, out = _lint(mod, capsys)
        assert rc == 0
        assert "固定等待 wait 2" in out and "固定等待 wait 1.5" in out
        assert "共 2 处数字字面量 wait，合计固定等待约 3.5s" in out

    @pytest.mark.parametrize("value,per_step,legacy", [("1", 1.0, True), ("500", 0.5, False)])
    def test_waittime_positive_warns(self, tmp_path, capsys, value, per_step, legacy):
        mod = _module(tmp_path, _cases('<test_step action="DB" model="OrderDB" data="Q_OK"/>',
                                       '<test_step action="verify" model="OrderDB" data="V1"/>'), wait_time=value)
        rc, out = _lint(mod, capsys)
        assert rc == 0
        assert f"DefaultValue.WaitTime={value} > 0" in out
        assert f"估算额外耗时 {per_step * 2:g}s" in out
        assert ("按旧写法以秒兼容" in out) is legacy

    @pytest.mark.parametrize("value", ["0", None])
    def test_waittime_zero_or_missing_silent(self, tmp_path, capsys, value):
        mod = _module(tmp_path, _cases('<test_step action="DB" model="OrderDB" data="Q_OK"/>'), wait_time=value)
        rc, out = _lint(mod, capsys)
        assert "WaitTime" not in out

    def test_strict_verify_blank_ratio_info(self, tmp_path, capsys):
        mod = _module(tmp_path, _cases(
            '<test_step action="verify" model="Page" data="V_MOSTLY_BLANK"/>',
            '<test_step action="verify" model="Page" data="V_FULL"/>',
            '<test_step action="verify" model="Page" data="V_MOSTLY_BLANK" match_mode="subset"/>',
        ))
        rc, out = _lint(mod, capsys)
        assert rc == 0
        assert out.count("strict verify") == 1
        assert "Page_verify.V_MOSTLY_BLANK 中 2/3 个字段为 BLANK" in out
        assert 'match_mode="subset"' in out

    def test_subset_step_not_flagged(self, tmp_path, capsys):
        mod = _module(tmp_path, _cases(
            '<test_step action="verify" model="Page" data="V_MOSTLY_BLANK" match_mode="subset"/>'))
        rc, out = _lint(mod, capsys)
        assert "strict verify" not in out

    def test_sql_blank_without_query_is_error(self, tmp_path, capsys):
        mod = _module(tmp_path, _cases('<test_step action="DB" model="OrderDB" data="Q_OK"/>'), tables={
            "OrderDB": ("data", ["operation", "query", "sql"], {
                "Q_OK": {"operation": "BLANK", "query": "count_all", "sql": "BLANK"},
                "Q_BAD": {"operation": "BLANK", "query": "NULL", "sql": "BLANK"},
            }),
        })
        rc, out = _lint(mod, capsys)
        assert rc == 1
        assert "[ERROR] 数据行 OrderDB.Q_BAD 既没有有效的 sql 也没有 query" in out
        assert "Q_OK" not in out

    def test_sql_field_on_non_db_model_ignored(self, tmp_path, capsys):
        mod = _module(tmp_path, _cases('<test_step action="DB" model="OrderDB" data="Q_OK"/>'), tables={
            "Page": ("data", ["a", "sql"], {"R1": {"a": "x", "sql": "BLANK"}}),
        })
        rc, out = _lint(mod, capsys)
        assert rc == 0

    def test_xml_parse_error_reports_escape_hint(self, tmp_path, capsys):
        mod = _module(tmp_path, _cases('<test_step action="evaluate" model="" data="a && b"/>'))
        rc, out = _lint(mod, capsys)
        assert rc == 1
        assert "用例 XML 解析失败" in out and "&amp;&amp;" in out and "file:" in out

    def test_non_executed_cases_still_linted(self, tmp_path, capsys):
        mod = _module(tmp_path, _cases('<test_step action="wait" model="" data="1"/>', execute="否"))
        rc, out = _lint(mod, capsys)
        assert "固定等待 wait 1" in out


class TestLintAgainstDemoFixtures:
    """V14 对应的 demo 夹具（不改动夹具，只读扫描）。"""

    PIT = REPO / "rodski-demo" / "DEMO" / "demo_authoring_v116_pitfalls"
    GOOD = REPO / "rodski-demo" / "DEMO" / "demo_authoring_v116"

    @pytest.mark.skipif(not PIT.is_dir(), reason="demo 夹具不存在")
    def test_pitfalls_fixture_hits_all_rules(self, capsys):
        rc, out = _lint(self.PIT, capsys)
        assert rc == 1
        for token in ["querySelectorAll", "location.pathname", "wait", "WaitTime", "window.confirm", "Q_BAD"]:
            assert token in out

    @pytest.mark.skipif(not GOOD.is_dir(), reason="demo 模块不存在")
    def test_good_module_has_no_error(self, capsys):
        rc, out = _lint(self.GOOD, capsys)
        assert rc == 0
        assert "ERROR" not in out


# ---------------------------------------------------------------- data set / add-row / delete-row
def _rows(mod: Path, table: str):
    conn = sqlite3.connect(str(mod / "data" / "data.sqlite"))
    try:
        cur = conn.execute("SELECT data_id, field_name, field_value FROM rs_field WHERE table_name = ?", (table,))
        out = {}
        for data_id, f, v in cur.fetchall():
            out.setdefault(data_id, {})[f] = v
        return out
    finally:
        conn.close()


def _data(capsys, *argv):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    data_cli.setup_parser(sub)
    args = parser.parse_args(["data", *argv])
    rc = data_cli.handle(args)
    out = capsys.readouterr()
    return rc, out.out + out.err


class TestDataRowEdit:
    @pytest.fixture
    def mod(self, tmp_path):
        return _module(tmp_path, _cases('<test_step action="DB" model="OrderDB" data="Q_OK"/>'))

    def test_set_updates_fields(self, mod, capsys):
        rc, out = _data(capsys, "set", str(mod), "OrderDB_verify", "V1", "n=2")
        assert rc == 0, out
        assert _rows(mod, "OrderDB_verify")["V1"]["n"] == "2"

    def test_set_value_may_contain_equals_and_json(self, mod, capsys):
        rc, out = _data(capsys, "set", str(mod), "Page_verify", "V_FULL", 'a={"$count": 10}', "b=x=y")
        assert rc == 0, out
        row = _rows(mod, "Page_verify")["V_FULL"]
        assert row["a"] == '{"$count": 10}' and row["b"] == "x=y"

    def test_set_is_visible_to_data_parser(self, mod, capsys):
        _data(capsys, "set", str(mod), "OrderDB_verify", "V1", "n=7")
        rc, out = _data(capsys, "show", str(mod), "OrderDB_verify", "V1")
        assert rc == 0 and "n: 7" in out

    @pytest.mark.parametrize("argv,msg", [
        (["NoTable", "V1", "n=1"], "逻辑表 'NoTable' 不存在"),
        (["OrderDB_verify", "V9", "n=1"], "找不到 DataID='V9'"),
        (["OrderDB_verify", "V1", "zz=1"], "没有字段 zz"),
        (["OrderDB_verify", "V1", "n="], "BLANK/NULL/NONE"),
        (["OrderDB_verify", "V1", "n"], "field=value"),
        (["OrderDB_verify", "V1", "n=1", "n=2"], "重复赋值"),
    ])
    def test_set_validation_errors_do_not_write(self, mod, capsys, argv, msg):
        before = _rows(mod, "OrderDB_verify")
        rc, out = _data(capsys, "set", str(mod), *argv)
        assert rc == 1
        assert msg in out
        assert _rows(mod, "OrderDB_verify") == before

    def test_set_multiple_fields_validated_atomically(self, mod, capsys):
        rc, out = _data(capsys, "set", str(mod), "Page_verify", "V_FULL", "a=new", "nope=1")
        assert rc == 1
        assert _rows(mod, "Page_verify")["V_FULL"]["a"] == "x"

    def test_set_rejects_return_self_ref_in_non_ui_verify(self, mod, capsys):
        rc, out = _data(capsys, "set", str(mod), "OrderDB_verify", "V1", "n=${Return[-1]}")
        assert rc == 1 and "Return[-1]" in out
        rc, out = _data(capsys, "set", str(mod), "Api_verify", "V1", "x=${Return[-1].x}")
        assert rc == 1

    def test_set_allows_return_ref_in_ui_verify(self, mod, capsys):
        rc, out = _data(capsys, "set", str(mod), "Page_verify", "V_FULL", "a=${Return[-1]}")
        assert rc == 0, out

    def test_add_row_requires_full_field_set(self, mod, capsys):
        rc, out = _data(capsys, "add-row", str(mod), "OrderDB", "Q_NEW", "query=count_all")
        assert rc == 1
        assert "缺少字段" in out and "operation" in out and "sql" in out and "BLANK" in out
        assert "Q_NEW" not in _rows(mod, "OrderDB")

    def test_add_row_success(self, mod, capsys):
        rc, out = _data(capsys, "add-row", str(mod), "OrderDB", "Q_NEW",
                        "operation=BLANK", "query=count_all", "sql=BLANK", "--remark", "新增")
        assert rc == 0, out
        assert _rows(mod, "OrderDB")["Q_NEW"] == {"operation": "BLANK", "query": "count_all", "sql": "BLANK"}

    def test_add_row_rejects_duplicate_and_unknown(self, mod, capsys):
        rc, out = _data(capsys, "add-row", str(mod), "OrderDB_verify", "V1", "n=1")
        assert rc == 1 and "已存在" in out
        rc, out = _data(capsys, "add-row", str(mod), "OrderDB_verify", "V2", "n=1", "zz=1")
        assert rc == 1 and "没有字段 zz" in out

    def test_delete_row(self, mod, capsys):
        rc, out = _data(capsys, "delete-row", str(mod), "OrderDB", "Q_SQL")
        assert rc == 0, out
        assert "Q_SQL" not in _rows(mod, "OrderDB")
        conn = sqlite3.connect(str(mod / "data" / "data.sqlite"))
        assert conn.execute("SELECT COUNT(*) FROM rs_row WHERE data_id='Q_SQL'").fetchone()[0] == 0
        conn.close()
        rc, out = _data(capsys, "delete-row", str(mod), "OrderDB", "Q_SQL")
        assert rc == 1 and "找不到" in out

    def test_missing_sqlite(self, tmp_path, capsys):
        (tmp_path / "m" / "data").mkdir(parents=True)
        rc, out = _data(capsys, "set", str(tmp_path / "m"), "T", "D", "a=1")
        assert rc == 1 and "SQLite 文件不存在" in out


# ---------------------------------------------------------------- capabilities.pitfalls 与 skill
class TestCapabilitiesPitfalls:
    REQUIRED = {"verify_strict_subset", "xml_attr_escape", "sql_placeholder", "sql_blank_fallback",
                "dialog", "db_assertion", "waittime_ms", "native_assert_over_evaluate"}

    def test_capabilities_contains_pitfalls(self):
        caps = get_capabilities()
        pitfalls = caps["pitfalls"]
        assert isinstance(pitfalls, list) and len(pitfalls) >= 6
        assert self.REQUIRED <= {p["id"] for p in pitfalls}
        json.dumps(caps, ensure_ascii=False)  # 可序列化

    def test_pitfall_shape(self):
        ids = [p["id"] for p in PITFALLS]
        assert len(ids) == len(set(ids))
        for p in PITFALLS:
            assert p["title"] and p["wrong"] and p["right"]
            assert "lint" in p

    def test_capabilities_returns_copy(self):
        get_capabilities()["pitfalls"][0]["id"] = "mutated"
        assert PITFALLS[0]["id"] != "mutated"

    @pytest.mark.parametrize("skill", ["rodski-skill--rodski-case-writer", "rodski-test-guide"])
    def test_skill_contract_cheatsheet_same_source(self, skill):
        path = REPO / "rodski-skills" / skill / "SKILL.md"
        if not path.is_file():
            pytest.skip("rodski-skills 不在仓库中")
        text = path.read_text(encoding="utf-8")
        assert "契约速查" in text
        for p in PITFALLS:
            assert f"`{p['id']}`" in text, f"{skill} 契约速查缺少 {p['id']}"

    def test_case_writer_waittime_is_milliseconds(self):
        path = REPO / "rodski-skills" / "rodski-skill--rodski-case-writer" / "SKILL.md"
        if not path.is_file():
            pytest.skip("rodski-skills 不在仓库中")
        text = path.read_text(encoding="utf-8")
        assert "当前单位为秒" not in text
        # 契约速查位于 skill 前部（在「范围与上下文」之前）
        assert text.index("契约速查") < text.index("## 范围与上下文")
