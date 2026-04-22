"""SQLiteDataSource 单元测试"""
import sqlite3
import pytest
from pathlib import Path
from core.sqlite_data_source import SQLiteDataSource


def _make_db(tmp_path: Path) -> Path:
    db = tmp_path / "testdata.sqlite"
    conn = sqlite3.connect(str(db))
    conn.executescript("""
        CREATE TABLE rs_datatable (
            table_name TEXT PRIMARY KEY,
            model_name TEXT NOT NULL,
            table_kind TEXT NOT NULL,
            row_mode TEXT NOT NULL,
            remark TEXT DEFAULT '',
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE rs_datatable_field (
            table_name TEXT NOT NULL,
            field_name TEXT NOT NULL,
            field_order INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (table_name, field_name)
        );
        CREATE TABLE rs_row (
            table_name TEXT NOT NULL,
            data_id TEXT NOT NULL,
            remark TEXT DEFAULT '',
            PRIMARY KEY (table_name, data_id)
        );
        CREATE TABLE rs_field (
            table_name TEXT NOT NULL,
            data_id TEXT NOT NULL,
            field_name TEXT NOT NULL,
            field_value TEXT NOT NULL,
            PRIMARY KEY (table_name, data_id, field_name)
        );
    """)
    conn.execute("INSERT INTO rs_datatable VALUES ('Login','Login','data','standard','','')")
    conn.execute("INSERT INTO rs_datatable_field VALUES ('Login','username',0)")
    conn.execute("INSERT INTO rs_datatable_field VALUES ('Login','password',1)")
    conn.execute("INSERT INTO rs_row VALUES ('Login','L001','')")
    conn.execute("INSERT INTO rs_field VALUES ('Login','L001','username','admin')")
    conn.execute("INSERT INTO rs_field VALUES ('Login','L001','password','secret')")
    conn.commit()
    conn.close()
    return db


class TestLoadTables:
    def test_loads_rows(self, tmp_path):
        db = _make_db(tmp_path)
        src = SQLiteDataSource(str(db))
        tables = src.load_tables()
        assert "Login" in tables
        assert tables["Login"]["L001"]["username"] == "admin"
        assert tables["Login"]["L001"]["password"] == "secret"
        src.close()

    def test_empty_db(self, tmp_path):
        db = tmp_path / "empty.sqlite"
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
        conn.close()
        src = SQLiteDataSource(str(db))
        assert src.load_tables() == {}
        src.close()


class TestGetSchema:
    def test_returns_field_list(self, tmp_path):
        db = _make_db(tmp_path)
        src = SQLiteDataSource(str(db))
        schemas = src.get_schema()
        assert "Login" in schemas
        assert set(schemas["Login"]) == {"username", "password"}
        src.close()


class TestGetTableNames:
    def test_returns_names(self, tmp_path):
        db = _make_db(tmp_path)
        src = SQLiteDataSource(str(db))
        assert "Login" in src.get_table_names()
        src.close()


class TestClose:
    def test_close_idempotent(self, tmp_path):
        db = _make_db(tmp_path)
        src = SQLiteDataSource(str(db))
        src.load_tables()
        src.close()
        src.close()  # 不应抛异常
