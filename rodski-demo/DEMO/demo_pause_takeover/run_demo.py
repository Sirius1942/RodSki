#!/usr/bin/env python3
"""演示「执行一段用例 → 暂停 → 接管执行探索类步骤 → 后置自动化用例（含 close）」。

对应 rodski-skills/rodski-skill--pause-takeover。共享浏览器 + 五段编排，全程无人值守：

  run-1   TK_P1   固定用例段：navigate 被测站 + 登录 → dashboard。
                  executor.close() 只断连，**浏览器保留登录态**。
                  ← 这里是「暂停」点：用例跑完了，页面停在被测站点上。
  agent   接管段：内嵌 playwright 扮演外部 AI Agent，connect_over_cdp 同一浏览器 →
                  判断当前页面（读 #currentUser / 看板卡片，输出证据）→
                  切功能测试页 → 填表格 + 选角色 → 提交。
  run-2   TK_P2   自动化用例收回控制权：verify 接管段写进 #formResult 的值。
  explore 探索段：用**真实 CLI**（rodski explore-step --cdp）在**同一浏览器会话**上
                  执行探索类步骤——边界输入（用户名留空提交）、读取表单实际文本、
                  用 evaluate 读模型未覆盖的页面内部状态（#resultId）。
                  每步返回结构化证据（截图 / URL / 返回值）。
                  这是「接管期间做探索测试」的落点：探索动作不是固定用例，因此不写进
                  case XML，而是由 Agent 逐条发起、逐条留证。
  run-3   TK_P3   后置自动化用例段：verify 探索段留下的页面状态（严格模式）+
                  verify 看板登录态 + **close 收尾**。
                  在 CDP 附加模式下 close 只断连，浏览器仍存活（脚本随后显式断言这一点，
                  再由本进程真正关闭）——这正是「接管期间浏览器不被框架顺手关掉」的保证。

每个 rodski 阶段都用独立 Python 子进程跑（_run_phase.py / _run_explore.py），避免同一
线程内嵌套 sync_playwright（Sync API inside asyncio loop）冲突；共享浏览器由本脚本进程
保活并最终关闭。

证明点：run-2 / explore / run-3 都是独立进程，彼此不共享任何 Python 状态；只有 CDP 附加到
同一浏览器，才能读到前一段留下的页面状态。若非共享浏览器（全新 launch），TK_P2/TK_P3 会
回到登录页而 FAIL → 排除空洞通过。

前置：被测站已在 :8000 运行（python3 rodski-demo/DEMO/demo_full/demosite/app.py）。
运行：仓库根目录 python3 rodski-demo/DEMO/demo_pause_takeover/run_demo.py
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright  # noqa: E402

MODULE = Path(__file__).resolve().parent
SITE = "http://localhost:8000"
CDP_PORT = 9333
CDP_ENDPOINT = f"http://127.0.0.1:{CDP_PORT}"
WATCHDOG_SECONDS = 90.0
EXPLORE_SESSION = "takeover_demo"

# 探索段步骤：真实 CLI 形态（agent 手里只有 rodski 命令时就是这么用的）。
# 每步 (说明, CLI 参数)。动词都是探索语义——探测边界、采集证据，不做固定断言。
EXPLORE_STEPS = [
    (
        "边界输入：用户名留空 + 选择角色「用户」后提交（观察页面缺参时的表现）",
        ["--action", "type", "--model", "TakeoverForm", "--data", "E001"],
    ),
    (
        "采集证据：读取功能测试表单各元素当前文本（拿回结构化实际值）",
        ["--action", "get", "--model", "TakeoverForm", "--data", "E001"],
    ),
    (
        "模型盲区：evaluate 读模型未覆盖的 #resultId（探索补充模型之外的状态）",
        ["--action", "evaluate", "--model", "",
         "--data", "document.getElementById('resultId').textContent"],
    ),
]


def probe_site() -> None:
    import urllib.request
    for _ in range(30):
        try:
            with urllib.request.urlopen(SITE, timeout=2) as resp:
                if resp.status == 200:
                    return
        except Exception:
            time.sleep(0.5)
    raise SystemExit(
        f"被测站未在 {SITE} 响应。请先启动: "
        f"python3 rodski-demo/DEMO/demo_full/demosite/app.py"
    )


def run_phase(case_name: str) -> int:
    """子进程执行一个 phase case（独立事件循环，避免嵌套 sync_playwright）。"""
    runner = MODULE / "_run_phase.py"
    proc = subprocess.run(
        [sys.executable, str(runner), case_name],
        cwd=str(MODULE),
        capture_output=False,
        text=True,
    )
    return proc.returncode


def run_explore_step(step_no: int, args: list[str]) -> int:
    """子进程走真实 CLI 执行一步探索命令（--cdp 由 runner 注入）。

    以 JSON 模式调用并解析结果，把探索证据（URL / 返回值 / 截图路径）压成一行摘要
    ——探索的价值就在这些证据上，命令行原样输出会淹没在日志里。
    """
    runner = MODULE / "_run_explore.py"
    proc = subprocess.run(
        [
            sys.executable, str(runner),
            "--session", EXPLORE_SESSION,
            "--budget-steps", str(len(EXPLORE_STEPS) + 5),
            "--output", "json",
            *args,
        ],
        cwd=str(MODULE),
        capture_output=True,
        text=True,
    )

    payload = _parse_cli_json(proc.stdout)
    if payload is None:
        print(proc.stdout.rstrip())
        print(proc.stderr.rstrip(), file=sys.stderr)
        return proc.returncode or 1

    evidence = payload.get("evidence") or {}
    print(f"       success={payload.get('success')} url={evidence.get('url')}")
    if evidence.get("return_value") is not None:
        print(f"       return_value={evidence['return_value']}")
    screenshot = evidence.get("screenshot")
    if screenshot:
        try:
            screenshot = Path(screenshot).relative_to(MODULE.parents[3])
        except ValueError:
            pass
        print(f"       screenshot={screenshot}")
    for err in payload.get("errors") or []:
        print(f"       error: {err.splitlines()[0]}")
    return 0 if payload.get("success") else 1


def _parse_cli_json(stdout: str) -> dict | None:
    """从 CLI 输出中摘出结果 JSON（日志行可能与 JSON 混在同一路输出）。"""
    import json

    start = stdout.find("{\n")
    while start != -1:
        try:
            return json.loads(stdout[start:])
        except json.JSONDecodeError:
            start = stdout.find("{\n", start + 1)
    return None


def agent_takeover(pw) -> None:
    """Agent 接管段：connect_over_cdp 同一浏览器，判断 + 输出 + 操作。

    扮演真实外部 AI Agent：用 playwright API 直接读页面内容并输出证据，
    再做有限操作（点 #navTest 切功能测试页 → 填表单 + 选角色 → 点 #submitBtn）。

    注意：与共享浏览器共用一个 sync_playwright 实例（同一线程同一事件循环，
    不能在同进程内第二次 sync_playwright()）。
    """
    browser = pw.chromium.connect_over_cdp(CDP_ENDPOINT)
    try:
        ctx = browser.contexts[0]
        page = ctx.pages[0]
        page.wait_for_load_state("domcontentloaded")

        # 1) 判断：读到的是登录后的 dashboard（run-1 保留的会话），不是登录页
        user = (page.text_content("#currentUser") or "").strip()
        total = (page.text_content("#totalOrders") or "").strip()
        completed = (page.text_content("#completedOrders") or "").strip()
        login_visible = page.is_visible("#loginBtn")
        print(f"  [agent] 附加共享浏览器 → title={page.title()!r} url={page.url}")
        print(f"  [agent] 判断：当前用户={user!r} 总订单={total!r} 已完成={completed!r} "
              f"登录表单可见={login_visible}")
        if login_visible or user != "admin":
            raise SystemExit(
                "[agent] 未看到登录态（当前用户 admin、dashboard 卡片），共享会话未保留 → 演示失败"
            )
        print("  [agent] ✓ 判断成立：run-1 的登录态在共享浏览器中延续")

        # 2) 操作：切到功能测试页，填表并提交（写 #formResult 供 run-2 verify）
        page.click("#navTest")
        page.fill("#username", "接管人")
        page.select_option("#role", "admin")
        page.click("#submitBtn")
        page.wait_for_timeout(200)
        form_result = (page.text_content("#formResult") or "").replace("\n", " ").strip()
        print(f"  [agent] 操作完成：#navTest + 表单(username=接管人, role=admin, submit) "
              f"→ #formResult={form_result!r}")
        if "接管人" not in form_result:
            raise SystemExit(f"[agent] #formResult 断言失败: {form_result!r}")
        print("  [agent] ✓ Agent 操作已作用到共享浏览器页面")
    finally:
        browser.close()  # 仅断连


def main() -> int:
    probe_site()
    print("=" * 72)
    print("演示「用例段 → 暂停 → 接管（含探索步骤）→ 后置用例（含 close）」")
    print(f"被测站: {SITE}   共享浏览器 CDP: {CDP_ENDPOINT}")
    print("=" * 72)

    ok = True

    def fail(msg: str) -> None:
        nonlocal ok
        ok = False
        print(f"  ✗ {msg}")

    # 清理上一轮探索会话，保证可重复执行（否则去重会把同一条命令判为重复）
    session_file = MODULE / "result" / "explore" / f"session_{EXPLORE_SESSION}.json"
    if session_file.exists():
        session_file.unlink()

    try:
        # 启动共享浏览器（--remote-debugging-port），整场保活，finally 里真关。
        # 注意：必须在最外层 with sync_playwright() 内（同一线程同一事件循环），
        # 内嵌的 Agent 接管段复用同一实例，不再二次 sync_playwright()。
        with sync_playwright() as pw:
            shared = pw.chromium.launch(
                headless=True, args=[f"--remote-debugging-port={CDP_PORT}"]
            )
            print(f"[setup] 共享浏览器已启动 (headless, CDP {CDP_ENDPOINT})")

            # ---- run-1：固定用例段（登录），跑完即「暂停」----
            print("\n[run-1] TK_P1 固定用例段：navigate + 登录（CDP 附加，close 仅断连）")
            if run_phase("part1_login.xml") != 0:
                raise SystemExit("run-1 TK_P1 失败，无法继续接管演示")

            # ---- 接管段 A：Agent 判断页面 + 操作 ----
            print("\n[agent] 接管段 A：外部 Agent connect_over_cdp → 判断页面 → 操作")
            agent_takeover(pw)

            # ---- run-2：自动化用例收回控制权，验证接管操作 ----
            print("\n[run-2] TK_P2 自动化用例：verify 接管段写进 #formResult 的值")
            if run_phase("part2_continue.xml") != 0:
                fail("run-2 TK_P2 失败（若回到登录页/读不到 formResult，说明会话未共享）")

            # ---- 接管段 B：探索类测试步骤（真实 CLI，逐条发起、逐条留证）----
            print(f"\n[explore] 接管段 B：探索类步骤（真实 CLI: rodski explore-step --cdp "
                  f"{CDP_ENDPOINT}）")
            for idx, (desc, step_args) in enumerate(EXPLORE_STEPS, start=1):
                print(f"\n  [explore {idx}/{len(EXPLORE_STEPS)}] {desc}")
                if run_explore_step(idx, step_args) != 0:
                    fail(f"探索步骤 {idx} 执行失败: {' '.join(step_args)}")

            # ---- run-3：后置自动化用例段（验证探索产物 + close 收尾）----
            print("\n[run-3] TK_P3 后置用例段：verify 探索产物 + verify 登录态 + close 收尾")
            if run_phase("part3_post.xml") != 0:
                fail("run-3 TK_P3 失败（探索步骤写入的页面状态未被后置用例读到）")

            # ---- 收尾断言：附加模式下的 close 只断连，浏览器必须仍存活 ----
            if shared.is_connected():
                print("\n[teardown] ✓ 后置用例的 close 未关闭共享浏览器"
                      "（CDP 附加模式 close = 断连）")
            else:
                fail("后置用例的 close 把共享浏览器关掉了（附加模式语义被破坏）")

            shared.close()  # 拥有者收尾：这才真正关闭浏览器
            print("[teardown] 共享浏览器已由编排进程（拥有者）关闭")

        if ok:
            print("\n结论: 「用例段 → 暂停 → 接管（含探索步骤）→ 后置用例 + close」闭环通过 ✔")
            print("       run-2 / explore / run-3 均为独立进程附加同一浏览器，"
                  "读到前一段留下的页面状态 → 接管真实延续")
        else:
            print("\n结论: 存在失败 ✘")
        return 0 if ok else 1
    finally:
        # 若子进程把共享浏览器关了（异常路径），不影响退出码判定
        pass


if __name__ == "__main__":
    raise SystemExit(main())
