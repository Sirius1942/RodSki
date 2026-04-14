# rodski-agent 项目需求与设计方案

## Context

RodSki 是面向 AI Agent 的跨平台确定性测试执行引擎。当前 `rodski/` 只负责执行，缺少一个 AI Agent 层来完成"理解需求→设计测试→执行测试→分析结果"的完整闭环。需要新建 `rodski-agent/` 项目，作为 RodSki 生态的 AI Agent 层。

---

## 1. 项目概述

### 1.1 定位

rodski-agent 是 **测试自动化领域的工具 Agent**：
- 不是对话式助手（没有聊天 UI）
- 不是通用 Agent 框架（不编排外部 Agent）
- 是一个 CLI 工具，被上层 Harness Agent（Claude Code、小龙虾等）或 CI/CD 调用
- 内部用 LangGraph 编排两个领域 Agent（Design + Execution）
- 底层调用 rodski 执行引擎

### 1.2 三层架构

```
┌──────────────────────────────────────────────────────┐
│ Layer 3: Harness Agent（助理/虚拟员工）                │
│ Claude Code / 小龙虾 / CI/CD Pipeline                 │
│ 职责：理解用户意图、任务规划、多轮对话                   │
└──────────────────┬───────────────────────────────────┘
                   │ CLI 调用 + JSON stdout
                   ▼
┌──────────────────────────────────────────────────────┐
│ Layer 2: rodski-agent（领域工具 Agent）← 本项目        │
│ 职责：测试设计工作流 + 测试执行工作流                    │
│ 技术：LangGraph + CLI（Click/Typer）                  │
└──────────────────┬───────────────────────────────────┘
                   │ CLI 调用（rodski run/validate）
                   ▼
┌──────────────────────────────────────────────────────┐
│ Layer 1: rodski（确定性执行引擎）← 已有                │
│ 职责：XML 解析 → 关键字执行 → 结果返回                 │
└──────────────────────────────────────────────────────┘
```

### 1.3 边界

| 做什么 | 不做什么 |
|--------|---------|
| 理解测试需求，生成 XML 用例 | 理解非测试领域需求 |
| 执行测试并分析结果 | 管理对话历史、记忆 |
| 诊断失败原因，智能重试 | 做通用 Agent 编排 |
| CLI 输出结构化 JSON | 提供 Web UI/聊天界面 |
| 复用 rodski LLM 能力 | 自建 LLM 服务层 |

---

## 2. CLI 命令设计

所有命令输出统一 `--format json`（默认 human-readable，`json` 模式供 Agent 解析）。

### 2.1 命令总览

```bash
# 测试设计
rodski-agent design \
  --requirement "登录功能，支持账号密码和验证码" \
  --url "https://app.example.com/login" \
  --output cassmall/login/ \
  --format json

# 测试执行
rodski-agent run \
  --case cassmall/login/ \
  --max-retry 3 \
  --format json

# 完整 Pipeline（设计 + 执行）
rodski-agent pipeline \
  --requirement "登录功能测试" \
  --url "https://app.example.com/login" \
  --output cassmall/login/ \
  --format json

# 失败诊断
rodski-agent diagnose \
  --result cassmall/login/result/execution_summary.json \
  --format json

# 版本/配置
rodski-agent --version
rodski-agent config show
```

### 2.2 输出格式（JSON 模式）

```json
// design 输出
{
  "status": "success",
  "command": "design",
  "output": {
    "cases": ["case/c001.xml", "case/c002.xml"],
    "models": ["model/model.xml"],
    "data": ["data/data.xml", "data/data_verify.xml"],
    "summary": "生成 2 个用例，覆盖正常登录和密码错误场景"
  }
}

// run 输出
{
  "status": "success",
  "command": "run",
  "output": {
    "total": 3,
    "passed": 2,
    "failed": 1,
    "cases": [
      {"id": "c001", "status": "PASS", "time": 5.2},
      {"id": "c002", "status": "PASS", "time": 3.1},
      {"id": "c003", "status": "FAIL", "error": "元素未找到: 验证码输入框", "diagnosis": "..."}
    ]
  }
}

// diagnose 输出
{
  "status": "success",
  "command": "diagnose",
  "output": {
    "root_cause": "验证码输入框 CSS 选择器变更",
    "confidence": 0.85,
    "suggestion": "更新 model.xml 中 captchaInput 的定位器",
    "evidence": ["截图分析显示页面结构变化", "执行日志中 ElementNotFound"]
  }
}
```

---

## 3. Design Agent 详细设计

### 3.1 LangGraph 图拓扑

```
                    ┌──────────────┐
                    │   START      │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ 需求分析      │ ← LLM: 理解需求，提取测试场景
                    │ analyze_req  │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ 页面探索      │ ← OmniParser + 截图
                    │ explore_page │   （如果提供了 URL）
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ 元素识别      │ ← LLM Vision: 语义标签
                    │ identify_elem│
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ 用例规划      │ ← LLM: 规划 Case 结构
                    │ plan_cases   │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ 数据设计      │ ← LLM: 生成测试数据
                    │ design_data  │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ XML 生成      │ ← 模板 + 数据拼装
                    │ generate_xml │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
              ┌─────│ XML 校验      │─────┐
              │     │ validate_xml │     │
              │     └──────────────┘     │
              │                          │
        ┌─────▼─────┐           ┌───────▼──────┐
        │ 校验通过   │           │ 校验失败      │
        │ → 输出     │           │ → 修复(max 3) │
        └───────────┘           └──────┬───────┘
                                       │ 回到 generate_xml
```

### 3.2 State Schema

```python
class DesignState(TypedDict):
    # 输入
    requirement: str                    # 需求描述
    target_url: str                     # 目标 URL（可选）
    output_dir: str                     # 输出目录

    # 中间状态
    test_scenarios: list[dict]          # 分析出的测试场景
    page_elements: list[dict]           # OmniParser 识别的元素
    enriched_elements: list[dict]       # LLM 语义增强后的元素
    case_plan: list[dict]               # 用例规划结构
    test_data: list[dict]               # 测试数据设计
    generated_files: list[str]          # 已生成的 XML 文件路径

    # 控制
    validation_errors: list[str]        # XML 校验错误
    fix_attempt: int                    # 修复尝试次数
    status: str                         # "running" | "success" | "failed"
    error: str                          # 错误信息
```

### 3.3 节点职责

| 节点 | 输入 | 输出 | 使用的能力 | rodski 知识依赖 |
|------|------|------|-----------|----------------|
| `analyze_req` | requirement | test_scenarios | LLMClient (text) | CORE_DESIGN_CONSTRAINTS §1（关键字能力边界） |
| `explore_page` | target_url | page_elements | OmniParser HTTP | — |
| `identify_elem` | page_elements + 截图 | enriched_elements | LLMClient (vision_locator) | CORE_DESIGN_CONSTRAINTS §2.5（定位器类型枚举） |
| `plan_cases` | test_scenarios + enriched_elements | case_plan | LLMClient (text) | TEST_CASE_WRITING_GUIDE §3（三阶段容器、action 枚举）、§2（目录结构） |
| `design_data` | case_plan | test_data | LLMClient (text) | CORE_DESIGN_CONSTRAINTS §2（数据表命名）、§4（特殊值、Return 引用限制） |
| `generate_xml` | case_plan + test_data + enriched_elements | generated_files | xml_builder + rodski_knowledge | CORE_DESIGN_CONSTRAINTS §6（目录）、§7（XML 格式）、§2.5（定位器格式） |
| `validate_xml` | generated_files | validation_errors | rodski validate CLI | rodski/schemas/*.xsd |

---

## 4. Execution Agent 详细设计

### 4.1 LangGraph 图拓扑

```
                    ┌──────────────┐
                    │   START      │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ 预检查        │ ← rodski validate + 文件完整性
                    │ pre_check    │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ 执行测试      │ ← rodski run (subprocess)
                    │ execute      │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ 解析结果      │ ← 读取 execution_summary.json
                    │ parse_result │
                    └──────┬───────┘
                           │
              ┌────────────┤────────────┐
              │            │            │
        ┌─────▼─────┐ ┌───▼────┐ ┌────▼─────┐
        │ ALL PASS  │ │ 部分   │ │ ALL FAIL │
        │ → 报告    │ │ FAIL   │ │ → 诊断   │
        └───────────┘ └───┬────┘ └────┬─────┘
                          │           │
                    ┌─────▼───────────▼─┐
                    │ 诊断分析            │ ← LLM + 截图分析
                    │ diagnose           │
                    └──────┬─────────────┘
                           │
                    ┌──────▼───────┐
              ┌─────│ 重试决策      │─────┐
              │     │ retry_decide │     │
              │     └──────────────┘     │
              │                          │
        ┌─────▼──────┐         ┌────────▼───────┐
        │ 可修复      │         │ 不可修复        │
        │ → 修复 XML  │         │ → 标记失败      │
        │ → 回到执行  │         └────────┬───────┘
        └────────────┘                  │
                                 ┌──────▼───────┐
                                 │ 生成报告      │
                                 │ report       │
                                 └──────────────┘
```

### 4.2 State Schema

```python
class ExecutionState(TypedDict):
    # 输入
    case_path: str                      # 用例目录或文件路径
    max_retry: int                      # 最大重试次数

    # 执行状态
    execution_result: dict              # execution_summary.json 内容
    case_results: list[dict]            # 每个 case 的结果
    screenshots: list[str]              # 截图路径

    # 诊断
    diagnosis: dict                     # 诊断结果 {root_cause, confidence, suggestion}
    retry_count: int                    # 已重试次数
    fixes_applied: list[str]           # 已应用的修复

    # 输出
    report: dict                        # 最终报告
    status: str                         # "running" | "pass" | "fail" | "partial"
    error: str
```

### 4.3 节点职责

| 节点 | 输入 | 输出 | 使用的能力 | rodski 知识依赖 |
|------|------|------|-----------|----------------|
| `pre_check` | case_path | validation OK/errors | rodski validate CLI | CORE_DESIGN_CONSTRAINTS §6（目录结构）、§7.0（XSD 校验） |
| `execute` | case_path | execution_result | rodski run CLI | AGENT_INTEGRATION（CLI 调用契约、exit code 语义） |
| `parse_result` | execution_summary.json | case_results | JSON 解析 | AGENT_INTEGRATION（输出格式、result 结构） |
| `diagnose` | case_results + screenshots | diagnosis | LLMClient (screenshot_verifier + test_reviewer) | CORE_DESIGN_CONSTRAINTS §8.8.2（CASE/ENV/PRODUCT_DEFECT 分类）、AGENT_INTEGRATION（错误类型映射） |
| `retry_decide` | diagnosis + retry_count | 修复/放弃 | 规则引擎 + LLM | CORE_DESIGN_CONSTRAINTS §8.8（置信度阈值：< 0.6 不自动修复） |
| `report` | 所有状态 | report JSON | 模板生成 | — |

---

## 5. 项目目录结构

```
RodSki/
├── rodski/                     # 执行引擎（已有，不动）
├── rodski-demo/                # 框架示例（已有，不动）
├── rodski-agent/               # ← 新项目
│   ├── pyproject.toml          # 包配置 + 依赖
│   ├── README.md
│   ├── config/
│   │   └── agent_config.yaml   # Agent 配置
│   ├── src/
│   │   └── rodski_agent/
│   │       ├── __init__.py
│   │       ├── cli.py              # CLI 入口（Click/Typer）
│   │       ├── common/
│   │       │   ├── __init__.py
│   │       │   ├── state.py            # 共享状态定义
│   │       │   ├── rodski_tools.py     # rodski CLI 封装
│   │       │   ├── rodski_knowledge.py # rodski 框架约束知识库
│   │       │   ├── llm_bridge.py       # rodski.llm 桥接
│   │       │   └── xml_builder.py      # XML 生成工具
│   │       ├── design/
│   │       │   ├── __init__.py
│   │       │   ├── graph.py        # Design Agent LangGraph 图
│   │       │   ├── nodes.py        # 各节点实现
│   │       │   └── prompts.py      # 提示词模板
│   │       ├── execution/
│   │       │   ├── __init__.py
│   │       │   ├── graph.py        # Execution Agent LangGraph 图
│   │       │   ├── nodes.py        # 各节点实现
│   │       │   └── prompts.py      # 提示词模板
│   │       └── pipeline/
│   │           ├── __init__.py
│   │           └── orchestrator.py # Design → Execution 串联
│   └── tests/
│       ├── conftest.py
│       ├── test_design_graph.py
│       ├── test_execution_graph.py
│       └── test_cli.py
```

---

## 6. 依赖管理

```toml
[project]
name = "rodski-agent"
version = "0.1.0"
description = "AI Agent layer for RodSki test automation framework"
requires-python = ">=3.10"

dependencies = [
    "langgraph>=0.4.0",
    "langchain-core>=0.3.0",
    "langchain-anthropic>=0.3.0",     # Claude provider
    "langchain-openai>=0.3.0",        # OpenAI provider
    "click>=8.0",                     # CLI 框架
    "pyyaml>=6.0",
    "requests>=2.31.0",               # OmniParser HTTP
    "pillow>=10.0.0",                 # 截图处理
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.12.0",
]

[project.scripts]
rodski-agent = "rodski_agent.cli:main"
```

---

## 7. 配置设计

`config/agent_config.yaml`:

```yaml
# rodski 路径配置
rodski:
  cli_path: "python rodski/ski_run.py"    # rodski CLI 命令
  validate_cmd: "rodski validate"
  default_browser: "chromium"
  headless: true

# LLM 配置（继承 rodski 的 llm_config.yaml）
llm:
  config_path: "../rodski/config/llm_config.yaml"  # 复用 rodski LLM 配置
  # 可覆盖
  provider: claude
  model: claude-opus-4-6

# OmniParser 配置（继承 rodski 的配置）
omniparser:
  config_path: "../rodski/config/llm_config.yaml"

# Agent 行为配置
design:
  max_scenarios: 10         # 单次最多生成场景数
  max_fix_attempts: 3       # XML 校验失败最大修复次数

execution:
  max_retry: 3              # 最大重试次数
  screenshot_on_fail: true  # 失败时截图
  diagnosis_enabled: true   # 启用 AI 诊断

# 输出配置
output:
  format: "human"           # "human" | "json"
  verbose: false
```

---

## 8. 与 rodski 的集成接口

### 8.1 rodski_tools.py — CLI 封装

```python
# 核心工具函数，封装 rodski CLI 调用

def rodski_run(case_path: str, headless: bool = True,
               output_format: str = "json") -> dict:
    """调用 rodski run，返回执行结果"""

def rodski_validate(path: str) -> dict:
    """调用 rodski validate，返回校验结果"""

def rodski_explain(case_xml: str) -> str:
    """调用 rodski explain，返回用例说明"""
```

### 8.2 llm_bridge.py — LLM 能力桥接

```python
# 桥接 rodski.llm 模块，复用已有 LLM 能力

def get_llm_client() -> LLMClient:
    """获取 rodski LLMClient 实例"""

def analyze_screenshot(image_path: str, question: str) -> dict:
    """调用 screenshot_verifier 能力"""

def analyze_elements(image_path: str, elements: list) -> list:
    """调用 vision_locator 能力"""

def review_test_result(result_dir: str) -> dict:
    """调用 test_reviewer 能力"""
```

### 8.3 xml_builder.py — XML 生成

```python
# XML 文件生成工具，严格遵循 TEST_CASE_WRITING_GUIDE.md 和 CORE_DESIGN_CONSTRAINTS.md
# 内部使用 rodski_knowledge.py 的约束常量进行预校验

def build_case_xml(cases: list[dict]) -> str:
    """生成 case XML
    约束：action 必须在 SUPPORTED_KEYWORDS 中，
    三阶段容器 pre_process/test_case/post_process，
    execute 只能是 '是'/'否'"""

def build_model_xml(models: list[dict]) -> str:
    """生成 model XML
    约束：唯一格式 <location type="...">值</location>，
    type 必须在 LOCATOR_TYPES 中，
    禁止使用简化格式"""

def build_data_xml(datatables: list[dict]) -> str:
    """生成 data XML
    约束：datatable name 必须与 model name 一致，
    row id 表内唯一，field name 必须与 element name 一致"""

def build_verify_xml(datatables: list[dict]) -> str:
    """生成 data_verify XML
    约束：表名为 {模型名}_verify，
    禁止在接口/DB verify 表中使用 ${Return[-1]}"""

def build_globalvalue_xml(groups: list[dict]) -> str:
    """生成 globalvalue XML
    约束：group name 全局唯一，var 须有 name+value"""
```

---

## 9. 迭代计划

### MVP（v0.1.0）— Execution Agent

**目标**：先让执行跑通，验证 LangGraph + CLI 架构可行。

**范围**：
- [ ] 项目骨架搭建（pyproject.toml、目录结构、CLI 入口）
- [ ] `rodski_tools.py` — 封装 `rodski run` / `rodski validate`
- [ ] Execution Agent LangGraph 图（execute → parse → report）
- [ ] `rodski-agent run --case <path> --format json`
- [ ] 基础错误处理和 JSON 输出
- [ ] 单元测试

**不做**：诊断、重试、Design Agent

### V1.0 — 完整执行 + 基础设计

**目标**：执行 Agent 加入诊断/重试，Design Agent 可生成简单用例。

**范围**：
- [ ] Execution Agent 增加 diagnose + retry_decide 节点
- [ ] `llm_bridge.py` — 桥接 rodski LLM 能力
- [ ] Design Agent 基础流程（需求分析 → 用例规划 → XML 生成 → 校验）
- [ ] `rodski-agent design --requirement "..." --output <dir>`
- [ ] `rodski-agent pipeline` 命令
- [ ] LangGraph checkpointing（SQLite）
- [ ] 集成测试

### V2.0 — 视觉探索 + 智能修复

**目标**：Design Agent 具备页面探索能力，Execution Agent 能自动修复 XML。

**范围**：
- [ ] Design Agent 增加 explore_page + identify_elem 节点
- [ ] OmniParser 集成
- [ ] Execution Agent 智能修复（修改定位器、调整等待时间）
- [ ] `rodski-agent diagnose` 独立命令
- [ ] 执行历史记录和趋势分析
- [ ] MCP Server 封装（为后续接入更多 Harness Agent 准备）

---

## 10. rodski 知识依赖

rodski-agent 的 Design Agent 和 Execution Agent 都**强依赖 rodski 框架的规则和约束**。这些知识不是"最佳实践"，而是**硬性约束**——违反任何一条都会导致生成的 XML 无法通过校验或执行失败。

### 10.1 依赖的 rodski 文档清单

| 文档 | 路径 | 依赖方 | 关键约束 |
|------|------|--------|---------|
| **用例编写指南** | `rodski/docs/TEST_CASE_WRITING_GUIDE.md` | Design Agent（核心）, Execution Agent（诊断参考） | XML 文件格式、三阶段容器、关键字用法、数据引用规则、目录结构 |
| **核心设计约束** | `rodski/docs/CORE_DESIGN_CONSTRAINTS.md` | Design Agent（核心）, Execution Agent（诊断分类） | 15 个关键字清单、UI 原子动作禁止规则、数据表命名、定位器格式、Return 语义 |
| **关键字语法参考** | `rodski/docs/SKILL_REFERENCE.md` | Design Agent（核心） | 每个关键字的参数格式、模型/数据引用方式 |
| **Agent 集成指南** | `rodski/docs/AGENT_INTEGRATION.md` | Execution Agent（核心） | CLI 调用契约、exit code 语义、execution_summary.json 结构、错误分类 |
| **数据文件组织** | `rodski/docs/DATA_FILE_ORGANIZATION.md` | Design Agent（XML 生成） | data.xml/data_verify.xml 组织方式、文件覆盖规则 |
| **XSD Schema 文件** | `rodski/schemas/*.xsd` | Design Agent（校验）, Execution Agent（校验） | case.xsd、model.xsd、data.xsd、globalvalue.xsd |

### 10.2 知识嵌入策略

框架知识通过三个层次嵌入 rodski-agent：

```
┌─────────────────────────────────────────────────────┐
│ 层1: rodski_knowledge.py（编译期约束）               │
│ 硬编码的结构化规则：关键字清单、定位器枚举、           │
│ 目录结构约束、数据表命名规则                          │
│ → xml_builder / fixer / validate 使用               │
├─────────────────────────────────────────────────────┤
│ 层2: prompts.py（LLM 提示词约束）                    │
│ 将框架规则转化为 LLM 可理解的约束描述                 │
│ → Design Agent 和 Execution Agent 的 LLM 节点使用    │
├─────────────────────────────────────────────────────┤
│ 层3: rodski validate CLI（运行时校验）               │
│ 调用 rodski 的 XSD 校验和语义校验                     │
│ → 生成后校验 + 修复循环的终止条件                     │
└─────────────────────────────────────────────────────┘
```

### 10.3 rodski_knowledge.py — 框架约束模块

新增 `common/rodski_knowledge.py`，将 rodski 的硬性约束编码为 Python 常量和校验函数：

```python
"""rodski 框架约束知识库 — 编译期约束，不依赖 LLM"""

# === 关键字约束 ===
SUPPORTED_KEYWORDS = [
    "close", "type", "verify", "wait", "navigate", "launch",
    "assert", "upload_file", "clear", "get_text", "get",
    "send", "set", "DB", "run",
]
COMPAT_KEYWORDS = ["check"]  # check 等同 verify
UI_ATOMIC_ACTIONS = [
    "click", "double_click", "right_click", "hover",
    "select", "key_press", "drag", "scroll",
]  # 仅作为数据表字段值，不能作为 action

# === 定位器约束 ===
LOCATOR_TYPES = [
    "id", "class", "css", "xpath", "text", "tag", "name",
    "static", "field",                        # 传统定位器
    "vision", "ocr", "vision_bbox",           # 视觉定位器
]
DRIVER_TYPES = ["web", "interface", "other", "windows", "macos"]

# === 目录结构约束 ===
REQUIRED_DIRS = ["case", "model", "data"]     # 必须存在的子目录
OPTIONAL_DIRS = ["fun", "result"]
FIXED_FILES = {
    "model": "model.xml",
    "data": "data.xml",
    "data_verify": "data_verify.xml",         # 可选
    "globalvalue": "globalvalue.xml",          # 可选
}

# === 数据表约束 ===
SPECIAL_VALUES = ["BLANK", "NULL", "NONE"]
VERIFY_TABLE_SUFFIX = "_verify"

# === Case XML 约束 ===
CASE_PHASES = ["pre_process", "test_case", "post_process"]
COMPONENT_TYPES = ["界面", "接口", "数据库"]
EXECUTE_VALUES = ["是", "否"]

# === 校验函数 ===
def validate_action(action: str) -> bool:
    """检查 action 是否在 SUPPORTED 关键字清单中"""

def validate_locator_type(loc_type: str) -> bool:
    """检查定位器类型是否合法"""

def validate_element_data_consistency(model_elements: list, data_fields: list) -> list[str]:
    """检查模型元素名 = 数据表字段名"""

def validate_directory_structure(path: str) -> list[str]:
    """检查目录结构是否遵循 case/model/data 约束"""

def validate_verify_table_name(model_name: str, table_name: str) -> bool:
    """验证数据表名为 {模型名}_verify"""
```

### 10.4 知识在 Design Agent 中的应用

| 节点 | 使用的知识 | 来源 |
|------|-----------|------|
| `analyze_req` | 关键字能力边界（type 做 UI、send 做接口、verify 通用验证） | CORE_DESIGN_CONSTRAINTS §1 |
| `plan_cases` | 三阶段容器规则、action 枚举、模型名=数据表名 | TEST_CASE_WRITING_GUIDE §3、CORE_DESIGN_CONSTRAINTS §2 |
| `design_data` | 特殊值语义（click/select/BLANK/NULL）、Return 引用限制、verify 表后缀规则 | CORE_DESIGN_CONSTRAINTS §4、§2.2 |
| `generate_xml` | 定位器格式（`<location type>` 唯一格式）、XSD 结构、目录结构 | CORE_DESIGN_CONSTRAINTS §2.5、§6、§7 |
| `validate_xml` | XSD Schema 文件 | rodski/schemas/*.xsd |

### 10.5 知识在 Execution Agent 中的应用

| 节点 | 使用的知识 | 来源 |
|------|-----------|------|
| `pre_check` | 目录结构约束（case/model/data 必须存在）、XSD 校验 | CORE_DESIGN_CONSTRAINTS §6、§7.0 |
| `execute` | CLI 调用契约（exit code 语义、参数格式） | AGENT_INTEGRATION §CLI 命令 |
| `parse_result` | execution_summary.json 结构、result XML 结构 | AGENT_INTEGRATION §输出契约 |
| `diagnose` | 错误分类体系（CASE_DEFECT/ENV_DEFECT/PRODUCT_DEFECT/UNKNOWN）、关键字失败模式 | CORE_DESIGN_CONSTRAINTS §8.8.2、AGENT_INTEGRATION §错误处理 |
| `retry_decide` | 可修复 vs 不可修复的判定规则 | AGENT_INTEGRATION §错误分类 |
| `apply_fix` | 定位器修改规则、等待机制、数据表修改约束 | CORE_DESIGN_CONSTRAINTS §2.5、§13、TEST_CASE_WRITING_GUIDE §4 |

### 10.6 提示词中必须包含的 rodski 约束摘要

所有 Design Agent 和 Execution Agent 的 LLM 提示词必须嵌入以下约束摘要（`prompts.py` 中的共享常量）：

```python
RODSKI_CONSTRAINT_SUMMARY = """
## RodSki 框架约束（必须严格遵守）

### 关键字规则
- 仅支持 15 个关键字：close/type/verify/wait/navigate/launch/assert/upload_file/clear/get_text/get/send/set/DB/run
- type 只做 UI 输入，send 只做接口请求，verify 通用验证
- click/hover/select 等 UI 原子动作不是独立关键字，只能作为数据表字段值
- navigate 用于 Web/Mobile，launch 用于 Desktop，功能相同

### Case XML 格式
- 三阶段容器：pre_process(可选) → test_case(必选,1个) → post_process(可选)
- test_step 属性：action(必填) + model(可选) + data(可选)
- execute 属性只能是"是"或"否"
- component_type 只能是"界面"/"接口"/"数据库"

### Model XML 格式
- 定位器唯一格式：<location type="类型">值</location>
- 简化格式(type+value属性)已废弃，禁止使用
- element name 必须与数据表 field name 完全一致（区分大小写）
- 接口保留元素名：_method、_url、_header_*

### Data XML 格式
- 数据表名(datatable.name) 必须与模型名一致
- 验证数据表名为 {模型名}_verify
- row id 表内唯一
- 特殊值：空值=跳过，BLANK=空字符串，NULL=null，NONE=不发送
- ${Return[-1]} 只在数据表字段中使用，不写在 case XML 的 data 属性
- 禁止在接口/DB 的 _verify 表中使用 ${Return[-1]}（空校验）

### 目录结构
- 固定结构：case/ + model/ + data/ (必须) + fun/ + result/ (可选)
- 文件名固定：model.xml, data.xml, data_verify.xml, globalvalue.xml
"""
```

---

## 11. 关键设计约束

1. **rodski 不做 Agent 框架** — rodski-agent 是独立项目，通过 CLI 调用 rodski，不直接 import rodski 内部模块（llm 除外）
2. **LLM 是可选增强** — rodski-agent 的 Execution Agent 在无 LLM 时仍可工作（跳过诊断），Design Agent 必须有 LLM
3. **XML 格式遵循 TEST_CASE_WRITING_GUIDE.md** — xml_builder 生成的 XML 必须通过 rodski validate
4. **JSON 输出契约稳定** — CLI 的 JSON 输出格式一旦发布就是 API 契约，不能随意变更
5. **文件系统是 Agent 间通道** — Design → Execution 通过 XML 文件传递，不走内存
6. **rodski 知识是硬依赖** — 两个 Agent 的所有 LLM 提示词必须嵌入 rodski 约束摘要，xml_builder 的校验逻辑必须引用 rodski_knowledge.py 中的约束常量，不允许"凭 LLM 自由发挥"生成 XML

---

## 实施第一步

从 MVP 开始：搭建项目骨架 + 实现 `rodski-agent run` 命令。

需要创建/修改的文件：
1. `rodski-agent/pyproject.toml` — 新建
2. `rodski-agent/src/rodski_agent/__init__.py` — 新建
3. `rodski-agent/src/rodski_agent/cli.py` — 新建（Click CLI）
4. `rodski-agent/src/rodski_agent/common/rodski_tools.py` — 新建
5. `rodski-agent/src/rodski_agent/execution/graph.py` — 新建
6. `rodski-agent/src/rodski_agent/execution/nodes.py` — 新建
7. `rodski-agent/tests/conftest.py` — 新建
8. `rodski-agent/tests/test_cli.py` — 新建

验证方式：
```bash
cd rodski-agent
pip install -e ".[dev]"
rodski-agent run --case ../rodski-demo/demo_login/ --format json
```
