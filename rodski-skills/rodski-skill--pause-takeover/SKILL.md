---
name: pause-takeover
description: RodSki 用例「暂停 → Agent 接管页面 → 继续」工作流。当 Agent 需要让 RodSki 固定步骤跑到测试站点页面后暂停/停在 checkpoint，由 AI 用 playwright 判断页面内容并输出、操作 1-2 个按钮，再继续后续验证步骤时使用。触发词：「暂停接管」「pause takeover」「人工接管」「checkpoint」「Agent 操作页面后继续」。框架无关，支持任何能加载 Markdown skill 的 Agent。
---

# RodSki Pause-Takeover（暂停接管）

使用本 skill 时，将执行 RodSki「暂停 → Agent 接管 → 继续」交接协议：用例跑到目标页
（**checkpoint**）后，**调用 Agent 自己在共享浏览器上判断 + 操作**，再由 RodSki 在同一浏览器
会话继续 verify。编排权完全在调用 Agent 手里——本 skill 只给协议与边界。

## 什么时候用 / 什么时候不用

**适用：**
1. 固定用例已能稳定走到某页面，但中间需要「看一眼再决定」的判定，或临时填 1–2 个表单/按钮。
2. 交互结果必须与**同一会话**延续（登录态、SPA 内存状态、跨 run 一致的页面）才成立。
3. 需要人/AI 在自动化中途介入（回归联调、探索接管、异常处置）。

**不用：**
- 判定能固化成 `verify`（数据表期望 + `match_mode=subset`）→ 写进用例，别打断。
- 需要框架**内**暂停/插入（步骤边界注入步骤）→ `demo_runtime_control` / `RuntimeCommandQueue`。
- 目标是让框架自己多轮对话 → RodSki core 不做策略编排（`AGENT_INTEGRATION.md` 边界）。

## 编排协议（CDP 共享浏览器、双 run 交接）

RodSki 运行时控制（§8.6–8.7）的 pause 只在**步骤边界**生效、命令来自框架内 controller，
**没有**「从用例步内同步阻塞等 Agent」的原语。所以本协议用「自然 checkpoint + 双 run」：

```
① 启动共享浏览器（带 --remote-debugging-port，留窗口）
② rodski run <part1/case/> --cdp :9222      → 跑「进入目标页 + 前置登录」；run 结束浏览器保活
③ Agent: connect_over_cdp → 读页面判断 → 输出 → 点 1-2 按钮     （自行决定）
④ rodski run <part2/case/> --cdp :9222      → 同一浏览器继续 verify 跨 Agent 操作
```

前置：RodSki ≥ v11.1.0（含 driver CDP attach + CLI `--cdp`）；本机已装 playwright；被测站可达。

### ① 启动共享浏览器（任选其一）

```bash
# 有界面（推荐：可人工同时盯）
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 --user-data-dir=/tmp/rodski-takeover &
# Windows / Linux 换成各自 Chrome 路径

# 无头（无人盯、CI）
python3 - <<'PY'
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    p.chromium.launch(headless=True, args=["--remote-debugging-port=9222"])
    import time; time.sleep(3600)
PY
```

端口占用/`user-data-dir` 被锁 → 换端口或换目录；确认可达：`curl http://127.0.0.1:9222/json/version`。

### ② run-1：跑到 checkpoint（浏览器保活）

```bash
rodski run product/你的模块/case/part1_login.xml --cdp :9222 --output-format json
```

- **用例不要以 `close` 结尾**：`--cdp` 下 executor 结束时 driver 仅断连、不关浏览器
  （attached driver 的 `close()` 是断连语义），登录态/页面留在共享 context。
- 段间唯一约定：**不改写被测站状态导致下一段失效**（登录不算，登出算）。

### ③ Agent 接管：读、判、点

任意 playwright 客户端（Claude Code / Codex / 脚本）连同一浏览器：

```python
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    page = b.contexts[0].pages[0]          # run-1 停在的那个页面
    # 判断：先输出证据再行动
    print(page.url, page.title())
    print(page.text_content("body"))
    # 操作 1-2 个按钮 / 填表
    page.click("#navTest"); page.fill("#username", "接管人"); page.click("#submitBtn")
    b.close()                               # 仅断连，别关浏览器
```

- 多个 playwright 客户端**串行** connect（同一浏览器同一默认 context，别并发抢同一个 page）。
- 同一进程内不要嵌套两次 `sync_playwright()`（会报 Sync API inside asyncio loop）——共用一个实例。

### ④ run-2：同一浏览器继续验证

```bash
rodski run product/你的模块/case/part2_continue.xml --cdp :9222
```

part2 用**全新进程 + CDP 附加**验证 ③ 的操作结果与 ① 保留的会话态；参考
`demo_pause_takeover/case/part2_continue.xml`（两条互补断言见下）。

## 可执行参考

- **全自动闭环 demo**：`rodski-demo/DEMO/demo_pause_takeover/run_demo.py`
  （真实 CDP 三段：run-1 登录 → agent 接管 → run-2 verify），仓库根目录直接跑。
- 用例对：`part1_login.xml`（进站登录）+ `part2_continue.xml`（verify agent 写入值 + 登录态）。

## 把用例切成 checkpoint 的写法

1. **part1 到 checkpoint 即停**：前置 + 进入目标页 + 登录（如需），**不要** close。
2. **part2 只做断言**：用 `verify Model DataID match_mode="subset"` 只验 Agent 会改动的字段；
   期望值 = Agent 操作后的**确切文本**（写进 `<Model>_verify` 表）。
3. **互补断言防空洞**：
   - 验 Agent 写入的字段（`formResult`）→ 排除「part2 自己另起炉灶」不够，还要
   - 验登录/会话态（如 dashboard 卡片）→ 排除「part2 重新登录后自己操作表单」。
   两者都 PASS 才说明「接管真的作用于共享会话」。见 `references/checkpoint-partitioning.md`。

## 验证手段（防空洞 checklist）

- [ ] run-2 用**全新进程 + CDP**（无任何跨进程 Python 状态共享）。
- [ ] part2 至少一条 verify 依赖「Agent 在页面上产生的状态」。
- [ ] 做过负向对照：part2 换全新 launch 浏览器应 FAIL（回到登录页 / 读不到写入值）。
- [ ] Agent 段先输出判断证据（URL/文本）再行动；断连不关浏览器。

## 常见坑

| 坑 | 对策 |
|----|------|
| `--cdp` 下用例以 close 结尾 | attached driver close=断连，页面保留；但别在用例里显式 close 关 context（会被忽略/影响复用）。直接不加 close 步骤 |
| 端口占用 / `user-data-dir` 被锁 | 换端口、换临时目录；`curl .../json/version` 探活 |
| 同一进程内两次 `sync_playwright()` | 报 asyncio 冲突；子进程/复用实例 |
| 录制/截图默认开 | run 用 `--record-mode off` 或 ConfigManager 关 `recording.enabled/auto_screenshot_*` |
| connect 到已有页面后立刻操作失败 | `page.wait_for_load_state("domcontentloaded")` |
| 无头下没 `#loginBtn` 判断 | 用可见性/文本做会话判据，别只看元素存在 |
