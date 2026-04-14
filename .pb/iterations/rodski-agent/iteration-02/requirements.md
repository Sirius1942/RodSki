# Iteration 02: Execution Agent 最小图

## 目标

实现 `rodski-agent run --case <path>` 能调用 rodski 执行引擎并返回结构化结果。

## 前置依赖

- Iteration 01（项目骨架 + CLI 框架 + 知识库）

## 任务列表

### T02-001: rodski CLI 封装 -- rodski_tools.py (90min)

- **文件**:
  - `rodski-agent/src/rodski_agent/common/rodski_tools.py`
  - `rodski-agent/tests/test_rodski_tools.py`
- **描述**: 实现 `rodski_run(case_path, headless, browser)` 通过 `subprocess.run` 调用 `python rodski/ski_run.py`。实现 `rodski_validate(path)` 调用 XSD 校验逻辑。封装返回值为 `RodskiResult` dataclass（success, exit_code, stdout, stderr, result_dir）。实现 result 目录自动发现，解析 `execution_summary.json` 和 `result_*.xml`。
- **rodski 知识依赖**:
  - `rodski/docs/AGENT_INTEGRATION.md` -- CLI 调用契约、exit code 语义（0=成功, 1=执行失败, 2=配置错误）
- **验收标准**:
  - [ ] `rodski_run("rodski-demo/DEMO/demo_full/case/demo_case.xml")` 能正确调用 rodski
  - [ ] 返回值包含 exit_code 和 stdout/stderr
  - [ ] 单元测试中用 Mock subprocess 验证参数传递正确

### T02-002: 执行状态定义 -- state.py (30min)

- **文件**: `rodski-agent/src/rodski_agent/common/state.py`
- **描述**: 定义 `ExecutionState(TypedDict)` 与设计方案 SS4.2 对齐。包含字段：`case_path`、`max_retry`、`execution_result`、`case_results`、`screenshots`、`report`、`status`、`error`。定义 `StatusEnum`：running/pass/fail/partial/error。
- **验收标准**:
  - [ ] TypedDict 定义完整，类型标注正确
  - [ ] 可被 LangGraph 的 StateGraph 使用

### T02-003: Execution Agent 图定义 -- graph.py (60min)

- **文件**: `rodski-agent/src/rodski_agent/execution/graph.py`
- **描述**: 使用 LangGraph `StateGraph` 定义 Execution Agent 图。MVP 阶段仅 3 个节点：`pre_check` -> `execute` -> `parse_result` -> `report`。条件边：`parse_result` 根据结果分流到 `report`（MVP 不含 diagnose/retry）。导出 `build_execution_graph()` 工厂函数。
- **验收标准**:
  - [ ] `build_execution_graph()` 返回可调用的 CompiledGraph
  - [ ] 图的节点和边定义正确（可通过 `.get_graph().nodes` 验证）

### T02-004: 执行节点实现 -- nodes.py (90min)

- **文件**: `rodski-agent/src/rodski_agent/execution/nodes.py`
- **描述**: 实现 4 个节点函数：
  1. `pre_check(state)` -- 使用 `rodski_knowledge.validate_directory_structure()` 检查目录完整性，可选调 rodski_validate 做 XSD 校验
  2. `execute(state)` -- 调用 `rodski_tools.rodski_run()`，将结果存入 state
  3. `parse_result(state)` -- 解析 result XML 或 execution_summary.json，提取 case_results 列表
  4. `report(state)` -- 汇总结果，生成 report dict（total/passed/failed/cases 明细）
- **rodski 知识依赖**:
  - `rodski/docs/AGENT_INTEGRATION.md` -- CLI 调用契约、exit code 语义、execution_summary.json 结构
  - `rodski_knowledge.validate_directory_structure()` -- 目录结构校验
- **验收标准**:
  - [ ] 每个节点函数签名正确（接收 state，返回 state 更新）
  - [ ] `pre_check` 使用 rodski_knowledge 校验目录结构
  - [ ] `execute` 能正确调用 rodski 并根据 AGENT_INTEGRATION 契约解析 exit code
  - [ ] `parse_result` 能正确解析 rodski 输出的 result XML

### T02-005: CLI run 命令对接 (60min)

- **文件**: `rodski-agent/src/rodski_agent/cli.py`（修改 run 子命令）
- **描述**: 实现 `run` 子命令完整参数：`--case`（必填）、`--max-retry`（默认 0，MVP 不重试）、`--headless`、`--browser`。构建初始 `ExecutionState`，调用 `build_execution_graph().invoke(state)`。根据 `--format` 输出结果（human-readable 或 JSON）。设置正确的退出码（0=全通过，1=有失败，2=执行错误）。
- **验收标准**:
  - [ ] `rodski-agent run --case rodski-demo/DEMO/demo_full/case/demo_case.xml` 能执行并输出结果
  - [ ] `--format json` 输出合法 JSON
  - [ ] 退出码正确反映执行结果

### T02-006: 集成测试 (60min)

- **文件**:
  - `rodski-agent/tests/test_execution_graph.py`
  - `rodski-agent/tests/test_cli_run.py`
- **描述**: 编写图级别测试（Mock rodski_tools 测试节点间数据流转）。编写 CLI 集成测试（CliRunner + Mock 测试完整命令行流程）。可选编写真实集成测试（实际调用 rodski-demo 用例，标记为 slow）。
- **验收标准**:
  - [ ] pytest 全部通过
  - [ ] 至少 10 个测试用例
  - [ ] 图流转测试覆盖 pre_check/execute/parse_result/report 全链路

## 交付物

- `rodski-agent run --case <path>` 可运行
- Execution Agent LangGraph 图（MVP 版，无诊断/重试）
- rodski CLI 封装层（rodski_tools.py）
- 10+ 个测试用例

## 约束检查

- [ ] rodski CLI 调用参数与 `AGENT_INTEGRATION.md` 契约一致
- [ ] exit code 语义（0/1/2）正确映射
- [ ] `pre_check` 使用 `rodski_knowledge` 校验目录结构（case/model/data 必须存在）
- [ ] 示例路径使用 `rodski-demo/`，不使用 `rodski/examples/`
- [ ] 测试分层正确：单元测试用 pytest，真实集成测试标记为 slow
