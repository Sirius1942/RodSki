# RodSki v7.0 路线图 — 优化 Agent

**版本**: v7.0  
**日期**: 2026-04-16  
**状态**: 待审批  
**前置**: 承接 `architecture_improvement_v6.md`（Phase 0-3 已收录）  
**来源**: 从 `roadmap_v7_design_review.md` 拆分，聚焦 Agent 优化方向

---

## 目录

1. [背景与目标](#1-背景与目标)
2. [Phase 4: 自研测试报告系统（对标 Allure）](#2-phase-4-自研测试报告系统对标-allure)
3. [Phase 5: Observability 与 Agent KPI 体系](#3-phase-5-observability-与-agent-kpi-体系)
4. [Phase 6: 架构补强（Agent 能力增强）](#4-phase-6-架构补强agent-能力增强)
5. [项目归属划分](#5-项目归属划分)
6. [全局依赖关系图](#6-全局依赖关系图)
7. [工作量总览](#7-工作量总览)
8. [风险分析](#8-风险分析)
9. [验证方案](#9-验证方案)

---

## 1. 背景与目标

### 1.1 v7 定位

v7 的核心目标：**让 RodSki 的 AI Agent 壳（test agent + design agent）更好用、更准确、可度量。**

刚完成了 `.claude/agents/test.md` 和 `.claude/agents/design.md` 的重新定位：
- **test agent** — 帮助测试人员编写、运行、调试 RodSki XML 用例
- **design agent** — 帮助测试人员规划测试方案、设计 Case/Model/Data 结构

两个 Agent 是 RodSki 的「AI 壳」，让测试人员更高效准确地使用框架。v7 要做的就是给这个 AI 壳提供更好的基础设施：

1. **更好的结果分析能力** — 自研报告系统，让 Agent 和用户都能看到清晰的执行结果
2. **可度量的 Agent 效能** — Observability + KPI 体系，量化 Agent 的准确率和效率
3. **更强的框架能力** — 补强关键字、流程控制、Tag 过滤，让 Agent 生成更优质的 XML

### 1.2 与 v6 的关系

v6（Phase 0-3）完成了核心架构搭建：
- Phase 0: 工程基础
- Phase 1: RuntimeContext 一等公民
- Phase 2: 驱动层对齐
- Phase 3: Agent Pipeline 增强

v7 在此基础上进一步优化 Agent 体验，不涉及 RPA 方向（RPA 推到 v8，见 `roadmap_v8_rpa.md`）。

### 1.3 v7 Phase 编号

承接 v6 的 Phase 0-3，v7 内部使用 Phase 4-6：

| Phase | 内容 | 与 Agent 优化的关系 |
|-------|------|-------------------|
| Phase 4 | 自研测试报告系统 | Agent 分析执行结果的基础能力 |
| Phase 5 | Observability + Agent KPI | 度量和优化 Agent 性能 |
| Phase 6 | 架构补强 | 让 Agent 生成更优质的 XML |

---

## 2. Phase 4: 自研测试报告系统（对标 Allure）

### 2.1 与 Agent 优化的关系

测试报告是 Agent 分析执行结果的**基础设施**。当前仅有 `result.xml` + `execution_summary.json`，Agent（test agent）在分析测试失败时只能读原始 XML，缺乏结构化的步骤级详情、截图关联、历史趋势等信息。

自研报告系统为 Agent 提供：
- **结构化步骤数据**：每步的耗时、状态、截图、Return 值，Agent 可以精准定位失败步骤
- **历史趋势数据**：Agent 可以判断失败是新增还是回归，是偶发还是持续
- **诊断修复可视化**：Agent 执行的诊断和修复过程可以被记录和展示，便于评估 Agent 效果
- **缺陷聚合信息**：相同错误的 case 自动聚合，Agent 可以批量修复

### 2.2 背景

**现状**：仅有 `result.xml` + `execution_summary.json`，无任何可视化。

**目标**：自研 HTML 报告系统，参考 Allure Report 核心功能，零外部依赖。

**为什么不直接用 Allure**：
1. Allure 需要 Java 运行时 + allure-commandline，增加部署复杂度
2. Allure 的数据格式（JSON + attachments）需要适配层
3. RodSki 的 XML 三阶段容器、Return 链、Model/Data 绑定是独特概念，Allure 无法原生展示
4. 自研可完全控制，后续支持 Agent 诊断结果等定制内容

### 2.3 功能矩阵（对标 Allure）

| Allure 功能 | 自研对标 | 优先级 | 说明 |
|-------------|---------|--------|------|
| **Overview Dashboard** | 总览仪表板 | P0 | 通过率饼图、耗时分布、趋势折线图 |
| **Suites 视图** | 按 Project/Module 分组 | P0 | 树形结构，展开到 case 级 |
| **Test Case Detail** | 用例详情页 | P0 | 三阶段时间线、每步状态、截图、日志 |
| **步骤时间线** | Step Timeline | P0 | 可视化三阶段（pre/test/post）+ 每步耗时 |
| **失败截图内联** | 截图查看器 | P0 | 失败步骤自动内联截图，支持全屏查看 |
| **Categories** | 错误分类 | P1 | 按 Agent 诊断类别分组（CASE/ENV/PRODUCT） |
| **历史趋势** | 多次运行趋势 | P1 | 通过率趋势、耗时趋势、新增/修复缺陷 |
| **Retry 可视化** | 重试链路 | P1 | 展示 Agent 自愈过程（原始失败->修复->重试结果） |
| **Environment** | 环境信息面板 | P1 | OS/Browser/Driver/RodSki 版本 |
| **Attachments** | 附件系统 | P1 | 日志文件、XML 源文件、HTTP 请求/响应 |
| **Behaviors (BDD)** | Model/Data 视图 | P2 | 按 Model 和 DataTable 组织视图 |
| **Timeline** | 并行时间线 | P2 | 多 case 并行执行时的甘特图 |
| **Defects** | 缺陷聚合 | P2 | 相同错误消息的 case 自动聚合 |
| **Flaky Tests** | 不稳定用例 | P2 | 标记多次运行结果不一致的 case |

### 2.4 工作项

#### WI-40: 报告数据模型与收集器 [M]

**新建文件**：

```
rodski/report/
├── __init__.py
├── collector.py        # 执行数据收集器（hook 到 SKIExecutor）
├── data_model.py       # 报告数据模型
├── history.py          # 历史数据管理
└── trend.py            # 趋势计算
```

**数据模型**：

```python
@dataclass
class ReportData:
    # 总览
    run_id: str                     # 唯一运行 ID
    start_time: datetime
    end_time: datetime
    duration: float
    environment: EnvironmentInfo    # OS, browser, versions

    # 统计
    summary: RunSummary             # total, passed, failed, skipped, error
    
    # 用例详情
    cases: list[CaseReport]

@dataclass
class CaseReport:
    case_id: str
    title: str
    description: str
    component_type: str             # 界面/接口/数据库
    status: str                     # PASS/FAIL/SKIP/ERROR
    duration: float
    tags: list[str]
    
    # 三阶段
    pre_process: PhaseReport
    test_case: PhaseReport
    post_process: PhaseReport

@dataclass
class PhaseReport:
    steps: list[StepReport]
    status: str
    duration: float

@dataclass 
class StepReport:
    index: int
    action: str                     # 关键字
    model: str
    data: str
    status: str                     # ok/fail/skip
    duration: float
    screenshot: Optional[str]       # 截图路径（base64 或文件路径）
    log: str                        # 步骤日志
    return_value: Any               # Return 值
    error: Optional[str]            # 错误信息
    
    # Agent 诊断信息（如有）
    diagnosis: Optional[dict]       # {category, root_cause, fix_applied}
    retry_history: list[dict]       # [{attempt, fix, result}, ...]
```

**收集器实现**：
- Hook 到 `SKIExecutor.execute_case()` 和 `KeywordEngine.execute()` 的入口和出口
- 自动收集每步的开始/结束时间、Return 值、截图
- 不影响执行性能（异步写入）

**验证**：`pytest rodski/tests/unit/test_report_collector.py`

---

#### WI-41: HTML 报告生成器 [L]

**依赖**：WI-40

**新建文件**：

```
rodski/report/
├── generator.py        # 报告生成引擎
├── templates/          # HTML 模板（内嵌，无外部依赖）
│   ├── base.html       # 基础布局（含 CSS + JS 内联）
│   ├── overview.html   # 总览仪表板
│   ├── suite.html      # 套件视图
│   ├── case.html       # 用例详情
│   └── components/     # 可复用组件
│       ├── chart.html      # 图表组件（Canvas/SVG）
│       ├── timeline.html   # 时间线组件
│       ├── screenshot.html # 截图查看器
│       └── table.html      # 数据表组件
└── assets/             # 内联资源
    ├── style.css       # 样式表
    └── report.js       # 交互逻辑
```

**技术选型**（零外部依赖）：
- 模板引擎：Python `string.Template` 或内嵌 f-string（不引入 Jinja2）
- 图表：纯 SVG 生成（饼图、柱状图、折线图，Python 端计算坐标）
- 交互：原生 JavaScript（折叠/展开、截图全屏、筛选）
- 样式：内联 CSS（单文件 HTML，无外部引用）
- 截图：Base64 内联到 HTML（或相对路径引用）

**报告结构**：

```
report_20260416_143000/
├── index.html              # 主入口（总览 + 导航）
├── suites/
│   ├── DEMO_demo_site.html # 按 Module 分组
│   └── ...
├── cases/
│   ├── c001.html           # 用例详情页
│   └── ...
├── assets/
│   └── screenshots/        # 截图文件
└── data/
    └── report_data.json    # 原始数据（供外部工具消费）
```

**单文件模式**：`--single-file` 参数生成单个 HTML（所有截图 base64 内联，便于邮件分发）。

**验证**：生成报告 + 浏览器打开验证

---

#### WI-42: 历史趋势与缺陷聚合 [M]

**依赖**：WI-40

**新建文件**：
- `rodski/report/history.py` -- 历史数据管理
- `rodski/report/trend.py` -- 趋势计算

**历史存储**：

```
result/
├── history.json        # 历史摘要索引
├── run_20260416_1430/
│   ├── result.xml
│   ├── report_data.json
│   └── report/
└── run_20260416_1500/
    └── ...
```

**趋势计算**：
- 通过率趋势（最近 N 次运行）
- 平均耗时趋势
- 新增失败 / 修复成功统计
- 不稳定用例识别（同一 case 在最近 N 次中状态不一致）

**缺陷聚合**：
- 按错误消息 fingerprint（去除动态部分后取哈希）聚合
- 展示影响的 case 列表、首次出现时间、最近出现时间

---

#### WI-43: CLI 集成 [S]

**依赖**：WI-41

**改动文件**：
- `rodski/rodski_cli/run.py` -- `rodski run` 新增 `--report` 参数
- `rodski/rodski_cli/` -- 新增 `report.py` 子命令

**CLI 接口**：

```bash
# 执行时自动生成报告
rodski run case/ --report html

# 从已有 result 生成报告
rodski report generate result/run_20260416_1430/

# 查看历史趋势
rodski report trend --last 10

# 生成单文件报告（便于邮件发送）
rodski report generate result/ --single-file --output report.html
```

**验证**：端到端执行 + 报告生成

---

#### WI-44: Agent 诊断/修复可视化 [S]

**依赖**：WI-41, WI-40

**目标**：报告中展示 Agent 自愈过程（仅当由 rodski-agent 驱动执行时）。

**展示内容**：
- 原始失败：哪步失败、错误信息、截图
- 诊断结果：LLM 分析的类别、根因、置信度
- 修复操作：应用了什么修复（wait/locator/data/navigation）
- 修复后结果：重试是否成功
- Token 消耗：诊断和修复消耗的 LLM token 数

**数据来源**：`execution_summary.json` 中 Agent 写入的诊断字段

---

### 2.5 Phase 4 改动汇总

| WI | 名称 | 大小 | 依赖 |
|----|------|------|------|
| WI-40 | 报告数据模型与收集器 | M | 无 |
| WI-41 | HTML 报告生成器 | L | WI-40 |
| WI-42 | 历史趋势与缺陷聚合 | M | WI-40 |
| WI-43 | CLI 集成 | S | WI-41 |
| WI-44 | Agent 诊断修复可视化 | S | WI-41, WI-40 |

---

## 3. Phase 5: Observability 与 Agent KPI 体系

### 3.1 与 Agent 优化的关系

没有度量就没有优化。当前 Agent（test agent + design agent）的效果完全凭主观感受，无法回答：
- Agent 生成的 XML 首次通过率是多少？
- 自动修复成功率多高？每次修复消耗多少 token/钱？
- Agent 比手工写用例快多少？质量差距在哪？

Observability + KPI 体系让 Agent 效能可度量、可优化：
- **Execution Trace** 提供细粒度的执行数据，Agent 和开发者可以分析性能瓶颈
- **LLM Token 计量** 让每次 Agent 调用的成本透明
- **KPI 评估框架** 建立 Agent 效能基线，持续跟踪改进效果
- **对比实验框架** 量化 RodSki Agent 相对于通用 Agent 的优势

### 3.2 背景

**现状**：
- 仅有结构化日志 + performance decorator
- LLM 调用没有 token 计量
- 无法量化 Agent 效能（生成质量、修复成功率、成本效率）

**目标**：建立完整的可观测性和 Agent KPI 量化体系。

### 3.3 工作项

#### WI-50: Execution Trace 层 [M]

**新建文件**：

```
rodski/observability/
├── __init__.py
├── tracer.py           # 轻量 trace 实现（不依赖 OpenTelemetry）
├── span.py             # Span 数据结构
├── metrics.py          # 指标收集
└── exporter.py         # 导出器（JSON / 报告系统）
```

**Trace 结构**：

```
trace: run_20260416_1430
├── span: case_c001 (duration=12.3s)
│   ├── span: pre_process (2.1s)
│   │   └── span: step_navigate (2.0s)
│   ├── span: test_case (8.5s)
│   │   ├── span: step_type (3.2s)
│   │   │   ├── span: locate_element (0.5s, locator=id, retries=0)
│   │   │   └── span: driver_type_text (0.3s)
│   │   ├── span: step_verify (2.1s)
│   │   └── span: step_send (3.2s)
│   │       └── span: http_request (2.8s, url=..., status=200)
│   └── span: post_process (1.7s)
│       └── span: step_close (1.7s)
└── span: case_c002 ...
```

**指标收集**（自动）：

| 指标 | 类型 | 说明 |
|------|------|------|
| `step_duration_seconds` | histogram | 每步耗时分布 |
| `locate_retry_count` | counter | 定位重试次数 |
| `http_request_duration` | histogram | API 请求耗时 |
| `case_status` | counter | 按状态计数 |
| `driver_action_duration` | histogram | 驱动操作耗时 |

**Hook 点**（装饰器方式，非侵入）：

```python
@trace_span("keyword_execute")
def _kw_type(self, model_name, data_id):
    ...
```

**导出**：
- JSON 文件（供报告系统消费）
- 兼容 OpenTelemetry JSON 格式（未来可对接 Jaeger/Grafana）

---

#### WI-51: LLM Token 计量 [S]

**改动文件**：
- `rodski/llm/client.py` -- 包装每次调用，记录 token
- `rodski-agent/src/rodski_agent/common/llm_bridge.py` -- 同上

**记录内容**：

```python
@dataclass
class LLMCallRecord:
    timestamp: datetime
    provider: str           # claude / openai
    model: str              # claude-sonnet-4-20250514
    purpose: str            # diagnosis / design / vision_locate / ...
    input_tokens: int
    output_tokens: int
    total_tokens: int
    duration_ms: int
    cost_usd: float         # 按公开价格估算
    success: bool
    error: Optional[str]
```

**汇总报告**：

```json
{
  "llm_summary": {
    "total_calls": 15,
    "total_tokens": 28500,
    "total_cost_usd": 0.42,
    "by_purpose": {
      "diagnosis": {"calls": 3, "tokens": 8000, "cost": 0.12},
      "design": {"calls": 5, "tokens": 15000, "cost": 0.22},
      "vision_locate": {"calls": 7, "tokens": 5500, "cost": 0.08}
    }
  }
}
```

---

#### WI-52: Agent KPI 评估框架 [M]

**依赖**：WI-50, WI-51

**新建文件**：

```
rodski-agent/src/rodski_agent/common/kpi.py     # KPI 计算器
rodski-agent/src/rodski_agent/common/benchmark.py # 基准测试运行器
```

**KPI 指标体系**：

```
一、效率指标
├── T_design        -- 从需求到可执行用例的时间（秒）
├── T_execute       -- 单 case 平均执行时间（秒）
├── T_fix           -- 失败到自动修复成功的时间（秒）
├── Token_per_case  -- 每个用例的总 token 消耗
├── Token_per_fix   -- 每次修复的 token 消耗
└── Cost_per_case   -- 每个用例的 LLM 成本（USD）

二、质量指标
├── First_pass_rate     -- 首次生成即通过率（%）
├── Valid_assertion_pct -- 有效断言比例（非空断言 / 总断言）
├── False_positive_pct  -- 假阳率（通过但实际有 bug 的 case）
├── Flakiness_rate      -- 同一 case 多次执行结果不一致率
├── Coverage_score      -- 对需求的覆盖评分（LLM 辅助评估）
└── XML_validity_rate   -- 生成的 XML 首次通过 XSD 校验率

三、自愈指标
├── MTTR_auto           -- 自动修复的平均恢复时间（秒）
├── MTTR_manual         -- 需人工介入的平均恢复时间
├── Fix_success_pct     -- 自动修复成功率（%）
├── Fix_by_strategy     -- 各修复策略的成功率分布
└── Churn_rate          -- 用例因 UI 变更需修改的频率
```

**基准测试运行器**：

```bash
# 运行 KPI 基准测试（使用 rodski-demo 标准用例集）
rodski-agent benchmark run --suite rodski-demo/DEMO/

# 对比两次运行
rodski-agent benchmark compare run_001 run_002

# 生成 KPI 报告
rodski-agent benchmark report --last 5
```

**基准测试集要求**：
- 至少 10 个 Web UI 用例（覆盖 type/verify/navigate/wait）
- 至少 5 个 API 用例（覆盖 send/verify/set/get）
- 至少 3 个 DB 用例
- 每个用例标注"已知正确结果"，用于验证 Agent 生成质量

---

#### WI-53: Test Agent vs 通用 Agent 对比实验框架 [S]

**依赖**：WI-52

**目标**：提供标准化实验框架，量化对比 rodski-agent 与通用 Agent（如 Claude 直写 Playwright 代码）的效能差异。

**新建文件**：
- `rodski-agent/benchmark/comparison.py`

**实验设计**：

| 维度 | rodski-agent 测量方法 | 通用 Agent 测量方法 |
|------|---------------------|-------------------|
| 生成速度 | T_design（需求->XML） | T_codegen（需求->代码） |
| 首次成功率 | XML valid + 执行通过 | 代码编译+运行通过 |
| 维护成本 | UI 变更后修改行数 | UI 变更后修改行数 |
| Token 消耗 | WI-51 计量 | 同等计量 |
| 自愈能力 | Fix_success_pct | 无（人工） |
| 跨平台 | 换 driver_type 行数 | 重写代码行数 |

**输出**：对比报告（Markdown 表格 + 图表）

---

### 3.4 Phase 5 改动汇总

| WI | 名称 | 大小 | 依赖 |
|----|------|------|------|
| WI-50 | Execution Trace 层 | M | 无 |
| WI-51 | LLM Token 计量 | S | 无 |
| WI-52 | Agent KPI 评估框架 | M | WI-50, WI-51 |
| WI-53 | Agent vs 通用 Agent 对比 | S | WI-52 |

---

## 4. Phase 6: 架构补强（Agent 能力增强）

### 4.1 与 Agent 优化的关系

这些架构补强直接提升 Agent 生成 XML 和管理用例的能力：

- **Agent 记忆层**：Agent 从历史修复模式中学习，不再重复犯同样的错误，自愈成功率提升
- **set/get 一等公民化**：简化 Agent 生成的 XML，减少脆弱的 `${Return[-1]}` 索引
- **Case Tag 选择性执行**：Agent 可以按 tag 精准运行子集，测试管理更灵活
- **两层 if/else + elif**：更强的流程控制能力，让 Agent 生成的用例能处理更复杂的业务场景
- **Network Interception**：更完整的测试能力，Agent 可以生成 Mock API 的测试用例

### 4.2 工作项

#### WI-60: Agent 记忆层（History-based Self-healing）[M]

**目标**：Execution Agent 和 Design Agent 基于历史修复模式提升自愈成功率。

**新建文件**：
- `rodski-agent/src/rodski_agent/common/memory_store.py`

**存储结构**（SQLite）：

```sql
CREATE TABLE fix_patterns (
    id INTEGER PRIMARY KEY,
    failure_pattern TEXT,     -- 失败模式（诊断类别 + 关键字 + 错误特征）
    fix_strategy TEXT,        -- 修复策略 JSON
    success_count INTEGER,    -- 成功次数
    fail_count INTEGER,       -- 失败次数
    confidence REAL,          -- 计算置信度: success / (success + fail)
    last_used TIMESTAMP
);

CREATE TABLE app_models (
    id INTEGER PRIMARY KEY,
    app_name TEXT,            -- 应用名
    window_title TEXT,        -- 窗口标题
    model_xml TEXT,           -- 自动生成的 model XML
    screenshot_path TEXT,     -- 参考截图
    last_verified TIMESTAMP,  -- 最后验证时间
    reliability REAL          -- 可靠性评分
);
```

**改动文件**：
- `rodski-agent/src/rodski_agent/execution/nodes.py` -- `diagnose` 和 `apply_fix` 节点增加记忆查询
- `rodski-agent/src/rodski_agent/execution/fixer.py` -- 修复策略选择时优先查历史

**使用场景**：

| 场景 | 查询 | 效果 |
|------|------|------|
| 修复阶段 | 查 fix_patterns 中匹配的修复 | 优先尝试高置信度修复 |
| 设计阶段 | 查 app_models 中已知的应用模型 | 复用 model XML，减少探索 |
| 回顾阶段 | 统计成功率、耗时趋势 | 识别退化和优化点 |

**记忆淘汰策略**：
- fix_patterns: `confidence < 0.3 AND last_used < 30d` -> 自动清理
- app_models: `last_verified < 7d` -> 标记 stale，下次使用前重新验证

**效果**：预期自愈成功率提升 30-50%。

**验证**：`pytest rodski-agent/tests/test_memory_store.py`

---

#### WI-61: set/get 一等公民化 [S]

**目标**：推广命名变量为主要数据传递方式，弱化 Return 索引。Agent 生成 XML 时使用 set/get 命名变量，比 `${Return[-3]}` 更可读、更稳定。

**改动文件**：
- `rodski/docs/TEST_CASE_WRITING_GUIDE.md` -- 用例编写指南推荐 set/get 优先
- `rodski/docs/AGENT_INTEGRATION.md` -- Agent 指南推荐 set/get
- rodski-agent prompts -- 生成 XML 时优先使用 set/get

**不做**：不移除 Return 索引（向后兼容），仅在文档和 Agent Prompt 中降低其权重。

---

#### WI-62: Network Interception 支持 [M]

**目标**：PlaywrightDriver 暴露 `route()` 能力，让 Agent 可以生成 Mock API 的测试用例。

**新增内置函数**（通过 `run` 关键字）：

```xml
<!-- Mock API 响应 -->
<test_step action="run" model="" data="mock_route('/api/users', status=200, body='[]')"/>

<!-- 等待特定网络请求完成 -->
<test_step action="run" model="" data="wait_for_response('/api/login', timeout=10)"/>

<!-- 清除所有 mock -->
<test_step action="run" model="" data="clear_routes()"/>
```

**新建文件**：
- `rodski/builtins/network_ops.py` -- PlaywrightDriver 网络操作封装

---

#### WI-63: Case Tag 与选择性执行 [S]

**目标**：case XML 支持 tags，CLI 支持按 tag/priority 过滤。Agent 可以精准选择要运行的用例子集。

**改动**：

```xml
<case id="c001" execute="是" tags="smoke,login" priority="P0" title="...">
```

```bash
rodski run case/ --tags smoke --priority P0
rodski run case/ --tags "smoke,regression" --exclude-tags "slow"
```

**改动文件**：
- `rodski/schemas/case.xsd` -- case 元素新增 tags, priority 属性
- `rodski/core/case_parser.py` -- 解析新属性
- `rodski/core/ski_executor.py` -- 执行前过滤
- `rodski/rodski_cli/run.py` -- CLI 新增过滤参数

---

#### WI-64: 两层 if/else + elif 支持 [S]

**目标**：支持两层嵌套和 elif，让 Agent 生成的用例能处理更复杂的条件分支场景。

```xml
<if condition="element_exists(#dialog)">
  <test_step action="type" model="Dialog" data="D001"/>
  <if condition="${Return[-1].status == 'error'}">
    <test_step action="screenshot" data="error.png"/>
  </if>
<elif condition="text_contains('超时')">
  <test_step action="wait" model="" data="3"/>
<else>
  <test_step action="close" model="" data=""/>
</else>
```

**限制**：最大 2 层嵌套（不支持 3 层及以上）。

**改动文件**：
- `rodski/schemas/case.xsd` -- 更新 if/elif/else 结构
- `rodski/core/dynamic_executor.py` -- 支持嵌套评估

---

### 4.3 Phase 6 改动汇总

| WI | 名称 | 大小 | 依赖 |
|----|------|------|------|
| WI-60 | Agent 记忆层 | M | 无 |
| WI-61 | set/get 一等公民化 | S | 无 |
| WI-62 | Network Interception | M | 无 |
| WI-63 | Case Tag 选择性执行 | S | 无 |
| WI-64 | 两层 if/else + elif | S | 无 |

---

## 5. 项目归属划分

### 5.1 划分原则

> 详见 `.pb/conventions/PROJECT_BOUNDARY.md`

**三条硬约束**：

1. **单向依赖**：rodski-agent 依赖 rodski，反过来不成立
2. **rodski 独立可执行**：不装 rodski-agent 也能完整执行所有关键字
3. **LLM 配置不共享**：两个项目各自管理自己的 LLM 配置

### 5.2 全量归属表

| WI | 名称 | 项目 | 说明 |
|----|------|------|------|
| | **Phase 4: 自研报告系统** | | |
| WI-40 | 报告数据模型与收集器 | **rodski** | 新建 `report/collector.py` + `report/data_model.py` |
| WI-41 | HTML 报告生成器 | **rodski** | 新建 `report/generator.py` + `report/templates/` |
| WI-42 | 历史趋势与缺陷聚合 | **rodski** | 新建 `report/history.py` + `report/trend.py` |
| WI-43 | 报告 CLI 集成 | **rodski** | `rodski_cli/run.py` 新增 `--report` + 新建 `rodski_cli/report.py` |
| WI-44 | Agent 诊断修复可视化 | **rodski** | 报告模板条件渲染：有 diagnosis 字段就展示，没有就不展示 |
| | **Phase 5: Observability + KPI** | | |
| WI-50 | Execution Trace 层 | **rodski** | 新建 `observability/tracer.py`，装饰器方式 hook |
| WI-51 | LLM Token 计量 | **BOTH** | 各自独立实现。rodski: `llm/client.py`；rodski-agent: `common/llm_bridge.py` |
| WI-52 | Agent KPI 评估框架 | **rodski-agent** | 新建 `common/kpi.py` + `common/benchmark.py` |
| WI-53 | Agent vs 通用 Agent 对比 | **rodski-agent** | 新建 `benchmark/comparison.py` |
| | **Phase 6: 架构补强** | | |
| WI-60 | Agent 记忆层 | **rodski-agent** | 新建 `common/memory_store.py` + 接入 execution nodes |
| WI-61 | set/get 一等公民化 | **BOTH** | rodski: 文档推荐；rodski-agent: prompts 调整 |
| WI-62 | Network Interception | **rodski** | 新建 `builtins/network_ops.py` |
| WI-63 | Case Tag 选择性执行 | **rodski** | schema + parser + executor + CLI |
| WI-64 | 两层 if/else + elif | **rodski** | schema + dynamic_executor |

### 5.3 按项目汇总

#### rodski 核心（10 个独立 WI + 1 个 BOTH 中 rodski 侧）

```
Phase 4: WI-40, WI-41, WI-42, WI-43, WI-44         (5 个)
Phase 5: WI-50                                       (1 个，Trace)
Phase 6: WI-62, WI-63, WI-64                        (3 个)
BOTH 中 rodski 侧: WI-51, WI-61                     (2 个)
```

**rodski 核心改动范围**：
- `report/` -- 全新模块（collector / generator / templates / history / trend）
- `observability/` -- 全新模块（tracer / span / metrics）
- `builtins/` -- network_ops
- `schemas/` -- case.xsd (tags + elif)
- `core/` -- case_parser (tags) + dynamic_executor (elif) + ski_executor (tag filter)
- `llm/client.py` -- token 记录包装（可选层）
- `docs/` -- set/get 优先推荐
- `rodski_cli/` -- report 子命令 + --report/--tags 参数

#### rodski-agent 智能层（3 个独立 WI + 1 个 BOTH 中 agent 侧）

```
Phase 5: WI-52, WI-53                              (2 个，KPI/对比)
Phase 6: WI-60                                      (1 个，记忆层)
BOTH 中 agent 侧: WI-51, WI-61                     (2 个)
```

**rodski-agent 改动范围**：
- `common/memory_store.py` -- 全新（SQLite 持久化）
- `common/kpi.py` + `common/benchmark.py` -- 全新
- `common/llm_bridge.py` -- token 记录
- `execution/nodes.py` + `execution/fixer.py` -- 接入 Memory Store
- `benchmark/comparison.py` -- 全新
- `design/prompts.py` -- 优先生成 set/get 而非 Return 索引

---

## 6. 全局依赖关系图

```
Phase 0-3 (v6.0, 已完成)
    WI-01 ~ WI-15

Phase 4 (自研报告系统) <- 全部 rodski:
    WI-40 (数据模型) --+-- WI-41 (HTML 生成) --+-- WI-43 (CLI)
                       |                        +-- WI-44 (Agent 可视化)
                       +-- WI-42 (历史趋势)

Phase 5 (Observability + KPI) <- 混合:
    WI-50 (Trace, rodski) --+
    WI-51 (Token, BOTH) ----+-- WI-52 (KPI, agent) -- WI-53 (对比, agent)

Phase 6 (架构补强) <- 混合:
    WI-60 (Agent 记忆, agent)    <- 独立
    WI-61 (set/get, BOTH)        <- 独立
    WI-62 (Network, rodski)      <- 独立
    WI-63 (Tag, rodski)          <- 独立
    WI-64 (elif, rodski)         <- 独立
```

**推荐执行顺序**：
1. Phase 4（报告系统）-- 为后续度量提供数据基础
2. Phase 5（Observability + KPI）-- 部分依赖 Phase 4 的数据模型
3. Phase 6（架构补强）-- 各 WI 独立，可穿插执行

**并行开发建议**：rodski 和 rodski-agent 可由不同开发者/Agent 并行推进。Phase 4 全在 rodski 侧，Phase 5-6 中 agent 侧的 WI 可以与 rodski 侧并行。

---

## 7. 工作量总览

### 按 Phase + 项目汇总

| Phase | 内容 | 工作项数 | rodski | agent | BOTH | 关键路径 |
|-------|------|---------|--------|-------|------|---------|
| Phase 4 | 自研报告系统 | 5 | 5 | 0 | 0 | WI-40 -> WI-41 |
| Phase 5 | Observability + KPI | 4 | 1 | 2 | 1 | WI-50 + WI-51 -> WI-52 |
| Phase 6 | 架构补强 | 5 | 3 | 1 | 1 | 多数独立 |
| **总计** | | **14** | **9** | **3** | **2** | |

### 全量工作项索引

| WI | Phase | 名称 | 大小 | 项目 |
|----|-------|------|------|------|
| WI-40 | 4 | 报告数据模型与收集器 | M | rodski |
| WI-41 | 4 | HTML 报告生成器 | L | rodski |
| WI-42 | 4 | 历史趋势与缺陷聚合 | M | rodski |
| WI-43 | 4 | CLI 集成 | S | rodski |
| WI-44 | 4 | Agent 诊断修复可视化 | S | rodski |
| WI-50 | 5 | Execution Trace 层 | M | rodski |
| WI-51 | 5 | LLM Token 计量 | S | BOTH |
| WI-52 | 5 | Agent KPI 评估框架 | M | rodski-agent |
| WI-53 | 5 | Agent vs 通用 Agent 对比 | S | rodski-agent |
| WI-60 | 6 | Agent 记忆层 | M | rodski-agent |
| WI-61 | 6 | set/get 一等公民化 | S | BOTH |
| WI-62 | 6 | Network Interception | M | rodski |
| WI-63 | 6 | Case Tag 选择性执行 | S | rodski |
| WI-64 | 6 | 两层 if/else + elif | S | rodski |

---

## 8. 风险分析

| 风险 | 影响 | Phase | 缓解措施 |
|------|------|-------|---------|
| HTML 报告单文件过大 | 中 | 4 | 截图压缩 + 懒加载 + 分文件模式默认 |
| LLM Token 计量精度 | 中 | 5 | 部分 Provider 不返回 token 数，用估算 |
| KPI 基准测试集偏差 | 中 | 5 | 使用多样化用例集 + 定期更新 |
| Agent 记忆层 SQLite 膨胀 | 低 | 6 | 自动淘汰策略 + 容量上限 |
| Network Interception 仅 Web 可用 | 低 | 6 | 文档明确标注适用范围 |

---

## 9. 验证方案

### 9.1 Phase 4 验证

1. **报告生成**：
   - 从 rodski-demo 全量执行 -> 生成报告 -> 浏览器打开验证
   - 单文件模式验证（邮件大小 < 10MB）
2. **趋势图**：连续执行 3 次 -> 趋势图显示 3 个数据点
3. **截图内联**：失败步骤截图在报告中可查看
4. **Agent 可视化**：由 rodski-agent 驱动执行后，报告展示诊断信息

### 9.2 Phase 5 验证

1. **Trace 验证**：执行后检查 trace JSON 结构完整
2. **Token 计量**：LLM 调用后检查记录准确
3. **KPI 报告**：基准测试运行 -> 输出 KPI 指标表
4. **对比实验**：同一需求分别用 rodski-agent 和通用 Agent 执行，对比指标

### 9.3 Phase 6 验证

- **WI-60**：首次执行记录写入 -> 二次执行命中记忆 -> 修复模式置信度计算
- **WI-61**：文档和 Prompt 更新后，Agent 生成的 XML 优先使用 set/get
- **WI-62**：rodski-demo 新增 mock_route 示例用例
- **WI-63**：`rodski run case/ --tags smoke` 正确过滤用例
- **WI-64**：rodski-demo 新增两层 if/elif/else 示例用例

---

## 附录 A: Agent KPI 对比建议值

基于行业经验和 RodSki 特性，建议 KPI 基准目标：

| 指标 | 基准值 | 优秀值 | 说明 |
|------|--------|--------|------|
| First_pass_rate | > 60% | > 80% | Design Agent 首次生成通过率 |
| XML_validity_rate | > 90% | > 98% | XSD 校验通过率 |
| Fix_success_pct | > 40% | > 70% | 自动修复成功率 |
| Token_per_case | < 10K | < 5K | 平均 token 消耗 |
| Cost_per_case | < $0.50 | < $0.15 | 平均 LLM 成本 |
| T_design (秒) | < 120 | < 60 | 设计耗时 |
| T_fix (秒) | < 30 | < 10 | 修复耗时 |
| Flakiness_rate | < 10% | < 3% | 不稳定率 |
