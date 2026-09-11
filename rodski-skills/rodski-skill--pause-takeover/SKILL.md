---
name: pause-takeover
description: RodSki 用例「暂停 → Agent 接管页面（含探索步骤）→ 后置用例收尾」工作流。当 Agent 需要让 RodSki 固定步骤跑到测试站点页面后暂停/停在 checkpoint，由 AI 用 playwright 判断页面内容并输出、操作按钮、执行探索类测试步骤（rodski explore-step --cdp），再继续用自动化用例验证并由 close 收尾时使用。触发词：「暂停接管」「pause takeover」「人工接管」「checkpoint」「接管后探索」「Agent 操作页面后继续」。框架无关，支持任何能加载 Markdown skill 的 Agent。
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

## 编排协议（CDP 共享浏览器、多 run 交接）

RodSki 运行时控制（§8.6–8.7）的 pause 只在**步骤边界**生效、命令来自框架内 controller，
**没有**「从用例步内同步阻塞等 Agent」的原语。所以本协议用「自然 checkpoint + 多 run」：

```
① 启动共享浏览器（带 --remote-debugging-port，留窗口）
② rodski run <part1/case/> --cdp :9222      → 跑「进入目标页 + 前置登录」；run 结束浏览器保活
③ Agent: connect_over_cdp → 读页面判断 → 输出 → 点 1-2 按钮     （自行决定）
④ rodski run <part2/case/> --cdp :9222      → 同一浏览器继续 verify 跨 Agent 操作
⑤ Agent: rodski explore-step ... --cdp :9222 → 探索类步骤：逐条发起、逐条留证（可选）
⑥ rodski run <part3/case/> --cdp :9222      → 后置用例段：验证探索产物 + close 收尾
```

③ 与 ⑤ 的区别：③ 是**你自己**（Agent）用 playwright 直接操作页面；⑤ 是**复用框架的关键字
引擎**做探索步骤——批量定位、动作语法、证据采集（截图/URL/返回值）都由 RodSki 出，你只发命令。
两者可交替使用；需要「探索动作也进框架日志/证据链」时走 ⑤。

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

### ⑤ 探索类步骤：把探索动作也交给框架执行（可选）

当接管期要做**探索**（边界输入、探测未知界面、采集页面实际值）而不只是「看一眼点一下」时，
用 `explore-step` 单步命令代替手写 playwright——定位/动作语法/证据采集由框架出，你只发命令：

```bash
# 边界探测：用户名留空 + 选角色后提交（数据行 E001）
rodski explore-step --module product/你的模块 --session take1 --cdp :9222 \
  --action type --model TakeoverForm --data E001 --output json

# 采集证据：读回表单各元素当前文本（结构化 return_value）
rodski explore-step --module product/你的模块 --session take1 --cdp :9222 \
  --action get --model TakeoverForm --data E001 --output json

# 模型盲区：evaluate 读模型未覆盖的页面内部状态
rodski explore-step --module product/你的模块 --session take1 --cdp :9222 \
  --action evaluate --model "" --data "document.getElementById('resultId').textContent"
```

- 每条命令返回 `{success, evidence:{screenshot,url,return_value,browser_errors}, session_state, budget_status}`；
  截图落在 `{module}/result/explore/{session}_step_N.png`。
- **同一条命令在同一 session 内只执行一次**（`BudgetGuard` 去重）：重复 `action+model+data`
  会被拒（`success=false, 重复命令`）。要重跑换个 session 名，或删掉
  `{module}/result/explore/session_<id>.json`。
- `action` 取值就是关键字表（`type/verify/get/evaluate/navigate/…`）；`--model ""` 表示无模型。
- 预算默认 50 步 / 300 秒，可用 `--budget-steps` / `--budget-duration` 调。
- 探索动作**不写进 case XML**（它随探索过程变化）；由 ⑥ 的后置用例把**探索产物**固化成断言。

### ⑥ run-3：后置用例段（验证探索产物 + close 收尾）

```bash
rodski run product/你的模块/case/part3_post.xml --cdp :9222
```

后置段做两件事：把 ③/⑤ 在页面上留下的状态固化成 `verify`，然后 `close` 收尾。
**`--cdp` 下 `close` 只断连、不关浏览器**（attached 语义），所以收尾不会毁掉会话——
但收尾断言要验的是**探索产物**（如 ⑤ 边界提交后的实际文本），而不是接管前的状态。

## 可执行参考

- **全自动闭环 demo**：`rodski-demo/DEMO/demo_pause_takeover/run_demo.py`
  （真实 CDP 五段：run-1 登录 → agent 接管 → run-2 verify → explore 探索步骤 → run-3 后置 + close），
  仓库根目录直接跑。
- 用例三段：`part1_login.xml`（进站登录）+ `part2_continue.xml`（verify agent 写入值 + 登录态）
  + `part3_post.xml`（verify 探索产物 + close）。

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
| `--cdp` 下用例以 close 结尾 | attached driver close = 断连，浏览器与会话都保留 → 后置收尾段**可以**用 close；真正的浏览器由启动它的那一方关闭 |
| 探索命令报 `重复命令` | 同一 session 内 `action+model+data` 去重；换 session 名或删 `result/explore/session_<id>.json` |
| 探索截图互相覆盖（都是 `..._step_1.png`） | step 编号按 session 历史续接（`start_session(step_offset=len(history))`），已修复；若在更早版本上遇到，每次换 session 名即可 |
| `explore-step` 报 `'NoneType' object has no attribute 'on'` | `evaluate` 作为本进程第一个关键字时的历史缺陷（engine 未先确保浏览器就绪），已在 `explore-step` 装配修复中一并处理；若在更早的版本上遇到，先跑一条会拉起浏览器的动作（如 `--action navigate`） |
| `connect_over_cdp` 报 `Unexpected status 400 / not a DevTools server` | 端点缺 scheme（`:9333` 不能被 connect）；用 `--cdp http://127.0.0.1:9333` 或确认 CLI 已做归一化 |
| 端口占用 / `user-data-dir` 被锁 | 换端口、换临时目录；`curl .../json/version` 探活 |
| 同一进程内两次 `sync_playwright()` | 报 asyncio 冲突；子进程/复用实例 |
| 录制/截图默认开 | run 用 `--record-mode off` 或 ConfigManager 关 `recording.enabled/auto_screenshot_*` |
| connect 到已有页面后立刻操作失败 | `page.wait_for_load_state("domcontentloaded")` |
| 无头下没 `#loginBtn` 判断 | 用可见性/文本做会话判据，别只看元素存在 |
