# Iteration 06: Design Agent 基础

## 目标

实现 `rodski-agent design` 命令，能根据需求描述生成严格遵循 rodski 约束的 XML 用例文件。

## 前置依赖

- Iteration 03（JSON 契约）
- Iteration 04（LLM 桥接）

## 任务列表

### T06-001: Design Agent 状态定义 (30min)

- **文件**: `rodski-agent/src/rodski_agent/common/state.py`（新增 DesignState）
- **描述**: 定义 `DesignState(TypedDict)` 与设计方案 SS3.2 对齐。包含字段：`requirement`、`target_url`、`output_dir`、`test_scenarios`、`case_plan`、`test_data`、`generated_files`、`validation_errors`、`fix_attempt`、`status`、`error`。MVP 不含视觉探索字段（page_elements、enriched_elements 留到 V2）。
- **验收标准**:
  - [ ] TypedDict 定义完整
  - [ ] 与 Execution Agent 状态互不干扰

### T06-002: Design Agent 提示词 (120min)

- **文件**: `rodski-agent/src/rodski_agent/design/prompts.py`
- **rodski 知识依赖**（核心，决定 Design Agent 生成质量）:
  - `CORE_DESIGN_CONSTRAINTS.md` SS1（关键字职责划分）、SS1.2（UI 原子动作非独立关键字）
  - `CORE_DESIGN_CONSTRAINTS.md` SS2（数据表命名规则）、SS3（接口测试保留元素名）
  - `CORE_DESIGN_CONSTRAINTS.md` SS4（特殊值语义、Return 引用限制）、SS5（15 个关键字清单）
  - `TEST_CASE_WRITING_GUIDE.md` SS3（Case XML 三阶段容器）、SS4（Model XML 格式）、SS5（Data XML 格式）、SS6（GlobalValue XML 格式）
  - `SKILL_REFERENCE.md`（每个关键字的详细参数格式和用法示例）
- **描述**: 设计 4 个核心提示词：
  1. `ANALYZE_REQ_PROMPT` -- 需求分析，嵌入约束摘要，按关键字能力分类场景
  2. `PLAN_CASES_PROMPT` -- 用例规划，完整嵌入三阶段容器规则、15 个关键字清单、模型元素名=数据字段名约束、明确禁止 click/hover 作为 action
  3. `DESIGN_DATA_PROMPT` -- 数据设计，完整嵌入数据表规则、特殊值语义表、Return 引用限制、验证表后缀规则
  4. `DESIGN_MODEL_PROMPT` -- 模型设计，完整嵌入定位器格式约束（唯一格式 `<location type>`）、12 种定位器类型、接口模型保留元素名、多定位器格式

  所有提示词统一从 `rodski_knowledge` 模块引入约束常量，不硬编码。每个提示词包含 few-shot 示例（取自 TEST_CASE_WRITING_GUIDE.md）。
- **验收标准**:
  - [ ] 每个提示词都嵌入了 `RODSKI_CONSTRAINT_SUMMARY`
  - [ ] LLM 根据提示词生成的 XML 不违反任何 CORE_DESIGN_CONSTRAINTS 约束
  - [ ] 提示词中的关键字清单与 `rodski_knowledge.SUPPORTED_KEYWORDS` 一致
  - [ ] 提示词中的定位器类型与 `rodski_knowledge.LOCATOR_TYPES` 一致
  - [ ] 每个提示词都包含 few-shot 示例
  - [ ] LLM 输出格式可被后续节点解析

### T06-003: XML 生成器 -- xml_builder.py (120min)

- **文件**:
  - `rodski-agent/src/rodski_agent/common/xml_builder.py`
  - `rodski-agent/tests/test_xml_builder.py`
- **rodski 知识依赖**（xml_builder 是约束的执行者，必须硬编码所有规则）:
  - `rodski_knowledge.SUPPORTED_KEYWORDS` / `LOCATOR_TYPES` / `CASE_PHASES` / `SPECIAL_VALUES` / `VERIFY_TABLE_SUFFIX`
  - `rodski_knowledge.validate_*` 系列校验函数
  - `rodski/schemas/*.xsd` -- 最终 XSD 校验
- **描述**: 实现 5 个 XML 生成函数：
  1. `build_case_xml(cases)` -- action 用 `validate_action()` 校验，强制三阶段容器结构，execute 只允许 "是"/"否"，component_type 只允许 "界面"/"接口"/"数据库"
  2. `build_model_xml(models)` -- 定位器只用 `<location type="...">值</location>` 子节点格式，type 用 `validate_locator_type()` 校验，禁止简化格式
  3. `build_data_xml(datatables)` -- 用 `validate_element_data_consistency()` 校验元素名=字段名，row id 表内唯一
  4. `build_verify_xml(datatables)` -- 用 `validate_verify_table_name()` 校验表名后缀，检测并拒绝接口/DB verify 表中的 `${Return[-1]}`
  5. `build_globalvalue_xml(groups)` -- group name 全局唯一，var 须有 name+value

  所有 XML 包含声明头。生成后自动调用 XSD 校验。
- **验收标准**:
  - [ ] 生成的 case XML 通过 `case.xsd` 校验
  - [ ] 生成的 model XML 通过 `model.xsd` 校验
  - [ ] 生成的 data XML 通过 `data.xsd` 校验
  - [ ] 不使用已废弃的简化定位器格式
  - [ ] 非法 action 在生成时即被拦截
  - [ ] 元素名与字段名不一致时抛出明确错误
  - [ ] 接口 verify 表中 `${Return[-1]}` 被检测并报错

### T06-004: Design Agent 节点实现 (120min)

- **文件**: `rodski-agent/src/rodski_agent/design/nodes.py`
- **描述**: 实现 5 个节点函数：
  1. `analyze_req(state)` -- LLM 分析需求，输出 test_scenarios
  2. `plan_cases(state)` -- LLM 规划用例结构，后处理用 `validate_action()` 逐条检查 action 合法性
  3. `design_data(state)` -- LLM 设计测试数据，后处理用 `validate_element_data_consistency()` 检查一致性
  4. `generate_xml(state)` -- 调用 xml_builder 生成文件写入 output_dir，用 `validate_directory_structure()` 校验目录
  5. `validate_xml(state)` -- 调用 rodski validate 做 XSD 校验。成功则 status="success"，失败则记录 validation_errors 并 fix_attempt+1

  每个 LLM 节点的输出需二次校验，解析失败时重新请求（最多 2 次）。
- **验收标准**:
  - [ ] analyze_req 能从自然语言提取场景列表
  - [ ] plan_cases 输出的 action 全部在 SUPPORTED_KEYWORDS 中
  - [ ] design_data 输出的字段名与模型元素名一致
  - [ ] generate_xml 生成的文件目录结构正确（case/model/data 三目录）
  - [ ] validate_xml 能发现格式错误并传递给修复循环

### T06-005: Design Agent 图定义 (60min)

- **文件**: `rodski-agent/src/rodski_agent/design/graph.py`
- **描述**: 使用 LangGraph StateGraph 构建 Design Agent 图。节点链路：`analyze_req` -> `plan_cases` -> `design_data` -> `generate_xml` -> `validate_xml`。条件边：校验通过则 END，校验失败且 fix_attempt < 3 则回到 `generate_xml`（修复循环）。导出 `build_design_graph()` 工厂函数。
- **验收标准**:
  - [ ] 图拓扑与设计方案 SS3.1 一致（去除视觉探索节点）
  - [ ] 校验失败时能自动修复最多 3 次
  - [ ] 图可正确编译和调用

### T06-006: CLI design 命令 (45min)

- **文件**: `rodski-agent/src/rodski_agent/cli.py`（修改 design 子命令）
- **描述**: 实现 `design` 子命令参数：`--requirement`（必填）、`--url`（可选，MVP 暂不用）、`--output`（必填，输出目录）。构建 DesignState，调用 design graph。输出生成结果（JSON / human）。生成后的目录结构遵循 `product/项目/模块` 三层约束。
- **验收标准**:
  - [ ] `rodski-agent design --requirement "登录测试" --output cassmall/login/` 生成 XML 文件
  - [ ] 输出目录下有 case/ model/ data/ 三个目录
  - [ ] 生成的 XML 格式正确

### T06-007: Design Agent 测试 (90min)

- **文件**:
  - `rodski-agent/tests/test_design_graph.py`
  - `rodski-agent/tests/test_xml_builder.py`（扩展）
- **描述**: Mock LLM 返回，测试 analyze_req -> plan_cases -> design_data 数据流。测试 xml_builder 生成的 XML 通过 XSD 校验。测试校验失败时的修复循环。测试 CLI design 命令的端到端流程（Mock LLM）。
- **验收标准**:
  - [ ] 设计流程全链路测试覆盖
  - [ ] 生成的 XML 能通过 rodski validate
  - [ ] pytest 全部通过

## 交付物

- `rodski-agent design` 命令可用
- Design Agent LangGraph 图（无视觉探索）
- XML 生成器（xml_builder.py）-- 内置 rodski 约束校验
- 设计提示词模板 -- 嵌入完整 rodski 框架知识
- 生成的 XML 通过 XSD 校验

## 约束检查

- [ ] xml_builder 生成的 case XML 中 action 只使用 SUPPORTED 关键字（SS1、SS5）
- [ ] click/hover 等只出现在数据表 field 值中，不在 action 属性（SS1.2）
- [ ] design 生成的目录遵循 case/model/data 固定结构（SS6）
- [ ] 所有生成的 XML 通过对应 XSD 校验（SS7.0）
- [ ] model element name 与 data field name 一致（SS2.4）
- [ ] 只使用 `<location type="类型">值</location>` 格式（SS2.5.3）
- [ ] verify 数据表名为 `{模型名}_verify`（SS2.2）
- [ ] 接口/DB verify 表禁止 `${Return[-1]}`（SS4.2、SS4.3）
- [ ] 所有 LLM 提示词包含 `RODSKI_CONSTRAINT_SUMMARY`
- [ ] 提示词中约束常量从 `rodski_knowledge` 模块引入，不硬编码
