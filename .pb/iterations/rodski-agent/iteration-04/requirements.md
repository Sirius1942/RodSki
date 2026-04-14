# Iteration 04: LLM 桥接 + 诊断节点

## 目标

桥接 rodski 的 LLM 能力，实现 Execution Agent 的 `diagnose` 节点，产出失败根因分析。

## 前置依赖

- Iteration 02（Execution Agent 最小图）

## 任务列表

### T04-001: LLM 桥接层 -- llm_bridge.py (90min)

- **文件**:
  - `rodski-agent/src/rodski_agent/common/llm_bridge.py`
  - `rodski-agent/tests/test_llm_bridge.py`
- **描述**: 实现桥接函数，复用 `rodski/llm/client.py` 的 `LLMClient`。`get_llm_client()` 加载 rodski LLM 配置并初始化客户端。`analyze_screenshot(image_path, question)` 调用 `screenshot_verifier` 能力。`review_test_result(result_data)` 调用 `test_reviewer` 能力。处理 LLM 不可用时的降级（抛出 `LLMUnavailableError`，上层节点跳过诊断）。
- **验收标准**:
  - [ ] LLM 可用时，能正确调用 rodski LLM 能力
  - [ ] LLM 不可用时，抛出可预期的异常
  - [ ] 配置路径正确指向 `rodski/config/llm_config.yaml`

### T04-002: 诊断提示词设计 (90min)

- **文件**: `rodski-agent/src/rodski_agent/execution/prompts.py`
- **rodski 知识依赖**:
  - `CORE_DESIGN_CONSTRAINTS.md` SS8.8（问题判别器 + 四分类体系）
  - `AGENT_INTEGRATION.md`（错误类型到 exit code 映射、error contract）
  - `CORE_DESIGN_CONSTRAINTS.md` SS1（关键字职责边界）
  - `CORE_DESIGN_CONSTRAINTS.md` SS2（数据表规则）
- **描述**: 设计 `DIAGNOSE_SYSTEM_PROMPT`（嵌入 `RODSKI_CONSTRAINT_SUMMARY`、常见失败模式与 rodski 规则的映射关系）和 `DIAGNOSE_USER_TEMPLATE`（含失败用例信息、执行日志片段、截图描述、model/data 上下文）。输出格式要求 JSON：root_cause, confidence, category, suggestion, evidence, recommended_action。category 必须对齐 SS8.8.2 四分类：`CASE_DEFECT`/`ENV_DEFECT`/`PRODUCT_DEFECT`/`UNKNOWN`。recommended_action 必须对齐 SS8.8.2 四种动作：`insert`/`pause`/`terminate`/`escalate`。置信度约束：confidence < 0.6 时 recommended_action 只能是 `pause` 或 `escalate`。
- **验收标准**:
  - [ ] 提示词嵌入了 rodski 约束摘要和常见失败模式映射
  - [ ] 输出格式包含 category + confidence + recommended_action
  - [ ] 分类体系与 CORE_DESIGN_CONSTRAINTS SS8.8.2 完全一致
  - [ ] 低置信度约束已在提示词中明确

### T04-003: diagnose 节点实现 (90min)

- **文件**: `rodski-agent/src/rodski_agent/execution/nodes.py`（新增 diagnose 函数）
- **描述**: 实现 `diagnose(state)` 节点。从 state 提取失败用例列表和截图路径。逐个失败用例调用 LLM 进行诊断。合并诊断结果到 `state.diagnosis`。若 LLM 不可用，跳过诊断，设置 `diagnosis = {"skipped": true, "reason": "LLM unavailable"}`。截图分析：若有截图路径，附加到 LLM 请求中。
- **验收标准**:
  - [ ] 失败用例能获得诊断结果
  - [ ] 诊断结果包含 root_cause, confidence, suggestion
  - [ ] LLM 不可用时优雅降级

### T04-004: 更新 Execution Graph (45min)

- **文件**:
  - `rodski-agent/src/rodski_agent/execution/graph.py`（修改）
  - `rodski-agent/src/rodski_agent/common/state.py`（新增 diagnosis 字段）
- **描述**: 在 `parse_result` 之后添加条件边：有失败用例则进入 `diagnose`，全通过则直接到 `report`。`diagnose` 完成后进入 `report`。更新 `ExecutionState` 新增 `diagnosis` 字段。确保无 LLM 时图仍可执行。
- **验收标准**:
  - [ ] 有失败用例时，图经过 diagnose 节点
  - [ ] 全通过时，跳过 diagnose
  - [ ] report 中包含诊断信息（如有）

### T04-005: diagnose 独立命令 (45min)

- **文件**: `rodski-agent/src/rodski_agent/cli.py`（修改 diagnose 子命令）
- **描述**: 实现 `rodski-agent diagnose --result <path>` 命令。接受 result 目录或 execution_summary.json 路径。直接调用 diagnose 节点逻辑。输出诊断结果（JSON / human）。
- **验收标准**:
  - [ ] `rodski-agent diagnose --result <path>` 输出诊断结果
  - [ ] JSON 格式符合契约

### T04-006: 诊断功能测试 (60min)

- **文件**:
  - `rodski-agent/tests/test_diagnosis.py`
  - `rodski-agent/tests/fixtures/`（测试用 result 数据）
- **描述**: 准备测试用的 result XML 和截图 fixtures。Mock LLM 返回，测试诊断节点逻辑。测试 LLM 不可用时的降级行为。测试 diagnose CLI 命令。
- **验收标准**:
  - [ ] 诊断逻辑测试覆盖正常和降级路径
  - [ ] pytest 全部通过

## 交付物

- LLM 桥接层（复用 rodski LLM 能力）
- diagnose 节点（LLM 诊断失败根因）
- `rodski-agent diagnose` 独立命令
- 诊断功能可在无 LLM 时优雅降级

## 约束检查

- [ ] 诊断分类体系严格为 `CASE_DEFECT`/`ENV_DEFECT`/`PRODUCT_DEFECT`/`UNKNOWN`（SS8.8.2）
- [ ] recommended_action 严格为 `insert`/`pause`/`terminate`/`escalate`（SS8.8.2）
- [ ] confidence < 0.6 时不允许自动执行高风险动作（SS8.8.3）
- [ ] 所有 LLM 提示词嵌入 `RODSKI_CONSTRAINT_SUMMARY`
- [ ] LLM 不可用时 Execution Agent 仍可工作（跳过诊断）
- [ ] 诊断结果是策略输入，不直接改写原始执行结果（SS8.8.3）
