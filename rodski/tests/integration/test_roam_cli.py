"""CLI integration tests for the two roaming entry points."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from rodski_cli import roam


PROJECT_ROOT = Path(__file__).parent.parent.parent


def run_cli(*args, cwd=None):
    return subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "cli_main.py"), *args],
        capture_output=True,
        text=True,
        cwd=str(cwd or PROJECT_ROOT),
    )


def _json_stdout(stdout):
    start = stdout.find("{")
    assert start >= 0, stdout
    return json.JSONDecoder().raw_decode(stdout[start:])[0]


def _make_roam_module(base: Path, *, roaming_enabled: bool = True) -> Path:
    for directory in ("case", "model", "fun", "data", "plan", "result"):
        (base / directory).mkdir(parents=True, exist_ok=True)

    (base / "model" / "model.xml").write_text(
        '<?xml version="1.0"?><models></models>', encoding="utf-8"
    )
    enabled = "是" if roaming_enabled else "否"
    (base / "data" / "globalvalue.xml").write_text(
        f"""<?xml version="1.0"?>
<globalvalue>
  <group name="DefaultValue">
    <var name="WaitTime" value="0"/>
  </group>
  <group name="Roam">
    <var name="Enabled" value="{enabled}"/>
    <var name="MaxVariantsPerCase" value="1"/>
    <var name="MaxDurationSeconds" value="5"/>
    <var name="MinConfidenceToAct" value="0.6"/>
    <var name="MaxTokenBudget" value="20000"/>
    <var name="MaxCostUsd" value="0.5"/>
  </group>
</globalvalue>
""",
        encoding="utf-8",
    )
    (base / "case" / "roam.xml").write_text(
        """<?xml version="1.0"?>
<cases>
  <case execute="是" id="c_roam" title="可漫游" component_type="界面" roam="是">
    <test_case><test_step action="wait" data="0"/></test_case>
  </case>
  <case execute="是" id="c_skip" title="未声明漫游" component_type="界面">
    <test_case><test_step action="wait" data="0"/></test_case>
  </case>
</cases>
""",
        encoding="utf-8",
    )
    return base


def test_roam_command_registered_in_root_help():
    result = run_cli("--help")
    assert result.returncode == 0
    assert "roam" in result.stdout


def test_roam_command_requires_case_id():
    result = run_cli("roam", ".")
    assert result.returncode == 2
    assert "--case" in result.stderr


def test_roam_handle_delegates_single_case_intent_to_run(tmp_path):
    args = argparse.Namespace(
        path=str(tmp_path),
        roam_case_id="c001",
        model=None,
        browser="chromium",
        headless=True,
        verbose=False,
        output=None,
        output_format="json",
        report=None,
        trace=False,
        platform=None,
        force_compliance=False,
    )

    with patch("rodski_cli.roam.run.handle", return_value=0) as run_handle:
        assert roam.handle(args) == 0

    delegated = run_handle.call_args.args[0]
    assert delegated.case == str(tmp_path)
    assert delegated.roam is True
    assert delegated.roam_mode == "single_case"
    assert delegated.roam_case_id == "c001"


def test_roam_handle_defaults_path_to_current_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    args = argparse.Namespace(
        path=None,
        roam_case_id="c001",
        model=None,
        browser="chromium",
        output=None,
    )

    with patch("rodski_cli.roam.run.handle", return_value=0) as run_handle:
        assert roam.handle(args) == 0

    assert run_handle.call_args.args[0].case == str(tmp_path)


def test_roam_single_case_executes_only_requested_case(tmp_path):
    module = _make_roam_module(tmp_path)

    result = run_cli(
        "roam",
        "--case",
        "c_roam",
        str(module),
        "--output-format",
        "json",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    output = _json_stdout(result.stdout)
    assert [step["case_id"] for step in output["steps"]] == ["c_roam"]
    summary = output["steps"][0]["roam_summary"]
    assert summary["base_case_id"] == "c_roam"
    assert summary["triggered_by"] == "single_case"


def test_roam_single_case_reports_missing_case_id(tmp_path):
    module = _make_roam_module(tmp_path)

    result = run_cli("roam", "--case", "missing", str(module))

    assert result.returncode == 1
    assert "SKI801" in result.stdout + result.stderr


def test_roam_single_case_rejects_disabled_global_switch(tmp_path):
    module = _make_roam_module(tmp_path, roaming_enabled=False)

    result = run_cli("roam", "--case", "c_roam", str(module))

    assert result.returncode == 1
    assert "SKI802" in result.stdout + result.stderr


def test_run_roam_executes_selected_cases_and_skips_ineligible_roaming(tmp_path):
    module = _make_roam_module(tmp_path)

    result = run_cli("run", str(module), "--roam", "--output-format", "json")

    assert result.returncode == 0, result.stdout + result.stderr
    output = _json_stdout(result.stdout)
    steps = {step["case_id"]: step for step in output["steps"]}
    assert set(steps) == {"c_roam", "c_skip"}
    assert steps["c_roam"]["roam_summary"]["triggered_by"] == "batch_just_passed"
    assert "roam_summary" not in steps["c_skip"]
