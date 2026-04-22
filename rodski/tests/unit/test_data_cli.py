"""data CLI 单元测试 — v6.0.0 SQLite-only"""
import sqlite3
import pytest
from pathlib import Path
from argparse import Namespace
from rodski_cli.data import handle


def _make_module(tmp_path: Path, tables_spec: dict = None) -> Path:
    mod = tmp_path / "mod"
    (mod / "data").mkdir(parents=True)
    if tables_spec:
        db = mod / "data" / "data.sqlite"
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
        for table_name, rows in tables_spec.items():
            conn.execute("INSERT INTO rs_datatable VALUES (?,?,?,?,?,?)",
                         (table_name, table_name, 'data', 'standard', '', ''))
            all_fields = sorted({f for row in rows.values() for f in row})
            for i, field in enumerate(all_fields):
                conn.execute("INSERT INTO rs_datatable_field VALUES (?,?,?)", (table_name, field, i))
            for data_id, row_data in rows.items():
                conn.execute("INSERT INTO rs_row VALUES (?,?,?)", (table_name, data_id, ''))
                for fn, fv in row_data.items():
                    conn.execute("INSERT INTO rs_field VALUES (?,?,?,?)", (table_name, data_id, fn, fv))
        conn.commit()
        conn.close()
    return mod


_LOGIN = {"Login": {
    "L001": {"username": "admin", "password": "secret"},
    "L002": {"username": "user", "password": "pass"},
}}


class TestDataList:
    def test_lists_tables(self, tmp_path, capsys):
        mod = _make_module(tmp_path, _LOGIN)
        handle(Namespace(data_cmd="list", module=str(mod)))
        assert "Login" in capsys.readouterr().out

    def test_ignores_nonstandard_sqlite_filename(self, tmp_path, capsys):
        mod = _make_module(tmp_path, _LOGIN)
        # create other.sqlite with a Hidden table — should not appear
        db = mod / "data" / "other.sqlite"
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
        conn.execute("INSERT INTO rs_datatable VALUES ('Hidden','Hidden','data','standard','','')")
        conn.execute("INSERT INTO rs_datatable_field VALUES ('Hidden','value',0)")
        conn.execute("INSERT INTO rs_row VALUES ('Hidden','H001','')")
        conn.execute("INSERT INTO rs_field VALUES ('Hidden','H001','value','secret')")
        conn.commit()
        conn.close()
        handle(Namespace(data_cmd="list", module=str(mod)))
        out = capsys.readouterr().out
        assert "Login" in out
        assert "Hidden" not in out

    def test_empty_module(self, tmp_path, capsys):
        mod = _make_module(tmp_path)
        handle(Namespace(data_cmd="list", module=str(mod)))
        assert "无数据表" in capsys.readouterr().out


class TestDataSchema:
    def test_shows_fields(self, tmp_path, capsys):
        mod = _make_module(tmp_path, _LOGIN)
        handle(Namespace(data_cmd="schema", module=str(mod), table="Login"))
        out = capsys.readouterr().out
        assert "username" in out
        assert "password" in out

    def test_missing_table(self, tmp_path):
        mod = _make_module(tmp_path, _LOGIN)
        assert handle(Namespace(data_cmd="schema", module=str(mod), table="NoSuch")) == 1


class TestDataShow:
    def test_shows_row(self, tmp_path, capsys):
        mod = _make_module(tmp_path, _LOGIN)
        handle(Namespace(data_cmd="show", module=str(mod), table="Login", data_id="L001"))
        assert "admin" in capsys.readouterr().out

    def test_missing_row(self, tmp_path):
        mod = _make_module(tmp_path, _LOGIN)
        assert handle(Namespace(data_cmd="show", module=str(mod), table="Login", data_id="X999")) == 1


class TestDataQuery:
    def test_lists_rows(self, tmp_path, capsys):
        mod = _make_module(tmp_path, _LOGIN)
        handle(Namespace(data_cmd="query", module=str(mod), table="Login", limit=50))
        out = capsys.readouterr().out
        assert "L001" in out
        assert "L002" in out


class TestDataValidate:
    def test_valid_module(self, tmp_path, capsys):
        mod = _make_module(tmp_path, _LOGIN)
        rc = handle(Namespace(data_cmd="validate", module=str(mod)))
        assert rc == 0
        assert "OK" in capsys.readouterr().out

    def test_xml_legacy_fails(self, tmp_path, capsys):
        mod = _make_module(tmp_path)
        (mod / "data" / "data.xml").write_text("<datatables/>", encoding="utf-8")
        rc = handle(Namespace(data_cmd="validate", module=str(mod)))
        assert rc == 1
