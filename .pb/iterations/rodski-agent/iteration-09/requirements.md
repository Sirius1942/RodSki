# Iteration 09: 智能修复

## 目标

Execution Agent 能根据诊断结果自动修复 XML 文件（主要是定位器更新），提升重试成功率。

## 前置依赖

- Iteration 05（重试机制）
- Iteration 08（视觉探索 -- 提供 OmniParser 能力）

## 任务列表

### T09-001: 修复策略框架 (60min)

- **文件**: `rodski-agent/src/rodski_agent/execution/fixer.py`（重构）
- **描述**: 定义 `FixStrategy` 基类（Strategy 模式）。定义 `FixResult` dataclass（applied, description, files_modified）。策略注册机制：根据 diagnosis.category 选择策略。修复优先级：简单修复（等待）-> 定位器修复 -> XML 重写。
- **验收标准**:
  - [ ] Strategy 模式结构清晰
  - [ ] 策略选择逻辑正确

### T09-002: 定位器修复策略 (120min)

- **文件**: `rodski-agent/src/rodski_agent/execution/strategies/locator_fix.py`
- **rodski 知识依赖**:
  - `rodski_knowledge.LOCATOR_TYPES` -- 新定位器类型必须合法
  - `CORE_DESIGN_CONSTRAINTS.md` SS2.5.3 -- 唯一定位器格式
  - `CORE_DESIGN_CONSTRAINTS.md` SS2.5.4 -- 多定位器格式（priority 属性）
  - `rodski/schemas/model.xsd` -- 修改后必须通过校验
- **描述**: 实现 `LocatorFixStrategy`。流程：截取当前页面 -> OmniParser 识别 -> LLM 匹配失败元素 -> 更新 model.xml。解析 model.xml 找到失败元素的 `<location>` 节点。用新的定位器值替换旧值。支持添加多定位器（priority 备选）。修改后重新校验 model.xml 通过 model.xsd。
- **验收标准**:
  - [ ] 能识别并替换失败的定位器
  - [ ] 修改后的 model.xml 通过 XSD 校验
  - [ ] 定位器格式遵循 `<location type="类型">值</location>`

### T09-003: 等待时间修复策略 (45min)

- **文件**: `rodski-agent/src/rodski_agent/execution/strategies/wait_fix.py`
- **描述**: 实现 `WaitFixStrategy`。在失败步骤前插入 `<test_step action="wait" data="3"/>`。或修改 globalvalue 中的 WaitTime。修改后的 case XML 通过 case.xsd 校验。
- **rodski 知识依赖**:
  - `CORE_DESIGN_CONSTRAINTS.md` SS13 -- 智能等待机制（避免与之冲突）
  - `rodski_knowledge.validate_action("wait")` -- 确认 wait 是合法关键字
- **验收标准**:
  - [ ] 等待步骤正确插入
  - [ ] 修改后 XML 通过校验

### T09-004: 数据修复策略 (60min)

- **文件**: `rodski-agent/src/rodski_agent/execution/strategies/data_fix.py`
- **描述**: 实现 `DataFixStrategy`。场景：验证失败（expected != actual）且诊断为期望值过时。调用 LLM 分析实际值与期望值的差异。若 LLM 判断是"期望值过时"，更新 data_verify.xml。明确不自动修改"不应该改"的期望值（避免掩盖真实缺陷）。
- **rodski 知识依赖**:
  - `CORE_DESIGN_CONSTRAINTS.md` SS2.2 -- 验证表命名规则
  - `rodski/schemas/data.xsd` -- 修改后通过校验
- **验收标准**:
  - [ ] 能识别期望值过时的情况
  - [ ] 不会错误地修改真实断言失败

### T09-005: 修复策略集成到重试循环 (45min)

- **文件**:
  - `rodski-agent/src/rodski_agent/execution/nodes.py`（修改 apply_fix）
  - `rodski-agent/src/rodski_agent/execution/graph.py`（调整边）
- **描述**: `apply_fix` 节点调用策略框架选择并执行修复。修复结果记录到 `state.fixes_applied`。多次重试时，策略可以升级（先等待 -> 再定位器 -> 再数据）。
- **验收标准**:
  - [ ] 重试循环中使用正确的修复策略
  - [ ] 策略升级逻辑正常

### T09-006: 智能修复测试 (90min)

- **文件**:
  - `rodski-agent/tests/test_fixer.py`
  - `rodski-agent/tests/test_strategies.py`
- **描述**: 为每种修复策略编写独立测试。测试策略选择逻辑。测试修复后 XML 的正确性。端到端：执行失败 -> 诊断 -> 修复 -> 重试成功。
- **验收标准**:
  - [ ] 每种策略都有测试覆盖
  - [ ] 修复后 XML 通过 XSD 校验
  - [ ] pytest 全部通过

## 交付物

- 策略模式的修复框架
- 三种修复策略（定位器 / 等待 / 数据）
- 修复 -> 重试完整循环
- 修复后 XML 保证通过 XSD 校验

## 约束检查

- [ ] 定位器修复只使用 `<location type="类型">值</location>` 格式（SS2.5.3）
- [ ] 新定位器类型通过 `validate_locator_type()` 校验
- [ ] 多定位器使用 priority 属性（SS2.5.4）
- [ ] 等待修复插入的 action="wait" 在 SUPPORTED 清单中
- [ ] 修改后的 case/model/data XML 均通过对应 XSD 校验（SS7.0）
- [ ] 数据修复不掩盖真实缺陷（仅修改 LLM 高置信度判定为"过时"的期望值）
- [ ] 修复策略不与 rodski 智能等待机制冲突（SS13）
- [ ] 修复前备份原始 XML
