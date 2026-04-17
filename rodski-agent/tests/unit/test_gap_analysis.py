"""Unit tests for gap_analysis node."""

import os
import textwrap
from pathlib import Path

import pytest

from rodski_agent.design.nodes import gap_analysis


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")


def _make_model_xml(model_names: list) -> str:
    models = "\n".join(f'  <model name="{n}" type="ui" servicename=""/>' for n in model_names)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<models>\n{models}\n</models>\n'


def _make_data_xml(table_names: list) -> str:
    tables = "\n".join(f'  <datatable name="{n}"/>' for n in table_names)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<datatables>\n{tables}\n</datatables>\n'


def _plan(steps: list) -> list:
    """Build a minimal case_plan from a list of step dicts."""
    return [{"id": "C001", "steps": steps}]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_output_dir_not_exist_all_missing(tmp_path):
    """output_dir doesn't exist => all referenced assets are missing."""
    state = {
        "output_dir": str(tmp_path / "nonexistent"),
        "case_plan": _plan([
            {"model": "Login", "data": "LoginData.R001"},
            {"model": "Home", "data": "HomeData.R001"},
        ]),
    }
    result = gap_analysis(state)
    report = result["gap_report"]

    assert sorted(report["missing_models"]) == ["Home", "Login"]
    assert sorted(report["missing_data"]) == ["HomeData", "LoginData"]
    assert report["reusable_models"] == []
    assert report["reusable_data"] == []


def test_partial_model_reuse(tmp_path):
    """model.xml has some models => correct reusable vs missing split."""
    _write(tmp_path / "model" / "model.xml", _make_model_xml(["Login", "Nav"]))

    state = {
        "output_dir": str(tmp_path),
        "case_plan": _plan([
            {"model": "Login", "data": ""},
            {"model": "Home", "data": ""},
        ]),
    }
    result = gap_analysis(state)
    report = result["gap_report"]

    assert report["missing_models"] == ["Home"]
    assert report["reusable_models"] == ["Login"]


def test_partial_data_reuse(tmp_path):
    """data/ has some tables => correct reusable vs missing split."""
    _write(tmp_path / "data" / "data.xml", _make_data_xml(["LoginData", "FormData"]))

    state = {
        "output_dir": str(tmp_path),
        "case_plan": _plan([
            {"model": "", "data": "LoginData.R001"},
            {"model": "", "data": "OrderData.R001"},
        ]),
    }
    result = gap_analysis(state)
    report = result["gap_report"]

    assert report["missing_data"] == ["OrderData"]
    assert "LoginData" in report["reusable_data"]
    assert "FormData" in report["reusable_data"]


def test_empty_case_plan(tmp_path):
    """Empty case_plan => all gap fields are empty lists."""
    state = {
        "output_dir": str(tmp_path),
        "case_plan": [],
    }
    result = gap_analysis(state)
    report = result["gap_report"]

    assert report["missing_models"] == []
    assert report["missing_data"] == []
    assert report["reusable_models"] == []
    assert report["reusable_data"] == []
