# 结果审查 Agent 架构分析

## 一、当前架构层次

```
RodSki 测试框架
│
├── 核心层 (rodski/core/)
│   ├── ski_executor.py         # 测试执行引擎
│   └── result_writer.py        # 结果写入
│
├── LLM 层 (rodski/llm/)
│   ├── client.py               # 统一 LLM 客户端
│   └── capabilities/           # 基础能力（简单调用）
│       ├── vision_locator.py
│       └── result_reviewer.py  # ← 当前位置（简单能力）
│
├── Agent 层 (rodski/agents/)   # ← 新增：复杂 Agent
│   └── review_agent.py         # ← 建议位置（LangChain Agent）
│
└── CLI 层 (rodski/cli/)
    └── review.py               # CLI 入口
```

## 二、为什么需要独立的 Agent 层？

### 2.1 Capability vs Agent

| 维度 | Capability | Agent |
|------|-----------|-------|
| 复杂度 | 简单，单次调用 | 复杂，多步推理 |
| 工具使用 | 不使用工具 | 使用多个工具 |
| 决策能力 | 无决策 | 有决策链 |
| 框架依赖 | 无 | LangChain |

**Capability 示例**（当前 result_reviewer）
```python
# 简单：一次 LLM 调用
def review(log, xml, screenshots):
    prompt = build_prompt(log, xml)
    result = llm.chat_with_vision(prompt, screenshots)
    return parse_result(result)
```

**Agent 示例**（建议的 review_agent）
```python
# 复杂：多步推理 + 工具调用
agent = create_react_agent(llm, tools=[
    read_log_tool,
    read_xml_tool,
    analyze_screenshot_tool,
    compare_expected_tool
])

# Agent 自主决策：
# 1. 先读日志找错误
# 2. 再看截图验证
# 3. 对比用例预期
# 4. 生成审查报告
result = agent.invoke({"result_dir": path})
```

## 三、架构方案对比

### 方案 1：放在 LLM Capability 层（当前）

```
rodski/llm/capabilities/result_reviewer.py
```

**优点**
- 简单，与其他能力统一
- 复用 LLM 客户端

**缺点**
- 无法使用 LangChain Agent 框架
- 无法多步推理和工具调用
- 功能受限

### 方案 2：独立 Agent 层（推荐）

```
rodski/agents/
├── __init__.py
├── base.py                 # Agent 基类
├── review_agent.py         # 结果审查 Agent
└── tools/                  # Agent 工具集
    ├── log_reader.py
    ├── screenshot_analyzer.py
    └── expectation_checker.py
```

**优点**
- 使用 LangChain Agent 框架
- 支持多步推理和工具调用
- 可扩展（未来可添加其他 Agent）

**缺点**
- 增加一层架构
- 依赖 LangChain

## 四、集成方案

### 4.1 CLI 使用

```bash
# 独立审查
python -m rodski.cli.review result/run_20260403_084451

# 或
rodski review result/run_20260403_084451
```

### 4.2 自动审查（测试执行后）

**配置文件**
```yaml
# rodski/config/config.yaml
review:
  enabled: true              # 是否启用自动审查
  mode: auto                 # auto: 自动审查, manual: 仅 CLI
  on_pass: false             # PASS 的用例是否审查
  on_fail: true              # FAIL 的用例是否审查
```

**集成点：ski_executor.py**
```python
# rodski/core/ski_executor.py
def execute_case(self, case):
    result = self._run_case(case)
    self.result_writer.write(result)

    # 自动审查
    if self.config.get('review.enabled'):
        self._auto_review(result)
```

### 4.3 架构层次关系

```
┌─────────────────────────────────────────┐
│  CLI 层                                  │
│  rodski/cli/review.py                   │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  Agent 层 (新增)                         │
│  rodski/agents/review_agent.py          │
│  - LangChain Agent                      │
│  - 多步推理                              │
│  - 工具调用                              │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  LLM 层                                  │
│  rodski/llm/client.py                   │
│  - 统一客户端                            │
│  - Provider 抽象                         │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  核心层                                  │
│  rodski/core/ski_executor.py            │
│  - 测试执行                              │
│  - 自动审查触发                          │
└─────────────────────────────────────────┘
```

## 五、推荐方案

### 建议：独立 Agent 层

**理由**
1. **功能需求**：结果审查需要多步推理（读日志→分析截图→对比预期→生成报告）
2. **技术选型**：LangChain Agent 框架天然支持这种场景
3. **可扩展性**：未来可添加其他 Agent（用例生成、Bug 分析等）
4. **职责清晰**：
   - LLM 层：基础能力（单次调用）
   - Agent 层：复杂任务（多步推理）

### 目录结构

```
rodski/
├── llm/                    # LLM 基础设施
│   ├── client.py
│   └── capabilities/       # 简单能力
│       └── vision_locator.py
│
├── agents/                 # Agent 层（新增）
│   ├── __init__.py
│   ├── base.py
│   ├── review_agent.py     # 结果审查 Agent
│   └── tools/              # Agent 工具
│       ├── log_reader.py
│       ├── screenshot_analyzer.py
│       └── expectation_checker.py
│
└── cli/
    └── review.py           # CLI 入口
```

### 依赖关系

- Agent 层依赖 LLM 层（使用统一客户端）
- 核心层可选依赖 Agent 层（自动审查）
- CLI 层调用 Agent 层

---

## 六、实施建议

1. **阶段 1**：先实现 LLM 基础设施（iteration-06 当前范围）
2. **阶段 2**：创建 Agent 层，实现 review_agent（可作为 iteration-07）
3. **阶段 3**：集成到核心层，支持自动审查




