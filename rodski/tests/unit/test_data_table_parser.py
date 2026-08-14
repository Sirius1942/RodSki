"""DataTableParser 单元测试 — v6.0.0 SQLite-only"""
import sqlite3
import pytest
from pathlib import Path
from unittest.mock import patch
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


class TestInit:
    def test_init_sets_empty_tables_dict(self, tmp_path):
        """__init__ 后 tables 应为空 dict（而不是 None）"""
        parser = DataTableParser(str(tmp_path))
        assert parser.tables == {}
        assert isinstance(parser.tables, dict)

    def test_init_sets_sqlite_source_to_none(self, tmp_path):
        """__init__ 后 _sqlite_source 应为 None（而不是空字符串等其他假值）"""
        parser = DataTableParser(str(tmp_path))
        assert parser._sqlite_source is None


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

    def test_merge_table_updates_existing_without_dropping_old_rows(self, tmp_path):
        """merge_table 对已存在的逻辑表应是增量更新（update），不能整表替换掉旧行"""
        d = tmp_path / "data"
        d.mkdir()
        parser = DataTableParser(str(d))
        parser.parse_all_tables()
        parser.merge_table("Tmp", {"T001": {"x": "1"}})
        parser.merge_table("Tmp", {"T002": {"x": "2"}})
        # T001 应仍然存在，没有被第二次 merge_table 覆盖掉
        assert parser.get_data("Tmp", "T001")["x"] == "1"
        assert parser.get_data("Tmp", "T002")["x"] == "2"

    def test_close_clears_tables_and_sqlite_source(self, tmp_path):
        """close() 应清空 tables 并将 _sqlite_source 重置为 None（而非其他假值）"""
        d = tmp_path / "data"
        d.mkdir()
        _make_sqlite(d, {"Order": {"O001": {"amount": "100"}}})
        parser = DataTableParser(str(d))
        parser.parse_all_tables()
        assert parser._sqlite_source is not None

        parser.close()
        assert parser.tables == {}
        assert parser._sqlite_source is None

    def test_sqlite_filename_is_exact_lowercase(self, tmp_path):
        """sqlite_file 属性拼接的文件名必须精确为 'data.sqlite'（全小写）"""
        d = tmp_path / "data"
        d.mkdir()
        parser = DataTableParser(str(d))
        assert parser.sqlite_file.name == "data.sqlite"

    def test_legacy_xml_filenames_are_exact_lowercase(self, tmp_path):
        """废弃文件检测的文件名必须精确为 'data.xml' / 'data_verify.xml'（全小写）

        通过 mock Path.exists 拦截实际被查询的文件名，避免大小写不敏感的
        文件系统（如 macOS APFS 默认配置）掩盖大小写拼写错误。
        """
        d = tmp_path / "data"
        d.mkdir()
        parser = DataTableParser(str(d))

        queried_names = []
        original_exists = Path.exists

        def spy_exists(self):
            queried_names.append(self.name)
            return False

        with patch.object(Path, "exists", spy_exists):
            parser.parse_all_tables()

        assert "data.xml" in queried_names
        assert "data_verify.xml" in queried_names
