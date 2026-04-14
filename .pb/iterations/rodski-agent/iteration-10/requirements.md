# Iteration 10: MCP Server 封装

## 目标

将 rodski-agent 功能封装为 MCP Server，供 Claude Code / 其他 Harness Agent 通过 MCP 协议调用。

## 前置依赖

- Iteration 07（Pipeline 命令 -- V1.0 功能完整）

## 任务列表

### T10-001: MCP Server 骨架 (60min)

- **文件**:
  - `rodski-agent/src/rodski_agent/mcp/__init__.py`
  - `rodski-agent/src/rodski_agent/mcp/server.py`
  - `rodski-agent/pyproject.toml`（新增 mcp 依赖）
- **描述**: 添加 `mcp[server]` 依赖。实现 MCP Server 框架，注册工具列表。实现 `rodski-agent serve` CLI 命令启动 MCP Server。配置 stdio 传输模式（Claude Code 默认使用 stdio）。
- **验收标准**:
  - [ ] `rodski-agent serve` 启动 MCP Server
  - [ ] Server 能响应 MCP 初始化请求

### T10-002: MCP 工具 -- run (60min)

- **文件**: `rodski-agent/src/rodski_agent/mcp/tools.py`
- **描述**: 注册 `rodski_run` 工具。输入参数：`case_path`、`max_retry`、`headless`。调用 Execution Agent 图。返回结构化 JSON 结果。
- **验收标准**:
  - [ ] MCP 调用 `rodski_run` 返回正确结果
  - [ ] 参数验证正确

### T10-003: MCP 工具 -- design (60min)

- **文件**: `rodski-agent/src/rodski_agent/mcp/tools.py`（追加）
- **描述**: 注册 `rodski_design` 工具。输入参数：`requirement`、`url`（可选）、`output_dir`。调用 Design Agent 图。返回生成的文件列表和摘要。
- **验收标准**:
  - [ ] MCP 调用 `rodski_design` 返回正确结果

### T10-004: MCP 工具 -- pipeline + diagnose (45min)

- **文件**: `rodski-agent/src/rodski_agent/mcp/tools.py`（追加）
- **描述**: 注册 `rodski_pipeline` 工具和 `rodski_diagnose` 工具。各调用对应的内部逻辑。
- **验收标准**:
  - [ ] 所有 4 个工具都可通过 MCP 调用

### T10-005: MCP 资源 -- 配置和文档 (45min)

- **文件**: `rodski-agent/src/rodski_agent/mcp/resources.py`
- **描述**: 注册 3 个资源：
  1. `rodski://config` -- 当前配置
  2. `rodski://keywords` -- 关键字参考（从 SKILL_REFERENCE.md 读取）
  3. `rodski://guide` -- 用例编写指南摘要
- **验收标准**:
  - [ ] Harness Agent 可通过 MCP 获取框架参考文档

### T10-006: Claude Code 集成配置 (30min)

- **文件**:
  - `rodski-agent/.mcp.json`（Claude Code MCP 配置）
  - `rodski-agent/README.md`（更新）
- **描述**: 编写 `.mcp.json` 配置文件。文档化 Claude Code 集成步骤。提供使用示例。
- **验收标准**:
  - [ ] Claude Code 能发现并使用 rodski-agent MCP Server

### T10-007: MCP Server 测试 (90min)

- **文件**: `rodski-agent/tests/test_mcp.py`
- **描述**: 测试 MCP Server 启动和初始化。测试每个工具的调用和返回。测试资源访问。测试错误处理（工具调用失败时的 MCP 错误响应）。
- **验收标准**:
  - [ ] MCP 工具测试全覆盖
  - [ ] pytest 全部通过

## 交付物

- MCP Server 实现（4 个工具 + 3 个资源）
- Claude Code 集成配置（`.mcp.json`）
- `rodski-agent serve` 命令
- V2.0 完整功能集

## 约束检查

- [ ] MCP 工具的 JSON 输出遵循 Iteration 03 定义的输出契约
- [ ] MCP run 工具的 exit code 语义与 CLI 一致
- [ ] MCP design 工具生成的 XML 遵循所有 rodski 约束（由内部 Design Agent 保证）
- [ ] MCP 资源 `rodski://keywords` 内容与 `SKILL_REFERENCE.md` 一致
- [ ] MCP 资源 `rodski://guide` 内容与 `TEST_CASE_WRITING_GUIDE.md` 摘要一致
- [ ] stdio 传输模式兼容 Claude Code 的 MCP 调用方式
- [ ] 错误响应遵循 MCP 协议规范
