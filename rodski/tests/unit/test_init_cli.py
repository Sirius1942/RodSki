"""init CLI 单元测试 — v6.0.0"""
import sqlite3
import pytest
from pathlib import Path
from argparse import Namespace
from rodski_cli.init import handle


class TestInitBasic:
    def test_creates_dirs(self, tmp_path):
        target = tmp_path / "mymod"
        handle(Namespace(target=str(target), no_sqlite=True, force=False))
        for d in ["case", "model", "fun", "data", "result"]:
            assert (target / d).is_dir()

    def test_creates_template_files(self, tmp_path):
        target = tmp_path / "mymod"
        handle(Namespace(target=str(target), no_sqlite=True, force=False))
        assert (target / "model" / "model.xml").exists()
        assert (target / "data" / "globalvalue.xml").exists()
        assert not (target / "data" / "data.xml").exists()

    def test_no_sqlite_flag_skips_db(self, tmp_path):
        target = tmp_path / "mymod"
        handle(Namespace(target=str(target), no_sqlite=True, force=False))
        assert not (target / "data" / "data.sqlite").exists()


class TestInitSQLite:
    def test_default_creates_sqlite(self, tmp_path):
        target = tmp_path / "mymod"
        handle(Namespace(target=str(target), no_sqlite=False, force=False))
        assert (target / "data" / "data.sqlite").exists()

    def test_sqlite_has_meta_tables(self, tmp_path):
        target = tmp_path / "mymod"
        handle(Namespace(target=str(target), no_sqlite=False, force=False))
        db = target / "data" / "data.sqlite"
        conn = sqlite3.connect(str(db))
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()
        assert {"rs_datatable", "rs_datatable_field", "rs_row", "rs_field"} <= tables

    def test_sqlite_usable_by_data_manager(self, tmp_path):
        from core.data_table_parser import DataTableParser
        target = tmp_path / "mymod"
        handle(Namespace(target=str(target), no_sqlite=False, force=False))
        tables = DataTableParser(str(target / "data")).parse_all_tables()
        assert isinstance(tables, dict)


class TestInitForce:
    def test_skip_existing_without_force(self, tmp_path):
        target = tmp_path / "mymod"
        handle(Namespace(target=str(target), no_sqlite=False, force=False))
        db = target / "data" / "data.sqlite"
        mtime1 = db.stat().st_mtime
        handle(Namespace(target=str(target), no_sqlite=False, force=False))
        assert db.stat().st_mtime == mtime1

    def test_force_overwrites(self, tmp_path):
        target = tmp_path / "mymod"
        handle(Namespace(target=str(target), no_sqlite=False, force=False))
        handle(Namespace(target=str(target), no_sqlite=False, force=True))
        assert (target / "data" / "data.sqlite").exists()
