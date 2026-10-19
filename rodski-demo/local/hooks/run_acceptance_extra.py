#!/usr/bin/env python3
"""F112 Hook 其他事件验收：on_session_start / after_keyword / on_case_failure / on_run_end。

用法（仓库根目录）:
    python3 rodski-demo/local/hooks/run_acceptance_extra.py          # 全部 H01~H04
    python3 rodski-demo/local/hooks/run_acceptance_extra.py H04      # 指定编号

文档依据: rodski/docs/HOOKS_REFERENCE.md §1（事件清单与触发点）、§2（进程内回调签名、HookResult）、
§3（hooks.json 格式、stdin JSON / exit code 协议）。

- 外部命令 hook（H01~H03）：本模块自带的 hooks.json 只配置了 on_run_start（run_demo.py 依赖其语义，不改）。
  因此把模块复制到临时目录，写入配置 on_session_start / on_run_start / on_case_failure / on_run_end 的
  hooks.json，四个事件都调用 fun/hooks/record_event.py，把事件名与 stdin 上下文写入 JSONL 后断言。
- 进程内回调（H04）：同样在临时模块上对 case/hook_events.xml 用 SKIExecutor(hooks=...) 注册
  after_keyword / on_case_failure。只执行只读行 Q_READ 与不存在的行，不写 audit_log。
- 用例源文件是 fun/hooks/hook_events.xml（不放进本模块 case/：plan/demo_plan.xml 未写 file 属性，
  case/ 出现第二个用例文件会让 run_demo.py 的 @demo_plan 步骤报 SKI207），只复制进临时模块的 case/。
- 全程不修改本模块任何已有文件，也不写被 git 跟踪的 data/data.sqlite。

输出与退出码约定：每项一行 `PASS|FAIL|KNOWN <编号> <说明>`，最后 `汇总: PASS=x FAIL=y KNOWN=z`；
全部 PASS 退出 0，否则 1。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

MODULE_DIR = Path(__file__).resolve().parent
REPO = MODULE_DIR.parents[2]
RODSKI_DIR = REPO / "rodski"
CLI = RODSKI_DIR / "cli_main.py"
PY = os.environ.get("RODSKI_PY") or sys.executable
CASE_FILE = "case/hook_events.xml"
EVENTS = ("on_session_start", "on_run_start", "on_case_failure", "on_run_end")

KNOWN: Dict[str, str] = {}

Outcome = List[Tuple[str, bool, str]]


def _temp_module(tmp: Path) -> Path:
    mod = tmp / "hooks"
    shutil.copytree(MODULE_DIR, mod, ignore=shutil.ignore_patterns("result", "__pycache__", "hooks.json"))
    (mod / "result").mkdir()
    # 用例源文件放在 fun/hooks/（原因见该文件头注释），只在临时模块中放入 case/
    shutil.copy2(MODULE_DIR / "fun" / "hooks" / "hook_events.xml", mod / CASE_FILE)
    py = shutil.which("python3") or sys.executable
    cfg = {ev: [{"command": [py, "fun/hooks/record_event.py", ev], "timeout": 10}] for ev in EVENTS}
    (mod / "hooks.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return mod


def _run_cli(mod: Path, log: Path, *extra: str, env_extra: Optional[Dict[str, str]] = None):
    env = os.environ.copy()
    env["RODSKI_DEMO_HOOK_LOG"] = str(log)
    env.update(env_extra or {})
    proc = subprocess.run([PY, str(CLI), "run", CASE_FILE, *extra], cwd=str(mod), env=env,
                          capture_output=True, text=True, timeout=300)
    events = []
    if log.is_file():
        events = [json.loads(ln) for ln in log.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return proc.returncode, proc.stdout + proc.stderr, events


def h01() -> Outcome:
    """外部 hook：一次含失败用例的 run 中四个事件按序各触发一次，上下文字段正确。"""
    tmp = Path(tempfile.mkdtemp(prefix="rodski-hooks-"))
    try:
        mod = _temp_module(tmp)
        code, out, events = _run_cli(mod, tmp / "events.jsonl")
        names = [e["event"] for e in events]
        by = {e["event"]: e["context"] for e in events}
        start = by.get("on_session_start", {})
        fail = by.get("on_case_failure", {})
        end = by.get("on_run_end", {})
        return [
            ("H01:exit", code == 1, f"一个用例失败时 CLI 退出码 1（实际 {code}）"),
            ("H01:order", names == list(EVENTS),
             f"事件顺序 on_session_start → on_run_start → on_case_failure → on_run_end，各一次（实际 {names}）"),
            ("H01:session_ctx", start.get("case_path") == CASE_FILE and "module_dir" in start,
             f"on_session_start 上下文含 case_path={start.get('case_path')!r} 与 module_dir"),
            ("H01:failure_ctx", fail.get("case_id") == "HE_FAIL" and "Q_NOT_EXIST" in str(fail.get("error_message", "")),
             f"on_case_failure 只针对 HE_FAIL，error_message 含失败原因（case_id={fail.get('case_id')!r}）"),
            ("H01:failure_once", names.count("on_case_failure") == 1, "通过的 HE_PASS 不触发 on_case_failure"),
            ("H01:run_end_ctx",
             (end.get("total"), end.get("passed"), end.get("failed"), end.get("status")) == (2, 1, 1, "failed"),
             f"on_run_end 汇总 total/passed/failed/status = "
             f"{end.get('total')}/{end.get('passed')}/{end.get('failed')}/{end.get('status')}（期望 2/1/1/failed）"),
        ]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def h02() -> Outcome:
    """外部 hook：全部通过时不触发 on_case_failure，on_run_end status=passed，退出码 0。"""
    tmp = Path(tempfile.mkdtemp(prefix="rodski-hooks-"))
    try:
        mod = _temp_module(tmp)
        code, out, events = _run_cli(mod, tmp / "events.jsonl", "--case-id", "HE_PASS")
        names = [e["event"] for e in events]
        end = next((e["context"] for e in events if e["event"] == "on_run_end"), {})
        return [
            ("H02:exit", code == 0, f"退出码 0（实际 {code}）"),
            ("H02:events", names == ["on_session_start", "on_run_start", "on_run_end"],
             f"只触发 on_session_start / on_run_start / on_run_end（实际 {names}）"),
            ("H02:run_end", (end.get("total"), end.get("failed"), end.get("status")) == (1, 0, "passed"),
             f"on_run_end total/failed/status = {end.get('total')}/{end.get('failed')}/{end.get('status')}（期望 1/0/passed）"),
        ]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def h03() -> Outcome:
    """外部 hook：on_session_start 返回 exit code 2 → deny，CLI 退出 1，后续 on_run_start 与用例都不执行。"""
    tmp = Path(tempfile.mkdtemp(prefix="rodski-hooks-"))
    try:
        mod = _temp_module(tmp)
        code, out, events = _run_cli(mod, tmp / "events.jsonl",
                                     env_extra={"RODSKI_DEMO_HOOK_EXIT_on_session_start": "2"})
        names = [e["event"] for e in events]
        results = list((mod / "result").glob("*/result.xml"))
        return [
            ("H03:exit", code == 1, f"退出码 1（实际 {code}）"),
            ("H03:reason", "demo on_session_start hook denied" in out, "输出含 hook stdout JSON 中的 reason"),
            ("H03:short_circuit", names == ["on_session_start"] and not results,
             f"只触发 on_session_start，未进入 on_run_start / 执行用例（事件 {names}，result.xml {len(results)} 个）"),
        ]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def h04() -> Outcome:
    """进程内回调：after_keyword 每个关键字恰好一次（成功/失败），on_case_failure 只对失败用例触发且签名正确。"""
    sys.path.insert(0, str(RODSKI_DIR))
    from core.keyword_engine import HookResult  # noqa: E402
    from core.ski_executor import SKIExecutor  # noqa: E402

    after: List[dict] = []
    failures: List[dict] = []

    def after_keyword(keyword, params, result):
        after.append({"keyword": keyword, "data": (params or {}).get("data"),
                      "is_result": isinstance(result, HookResult), "status": getattr(result, "status", None),
                      "attempts": getattr(result, "attempts", None), "elapsed": getattr(result, "elapsed", None)})

    def on_case_failure(case, error, screenshot_path):
        failures.append({"case_id": case.get("case_id"), "error": error, "screenshot_path": screenshot_path})

    tmp = Path(tempfile.mkdtemp(prefix="rodski-hooks-"))
    try:
        mod = _temp_module(tmp)
        executor = SKIExecutor(case_path=str(mod / CASE_FILE), driver=None, module_dir=str(mod),
                               hooks={"after_keyword": [after_keyword], "on_case_failure": [on_case_failure]})
        try:
            results = {r["case_id"]: r["status"] for r in executor.execute_all_cases()}
        finally:
            executor.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    ok_calls = [a for a in after if a["data"] == "Q_READ"]
    err_calls = [a for a in after if a["data"] == "Q_NOT_EXIST"]
    f = failures[0] if failures else {}
    return [
        ("H04:status", results == {"HE_PASS": "PASS", "HE_FAIL": "FAIL"}, f"用例状态 {results}"),
        ("H04:after_ok", len(ok_calls) == 1 and ok_calls[0]["keyword"] == "DB" and ok_calls[0]["status"] == "ok"
         and ok_calls[0]["is_result"] and (ok_calls[0]["attempts"] or 0) >= 1 and (ok_calls[0]["elapsed"] or -1) >= 0,
         f"成功步骤 after_keyword 恰好一次，(keyword, params, HookResult status=ok)：{ok_calls}"),
        ("H04:after_err", len(err_calls) == 1 and err_calls[0]["status"] == "error",
         f"失败步骤 after_keyword 恰好一次，HookResult.status=error：{err_calls}"),
        ("H04:after_total", len(after) == 2, f"after_keyword 总调用次数 2（实际 {len(after)}）"),
        ("H04:failure", len(failures) == 1 and f.get("case_id") == "HE_FAIL"
         and isinstance(f.get("error"), Exception) and "Q_NOT_EXIST" in str(f.get("error"))
         and f.get("screenshot_path") in (None, ""),
         f"on_case_failure 只对 HE_FAIL 触发一次，(case dict, Exception, screenshot_path=None)："
         f"{[(x['case_id'], type(x['error']).__name__, x['screenshot_path']) for x in failures]}"),
    ]


CHECKS: Dict[str, Callable[[], Outcome]] = {"H01": h01, "H02": h02, "H03": h03, "H04": h04}


def main(argv: List[str]) -> int:
    selected = [a.upper() for a in argv] or list(CHECKS)
    counts = {"PASS": 0, "FAIL": 0, "KNOWN": 0}
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
    print(f"汇总: PASS={counts['PASS']} FAIL={counts['FAIL']} KNOWN={counts['KNOWN']}")
    return 0 if counts["FAIL"] == 0 and counts["KNOWN"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
