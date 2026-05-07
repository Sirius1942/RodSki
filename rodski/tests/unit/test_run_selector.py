"""rodski run selector CLI 参数解析测试。"""
import argparse
from unittest.mock import patch, MagicMock

import pytest

from rodski_cli.run import (
    _build_selector_filters,
    _has_active_selector,
    _is_plan_ref,
    _print_selector_dry_run_selection,
    setup_parser,
)
from core.test_plan_selection import check_plan_selector_conflict


def _parse_run_args(argv):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    setup_parser(subparsers)
    return parser.parse_args(["run", "case"] + argv)


def test_tag_and_tags_parse_equivalent():
    tag_args = _parse_run_args(["--tag", "smoke,login"])
    tags_args = _parse_run_args(["--tags", "smoke,login"])

    assert _build_selector_filters(tag_args)["filter_tags"] == ["smoke", "login"]
    assert _build_selector_filters(tags_args)["filter_tags"] == ["smoke", "login"]


def test_tag_and_tags_merge_to_filter_tags():
    args = _parse_run_args(["--tag", "smoke", "--tags", "login,regression"])

    assert _build_selector_filters(args)["filter_tags"] == ["smoke", "login", "regression"]


def test_exclude_tag_and_exclude_tags_parse_equivalent():
    exclude_tag_args = _parse_run_args(["--exclude-tag", "slow,flaky"])
    exclude_tags_args = _parse_run_args(["--exclude-tags", "slow,flaky"])

    assert _build_selector_filters(exclude_tag_args)["exclude_tags"] == ["slow", "flaky"]
    assert _build_selector_filters(exclude_tags_args)["exclude_tags"] == ["slow", "flaky"]


def test_group_parse_to_filter_group():
    args = _parse_run_args(["--group", "auth"])

    assert _build_selector_filters(args)["filter_group"] == "auth"


# =====================================================================
# _is_plan_ref
# =====================================================================
class TestIsPlanRef:
    def test_at_prefix_is_plan_ref(self):
        assert _is_plan_ref("@smoke") is True

    def test_plain_path_is_not_plan_ref(self):
        assert _is_plan_ref("case/tc001.xml") is False

    def test_none_is_not_plan_ref(self):
        assert _is_plan_ref(None) is False

    def test_empty_at_is_not_plan_ref(self):
        assert _is_plan_ref("@") is False


# =====================================================================
# _has_active_selector
# =====================================================================
class TestHasActiveSelector:
    def test_empty_filters(self):
        assert _has_active_selector({"filter_tags": None, "filter_group": None, "exclude_tags": None, "filter_priority": None}) is False

    def test_filter_tags_active(self):
        assert _has_active_selector({"filter_tags": ["smoke"], "filter_group": None, "exclude_tags": None, "filter_priority": None}) is True

    def test_filter_group_active(self):
        assert _has_active_selector({"filter_tags": None, "filter_group": "auth", "exclude_tags": None, "filter_priority": None}) is True


# =====================================================================
# Mutual exclusion: plan + selector conflict
# =====================================================================
class TestPlanSelectorConflictInHandle:
    """check_plan_selector_conflict returns non-zero when plan + selector both specified."""

    def test_plan_with_tag_raises(self):
        with pytest.raises(ValueError, match="不能同时使用"):
            check_plan_selector_conflict(
                "plans/smoke.xml",
                {"filter_tags": ["smoke"], "filter_group": None, "exclude_tags": None, "filter_priority": None},
            )

    def test_no_plan_no_error(self):
        # Should not raise
        check_plan_selector_conflict(
            None,
            {"filter_tags": ["smoke"], "filter_group": None, "exclude_tags": None, "filter_priority": None},
        )


# =====================================================================
# Selector dry-run output
# =====================================================================
class TestSelectorDryRunOutput:
    def test_prints_selected_scenarios(self, capsys):
        selection = {
            "selected": [
                {"type": "scenario", "case_id": "tc001", "scenario_id": "sc01", "reason": "selector"},
                {"type": "scenario", "case_id": "tc001", "scenario_id": "sc02", "reason": "selector"},
            ],
            "skipped": [],
            "stale_references": [],
        }
        _print_selector_dry_run_selection(selection)
        captured = capsys.readouterr()
        assert "Selector" in captured.out
        assert "tc001" in captured.out
        assert "sc01" in captured.out
        assert "sc02" in captured.out
        # No stale section in selector dry-run
        assert "Stale" not in captured.out

    def test_prints_none_when_empty(self, capsys):
        selection = {"selected": [], "skipped": [], "stale_references": []}
        _print_selector_dry_run_selection(selection)
        captured = capsys.readouterr()
        assert "(none)" in captured.out
