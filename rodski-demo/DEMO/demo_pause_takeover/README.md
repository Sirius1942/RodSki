# demo_pause_takeover

演示 **「暂停 → Agent 接管页面 → 继续」**（RodSki「暂停接管 / checkpoint 交接」工作流）：

固定用例跑到测试站点页面后，让 **外部 AI Agent**（Claude Code / Codex / 任意 playwright 驱动的
Agent）在**同一浏览器会话**上判断页面内容、操作 1–2 个按钮，RodSki 再继续执行后续验证步骤。

## 实现方式：CDP 共享浏览器、双 run 交接（无同步暂停原语）

RodSki 的运行时控制（`RuntimeCommandQueue.pause/resume`）只在**步骤边界**生效、且命令来自
**框架内** controller 线程（见 `demo_runtime_control`），没有「从用例步骤内同步阻塞等 Agent」的
原语。因此本 demo 采用业界标准的 **CDP（Chrome DevTools Protocol）共享浏览器**方案，把一个
完整流程切成两段用例，由 Agent 在中间接管：

```
run-1  TK_P1   登录进入 dashboard          （CDP 附加共享浏览器；run 结束 driver 只断连，浏览器保活）
   ↓   自然 checkpoint
agent           connect_over_cdp 同一浏览器 → 判断页面 → 点 #navTest → 填表/选角色 → 点 #submitBtn
   ↓
run-2  TK_P2   verify Agent 写入的 #formResult + dashboard 登录态/卡片值  （全新进程再附加同一浏览器）
```

## 目录结构

```
demo_pause_takeover/
├── case/
│   ├── part1_login.xml      # TK_P1：navigate → type LoginForm L001（登录，不加 close）
│   └── part2_continue.xml   # TK_P2：verify TakeoverForm V001(subset) + verify Dashboard V001
├── model/model.xml          # LoginForm / Dashboard / TakeoverForm
├── data/
│   ├── data.sqlite          # 测试数据（init_db.py 生成）
│   ├── globalvalue.xml
│   └── init_db.py           # 幂等建库脚本
├── _run_phase.py            # 单 phase 子进程 runner（独立事件循环）
├── run_demo.py              # 三段闭环编排
└── README.md
```

## 运行

前置：被测站已在 `:8000` 运行（依赖 `demo_full/demosite`）：

```bash
python3 rodski-demo/DEMO/demo_full/demosite/app.py &   # http://localhost:8000
```

仓库根目录执行：

```bash
python3 rodski-demo/DEMO/demo_pause_takeover/data/init_db.py     # 幂等建 data.sqlite
python3 rodski-demo/DEMO/demo_pause_takeover/run_demo.py
```

预期输出（exit 0）：

```
[setup] 共享浏览器已启动 (headless, CDP http://127.0.0.1:9333)
[phase:part1_login] TK_P1: PASS
[agent] 附加共享浏览器 → title='RodSki测试样例' url=http://localhost:8000/
[agent] 判断：当前用户='admin' 总订单='3' 已完成='2' 登录表单可见=False
[agent] ✓ 判断成立：run-1 的登录态在共享浏览器中延续
[agent] 操作完成：… → #formResult='提交成功！用户名: 接管人角色: admin'
[agent] ✓ Agent 操作已作用到共享浏览器页面
[phase:part2_continue] TK_P2: PASS
结论: 暂停接管闭环通过 ✔
```

## 为什么能证明「接管真实延续」（排除空洞通过）

- `run-1` 与 `run-2` 是**两个独立 Python 子进程**，彼此没有共享任何 Python 状态；
- `run-2` 用 **CDP 附加**（`PlaywrightDriver(cdp_endpoint=...)`）到 run-1 保活的同一浏览器，
  才读到 Agent 操作产生的 `#formResult` 与已登录的 dashboard；
- 负向对照：若 `run-2` 换用**全新 launch 浏览器**，会回到登录页、`verify Dashboard` FAIL
  （实测：`formResult 期望='…接管人角色: admin', 实际=''`）→ 证明 CDP 共享是唯一通路。

## 与 runtime_control 的关系

| 维度 | `demo_runtime_control` | `demo_pause_takeover` |
|------|------------------------|-----------------------|
| 命令来源 | 框架内 controller 线程 | **外部 Agent**（任意 playwright 客户端） |
| 暂停语义 | `pause()` 在步骤边界生效 | 无同步暂停；用「自然 checkpoint + 双 run」 |
| 状态交接 | 无页面状态延续 | **同一浏览器会话**跨 run/Agent 延续 |
| 适用 | 框架级暂停/插入演示 | Agent 判断页面 + 人工/智能接管 + 继续验证 |

## 裸 CLI 形态（供 skill 文档引用）

同样机制完全可用 CLI 表达（Agent 自编导）：

```bash
# 1) 启动共享浏览器（留窗口，别关）
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 --user-data-dir=/tmp/rodski-takeover

# 2) run-1：登录到目标页（CDP 附加；结束只断连，浏览器保活）
rodski run rodski-demo/DEMO/demo_pause_takeover/case/part1_login.xml --cdp :9222

# 3) Agent 用 playwright connect_over_cdp("http://127.0.0.1:9222") 判断页面并操作
#    → contexts[0].pages[0]

# 4) run-2：同一浏览器继续验证
rodski run rodski-demo/DEMO/demo_pause_takeover/case/part2_continue.xml --cdp :9222
```

> `--cdp` 需要 RodSki ≥ v11.1.0（含 driver CDP attach + CLI `--cdp`）。详见
> `rodski-skills/rodski-skill--pause-takeover/`。
