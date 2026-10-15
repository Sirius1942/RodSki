#!/usr/bin/env python3
"""Run both real RodSki roaming CLI entry points against a local web target."""
from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import xml.etree.ElementTree as ET
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List


MODULE_DIR = Path(__file__).resolve().parent
REPO_ROOT = MODULE_DIR.parents[2]
CLI_MAIN = REPO_ROOT / "rodski" / "cli_main.py"
GLOBALVALUE_PATH = MODULE_DIR / "data" / "globalvalue.xml"
SIMPLE_ENGINE_PATH = MODULE_DIR / "simple_engine.py"
DATA_PATH = MODULE_DIR / "data" / "data.sqlite"
KNOWLEDGE_DIR = MODULE_DIR / "knowledge"
RESULT_DIR = MODULE_DIR / "result"
STATIC_DIR = MODULE_DIR / "fun" / "static"


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        return


def _create_data_sqlite() -> None:
    DATA_PATH.unlink(missing_ok=True)
    with sqlite3.connect(DATA_PATH) as conn:
        conn.executescript(
            """
            CREATE TABLE rs_datatable (
                table_name TEXT PRIMARY KEY,
                model_name TEXT NOT NULL,
                table_kind TEXT NOT NULL,
                row_mode TEXT NOT NULL,
                remark TEXT DEFAULT '',
                updated_at TEXT DEFAULT ''
            );
            CREATE TABLE rs_datatable_field (
                table_name TEXT NOT NULL,
                field_name TEXT NOT NULL,
                field_order INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (table_name, field_name)
            );
            CREATE TABLE rs_row (
                table_name TEXT NOT NULL,
                data_id TEXT NOT NULL,
                remark TEXT DEFAULT '',
                PRIMARY KEY (table_name, data_id)
            );
            CREATE TABLE rs_field (
                table_name TEXT NOT NULL,
                data_id TEXT NOT NULL,
                field_name TEXT NOT NULL,
                field_value TEXT NOT NULL,
                PRIMARY KEY (table_name, data_id, field_name)
            );
            INSERT INTO rs_datatable VALUES
                ('RoamForm', 'RoamForm', 'data', 'standard', 'Offline roaming rows', '');
            INSERT INTO rs_datatable_field VALUES ('RoamForm', 'username', 0);
            INSERT INTO rs_row VALUES
                ('RoamForm', 'D001', ''), ('RoamForm', 'D002', '');
            INSERT INTO rs_field VALUES
                ('RoamForm', 'D001', 'username', 'base-data-id'),
                ('RoamForm', 'D002', 'username', 'roamed-data-id');
            """
        )


def _set_target_url(url: str) -> bytes:
    original = GLOBALVALUE_PATH.read_bytes()
    tree = ET.parse(GLOBALVALUE_PATH)
    root = tree.getroot()
    for group in root.findall("group"):
        if group.get("name") != "Demo":
            continue
        for variable in group.findall("var"):
            if variable.get("name") == "URL":
                variable.set("value", url)
                tree.write(GLOBALVALUE_PATH, encoding="UTF-8", xml_declaration=True)
                return original
    raise RuntimeError("globalvalue.xml is missing Demo.URL")


def _reset_generated_outputs() -> None:
    shutil.rmtree(KNOWLEDGE_DIR, ignore_errors=True)
    for child in RESULT_DIR.iterdir():
        if child.name == ".gitkeep":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def _json_stdout(stdout: str) -> Dict[str, Any]:
    decoder = json.JSONDecoder()
    for index, character in enumerate(stdout):
        if character != "{":
            continue
        try:
            value, end = decoder.raw_decode(stdout[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and not stdout[index + end:].strip():
            return value
    raise AssertionError(f"CLI stdout did not end with a JSON object:\n{stdout}")


def _map_proves_d002_execution() -> Dict[str, Any]:
    map_path = KNOWLEDGE_DIR / "test_map.json"
    assert map_path.is_file(), f"Test Map was not generated: {map_path}"
    test_map = json.loads(map_path.read_text(encoding="utf-8"))
    matching_edges = [
        edge
        for edge in test_map.get("edges", [])
        if edge.get("action", {}).get("action") == "type"
        and edge.get("action", {}).get("model") == "RoamForm"
        and edge.get("action", {}).get("data") == "D002"
    ]
    assert matching_edges, test_map
    return {
        "path": str(map_path.relative_to(MODULE_DIR)),
        "schema_version": test_map.get("schema_version"),
        "nodes": len(test_map.get("nodes", [])),
        "edges": len(test_map.get("edges", [])),
        "executed_variant": matching_edges[0]["action"],
    }


def _run_and_assert(
    label: str,
    command: List[str],
    triggered_by: str,
    cwd: Path,
) -> Dict[str, Any]:
    shutil.rmtree(KNOWLEDGE_DIR, ignore_errors=True)
    result = subprocess.run(
        [sys.executable, str(CLI_MAIN), *command],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    combined = result.stdout + result.stderr
    assert result.returncode == 0, f"{label} failed:\n{combined}"
    payload = _json_stdout(result.stdout)
    assert payload.get("status") == "success", payload
    assert len(payload.get("steps", [])) == 1, payload
    step = payload["steps"][0]
    assert step.get("case_id") == "RT001", step
    assert step.get("status") == "pass", step
    summary = step.get("roam_summary") or {}
    assert summary.get("triggered_by") == triggered_by, summary
    assert int(summary.get("variants_tried", 0)) > 0, summary
    assert summary.get("findings") == [], summary
    assert summary.get("test_map_delta", {}).get("written") is True, summary
    map_evidence = _map_proves_d002_execution()
    return {
        "command": [sys.executable, str(CLI_MAIN), *command],
        "exit_code": result.returncode,
        "variants_tried": summary["variants_tried"],
        "stopped_reason": summary.get("stopped_reason"),
        "test_map": map_evidence,
    }


def main() -> int:
    if sys.version_info[:2] != (3, 12):
        print(
            f"warning: acceptance is specified for Python 3.12; running {sys.version.split()[0]}",
            file=sys.stderr,
        )

    _reset_generated_outputs()
    _create_data_sqlite()
    handler = partial(_QuietHandler, directory=str(STATIC_DIR))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    port = server.server_address[1]
    original_globalvalue = _set_target_url(f"http://127.0.0.1:{port}/index.html")

    try:
        with tempfile.TemporaryDirectory(prefix="rodski-roaming-demo-") as temp_dir:
            temp_cwd = Path(temp_dir)
            (temp_cwd / "config").mkdir()
            (temp_cwd / "config" / "config.json").write_text(
                json.dumps({"recording": {"enabled": False}}),
                encoding="utf-8",
            )
            module_arg = str(MODULE_DIR)
            batch = _run_and_assert(
                "rodski run --roam",
                [
                    "run",
                    module_arg,
                    "--roam",
                    "--roam-engine",
                    str(SIMPLE_ENGINE_PATH),
                    "--headless",
                    "--output-format",
                    "json",
                ],
                "batch_just_passed",
                temp_cwd,
            )
            focused = _run_and_assert(
                "rodski roam --case",
                [
                    "roam",
                    "--case",
                    "RT001",
                    module_arg,
                    "--roam-engine",
                    str(SIMPLE_ENGINE_PATH),
                    "--headless",
                    "--output-format",
                    "json",
                ],
                "single_case",
                temp_cwd,
            )

        print(
            json.dumps(
                {
                    "status": "PASS",
                    "python": sys.version.split()[0],
                    "target": f"http://127.0.0.1:{port}/index.html",
                    "batch_run": batch,
                    "single_case_roam": focused,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5)
        GLOBALVALUE_PATH.write_bytes(original_globalvalue)
        DATA_PATH.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
