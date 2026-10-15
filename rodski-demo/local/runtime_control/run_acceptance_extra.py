#!/usr/bin/env python3
"""F108 运行时控制：终止 / 强制终止 / 暂停期间终止 + 文档声明的 CLI/服务端入口。

用法（仓库根目录）:
    python3 rodski-demo/local/runtime_control/run_acceptance_extra.py

文档依据:
    CORE_DESIGN_CONSTRAINTS.md §8.6（暂停「直至收到继续或终止」；终止区分正常 / 强制）、
    §8.7（一般命令等当前步骤结束后在步骤边界生效；强制终止不要求等待当前步骤自然结束，尽快中止）
    TEST_CASE_WRITING_GUIDE.md §11.5（终止：未勾选强制时等当前这一步跑完再停；命令来源 CLI / GUI / 服务端）

用例: case/terminate_case.xml（RT_TERM / RT_FORCE / RT_PAUSE_TERM / RT_AFTER）。
执行方式与 run_demo.py 相同：SKIExecutor + RuntimeCommandQueue（进程内 API），before/after_keyword
记录步骤日志，控制器线程在指定步骤执行中下发命令。看门狗：暂停后终止若把执行器卡住，
超时后补发 resume() 解卡并记为失败，避免脚本永久挂起。

输出与退出码约定：每项一行 `PASS|FAIL|KNOWN <编号> <说明>`，INFO 行只记录行为不计数；
最后 `汇总: PASS=x FAIL=y KNOWN=z`；全部 PASS 退出 0，否则 1。
"""
from __future__ import annotations

import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Dict, List, Tuple

MODULE_DIR = Path(__file__).resolve().parent
REPO = MODULE_DIR.parents[2]
RODSKI = REPO / "rodski"
sys.path.insert(0, str(RODSKI))

from core.config_manager import ConfigManager  # noqa: E402
from core.keyword_engine import HookDecision  # noqa: E402
from core.runtime_control import RuntimeCommandQueue  # noqa: E402
from core.ski_executor import SKIExecutor  # noqa: E402
from drivers.playwright_driver import PlaywrightDriver  # noqa: E402

CASE_FILE = MODULE_DIR / "case" / "terminate_case.xml"
CASE_IDS = ("RT_TERM", "RT_FORCE", "RT_PAUSE_TERM", "RT_AFTER")
FORCE_MAX_SECONDS = 1.0     # 强制终止：命令下发后应在 1s 内结束用例（当前步 wait 3 还剩约 2.7s）
PAUSE_TERM_UNSTICK = 8.0    # 暂停期间终止后 8s 仍未结束 → 判定卡住，补发 resume 解卡
WATCHDOG_SECONDS = 90.0

KNOWN = {
    "R02:fast": "强制终止只在步骤边界被处理，等当前步骤自然结束后才生效（CORE §8.7 要求不必等待）；"
                "core/runtime_control.py:98-115 drain_at_boundary 只在 core/ski_executor.py:1923-1961 "
                "_run_steps 的步骤前后调用，步内无中断点",
    "R03:no_hang": "暂停期间收到 terminate 后执行器仍处于暂停态（_unpaused 未 set），"
                   "后处理与后续用例在 _run_steps 的 wait_unpaused 循环中卡住"
                   "（core/runtime_control.py:112-113 TERMINATE 分支未 set _unpaused；core/ski_executor.py:1935）",
    "R05:cli_entry": "文档声明运行时控制命令可由 CLI / GUI / 服务端下发（CORE §8.6、GUIDE §11.5），"
                     "但 rodski run 只有 --insert-step，没有 pause / resume / terminate / force-terminate 入口，"
                     "也没有服务端下发接口（rodski/rodski_cli/run.py:1124 仅在 --insert-step 时创建队列）",
}


def build_config() -> ConfigManager:
    cfg = ConfigManager(config_path=str(MODULE_DIR / "no_such_config.json"))
    cfg.config["recording"]["enabled"] = False
    cfg.config["auto_screenshot_on_failure"] = False
    cfg.config["auto_screenshot_on_step"] = False
    return cfg


def run_executor() -> Tuple[Dict[str, dict], Dict[str, list], Dict[str, float], List[str], Dict[str, bool]]:
    rq = RuntimeCommandQueue()
    logs: Dict[str, list] = {}         # case_id -> [(phase, keyword, data, t_start)]
    step_end: Dict[Tuple[str, str], float] = {}
    case_end: Dict[str, float] = {}
    marks: Dict[str, float] = {}
    flags = {"unstuck": False, "watchdog": False}
    errors: List[str] = []
    started = {cid: threading.Event() for cid in CASE_IDS}
    done = threading.Event()
    holder: Dict[str, SKIExecutor] = {}

    def cid() -> str:
        ex = holder.get("ex")
        return getattr(ex, "_current_case_id", "?") if ex else "?"

    def before(keyword: str, params: dict):
        c = cid()
        logs.setdefault(c, []).append((keyword, str(params.get("data", "")), time.monotonic()))
        if c in started:
            started[c].set()
        return HookDecision(allow=True)

    def after(keyword: str, params: dict, result) -> None:
        step_end[(cid(), str(params.get("data", "")))] = time.monotonic()

    def wait_step(c: str, data: str, timeout: float = 30.0) -> bool:
        deadline = time.monotonic() + timeout
        while not any(d == data for _, d, _ in logs.get(c, [])):
            if time.monotonic() > deadline:
                errors.append(f"{c}: 等待步骤 wait {data} 开始超时")
                return False
            time.sleep(0.01)
        return True

    def controller() -> None:
        try:
            # RT_TERM：wait 1.5 执行中下发非强制 terminate
            if wait_step("RT_TERM", "1.5"):
                time.sleep(0.3)
                marks["term_cmd"] = time.monotonic()
                rq.terminate()
            # RT_FORCE：wait 3 执行中下发强制终止
            if wait_step("RT_FORCE", "3"):
                time.sleep(0.3)
                marks["force_cmd"] = time.monotonic()
                rq.terminate(force=True)
            # RT_PAUSE_TERM：navigate 后 pause，暂停生效后 terminate
            if started["RT_PAUSE_TERM"].wait(timeout=60):
                rq.pause()
                deadline = time.monotonic() + 10
                while rq.wait_unpaused(timeout=0.02):
                    if time.monotonic() > deadline:
                        errors.append("RT_PAUSE_TERM: pause 未在 10s 内生效")
                        return
                marks["paused_steps"] = len(logs.get("RT_PAUSE_TERM", []))
                time.sleep(0.3)
                marks["pause_term_cmd"] = time.monotonic()
                rq.terminate()
                # 看是否卡住：RT_PAUSE_TERM 结束（case_end 有记录）应很快发生
                deadline = time.monotonic() + PAUSE_TERM_UNSTICK
                while "RT_PAUSE_TERM" not in case_end and time.monotonic() < deadline:
                    time.sleep(0.05)
                if "RT_PAUSE_TERM" not in case_end:
                    flags["unstuck"] = True
                    rq.resume()
        except Exception:
            errors.append(traceback.format_exc())

    def watchdog() -> None:
        if not done.wait(timeout=WATCHDOG_SECONDS):
            flags["watchdog"] = True
            rq.resume()
            rq.terminate(force=True)

    driver = PlaywrightDriver(headless=True, browser="chromium")
    ex = SKIExecutor(str(CASE_FILE), driver, config=build_config(),
                     driver_factory=lambda: PlaywrightDriver(headless=True, browser="chromium"),
                     module_dir=str(MODULE_DIR), runtime_control=rq)
    holder["ex"] = ex
    ex.keyword_engine.before_keyword_hooks = [before]
    ex.keyword_engine.after_keyword_hooks = [after]
    orig_execute_case = ex.execute_case

    def execute_case(case):
        try:
            return orig_execute_case(case)
        finally:
            case_end[case.get("case_id", "?")] = time.monotonic()

    ex.execute_case = execute_case  # type: ignore[method-assign]
    threads = [threading.Thread(target=controller, daemon=True), threading.Thread(target=watchdog, daemon=True)]
    for t in threads:
        t.start()
    try:
        results = {r["case_id"]: r for r in ex.execute_all_cases()}
    finally:
        done.set()
        try:
            ex.close()
        except Exception:
            pass
        try:
            driver.close()
        except Exception:
            pass
    marks.update({f"end:{k}": v for k, v in case_end.items()})
    marks.update({f"step_end:{c}:{d}": v for (c, d), v in step_end.items()})
    return results, logs, marks, errors, flags


def main() -> int:
    counts = {"PASS": 0, "FAIL": 0, "KNOWN": 0}

    def report(sub: str, ok: bool, msg: str) -> None:
        status = "PASS" if ok else ("KNOWN" if sub in KNOWN else "FAIL")
        counts[status] += 1
        extra = f"  [已登记: {KNOWN[sub]}]" if status == "KNOWN" else ""
        print(f"{status}\t{sub}\t{msg}{extra}")

    results, logs, marks, errors, flags = run_executor()
    data = {c: [d for _, d, _ in logs.get(c, [])] for c in CASE_IDS}

    print("== R01 正常终止：当前步骤跑完后在步骤边界停止，后续固定步骤不执行（CORE §8.6/§8.7、GUIDE §11.5）")
    t_cmd = marks.get("term_cmd")
    t_end15 = marks.get("step_end:RT_TERM:1.5")
    report("R01:step_completed", bool(t_cmd and t_end15 and t_end15 - t_cmd > 0.9),
           f"wait 1.5 未被打断（命令后又执行 {((t_end15 or 0) - (t_cmd or 0)):.2f}s，应约 1.2s）")
    report("R01:no_next_step", "0.31" not in data["RT_TERM"],
           f"终止后后续固定步骤 wait 0.31 未执行（实际步骤 {data['RT_TERM']}）")
    print(f"INFO\tR01:status\tRT_TERM 结果 status={results.get('RT_TERM', {}).get('status')} "
          f"error={results.get('RT_TERM', {}).get('error')!r}；post_process 是否执行="
          f"{'0.01' in data['RT_TERM']}（文档未规定）")

    print("== R02 强制终止：不等待当前步骤自然结束，尽快中止（CORE §8.7）")
    f_cmd, f_end = marks.get("force_cmd"), marks.get("end:RT_FORCE")
    lag = (f_end - f_cmd) if (f_cmd and f_end) else float("nan")
    report("R02:fast", lag <= FORCE_MAX_SECONDS,
           f"命令下发到用例结束 {lag:.2f}s（期望 ≤ {FORCE_MAX_SECONDS}s；当前步 wait 3 剩余约 2.7s）")
    report("R02:no_next_step", "0.32" not in data["RT_FORCE"],
           f"强制终止后后续固定步骤 wait 0.32 未执行（实际步骤 {data['RT_FORCE']}）")
    print(f"INFO\tR02:status\tRT_FORCE 结果 status={results.get('RT_FORCE', {}).get('status')} "
          f"error={results.get('RT_FORCE', {}).get('error')!r}；post_process 是否执行={'0.02' in data['RT_FORCE']}")

    print("== R03 暂停期间终止：暂停「直至收到继续或终止」（CORE §8.6），终止后不应停留在暂停态")
    report("R03:no_next_step", "0.21" not in data["RT_PAUSE_TERM"] and "0.33" not in data["RT_PAUSE_TERM"],
           f"暂停期间终止后剩余固定步骤未执行（实际步骤 {data['RT_PAUSE_TERM']}）")
    report("R03:no_hang", not flags["unstuck"],
           f"终止后 {PAUSE_TERM_UNSTICK:.0f}s 内用例结束，无需额外 resume 解卡（实际需要解卡={flags['unstuck']}）")

    print("== R04 终止不使执行器挂起：所有用例都有结果返回")
    report("R04:returned", set(results) == set(CASE_IDS) and not flags["watchdog"],
           f"返回结果 {sorted(results)}，看门狗触发={flags['watchdog']}")
    print(f"INFO\tR04:after\tRT_AFTER status={results.get('RT_AFTER', {}).get('status')} 步骤={data['RT_AFTER']}"
          "（终止作用于当前用例还是整个会话，文档写「当前用例或当前执行会话」，未定，仅记录）")

    print("== R05 文档声明的 CLI / 服务端入口（CORE §8.6「来源可为 CLI、本地 GUI 或服务端」、GUIDE §11.5）")
    help_text = subprocess.run([sys.executable, str(RODSKI / "cli_main.py"), "run", "--help"],
                               capture_output=True, text=True).stdout
    has_entry = any(k in help_text for k in ("--terminate", "--force-terminate", "--pause", "--control"))
    report("R05:cli_entry", has_entry, "rodski run --help 存在 pause / terminate 类控制入口")

    for e in errors:
        print(f"FAIL\tcontroller\t{e.strip().splitlines()[-1]}")
        counts["FAIL"] += 1
    print(f"汇总: PASS={counts['PASS']} FAIL={counts['FAIL']} KNOWN={counts['KNOWN']}")
    return 0 if counts["FAIL"] == 0 and counts["KNOWN"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
