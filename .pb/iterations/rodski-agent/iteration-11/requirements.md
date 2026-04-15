# Iteration 11: 架构整改

## 目标

修复 v2.0.0 中 8 个架构问题，提升代码质量和可维护性。版本升至 v2.1.0。

## 前置依赖

- Iteration 10（V2.0 功能完整）

## 变更清单

### Task A: 删除 MCP Server

- **删除文件**: `mcp_server.py`、`tests/test_mcp_server.py`
- **修改文件**: `pyproject.toml`（删 mcp entry point 和依赖）、`common/errors.py`（删 MCPUnavailableError）
- **理由**: 当前仅保留 CLI 接口，MCP 方案搁置

### Task B: 移除 SimpleGraph，仅用 LangGraph

- **修改文件**: `execution/graph.py`、`design/graph.py`、对应测试
- **理由**: 消除双图引擎并存，统一用 LangGraph StateGraph

### Task C: 重构 LLM 配置，rodski-agent 自建 LLM 客户端

- **修改文件**: `common/config.py`、`common/llm_bridge.py`、`config/agent_config.yaml`
- **理由**: rodski-agent 不再通过 sys.path 复用 rodski 的 LLM 配置，自建 langchain ChatModel 客户端。设计/执行 agent 各有独立 LLM 配置（temperature/max_tokens 不同）

### Task D: 版本协商 — rodski 新增 capabilities 命令

- **新建文件**: `rodski/rodski_cli/capabilities.py`
- **修改文件**: `rodski/cli_main.py`、`rodski-agent/common/rodski_tools.py`
- **理由**: rodski-agent 通过 `rodski capabilities` 获取 rodski 版本和能力清单，实现版本协商

### Task E: 移除 LLM 优雅降级

- **修改文件**: `design/nodes.py`、`design/visual.py`、`execution/nodes.py`、对应测试
- **理由**: LLM 不可用时直接报错，不再用 fallback 函数静默降级

### Task F: OmniParser 不降级 + 修复双路径 bug

- **修改文件**: `common/omniparser_client.py`、`design/visual.py`、`config/agent_config.yaml`
- **理由**: OmniParser 已独立部署，不可用时直接报错。修复 URL 末尾重复拼接 `/parse` 的 bug

### Task G: 动态约束 — rodski_knowledge.py 从 rodski 获取

- **修改文件**: `common/rodski_knowledge.py`、`tests/test_rodski_knowledge.py`
- **理由**: 新增 `RodskiConstraints` 单例类，首次访问时调用 `rodski_capabilities()` 动态获取关键字/定位器列表，硬编码常量保留为 fallback

### Task H: Pipeline 编排增强

- **修改文件**: `pipeline/orchestrator.py`、`cli.py`、`tests/test_pipeline.py`
- **理由**: 新增验证门（Design 后调 `rodski_validate` 校验所有 XML）、多 case 并行执行（ThreadPoolExecutor）、结果聚合

### Task I: 版本号 + 迭代记录

- **修改文件**: `pyproject.toml`、`__init__.py`
- **理由**: 版本号 2.0.0 → 2.1.0

## 交付物

- 架构整改后的 rodski-agent v2.1.0
- rodski capabilities 命令
- 424 个单元测试全部通过

## 约束检查

- [x] LangGraph 为唯一图引擎，无 SimpleGraph 残留
- [x] rodski-agent 自建 LLM 客户端，不复用 rodski LLM 配置
- [x] LLM/OmniParser 不可用时直接报错，无静默降级
- [x] `rodski capabilities` 输出 JSON 格式能力清单
- [x] `RodskiConstraints` 单例优先查动态约束，fallback 到硬编码
- [x] Pipeline 验证门在 Design 和 Execution 之间
- [x] MCP Server 已删除
- [x] 所有测试通过
