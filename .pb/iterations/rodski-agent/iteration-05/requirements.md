# Iteration 05: 重试机制

## 目标

Execution Agent 具备受控重试能力，失败用例可尝试自动修复后重跑。

## 前置依赖

- Iteration 04（LLM 桥接 + 诊断节点）

## 任务列表

### T05-001: retry_decide 节点 (90min)

- **文件**: `rodski-agent/src/rodski_agent/execution/nodes.py`（新增 retry_decide 函数）
- **描述**: 实现 `retry_decide(state)` 节点。基于 `diagnosis.category` 和 `diagnosis.confidence` 判断是否可修复：
  - `CASE_DEFECT` + confidence > 0.7 -> 可修复
  - `ENV_DEFECT` -> 不可修复（环境问题不在 Agent 能力范围）
  - `PRODUCT_DEFECT` -> 不可修复
  - `UNKNOWN` -> 不可修复
  检查 `retry_count < max_retry`。返回 `state.retry_decision`: "retry" 或 "give_up"。
- **验收标准**:
  - [ ] 分类决策逻辑正确
  - [ ] 超过最大重试次数时强制 give_up
  - [ ] 可修复条件清晰

### T05-002: 简单修复策略 (90min)

- **文件**: `rodski-agent/src/rodski_agent/execution/fixer.py`
- **rodski 知识依赖**:
  - `rodski_knowledge.SUPPORTED_KEYWORDS` -- 修复时插入的 wait 步骤必须是合法关键字
  - `rodski_knowledge.LOCATOR_TYPES` -- 更新定位器时类型必须合法
  - `rodski_knowledge.CASE_PHASES` -- 了解在哪个阶段插入步骤合法
  - `CORE_DESIGN_CONSTRAINTS.md` SS13 -- 理解 rodski 已有的智能等待机制，避免冗余
- **描述**: 实现 `apply_fix(state)` 函数。MVP 支持两种修复策略：
  1. **添加等待**: 若诊断为超时，在失败步骤前插入 `<test_step action="wait" data="3"/>`，使用 `rodski_knowledge.validate_action("wait")` 确认合法。注意 rodski 已有智能等待（SS13），此处显式 wait 用于页面加载等非元素等待场景
  2. **更新定位器**: 若诊断为元素未找到，尝试使用替代定位器（需 LLM 建议），新定位器类型必须用 `rodski_knowledge.validate_locator_type()` 校验，格式必须是 `<location type="类型">值</location>`
  修复后的 XML 必须通过 XSD 校验。修复前备份原始 XML。记录修复动作到 `state.fixes_applied`。
- **验收标准**:
  - [ ] 等待修复能正确修改 XML，修改后通过 case.xsd 校验
  - [ ] 定位器修复后通过 model.xsd 校验，格式为 `<location type>` 唯一格式
  - [ ] 修复后原始 XML 有备份
  - [ ] fixes_applied 记录完整

### T05-003: 更新 Execution Graph -- 重试循环 (60min)

- **文件**: `rodski-agent/src/rodski_agent/execution/graph.py`（修改）
- **描述**: `diagnose` 到 `retry_decide` 条件边。`retry_decide` = "retry" 则进入 `apply_fix` 然后回到 `execute`（重试循环）。`retry_decide` = "give_up" 则进入 `report`。确保循环有终止条件（max_retry）。
- **验收标准**:
  - [ ] 重试循环工作正常
  - [ ] 达到 max_retry 后终止
  - [ ] 每次重试的结果都被记录

### T05-004: CLI 参数更新 (30min)

- **文件**: `rodski-agent/src/rodski_agent/cli.py`（修改）
- **描述**: `--max-retry` 参数默认值改为 3。输出中显示重试次数和每次的修复动作。JSON 输出增加 `retries` 数组。
- **验收标准**:
  - [ ] `--max-retry 0` 不重试
  - [ ] `--max-retry 3` 最多重试 3 次
  - [ ] 重试历史在输出中可见

### T05-005: 重试机制测试 (60min)

- **文件**: `rodski-agent/tests/test_retry.py`
- **描述**: 测试正常重试循环（Mock execute 第一次失败、第二次成功）。测试达到 max_retry 后停止。测试不可修复场景跳过重试。测试修复策略的 XML 变更。
- **验收标准**:
  - [ ] 重试逻辑全路径测试覆盖
  - [ ] pytest 全部通过

## 交付物

- retry_decide 节点（基于诊断决策是否重试）
- 简单修复策略（添加等待 + 更新定位器）
- 完整的 Execution Agent 图（pre_check -> execute -> parse -> diagnose -> retry_decide -> report）

## 约束检查

- [ ] 修复插入的 wait 步骤使用 `validate_action()` 确认在 SUPPORTED 清单中
- [ ] 定位器修复只使用 `<location type="类型">值</location>` 格式，禁止简化格式
- [ ] 定位器类型通过 `validate_locator_type()` 校验（12 种合法类型）
- [ ] 修复后的 case XML 通过 case.xsd 校验
- [ ] 修复后的 model XML 通过 model.xsd 校验
- [ ] 仅 `CASE_DEFECT` + 高置信度才允许自动修复，其他分类不自动修复
- [ ] 不与 rodski 智能等待机制冲突（SS13）
