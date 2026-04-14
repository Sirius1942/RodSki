# rodski-agent 迭代开发计划

> 基于设计方案: `.pb/design/rodski-agent-design.md`
> 日期: 2026-04-13
> 总工时估算: ~73h（10 个迭代，每个迭代 1~2 天）
> 技术栈: Python 3.10+ / LangGraph / Click / rodski CLI

---

## 总览：迭代路线图

| 阶段 | 迭代 | 名称 | 核心产出 | 预计工时 |
|------|------|------|---------|---------|
| **MVP** | 01 | 项目骨架 + CLI 框架 + 知识库 | `rodski-agent --version` 可运行 + `rodski_knowledge.py` | 5h |
| **MVP** | 02 | Execution Agent 最小图 | `rodski-agent run` 调用 rodski 并返回 JSON | 8h |
| **MVP** | 03 | JSON 输出契约 + 错误处理 | 稳定的 JSON 输出格式 + 完善的错误分类 | 6h |
| **V1** | 04 | LLM 桥接 + 诊断节点 | `diagnose` 节点产出失败根因分析 | 8h |
| **V1** | 05 | 重试机制 | `retry_decide` 节点 + 受控重试循环 | 6h |
| **V1** | 06 | Design Agent 基础 | `rodski-agent design` 生成简单 XML 用例 | 12h |
| **V1** | 07 | Pipeline 命令 | `rodski-agent pipeline` 串联 design + run | 5h |
| **V2** | 08 | 视觉探索 | OmniParser 集成 + explore_page 节点 | 8h |
| **V2** | 09 | 智能修复 | Execution Agent 自动修复 XML 定位器 | 8h |
| **V2** | 10 | MCP Server 封装 | MCP 协议封装，供 Harness Agent 调用 | 7h |

---

## 依赖关系图

```
iteration-01 (骨架)
    │
    ▼
iteration-02 (Execution 最小图)
    │
    ├───────────────┐
    ▼               ▼
iteration-03    iteration-04
(JSON契约)      (LLM桥接+诊断)
    │               │
    │               ▼
    │           iteration-05
    │           (重试机制)
    │               │
    ├───────────────┤
    ▼               │
iteration-06        │
(Design Agent) ─────┤
    │               │
    ▼               │
iteration-07 ◄──────┘
(Pipeline)
    │
    ├───────────┐
    ▼           ▼
iteration-08  iteration-09
(视觉探索)    (智能修复)
    │           │
    └─────┬─────┘
          ▼
    iteration-10
    (MCP Server)
```

---

## MVP 阶段

---

### Iteration 01: 项目骨架 + CLI 框架 + 知识库

> **目标**: 搭建 rodski-agent 项目结构，实现 `rodski-agent --version` 可运行，构建 rodski 框架约束知识库。
> **预计工时**: 5h
> **分支**: `feature/rodski-agent-scaffold`
> **前置依赖**: 无

#### 任务列表

##### T01-001: 创建项目目录结构 (30min)

**文件**:
- `rodski-agent/pyproject.toml`
- `rodski-agent/README.md`
- `rodski-agent/src/rodski_agent/__init__.py`
- `rodski-agent/src/rodski_agent/common/__init__.py`
- `rodski-agent/src/rodski_agent/design/__init__.py`
- `rodski-agent/src/rodski_agent/execution/__init__.py`
- `rodski-agent/src/rodski_agent/pipeline/__init__.py`
- `rodski-agent/config/agent_config.yaml`

**任务**:
1. 按设计方案 SS5 创建完整目录结构
2. 编写 `pyproject.toml`，声明依赖（langgraph, click, pyyaml, requests, pillow）
3. 配置 `[project.scripts]` 使 `rodski-agent` 命令可用
4. 在 `__init__.py` 中定义 `__version__ = "0.1.0"`

**验收**:
- [ ] `pip install -e ".[dev]"` 成功
- [ ] `python -c "import rodski_agent"` 不报错

##### T01-002: 实现 CLI 入口框架 (60min)

**文件**:
- `rodski-agent/src/rodski_agent/cli.py`

**任务**:
1. 使用 Click 创建 CLI 入口 `main()`
2. 实现 `--version` 选项
3. 实现 `--format` 全局选项（human / json，默认 human）
4. 注册子命令占位符：`run`, `design`, `pipeline`, `diagnose`, `config`
5. 每个子命令先返回 "Not implemented yet"

**验收**:
- [ ] `rodski-agent --version` 输出版本号
- [ ] `rodski-agent run --help` 显示帮助信息
- [ ] `rodski-agent --format json run` 以 JSON 格式输出（即使是占位内容）

##### T01-003: 配置加载器 (45min)

**文件**:
- `rodski-agent/src/rodski_agent/common/config.py`
- `rodski-agent/config/agent_config.yaml`

**任务**:
1. 实现 `AgentConfig` 类，加载 YAML 配置
2. 支持配置文件路径查找（当前目录 > 项目根 > 默认）
3. 支持环境变量覆盖（`RODSKI_AGENT_*`）
4. 编写默认配置文件 `agent_config.yaml`（含 rodski 路径、LLM 配置、Agent 行为配置）

**验收**:
- [ ] `AgentConfig().rodski.cli_path` 返回正确路径
- [ ] 环境变量 `RODSKI_AGENT_LLM_MODEL` 可覆盖配置

##### T01-004: rodski 框架约束知识库 — rodski_knowledge.py (60min)

**文件**:
- `rodski-agent/src/rodski_agent/common/rodski_knowledge.py`
- `rodski-agent/tests/test_rodski_knowledge.py`

**任务**:
1. 从 `rodski/docs/CORE_DESIGN_CONSTRAINTS.md` 提取硬性约束，编码为 Python 常量：
   - `SUPPORTED_KEYWORDS` — 15 个关键字清单（§5）
   - `UI_ATOMIC_ACTIONS` — 仅作为数据表字段值的原子动作（§1.2）
   - `LOCATOR_TYPES` — 12 种定位器类型枚举（§2.5）
   - `DRIVER_TYPES` — 驱动类型枚举
   - `CASE_PHASES` — 三阶段容器名称
   - `COMPONENT_TYPES` — "界面"/"接口"/"数据库"
   - `SPECIAL_VALUES` — BLANK/NULL/NONE 语义
   - `VERIFY_TABLE_SUFFIX` — "_verify" 后缀规则
2. 从 `rodski/docs/TEST_CASE_WRITING_GUIDE.md` 提取目录结构约束：
   - `REQUIRED_DIRS` — case/model/data 三个必须子目录
   - `FIXED_FILES` — model.xml/data.xml/data_verify.xml/globalvalue.xml
3. 实现校验函数：
   - `validate_action(action)` — 检查 action 是否在 SUPPORTED 清单中
   - `validate_locator_type(loc_type)` — 检查定位器类型是否合法
   - `validate_element_data_consistency(elements, fields)` — 检查元素名=字段名
   - `validate_directory_structure(path)` — 检查目录结构合规
   - `validate_verify_table_name(model_name, table_name)` — 验证 _verify 后缀
4. 编写 `RODSKI_CONSTRAINT_SUMMARY` 字符串常量 — 供 LLM 提示词嵌入的约束摘要
5. 单元测试：验证常量完整性（与 rodski 源码中的 SUPPORTED 列表一致）

**验收**:
- [ ] 所有常量与 `rodski/docs/CORE_DESIGN_CONSTRAINTS.md` 一致
- [ ] 校验函数能正确识别合法/非法输入
- [ ] `RODSKI_CONSTRAINT_SUMMARY` 涵盖关键字、Case XML、Model XML、Data XML、目录结构五大类约束
- [ ] 单元测试验证约束与 rodski 源码同步

##### T01-005: 单元测试基础设施 (30min)

**文件**:
- `rodski-agent/tests/__init__.py`
- `rodski-agent/tests/conftest.py`
- `rodski-agent/tests/test_cli.py`
- `rodski-agent/tests/test_config.py`

**任务**:
1. 编写 `conftest.py`，提供 `cli_runner` fixture（Click CliRunner）
2. 编写 CLI 版本号测试
3. 编写配置加载测试

**验收**:
- [ ] `cd rodski-agent && pytest tests/ -v` 全部通过
- [ ] 至少 5 个测试用例

##### T01-006: CI 配置 (15min)

**文件**:
- `rodski-agent/Makefile`（或 `justfile`）

**任务**:
1. 编写 `make test`（运行 pytest）
2. 编写 `make lint`（运行 ruff 或 flake8）
3. 编写 `make install`（pip install -e .）

**验收**:
- [ ] `make test` 可运行
- [ ] `make install && rodski-agent --version` 成功

#### 交付物

- 可安装的 Python 包 `rodski-agent`
- `rodski-agent --version` 可运行
- `rodski_knowledge.py` 框架约束知识库（含常量 + 校验函数 + LLM 约束摘要）
- 8+ 个单元测试通过
- 完整的项目目录结构

---

### Iteration 02: Execution Agent 最小图

> **目标**: 实现 `rodski-agent run --case <path>` 能调用 rodski 执行引擎并返回结构化结果。
> **预计工时**: 8h
> **分支**: `feature/rodski-agent-execution-mvp`
> **前置依赖**: Iteration 01

#### 任务列表

##### T02-001: rodski CLI 封装 — rodski_tools.py (90min)

**文件**:
- `rodski-agent/src/rodski_agent/common/rodski_tools.py`
- `rodski-agent/tests/test_rodski_tools.py`

**任务**:
1. 实现 `rodski_run(case_path, headless, browser)` — 通过 `subprocess.run` 调用 `python rodski/ski_run.py <case_path> --headless`
2. 实现 `rodski_validate(path)` — 调用 `rodski validate <path>`（若 rodski 尚无 validate 子命令，则直接调用 XSD 校验逻辑）
3. 封装返回值为统一的 `RodskiResult` dataclass：`success: bool, exit_code: int, stdout: str, stderr: str, result_dir: str`
4. 实现 result 目录自动发现（执行后在 `result/` 下找到最新的结果目录）
5. 解析 `execution_summary.json`（若存在）和 `result_*.xml`

**验收**:
- [ ] `rodski_run("rodski-demo/DEMO/demo_full/case/demo_case.xml")` 能正确调用 rodski
- [ ] 返回值包含 exit_code 和 stdout/stderr
- [ ] 单元测试中用 Mock subprocess 验证参数传递正确

##### T02-002: 执行状态定义 — state.py (30min)

**文件**:
- `rodski-agent/src/rodski_agent/common/state.py`

**任务**:
1. 定义 `ExecutionState(TypedDict)`（与设计方案 SS4.2 对齐）
2. 包含字段：`case_path`, `max_retry`, `execution_result`, `case_results`, `screenshots`, `report`, `status`, `error`
3. 定义 `StatusEnum`：`running`, `pass`, `fail`, `partial`, `error`

**验收**:
- [ ] TypedDict 定义完整，类型标注正确
- [ ] 可被 LangGraph 的 StateGraph 使用

##### T02-003: Execution Agent 图定义 — graph.py (60min)

**文件**:
- `rodski-agent/src/rodski_agent/execution/graph.py`

**任务**:
1. 使用 LangGraph `StateGraph` 定义 Execution Agent 图
2. MVP 阶段仅包含 3 个节点：`pre_check` -> `execute` -> `parse_result` -> `report`
3. 条件边：`parse_result` → 根据结果分流到 `report`（MVP 不含 diagnose/retry）
4. 编译图为可运行的 `CompiledGraph`
5. 导出 `build_execution_graph()` 工厂函数

**验收**:
- [ ] `build_execution_graph()` 返回可调用的 CompiledGraph
- [ ] 图的节点和边定义正确（可通过 `.get_graph().nodes` 验证）

##### T02-004: 执行节点实现 — nodes.py (90min)

**文件**:
- `rodski-agent/src/rodski_agent/execution/nodes.py`

**任务**:
1. `pre_check(state)` — 使用 `rodski_knowledge.validate_directory_structure()` 检查目录完整性（case/model/data 存在），再可选调 rodski_validate 做 XSD 校验
2. `execute(state)` — 调用 `rodski_tools.rodski_run()`，将 stdout/stderr 和 result 存入 state。参考 `AGENT_INTEGRATION.md` 的 CLI 调用契约和 exit code 语义（0=成功, 1=执行失败, 2=配置错误）
3. `parse_result(state)` — 解析 result XML 或 execution_summary.json，提取 case_results 列表。解析格式参考 `AGENT_INTEGRATION.md` 输出契约
4. `report(state)` — 汇总结果，生成 report dict（total/passed/failed/cases 明细）

**验收**:
- [ ] 每个节点函数签名正确（接收 state，返回 state 更新）
- [ ] `pre_check` 使用 rodski_knowledge 校验目录结构
- [ ] `execute` 能正确调用 rodski 并根据 AGENT_INTEGRATION 契约解析 exit code
- [ ] `parse_result` 能正确解析 rodski 输出的 result XML

##### T02-005: CLI run 命令对接 (60min)

**文件**:
- `rodski-agent/src/rodski_agent/cli.py`（修改 run 子命令）

**任务**:
1. 实现 `run` 子命令完整参数：`--case`（必填）、`--max-retry`（默认 0，MVP 阶段不重试）、`--headless`、`--browser`
2. 构建初始 `ExecutionState`
3. 调用 `build_execution_graph().invoke(state)`
4. 根据 `--format` 输出结果（human-readable 或 JSON）
5. 设置正确的退出码（0=全通过，1=有失败，2=执行错误）

**验收**:
- [ ] `rodski-agent run --case rodski-demo/DEMO/demo_full/case/demo_case.xml` 能执行并输出结果
- [ ] `--format json` 输出合法 JSON
- [ ] 退出码正确反映执行结果

##### T02-006: 集成测试 (60min)

**文件**:
- `rodski-agent/tests/test_execution_graph.py`
- `rodski-agent/tests/test_cli_run.py`

**任务**:
1. 编写图级别测试：用 Mock rodski_tools 测试节点间数据流转
2. 编写 CLI 集成测试：用 CliRunner + Mock 测试完整命令行流程
3. （可选）编写真实集成测试：实际调用 rodski-demo 用例（标记为 slow，CI 可选跑）

**验收**:
- [ ] pytest 全部通过
- [ ] 至少 10 个测试用例
- [ ] 图流转测试覆盖 pre_check/execute/parse_result/report 全链路

#### 交付物

- `rodski-agent run --case <path>` 可运行
- Execution Agent LangGraph 图（MVP 版，无诊断/重试）
- rodski CLI 封装层（rodski_tools.py）
- 10+ 个测试用例

---

### Iteration 03: JSON 输出契约 + 错误处理

> **目标**: 稳定 JSON 输出格式（作为 API 契约），完善错误分类和异常处理。
> **预计工时**: 6h
> **分支**: `feature/rodski-agent-json-contract`
> **前置依赖**: Iteration 02

#### 任务列表

##### T03-001: JSON 输出契约定义 (60min)

**文件**:
- `rodski-agent/src/rodski_agent/common/contracts.py`
- `rodski-agent/schemas/output_schema.json`（JSON Schema）

**任务**:
1. 定义 `AgentOutput` dataclass：`status`, `command`, `output`, `error`, `metadata`
2. 定义每个命令的 output 结构体：`RunOutput`, `DesignOutput`, `DiagnoseOutput`
3. 编写 JSON Schema 文件，供上层 Agent 校验输出格式
4. 实现 `to_json()` / `to_human()` 序列化方法

**验收**:
- [ ] JSON 输出严格遵循 schema 定义
- [ ] 所有命令输出格式一致（status + command + output 三层结构）
- [ ] JSON Schema 文件可用 jsonschema 库校验

##### T03-002: 错误分类体系 (45min)

**文件**:
- `rodski-agent/src/rodski_agent/common/errors.py`

**任务**:
1. 定义错误分类枚举：`CONFIG_ERROR`, `VALIDATION_ERROR`, `EXECUTION_ERROR`, `PARSE_ERROR`, `LLM_ERROR`, `TIMEOUT_ERROR`
2. 定义 `AgentError` 基类，包含 `code`, `category`, `message`, `details`, `suggestion`
3. 为每种错误类型定义子类
4. 实现错误 → JSON 序列化

**验收**:
- [ ] 所有错误都有明确分类和建议性修复方案
- [ ] 错误 JSON 格式统一

##### T03-003: 全局异常处理器 (45min)

**文件**:
- `rodski-agent/src/rodski_agent/cli.py`（修改）

**任务**:
1. 在 CLI 入口添加全局异常捕获
2. 未预期异常转为 JSON 格式的 `INTERNAL_ERROR`
3. 已知异常（AgentError 子类）输出结构化错误信息
4. `--format json` 模式下所有输出（含错误）都是 JSON
5. 保证退出码语义：0=成功，1=测试失败，2=Agent 错误

**验收**:
- [ ] 任何异常都不会导致非 JSON 输出（在 json 模式下）
- [ ] 退出码正确

##### T03-004: rodski 输出解析增强 (60min)

**文件**:
- `rodski-agent/src/rodski_agent/common/result_parser.py`
- `rodski-agent/tests/test_result_parser.py`

**任务**:
1. 实现 `parse_result_xml(path)` — 解析 rodski 的 `result_*.xml`（遵循 result.xsd 结构）
2. 实现 `parse_execution_summary(path)` — 解析 `execution_summary.json`
3. 实现 `find_latest_result(result_dir)` — 在 result 目录找到最新结果
4. 提取截图路径列表
5. 处理各种边界情况（result 目录为空、XML 格式异常、文件不存在）

**验收**:
- [ ] 能正确解析 rodski-demo 实际产生的 result XML
- [ ] 边界情况不抛异常，返回有意义的错误信息
- [ ] 单元测试覆盖正常和异常路径

##### T03-005: human-readable 输出美化 (30min)

**文件**:
- `rodski-agent/src/rodski_agent/common/formatters.py`

**任务**:
1. 实现 human-readable 格式的输出渲染
2. 用颜色标注 PASS（绿）/FAIL（红）/SKIP（黄）
3. 显示执行摘要表格
4. 显示失败用例的错误详情

**验收**:
- [ ] `rodski-agent run --case ... --format human` 输出可读性好
- [ ] 终端颜色正确（支持 NO_COLOR 环境变量禁用）

##### T03-006: 契约测试 (60min)

**文件**:
- `rodski-agent/tests/test_contracts.py`
- `rodski-agent/tests/test_error_handling.py`

**任务**:
1. 编写 JSON 输出 schema 校验测试
2. 编写各种错误场景测试（case 路径不存在、rodski 执行失败、result 解析失败）
3. 编写退出码测试

**验收**:
- [ ] 所有 JSON 输出通过 schema 校验
- [ ] 错误场景测试覆盖完整
- [ ] pytest 全部通过

#### 交付物

- 稳定的 JSON 输出契约（附 JSON Schema）
- 完善的错误分类和处理体系
- result XML/JSON 解析器
- human-readable 美化输出

---

## V1 阶段

---

### Iteration 04: LLM 桥接 + 诊断节点

> **目标**: 桥接 rodski 的 LLM 能力，实现 Execution Agent 的 `diagnose` 节点。
> **预计工时**: 8h
> **分支**: `feature/rodski-agent-diagnosis`
> **前置依赖**: Iteration 02

#### 任务列表

##### T04-001: LLM 桥接层 — llm_bridge.py (90min)

**文件**:
- `rodski-agent/src/rodski_agent/common/llm_bridge.py`
- `rodski-agent/tests/test_llm_bridge.py`

**任务**:
1. 实现桥接函数，复用 `rodski/llm/client.py` 的 `LLMClient`
2. `get_llm_client()` — 加载 rodski LLM 配置并初始化客户端
3. `analyze_screenshot(image_path, question)` — 调用 `screenshot_verifier` 能力
4. `review_test_result(result_data)` — 调用 `test_reviewer` 能力
5. 处理 LLM 不可用时的降级（抛出 `LLMUnavailableError`，上层节点跳过诊断）

**验收**:
- [ ] LLM 可用时，能正确调用 rodski LLM 能力
- [ ] LLM 不可用时，抛出可预期的异常
- [ ] 配置路径正确指向 `rodski/config/llm_config.yaml`

##### T04-002: 诊断提示词设计 (90min)

**文件**:
- `rodski-agent/src/rodski_agent/execution/prompts.py`

**rodski 知识依赖**:
- `CORE_DESIGN_CONSTRAINTS.md` §8.8（问题判别器 + 四分类体系）
- `AGENT_INTEGRATION.md`（错误类型 → exit code 映射、error contract）
- `CORE_DESIGN_CONSTRAINTS.md` §1（关键字职责边界 — 帮助诊断"用错关键字"类缺陷）
- `CORE_DESIGN_CONSTRAINTS.md` §2（数据表规则 — 帮助诊断"数据引用错误"类缺陷）

**任务**:
1. 设计 `DIAGNOSE_SYSTEM_PROMPT` — 系统提示词，定义诊断助手角色。嵌入以下 rodski 知识：
   - 引用 `rodski_knowledge.RODSKI_CONSTRAINT_SUMMARY` 让 LLM 理解框架规则
   - 列出常见失败模式与 rodski 规则的映射关系：
     - `ElementNotFound` → 定位器问题（定位器类型、定位值、页面变更）
     - `XmlSchemaValidationError (SKI204)` → XML 格式违反 XSD
     - `KeywordNotSupported` → 使用了 SUPPORTED 以外的关键字
     - `DataNotFound` → 数据表名与模型名不一致 / DataID 不存在
     - HTTP 错误 → 接口模型 _method/_url 配置问题
   - 参考 `AGENT_INTEGRATION.md` 的 exit code 语义（0/1/2）帮助定位失败层级
2. 设计 `DIAGNOSE_USER_TEMPLATE` — 用户提示词模板，包含：
   - 失败用例信息（case_id, title, action, model, data, error_message）
   - 执行日志片段
   - 截图描述（如有）
   - 相关的 model.xml 元素定义和 data.xml 数据行（提供上下文，帮助 LLM 判断是用例缺陷还是产品缺陷）
3. 设计输出格式要求（JSON：root_cause, confidence, category, suggestion, evidence, recommended_action）
4. category **必须对齐** `CORE_DESIGN_CONSTRAINTS.md` §8.8.2 的四分类：
   - `CASE_DEFECT` — 用例/数据/断言定义问题
   - `ENV_DEFECT` — 环境或依赖服务异常
   - `PRODUCT_DEFECT` — 疑似产品缺陷
   - `UNKNOWN` — 证据不足，需人工确认
5. recommended_action **必须对齐** §8.8.2 的四种建议动作：`insert`/`pause`/`terminate`/`escalate`
6. 置信度约束：confidence < 0.6 时，recommended_action 只能是 `pause` 或 `escalate`（不允许自动执行高风险修复）

**验收**:
- [ ] 提示词嵌入了 rodski 约束摘要和常见失败模式映射
- [ ] 输出格式包含 category + confidence + recommended_action
- [ ] 分类体系与 CORE_DESIGN_CONSTRAINTS §8.8.2 完全一致
- [ ] 低置信度约束已在提示词中明确

##### T04-003: diagnose 节点实现 (90min)

**文件**:
- `rodski-agent/src/rodski_agent/execution/nodes.py`（新增 diagnose 函数）

**任务**:
1. 实现 `diagnose(state)` 节点
2. 从 state 提取失败用例列表和截图路径
3. 逐个失败用例调用 LLM 进行诊断
4. 合并诊断结果到 `state.diagnosis`
5. 若 LLM 不可用，跳过诊断，设置 `diagnosis = {"skipped": true, "reason": "LLM unavailable"}`
6. 截图分析：若有截图路径，附加到 LLM 请求中

**验收**:
- [ ] 失败用例能获得诊断结果
- [ ] 诊断结果包含 root_cause, confidence, suggestion
- [ ] LLM 不可用时优雅降级

##### T04-004: 更新 Execution Graph (45min)

**文件**:
- `rodski-agent/src/rodski_agent/execution/graph.py`（修改）
- `rodski-agent/src/rodski_agent/common/state.py`（新增 diagnosis 字段）

**任务**:
1. 在 `parse_result` 之后添加条件边：有失败用例 → `diagnose`，全通过 → `report`
2. `diagnose` → `report`
3. 更新 `ExecutionState` 新增 `diagnosis` 字段
4. 确保无 LLM 时图仍可执行

**验收**:
- [ ] 有失败用例时，图经过 diagnose 节点
- [ ] 全通过时，跳过 diagnose
- [ ] report 中包含诊断信息（如有）

##### T04-005: diagnose 独立命令 (45min)

**文件**:
- `rodski-agent/src/rodski_agent/cli.py`（修改 diagnose 子命令）

**任务**:
1. 实现 `rodski-agent diagnose --result <path>` 命令
2. 接受 result 目录或 execution_summary.json 路径
3. 直接调用 diagnose 节点逻辑
4. 输出诊断结果（JSON / human）

**验收**:
- [ ] `rodski-agent diagnose --result <path>` 输出诊断结果
- [ ] JSON 格式符合契约

##### T04-006: 诊断功能测试 (60min)

**文件**:
- `rodski-agent/tests/test_diagnosis.py`
- `rodski-agent/tests/fixtures/` (测试用 result 数据)

**任务**:
1. 准备测试用的 result XML 和截图 fixtures
2. Mock LLM 返回，测试诊断节点逻辑
3. 测试 LLM 不可用时的降级行为
4. 测试 diagnose CLI 命令

**验收**:
- [ ] 诊断逻辑测试覆盖正常和降级路径
- [ ] pytest 全部通过

#### 交付物

- LLM 桥接层（复用 rodski LLM 能力）
- diagnose 节点（LLM 诊断失败根因）
- `rodski-agent diagnose` 独立命令
- 诊断功能可在无 LLM 时优雅降级

---

### Iteration 05: 重试机制

> **目标**: Execution Agent 具备受控重试能力，失败用例可尝试自动修复后重跑。
> **预计工时**: 6h
> **分支**: `feature/rodski-agent-retry`
> **前置依赖**: Iteration 04

#### 任务列表

##### T05-001: retry_decide 节点 (90min)

**文件**:
- `rodski-agent/src/rodski_agent/execution/nodes.py`（新增 retry_decide 函数）

**任务**:
1. 实现 `retry_decide(state)` 节点
2. 基于 `diagnosis.category` 和 `diagnosis.confidence` 判断是否可修复：
   - `CASE_DEFECT` + confidence > 0.7 → 可修复
   - `ENV_DEFECT` → 不可修复（环境问题不在 Agent 能力范围）
   - `PRODUCT_DEFECT` → 不可修复
   - `UNKNOWN` → 不可修复
3. 检查 `retry_count < max_retry`
4. 返回 `state.retry_decision`: `"retry"` 或 `"give_up"`

**验收**:
- [ ] 分类决策逻辑正确
- [ ] 超过最大重试次数时强制 give_up
- [ ] 可修复条件清晰

##### T05-002: 简单修复策略 (90min)

**文件**:
- `rodski-agent/src/rodski_agent/execution/fixer.py`

**rodski 知识依赖**:
- `rodski_knowledge.SUPPORTED_KEYWORDS` — 修复时插入的 wait 步骤必须是合法关键字
- `rodski_knowledge.LOCATOR_TYPES` — 更新定位器时类型必须合法
- `rodski_knowledge.CASE_PHASES` — 了解在哪个阶段插入步骤合法
- `CORE_DESIGN_CONSTRAINTS.md` §13（智能等待机制 — 理解 rodski 已有的等待能力，避免冗余）

**任务**:
1. 实现 `apply_fix(state)` 函数
2. MVP 版本支持的修复策略：
   - **添加等待**: 若诊断为超时，在失败步骤前插入 `<test_step action="wait" data="3"/>`。使用 `rodski_knowledge.validate_action("wait")` 确认合法。注意：rodski 已有智能等待（§13），此处的显式 wait 用于页面加载等非元素等待场景
   - **更新定位器**: 若诊断为元素未找到，尝试使用替代定位器（需 LLM 建议）。新定位器类型必须用 `rodski_knowledge.validate_locator_type()` 校验，格式必须是 `<location type="类型">值</location>`
3. 修复后的 XML **必须通过 XSD 校验**才能进入重试循环
4. 修复前备份原始 XML
5. 记录修复动作到 `state.fixes_applied`

**验收**:
- [ ] 等待修复能正确修改 XML，修改后通过 case.xsd 校验
- [ ] 定位器修复后通过 model.xsd 校验，格式为 `<location type>` 唯一格式
- [ ] 修复后原始 XML 有备份
- [ ] fixes_applied 记录完整

##### T05-003: 更新 Execution Graph — 重试循环 (60min)

**文件**:
- `rodski-agent/src/rodski_agent/execution/graph.py`（修改）

**任务**:
1. `diagnose` → `retry_decide` 条件边
2. `retry_decide` = "retry" → `apply_fix` → `execute`（回到执行节点）
3. `retry_decide` = "give_up" → `report`
4. 确保循环有终止条件（max_retry）

**验收**:
- [ ] 重试循环工作正常
- [ ] 达到 max_retry 后终止
- [ ] 每次重试的结果都被记录

##### T05-004: CLI 参数更新 (30min)

**文件**:
- `rodski-agent/src/rodski_agent/cli.py`（修改）

**任务**:
1. `--max-retry` 参数默认值改为 3
2. 输出中显示重试次数和每次的修复动作
3. JSON 输出增加 `retries` 数组

**验收**:
- [ ] `--max-retry 0` 不重试
- [ ] `--max-retry 3` 最多重试 3 次
- [ ] 重试历史在输出中可见

##### T05-005: 重试机制测试 (60min)

**文件**:
- `rodski-agent/tests/test_retry.py`

**任务**:
1. 测试正常重试循环（Mock execute 第一次失败、第二次成功）
2. 测试达到 max_retry 后停止
3. 测试不可修复场景跳过重试
4. 测试修复策略的 XML 变更

**验收**:
- [ ] 重试逻辑全路径测试覆盖
- [ ] pytest 全部通过

#### 交付物

- retry_decide 节点（基于诊断决策是否重试）
- 简单修复策略（添加等待 + 更新定位器）
- 完整的 Execution Agent 图（pre_check → execute → parse → diagnose → retry_decide → report）

---

### Iteration 06: Design Agent 基础

> **目标**: 实现 `rodski-agent design` 命令，能根据需求描述生成**严格遵循 rodski 约束**的 XML 用例文件。
> **预计工时**: 12h（含 rodski 知识嵌入提示词和 xml_builder 约束校验）
> **分支**: `feature/rodski-agent-design`
> **前置依赖**: Iteration 03（JSON 契约）, Iteration 04（LLM 桥接）

#### 任务列表

##### T06-001: Design Agent 状态定义 (30min)

**文件**:
- `rodski-agent/src/rodski_agent/common/state.py`（新增 DesignState）

**任务**:
1. 定义 `DesignState(TypedDict)`（与设计方案 SS3.2 对齐）
2. 包含字段：`requirement`, `target_url`, `output_dir`, `test_scenarios`, `case_plan`, `test_data`, `generated_files`, `validation_errors`, `fix_attempt`, `status`, `error`
3. MVP 不含视觉探索字段（page_elements, enriched_elements 留到 V2）

**验收**:
- [ ] TypedDict 定义完整
- [ ] 与 Execution Agent 状态互不干扰

##### T06-002: Design Agent 提示词 (120min)

**文件**:
- `rodski-agent/src/rodski_agent/design/prompts.py`

**rodski 知识依赖（核心！这是 Design Agent 质量的关键）**:
- `CORE_DESIGN_CONSTRAINTS.md` §1（关键字职责划分 — type 只做 UI，send 只做接口）
- `CORE_DESIGN_CONSTRAINTS.md` §1.2（UI 原子动作不是独立关键字 — click/hover 只在数据表）
- `CORE_DESIGN_CONSTRAINTS.md` §2（数据表命名 — 模型名=表名、_verify 后缀、DataID 规则）
- `CORE_DESIGN_CONSTRAINTS.md` §3（接口测试 — _method/_url/_header_* 保留元素名）
- `CORE_DESIGN_CONSTRAINTS.md` §4（特殊值 — BLANK/NULL/NONE 语义、Return 引用限制）
- `CORE_DESIGN_CONSTRAINTS.md` §5（15 个关键字完整清单）
- `TEST_CASE_WRITING_GUIDE.md` §3（Case XML 三阶段容器 + test_step 格式）
- `TEST_CASE_WRITING_GUIDE.md` §4（Model XML 格式 — location 子节点唯一格式）
- `TEST_CASE_WRITING_GUIDE.md` §5（Data XML 格式 — datatables/datatable/row/field 结构）
- `TEST_CASE_WRITING_GUIDE.md` §6（GlobalValue XML 格式）
- `SKILL_REFERENCE.md`（每个关键字的详细参数格式和用法示例）

**任务**:
1. `ANALYZE_REQ_PROMPT` — 需求分析提示词：
   - 嵌入 `rodski_knowledge.RODSKI_CONSTRAINT_SUMMARY` 告知 LLM 框架能力边界
   - 引导 LLM 按关键字能力分类场景（UI 场景 → type+verify、接口场景 → send+verify、DB 场景 → DB+verify）
   - 输出格式：`[{"id": "S001", "title": "...", "type": "UI/API/DB", "steps": [...], "expected": [...]}]`
2. `PLAN_CASES_PROMPT` — 用例规划提示词：
   - **完整嵌入** 三阶段容器规则（pre_process 可选 → test_case 必选 → post_process 可选）
   - **完整嵌入** 关键字清单（15 个 SUPPORTED + 1 个兼容 check）及每个关键字的 action/model/data 参数模式
   - **明确约束** model 元素名 = data field 名
   - **明确约束** navigate 用于 Web/Mobile，launch 用于 Desktop
   - **明确禁止** 使用 click/hover/select 作为 action（只能在数据表字段值中）
   - 提供 `TEST_CASE_WRITING_GUIDE.md` §3.6 中的 Case XML 示例作为 few-shot
3. `DESIGN_DATA_PROMPT` — 数据设计提示词：
   - **完整嵌入** 数据表规则：datatable name = model name，row id 唯一，field name = element name
   - **完整嵌入** 特殊值语义表：空值/BLANK/NULL/NONE/click/select【值】/key_press【键】
   - **完整嵌入** Return 引用限制：`${Return[-1]}` 只在数据表字段中，不在 case data 属性中；禁止接口/DB verify 表用 `${Return[-1]}`
   - **完整嵌入** 验证表后缀规则：verify 自动查找 `{模型名}_verify` 表
   - 提供 `TEST_CASE_WRITING_GUIDE.md` §5 的 Data XML 完整示例作为 few-shot
4. `DESIGN_MODEL_PROMPT` — 模型设计提示词（新增）：
   - **完整嵌入** 定位器格式约束：唯一格式 `<location type="类型">值</location>`，禁止简化格式
   - **完整嵌入** 12 种定位器类型及其转换规则（id→#值, class→.值, css→原样...）
   - **完整嵌入** 接口模型保留元素名：_method, _url, _header_*
   - **完整嵌入** 多定位器格式（priority 属性，失败时切换）
5. 所有提示词统一从 `rodski_knowledge` 模块引入约束常量，不硬编码

**验收**:
- [ ] 每个提示词都嵌入了 `RODSKI_CONSTRAINT_SUMMARY`
- [ ] LLM 根据提示词生成的 XML 不违反任何 CORE_DESIGN_CONSTRAINTS 约束
- [ ] 提示词中的关键字清单与 `rodski_knowledge.SUPPORTED_KEYWORDS` 一致
- [ ] 提示词中的定位器类型与 `rodski_knowledge.LOCATOR_TYPES` 一致
- [ ] 每个提示词都包含 few-shot 示例（取自 TEST_CASE_WRITING_GUIDE.md）
- [ ] LLM 输出格式可被后续节点解析

##### T06-003: XML 生成器 — xml_builder.py (120min)

**文件**:
- `rodski-agent/src/rodski_agent/common/xml_builder.py`
- `rodski-agent/tests/test_xml_builder.py`

**rodski 知识依赖（xml_builder 是约束的执行者，必须硬编码所有规则）**:
- `rodski_knowledge.SUPPORTED_KEYWORDS` — action 枚举校验
- `rodski_knowledge.LOCATOR_TYPES` — 定位器类型校验
- `rodski_knowledge.CASE_PHASES` — 三阶段容器结构
- `rodski_knowledge.SPECIAL_VALUES` — 特殊值处理
- `rodski_knowledge.VERIFY_TABLE_SUFFIX` — 验证表命名
- `rodski_knowledge.validate_*` — 各类校验函数
- `rodski/schemas/*.xsd` — 最终 XSD 校验

**任务**:
1. `build_case_xml(cases)` — 生成 case XML
   - action 属性使用 `rodski_knowledge.validate_action()` 校验
   - 强制三阶段容器结构（pre_process/test_case/post_process），test_case 至少 1 个 test_step
   - execute 属性只允许 "是"/"否"
   - component_type 只允许 "界面"/"接口"/"数据库" 或空
2. `build_model_xml(models)` — 生成 model XML
   - 定位器**只使用** `<location type="...">值</location>` 子节点格式
   - type 属性使用 `rodski_knowledge.validate_locator_type()` 校验
   - 禁止生成简化格式（type+value 属性）或 locator 属性
   - 接口模型中 _method/_url/_header_* 元素使用 `static`/`field` 定位器类型
3. `build_data_xml(datatables)` — 生成 data XML（合并多表到 `<datatables>` 根元素）
   - 使用 `rodski_knowledge.validate_element_data_consistency()` 校验元素名=字段名一致性
   - row id 表内唯一校验
   - 支持特殊值：click/select【值】/key_press【键】等 UI 原子动作作为字段值
4. `build_verify_xml(datatables)` — 生成 data_verify XML
   - 使用 `rodski_knowledge.validate_verify_table_name()` 校验表名后缀
   - 检测并拒绝在接口/DB 模型的 verify 表中使用 `${Return[-1]}`（空校验禁止）
5. `build_globalvalue_xml(groups)` — 生成 globalvalue XML
   - group name 全局唯一校验
   - var 必须有 name + value
6. 所有生成的 XML 必须包含 `<?xml version="1.0" encoding="UTF-8"?>` 声明
7. 生成后**自动调用** XSD 校验（import rodski.core.xml_schema_validator 或调用 rodski validate CLI）

**验收**:
- [ ] 生成的 case XML 通过 `rodski/schemas/case.xsd` 校验
- [ ] 生成的 model XML 通过 `rodski/schemas/model.xsd` 校验
- [ ] 生成的 data XML 通过 `rodski/schemas/data.xsd` 校验
- [ ] 不使用已废弃的简化定位器格式
- [ ] 非法 action 在生成时即被拦截（不等到 XSD 校验）
- [ ] 元素名与字段名不一致时抛出明确错误
- [ ] 接口 verify 表中 ${Return[-1]} 被检测并报错

##### T06-004: Design Agent 节点实现 (120min)

**文件**:
- `rodski-agent/src/rodski_agent/design/nodes.py`

**任务**:
1. `analyze_req(state)` — 调用 LLM 分析需求，使用 `ANALYZE_REQ_PROMPT`（含 rodski 约束摘要），输出 test_scenarios
2. `plan_cases(state)` — 调用 LLM 规划用例结构，使用 `PLAN_CASES_PROMPT`（含完整关键字和容器规则），输出 case_plan。对 LLM 输出做后处理：用 `rodski_knowledge.validate_action()` 逐条检查 action 合法性
3. `design_data(state)` — 调用 LLM 设计测试数据，使用 `DESIGN_DATA_PROMPT`（含数据表规则和特殊值语义），输出 test_data。后处理：用 `rodski_knowledge.validate_element_data_consistency()` 检查元素名=字段名
4. `generate_xml(state)` — 调用 xml_builder 生成文件，写入 output_dir。xml_builder 内部使用 rodski_knowledge 约束。生成的目录结构使用 `rodski_knowledge.validate_directory_structure()` 校验
5. `validate_xml(state)` — 调用 rodski validate 校验生成的 XML（XSD 校验是最终防线）
   - 成功 → status = "success"
   - 失败 → validation_errors 记录错误，fix_attempt + 1，将 validation_errors 作为上下文传给下一轮 generate_xml
6. 每个 LLM 节点的输出都需要**二次校验**：先用 rodski_knowledge 的校验函数检查结构合规，再进入下一节点。解析失败或格式不对时重新请求（最多 2 次）

**验收**:
- [ ] analyze_req 能从自然语言提取场景列表，场景类型与 rodski 关键字能力对齐
- [ ] plan_cases 输出的 action 全部在 SUPPORTED_KEYWORDS 中
- [ ] design_data 输出的字段名与模型元素名一致
- [ ] generate_xml 生成的文件目录结构正确（case/model/data 三目录）
- [ ] validate_xml 能发现格式错误并传递给修复循环

##### T06-005: Design Agent 图定义 (60min)

**文件**:
- `rodski-agent/src/rodski_agent/design/graph.py`

**任务**:
1. 使用 LangGraph StateGraph 构建 Design Agent 图
2. 节点链路：`analyze_req` → `plan_cases` → `design_data` → `generate_xml` → `validate_xml`
3. 条件边：`validate_xml` → 校验通过 → END，校验失败 + fix_attempt < 3 → `generate_xml`（修复循环）
4. 修复循环中，将 validation_errors 作为额外上下文传给 generate_xml
5. 导出 `build_design_graph()` 工厂函数

**验收**:
- [ ] 图拓扑与设计方案 SS3.1 一致（去除视觉探索节点）
- [ ] 校验失败时能自动修复最多 3 次
- [ ] 图可正确编译和调用

##### T06-006: CLI design 命令 (45min)

**文件**:
- `rodski-agent/src/rodski_agent/cli.py`（修改 design 子命令）

**任务**:
1. 实现 `design` 子命令参数：`--requirement`（必填）、`--url`（可选，MVP 暂不用）、`--output`（必填，输出目录）
2. 构建 DesignState，调用 design graph
3. 输出生成结果（JSON / human）
4. 生成后的目录结构必须遵循 `product/项目/模块` 三层约束

**验收**:
- [ ] `rodski-agent design --requirement "登录测试" --output cassmall/login/` 生成 XML 文件
- [ ] 输出目录下有 case/ model/ data/ 三个目录
- [ ] 生成的 XML 格式正确

##### T06-007: Design Agent 测试 (90min)

**文件**:
- `rodski-agent/tests/test_design_graph.py`
- `rodski-agent/tests/test_xml_builder.py`（扩展）

**任务**:
1. Mock LLM 返回，测试 analyze_req → plan_cases → design_data 数据流
2. 测试 xml_builder 生成的 XML 通过 XSD 校验
3. 测试校验失败时的修复循环
4. 测试 CLI design 命令的端到端流程（Mock LLM）

**验收**:
- [ ] 设计流程全链路测试覆盖
- [ ] 生成的 XML 能通过 rodski validate
- [ ] pytest 全部通过

#### 交付物

- `rodski-agent design` 命令可用
- Design Agent LangGraph 图（无视觉探索）
- XML 生成器（xml_builder.py）
- 设计提示词模板
- 生成的 XML 通过 XSD 校验

---

### Iteration 07: Pipeline 命令

> **目标**: 实现 `rodski-agent pipeline` 命令，串联 Design Agent 和 Execution Agent。
> **预计工时**: 5h
> **分支**: `feature/rodski-agent-pipeline`
> **前置依赖**: Iteration 05（重试）, Iteration 06（Design Agent）

#### 任务列表

##### T07-001: Pipeline 编排器 (90min)

**文件**:
- `rodski-agent/src/rodski_agent/pipeline/orchestrator.py`

**任务**:
1. 实现 `PipelineOrchestrator` 类
2. 串联逻辑：Design Agent 完成 → 获取生成的 case 路径 → Execution Agent 执行
3. 中间状态传递：Design 输出的 `generated_files` → Execution 输入的 `case_path`
4. 阶段性输出：每个阶段（design/run）完成后输出中间结果
5. 任一阶段失败时的中止策略

**验收**:
- [ ] Design → Execution 串联成功
- [ ] 文件系统是两个 Agent 的通道（不走内存传递 XML 内容）
- [ ] 中间状态可观测

##### T07-002: CLI pipeline 命令 (60min)

**文件**:
- `rodski-agent/src/rodski_agent/cli.py`（修改 pipeline 子命令）

**任务**:
1. 实现 `pipeline` 子命令参数：`--requirement`、`--url`、`--output`、`--max-retry`
2. 调用 PipelineOrchestrator
3. 输出合并报告（design 生成了什么 + run 执行结果如何）
4. JSON 输出包含 `design_output` 和 `run_output` 两个子节点

**验收**:
- [ ] `rodski-agent pipeline --requirement "登录测试" --output cassmall/login/` 完整执行
- [ ] 输出同时包含设计和执行结果

##### T07-003: config show 命令 (30min)

**文件**:
- `rodski-agent/src/rodski_agent/cli.py`（修改 config 子命令）

**任务**:
1. 实现 `rodski-agent config show` — 显示当前生效配置
2. 显示配置来源（文件 / 环境变量 / 默认值）
3. 敏感信息脱敏（API key 只显示前后几位）

**验收**:
- [ ] 配置信息完整展示
- [ ] API key 已脱敏

##### T07-004: Pipeline 测试 (60min)

**文件**:
- `rodski-agent/tests/test_pipeline.py`

**任务**:
1. 测试 Design → Execution 串联（Mock 两个 Agent）
2. 测试 Design 失败时 Pipeline 中止
3. 测试 Execution 全通过和部分失败的输出
4. 测试 CLI pipeline 命令端到端

**验收**:
- [ ] 串联逻辑测试覆盖
- [ ] pytest 全部通过

##### T07-005: V1.0 端到端验收 (60min)

**文件**:
- `rodski-agent/tests/test_e2e.py`（标记为 @pytest.mark.e2e）

**任务**:
1. 用 rodski-demo 的登录场景做端到端测试
2. `rodski-agent run --case rodski-demo/DEMO/demo_full/case/demo_case.xml` 真实执行
3. 验证 JSON 输出格式正确
4. 验证退出码正确
5. 记录 V1.0 release checklist

**验收**:
- [ ] 端到端测试通过
- [ ] V1.0 所有功能可用：run / design / pipeline / diagnose / config

#### 交付物

- `rodski-agent pipeline` 命令可用
- `rodski-agent config show` 命令可用
- V1.0 完整功能集端到端验证通过
- 所有命令的 JSON 输出遵循统一契约

---

## V2 阶段

---

### Iteration 08: 视觉探索

> **目标**: Design Agent 具备页面探索能力，通过 OmniParser 识别页面元素并生成视觉定位器。
> **预计工时**: 8h
> **分支**: `feature/rodski-agent-vision`
> **前置依赖**: Iteration 06（Design Agent）

#### 任务列表

##### T08-001: OmniParser 客户端封装 (60min)

**文件**:
- `rodski-agent/src/rodski_agent/common/omniparser_client.py`
- `rodski-agent/tests/test_omniparser.py`

**任务**:
1. 封装 OmniParser HTTP API 调用
2. `parse_screenshot(image_path)` → 返回元素列表 `[{label, bbox, confidence, text}]`
3. 配置从 `agent_config.yaml` 读取 OmniParser URL
4. 超时处理和重试
5. OmniParser 不可用时抛出 `OmniParserUnavailableError`

**验收**:
- [ ] 能正确调用 OmniParser API
- [ ] 返回结构化的元素列表
- [ ] 超时和错误处理正确

##### T08-002: 截图采集工具 (45min)

**文件**:
- `rodski-agent/src/rodski_agent/common/screenshot.py`

**任务**:
1. `capture_web_page(url, output_path)` — 使用 Playwright 截取页面
2. `capture_desktop(output_path)` — 使用 pyautogui 截取桌面
3. 截图存储到临时目录，返回路径

**验收**:
- [ ] Web 截图功能可用
- [ ] 截图文件存在且可读

##### T08-003: explore_page 节点 (90min)

**文件**:
- `rodski-agent/src/rodski_agent/design/nodes.py`（新增 explore_page 函数）

**任务**:
1. 实现 `explore_page(state)` 节点
2. 流程：截取页面 → 调用 OmniParser → 获取元素列表
3. 将元素列表存入 `state.page_elements`
4. 若 OmniParser 不可用，跳过探索，使用纯 LLM 方式（fallback）

**验收**:
- [ ] 能从 URL 探索出页面元素
- [ ] 元素列表包含 label, bbox, text 信息
- [ ] OmniParser 不可用时优雅降级

##### T08-004: identify_elem 节点 — LLM 语义增强 (90min)

**文件**:
- `rodski-agent/src/rodski_agent/design/nodes.py`（新增 identify_elem 函数）
- `rodski-agent/src/rodski_agent/design/prompts.py`（新增提示词）

**任务**:
1. 实现 `identify_elem(state)` 节点
2. 将 OmniParser 识别的元素 + 截图送给 LLM 做语义增强
3. 输出 `enriched_elements`：每个元素带有语义标签（如 "用户名输入框"）和推荐定位器类型
4. 为每个元素选择最佳定位器：有稳定属性 → xpath/css，无属性 → vision/ocr
5. 生成 model XML 友好的元素名（遵循 element name = data field name 约束）

**验收**:
- [ ] LLM 能正确标注元素语义
- [ ] 定位器选择策略合理（传统优先，视觉兜底）
- [ ] 元素名合法（无特殊字符，可用作 data field name）

##### T08-005: 更新 Design Graph (45min)

**文件**:
- `rodski-agent/src/rodski_agent/design/graph.py`（修改）
- `rodski-agent/src/rodski_agent/common/state.py`（更新 DesignState）

**任务**:
1. 在 `analyze_req` 之后添加条件边：有 target_url → `explore_page` → `identify_elem`，无 URL → 跳过
2. `identify_elem` → `plan_cases`
3. `plan_cases` 现在可以使用 enriched_elements 信息
4. 更新 DesignState 新增 page_elements, enriched_elements 字段

**验收**:
- [ ] 提供 URL 时，图经过探索节点
- [ ] 不提供 URL 时，跳过探索
- [ ] 探索结果正确传递给后续节点

##### T08-006: 视觉探索测试 (60min)

**文件**:
- `rodski-agent/tests/test_vision.py`

**任务**:
1. Mock OmniParser 返回，测试 explore_page 节点
2. Mock LLM 返回，测试 identify_elem 节点
3. 测试带 URL 的完整 design 流程
4. 测试 OmniParser 不可用时的降级

**验收**:
- [ ] 视觉探索全链路测试覆盖
- [ ] pytest 全部通过

#### 交付物

- OmniParser 集成
- explore_page 和 identify_elem 节点
- 视觉定位器生成能力
- Design Agent 完整图（含视觉探索）

---

### Iteration 09: 智能修复

> **目标**: Execution Agent 能根据诊断结果自动修复 XML 文件（主要是定位器更新）。
> **预计工时**: 8h
> **分支**: `feature/rodski-agent-smart-fix`
> **前置依赖**: Iteration 05（重试）, Iteration 08（视觉探索）

#### 任务列表

##### T09-001: 修复策略框架 (60min)

**文件**:
- `rodski-agent/src/rodski_agent/execution/fixer.py`（重构）

**任务**:
1. 定义 `FixStrategy` 基类（Strategy 模式）
2. 定义 `FixResult` dataclass：`applied: bool, description: str, files_modified: list[str]`
3. 策略注册机制：根据 diagnosis.category 选择策略
4. 修复优先级：简单修复（等待）→ 定位器修复 → XML 重写

**验收**:
- [ ] Strategy 模式结构清晰
- [ ] 策略选择逻辑正确

##### T09-002: 定位器修复策略 (120min)

**文件**:
- `rodski-agent/src/rodski_agent/execution/strategies/locator_fix.py`

**任务**:
1. 实现 `LocatorFixStrategy`
2. 流程：截取当前页面 → OmniParser 识别 → LLM 匹配失败元素 → 更新 model.xml
3. 解析 model.xml 找到失败元素的 `<location>` 节点
4. 用新的定位器值替换旧值
5. 支持添加多定位器（priority 备选）
6. 修改后重新校验 model.xml 通过 model.xsd

**验收**:
- [ ] 能识别并替换失败的定位器
- [ ] 修改后的 model.xml 通过 XSD 校验
- [ ] 定位器格式遵循 `<location type="类型">值</location>`

##### T09-003: 等待时间修复策略 (45min)

**文件**:
- `rodski-agent/src/rodski_agent/execution/strategies/wait_fix.py`

**任务**:
1. 实现 `WaitFixStrategy`
2. 在失败步骤前插入 `<test_step action="wait" data="3"/>`
3. 或修改 globalvalue 中的 WaitTime
4. 修改后的 case XML 通过 case.xsd 校验

**验收**:
- [ ] 等待步骤正确插入
- [ ] 修改后 XML 通过校验

##### T09-004: 数据修复策略 (60min)

**文件**:
- `rodski-agent/src/rodski_agent/execution/strategies/data_fix.py`

**任务**:
1. 实现 `DataFixStrategy`
2. 场景：验证失败（expected != actual）→ 可能是期望值需要更新
3. 调用 LLM 分析实际值与期望值的差异
4. 若 LLM 判断是"期望值过时"，更新 data_verify.xml
5. 明确不自动修改"不应该改"的期望值（避免掩盖真实缺陷）

**验收**:
- [ ] 能识别期望值过时的情况
- [ ] 不会错误地修改真实断言失败

##### T09-005: 修复策略集成到重试循环 (45min)

**文件**:
- `rodski-agent/src/rodski_agent/execution/nodes.py`（修改 apply_fix）
- `rodski-agent/src/rodski_agent/execution/graph.py`（调整边）

**任务**:
1. `apply_fix` 节点调用策略框架选择并执行修复
2. 修复结果记录到 `state.fixes_applied`
3. 多次重试时，策略可以升级（先等待 → 再定位器 → 再数据）

**验收**:
- [ ] 重试循环中使用正确的修复策略
- [ ] 策略升级逻辑正常

##### T09-006: 智能修复测试 (90min)

**文件**:
- `rodski-agent/tests/test_fixer.py`
- `rodski-agent/tests/test_strategies.py`

**任务**:
1. 为每种修复策略编写独立测试
2. 测试策略选择逻辑
3. 测试修复后 XML 的正确性
4. 端到端：执行失败 → 诊断 → 修复 → 重试成功

**验收**:
- [ ] 每种策略都有测试覆盖
- [ ] 修复后 XML 通过 XSD 校验
- [ ] pytest 全部通过

#### 交付物

- 策略模式的修复框架
- 三种修复策略（定位器 / 等待 / 数据）
- 修复 → 重试完整循环
- 修复后 XML 保证通过 XSD 校验

---

### Iteration 10: MCP Server 封装

> **目标**: 将 rodski-agent 功能封装为 MCP Server，供 Claude Code / 小龙虾等 Harness Agent 通过 MCP 协议调用。
> **预计工时**: 7h
> **分支**: `feature/rodski-agent-mcp`
> **前置依赖**: Iteration 07（Pipeline）

#### 任务列表

##### T10-001: MCP Server 骨架 (60min)

**文件**:
- `rodski-agent/src/rodski_agent/mcp/__init__.py`
- `rodski-agent/src/rodski_agent/mcp/server.py`
- `rodski-agent/pyproject.toml`（新增 mcp 依赖）

**任务**:
1. 添加 `mcp` 依赖（`mcp[server]`）
2. 实现 MCP Server 框架，注册工具列表
3. 实现 `rodski-agent serve` CLI 命令启动 MCP Server
4. 配置 stdio 传输模式（Claude Code 默认使用 stdio）

**验收**:
- [ ] `rodski-agent serve` 启动 MCP Server
- [ ] Server 能响应 MCP 初始化请求

##### T10-002: MCP 工具 — run (60min)

**文件**:
- `rodski-agent/src/rodski_agent/mcp/tools.py`

**任务**:
1. 注册 `rodski_run` 工具
2. 输入参数：`case_path`, `max_retry`, `headless`
3. 调用 Execution Agent 图
4. 返回结构化 JSON 结果

**验收**:
- [ ] MCP 调用 `rodski_run` 返回正确结果
- [ ] 参数验证正确

##### T10-003: MCP 工具 — design (60min)

**文件**:
- `rodski-agent/src/rodski_agent/mcp/tools.py`（追加）

**任务**:
1. 注册 `rodski_design` 工具
2. 输入参数：`requirement`, `url`(可选), `output_dir`
3. 调用 Design Agent 图
4. 返回生成的文件列表和摘要

**验收**:
- [ ] MCP 调用 `rodski_design` 返回正确结果

##### T10-004: MCP 工具 — pipeline + diagnose (45min)

**文件**:
- `rodski-agent/src/rodski_agent/mcp/tools.py`（追加）

**任务**:
1. 注册 `rodski_pipeline` 工具
2. 注册 `rodski_diagnose` 工具
3. 各调用对应的内部逻辑

**验收**:
- [ ] 所有 4 个工具都可通过 MCP 调用

##### T10-005: MCP 资源 — 配置和文档 (45min)

**文件**:
- `rodski-agent/src/rodski_agent/mcp/resources.py`

**任务**:
1. 注册资源：`rodski://config` — 当前配置
2. 注册资源：`rodski://keywords` — 关键字参考（从 SKILL_REFERENCE.md 读取）
3. 注册资源：`rodski://guide` — 用例编写指南摘要

**验收**:
- [ ] Harness Agent 可通过 MCP 获取框架参考文档

##### T10-006: Claude Code 集成配置 (30min)

**文件**:
- `rodski-agent/.mcp.json`（Claude Code MCP 配置）
- `rodski-agent/README.md`（更新）

**任务**:
1. 编写 `.mcp.json` 配置文件
2. 文档化 Claude Code 集成步骤
3. 提供使用示例

**验收**:
- [ ] Claude Code 能发现并使用 rodski-agent MCP Server

##### T10-007: MCP Server 测试 (90min)

**文件**:
- `rodski-agent/tests/test_mcp.py`

**任务**:
1. 测试 MCP Server 启动和初始化
2. 测试每个工具的调用和返回
3. 测试资源访问
4. 测试错误处理（工具调用失败时的 MCP 错误响应）

**验收**:
- [ ] MCP 工具测试全覆盖
- [ ] pytest 全部通过

#### 交付物

- MCP Server 实现（4 个工具 + 3 个资源）
- Claude Code 集成配置
- `rodski-agent serve` 命令
- V2.0 完整功能集

---

## 约束检查清单

每个迭代在提交前，必须对照以下约束检查：

| # | 约束项 | 检查点 | 来源文档 |
|---|--------|--------|---------|
| 1 | 关键字职责划分 | xml_builder 生成的 case XML 中 action 只使用 SUPPORTED 关键字 | CORE_DESIGN_CONSTRAINTS §1、§5 |
| 2 | UI 原子动作非独立关键字 | click/hover 等只出现在数据表 field 值中，不在 action 属性 | CORE_DESIGN_CONSTRAINTS §1.2 |
| 3 | SUPPORTED 关键字清单同步 | `rodski_knowledge.SUPPORTED_KEYWORDS` 与 rodski 源码一致 | CORE_DESIGN_CONSTRAINTS §5 |
| 4 | 目录结构 | design 命令生成的目录遵循 case/model/data 固定结构 | CORE_DESIGN_CONSTRAINTS §6 |
| 5 | XSD 校验 | 所有生成的 XML 通过对应 XSD 校验 | CORE_DESIGN_CONSTRAINTS §7.0 |
| 6 | 元素名=字段名 | xml_builder 确保 model element name 与 data field name 一致 | CORE_DESIGN_CONSTRAINTS §2.4 |
| 7 | 定位器格式 | 只使用 `<location type="类型">值</location>` 格式，禁止简化格式 | CORE_DESIGN_CONSTRAINTS §2.5.3 |
| 8 | 验证表命名 | verify 数据表名为 `{模型名}_verify` | CORE_DESIGN_CONSTRAINTS §2.2 |
| 9 | Return 引用限制 | `${Return[-1]}` 不在 case data 属性，不在接口/DB verify 表 | CORE_DESIGN_CONSTRAINTS §4.2、§4.3 |
| 10 | 诊断分类体系 | 诊断输出 category 为 CASE/ENV/PRODUCT_DEFECT/UNKNOWN 之一 | CORE_DESIGN_CONSTRAINTS §8.8.2 |
| 11 | 提示词约束嵌入 | 所有 LLM 提示词包含 `RODSKI_CONSTRAINT_SUMMARY` | 设计方案 §10.6 |
| 12 | 测试分层 | 单元测试用 pytest，验收测试在 rodski-demo | CORE_DESIGN_CONSTRAINTS §9 |
| 13 | 示例目录 | 只使用 rodski-demo，不使用 rodski/examples | CLAUDE.md |
| 14 | JSON 契约 | CLI JSON 输出格式一旦发布不可随意变更 | 设计方案 §11.4 |

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| rodski 尚无 validate 子命令 | Iteration 02 中 rodski_tools.rodski_validate 无法直接 CLI 调用 | 先直接 import rodski.core.xml_schema_validator 做校验，后续 rodski 补上 CLI |
| LLM API 不稳定 | Iteration 04~09 中诊断/设计功能不可用 | 所有 LLM 依赖路径都有降级策略；测试用 Mock |
| OmniParser 服务不可达 | Iteration 08 视觉探索不可用 | explore_page 节点有 fallback（纯 LLM 方式） |
| LangGraph 版本兼容 | API 可能在 0.x 阶段变更 | 锁定 langgraph 版本，在 pyproject.toml 中指定最小版本 |
| Design Agent 生成的 XML 质量 | LLM 可能生成不合法的 XML | validate_xml 节点 + 最多 3 次修复循环 + 详细的提示词约束 + rodski_knowledge 预校验 |
| rodski 约束知识漂移 | rodski 升级后 SUPPORTED_KEYWORDS 等变更，rodski_knowledge.py 未同步 | 在 T01-004 测试中加入与 rodski 源码的一致性检查；CI 跑同步测试 |

---

## 里程碑时间线（建议）

| 里程碑 | 迭代范围 | 版本 | 预计完成 |
|--------|---------|------|---------|
| **MVP Release** | 01~03 | v0.1.0 | +1 周 |
| **V1.0 Release** | 04~07 | v1.0.0 | +3 周 |
| **V2.0 Release** | 08~10 | v2.0.0 | +5 周 |

---

*文档版本: v1.1 | 创建日期: 2026-04-13 | 更新日期: 2026-04-13 | 基于设计方案: .pb/design/rodski-agent-design.md*
*v1.1 变更: 新增 T01-004 rodski_knowledge.py 知识库任务；Iteration 04/05/06 补充 rodski 知识依赖说明；约束检查清单扩展至 14 条*
