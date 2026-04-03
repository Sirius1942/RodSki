# Iteration 06: 动态执行能力 — 任务清单

## 阶段一: 动态步骤注入

### T6-001: DynamicStep 类型定义
**文件**: `core/dynamic_steps.py` (新)

- 实现 `DynamicStep` dataclass: id / keyword / params / condition / position / target_step_index / timeout / retry_on_fail / metadata
- 实现 `DynamicStep.to_dict()` 和 `from_dict()` 方法
- 实现 `StepResult` 中与动态步骤相关的字段扩展
- 定义 `TriggerPoint` 枚举: pre_step / post_step / on_error
**预计**: 4h | **Owner**: 待分配

### T6-002: DynamicStepParser 解析器
**文件**: `core/dynamic_steps.py` (新)

- 实现 `DynamicStepParser.parse_from_xml(xml_root)` → List[DynamicStep]
- 支持从 case.xml 的 `<dynamic_steps>` 节点解析
- 支持 `trigger` + `trigger_locator` 定位目标步骤
- 支持直接 `target_step_index` 定位
- 解析失败时记录 warning 但不中断执行
**预计**: 4h | **Owner**: 待分配

### T6-003: ExecutionContext 数据类
**文件**: `core/dynamic_steps.py` (新)

- 实现 `ExecutionContext` dataclass
- 实现 `last_result` 属性（返回最近步骤结果，供条件引用）
- 实现 `get_driver_state()` 方法（获取浏览器当前 URL/标题/screenshot_path）
**预计**: 2h | **Owner**: 待分配

### T6-004: SKIExecutor 注入钩子集成
**文件**: `core/ski_executor.py`

- 在 `_execute_step()` 中插入 pre-step / post-step / on-error 注入钩子
- 实现 `_inject_steps(trigger_point, context) → List[DynamicStep]`
- 实现 `_execute_dynamic_step(step) → StepResult`
- 动态步骤结果写入 Result XML（标记 `is_dynamic=true`）
- 配置项: `dynamic_step.enabled: true/false`
**预计**: 8h | **Owner**: 待分配

### T6-005: Case XSD dynamic_steps 扩展
**文件**: `schemas/case.xsd`

- 新增 `<xs:element name="dynamic_steps">` 复杂类型
- 定义 `step` 子元素: id / keyword / position / trigger / trigger_locator / target_step_index / condition / timeout / retry_on_fail
- 编写 Schema 单元测试，验证解析正确性
**预计**: 2h | **Owner**: 待分配

---

## 阶段二: 条件执行

### T6-006: ConditionEvaluator 核心
**文件**: `core/condition_evaluator.py` (新)

- 实现 `ConditionEvaluator` 类
- 使用 `ast.parse()` + `_safe_eval()` 安全求值
- 实现所有运算符: `== / != / > / < / >= / <= / in / not in / and / or / not`
- 实现属性访问: `${obj.attr}` 语法
- 实现内置函数: len / str / int / float / bool / any / all / sum / abs / min / max
- 变量从 `self._variables` 字典中查找
- 未知变量默认返回 `None`，不抛异常
**预计**: 8h | **Owner**: 待分配

### T6-007: TestStep.condition 字段解析
**文件**: `core/case_parser.py`

- 在 `TestStep` dataclass 中新增 `condition: Optional[str]` 字段
- 在 `CaseParser._parse_step()` 中解析 `condition` 属性
- 在 `CaseParser._parse_test_steps()` 中处理 `condition` 属性
**预计**: 2h | **Owner**: 待分配

### T6-008: 条件执行集成 SKIExecutor
**文件**: `core/ski_executor.py`

- 在 `_execute_step()` 开始时检查 `step.condition`
- 使用 `ConditionEvaluator` 求值条件
- 条件不满足时返回 `StepResult(status="skipped", reason="...")`
- 在 Result XML 中标记 `<step status="skipped" skip_reason="...">`
- 条件求值失败时视为 `false`（不阻断执行）
**预计**: 4h | **Owner**: 待分配

### T6-009: last_result 上下文变量
**文件**: `core/ski_executor.py`

- 在 `_variables` 中维护 `last_result` 变量
- 每次步骤执行后更新: `self._variables["last_result"] = result.to_dict()`
- 支持 `${last_result.status}` / `${last_result.message}` 等引用
- 清空规则: 用例开始时重置为 `None`
**预计**: 2h | **Owner**: 待分配

---

## 阶段三: 循环能力

### T6-010: LoopConfiguration 数据类
**文件**: `core/loop_executor.py` (新)

- 实现 `LoopConfiguration` dataclass: loop_type / count / items / item_var / index_var / condition / max_iterations / break_on_fail
- 实现 `LoopParser.parse(loop_str) → LoopConfiguration`
- 支持语法: `5` / `for item in ${list}` / `until condition max=N` / `while condition max=N`
- 解析失败时抛出 `ValueError`
**预计**: 4h | **Owner**: 待分配

### T6-011: LoopExecutor 执行器
**文件**: `core/loop_executor.py` (新)

- 实现 `LoopExecutor.__init__(ski_executor)`
- 实现 `execute_loop(step, loop_config) → List[LoopIterationResult]`
- 实现 `_execute_single_iteration()` 单次迭代
- 实现 `_should_break()` 终止判断
- 固定次数 / for_each / until / while 四种循环类型
- `break_on_fail=True` 时，迭代失败自动终止
- 循环最大次数硬限制 1000
**预计**: 8h | **Owner**: 待分配

### T6-012: TestStep.loop 字段解析
**文件**: `core/case_parser.py`

- 在 `TestStep` dataclass 中新增 `loop: Optional[str]` 字段
- 在 `CaseParser._parse_step()` 中解析 `loop` 属性
- 同时解析内联循环参数（如 `max_iterations`）
**预计**: 2h | **Owner**: 待分配

### T6-013: 循环执行集成 SKIExecutor
**文件**: `core/ski_executor.py`

- 在 `_execute_step()` 中检测 `step.loop`
- 存在 loop 时调用 `LoopExecutor.execute_loop()`
- 每次迭代调用 `_do_execute_step()` 并记录独立结果
- 循环变量 (`item` / `index`) 注入 `_variables`
- 循环结果（所有迭代）汇总返回
**预计**: 4h | **Owner**: 待分配

### T6-014: 循环结果写入 Result XML
**文件**: `core/result_writer.py`

- 每次循环迭代生成独立 `<step>` 节点
- 节点属性: `loop_id` / `loop_type` / `loop_iteration` / `loop_item`
- 循环汇总信息写入 `<loop_summary>` 子元素（总次数/通过/失败/平均耗时）
**预计**: 4h | **Owner**: 待分配

---

## 阶段四: 集成与文档

### T6-015: 配置项集成
**文件**: `config/default_config.yaml`

- 新增 `execution.allow_conditions: true`
- 新增 `execution.allow_loops: true`
- 新增 `execution.allow_dynamic_steps: true`
- 新增 `execution.loop_max_iterations: 1000`
- 新增 `execution.dynamic_step.max_per_trigger: 10`
**预计**: 2h | **Owner**: 待分配

### T6-016: 集成测试
**文件**: `tests/integration/test_dynamic_execution.py` (新)

- 测试 DynamicStep 解析和注入（pre/post/on-error）
- 测试 ConditionEvaluator 求值（所有操作符和函数）
- 测试条件执行（满足/不满足/组合条件）
- 测试固定次数循环
- 测试 for_each 循环（列表引用）
- 测试 until/while 循环（条件终止）
- 测试循环 `break_on_fail` 行为
- 测试动态步骤注入 on-error 恢复
**预计**: 8h | **Owner**: 待分配

### T6-017: 示例用例
**文件**: `examples/dynamic/` 目录 (新)

- `conditional_case.xml` - 条件执行示例
- `loop_case.xml` - 循环执行示例
- `dynamic_injection_case.xml` - 动态步骤注入示例
- 每个示例配合 README.md 说明
**预计**: 4h | **Owner**: 待分配

### T6-018: 文档
**文件**: `docs/user-guides/DYNAMIC_EXECUTION.md` (新)

- 条件执行语法说明（所有操作符和示例）
- 循环执行语法说明（固定次数/for_each/until/while）
- 动态步骤注入配置说明
- `last_result` 上下文变量使用指南
- 常见错误和调试方法
- 更新 QUICKSTART.md 添加动态执行章节
**预计**: 4h | **Owner**: 待分配

---

## 任务汇总

| 任务 | 名称 | 预计 | 阶段 |
|------|------|------|------|
| T6-001 | DynamicStep 类型定义 | 4h | 1 |
| T6-002 | DynamicStepParser 解析器 | 4h | 1 |
| T6-003 | ExecutionContext 数据类 | 2h | 1 |
| T6-004 | SKIExecutor 注入钩子集成 | 8h | 1 |
| T6-005 | Case XSD dynamic_steps 扩展 | 2h | 1 |
| T6-006 | ConditionEvaluator 核心 | 8h | 2 |
| T6-007 | TestStep.condition 字段解析 | 2h | 2 |
| T6-008 | 条件执行集成 SKIExecutor | 4h | 2 |
| T6-009 | last_result 上下文变量 | 2h | 2 |
| T6-010 | LoopConfiguration 数据类 | 4h | 3 |
| T6-011 | LoopExecutor 执行器 | 8h | 3 |
| T6-012 | TestStep.loop 字段解析 | 2h | 3 |
| T6-013 | 循环执行集成 SKIExecutor | 4h | 3 |
| T6-014 | 循环结果写入 Result XML | 4h | 3 |
| T6-015 | 配置项集成 | 2h | 4 |
| T6-016 | 集成测试 | 8h | 4 |
| T6-017 | 示例用例 | 4h | 4 |
| T6-018 | 文档 | 4h | 4 |

**总预计**: 72h
