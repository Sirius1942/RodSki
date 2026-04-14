# Iteration 07: Pipeline 命令

## 目标

实现 `rodski-agent pipeline` 命令，串联 Design Agent 和 Execution Agent，完成 V1.0 功能集。

## 前置依赖

- Iteration 05（重试机制）
- Iteration 06（Design Agent）

## 任务列表

### T07-001: Pipeline 编排器 (90min)

- **文件**: `rodski-agent/src/rodski_agent/pipeline/orchestrator.py`
- **描述**: 实现 `PipelineOrchestrator` 类。串联逻辑：Design Agent 完成后获取生成的 case 路径，传递给 Execution Agent 执行。中间状态传递：Design 输出的 `generated_files` -> Execution 输入的 `case_path`。阶段性输出：每个阶段（design/run）完成后输出中间结果。任一阶段失败时的中止策略。
- **验收标准**:
  - [ ] Design -> Execution 串联成功
  - [ ] 文件系统是两个 Agent 的通道（不走内存传递 XML 内容）
  - [ ] 中间状态可观测

### T07-002: CLI pipeline 命令 (60min)

- **文件**: `rodski-agent/src/rodski_agent/cli.py`（修改 pipeline 子命令）
- **描述**: 实现 `pipeline` 子命令参数：`--requirement`、`--url`、`--output`、`--max-retry`。调用 PipelineOrchestrator。输出合并报告（design 生成了什么 + run 执行结果如何）。JSON 输出包含 `design_output` 和 `run_output` 两个子节点。
- **验收标准**:
  - [ ] `rodski-agent pipeline --requirement "登录测试" --output cassmall/login/` 完整执行
  - [ ] 输出同时包含设计和执行结果

### T07-003: config show 命令 (30min)

- **文件**: `rodski-agent/src/rodski_agent/cli.py`（修改 config 子命令）
- **描述**: 实现 `rodski-agent config show` 显示当前生效配置。显示配置来源（文件/环境变量/默认值）。敏感信息脱敏（API key 只显示前后几位）。
- **验收标准**:
  - [ ] 配置信息完整展示
  - [ ] API key 已脱敏

### T07-004: Pipeline 测试 (60min)

- **文件**: `rodski-agent/tests/test_pipeline.py`
- **描述**: 测试 Design -> Execution 串联（Mock 两个 Agent）。测试 Design 失败时 Pipeline 中止。测试 Execution 全通过和部分失败的输出。测试 CLI pipeline 命令端到端。
- **验收标准**:
  - [ ] 串联逻辑测试覆盖
  - [ ] pytest 全部通过

### T07-005: V1.0 端到端验收 (60min)

- **文件**: `rodski-agent/tests/test_e2e.py`（标记为 @pytest.mark.e2e）
- **描述**: 用 rodski-demo 的场景做端到端测试。`rodski-agent run --case rodski-demo/DEMO/demo_full/case/demo_case.xml` 真实执行。验证 JSON 输出格式正确和退出码正确。记录 V1.0 release checklist。
- **验收标准**:
  - [ ] 端到端测试通过
  - [ ] V1.0 所有功能可用：run / design / pipeline / diagnose / config

## 交付物

- `rodski-agent pipeline` 命令可用
- `rodski-agent config show` 命令可用
- V1.0 完整功能集端到端验证通过
- 所有命令的 JSON 输出遵循统一契约

## 约束检查

- [ ] Pipeline 通过文件系统传递 XML（Design -> 文件 -> Execution），不走内存传递
- [ ] JSON 输出契约一旦发布不可随意变更（设计方案 SS11.4）
- [ ] 端到端验收使用 `rodski-demo/` 目录，不使用 `rodski/examples/`
- [ ] Pipeline design 阶段生成的目录遵循 case/model/data 固定结构（SS6）
- [ ] Pipeline run 阶段的 exit code 语义正确（0/1/2）
