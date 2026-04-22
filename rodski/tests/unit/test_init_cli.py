"""init CLI 单元测试"""
import sqlite3
import pytest
from pathlib import Path
from argparse import Namespace
from rodski_cli.init import handle


class TestInitBasic:
    def test_creates_dirs(self, tmp_path):
        target = tmp_path / "mymod"
        handle(Namespace(target=str(target), with_verify=False, with_sqlite=False, force=False))
        for d in ["case", "model", "fun", "data", "result"]:
            assert (target / d).is_dir()

    def test_creates_template_files(self, tmp_path):
        target = tmp_path / "mymod"
        handle(Namespace(target=str(target), with_verify=False, with_sqlite=False, force=False))
        assert (target / "model" / "model.xml").exists()
        assert (target / "data" / "data.xml").exists()
        assert (target / "data" / "globalvalue.xml").exists()

    def test_with_verify(self, tmp_path):
        target = tmp_path / "mymod"
        handle(Namespace(target=str(target), with_verify=True, with_sqlite=False, force=False))
        assert (target / "data" / "data_verify.xml").exists()

    def test_without_verify(self, tmp_path):
        target = tmp_path / "mymod"
        handle(Namespace(target=str(target), with_verify=False, with_sqlite=False, force=False))
        assert not (target / "data" / "data_verify.xml").exists()


class TestInitSQLite:
    def test_with_sqlite_creates_db(self, tmp_path):
        target = tmp_path / "mymod"
        handle(Namespace(target=str(target), with_verify=False, with_sqlite=True, force=False))
        db = target / "data" / "testdata.sqlite"
        assert db.exists()

    def test_sqlite_has_meta_tables(self, tmp_path):
        target = tmp_path / "mymod"
        handle(Namespace(target=str(target), with_verify=False, with_sqlite=True, force=False))
        db = target / "data" / "testdata.sqlite"
        conn = sqlite3.connect(str(db))
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        conn.close()
        assert {"rs_datatable", "rs_datatable_field", "rs_row", "rs_field"} <= tables

    def test_sqlite_usable_by_data_manager(self, tmp_path):
        """init 生成的骨架可被 DataTableParser 正常加载"""
        from core.data_table_parser import DataTableParser
        target = tmp_path / "mymod"
        handle(Namespace(target=str(target), with_verify=False, with_sqlite=True, force=False))
        dm = DataTableParser(str(target / "data"))
        tables = dm.parse_all_tables()
        assert isinstance(tables, dict)


class TestInitForce:
    def test_skip_existing_without_force(self, tmp_path, capsys):
        target = tmp_path / "mymod"
        handle(Namespace(target=str(target), with_verify=False, with_sqlite=False, force=False))
        (target / "data" / "data.xml").write_text("custom", encoding="utf-8")
        handle(Namespace(target=str(target), with_verify=False, with_sqlite=False, force=False))
        assert (target / "data" / "data.xml").read_text() == "custom"

    def test_force_overwrites(self, tmp_path):
        target = tmp_path / "mymod"
        handle(Namespace(target=str(target), with_verify=False, with_sqlite=False, force=False))
        (target / "data" / "data.xml").write_text("custom", encoding="utf-8")
        handle(Namespace(target=str(target), with_verify=False, with_sqlite=False, force=True))
        assert (target / "data" / "data.xml").read_text() != "custom"
