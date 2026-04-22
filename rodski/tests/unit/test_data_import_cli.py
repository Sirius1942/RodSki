"""data import CLI 单元测试"""
import sqlite3
import pytest
from pathlib import Path
from rodski_cli.data_import import run_import


def _make_module(tmp_path, data_xml=None, verify_xml=None):
    mod = tmp_path / "mod"
    (mod / "data").mkdir(parents=True)
    if data_xml:
        (mod / "data" / "data.xml").write_text(data_xml, encoding="utf-8")
    if verify_xml:
        (mod / "data" / "data_verify.xml").write_text(verify_xml, encoding="utf-8")
    return str(mod)


_DATA_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<datatables>
  <datatable name="Login">
    <row id="L001"><field name="username">admin</field><field name="password">123</field></row>
    <row id="L002"><field name="username">user</field><field name="password">456</field></row>
  </datatable>
</datatables>'''

_VERIFY_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<datatables>
  <datatable name="Login_verify">
    <row id="V001"><field name="msg">ok</field></row>
  </datatable>
</datatables>'''


def _read_table(db_path, table_name):
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute(
        "SELECT r.data_id, f.field_name, f.field_value FROM rs_row r "
        "JOIN rs_field f ON r.table_name=f.table_name AND r.data_id=f.data_id "
        "WHERE r.table_name=? ORDER BY r.data_id, f.field_name",
        (table_name,)
    ).fetchall()
    conn.close()
    result = {}
    for data_id, field, value in rows:
        result.setdefault(data_id, {})[field] = value
    return result


class TestDataImport:
    def test_imports_data_xml(self, tmp_path):
        mod = _make_module(tmp_path, data_xml=_DATA_XML)
        assert run_import(mod) == 0
        rows = _read_table(Path(mod) / "data" / "data.sqlite", "Login")
        assert rows["L001"]["username"] == "admin"
        assert rows["L002"]["password"] == "456"

    def test_imports_verify_xml_sets_kind(self, tmp_path):
        mod = _make_module(tmp_path, verify_xml=_VERIFY_XML)
        run_import(mod)
        conn = sqlite3.connect(str(Path(mod) / "data" / "data.sqlite"))
        kind = conn.execute(
            "SELECT table_kind FROM rs_datatable WHERE table_name='Login_verify'"
        ).fetchone()[0]
        conn.close()
        assert kind == "verify"

    def test_idempotent_skip_by_default(self, tmp_path):
        mod = _make_module(tmp_path, data_xml=_DATA_XML)
        run_import(mod)
        # modify value directly in db
        db = Path(mod) / "data" / "data.sqlite"
        conn = sqlite3.connect(str(db))
        conn.execute("UPDATE rs_field SET field_value='changed' WHERE table_name='Login' AND data_id='L001' AND field_name='username'")
        conn.commit()
        conn.close()
        run_import(mod)  # should skip
        rows = _read_table(db, "Login")
        assert rows["L001"]["username"] == "changed"

    def test_overwrite_replaces_data(self, tmp_path):
        mod = _make_module(tmp_path, data_xml=_DATA_XML)
        run_import(mod)
        db = Path(mod) / "data" / "data.sqlite"
        conn = sqlite3.connect(str(db))
        conn.execute("UPDATE rs_field SET field_value='changed' WHERE table_name='Login' AND data_id='L001' AND field_name='username'")
        conn.commit()
        conn.close()
        run_import(mod, overwrite=True)
        rows = _read_table(db, "Login")
        assert rows["L001"]["username"] == "admin"

    def test_no_xml_is_noop(self, tmp_path):
        mod = _make_module(tmp_path)
        assert run_import(mod) == 0
        assert not (Path(mod) / "data" / "data.sqlite").exists()

    def test_creates_sqlite_when_missing(self, tmp_path):
        mod = _make_module(tmp_path, data_xml=_DATA_XML)
        db = Path(mod) / "data" / "data.sqlite"
        assert not db.exists()
        run_import(mod)
        assert db.exists()
