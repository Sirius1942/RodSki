"""CLI wiring tests for the business-model debug command."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _run_module(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-m", "rodski.rodski_cli", *args],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_python_module_entry_registers_business_command():
    result = _run_module("--help")

    assert result.returncode == 0
    assert "business" in result.stdout
    assert result.stderr == ""


def test_python_module_entry_exposes_business_debug_arguments():
    result = _run_module("business", "debug", "--help")

    assert result.returncode == 0
    assert "--flow" in result.stdout
    assert "--input" in result.stdout
    assert "--expect" in result.stdout
    assert "--id" in result.stdout
    assert result.stderr == ""
