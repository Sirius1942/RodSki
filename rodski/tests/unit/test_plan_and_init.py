"""T41-005: plan validator registration and rodski init skeleton tests.

Tests:
- RodskiXmlValidator recognizes 'plan' kind
- rodski init creates plan/ directory
- rodski init creates data/data.sqlite and data/globalvalue.xml
- --no-sqlite prints deprecation warning
"""
import sqlite3
from argparse import Namespace
from pathlib import Path

import pytest

from core.xml_schema_validator import RodskiXmlValidator, SCHEMA_FILES, schemas_directory
from rodski_cli.init import handle


class TestPlanKindRegistration:
    """RodskiXmlValidator should recognize 'plan' kind."""

    def setup_method(self):
        RodskiXmlValidator.clear_schema_cache()

    def teardown_method(self):
        RodskiXmlValidator.clear_schema_cache()

    def test_plan_in_schema_files(self):
        assert "plan" in SCHEMA_FILES
        assert SCHEMA_FILES["plan"] == "plan.xsd"

    def test_kind_plan_constant(self):
        assert RodskiXmlValidator.KIND_PLAN == "plan"

    def test_plan_xsd_exists(self):
        xsd = schemas_directory() / "plan.xsd"
        assert xsd.is_file(), f"plan.xsd not found at {xsd}"

    def test_validate_valid_plan(self, tmp_path):
        p = tmp_path / "demo.xml"
        p.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<test_plan id="demo" title="Demo" kind="suite" execute="是" default_execute="否">\n'
            '  <case id="tc001" execute="是">\n'
            '    <scenario id="sc001" execute="是">\n'
            '      <step no="1" execute="是"/>\n'
            '    </scenario>\n'
            '  </case>\n'
            '</test_plan>',
            encoding="utf-8",
        )
        # Should not raise
        RodskiXmlValidator.validate_file(p, RodskiXmlValidator.KIND_PLAN)

    def test_validate_invalid_plan_raises(self, tmp_path):
        p = tmp_path / "bad.xml"
        p.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<wrong_root/>\n',
            encoding="utf-8",
        )
        with pytest.raises(Exception):
            RodskiXmlValidator.validate_file(p, RodskiXmlValidator.KIND_PLAN)


class TestInitCreatesPlanDir:
    """rodski init should create plan/ directory."""

    def test_plan_dir_created(self, tmp_path):
        target = tmp_path / "proj"
        handle(Namespace(target=str(target), no_sqlite=False, force=False))
        assert (target / "plan").is_dir()

    def test_all_expected_dirs(self, tmp_path):
        target = tmp_path / "proj"
        handle(Namespace(target=str(target), no_sqlite=False, force=False))
        for d in ["case", "model", "fun", "data", "plan", "result"]:
            assert (target / d).is_dir(), f"Missing directory: {d}"


class TestInitCreatesSqliteAndGlobalvalue:
    """rodski init should create data/data.sqlite and data/globalvalue.xml."""

    def test_sqlite_created(self, tmp_path):
        target = tmp_path / "proj"
        handle(Namespace(target=str(target), no_sqlite=False, force=False))
        db = target / "data" / "data.sqlite"
        assert db.is_file()
        conn = sqlite3.connect(str(db))
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()
        assert "rs_datatable_field" in tables

    def test_globalvalue_created(self, tmp_path):
        target = tmp_path / "proj"
        handle(Namespace(target=str(target), no_sqlite=False, force=False))
        gv = target / "data" / "globalvalue.xml"
        assert gv.is_file()
        content = gv.read_text(encoding="utf-8")
        assert "<globalvalue>" in content


class TestNoSqliteDeprecation:
    """--no-sqlite should print deprecation warning to stderr."""

    def test_deprecation_warning(self, tmp_path, capsys):
        target = tmp_path / "proj"
        handle(Namespace(target=str(target), no_sqlite=True, force=False))
        captured = capsys.readouterr()
        assert "已废弃" in captured.err
        assert "data.sqlite" in captured.err
        # sqlite should NOT be created
        assert not (target / "data" / "data.sqlite").exists()
