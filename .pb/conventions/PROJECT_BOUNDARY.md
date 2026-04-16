# rodski / rodski-agent 项目边界约束

**版本**: 1.0  
**日期**: 2026-04-16  
**状态**: 生效

---

## 1. 三条硬约束

### 约束 1：单向依赖

```
rodski-agent ──依赖──> rodski
rodski ──不依赖──> rodski-agent
```

- rodski-agent 的 `pyproject.toml` 可以声明 `rodski` 为依赖
- rodski 的代码中 **禁止** `import rodski_agent` 或 `from rodski_agent import ...`
- rodski 的 `pyproject.toml` 不得引用 rodski-agent

### 约束 2：rodski 独立可执行

rodski 不安装 rodski-agent 也能完整运行：

```bash
# 这必须能工作（不安装 rodski-agent）
pip install rodski
rodski run case/ --output-format json
rodski validate dir/
rodski report generate result/
```

- rodski 的所有 **核心路径**（关键字执行、驱动、数据解析、结果输出、报告生成）不依赖 LLM
- rodski 内的 LLM 模块（`rodski/llm/`）是 **可选依赖**：
  - 安装方式：`pip install rodski[llm]`
  - 用途：视觉定位（vision locator）、截图验证等 **执行层能力**
  - 不装也能跑：退化到传统定位器（id / css / xpath / ocr）
- rodski 中 **禁止** 在核心路径出现 LLM 强依赖（`import anthropic` 等必须在 try/except 或延迟导入中）

### 约束 3：LLM 配置不共享

两个项目各自管理自己的 LLM 配置：

| | rodski | rodski-agent |
|---|---|---|
| 配置文件 | `rodski/config/llm_config.yaml` | `rodski-agent/config/agent_config.yaml` |
| Provider 实现 | `rodski/llm/providers/` | `rodski-agent/common/llm_bridge.py` (langchain) |
| API Key 管理 | 各自通过环境变量 | 各自通过环境变量 |
| Token 计量 | 各自独立记录 | 各自独立记录 |
| 类型定义 | 各自定义 `LLMCallRecord` 等 | 各自定义，不从 rodski 导入 |

**禁止事项**：
- rodski-agent 不得 `from rodski.llm import ...`
- 不得共享 LLM 配置文件路径
- 不得共享 Provider 实例

---

## 2. 交互方式

rodski-agent 通过 rodski 的 **公开接口** 与 rodski 交互，不通过 Python import 内部模块。

### 2.1 允许的交互方式

| 接口类型 | 示例 | 说明 |
|---------|------|------|
| CLI 调用 | `rodski run case/ --output-format json` | 主要交互方式 |
| CLI 查询 | `rodski capabilities` | 动态获取支持的关键字、定位器类型等 |
| CLI 校验 | `rodski validate dir/` | 校验生成的 XML |
| 输出文件 | `execution_summary.json` / `result.xml` | rodski-agent 读取执行结果 |
| XSD Schema | `rodski/schemas/*.xsd` | rodski-agent 用于验证或参考 XML 格式 |

### 2.2 禁止的交互方式

```python
# 以下全部禁止
from rodski.core.keyword_engine import KeywordEngine     # 禁止导入内部模块
from rodski.llm import LLMClient                         # 禁止导入 LLM 模块
from rodski.report import ReportData                     # 禁止导入报告模块
from rodski.core.ski_executor import SKIExecutor          # 禁止导入执行器
```

### 2.3 允许的导入（如需要）

```python
# 仅允许导入 rodski 公开的数据类型（如果有 public API）
from rodski import __version__                            # 版本号
# 其他一律通过 CLI 交互
```

---

## 3. 职责边界

### 3.1 rodski 负责

- 关键字执行（17 个关键字 + builtins 系统函数）
- 驱动管理（Web / Desktop / Mobile / API）
- XML 解析（Case / Model / Data / GlobalValue）
- XSD Schema 校验
- 结果输出（result.xml / execution_summary.json）
- HTML 报告生成
- Execution Trace（可观测性）
- LLM 可选层（视觉定位、截图验证 — 不装也能跑）

### 3.2 rodski-agent 负责

- 所有需要 LLM 做 **推理/决策** 的功能：
  - Design Agent（需求 → XML 生成）
  - Execution Agent（失败诊断 → 自愈修复）
  - RPA Agent（流程规划 → 跨应用编排）
- Agent 状态图（LangGraph StateGraph）
- 流程记忆（Memory Store）
- Agent KPI 评估
- Agent CLI（`rodski-agent run / design / pipeline / rpa`）

### 3.3 判定标准

当一个功能不确定归哪个项目时，问：

1. **去掉 LLM 还能工作吗？** → 能 → rodski
2. **这是执行还是决策？** → 执行 → rodski；决策 → rodski-agent
3. **用户不安装 rodski-agent 还需要这个功能吗？** → 需要 → rodski

---

## 4. 版本兼容

- rodski-agent 的版本声明中应指定兼容的 rodski 最低版本
- rodski 升级关键字 / Schema 后，rodski-agent 通过 `rodski capabilities` 动态适配
- rodski 不负责维护 rodski-agent 的兼容性（单向依赖原则）

---

## 5. 检查清单

每次提交 PR 前确认：

- [ ] rodski 的代码中没有 `import rodski_agent`
- [ ] rodski 的核心路径中没有 LLM 强依赖（try/except 或 optional 保护）
- [ ] rodski-agent 没有 `from rodski.llm import ...`
- [ ] rodski-agent 没有 `from rodski.core import ...`（内部模块）
- [ ] rodski-agent 通过 CLI 或文件格式与 rodski 交互
- [ ] 两个项目的 LLM 配置文件独立

---

**最后更新**: 2026-04-16
