#!/usr/bin/env python3
"""演示 RuntimeCommandQueue：暂停 / 恢复 / 暂停期间插入（与《核心设计约束》§8.6–8.7 一致）

本脚本覆盖 3 个用例（case/runtime_case.xml）：
  RT_INSERT        固定步骤执行中 insert 一条 wait 0.2（保留既有演示，不回归）
  RT_PAUSE         pause 后执行流在步骤边界停住：暂停期间无任何新步骤启动，resume 后继续
  RT_PAUSE_INSERT  暂停期间队列仍被消费：insert 排到队首，resume 后按插入顺序先执行

验证手段：挂在 before_keyword 的步骤日志 + 控制器线程轮询 rq.wait_unpaused()。
  - 控制器在执行器暂停生效（wait_unpaused 返回 False）后，开一个观察窗；
    若暂停未生效，剩余 wait 步会在观察窗内启动，日志长度会增长 → 可据此断言
    "暂停期间没有启动新步骤"，避免空洞通过。
"""
from __future__ import annotations

import sys
import threading
import time
import traceback
from pathlib import Path

# rodski 包路径：…/RodSki/rodski
_REPO = Path(__file__).resolve().parent.parent.parent.parent
_RODSKI = _REPO / "rodski"
if str(_RODSKI) not in sys.path:
    sys.path.insert(0, str(_RODSKI))

from core.config_manager import ConfigManager  # noqa: E402
from core.keyword_engine import HookDecision  # noqa: E402
from core.runtime_control import RuntimeCommandQueue  # noqa: E402
from core.ski_executor import SKIExecutor  # noqa: E402
from drivers.playwright_driver import PlaywrightDriver  # noqa: E402

CASE_IDS = ("RT_INSERT", "RT_PAUSE", "RT_PAUSE_INSERT")
# 观察窗：若未真正暂停，剩余 wait 步会在此窗口内启动（断言依据）
OBSERVE_SECONDS = 0.6
# 各控制器等待"用例已开始"的上限
START_TIMEOUT_SECONDS = 30.0
# 总执行看门狗：防止意外"暂停后无人 resume"把脚本永久挂起
WATCHDOG_SECONDS = 60.0


def build_config() -> ConfigManager:
    """关闭录制/截图副作用，保持运行干净（对应根 config/config.json 的 recording.enabled=false）。"""
    cfg = ConfigManager(config_path=str(Path(__file__).resolve().parent / "no_such_config.json"))
    cfg.config["recording"]["enabled"] = False
    cfg.config["auto_screenshot_on_failure"] = False
    cfg.config["auto_screenshot_on_step"] = False
    return cfg


def main() -> int:
    module_dir = Path(__file__).resolve().parent
    case_path = module_dir / "case" / "runtime_case.xml"

    rq = RuntimeCommandQueue()
    logs: dict[str, list] = {}        # case_id -> [{keyword, data, t}]
    started: dict[str, threading.Event] = {cid: threading.Event() for cid in CASE_IDS}
    ctl_errors: list[str] = []
    done = threading.Event()          # 看门狗：整体执行结束
    watchdog_fired = threading.Event()
    executor: SKIExecutor | None = None

    def create_driver() -> PlaywrightDriver:
        return PlaywrightDriver(headless=True, browser="chromium")

    driver = create_driver()

    def before_keyword(keyword: str, params: dict):
        """步骤日志 + 用例开始信号。返回值恒放行，不改变执行语义。"""
        cid = getattr(executor, "_current_case_id", "?") if executor is not None else "?"
        bucket = logs.setdefault(cid, [])
        bucket.append({
            "keyword": keyword,
            "data": str(params.get("data", "")),
            "t": time.monotonic(),
        })
        if cid in started:
            started[cid].set()
        return HookDecision(allow=True)

    def fail_controller(msg: str) -> None:
        ctl_errors.append(msg)

    def _run_controller(cid: str, body) -> None:
        try:
            if not started[cid].wait(timeout=START_TIMEOUT_SECONDS):
                fail_controller(f"{cid}: 用例未在 {START_TIMEOUT_SECONDS}s 内开始")
                return
            body()
        except Exception:
            fail_controller(f"{cid}: {traceback.format_exc()}")

    def controller_insert() -> None:
        """RT_INSERT：等固定 wait 1 已开始后在其中途入队一条 wait 0.2。

        用例固定为 navigate about:blank → wait 1；navigate 首次冷启动较慢（约 1s），
        因此必须先等到 wait 1 的 before_keyword 触发（navigate 已结束）再 insert，
        确保插入落在 wait 1 执行中、在该步边界后才被处理 → 顺序为
        navigate → wait 1 → 插入的 wait 0.2（与既有演示语义一致）。
        """
        def body() -> None:
            log = logs.setdefault("RT_INSERT", [])
            deadline = time.monotonic() + 20.0
            while not any(e["keyword"] == "wait" and e["data"] == "1" for e in log):
                if time.monotonic() > deadline:
                    fail_controller("RT_INSERT: 等待固定 wait 1 步骤开始超时")
                    return
                time.sleep(0.01)
            time.sleep(0.3)  # 处于 wait 1 执行中（§8.7：边界排队）
            rq.insert([{"action": "wait", "model": "", "data": "0.2"}])
        _run_controller("RT_INSERT", body)

    def _pause_and_wait_effective(cid: str) -> None:
        """入队 pause 并轮询到边界生效（wait_unpaused 返回 False）。"""
        rq.pause()
        deadline = time.monotonic() + 10.0
        while rq.wait_unpaused(timeout=0.02):
            if time.monotonic() > deadline:
                fail_controller(f"{cid}: pause 未在 10s 内于边界生效")
                return

    def controller_pause() -> None:
        """RT_PAUSE：navigate 一结束即暂停，观察窗内无新步骤启动，再 resume。"""
        def body() -> None:
            log = logs.setdefault("RT_PAUSE", [])
            _pause_and_wait_effective("RT_PAUSE")
            pause_t = time.monotonic()
            base = len(log)
            print(f"[controller RT_PAUSE] pause 生效于 t={pause_t - log[0]['t']:.2f}s"
                  f"（已执行 {base} 步: {[e['keyword'] for e in log]}），开观察窗 {OBSERVE_SECONDS}s")
            time.sleep(OBSERVE_SECONDS)
            now = len(log)
            if now != base or rq.wait_unpaused(timeout=0.0):
                fail_controller(
                    f"RT_PAUSE: 暂停观察窗内不应启动新步骤（base={base}, now={now}）"
                )
                return
            print("[controller RT_PAUSE] 观察窗内无新步骤启动 → resume")
            rq.resume()
        _run_controller("RT_PAUSE", body)

    def controller_pause_insert() -> None:
        """RT_PAUSE_INSERT：暂停期间 insert 3×wait 0.2，验证队列在暂停中仍被消费。"""
        def body() -> None:
            log = logs.setdefault("RT_PAUSE_INSERT", [])
            _pause_and_wait_effective("RT_PAUSE_INSERT")
            pause_t = time.monotonic()
            base = len(log)
            steps = [{"action": "wait", "model": "", "data": "0.2"} for _ in range(3)]
            rq.insert(steps)
            print(f"[controller RT_PAUSE_INSERT] pause 生效于 t={pause_t - log[0]['t']:.2f}s"
                  f"（已执行 {base} 步），暂停期间插入 {len(steps)}×wait 0.2")
            time.sleep(OBSERVE_SECONDS)
            now = len(log)
            if now != base or rq.wait_unpaused(timeout=0.0):
                fail_controller(
                    f"RT_PAUSE_INSERT: 暂停观察窗内不应启动新步骤（base={base}, now={now}）"
                )
                return
            print("[controller RT_PAUSE_INSERT] 插入后观察窗内仍无新步骤启动 → resume")
            rq.resume()
        _run_controller("RT_PAUSE_INSERT", body)

    def watchdog() -> None:
        if done.wait(timeout=WATCHDOG_SECONDS):
            return
        watchdog_fired.set()
        rq.terminate(force=True)
        print(f"[watchdog] {WATCHDOG_SECONDS}s 未完成，force_terminate 兜底")

    try:
        executor = SKIExecutor(
            str(case_path),
            driver,
            config=build_config(),
            driver_factory=lambda: create_driver(),
            module_dir=str(module_dir),
            runtime_control=rq,
        )
        executor.keyword_engine.before_keyword_hooks = [before_keyword]

        threads = [
            threading.Thread(target=controller_insert, daemon=True),
            threading.Thread(target=controller_pause, daemon=True),
            threading.Thread(target=controller_pause_insert, daemon=True),
            threading.Thread(target=watchdog, daemon=True),
        ]
        for t in threads:
            t.start()

        results = executor.execute_all_cases()
        done.set()
        for t in threads[:3]:
            t.join(timeout=10)

        by_case = {r["case_id"]: r for r in results}
        ok = True

        def fail(msg: str) -> None:
            nonlocal ok
            ok = False
            print(f"  ✗ {msg}")

        def actions(res: dict) -> list[str]:
            return [s.get("action", "") for s in res.get("steps", [])]

        def data_seq(cid: str) -> list[str]:
            return [e["data"] for e in logs.get(cid, [])]

        # 1) 三个用例都应 PASS
        for cid in CASE_IDS:
            st = by_case.get(cid, {}).get("status", "MISSING")
            print(f"  {cid}: {st}")
            if st != "PASS":
                fail(f"{cid} 应为 PASS，实际 {st}: {by_case.get(cid, {}).get('error')}")

        # 2) 控制器断言语义（暂停期间无新步骤）不允许失败
        if ctl_errors:
            ok = False
            for e in ctl_errors:
                print(f"  ✗ controller: {e}")

        # 3) 步骤/顺序断言
        #    RT_INSERT：navigate + wait1 + 插入的 wait0.2，共 3 条 wait 后一条
        a = actions(by_case.get("RT_INSERT", {}))
        if a != ["navigate", "wait", "wait"]:
            fail(f"RT_INSERT 步序异常: {a}")
        d = data_seq("RT_INSERT")
        if d != ["about:blank", "1", "0.2"]:
            fail(f"RT_INSERT hook 数据顺序异常: {d}")
        #    RT_PAUSE：navigate → wait 0.2 → wait 1（暂停后 resume，顺序不变）
        a = actions(by_case.get("RT_PAUSE", {}))
        if a != ["navigate", "wait", "wait"]:
            fail(f"RT_PAUSE 步序异常: {a}")
        d = data_seq("RT_PAUSE")
        if d != ["about:blank", "0.2", "1"]:
            fail(f"RT_PAUSE hook 数据顺序异常: {d}")
        #    RT_PAUSE_INSERT：navigate 后暂停，插入 3×wait0.2 排到队首，再执行 wait1
        a = actions(by_case.get("RT_PAUSE_INSERT", {}))
        if a != ["navigate"] + ["wait"] * 5:
            fail(f"RT_PAUSE_INSERT 步序异常: {a}")
        d = data_seq("RT_PAUSE_INSERT")
        if d != ["about:blank", "0.2", "0.2", "0.2", "0.2", "1"]:
            fail(f"RT_PAUSE_INSERT hook 数据顺序异常: {d}")

        if watchdog_fired.is_set():
            ok = False
            print("  ✗ watchdog 触发（执行未在时限内完成）")

        print("结论: " + ("全部通过 ✔" if ok else "存在失败 ✘"))
        return 0 if ok else 1
    finally:
        if executor is not None:
            try:
                executor.close()
            except Exception:
                pass
        try:
            driver.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
