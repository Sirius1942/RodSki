#!/usr/bin/env python3
"""F109 漫游正向 / F110 漫游资格负向（SKI801 / SKI802 / SKI803）补充验收。

用法（仓库根目录）:
    python3 rodski-demo/local/roaming/run_acceptance_extra.py          # 全部 M01~M08
    python3 rodski-demo/local/roaming/run_acceptance_extra.py M04 M05  # 指定编号

文档依据:
    CORE_DESIGN_CONSTRAINTS.md §7.2（case.roam 行：非界面用例声明 roam 抛 SKI803）、§8.9（三层开关、
    SKI801 找不到 / SKI802 不满足条件、批量 --roam 静默跳过、决策引擎由 Hook 或 --roam-engine 注入，
    无 Handler 时 stopped_reason="no_handler"）
    TEST_CASE_WRITING_GUIDE.md §11.6（核心默认引擎纯规则零 LLM；`rodski roam --case-file + --case-id`）
    HOOKS_REFERENCE.md §2 on_case_pass_roam_ready

隔离方式：每个检查项把本模块复制到临时目录（不含 result/ knowledge/），在临时模块里生成 data.sqlite、
把 Demo.URL 指向本脚本在 127.0.0.1:18132 启动的 fun/static 站点，并按需放入 fun/roam_cases/ 下的
补充用例或改写 globalvalue。全程不修改本模块已有文件（run_demo.py 会改写 globalvalue / 生成 data.sqlite，
两者可并行运行互不干扰）。

输出与退出码约定：每项一行 `PASS|FAIL|KNOWN <编号> <说明>`，最后 `汇总: PASS=x FAIL=y KNOWN=z`；
全部 PASS 退出 0，否则 1。
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

MODULE_DIR = Path(__file__).resolve().parent
REPO = MODULE_DIR.parents[2]
CLI = REPO / "rodski" / "cli_main.py"
PY = os.environ.get("RODSKI_PY") or sys.executable
ENGINE = MODULE_DIR / "simple_engine.py"
EXTRA = MODULE_DIR / "fun" / "roam_cases" / "negative"
SITE_PORT = 18132
URL = f"http://127.0.0.1:{SITE_PORT}/index.html"

sys.path.insert(0, str(REPO / "rodski"))
from core.sqlite_schema import SQLITE_DDL  # noqa: E402

KNOWN = {
    "M01:default_engine": "文档冲突：GUIDE §11.6（TEST_CASE_WRITING_GUIDE.md:2254）与 ARCHITECTURE.md:612 称"
                          "「核心默认引擎是纯规则、零 LLM 实现」，不传 --roam-engine 也会做数据变体探索；"
                          "CORE §8.9（CORE_DESIGN_CONSTRAINTS.md:1579）与 HOOKS_REFERENCE.md:95 规定核心不含引擎、"
                          "无 Handler 时 stopped_reason=no_handler。实现符合 CORE，GUIDE/ARCHITECTURE 未同步",
}

Outcome = List[Tuple[str, bool, str]]


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args: Any) -> None:
        return


def start_site() -> ThreadingHTTPServer:
    ThreadingHTTPServer.allow_reuse_address = True
    srv = ThreadingHTTPServer(("127.0.0.1", SITE_PORT), partial(_Quiet, directory=str(MODULE_DIR / "fun" / "static")))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def _write_data(db: Path) -> None:
    """与 run_demo.py 相同的 RoamForm 数据：基础行 D001，漫游候选 D002（字段集合一致）。"""
    db.unlink(missing_ok=True)
    with sqlite3.connect(db) as conn:
        conn.executescript(SQLITE_DDL)
        conn.execute("INSERT INTO rs_datatable (table_name, model_name, table_kind, row_mode, remark) "
                     "VALUES ('RoamForm','RoamForm','data','standard','Offline roaming rows')")
        conn.execute("INSERT INTO rs_datatable_field VALUES ('RoamForm','username',0)")
        for data_id, value in (("D001", "base-data-id"), ("D002", "roamed-data-id")):
            conn.execute("INSERT INTO rs_row VALUES ('RoamForm',?,'')", (data_id,))
            conn.execute("INSERT INTO rs_field VALUES ('RoamForm',?,'username',?)", (data_id, value))


class TempModule:
    """临时模块 + 临时 cwd（config/config.json 关闭录像，同 run_demo.py）。"""

    def __init__(self, extra_cases: Tuple[str, ...] = (), roam_enabled: str = "是"):
        self.tmp = Path(tempfile.mkdtemp(prefix="rodski-roam-extra-"))
        self.mod = self.tmp / "roaming"
        shutil.copytree(MODULE_DIR, self.mod, ignore=shutil.ignore_patterns(
            "result", "knowledge", "__pycache__", "data.sqlite", "run_*.py", "test_*.py"))
        (self.mod / "result").mkdir()
        _write_data(self.mod / "data" / "data.sqlite")
        gv = self.mod / "data" / "globalvalue.xml"
        text = gv.read_text(encoding="utf-8").replace("http://127.0.0.1:0/index.html", URL)
        text = text.replace('<var name="Enabled" value="是"/>', f'<var name="Enabled" value="{roam_enabled}"/>')
        gv.write_text(text, encoding="utf-8")
        if extra_cases:
            (self.mod / "case" / "negative").mkdir(parents=True, exist_ok=True)
            for name in extra_cases:
                shutil.copy2(EXTRA / name, self.mod / "case" / "negative" / name)
        self.cwd = self.tmp / "cwd"
        (self.cwd / "config").mkdir(parents=True)
        (self.cwd / "config" / "config.json").write_text(json.dumps({"recording": {"enabled": False}}),
                                                        encoding="utf-8")

    def cli(self, *args: str) -> Tuple[int, str, str]:
        p = subprocess.run([PY, str(CLI), *args], cwd=str(self.cwd), capture_output=True, text=True, timeout=600)
        return p.returncode, p.stdout, p.stdout + p.stderr

    def test_map(self) -> Dict[str, Any]:
        p = self.mod / "knowledge" / "test_map.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}

    def __enter__(self) -> "TempModule":
        return self

    def __exit__(self, *exc: Any) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)


def _json_tail(stdout: str) -> Dict[str, Any]:
    dec = json.JSONDecoder()
    for i, ch in enumerate(stdout):
        if ch != "{":
            continue
        try:
            val, end = dec.raw_decode(stdout[i:])
        except json.JSONDecodeError:
            continue
        if isinstance(val, dict) and not stdout[i + end:].strip():
            return val
    return {}


def _steps(payload: Dict[str, Any]) -> Dict[str, dict]:
    return {s.get("case_id"): s for s in payload.get("steps", [])}


def _first_line(text: str, key: str) -> str:
    return next((ln.strip() for ln in text.splitlines() if key in ln), "(无)")[:200]


# ---------------------------------------------------------------- 检查项
def m01() -> Outcome:
    """F109 不传 --roam-engine：rodski roam --case-file + --case-id 基础用例通过、产出 roam_summary。"""
    with TempModule() as t:
        code, out, _ = t.cli("roam", "--case-file", "roaming_case.xml", "--case-id", "RT001", str(t.mod),
                             "--headless", "--output-format", "json")
        step = _steps(_json_tail(out)).get("RT001", {})
        summ = step.get("roam_summary") or {}
        return [
            ("M01:base", code == 0 and step.get("status") == "pass" and bool(summ),
             f"退出码 {code}，RT001 status={step.get('status')}，roam_summary 存在={bool(summ)}"),
            ("M01:default_engine", int(summ.get("variants_tried", 0) or 0) > 0,
             f"核心默认规则引擎执行了数据变体（variants_tried={summ.get('variants_tried')}，"
             f"stopped_reason={summ.get('stopped_reason')}）"),
        ]


def m02() -> Outcome:
    """F109 rodski roam --case-file + --case-id（v11.5 推荐写法）+ --roam-engine：定向漫游执行 D002 变体。"""
    with TempModule() as t:
        code, out, _ = t.cli("roam", "--case-file", "roaming_case.xml", "--case-id", "RT001", str(t.mod),
                             "--roam-engine", str(ENGINE), "--headless", "--output-format", "json")
        step = _steps(_json_tail(out)).get("RT001", {})
        summ = step.get("roam_summary") or {}
        edges = [e for e in t.test_map().get("edges", []) if e.get("action", {}).get("data") == "D002"]
        return [
            ("M02:exit", code == 0 and step.get("status") == "pass", f"退出码 {code}，RT001 status={step.get('status')}"),
            ("M02:summary", summ.get("triggered_by") == "single_case" and int(summ.get("variants_tried", 0) or 0) > 0,
             f"triggered_by={summ.get('triggered_by')}，variants_tried={summ.get('variants_tried')}"),
            ("M02:test_map", bool(edges), f"knowledge/test_map.json 含 data=D002 的边（{len(edges)} 条）"),
        ]


def m03() -> Outcome:
    """F110 SKI801：定向漫游的用例不存在。"""
    with TempModule() as t:
        code, _, allout = t.cli("roam", "--case-file", "roaming_case.xml", "--case-id", "NOPE", str(t.mod),
                                "--roam-engine", str(ENGINE), "--headless")
        return [("M03:ski801", code != 0 and "SKI801" in allout,
                 f"退出码 {code}，输出含 SKI801：{_first_line(allout, 'SKI80')}")]


def m04() -> Outcome:
    """F110 SKI802：globalvalue Roam.Enabled=否 时定向漫游。"""
    with TempModule(roam_enabled="否") as t:
        code, _, allout = t.cli("roam", "--case-file", "roaming_case.xml", "--case-id", "RT001", str(t.mod),
                                "--roam-engine", str(ENGINE), "--headless")
        return [("M04:ski802", code != 0 and "SKI802" in allout,
                 f"退出码 {code}，输出含 SKI802：{_first_line(allout, 'SKI80')}")]


def m05() -> Outcome:
    """F110 SKI802：用例未声明 roam="是" 时定向漫游。"""
    with TempModule(extra_cases=("no_roam.xml",)) as t:
        code, _, allout = t.cli("roam", "--case-file", "negative/no_roam.xml", "--case-id", "RT_NOROAM", str(t.mod),
                                "--roam-engine", str(ENGINE), "--headless")
        return [("M05:ski802", code != 0 and "SKI802" in allout,
                 f"退出码 {code}，输出含 SKI802：{_first_line(allout, 'SKI80')}")]


def m06() -> Outcome:
    """F110 SKI803：接口用例声明 roam="是"（rodski run 与 rodski roam 两个入口）。"""
    with TempModule(extra_cases=("api_roam.xml",)) as t:
        code1, _, out1 = t.cli("run", str(t.mod / "case" / "negative" / "api_roam.xml"), "--headless")
        code2, _, out2 = t.cli("roam", "--case-file", "negative/api_roam.xml", "--case-id", "RT_API", str(t.mod),
                               "--roam-engine", str(ENGINE), "--headless")
        return [
            ("M06:run", code1 != 0 and "SKI803" in out1, f"rodski run 退出码 {code1}，含 SKI803：{_first_line(out1, 'SKI80')}"),
            ("M06:roam", code2 != 0 and "SKI803" in out2, f"rodski roam 退出码 {code2}，含 SKI803：{_first_line(out2, 'SKI80')}"),
        ]


def m07() -> Outcome:
    """F110 批量 rodski run --roam：未声明 roam 的用例静默跳过漫游，基础用例照常执行。"""
    with TempModule(extra_cases=("no_roam.xml",)) as t:
        code, out, _ = t.cli("run", str(t.mod), "--roam", "--roam-engine", str(ENGINE), "--headless",
                             "--output-format", "json")
        steps = _steps(_json_tail(out))
        rt, nr = steps.get("RT001", {}), steps.get("RT_NOROAM", {})
        return [
            ("M07:exit", code == 0, f"退出码 {code}"),
            ("M07:roamed", rt.get("status") == "pass" and int((rt.get("roam_summary") or {}).get("variants_tried", 0) or 0) > 0,
             f"RT001 status={rt.get('status')} 漫游 variants_tried={(rt.get('roam_summary') or {}).get('variants_tried')}"),
            ("M07:skipped", nr.get("status") == "pass" and not nr.get("roam_summary"),
             f"RT_NOROAM status={nr.get('status')}，无 roam_summary={not nr.get('roam_summary')}"),
        ]


def m08() -> Outcome:
    """F110 批量 rodski run --roam 且 Roam.Enabled=否：静默跳过全部漫游，不报 SKI802。"""
    with TempModule(roam_enabled="否") as t:
        code, out, allout = t.cli("run", str(t.mod), "--roam", "--roam-engine", str(ENGINE), "--headless",
                                  "--output-format", "json")
        rt = _steps(_json_tail(out)).get("RT001", {})
        return [("M08:skip", code == 0 and rt.get("status") == "pass" and not rt.get("roam_summary")
                 and "SKI802" not in allout,
                 f"退出码 {code}，RT001 status={rt.get('status')}，无 roam_summary={not rt.get('roam_summary')}，"
                 f"未报 SKI802={'SKI802' not in allout}")]


CHECKS: Dict[str, Callable[[], Outcome]] = {
    "M01": m01, "M02": m02, "M03": m03, "M04": m04, "M05": m05, "M06": m06, "M07": m07, "M08": m08,
}


def main(argv: List[str]) -> int:
    selected = [a.upper() for a in argv] or list(CHECKS)
    srv: Optional[ThreadingHTTPServer] = start_site()
    counts = {"PASS": 0, "FAIL": 0, "KNOWN": 0}
    try:
        for key in selected:
            print(f"== {key} {CHECKS[key].__doc__.strip().splitlines()[0]}")
            try:
                items = CHECKS[key]()
            except Exception as e:  # noqa: BLE001
                items = [(key, False, f"执行异常: {type(e).__name__}: {e}")]
            for sub, ok, msg in items:
                status = "PASS" if ok else ("KNOWN" if sub in KNOWN else "FAIL")
                counts[status] += 1
                extra = f"  [已登记: {KNOWN[sub]}]" if status == "KNOWN" else ""
                print(f"{status}\t{sub}\t{msg}{extra}")
    finally:
        if srv:
            srv.shutdown()
            srv.server_close()
    print(f"汇总: PASS={counts['PASS']} FAIL={counts['FAIL']} KNOWN={counts['KNOWN']}")
    return 0 if counts["FAIL"] == 0 and counts["KNOWN"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
