# Iteration 26 Session Log — 2026-04-13

本文档记录本次 Claude Code 会话中围绕架构改进的完整对话过程。

---

## 1. 阅读项目中使用 Agent LLM 判断的功能

**问题**: 阅读项目关于使用 agent llm 判断的功能都有哪些实现什么功能?

**回答**:

RodSki 项目中使用 Agent/LLM 判断能力的功能共有以下几大类：

### 一、视觉 AI 分析（Vision + LLM）

#### 1. AI 截图验证器 — `rodski/vision/ai_verifier.py`
- `AIScreenshotVerifier` 类，用 LLM 视觉能力分析截图
- `verify()`: 将截图 + 自然语言描述发给 LLM，判断是否匹配
- `verify_with_reference()`: 基于 SSIM 的图像相似度比较
- `analyze_recording()`: 用 LLM 分析录屏视频
- 支持 Claude / OpenAI GPT-4V / Qwen-VL

#### 2. 视觉定位器 — `rodski/vision/llm_analyzer.py`
- `LLMAnalyzer` 类，OmniParser + 多模态 LLM 语义识别 UI 元素
- 格式：`vision:描述文本`，LLM 根据语义描述匹配页面元素坐标
- 用于 Web 和桌面平台的元素定位

#### 3. 视觉断言 — `rodski/core/assertion/image_matcher.py` + `video_analyzer.py`
- `ImageMatcher`: OpenCV 模板匹配截图
- `VideoAnalyzer`: 从视频中提取关键帧并匹配参考图

### 二、LLM 统一客户端架构

#### 4. LLM Client — `rodski/llm/` 目录
- `LLMClient` (`client.py`): 统一的 LLM 调用客户端
- `VisionLocatorCapability` (`capabilities/vision_locator.py`): 视觉定位能力封装
- **Providers**: Claude (`claude.py`)、OpenAI/Qwen (`openai.py`)
- **Config** (`config.py`): 优先级加载：外部传入 > global_vars > yaml > 默认值

### 三、智能诊断与恢复

#### 5. 诊断引擎 — `rodski/core/diagnosis_engine.py`
- `DiagnosisEngine` 类，执行失败时自动分析
- `_try_visual_analysis()`: 调用 AI 截图验证器分析失败截图
- 输出诊断报告 + 恢复建议

#### 6. 恢复引擎 — `rodski/core/recovery_engine.py`
- 根据诊断结果执行恢复动作：wait / refresh / screenshot / recycle / retry_step / abort

### 四、测试结果 AI 审核

#### 7. LLM 测试结果审核 — `rodski/reviewers/llm_reviewer.py`
- `LLMReviewer` 类，用 LLM 审核测试结果的真实性
- 分析日志、XML 报告、截图，判断测试是否被篡改或异常

### 五、Agent 集成框架

#### 8. Agent 集成指南 — `rodski/docs/AGENT_INTEGRATION.md`
- 定义 Agent → XML(活文档) → RodSki(执行) → 结果 → Agent(分析) 的协作模式

#### 9. 多 Agent 协作示例 — `rodski/examples/agent/multi_agent_example.py`
- PlannerAgent（规划）、ExecutorAgent（执行）、AnalyzerAgent（分析）三角色协作

#### 10. Claude Code 集成 — `rodski/examples/agent/claude_code_integration.py`
- `RodSkiExecutor` 封装，让 Claude Code 直接调用 RodSki 执行用例并解析结果

#### 11. 测试用例解释器 — `rodski/core/test_case_explainer.py`
- 将 XML 测试用例转换为自然语言说明，方便 LLM Agent 理解测试意图

### 总结

| 能力类别 | 核心功能 | LLM 用途 |
|---------|---------|---------|
| 视觉验证 | AI 截图验证、录屏分析 | 多模态 LLM 判断截图是否符合预期 |
| 视觉定位 | `vision:描述` 语义定位 | LLM 根据语义描述匹配 UI 元素 |
| 智能诊断 | 失败分析 + 恢复建议 | LLM 分析失败截图给出诊断 |
| 结果审核 | 测试结果真实性审核 | LLM 判断测试结果是否可信 |
| Agent 协作 | 多 Agent 测试流水线 | Agent 规划/执行/分析全流程 |

---

## 2. 现在代码里面实现的 Agent 是使用哪个框架实现的

**问题**: 现在代码里面实现的 agent 是使用哪个框架实现的

**回答**:

**Agent 不是基于 LangChain / AutoGen / CrewAI 这类现成框架实现的**，而是：

1. **自定义 Python 类手写编排**
2. **通过 `subprocess` 调 RodSki CLI**
3. **用文件共享状态**
4. **LLM 能力直接调用官方 SDK**

### 证据

1. **Agent 集成文档定义的是"RodSki 作为执行引擎，Agent 作为外部智能层"** — `rodski/docs/AGENT_INTEGRATION.md:13`
2. **多 Agent 示例是普通 Python 类** — `PlannerAgent`、`ExecutorAgent`、`AnalyzerAgent` 没有 LangChain/AutoGen/CrewAI 的基类或运行时
3. **Agent 协作状态通过文件系统传递** — `agent_state.json`
4. **执行层是 `subprocess.run(...)`** — 不是框架内建 tool/agent runtime
5. **Claude Code 集成也是手写封装** — `RodsKiExecutor` 本质上是自定义 wrapper

### LLM 层用的是什么

1. **自己封装的统一 LLM Client** — `rodski/llm/client.py:11` `LLMClient`
2. **Provider 直接对接官方 SDK** — `ClaudeProvider` + `OpenAIProvider`
3. **视觉验证直接调用官方 SDK** — `anthropic.Anthropic(...)` / `OpenAI(...)`
4. **结果审核也是直接 OpenAI SDK** — `rodski/reviewers/llm_reviewer.py:8`

**一句话总结**: 现在代码里的 Agent 实现不是基于某个成熟 Agent 框架，而是"自定义 Python 编排 + subprocess 调 RodSki + JSON 文件共享状态"，LLM 部分则是直接用 Anthropic/OpenAI SDK。

---

## 3. 现有 Agent 架构图

**问题**: 给出现有 agent 实现架构图

**回答**:

### 架构图

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

### 代码分层

#### Agent 编排层（手写 Python 类）
- `rodski/examples/agent/multi_agent_example.py:94` — `PlannerAgent`
- `rodski/examples/agent/multi_agent_example.py:162` — `ExecutorAgent`
- `rodski/examples/agent/multi_agent_example.py:243` — `AnalyzerAgent`
- `rodski/examples/agent/claude_code_integration.py:152` — `ClaudeCodeAgent`

#### 状态共享层（JSON 文件）
- `rodski/examples/agent/multi_agent_example.py:38` — `AgentState`
- 共享状态通过 `agent_state.json` 传递

#### RodSki 调用层（subprocess）
- `subprocess.run(["rodski", "run", case_path, "--output-format", "json"])`

#### RodSki 核心执行层
- `rodski/core/keyword_engine.py` — 关键字执行
- `rodski/core/diagnosis_engine.py` — 失败诊断
- `rodski/core/recovery_engine.py` — 恢复动作
- `rodski/core/test_case_explainer.py` — 用例解释

#### LLM 能力层
- `rodski/llm/client.py:11` — `LLMClient` 统一入口
- `rodski/vision/ai_verifier.py:14` — `AIScreenshotVerifier`
- `rodski/vision/llm_analyzer.py` — 视觉定位语义分析
- `rodski/reviewers/llm_reviewer.py:11` — `LLMReviewer`

### 一次完整执行流

```
PlannerAgent → 扫描 XML 用例目录 → 生成 plan → 写入 agent_state.json
ExecutorAgent → 读取 plan → subprocess 调 rodski run → 写回 agent_state.json
AnalyzerAgent → 读取 executions → 统计成功/失败 → 输出分析报告
```

### 架构本质

**"文件驱动的轻量多 Agent 编排 + CLI 执行器模式"**

---

## 4. 设计是否合理？建议

**问题**: 设计是否合理? 你给我一些建议, 给予 rodski 的定位

**回答**:

### 判断

**如果 RodSki 的定位是"AI Agent 的执行引擎 / 活文档协议层"，当前设计总体是合理的；如果定位是"一个完整的 Agent 框架"，当前设计就不够合理。** 更建议坚定走前一种。

### 合理的部分

1. **职责边界是对的** — Agent 负责"想"，RodSki 负责"做"
2. **核心关键字收敛得不错** — type/send/verify + run 扩展逃生舱，Agent 不容易生成漂移
3. **输出已经开始"面向 Agent 消费"** — execution_summary.json、return_source 等质量指标

### 不合理的部分

#### 问题 1：定位还不统一
- README 说传统测试框架，AGENT_INTEGRATION 说 Agent 执行引擎
- 建议：只能有一个主定位

#### 问题 2：文档契约不一致，对 Agent 非常危险
- AGENT_INTEGRATION 示例用 `locator="vision:xxx"` 旧格式
- CORE_DESIGN_CONSTRAINTS 说应该用 `<location type="...">`
- Agent 会学错格式，持续生成错误 XML

#### 问题 3：Excel / XML 双叙事没收拢
- README 写 `rodski run case.xlsx`，但代码已全面 XML 化
- Agent 困惑：到底官方主格式是什么？

#### 问题 4：LLM 能力有点分散
- 有统一 LLMClient 但多处直接调 SDK
- 配置口径不统一、provider 切换逻辑分散

#### 问题 5：当前 "agent 实现" 更像示例，不像正式产品能力

### 建议的正式定位

> **面向 AI Agent 的跨平台确定性测试执行引擎 + 活文档协议层**
> Agent 负责思考，RodSki 负责稳定执行。

### 5 个核心建议

1. **不要继续把 RodSki 做成"Agent 框架"** — 它应该是 Agent 的"工具"和"协议"，不是 Agent 本身
2. **把"契约"做成第一优先级** — 唯一输入格式、唯一定位器语法、唯一结果格式、schema 校验
3. **把 AI 能力彻底降到"可选能力层"** — Core 稳定执行、AI Capabilities 增强、Agent Integration 方便调用
4. **强化"面向 Agent 的接口"** — run/validate/explain/dry-run/step trace/health check
5. **所有文档围绕"Agent 友好"重写** — 产品定位、协议文档、集成文档三层分离

### 最终判断

- 设计本身：**方向对，边界也基本对**
- 主要问题：**不是"架构错了"，而是"定位还没彻底收口，契约还没彻底统一"**
- 最适合的路线：**AI Agent 可依赖的稳定执行内核**

> 完整文档已保存至 `.pb/design/agent_architecture_review_20260413.md`

---

## 5. 改进设计与需求文档

**问题**: 针对 5 个问题给出改进设计和需求文档

用户决策：
- 问题 1：主定位 = AI Agent 执行内核 + 活文档协议
- 问题 2：契约不一致列出来逐项核对，去掉简化写法只保留多定位器写法，不兼容
- 问题 3：Excel 去掉，统一 XML，包括代码和文档
- 问题 4：LLM 基础能力统一设计
- 问题 5：Agent 示例后续单独子项目，4 点建议都同意

**回答**:

经过详细探索和设计，产出了完整的改进需求文档。

### 改进概览

| # | 问题 | 决策 | 影响范围 |
|---|------|------|---------|
| P1 | 产品定位不统一 | 主定位 = AI Agent 执行内核 + 活文档协议 | README, 所有文档 |
| P2 | 文档契约不一致 | 统一为 `<location>` 格式，代码+文档都改，不向后兼容 | model_parser.py, vision/, 所有文档和 XML |
| P3 | Excel/XML 双叙事 | 去掉 Excel，统一 XML，包括代码和文档 | requirements.txt, 文档, 测试 |
| P4 | LLM 能力分散 | 统一到 LLMClient，3 个配置合并为 1 个 llm_config.yaml | llm/, vision/, reviewers/, config/ |
| P5 | Agent 示例不是产品能力 | 移到 archive 归档，后续独立子项目 | examples/agent/ → .pb/archive/ |

### 4 个 Phase、15 个工作项

- Phase 0: 契约统一（WI-01~04）
- Phase 1: 清理历史包袱（WI-05~07）
- Phase 2: LLM 统一服务层（WI-08~12）
- Phase 3: 定位叙事统一（WI-13~15）

> 完整文档已保存至 `.pb/requirements/architecture_improvement_v6.md`

---

## 6. 分解到迭代文档

**问题**: 先分解到迭代文档从当前迭代开始往后规划迭代

**回答**:

从当前 iteration-25（v5.3.2）之后，规划了 4 个迭代：

| 迭代 | 版本 | 工时 | 内容 | 任务数 |
|------|------|------|------|--------|
| iteration-26 | v5.4.0 | 5h | 代码契约统一 + Excel/Agent 清理 | 6 个任务 |
| iteration-27 | v5.5.0 | 4h | 文档契约统一（定位器 + Excel） | 8 个任务 |
| iteration-28 | v5.6.0 | 5h | LLM 统一服务层 | 6 个任务 |
| iteration-29 | v5.7.0 | 4h | 定位叙事统一 | 6 个任务 |

合计 18h，26 个任务。

创建的文件：
- `.pb/iterations/iteration-26-29-plan.md` — 总体规划
- `.pb/iterations/iteration-26/` — README.md + tasks.md
- `.pb/iterations/iteration-27/` — README.md + tasks.md
- `.pb/iterations/iteration-28/` — README.md + tasks.md
- `.pb/iterations/iteration-29/` — README.md + tasks.md
- `.pb/iterations/README.md` — 更新总览

---

## 7. 版本号命名规则

**问题**: 版本号命名规则再 .pb 上面明确一下, 大版本.功能版本.bug修复 原则. 刚刚迭代应该是 5.x.x 继续编号

**回答**:

创建了版本号规范文档 `.pb/conventions/VERSIONING.md`：

```
格式: X.Y.Z = 大版本.功能版本.Bug修复
```

| 位 | 含义 | 何时递增 |
|----|------|---------|
| X（大版本） | 架构级变更、不兼容的 Breaking Change | 核心架构重写 |
| Y（功能版本） | 新功能、功能增强、重构、文档大改 | 每个迭代交付 |
| Z（Bug 修复） | 缺陷修复、小补丁 | 不改功能 |

版本号修正：

| 迭代 | 原版本 | 修正后 |
|------|--------|--------|
| iteration-26 | ~~v6.0.0~~ | **v5.4.0** |
| iteration-27 | ~~v6.1.0~~ | **v5.5.0** |
| iteration-28 | ~~v6.2.0~~ | **v5.6.0** |
| iteration-29 | ~~v6.3.0~~ | **v5.7.0** |

---

## 8. 使用多 Agents 模式开始开发 Iteration 26

**问题**: 使用多 agents 模式开始开发

**回答**:

### 执行过程

创建分支 `release/v5.4.0`，按任务依赖启动 3 个并行 Agent：

**第一波（并行，无文件冲突）**:
- Agent 1: T26-001 XML 迁移 — 20 个文件，~100+ 元素转换
- Agent 2: T26-004 Excel 移除 — 9 个文件清理
- Agent 3: T26-005 Agent 示例归档 — 4 文件 → archive

**第二波（顺序执行）**:
- T26-002 model_parser.py 改代码 — 删除两种旧格式解析，22 tests passed
- T26-003 vision/locator.py 废弃标记 — 36 tests passed

**最终验证**:
- T26-006 全量回归 — **1126 passed, 2 skipped, 3 xfailed, 0 failed**

### 格式审计结果

| 审计项 | 结果 |
|--------|------|
| `locator="..."` XML 属性 | 0 残留 |
| `xlsx` / `openpyxl` Python 引用 | 0 残留 |
| `type="id" value="..."` 简化格式 | 0 残留 |
| `rodski/examples/agent/` 目录 | 已删除 |

### Iteration 26 完成状态

| 任务 | 状态 |
|------|------|
| T26-001 XML 迁移 | ✅ |
| T26-002 model_parser 改代码 | ✅ |
| T26-003 vision/locator 废弃标记 | ✅ |
| T26-004 Excel 移除 | ✅ |
| T26-005 Agent 示例归档 | ✅ |
| T26-006 全量回归 | ✅ |

> 实施记录已保存至 `.pb/iterations/iteration-26/record.md`
