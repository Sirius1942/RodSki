"""v11.8.1 回归：--start-from 接线、--group 选中 scenario、loop 变量解析

三处缺陷都只在完整 CLI 链路上暴露（run.py → SKIExecutor → 选择/循环），
因此以子进程执行真实的 rodski run，按 execution_summary.json 判定。
"""
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent


def _make_module(tmp_path: Path, case_xml: str) -> Path:
    module = tmp_path / "product" / "proj" / "mod"
    for name in ("case", "model", "data", "fun", "result"):
        (module / name).mkdir(parents=True)
    (module / "model" / "model.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?><models/>', encoding="utf-8")
    (module / "data" / "globalvalue.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?><globalvalue>'
        '<group name="DefaultValue"><var name="WaitTime" value="0"/></group></globalvalue>',
        encoding="utf-8")
    case_file = module / "case" / "c.xml"
    case_file.write_text(case_xml, encoding="utf-8")
    return case_file


def _run(case_file: Path, *args: str):
    proc = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "cli_main.py"), "run", str(case_file), *args],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT), timeout=120,
    )
    summaries = sorted((case_file.parents[1] / "result").rglob("execution_summary.json"))
    summary = json.loads(summaries[-1].read_text(encoding="utf-8")) if summaries else {}
    return proc, summary


def _case(body: str) -> str:
    return ('<?xml version="1.0" encoding="UTF-8"?><cases>'
            '<case execute="是" id="C1" title="t"><test_case>' + body +
            '</test_case></case></cases>')


def test_start_from_skips_earlier_steps(tmp_path):
    case_file = _make_module(tmp_path, _case(
        '<test_step action="set" model="" data="a=1"/>'
        '<test_step action="set" model="" data="b=2"/>'
        '<test_step action="set" model="" data="c=3"/>'))
    proc, summary = _run(case_file, "--start-from", "2")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    statuses = [s["status"] for s in summary["steps"]]
    assert statuses == ["skipped", "ok", "ok"]
    assert "a" not in summary["context_snapshot"]["named"]


def test_group_selects_only_matching_scenario(tmp_path):
    case_file = _make_module(tmp_path, _case(
        '<scenario id="S1" group="g1"><test_step action="set" model="" data="s1=1"/></scenario>'
        '<scenario id="S2" group="g2"><test_step action="set" model="" data="s2=1"/></scenario>'))
    proc, summary = _run(case_file, "--group", "g2")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "1/1 通过" in proc.stdout
    named = summary["context_snapshot"]["named"]
    assert "s2" in named and "s1" not in named


def test_loop_variable_resolved_in_data(tmp_path):
    case_file = _make_module(tmp_path, _case(
        '<loop range="1-3" var="i"><test_step action="set" model="" data="row_${i}=v${i}"/></loop>'))
    proc, summary = _run(case_file)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    named = summary["context_snapshot"]["named"]
    assert {k: named.get(k) for k in ("row_1", "row_2", "row_3")} == {
        "row_1": "v1", "row_2": "v2", "row_3": "v3"}
