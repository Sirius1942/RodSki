#!/usr/bin/env python3
"""Run and assert the complete RodSki Hooks demo.

This script intentionally exercises both hook surfaces:

1. CLI external ``on_run_start`` hooks and built-in compliance forcing.
2. Python API ``before_keyword`` hooks around real SQLite DB operations.
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parent
REPO_ROOT = MODULE_DIR.parents[2]
RODSKI_DIR = REPO_ROOT / "rodski"
CLI_MAIN = RODSKI_DIR / "cli_main.py"
DB_PATH = MODULE_DIR / "data" / "data.sqlite"

sys.path.insert(0, str(RODSKI_DIR))

from core.keyword_engine import HookDecision  # noqa: E402
from core.ski_executor import SKIExecutor  # noqa: E402


def _run_cli(*args: str, hook_mode: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["RODSKI_DEMO_HOOK_MODE"] = hook_mode
    env["PATH"] = os.pathsep.join(
        [str(Path(sys.executable).parent), env.get("PATH", "")]
    )
    return subprocess.run(
        [sys.executable, str(CLI_MAIN), *args],
        cwd=MODULE_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _combined(result: subprocess.CompletedProcess[str]) -> str:
    return result.stdout + result.stderr


def _assert_cli_hooks() -> dict[str, int]:
    conflict = _run_cli(
        "run",
        "@demo_plan",
        "--tag",
        "smoke",
        "--dry-run",
        hook_mode="allow",
    )
    assert conflict.returncode == 1, _combined(conflict)
    assert "SKI703" in _combined(conflict), _combined(conflict)

    forced = _run_cli(
        "run",
        "@demo_plan",
        "--tag",
        "smoke",
        "--dry-run",
        "--force-compliance",
        "--verbose",
        hook_mode="allow",
    )
    assert forced.returncode == 0, _combined(forced)
    assert "验证通过" in forced.stdout, _combined(forced)
    assert "已跳过合规检查失败项" in _combined(forced), _combined(forced)

    denied = _run_cli(
        "run",
        str(MODULE_DIR / "case"),
        "--dry-run",
        hook_mode="deny",
    )
    assert denied.returncode == 1, _combined(denied)
    assert "demo external policy denied" in _combined(denied), _combined(denied)

    denied_with_force = _run_cli(
        "run",
        str(MODULE_DIR / "case"),
        "--dry-run",
        "--force-compliance",
        hook_mode="deny",
    )
    assert denied_with_force.returncode == 1, _combined(denied_with_force)
    assert "demo external policy denied" in _combined(denied_with_force), _combined(
        denied_with_force
    )

    return {
        "built_in_compliance_denied": conflict.returncode,
        "built_in_compliance_forced": forced.returncode,
        "external_hook_denied": denied.returncode,
        "external_hook_denied_with_force": denied_with_force.returncode,
    }


def _reset_audit_table() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM audit_log")
        conn.commit()


def _audit_count() -> int:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()
    return int(row[0])


def _block_db_writes(keyword: str, params: dict) -> HookDecision:
    if keyword.lower() == "db" and params.get("data") == "Q_WRITE":
        return HookDecision(
            allow=False,
            reason="demo policy blocked DB write row Q_WRITE",
        )
    return HookDecision(allow=True)


def _assert_python_api_hooks() -> dict[str, object]:
    _reset_audit_table()
    executor = SKIExecutor(
        case_path=str(MODULE_DIR / "case"),
        driver=None,
        module_dir=str(MODULE_DIR),
        hooks={"before_keyword": [_block_db_writes]},
    )
    try:
        results = executor.execute_all_cases()
    finally:
        executor.close()

    by_case = {result["case_id"]: result for result in results}
    write_result = by_case["c_db_write"]
    read_result = by_case["c_db_read"]
    count_after = _audit_count()

    assert write_result["status"] == "FAIL", write_result
    assert "SKI701" in write_result.get("error", ""), write_result
    assert read_result["status"] == "PASS", read_result
    assert count_after == 0, f"blocked write unexpectedly changed audit_log: {count_after}"

    return {
        "c_db_write": write_result["status"],
        "c_db_write_error": write_result.get("error", ""),
        "c_db_read": read_result["status"],
        "audit_rows_after_run": count_after,
    }


def main() -> int:
    cli = _assert_cli_hooks()
    python_api = _assert_python_api_hooks()
    print(
        json.dumps(
            {"status": "PASS", "cli": cli, "python_api": python_api},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
