"""Tests for compile_from_selector() and check_plan_selector_conflict()."""
import pytest

from core.test_plan_selection import compile_from_selector, check_plan_selector_conflict


def _metadata():
    """Sample scenario metadata mimicking CaseParser.collect_scenario_metadata_from_cases() output."""
    return [
        {
            "case_id": "tc001",
            "case_priority": "P0",
            "file_tags": ["smoke", "login"],
            "scenario_id": "sc01",
            "scenario_group": "positive",
            "scenario_tags": ["fast"],
            "effective_tags": ["smoke", "login", "fast"],
        },
        {
            "case_id": "tc001",
            "case_priority": "P0",
            "file_tags": ["smoke", "login"],
            "scenario_id": "sc02",
            "scenario_group": "negative",
            "scenario_tags": ["slow"],
            "effective_tags": ["smoke", "login", "slow"],
        },
        {
            "case_id": "tc002",
            "case_priority": "P1",
            "file_tags": ["regression"],
            "scenario_id": "sc03",
            "scenario_group": "positive",
            "scenario_tags": [],
            "effective_tags": ["regression"],
        },
        {
            "case_id": "tc002",
            "case_priority": "P1",
            "file_tags": ["regression"],
            "scenario_id": "sc04",
            "scenario_group": "negative",
            "scenario_tags": ["slow"],
            "effective_tags": ["regression", "slow"],
        },
    ]


class TestCompileFromSelectorTagOR:
    """--tag: OR match against effective_tags."""

    def test_single_tag_matches(self):
        result = compile_from_selector(_metadata(), filter_tags=["smoke"])
        ids = [(e["case_id"], e["scenario_id"]) for e in result["selected"]]
        assert ("tc001", "sc01") in ids
        assert ("tc001", "sc02") in ids
        # tc002 scenarios do not have 'smoke'
        assert ("tc002", "sc03") not in ids
        assert ("tc002", "sc04") not in ids

    def test_multiple_tags_or_match(self):
        result = compile_from_selector(_metadata(), filter_tags=["smoke", "regression"])
        ids = [(e["case_id"], e["scenario_id"]) for e in result["selected"]]
        # All 4 scenarios should match (smoke OR regression)
        assert len(ids) == 4


class TestCompileFromSelectorGroup:
    """--group: exact match against scenario_group."""

    def test_group_exact_match(self):
        result = compile_from_selector(_metadata(), filter_group="negative")
        ids = [(e["case_id"], e["scenario_id"]) for e in result["selected"]]
        assert ids == [("tc001", "sc02"), ("tc002", "sc04")]

    def test_group_no_match(self):
        result = compile_from_selector(_metadata(), filter_group="edge")
        assert result["selected"] == []


class TestCompileFromSelectorExcludeTag:
    """--exclude-tag: remove scenarios whose effective_tags hit the exclude set."""

    def test_exclude_tag_removes_matching(self):
        result = compile_from_selector(_metadata(), exclude_tags=["slow"])
        ids = [(e["case_id"], e["scenario_id"]) for e in result["selected"]]
        # sc02 and sc04 have 'slow', should be excluded
        assert ("tc001", "sc02") not in ids
        assert ("tc002", "sc04") not in ids
        # sc01 and sc03 remain
        assert ("tc001", "sc01") in ids
        assert ("tc002", "sc03") in ids


class TestCompileFromSelectorPriority:
    """--priority: filter case_priority first, then apply scenario selectors."""

    def test_priority_filters_case_level(self):
        result = compile_from_selector(_metadata(), filter_priority="P0")
        ids = [(e["case_id"], e["scenario_id"]) for e in result["selected"]]
        # Only tc001 scenarios (P0)
        assert ids == [("tc001", "sc01"), ("tc001", "sc02")]

    def test_priority_combined_with_tag(self):
        result = compile_from_selector(
            _metadata(), filter_priority="P1", filter_tags=["regression"]
        )
        ids = [(e["case_id"], e["scenario_id"]) for e in result["selected"]]
        assert ids == [("tc002", "sc03"), ("tc002", "sc04")]

    def test_priority_combined_with_exclude(self):
        result = compile_from_selector(
            _metadata(), filter_priority="P1", exclude_tags=["slow"]
        )
        ids = [(e["case_id"], e["scenario_id"]) for e in result["selected"]]
        # P1 = tc002, exclude slow removes sc04
        assert ids == [("tc002", "sc03")]


class TestCheckPlanSelectorConflict:
    """check_plan_selector_conflict: mutual exclusion between plan and selectors."""

    def test_plan_with_filter_tags_raises(self):
        with pytest.raises(ValueError, match="不能同时使用"):
            check_plan_selector_conflict(
                "plans/smoke.xml",
                {"filter_tags": ["smoke"], "filter_group": None, "exclude_tags": None, "filter_priority": None},
            )

    def test_plan_with_filter_group_raises(self):
        with pytest.raises(ValueError, match="不能同时使用"):
            check_plan_selector_conflict(
                "plans/smoke.xml",
                {"filter_tags": None, "filter_group": "negative", "exclude_tags": None, "filter_priority": None},
            )

    def test_plan_with_exclude_tags_raises(self):
        with pytest.raises(ValueError, match="不能同时使用"):
            check_plan_selector_conflict(
                "plans/smoke.xml",
                {"filter_tags": None, "filter_group": None, "exclude_tags": ["slow"], "filter_priority": None},
            )

    def test_plan_with_priority_raises(self):
        with pytest.raises(ValueError, match="不能同时使用"):
            check_plan_selector_conflict(
                "plans/smoke.xml",
                {"filter_tags": None, "filter_group": None, "exclude_tags": None, "filter_priority": "P0"},
            )

    def test_no_plan_with_filter_tags_no_error(self):
        # Should not raise
        check_plan_selector_conflict(
            None,
            {"filter_tags": ["smoke"], "filter_group": None, "exclude_tags": None, "filter_priority": None},
        )

    def test_empty_plan_with_filter_tags_no_error(self):
        # Empty string plan_path should not raise
        check_plan_selector_conflict(
            "",
            {"filter_tags": ["smoke"], "filter_group": None, "exclude_tags": None, "filter_priority": None},
        )

    def test_plan_with_no_filters_no_error(self):
        # Plan specified but no selector filters active
        check_plan_selector_conflict(
            "plans/smoke.xml",
            {"filter_tags": None, "filter_group": None, "exclude_tags": None, "filter_priority": None},
        )
