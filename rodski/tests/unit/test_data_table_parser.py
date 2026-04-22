"""DataTableParser 单元测试 — v6.0.0 SQLite-only"""
import sqlite3
import pytest
from pathlib import Path
from core.data_table_parser import DataTableParser


def _make_sqlite(data_dir: Path, tables_spec: dict, filename: str = "data.sqlite") -> None:
    db = data_dir / filename
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
            for field_name, field_value in row_data.items():
                conn.execute("INSERT INTO rs_field VALUES (?,?,?,?)",
                             (table_name, data_id, field_name, field_value))
    conn.commit()
    conn.close()


class TestEmptyDirectory:
    def test_nonexistent_dir(self, tmp_path):
        parser = DataTableParser(str(tmp_path / "nonexistent"))
        assert parser.parse_all_tables() == {}

    def test_empty_dir(self, tmp_path):
        d = tmp_path / "data"
        d.mkdir()
        assert DataTableParser(str(d)).parse_all_tables() == {}


class TestXmlLegacyDetection:
    def test_data_xml_raises(self, tmp_path):
        from core.exceptions import DataParseError
        d = tmp_path / "data"
        d.mkdir()
        (d / "data.xml").write_text("<datatables/>", encoding="utf-8")
        with pytest.raises(DataParseError, match="data import"):
            DataTableParser(str(d)).parse_all_tables()

    def test_data_verify_xml_raises(self, tmp_path):
        from core.exceptions import DataParseError
        d = tmp_path / "data"
        d.mkdir()
        (d / "data_verify.xml").write_text("<datatables/>", encoding="utf-8")
        with pytest.raises(DataParseError, match="data import"):
            DataTableParser(str(d)).parse_all_tables()


class TestSQLiteOnly:
    def test_sqlite_tables_loaded(self, tmp_path):
        d = tmp_path / "data"
        d.mkdir()
        _make_sqlite(d, {"Order": {"O001": {"amount": "100", "status": "ok"}}})
        parser = DataTableParser(str(d))
        parser.parse_all_tables()
        assert parser.get_data("Order", "O001")["amount"] == "100"

    def test_ignores_nonstandard_sqlite_filename(self, tmp_path):
        d = tmp_path / "data"
        d.mkdir()
        _make_sqlite(d, {"Order": {"O001": {"amount": "100"}}}, filename="other.sqlite")
        parser = DataTableParser(str(d))
        parser.parse_all_tables()
        assert parser.get_data("Order", "O001") == {}

    def test_only_loads_data_sqlite_when_multiple_files_exist(self, tmp_path):
        d = tmp_path / "data"
        d.mkdir()
        _make_sqlite(d, {"Order": {"O001": {"amount": "100"}}})
        _make_sqlite(d, {"Ignored": {"X001": {"value": "skip"}}}, filename="other.sqlite")
        parser = DataTableParser(str(d))
        parser.parse_all_tables()
        assert parser.get_data("Order", "O001")["amount"] == "100"
        assert parser.get_data("Ignored", "X001") == {}

    def test_merge_table_works(self, tmp_path):
        d = tmp_path / "data"
        d.mkdir()
        parser = DataTableParser(str(d))
        parser.parse_all_tables()
        parser.merge_table("Tmp", {"T001": {"x": "1"}})
        assert parser.get_data("Tmp", "T001")["x"] == "1"
