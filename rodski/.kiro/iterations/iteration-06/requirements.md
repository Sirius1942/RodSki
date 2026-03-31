# Iteration 06: 动态执行能力 — 需求文档

**周期**: 2026-05-04 ~ 2026-05-17 (2 周)  
**目标**: 赋予测试用例运行时动态调整执行路径的能力

---

## 背景

当前 RodSki 用例按预定义顺序线性执行，无法应对以下场景：

1. **条件分支**: 登录后根据用户角色跳转到不同页面（admin vs user）
2. **动态循环**: 对搜索结果列表中的每一项执行相同验证步骤
3. **运行时注入**: 根据前一步的执行结果，动态插入额外验证步骤
4. **数据驱动增强**: 对同一 API 批量发送不同参数并验证每个响应

Iteration 06 引入**条件执行**、**循环能力**和**动态步骤插入**三大能力，使 RodSki 用例从"静态脚本"升级为"可编程测试流程"。

---

## 功能需求

### F6-1: 运行时步骤插入（Dynamic Step Injection）

#### F6-1.1: DynamicStep 类型定义
**文件**: `core/dynamic_steps.py` (新)

定义动态步骤数据结构：

```python
@dataclass
class DynamicStep:
    """动态步骤 - 在运行时插入到执行流的步骤"""
    id: str                          # 唯一标识，如 "inject_001"
    keyword: str                     # 关键字，如 "verify" / "type" / "click"
    params: Dict[str, Any]           # 参数字典
    condition: Optional[str] = None  # 触发条件表达式（None 表示无条件）
    position: str = "after"          # 插入位置: "after" / "before" / "replace"
    target_step_index: Optional[int] = None  # 相对于哪一步插入
    timeout: Optional[int] = None    # 步骤超时（秒）
    retry_on_fail: int = 0          # 失败重试次数
    metadata: Optional[Dict] = None # 扩展元数据

    def to_dict(self) -> Dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: Dict) -> "DynamicStep": ...
```

#### F6-1.2: 步骤注入时机
运行时在以下时机允许注入动态步骤：

| 时机 | 说明 | 优先级 |
|------|------|--------|
| 步骤执行前 (pre-step) | 在每个步骤执行前注入 | 高 |
| 步骤执行后 (post-step) | 在每个步骤执行成功后注入 | 高 |
| 异常发生时 (on-error) | 异常被捕获后注入恢复步骤 | 高 |
| 用例开始时 (pre-case) | 用例开始时注入初始化步骤 | 中 |
| 用例结束时 (post-case) | 用例结束时注入清理/验证步骤 | 中 |

#### F6-1.3: 注入配置格式
在 model.xml 或 case.xml 中声明动态步骤：

```xml
<!-- 在 case.xml 的 test_case 中 -->
<dynamic_steps>
  <!-- 每当点击提交按钮后，验证结果页面是否包含成功提示 -->
  <step id="ds_001"
        keyword="verify"
        position="after"
        trigger="click"
        trigger_locator="#submit-btn">
    <param name="expected">Welcome</param>
    <param name="timeout">10</param>
  </step>

  <!-- 当 API 返回码非 200 时，插入截图步骤 -->
  <step id="ds_002"
        keyword="screenshot"
        position="on-error"
        condition="last_result.status_code != 200">
  </step>
</dynamic_steps>
```

#### F6-1.4: SKIExecutor 动态步骤调度
**文件**: `core/ski_executor.py`

```python
class SKIExecutor:
    def _load_dynamic_steps(self) -> List[DynamicStep]: ...

    def _should_inject(self, step: DynamicStep, context: ExecutionContext) -> bool:
        """判断是否满足注入条件"""
        ...

    def _inject_steps(
        self,
        trigger_point: str,  # "pre-step" / "post-step" / "on-error"
        context: ExecutionContext,
    ) -> List[DynamicStep]:
        """获取所有应该在此时机注入的动态步骤"""
        ...

    def _execute_dynamic_step(self, step: DynamicStep) -> StepResult: ...
```

### F6-2: 条件执行（Conditional Execution）

#### F6-2.1: 条件表达式语法
支持在 XML 中用 `condition` 属性声明执行条件：

```xml
<step keyword="navigate" condition="${user_role} == 'admin'">
  <param name="url">https://example.com/admin</param>
</step>

<step keyword="click" condition="${is_logged_in} == true">
  <param name="locator">#dashboard</param>
</step>
```

#### F6-2.2: 支持的条件操作符

| 操作符 | 说明 | 示例 |
|--------|------|------|
| `==` | 等于 | `${status} == 'active'` |
| `!=` | 不等于 | `${role} != 'guest'` |
| `>` / `<` | 数值比较 | `${count} > 0` |
| `>=` / `<=` | 数值比较 | `${age} >= 18` |
| `in` | 包含于 | `${env} in ['dev', 'test']` |
| `not in` | 不包含于 | `${env} not in ['prod']` |
| `contains` | 字符串包含 | `${msg} contains 'success'` |
| `startswith` | 字符串前缀 | `${title} startswith 'Dashboard'` |
| `endswith` | 字符串后缀 | `${url} endswith '/admin'` |
| `and` / `or` | 逻辑组合 | `${a} == 'x' and ${b} > 0` |
| `not` | 逻辑取反 | `not ${is_disabled}` |

#### F6-2.3: 条件求值器
**文件**: `core/condition_evaluator.py` (新)

```python
class ConditionEvaluator:
    def __init__(self, variables: Dict[str, Any]):
        self._variables = variables

    def evaluate(self, expression: str) -> bool:
        """求值条件表达式，返回 True/False"""
        ...

    def _parse_expression(self, expr: str) -> ast.Expression: ...

    def _safe_eval(self, node: ast.AST) -> Any:
        """安全求值，不允许任意代码执行"""
        ...

# 预定义函数
BUILTIN_FUNCTIONS = {
    "len": len,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
    "any": any,
    "all": all,
    "sum": sum,
    "abs": abs,
}
```

#### F6-2.4: 条件步骤执行
在 `SKIExecutor._execute_step()` 中：

```python
def _execute_step(self, step: TestStep) -> StepResult:
    # 1. 检查条件
    if step.condition:
        evaluator = ConditionEvaluator(self._variables)
        if not evaluator.evaluate(step.condition):
            logger.info(f"Step {step.index} skipped (condition not met)")
            return StepResult(status="skipped", reason=f"Condition: {step.condition}")

    # 2. 正常执行步骤
    result = self._do_execute_step(step)

    # 3. 记录 last_result 供后续条件使用
    self._variables["last_result"] = result.to_dict()
    return result
```

### F6-3: 循环能力（Loop Execution）

#### F6-3.1: 循环语法
在 model.xml 中使用 `loop` 属性声明循环：

```xml
<!-- 重复执行点击操作 5 次 -->
<step keyword="click" loop="5">
  <param name="locator">#load-more-btn</param>
</step>

<!-- 对列表中的每个元素执行验证 -->
<step keyword="verify" loop="for item in ${search_results}">
  <param name="expected">${item.name}</param>
</step>

<!-- 循环直到条件满足（最多 10 次）-->
<step keyword="click" loop="until ${has_more} == false max=10">
  <param name="locator">#next-page</param>
</step>
```

#### F6-3.2: LoopConfiguration 数据类
**文件**: `core/loop_executor.py` (新)

```python
@dataclass
class LoopConfiguration:
    """循环配置"""
    loop_type: str           # "fixed" / "for_each" / "until" / "while"
    count: int = 0          # 固定次数（loop_type=fixed）
    items: Optional[List] = None  # 迭代项（loop_type=for_each）
    item_var: str = "item"  # 循环变量名
    index_var: str = "index"  # 索引变量名
    condition: Optional[str] = None  # 终止条件（loop_type=until/while）
    max_iterations: int = 100  # 最大迭代次数保护
    break_on_fail: bool = True  # 迭代失败时是否中断

    @classmethod
    def parse(cls, loop_str: str) -> "LoopConfiguration": ...

@dataclass
class LoopIterationResult:
    iteration: int
    variables: Dict[str, Any]  # 本次迭代的变量快照
    result: StepResult
    duration_ms: float
```

#### F6-3.3: LoopExecutor 执行器
**文件**: `core/loop_executor.py` (新)

```python
class LoopExecutor:
    def __init__(self, ski_executor: SKIExecutor):
        self._executor = ski_executor

    def execute_loop(
        self,
        step: TestStep,
        loop_config: LoopConfiguration,
    ) -> List[LoopIterationResult]:
        """执行循环步骤，返回每次迭代结果"""
        ...

    def _execute_single_iteration(
        self,
        step: TestStep,
        loop_config: LoopConfiguration,
        iteration: int,
        context: Dict[str, Any],
    ) -> LoopIterationResult:
        ...

    def _should_break(
        self,
        result: StepResult,
        loop_config: LoopConfiguration,
        iteration: int,
    ) -> bool:
        """判断是否应该终止循环"""
        ...
```

#### F6-3.4: 循环结果记录
每次循环迭代记录独立结果到 Result XML：

```xml
<step index="3" keyword="click" status="pass" loop_iteration="1/5" loop_id="lp_001">
  <!-- 第 1 次迭代结果 -->
</step>
<step index="3" keyword="click" status="pass" loop_iteration="2/5" loop_id="lp_001">
  <!-- 第 2 次迭代结果 -->
</step>
<!-- ... -->
```

---

## 非功能需求

### 性能
- 条件求值应在 O(1) 时间完成，不引入明显延迟
- 循环步骤的每次迭代开销与普通步骤相同
- 动态步骤注入不增加正常执行路径的开销

### 安全性
- `ConditionEvaluator` 必须使用 AST 安全求值，禁止 `eval()` 或 `exec()`
- 动态步骤注入仅限 YAML/XML 配置，不允许运行时字符串注入
- 循环最大迭代次数硬限制为 1000，防止死循环

### 可调试性
- 条件不满足而跳过的步骤，在 Result XML 中标记 `status="skipped"`
- 循环执行在 Result XML 中记录每次迭代的独立结果
- 日志清晰打印动态步骤注入信息：`[DynamicStep] Injecting verify after step 5`

---

## 里程碑

| 阶段 | 交付物 | 目标日期 |
|------|--------|---------|
| M6-1 | DynamicStep 类型 + 注入机制 | 2026-05-06 |
| M6-2 | ConditionEvaluator + 条件执行 | 2026-05-10 |
| M6-3 | LoopExecutor + 循环语法 | 2026-05-14 |
| M6-4 | 集成测试 + 文档 | 2026-05-17 |
