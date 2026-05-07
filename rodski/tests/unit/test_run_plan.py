"""rodski run 测试计划入口解析测试。"""
from pathlib import Path

import pytest

from rodski_cli.run import (
    _is_plan_ref,
    _print_plan_dry_run_selection,
    _resolve_case_path,
    _resolve_default_plan,
    _resolve_plan_path,
)


def test_plan_ref_maps_to_plan_xml(tmp_path: Path):
    plan_path = _resolve_plan_path("@smoke", tmp_path)

    assert _is_plan_ref("@smoke") is True
    assert plan_path == tmp_path / "plan" / "smoke.xml"


def test_default_plan_prefers_project_full(tmp_path: Path):
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    project_full = plan_dir / "project_full.xml"
    other_full = plan_dir / "invoice_full.xml"
    project_full.write_text("<plan />", encoding="utf-8")
    other_full.write_text("<plan />", encoding="utf-8")

    assert _resolve_default_plan(tmp_path) == project_full


def test_default_plan_selects_unique_full_plan(tmp_path: Path):
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    smoke_full = plan_dir / "smoke_full.xml"
    smoke_full.write_text("<plan />", encoding="utf-8")

    assert _resolve_default_plan(tmp_path) == smoke_full


def test_default_plan_errors_on_multiple_full_plans(tmp_path: Path):
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    (plan_dir / "invoice_full.xml").write_text("<plan />", encoding="utf-8")
    (plan_dir / "order_full.xml").write_text("<plan />", encoding="utf-8")

    with pytest.raises(ValueError, match="显式指定 @plan_id"):
        _resolve_default_plan(tmp_path)


def test_old_case_path_is_not_plan_ref(tmp_path: Path):
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    case_file = case_dir / "demo_case.xml"
    case_file.write_text("<cases />", encoding="utf-8")

    assert _is_plan_ref(str(case_file)) is False
    assert _resolve_case_path(case_file) == case_file
    assert _resolve_case_path(case_dir) == case_dir
    assert _resolve_case_path(tmp_path) == case_dir


def test_dry_run_plan_output_includes_selected_skipped_and_stale(capsys):
    plan = {"id": "smoke", "kind": "suite", "default_execute": "否"}
    selection = {
        "selected": [{"type": "step", "case_id": "c001", "scenario_id": "s1", "step_no": 2, "reason": "plan_step"}],
        "skipped": [{"type": "scenario", "case_id": "c001", "scenario_id": "s2", "reason": "plan_scenario_execute_false"}],
        "stale_references": [{"type": "scenario", "case_id": "c001", "scenario_id": "missing", "reason": "not_found"}],
    }

    _print_plan_dry_run_selection(plan, selection)

    out = capsys.readouterr().out
    assert "case c001 scenario s1 step 2" in out
    assert "case c001 scenario s2" in out
    assert "case c001 scenario missing" in out
