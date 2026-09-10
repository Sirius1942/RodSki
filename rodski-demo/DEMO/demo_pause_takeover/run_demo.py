#!/usr/bin/env python3
"""演示「暂停 → Agent 接管页面 → 继续」：CDP 共享浏览器双 run 交接。

对应 rodski-skills/rodski-skill--pause-takeover。编排三段，全程无人值守：

  run-1   TK_P1   （独立子进程 + CDP 附加 driver）navigate 被测站 + 登录 → dashboard。
                  executor.close() 只断连，**浏览器保留登录态**。
  agent   (内嵌 playwright 扮演外部 AI Agent) connect_over_cdp 到同一浏览器 →
                  读当前页判断登录态（输出证据）→ 切功能测试页 → 填表单 + 选角色 →
                  点提交（写 #formResult）→ 断连。
  run-2   TK_P2   （**全新子进程** + CDP 附加 driver）attach 同一浏览器 →
                  verify TakeoverForm V001(subset) 断言 Agent 写入的 formResult +
                  verify Dashboard V001 断言登录态与卡片值 → PASS。

每个 phase 用独立 Python 子进程跑（_run_phase.py），避免同一线程内嵌套
sync_playwright（Sync API inside asyncio loop）冲突；共享浏览器由本脚本进程保活。

证明点：run-2 与 run-1 是两个独立进程，没有任何共享 Python 状态；只有 CDP 附加到
同一浏览器，run-2 才能读到 Agent 操作产生的 #formResult 与已登录的 dashboard。
若非共享浏览器（全新 launch），TK_P2 会回到登录页而 FAIL → 排除空洞通过。

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
    print("=" * 64)
    print("演示「暂停 → Agent 接管 → 继续」：CDP 共享浏览器双 run 交接")
    print(f"被测站: {SITE}   共享浏览器 CDP: {CDP_ENDPOINT}")
    print("=" * 64)

    ok = True

    def fail(msg: str) -> None:
        nonlocal ok
        ok = False
        print(f"  ✗ {msg}")

    try:
        # 启动共享浏览器（--remote-debugging-port），整场保活，finally 里真关。
        # 注意：必须在最外层 with sync_playwright() 内（同一线程同一事件循环），
        # 内嵌的 Agent 接管段复用同一实例，不再二次 sync_playwright()。
        with sync_playwright() as pw:
            shared = pw.chromium.launch(
                headless=True, args=[f"--remote-debugging-port={CDP_PORT}"]
            )
            print(f"[setup] 共享浏览器已启动 (headless, CDP {CDP_ENDPOINT})")

            # ---- run-1：登录（独立子进程）----
            print("\n[run-1] TK_P1 登录进入 dashboard（CDP 附加，executor.close 仅断连）")
            rc1 = run_phase("part1_login.xml")
            if rc1 != 0:
                raise SystemExit("run-1 TK_P1 失败，无法继续接管演示")

            # ---- Agent 接管（复用共享浏览器同一 sync_playwright 实例）----
            print("\n[agent] 外部 Agent 接管：connect_over_cdp 同一浏览器 → 判断 → 操作")
            agent_takeover(pw)

            # ---- run-2：继续验证（全新子进程）----
            print("\n[run-2] TK_P2 全新子进程 attach 同一浏览器，验证 Agent 操作延续")
            rc2 = run_phase("part2_continue.xml")
            if rc2 != 0:
                fail("run-2 TK_P2 失败（若回到登录页/读不到 formResult，说明会话未共享）")

        if ok:
            print("\n结论: 暂停接管闭环通过 ✔（run-2 在全新 driver 进程附加同一浏览器，"
                  "读到 Agent 操作结果与登录态 → 接管真实延续）")
        else:
            print("\n结论: 存在失败 ✘")
        return 0 if ok else 1
    finally:
        # 若子进程把共享浏览器关了（异常路径），不影响退出码判定
        pass


if __name__ == "__main__":
    raise SystemExit(main())
