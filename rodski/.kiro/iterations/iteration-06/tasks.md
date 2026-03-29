# Iteration 06 任务清单

## Phase 1: 表达式引擎与变量存储 (3天)

### T6-001: ExpressionEngine 表达式解析器
- 新建 `core/expression_engine.py`
- 实现 `parse()` 方法，将条件字符串解析为 AST
- 支持操作符: `==`, `!=`, `>`, `<`, `>=`, `<=`, `&&`, `||`, `!`
- 支持括号嵌套
- 实现 `evaluate()` 方法，用 context 变量求值 AST
**预计**: 6h

### T6-002: VariableStore 变量存储
- 新建 `core/variable_store.py`
- 实现 `get(name)` / `set(name, value)` / `all()` 方法
- 实现 `resolve(text)` 方法替换 `${name}` 为实际值
- 注册内置变量（_case_id, _step_index, _timestamp, _last_result）
- 实现 `_update_from_step_result()` 从执行结果更新变量
**预计**: 4h

### T6-003: ExpressionEngine + VariableStore 单元测试
- 测试所有操作符组合
- 测试变量不存在时的处理（返回 false）
- 测试嵌套括号表达式
- 测试 resolve() 替换多个变量
**预计**: 4h

## Phase 2: CaseParser 动态节点解析 (3天)

### T6-004: XML Schema 动态节点定义
- 新建 `schemas/dynamic_nodes.xsd`
- 定义 IfNodeType / LoopNodeType / DynamicInsertType / CatchNodeType
- 允许动态节点内嵌 test_step
**预计**: 2h

### T6-005: CaseParser 解析 `<if>` 节点
- 修改 `core/case_parser.py` 的 `_parse_test_case()`
- 新增 `_parse_if_node()` 方法
- 支持 `<else>` 子节点
- CaseDefinition 支持返回混合节点列表（Step + IfNode + LoopNode + DynamicInsertNode）
**预计**: 4h

### T6-006: CaseParser 解析 `<loop>` 节点
- 新增 `_parse_loop_node()` 方法
- 支持 `times` 属性（次数或变量引用）
- 支持 `while` 属性（条件表达式）
- 支持 `<catch>` 子节点
**预计**: 4h

### T6-007: CaseParser 解析 `<dynamic_insert>` 节点
- 新增 `_parse_dynamic_insert_node()` 方法
- 支持 `source` 属性（variable / ai / file）
- 支持 `variable` / `path` 属性
**预计**: 2h

### T6-008: CaseParser 动态节点解析测试
- 编写单元测试覆盖: if / else / loop / dynamic_insert
- 测试嵌套场景
- 测试缺失属性时的默认值
**预计**: 2h

## Phase 3: DynamicExecutor 动态执行 (4天)

### T6-009: DynamicExecutor 执行器核心
- 新建 `core/dynamic_executor.py`
- 实现 `__init__()` 初始化（注入 keyword_engine / variable_store / result_writer）
- 实现 `execute_if()` 方法
- 实现 `execute_loop()` 方法
- 实现 `execute_dynamic_insert()` 方法
**预计**: 8h

### T6-010: 条件分支执行
- `execute_if()` 解析条件表达式
- 根据条件结果选择执行 then 或 else 分支
- 写入 IfResult（包含 branch、steps）
- 在 KeywordEngine 中集成条件分支处理
**预计**: 4h

### T6-011: 循环执行
- `execute_loop()` 支持 times 和 while 两种模式
- 每次迭代前检查 while 条件
- 执行 `<catch>` 块捕获异常
- 支持 max_attempts 防止死循环
- 写入 LoopResult（包含 iterations[]）
**预计**: 6h

### T6-012: 动态步骤插入
- `execute_dynamic_insert()` 从 variable / file / ai 加载步骤 JSON
- JSON 格式: `{"steps": [{"action":..., "model":..., "data":...}]}`
- 执行插入的步骤并收集结果
- 写入 InsertResult
**预计**: 4h

### T6-013: `set` 关键字支持
- 在 KeywordEngine 添加 "set" 关键字处理
- data 格式: `variable_name=value`
- 调用 VariableStore.set() 设置变量
- 不生成 result XML 节点（set 是副作用操作）
**预计**: 2h

## Phase 4: ResultWriter 增强 (2天)

### T6-014: ResultWriter 动态节点结果写入
- 修改 `core/result_writer.py`
- 新增 `write_if_result()` 方法
- 新增 `write_loop_result()` 方法（含迭代详情）
- 新增 `write_dynamic_insert_result()` 方法
- 在 ResultWriter 写入循环中识别动态节点并调用对应方法
**预计**: 6h

### T6-015: Result XML Schema 更新
- 在 result.xsd 中新增 `<if>` / `<loop>` / `<dynamic_insert>` 节点类型
- 定义 iteration 嵌套结构
- 更新 result_writer.py 的 XML 生成逻辑
**预计**: 4h

## Phase 5: 测试与文档 (2天)

### T6-016: 单元测试
- `tests/unit/test_expression_engine.py` — 表达式解析求值测试
- `tests/unit/test_variable_store.py` — 变量存储测试
- `tests/unit/test_dynamic_executor.py` — 动态执行器测试
**预计**: 6h

### T6-017: 集成测试
- `tests/integration/test_dynamic_execution.py`
- 测试条件分支（true 分支 / false 分支）
- 测试循环（固定次数 / while 条件 / 嵌套循环）
- 测试动态插入（variable / file 两种 source）
- 测试 set 关键字
**预计**: 8h

### T6-018: 文档更新
- 更新 `docs/user-guides/QUICKSTART.md` 新增动态执行说明
- 新增 `docs/user-guides/DYNAMIC_EXECUTION.md` 详细指南
- 包含 if / loop / dynamic_insert 的完整示例
**预计**: 4h

## 任务依赖关系

```
T6-001 → T6-002 → T6-003
                         ↓
T6-004 → T6-005 → T6-006 → T6-007 → T6-008
                                               ↓
T6-009 → T6-010 → T6-011 → T6-012 → T6-013
                                               ↓
T6-014 → T6-015 → T6-016 → T6-017 → T6-018
```

## 估计工时

- Phase 1: 14h
- Phase 2: 14h
- Phase 3: 20h
- Phase 4: 10h
- Phase 5: 18h
- **总计: ~76h（2人周+2天）**

## 成功标准检查

- [ ] `<if condition="...">` 条件分支正确执行
- [ ] `<loop times="N">` 按次数循环正确执行
- [ ] `<loop while="...">` 条件循环正确执行
- [ ] `<dynamic_insert>` 动态步骤插入正确执行
- [ ] `<test_step action="set">` 变量设置正确工作
- [ ] result XML 正确标记 if/loop/dynamic_insert 执行结果
- [ ] 所有新增代码有单元测试覆盖
- [ ] 集成测试通过
