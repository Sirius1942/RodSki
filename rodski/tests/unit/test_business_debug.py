"""Tests for the standalone business-model debug CLI."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from business_debug import main


ROOT = Path(__file__).parents[2]
SCHEMA = (ROOT / "core" / "sqlite_schema.py").read_text(encoding="utf-8")
DDL_START = SCHEMA.index('SQLITE_DDL = """') + len('SQLITE_DDL = """')
DDL_END = SCHEMA.index('"""', DDL_START)


def _make_module(tmp_path: Path) -> Path:
    module = tmp_path / "module"
    (module / "business").mkdir(parents=True)
    (module / "data").mkdir()
    (module / "model").mkdir()
    (module / "result").mkdir()

    (module / "business" / "business.xml").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<business_models version="0.1">
  <business_model id="demo_flow" name="Debug demo" version="1">
    <nodes>
      <node id="start" />
      <node id="finish" />
    </nodes>
    <edges><edge from="start" to="finish" /></edges>
    <flows><flow id="F_OK" type="basic" path="start&gt;finish" /></flows>
  </business_model>
</business_models>
""",
        encoding="utf-8",
    )

    with sqlite3.connect(module / "data" / "data.sqlite") as conn:
        conn.executescript(SCHEMA[DDL_START:DDL_END])
        conn.execute(
            "INSERT INTO rs_datatable(table_name, model_name, table_kind, row_mode) VALUES(?,?,?,?)",
            ("demo_flow", "demo_flow", "data", "standard"),
        )
        conn.execute(
            "INSERT INTO rs_datatable(table_name, model_name, table_kind, row_mode) VALUES(?,?,?,?)",
            ("demo_flow_verify", "demo_flow", "verify", "standard"),
        )
        conn.execute(
            "INSERT INTO rs_datatable_field(table_name, field_name, field_order) VALUES(?,?,?)",
            ("demo_flow", "value", 0),
        )
        conn.execute(
            "INSERT INTO rs_datatable_field(table_name, field_name, field_order) VALUES(?,?,?)",
            ("demo_flow_verify", "expected_path", 0),
        )
        conn.execute("INSERT INTO rs_row(table_name, data_id) VALUES(?,?)", ("demo_flow", "D1"))
        conn.execute("INSERT INTO rs_field(table_name, data_id, field_name, field_value) VALUES(?,?,?,?)",
                     ("demo_flow", "D1", "value", "debug"))
        conn.execute("INSERT INTO rs_row(table_name, data_id) VALUES(?,?)", ("demo_flow_verify", "V1"))
        conn.execute("INSERT INTO rs_field(table_name, data_id, field_name, field_value) VALUES(?,?,?,?)",
                     ("demo_flow_verify", "V1", "expected_path", "start>finish"))
    return module


def test_debug_cli_executes_one_invocation_without_formal_result(capsys, tmp_path):
    module = _make_module(tmp_path)
    formal_result = module / "result" / "result.xml"
    formal_result.write_text("sentinel", encoding="utf-8")

    rc = main([
        "--module", str(module),
        "--ref", "demo_flow",
        "--flow", "F_OK",
        "--input", "D1",
        "--expect", "V1",
    ])

    captured = capsys.readouterr()
    assert rc == 0
    assert "DEBUG business model" in captured.out
    assert "status: PASS" in captured.out
    assert "actual_path: start>finish" in captured.out
    assert formal_result.read_text(encoding="utf-8") == "sentinel"


def test_debug_cli_returns_nonzero_for_business_assertion(capsys, tmp_path):
    module = _make_module(tmp_path)
    with sqlite3.connect(module / "data" / "data.sqlite") as conn:
        conn.execute(
            "UPDATE rs_field SET field_value=? WHERE table_name=? AND data_id=? AND field_name=?",
            ("start>wrong", "demo_flow_verify", "V1", "expected_path"),
        )

    rc = main([
        "--module", str(module),
        "--ref", "demo_flow",
        "--flow", "F_OK",
        "--input", "D1",
        "--expect", "V1",
    ])

    captured = capsys.readouterr()
    assert rc == 1
    assert "status: FAIL" in captured.out
    assert "Path mismatch" in captured.out or "expected_path" in captured.out


def test_debug_cli_requires_explicit_business_selection():
    parser_error = None
    try:
        main([])
    except SystemExit as exc:
        parser_error = exc
    assert parser_error is not None
    assert parser_error.code == 2


def test_debug_cli_reuses_keyword_engine_for_interface_steps(capsys, tmp_path, monkeypatch):
    module = _make_module(tmp_path)
    (module / "business" / "business.xml").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<business_models version="0.1">
  <business_model id="send_flow" name="Send debug" version="1">
    <nodes>
      <node id="start" />
      <node id="request">
        <steps><test_step action="send" model="EchoAPI" data="${Business.InputDataID}" /></steps>
      </node>
      <node id="finish" />
    </nodes>
    <edges>
      <edge from="start" to="request" />
      <edge from="request" to="finish" />
    </edges>
    <flows><flow id="F_SEND" type="basic" path="start&gt;request&gt;finish" /></flows>
  </business_model>
</business_models>
""",
        encoding="utf-8",
    )
    (module / "model" / "model.xml").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<models>
  <model name="EchoAPI" type="interface">
    <element name="_method" type="http_method"><location type="static">POST</location></element>
    <element name="_url" type="http_url"><location type="static">http://example.test/echo</location></element>
    <element name="username" type="field"><location type="field">username</location></element>
  </model>
</models>
""",
        encoding="utf-8",
    )
    with sqlite3.connect(module / "data" / "data.sqlite") as conn:
        conn.execute(
            "INSERT INTO rs_datatable(table_name, model_name, table_kind, row_mode) VALUES(?,?,?,?)",
            ("send_flow", "send_flow", "data", "standard"),
        )
        conn.execute(
            "INSERT INTO rs_datatable(table_name, model_name, table_kind, row_mode) VALUES(?,?,?,?)",
            ("send_flow_verify", "send_flow", "verify", "standard"),
        )
        conn.execute(
            "INSERT INTO rs_datatable_field(table_name, field_name, field_order) VALUES(?,?,?)",
            ("send_flow", "username", 0),
        )
        for order, field in enumerate(("status", "expected_path")):
            conn.execute(
                "INSERT INTO rs_datatable_field(table_name, field_name, field_order) VALUES(?,?,?)",
                ("send_flow_verify", field, order),
            )
        conn.execute("INSERT INTO rs_row(table_name, data_id) VALUES(?,?)", ("send_flow", "D1"))
        conn.execute(
            "INSERT INTO rs_field(table_name, data_id, field_name, field_value) VALUES(?,?,?,?)",
            ("send_flow", "D1", "username", "admin"),
        )
        conn.execute("INSERT INTO rs_row(table_name, data_id) VALUES(?,?)", ("send_flow_verify", "V1"))
        for field, value in (("status", "200"), ("expected_path", "start>request>finish")):
            conn.execute(
                "INSERT INTO rs_field(table_name, data_id, field_name, field_value) VALUES(?,?,?,?)",
                ("send_flow_verify", "V1", field, value),
            )

    requests = []

    class FakeResponse:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {"message": "ok"}

    def fake_send_request(**kwargs):
        requests.append(kwargs)
        return FakeResponse()

    from rodski.api.rest_helper import RestHelper
    monkeypatch.setattr(RestHelper, "send_request", staticmethod(fake_send_request))

    rc = main([
        "--module", str(module),
        "--ref", "send_flow",
        "--flow", "F_SEND",
        "--input", "D1",
        "--expect", "V1",
    ])

    captured = capsys.readouterr()
    assert rc == 0
    assert "status: PASS" in captured.out
    assert requests and requests[0]["body"] == {"username": "admin"}
