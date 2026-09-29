"""Unit tests for plan support of nested case directories (v11.5.0 WI-63-03)."""
from __future__ import annotations

import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict

import pytest

from rodski.core.exceptions import PlanCaseFileRequiredError
from rodski.core.plan_parser import PlanParser
from rodski.core.test_plan_selection import TestPlanSelection


class TestPlanParserFileAttribute:
    """Test plan_parser.py support for case@file and case_dir elements."""

    def test_parse_case_with_file(self, tmp_path: Path):
        """plan_parser parses case@file attribute correctly."""
        plan_xml = tmp_path / "test.xml"
        plan_xml.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<test_plan id="test" kind="suite">
  <case id="TC001" file="order/refund.xml" execute="是"/>
</test_plan>
""")
        parser = PlanParser(str(plan_xml))
        plan = parser.parse_plan()
        assert plan["cases"][0]["file"] == "order/refund.xml"

    def test_parse_case_without_file(self, tmp_path: Path):
        """plan_parser handles case without file attribute (single-file compatibility)."""
        plan_xml = tmp_path / "test.xml"
        plan_xml.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<test_plan id="test" kind="suite">
  <case id="TC001" execute="是"/>
</test_plan>
""")
        parser = PlanParser(str(plan_xml))
        plan = parser.parse_plan()
        assert "file" not in plan["cases"][0]

    def test_parse_case_dir(self, tmp_path: Path):
        """plan_parser parses case_dir elements correctly."""
        plan_xml = tmp_path / "test.xml"
        plan_xml.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<test_plan id="test" kind="suite">
  <case_dir path="order" execute="是"/>
  <case_dir path="" execute="否"/>
</test_plan>
""")
        parser = PlanParser(str(plan_xml))
        plan = parser.parse_plan()
        assert len(plan["case_dirs"]) == 2
        assert plan["case_dirs"][0]["path"] == "order"
        assert plan["case_dirs"][0]["execute"] == "是"
        assert plan["case_dirs"][1]["path"] == ""
        assert plan["case_dirs"][1]["execute"] == "否"

    def test_mixed_case_and_case_dir(self, tmp_path: Path):
        """plan_parser handles mixed case and case_dir elements."""
        plan_xml = tmp_path / "test.xml"
        plan_xml.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<test_plan id="test" kind="suite">
  <case id="TC001" file="a.xml" execute="是"/>
  <case_dir path="order" execute="是"/>
  <case id="TC002" file="b.xml" execute="是"/>
</test_plan>
""")
        parser = PlanParser(str(plan_xml))
        plan = parser.parse_plan()
        assert len(plan["cases"]) == 2
        assert len(plan["case_dirs"]) == 1


class TestPlanSelectionCaseUid:
    """Test test_plan_selection.py case_uid-based indexing."""

    def _make_case(self, case_id: str, case_file: str) -> Dict[str, Any]:
        return {
            "case_id": case_id,
            "case_file": case_file,
            "id": case_id,
            "scenarios": [],
        }

    def test_single_file_compatibility(self):
        """Plan without file attribute works when module has single case file."""
        cases = [self._make_case("TC001", "smoke.xml")]
        plan = {
            "id": "test",
            "kind": "suite",
            "execute": "是",
            "default_execute": "否",
            "cases": [{"id": "TC001", "execute": "是", "scenarios": []}],
            "case_dirs": [],
            "debug": {},
        }
        selection = TestPlanSelection(cases, plan)
        result = selection.select()
        assert len(result["selected"]) == 1
        assert result["selected"][0]["case_id"] == "TC001"

    def test_multi_file_requires_explicit_file(self):
        """Plan without file attribute raises SKI207 when multiple files contain same ID."""
        cases = [
            self._make_case("TC001", "order/basic.xml"),
            self._make_case("TC001", "user/basic.xml"),
        ]
        plan = {
            "id": "test",
            "kind": "suite",
            "execute": "是",
            "default_execute": "否",
            "cases": [{"id": "TC001", "execute": "是", "scenarios": []}],
            "case_dirs": [],
            "debug": {},
        }
        selection = TestPlanSelection(cases, plan)
        with pytest.raises(PlanCaseFileRequiredError) as exc_info:
            selection.select()
        assert exc_info.value.case_id == "TC001"
        assert "order/basic.xml" in exc_info.value.candidates
        assert "user/basic.xml" in exc_info.value.candidates

    def test_explicit_file_disambiguates(self):
        """Plan with file attribute correctly selects specific file when IDs collide."""
        cases = [
            self._make_case("TC001", "order/basic.xml"),
            self._make_case("TC001", "user/basic.xml"),
        ]
        plan = {
            "id": "test",
            "kind": "suite",
            "execute": "是",
            "default_execute": "否",
            "cases": [{"id": "TC001", "file": "user/basic.xml", "execute": "是", "scenarios": []}],
            "case_dirs": [],
            "debug": {},
        }
        selection = TestPlanSelection(cases, plan)
        result = selection.select()
        assert len(result["selected"]) == 1
        assert result["selected"][0]["case"]["case_file"] == "user/basic.xml"

    def test_stale_file_reference(self):
        """Plan referencing non-existent file reports stale reference."""
        cases = [self._make_case("TC001", "smoke.xml")]
        plan = {
            "id": "test",
            "kind": "suite",
            "execute": "是",
            "default_execute": "否",
            "cases": [{"id": "TC001", "file": "nonexist.xml", "execute": "是", "scenarios": []}],
            "case_dirs": [],
            "debug": {},
        }
        selection = TestPlanSelection(cases, plan)
        result = selection.select()
        assert len(result["stale_references"]) == 1
        assert result["stale_references"][0]["case_id"] == "TC001"
        assert result["stale_references"][0]["case_file"] == "nonexist.xml"

    def test_stale_id_in_file(self):
        """Plan referencing non-existent ID in existing file reports stale reference."""
        cases = [self._make_case("TC001", "smoke.xml")]
        plan = {
            "id": "test",
            "kind": "suite",
            "execute": "是",
            "default_execute": "否",
            "cases": [{"id": "TC999", "file": "smoke.xml", "execute": "是", "scenarios": []}],
            "case_dirs": [],
            "debug": {},
        }
        selection = TestPlanSelection(cases, plan)
        result = selection.select()
        assert len(result["stale_references"]) == 1
        assert result["stale_references"][0]["case_id"] == "TC999"


class TestPlanSelectionCaseDir:
    """Test test_plan_selection.py case_dir support."""

    def _make_case(self, case_id: str, case_file: str) -> Dict[str, Any]:
        return {
            "case_id": case_id,
            "case_file": case_file,
            "id": case_id,
            "scenarios": [],
        }

    def test_case_dir_not_found(self, tmp_path: Path):
        """case_dir referencing non-existent directory reports stale reference."""
        module_dir = tmp_path / "module"
        (module_dir / "case").mkdir(parents=True)

        cases = [self._make_case("TC001", "smoke.xml")]
        plan = {
            "id": "test",
            "kind": "suite",
            "execute": "是",
            "default_execute": "否",
            "cases": [],
            "case_dirs": [{"path": "nonexist", "execute": "是"}],
            "debug": {},
        }
        selection = TestPlanSelection(cases, plan, module_dir=module_dir)
        result = selection.select()
        assert len(result["stale_references"]) == 1
        assert result["stale_references"][0]["type"] == "case_dir"
        assert result["stale_references"][0]["path"] == "nonexist"

    def _plan_without_file(self, case_id: str) -> Dict[str, Any]:
        return {
            "id": "test",
            "kind": "suite",
            "execute": "是",
            "default_execute": "否",
            "cases": [{"id": case_id, "execute": "是"}],
            "debug": {},
        }

    def test_missing_file_rejected_when_module_has_disabled_only_file(self, tmp_path: Path):
        """Owner C2: omit file only when the module has exactly one case file.

        A second file holding only execute="否" cases is absent from parsed
        cases but still counts, so a module-unique id must still raise SKI207.
        """
        module_dir = tmp_path / "module"
        (module_dir / "case").mkdir(parents=True)
        (module_dir / "case" / "login.xml").write_text("<cases/>", encoding="utf-8")
        (module_dir / "case" / "legacy.xml").write_text("<cases/>", encoding="utf-8")

        cases = [self._make_case("APP001", "login.xml")]
        selection = TestPlanSelection(cases, self._plan_without_file("APP001"), module_dir=module_dir)
        with pytest.raises(PlanCaseFileRequiredError) as exc:
            selection.select()
        assert "APP001" in str(exc.value)

    def test_missing_file_allowed_when_module_has_single_file(self, tmp_path: Path):
        module_dir = tmp_path / "module"
        (module_dir / "case" / "only").mkdir(parents=True)
        (module_dir / "case" / "only" / "only_case.xml").write_text("<cases/>", encoding="utf-8")

        cases = [self._make_case("TC002", "only/only_case.xml")]
        result = TestPlanSelection(cases, self._plan_without_file("TC002"), module_dir=module_dir).select()
        assert [e["case_id"] for e in result["selected"]] == ["TC002"]

    def test_unknown_id_without_file_is_stale_in_multi_file_module(self, tmp_path: Path):
        """An id present in no file has nothing to disambiguate: stale, not SKI207 or a crash."""
        module_dir = tmp_path / "module"
        (module_dir / "case").mkdir(parents=True)
        (module_dir / "case" / "a.xml").write_text("<cases/>", encoding="utf-8")
        (module_dir / "case" / "b.xml").write_text("<cases/>", encoding="utf-8")

        cases = [self._make_case("TC001", "a.xml"), self._make_case("TC001", "b.xml")]
        result = TestPlanSelection(cases, self._plan_without_file("NONEXISTENT_CASE"), module_dir=module_dir).select()
        assert result["selected"] == []
        assert result["stale_references"] == [
            {"type": "case", "case_id": "NONEXISTENT_CASE", "reason": "not_found"}
        ]


if __name__ == "__main__":
    pytest.main([__file__, "-xvs"])
