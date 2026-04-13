# RodSki Agent 架构评审与建议

**日期**: 2026-04-13  
**评审范围**: RodSki 项目中所有使用 Agent/LLM 判断能力的功能模块  

---

## 一、现有 Agent 架构概览

### 1.1 架构图

```
┌───────────────────────┐
│ 外部 Agent / Claude   │
│ 负责：规划、决策、分析 │
└──────────┬────────────┘
           │
           │ 生成/选择 XML 用例、模型、数据
           ▼
┌──────────────────────────────┐
│ RodSki CLI / 执行入口         │
│ rodski run / explain / validate │
└──────────┬───────────────────┘
           │
           │ subprocess.run(...)
           ▼
┌──────────────────────────────┐
│ RodSki 核心执行引擎           │
│ keyword_engine / drivers /    │
│ parser / verify / assert      │
└──────────┬───────────────────┘
           │
           ├── 执行结果 JSON/XML
           ├── 日志 / 截图 / 上下文
           └── 失败信息
           ▼
┌──────────────────────────────┐
│ Agent 分析层                  │
│ Analyzer / ClaudeCodeAgent    │
│ 读取结果后做总结、诊断、重试建议 │
└──────────────────────────────┘
```

### 1.2 代码分层

#### Agent 编排层

手写 Python 类，不依赖第三方 Agent 框架。

- `rodski/examples/agent/multi_agent_example.py:94` — `PlannerAgent`：分析测试目录、生成执行计划
- `rodski/examples/agent/multi_agent_example.py:162` — `ExecutorAgent`：执行测试
- `rodski/examples/agent/multi_agent_example.py:243` — `AnalyzerAgent`：汇总结果、生成分析报告
- `rodski/examples/agent/claude_code_integration.py:152` — `ClaudeCodeAgent`：给 Claude Code 用的集成包装

#### 状态共享层

多 Agent 之间不是消息总线，也不是框架内存，而是本地 JSON 文件。

- `rodski/examples/agent/multi_agent_example.py:14` — 注释写明：`共享状态通过文件系统传递 (agent_state.json)`
- `rodski/examples/agent/multi_agent_example.py:38` — `AgentState`：负责读写共享状态
- `rodski/examples/agent/multi_agent_example.py:63` — `save()`
- `rodski/examples/agent/multi_agent_example.py:69` — `set_plan()`
- `rodski/examples/agent/multi_agent_example.py:73` — `add_execution()`
- `rodski/examples/agent/multi_agent_example.py:77` — `set_analysis()`

#### RodSki 调用层

Agent 不直接操作浏览器/设备，而是调用 RodSki CLI。

- `rodski/examples/agent/multi_agent_example.py:175` — `cmd = ["rodski", "run", case_path, "--output-format", "json"]`
- `rodski/examples/agent/multi_agent_example.py:182` — `subprocess.run(...)`
- `rodski/examples/agent/claude_code_integration.py:46` — `run_case()`
- `rodski/examples/agent/claude_code_integration.py:69` — 构造 `rodski run ...`
- `rodski/examples/agent/claude_code_integration.py:82` — `subprocess.run(...)`

#### RodSki 核心执行层

真正执行 UI/API/DB/断言的是 RodSki 本体。

- `rodski/docs/AGENT_INTEGRATION.md:13` — 定义了架构：`Agent → XML → RodSki → 结果 → Agent`
- `rodski/core/keyword_engine.py` — 关键字执行核心
- `rodski/core/diagnosis_engine.py` — 失败诊断
- `rodski/core/recovery_engine.py` — 恢复动作
- `rodski/core/test_case_explainer.py` — 用例解释给 Agent/人看

#### LLM 能力层

如果 Agent 需要视觉判断/语义定位/AI 审查，会走这个层。

- `rodski/llm/client.py:11` — `LLMClient`：统一入口
- `rodski/vision/ai_verifier.py:14` — `AIScreenshotVerifier`
- `rodski/vision/llm_analyzer.py` — 视觉定位语义分析
- `rodski/reviewers/llm_reviewer.py:11` — `LLMReviewer`

### 1.3 一次完整执行流

```
PlannerAgent
  → 扫描 XML 用例目录
  → 生成 plan
  → 写入 agent_state.json

ExecutorAgent
  → 读取 plan
  → subprocess 调 rodski run
  → 获取 JSON 执行结果
  → 写回 agent_state.json

AnalyzerAgent
  → 读取 executions
  → 统计成功/失败
  → 输出分析报告
```

对应代码入口：

- 规划：`rodski/examples/agent/multi_agent_example.py:100`
- 执行：`rodski/examples/agent/multi_agent_example.py:168`
- 批量执行：`rodski/examples/agent/multi_agent_example.py:217`
- 分析：`rodski/examples/agent/multi_agent_example.py:249`

### 1.4 架构本质

**"文件驱动的轻量多 Agent 编排 + CLI 执行器模式"**

- Agent 负责任务分工和决策
- RodSki 负责实际执行
- 状态靠 JSON 文件共享
- LLM 能力按需插入视觉/审查/诊断环节

---

## 二、当前 Agent 实现不依赖第三方 Agent 框架

### 结论

当前实现更像是**自研轻量 Agent 编排**，不是某个第三方 Agent 框架。

### 证据

1. **Agent 集成文档定义的是"RodSki 作为执行引擎，Agent 作为外部智能层"** — `rodski/docs/AGENT_INTEGRATION.md:13`
2. **多 Agent 示例是普通 Python 类** — 没有 LangChain/AutoGen/CrewAI 的基类或运行时
3. **Agent 协作状态通过文件系统传递** — `agent_state.json`
4. **执行层是 `subprocess.run(...)`** — 不是框架内建 tool/agent runtime
5. **Claude Code 集成也是手写封装** — `RodsKiExecutor` 本质上是自定义 wrapper

### LLM 层用的是什么

虽然 Agent 不是现成框架，但 LLM 调用层确实有统一封装：

1. **自己封装的统一 LLM Client** — `rodski/llm/client.py:11` `LLMClient`
2. **Provider 直接对接官方 SDK** — `ClaudeProvider` + `OpenAIProvider`
3. **视觉验证直接调用官方 SDK** — `anthropic.Anthropic(...)` / `OpenAI(...)`
4. **结果审核也是直接 OpenAI SDK** — `rodski/reviewers/llm_reviewer.py:8`

---

## 三、设计合理性评审

### 3.1 合理的部分

#### 职责边界是对的

`rodski/docs/AGENT_INTEGRATION.md:13-24` 已经明确写了：

- Agent 负责：探索、决策、分析
- RodSki 负责：XML 解析、操作执行、结果返回

这个边界非常好。**Agent 负责"想"，RodSki 负责"做"**。这是最适合长期演进的设计。

#### 核心关键字收敛得不错

`rodski/docs/CORE_DESIGN_CONSTRAINTS.md:14-26` 定义了三大核心关键字：`type` / `send` / `verify`，再加一个扩展逃生舱 `run`（`rodski/docs/CORE_DESIGN_CONSTRAINTS.md:53-66`）。

这很符合 Agent 场景：**让 Agent 生成尽量少、尽量稳定、尽量语义清晰的指令。** 如果关键字过多，Agent 很容易生成漂移；现在这个方向是对的。

#### 输出已经开始"面向 Agent 消费"

`rodski/docs/AGENT_INTEGRATION.md:518-555` 里已经有 `execution_summary.json` 和一些质量指标，比如：`return_source`、`context_snapshot.named`。

这说明你已经不是在做"给人看的脚本框架"，而是在做"给 Agent 可消费的执行结果协议"。这点非常关键，而且方向正确。

---

### 3.2 不合理的部分

#### 问题 1：定位还不统一

`README.md:3-16` 仍然把 RodSki 讲成一个传统关键字驱动测试框架。但 `rodski/docs/AGENT_INTEGRATION.md:13-24` 已经把它定义成 Agent 的执行引擎。

这会导致两种产品思路混在一起：

- 对人类测试工程师：它像传统自动化框架
- 对 AI Agent：它像执行内核 + 活文档协议

**建议：只能有一个主定位。**

#### 问题 2：文档契约不一致，对 Agent 非常危险

这是目前最需要优先修的。比如：

- `rodski/docs/AGENT_INTEGRATION.md:94-103` 示例里还在生成 `<element name="..." locator="..."/>`
- 但 `rodski/docs/CORE_DESIGN_CONSTRAINTS.md:181-198` 明确说应该使用 `<location type="...">值</location>`，并且 `locator` 是错误格式

这类冲突对人类还好，对 Agent 是致命的。**Agent 会学错格式，然后持续生成错误 XML。**

#### 问题 3：Excel / XML 双叙事没收拢

`README.md:29-39` 还在写 `rodski run case.xlsx`。但 Agent 集成文档里大量是 XML 工作流（`rodski/docs/AGENT_INTEGRATION.md:107-140`）。

如果 RodSki 是 Agent 执行引擎，就应该尽量有一个唯一标准输入协议。否则 Agent 侧会困惑：到底官方主格式是 Excel？还是 XML？还是 Excel 面向人、XML 面向 Agent？

#### 问题 4：LLM 能力有点分散

已经有统一入口 `rodski/llm/client.py:11-56`，方向是对的。但现在又有很多地方直接调 SDK：

- `rodski/vision/ai_verifier.py:59-101`
- `rodski/reviewers/llm_reviewer.py:8-28`
- `rodski/vision/llm_analyzer.py` 也有直接 provider 调用

这会带来几个问题：

- 配置口径不统一
- provider 切换逻辑分散
- 重试 / 限流 / 观测难统一
- 后面接入新模型会重复改很多地方

#### 问题 5：当前 "agent 实现" 更像示例，不像正式产品能力

`rodski/examples/agent/multi_agent_example.py:14` 说明共享状态就是 `agent_state.json`。而 `PlannerAgent / ExecutorAgent / AnalyzerAgent` 也都是普通 Python 类。

这作为参考示例是合理的，但如果想把它说成"RodSki 的 agent runtime"，就太轻了。

---

## 四、建议的正式定位

> **面向 AI Agent 的跨平台确定性测试执行引擎 + 活文档协议层**

或者更短一点：

> **Agent 负责思考，RodSki 负责稳定执行。**

这个定位比"通用测试框架"更有辨识度，也更符合现在的演进方向。

---

## 五、基于定位的 5 个核心建议

### 建议 1：不要继续把 RodSki 做成"Agent 框架"

不要去和 LangGraph / AutoGen / CrewAI 这种方向竞争。

RodSki 更适合做的是：

- 执行器
- 契约层
- 验证器
- 结果解释器
- 诊断器

而不是：

- 对话管理器
- 多 Agent 编排平台
- Memory 系统
- 通用 Planner 框架

**换句话说：RodSki 应该是 Agent 的"工具"和"协议"，不是 Agent 本身。**

### 建议 2：把"契约"做成第一优先级

如果真的是给 Agent 用，最重要的不是再加一个新能力，而是把契约钉死。

优先统一这些：

1. **唯一官方输入格式** — XML 还是 Excel，选一个做主协议
2. **唯一定位器语法** — `<location type="...">` 成为唯一标准
3. **唯一结果格式** — `execution_summary.json`、失败上下文、截图索引都版本化
4. **schema 校验** — 最好提供严格 validator，而不只是文档说明

Agent 最怕"看起来都能用，但其实彼此冲突"。

### 建议 3：把 AI 能力彻底降到"可选能力层"

核心执行层应该保持确定性：

- parser
- keyword engine
- driver
- result contract

而 AI/LLM 部分应该是可插拔能力：

- vision locator
- screenshot verifier
- diagnosis
- reviewer

这样产品层次会清楚：

- **Core**：稳定执行
- **AI Capabilities**：增强理解与诊断
- **Agent Integration**：方便外部 Agent 调用

### 建议 4：强化"面向 Agent 的接口"，而不是强化示例 Agent

比起继续丰富 `PlannerAgent`/`AnalyzerAgent` 示例，更建议强化这些正式能力：

- `run`
- `validate`
- `explain`
- `dry-run`
- `step trace`
- `execution_summary.json`
- `health check`
- `session` 复用能力

也就是说，**把 RodSki 做成一个特别好调用、特别好判断、特别好恢复的执行内核**。

### 建议 5：所有文档都围绕"Agent 友好"重写一遍

现在最明显的问题不是代码，而是叙事不一致。

建议文档分三层：

1. **产品定位** — RodSki 是什么，不是什么
2. **协议文档** — case/model/data/result 的唯一规范
3. **集成文档** — Claude Code / OpenCode / 自定义 Agent 如何调用

其中：示例是示例，规范是规范，不要混写。

---

## 六、最终判断

### 设计本身

**方向对，边界也基本对。**

### 主要问题

**不是"架构错了"，而是"定位还没彻底收口，契约还没彻底统一"。**

### 最适合 RodSki 的路线

不是去做"通用 Agent 框架"，而是去做：

> **AI Agent 可依赖的稳定执行内核**

这个方向一旦立住，RodSki 的价值会非常清晰：

- 对人：它是自动化执行工具
- 对 Agent：它是标准化执行器和活文档协议
