# Iteration 03: JSON 输出契约 + 错误处理

## 目标

稳定 JSON 输出格式（作为 API 契约），完善错误分类和异常处理。

## 前置依赖

- Iteration 02（Execution Agent 最小图）

## 任务列表

### T03-001: JSON 输出契约定义 (60min)

- **文件**:
  - `rodski-agent/src/rodski_agent/common/contracts.py`
  - `rodski-agent/schemas/output_schema.json`（JSON Schema）
- **描述**: 定义 `AgentOutput` dataclass（status, command, output, error, metadata）。定义每个命令的 output 结构体：`RunOutput`、`DesignOutput`、`DiagnoseOutput`。编写 JSON Schema 文件供上层 Agent 校验输出格式。实现 `to_json()` / `to_human()` 序列化方法。
- **验收标准**:
  - [ ] JSON 输出严格遵循 schema 定义
  - [ ] 所有命令输出格式一致（status + command + output 三层结构）
  - [ ] JSON Schema 文件可用 jsonschema 库校验

### T03-002: 错误分类体系 (45min)

- **文件**: `rodski-agent/src/rodski_agent/common/errors.py`
- **描述**: 定义错误分类枚举：`CONFIG_ERROR`、`VALIDATION_ERROR`、`EXECUTION_ERROR`、`PARSE_ERROR`、`LLM_ERROR`、`TIMEOUT_ERROR`。定义 `AgentError` 基类（code, category, message, details, suggestion）。为每种错误类型定义子类。实现错误到 JSON 序列化。
- **验收标准**:
  - [ ] 所有错误都有明确分类和建议性修复方案
  - [ ] 错误 JSON 格式统一

### T03-003: 全局异常处理器 (45min)

- **文件**: `rodski-agent/src/rodski_agent/cli.py`（修改）
- **描述**: 在 CLI 入口添加全局异常捕获。未预期异常转为 JSON 格式的 `INTERNAL_ERROR`。已知异常（AgentError 子类）输出结构化错误信息。`--format json` 模式下所有输出（含错误）都是 JSON。保证退出码语义：0=成功，1=测试失败，2=Agent 错误。
- **验收标准**:
  - [ ] 任何异常都不会导致非 JSON 输出（在 json 模式下）
  - [ ] 退出码正确

### T03-004: rodski 输出解析增强 (60min)

- **文件**:
  - `rodski-agent/src/rodski_agent/common/result_parser.py`
  - `rodski-agent/tests/test_result_parser.py`
- **描述**: 实现 `parse_result_xml(path)` 解析 rodski 的 `result_*.xml`（遵循 result.xsd 结构）。实现 `parse_execution_summary(path)` 解析 `execution_summary.json`。实现 `find_latest_result(result_dir)` 在 result 目录找到最新结果。提取截图路径列表。处理各种边界情况（result 目录为空、XML 格式异常、文件不存在）。
- **rodski 知识依赖**:
  - `rodski/schemas/result.xsd` -- result XML 结构
  - `rodski/docs/AGENT_INTEGRATION.md` -- execution_summary.json 结构
- **验收标准**:
  - [ ] 能正确解析 rodski-demo 实际产生的 result XML
  - [ ] 边界情况不抛异常，返回有意义的错误信息
  - [ ] 单元测试覆盖正常和异常路径

### T03-005: human-readable 输出美化 (30min)

- **文件**: `rodski-agent/src/rodski_agent/common/formatters.py`
- **描述**: 实现 human-readable 格式的输出渲染。用颜色标注 PASS（绿）/FAIL（红）/SKIP（黄）。显示执行摘要表格和失败用例的错误详情。
- **验收标准**:
  - [ ] `rodski-agent run --case ... --format human` 输出可读性好
  - [ ] 终端颜色正确（支持 NO_COLOR 环境变量禁用）

### T03-006: 契约测试 (60min)

- **文件**:
  - `rodski-agent/tests/test_contracts.py`
  - `rodski-agent/tests/test_error_handling.py`
- **描述**: 编写 JSON 输出 schema 校验测试。编写各种错误场景测试（case 路径不存在、rodski 执行失败、result 解析失败）。编写退出码测试。
- **验收标准**:
  - [ ] 所有 JSON 输出通过 schema 校验
  - [ ] 错误场景测试覆盖完整
  - [ ] pytest 全部通过

## 交付物

- 稳定的 JSON 输出契约（附 JSON Schema）
- 完善的错误分类和处理体系
- result XML/JSON 解析器
- human-readable 美化输出

## 约束检查

- [ ] JSON 输出契约一旦发布不可随意变更（设计方案 SS11.4）
- [ ] 退出码语义（0=成功，1=测试失败，2=Agent 错误）与 rodski exit code 对齐
- [ ] result XML 解析遵循 `rodski/schemas/result.xsd` 结构
- [ ] execution_summary.json 解析遵循 `AGENT_INTEGRATION.md` 定义
- [ ] 错误分类中 EXECUTION_ERROR 与 rodski exit code=1 对应，CONFIG_ERROR 与 exit code=2 对应
