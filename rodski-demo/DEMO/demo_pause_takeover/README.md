# demo_pause_takeover

演示 **「执行一段用例 → 暂停 → 接管（含探索步骤）→ 后置自动化用例（含 `close`）」**
（RodSki「暂停接管 / checkpoint 交接」工作流）：

固定用例跑到测试站点页面后，让 **外部 AI Agent**（Claude Code / Codex / 任意 playwright 驱动的
Agent）在**同一浏览器会话**上判断页面内容、操作按钮、执行探索类测试步骤，RodSki 再收回控制权
执行后置自动化步骤并 `close` 收尾。

## 实现方式：CDP 共享浏览器、多 run 交接（无同步暂停原语）

RodSki 的运行时控制（`RuntimeCommandQueue.pause/resume`）只在**步骤边界**生效、且命令来自
**框架内** controller 线程（见 `demo_runtime_control`），没有「从用例步骤内同步阻塞等 Agent」的
原语。因此本 demo 采用业界标准的 **CDP（Chrome DevTools Protocol）共享浏览器**方案，把一个
完整流程切成若干段用例/探索步骤，由 Agent 在中间接管：

```
run-1  TK_P1   登录进入 dashboard          （CDP 附加共享浏览器；run 结束 driver 只断连，浏览器保活）
   ↓   自然 checkpoint ——「暂停」点：用例跑完，页面停在被测站上
agent          接管段 A：connect_over_cdp 同一浏览器 → 判断页面 → 点 #navTest → 填表/选角色 → #submitBtn
   ↓
run-2  TK_P2   自动化用例收回控制权：verify Agent 写入的 #formResult        （全新进程附加同一浏览器）
   ↓
explore        接管段 B：探索类测试步骤——用**真实 CLI** 在同一条会话上逐条发起、逐条留证：
                 rodski explore-step --cdp :9333 --action type --model TakeoverForm --data E001
                 （边界输入：用户名留空 + 选「用户」后提交）
                 rodski explore-step ... --action get        → 读回表单各元素当前文本
                 rodski explore-step ... --action evaluate   → 读模型盲区 #resultId
   ↓
run-3  TK_P3   后置自动化用例段：verify 探索产物（严格模式）+ verify 登录态 + **close 收尾**
                 ← 附加模式下 close 只断连，浏览器仍存活；由编排进程（拥有者）最终关闭
```

## 目录结构

```
demo_pause_takeover/
├── case/
│   ├── part1_login.xml      # TK_P1：navigate → type LoginForm L001（登录，不加 close）
│   ├── part2_continue.xml   # TK_P2：verify TakeoverForm V001(subset) + verify Dashboard V001
│   └── part3_post.xml       # TK_P3：verify TakeoverForm V002(subset) + verify Dashboard V001 + close
├── model/model.xml          # LoginForm / Dashboard / TakeoverForm / NavMenu
├── data/
│   ├── data.sqlite          # 测试数据（init_db.py 生成）
│   ├── globalvalue.xml
│   └── init_db.py           # 幂等建库脚本
├── _run_phase.py            # 单 phase case 子进程 runner（独立事件循环）
├── _run_explore.py          # 单条探索步骤子进程 runner（走真实 `rodski explore-step` CLI）
├── run_demo.py              # 五段闭环编排
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
[phase:part2_continue] TK_P2: PASS
[explore 1/3] 边界输入：用户名留空 + 选择角色「用户」后提交
       success=True url=http://localhost:8000/
       return_value={'username': '', 'role': 'select【user】', 'submitBtn': 'click', 'formResult': ''}
       screenshot=rodski-demo/DEMO/demo_pause_takeover/result/explore/takeover_demo_step_1.png
[explore 2/3] 采集证据：读取功能测试表单各元素当前文本
       return_value={..., 'formResult': '提交成功！用户名: 角色: user'}
       screenshot=.../takeover_demo_step_2.png
[explore 3/3] 模型盲区：evaluate 读模型未覆盖的 #resultId
       return_value=RID-anonymous-user
       screenshot=.../takeover_demo_step_3.png
[phase:part3_post] TK_P3: PASS
[teardown] ✓ 后置用例的 close 未关闭共享浏览器（CDP 附加模式 close = 断连）
结论: 「用例段 → 暂停 → 接管（含探索步骤）→ 后置用例 + close」闭环通过 ✔
```

## 为什么能证明「接管真实延续」（排除空洞通过）

- `run-2` / 探索步骤 / `run-3` 都是**独立 Python 子进程**，彼此没有共享任何 Python 状态；
- 它们用 **CDP 附加**（`PlaywrightDriver(cdp_endpoint=...)`）到 run-1 保活的同一浏览器，
  才读到前一段留下的 `#formResult`、探索段写入的页面状态与已登录的 dashboard；
- 负向对照：若换成**全新 launch 浏览器**，会回到登录页、`verify Dashboard` FAIL
  （实测：`formResult 期望='…接管人角色: admin', 实际=''`）→ 证明 CDP 共享是唯一通路。
- 收尾断言：后置用例执行 `close` 之后，编排进程检查 `shared.is_connected()` 仍为真
  → 证明附加模式下的 `close` 没有把共享会话关掉。

## 探索步骤为什么走 `explore-step` 而不是直接写 playwright

接管段 A 是「看一眼页面、点两下」；接管段 B 是**探索**——边界输入、探测未知界面、采集页面
实际值。后者用 `rodski explore-step` 的价值在于：

| | 接管段 A（纯 playwright） | 接管段 B（`explore-step`） |
|---|---|---|
| 定位/动作 | 自己写选择器与 API | 复用 model.xml + 数据表动作语法（`click` / `select【值】`…） |
| 证据 | 自己 print | 框架返回 `{success, evidence:{screenshot,url,return_value,browser_errors}}` |
| 会话/预算 | 自己管 | `ExploreSession` 落盘 + `BudgetGuard` 预算与去重 |
| 适用 | 自由操作 | 探索动作也要进框架证据链、要可复现 |

> 同一 session 内 `action+model+data` 会被去重；重跑换 session 名或删
> `result/explore/session_<id>.json`（`run_demo.py` 每次运行前自动清理）。

## 与 runtime_control 的关系

| 维度 | `demo_runtime_control` | `demo_pause_takeover` |
|------|------------------------|-----------------------|
| 命令来源 | 框架内 controller 线程 | **外部 Agent**（任意 playwright 客户端 / CLI） |
| 暂停语义 | `pause()` 在步骤边界生效 | 无同步暂停；用「自然 checkpoint + 多 run」 |
| 状态交接 | 无页面状态延续 | **同一浏览器会话**跨 run/Agent 延续 |
| 探索步骤 | 无 | `rodski explore-step --cdp`（框架执行 + 证据采集） |
| 收尾 | 用例内 `close` | 后置用例 `close`（附加模式 = 断连，会话保留） |
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

# 4) run-2：同一浏览器继续验证 Agent 操作
rodski run rodski-demo/DEMO/demo_pause_takeover/case/part2_continue.xml --cdp :9222

# 5) 探索步骤：逐条发起、逐条留证
rodski explore-step --module rodski-demo/DEMO/demo_pause_takeover --session take1 --cdp :9222 \
  --action type --model TakeoverForm --data E001 --output json
rodski explore-step --module rodski-demo/DEMO/demo_pause_takeover --session take1 --cdp :9222 \
  --action get  --model TakeoverForm --data E001 --output json

# 6) run-3：后置用例段（verify 探索产物 + close 收尾）
rodski run rodski-demo/DEMO/demo_pause_takeover/case/part3_post.xml --cdp :9222
```

> `--cdp` 需要 RodSki ≥ v11.1.0；`explore-step --cdp` 与其装配修复为本地未发布改动。
> 详见 `rodski-skills/rodski-skill--pause-takeover/`。
