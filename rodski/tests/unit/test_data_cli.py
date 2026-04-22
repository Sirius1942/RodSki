"""data CLI 单元测试"""
import sqlite3
import pytest
from pathlib import Path
from unittest.mock import patch
from argparse import Namespace
from rodski_cli.data import handle


def _make_module(tmp_path: Path, xml_content: str = None) -> Path:
    mod = tmp_path / "mod"
    (mod / "data").mkdir(parents=True)
    xml = xml_content or (
        '<?xml version="1.0"?><datatables>'
        '<datatable name="Login">'
        '<row id="L001"><field name="username">admin</field><field name="password">secret</field></row>'
        '<row id="L002"><field name="username">user</field><field name="password">pass</field></row>'
        '</datatable></datatables>'
    )
    (mod / "data" / "data.xml").write_text(xml, encoding="utf-8")
    return mod


class TestDataList:
    def test_lists_tables(self, tmp_path, capsys):
        mod = _make_module(tmp_path)
        handle(Namespace(data_cmd="list", module=str(mod)))
        out = capsys.readouterr().out
        assert "Login" in out

    def test_empty_module(self, tmp_path, capsys):
        mod = tmp_path / "empty"
        (mod / "data").mkdir(parents=True)
        handle(Namespace(data_cmd="list", module=str(mod)))
        out = capsys.readouterr().out
        assert "无数据表" in out


class TestDataSchema:
    def test_shows_fields(self, tmp_path, capsys):
        mod = _make_module(tmp_path)
        handle(Namespace(data_cmd="schema", module=str(mod), table="Login"))
        out = capsys.readouterr().out
        assert "username" in out
        assert "password" in out

    def test_missing_table(self, tmp_path, capsys):
        mod = _make_module(tmp_path)
        rc = handle(Namespace(data_cmd="schema", module=str(mod), table="NoSuch"))
        assert rc == 1


class TestDataShow:
    def test_shows_row(self, tmp_path, capsys):
        mod = _make_module(tmp_path)
        handle(Namespace(data_cmd="show", module=str(mod), table="Login", data_id="L001"))
        out = capsys.readouterr().out
        assert "admin" in out

    def test_missing_row(self, tmp_path, capsys):
        mod = _make_module(tmp_path)
        rc = handle(Namespace(data_cmd="show", module=str(mod), table="Login", data_id="X999"))
        assert rc == 1


class TestDataQuery:
    def test_lists_rows(self, tmp_path, capsys):
        mod = _make_module(tmp_path)
        handle(Namespace(data_cmd="query", module=str(mod), table="Login", limit=50))
        out = capsys.readouterr().out
        assert "L001" in out
        assert "L002" in out


class TestDataValidate:
    def test_valid_module(self, tmp_path, capsys):
        mod = _make_module(tmp_path)
        rc = handle(Namespace(data_cmd="validate", module=str(mod), strict=False))
        assert rc == 0
        assert "OK" in capsys.readouterr().out

    def test_strict_drift_warning(self, tmp_path, capsys):
        xml = (
            '<?xml version="1.0"?><datatables>'
            '<datatable name="Login">'
            '<row id="L001"><field name="username">a</field></row>'
            '<row id="L002"><field name="username">b</field><field name="extra">x</field></row>'
            '</datatable></datatables>'
        )
        mod = _make_module(tmp_path, xml)
        handle(Namespace(data_cmd="validate", module=str(mod), strict=True))
        out = capsys.readouterr().out
        assert "WARN" in out

    def test_conflict_fails(self, tmp_path, capsys):
        mod = _make_module(tmp_path)
        # create SQLite with same table name as XML
        db = mod / "data" / "testdata.sqlite"
        conn = sqlite3.connect(str(db))
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
        conn.execute("INSERT INTO rs_datatable VALUES ('Login','Login','data','standard','','')")
        conn.execute("INSERT INTO rs_datatable_field VALUES ('Login','username',0)")
        conn.execute("INSERT INTO rs_row VALUES ('Login','L001','')")
        conn.execute("INSERT INTO rs_field VALUES ('Login','L001','username','other')")
        conn.commit()
        conn.close()
        rc = handle(Namespace(data_cmd="validate", module=str(mod), strict=False))
        assert rc == 1
