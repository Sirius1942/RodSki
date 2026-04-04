# Iteration 06: 动态执行能力 — 设计文档

---

## 设计目标

1. **声明式优先**: 条件/循环/动态注入均通过 XML 属性声明，无需 Python 代码
2. **安全求值**: 条件表达式使用 AST 解析，禁止任意代码执行
3. **最小侵入**: 核心执行引擎改动极小，新增类独立封装
4. **可追溯**: 所有动态行为均记录到 Result XML，便于调试和审计

---

## 一、DynamicStep 注入机制

### 1.1 架构总览

```
SKIExecutor
  │
  ├── _load_dynamic_steps()  ──→  List[DynamicStep]
  │
  ├── _execute_step(step)
  │     │
  │     ├── 1. 注入 pre-step 动态步骤
  │     ├── 2. 执行原步骤
  │     ├── 3. 注入 post-step 动态步骤
  │     └── 4. 注入 on-error 动态步骤（异常时）
  │
  └── _inject_steps(trigger_point, context)
          │
          └── 返回所有满足条件的 DynamicStep 列表
```

### 1.2 触发点与注入点映射

| `DynamicStep.position` | 注入时机 | 说明 |
|----------------------|---------|------|
| `after` | `post-step` | 在指定步骤执行成功后插入 |
| `before` | `pre-step` | 在指定步骤执行前插入 |
| `replace` | 替换原步骤 | 完全替换原步骤执行 |
| `on-error` | `on-error` | 仅在异常发生时插入 |

### 1.3 DynamicStep 解析

**文件**: `core/dynamic_steps.py`

```python
class DynamicStepParser:
    """从 XML 解析 DynamicStep 列表"""

    @classmethod
    def parse_from_xml(cls, xml_root: Etree) -> List[DynamicStep]:
        ns = {"ski": "http://rodski.io/schema/case"}
        nodes = xml_root.findall(".//ski:dynamic_steps/ski:step", namespaces=ns)
        return [cls._parse_node(node) for node in nodes]

    @classmethod
    def _parse_node(cls, node: Etree) -> DynamicStep:
        return DynamicStep(
            id=node.get("id"),
            keyword=node.get("keyword"),
            params=cls._parse_params(node),
            condition=node.get("condition"),
            position=node.get("position", "after"),
            target_step_index=cls._resolve_target(node),
            timeout=int(node.get("timeout", 0)) or None,
            retry_on_fail=int(node.get("retry_on_fail", 0)),
        )

    @classmethod
    def _resolve_target(cls, node: Etree) -> Optional[int]:
        # 支持通过 trigger + trigger_locator 定位
        # 也支持通过 target_step_index 直接指定
        ...
```

### 1.4 执行上下文（ExecutionContext）

```python
@dataclass
class ExecutionContext:
    """动态步骤执行时的运行时上下文"""
    current_step_index: int
    current_step: TestStep
    current_result: Optional[StepResult]
    variables: Dict[str, Any]      # 当前变量快照
    exception: Optional[Exception]   # 当前异常（仅 on-error 时）
    driver_state: Dict[str, Any]   # 浏览器状态
    loop_state: Optional[Dict]      # 循环上下文（如有）

    @property
    def last_result(self) -> Optional[StepResult]:
        """返回最近一次步骤结果，供条件表达式引用"""
        return self.current_result
```

### 1.5 SKIExecutor 修改点

在 `SKIExecutor._execute_step()` 中插入钩子：

```python
def _execute_step(self, step: TestStep, step_index: int) -> StepResult:
    context = ExecutionContext(
        current_step_index=step_index,
        current_step=step,
        current_result=None,
        variables=self._variables,
        exception=None,
        driver_state=self._get_driver_state(),
        loop_state=None,
    )

    # === Pre-step injection ===
    pre_steps = self._inject_steps("pre-step", context)
    for ds in pre_steps:
        self._execute_dynamic_step(ds)

    # === Main step execution ===
    try:
        result = self._do_execute_step(step)
        context.current_result = result

        # === Post-step injection ===
        if result.status == "pass":
            post_steps = self._inject_steps("post-step", context)
            for ds in post_steps:
                self._execute_dynamic_step(ds)

        return result

    except Exception as e:
        context.exception = e
        # === On-error injection ===
        error_steps = self._inject_steps("on-error", context)
        for ds in error_steps:
            self._execute_dynamic_step(ds)
        raise
```

---

## 二、条件执行

### 2.1 表达式解析（AST Approach）

**文件**: `core/condition_evaluator.py`

设计核心: 将条件表达式解析为 AST，然后用 `_safe_eval()` 对 AST 节点递归求值，只允许预定义的运算符和函数。

```python
import ast
import operator

OPS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Gt: operator.gt,
    ast.Lt: operator.lt,
    ast.GtE: operator.ge,
    ast.LtE: operator.le,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
    ast.And: lambda a, b: a and b,
    ast.Or: lambda a, b: a or b,
    ast.Not: operator.not_,
    ast.Call: None,  # 函数调用单独处理
}

class ConditionEvaluator:
    BUILTINS = {
        "len": len, "str": str, "int": int, "float": float,
        "bool": bool, "any": any, "all": all, "sum": sum,
        "abs": abs, "min": min, "max": max, "list": list,
        "dict": dict, "set": set, "tuple": tuple,
        "getattr": getattr, "hasattr": hasattr,
    }

    def evaluate(self, expression: str) -> bool:
        """解析并求值条件表达式，返回 True/False"""
        tree = ast.parse(expression, mode="eval")
        return bool(self._safe_eval(tree.body))

    def _safe_eval(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            # 变量引用：从 variables 字典中查找
            return self._variables.get(node.id)
        elif isinstance(node, ast.BinOp):
            op_func = OPS[type(node.op)]
            left = self._safe_eval(node.left)
            right = self._safe_eval(node.right)
            return op_func(left, right)
        elif isinstance(node, ast.BoolOp):
            values = [self._safe_eval(v) for v in node.values]
            if isinstance(node.op, ast.And):
                return all(values)
            return any(values)
        elif isinstance(node, ast.UnaryOp):
            op_func = OPS[type(node.op)]
            operand = self._safe_eval(node.operand)
            return op_func(operand)
        elif isinstance(node, ast.Compare):
            return self._eval_compare(node)
        elif isinstance(node, ast.Call):
            return self._eval_call(node)
        elif isinstance(node, ast.Attribute):
            # 支持 ${result.status} 风格的属性访问
            obj = self._variables.get(node.value.id)
            return getattr(obj, node.attr)
        else:
            raise ValueError(f"Unsupported AST node: {type(node).__name__}")
```

### 2.2 支持的表达式语法

```
# 变量引用（${var_name} 在解析阶段替换）
${user_role} == 'admin'
${count} > 0
${env} in ['dev', 'test', 'staging']

# 属性访问
${last_result.status_code} == 200
${response.body.length} > 0

# 逻辑组合
${is_valid} == true and ${role} == 'admin'
${has_error} == false or ${retry_count} > 3
```

### 2.3 与 SKIExecutor 的集成

步骤执行前检查条件：

```python
def _execute_step(self, step: TestStep, step_index: int) -> StepResult:
    # 条件检查
    if step.condition:
        evaluator = ConditionEvaluator(self._variables)
        try:
            condition_met = evaluator.evaluate(step.condition)
        except Exception as e:
            logger.warning(f"Condition evaluation failed: {e}, treating as false")
            condition_met = False

        if not condition_met:
            logger.info(f"Step {step_index} skipped: condition not met: {step.condition}")
            return StepResult(
                status="skipped",
                keyword=step.keyword,
                index=step_index,
                message=f"Condition not met: {step.condition}",
            )

    # 正常执行
    return self._do_execute_step(step, step_index)
```

---

## 三、循环执行

### 3.1 循环配置解析

**文件**: `core/loop_executor.py`

```python
from dataclasses import dataclass
import re

class LoopParser:
    """解析 loop 属性字符串"""

    # 正则匹配: fixed / for_each / until / while
    FIXED_RE = re.compile(r'^(\d+)$')
    FOR_EACH_RE = re.compile(r'^for\s+(\w+)\s+in\s+(.+)$')
    UNTIL_RE = re.compile(r'^(until)\s+(.+?)\s+max=(\d+)$')
    WHILE_RE = re.compile(r'^(while)\s+(.+?)\s+max=(\d+)$')

    @classmethod
    def parse(cls, loop_str: str) -> LoopConfiguration:
        """解析 loop 属性值，返回 LoopConfiguration"""
        if cls.FIXED_RE.match(loop_str):
            count = int(loop_str)
            return LoopConfiguration(loop_type="fixed", count=count)

        m = cls.FOR_EACH_RE.match(loop_str)
        if m:
            item_var, items_expr = m.groups()
            # items_expr 可能引用变量，如 ${search_results}
            return LoopConfiguration(
                loop_type="for_each",
                item_var=item_var,
                items_ref=items_expr,  # 待运行时求值
            )

        m = cls.UNTIL_RE.match(loop_str)
        if m:
            _, condition, max_iter = m.groups()
            return LoopConfiguration(
                loop_type="until",
                condition=condition,
                max_iterations=int(max_iter),
            )

        m = cls.WHILE_RE.match(loop_str)
        if m:
            _, condition, max_iter = m.groups()
            return LoopConfiguration(
                loop_type="while",
                condition=condition,
                max_iterations=int(max_iter),
            )

        raise ValueError(f"Invalid loop syntax: {loop_str}")
```

### 3.2 LoopExecutor

```python
class LoopExecutor:
    def __init__(self, ski_executor: SKIExecutor):
        self._executor = ski_executor
        self._condition_evaluator = ConditionEvaluator({})

    def execute_loop(
        self,
        step: TestStep,
        loop_config: LoopConfiguration,
    ) -> List[LoopIterationResult]:
        """执行循环步骤，返回每次迭代结果"""
        results = []
        context_vars = dict(self._executor._variables)

        # 获取迭代项（for_each 场景）
        items = self._resolve_items(loop_config, context_vars)

        if loop_config.loop_type == "fixed":
            iterations = range(loop_config.count)
        elif loop_config.loop_type == "for_each":
            iterations = enumerate(items)
        else:
            iterations = range(loop_config.max_iterations)

        for iteration_data in iterations:
            if loop_config.loop_type in ("fixed", "for_each"):
                iteration_index, iteration_item = iteration_data
            else:
                iteration_index = iteration_data
                iteration_item = None

            # 设置循环变量
            if loop_config.loop_type == "for_each" and iteration_item is not None:
                context_vars[loop_config.item_var] = iteration_item
            context_vars[loop_config.index_var] = iteration_index

            # 备份原变量，植入循环变量
            original_vars = dict(self._executor._variables)
            self._executor._variables.update(context_vars)

            try:
                result = self._executor._do_execute_step(step, step.index)
            except Exception as e:
                if loop_config.break_on_fail:
                    results.append(LoopIterationResult(
                        iteration=iteration_index,
                        variables=dict(context_vars),
                        result=StepResult(status="fail", error=str(e)),
                        duration_ms=0,
                    ))
                    break
                result = StepResult(status="fail", error=str(e))

            results.append(LoopIterationResult(
                iteration=iteration_index,
                variables=dict(context_vars),
                result=result,
                duration_ms=getattr(result, 'duration_ms', 0),
            ))

            # 恢复变量
            self._executor._variables = original_vars

            # 检查 until/while 终止条件
            if loop_config.loop_type in ("until", "while"):
                self._condition_evaluator._variables = self._executor._variables
                should_continue = self._condition_evaluator.evaluate(loop_config.condition)
                if loop_config.loop_type == "until":
                    should_continue = not should_continue
                if not should_continue:
                    break

        return results

    def _resolve_items(self, config: LoopConfiguration, context: Dict) -> List:
        if config.items_ref:
            # 从 variables 中解析引用
            ref = config.items_ref  # 如 "${search_results}"
            var_name = ref[2:-1]   # 去除 ${}
            return context.get(var_name, [])
        return []
```

### 3.3 循环与 Result XML

每次迭代生成独立 `<step>` 节点，带循环属性：

```xml
<step index="3" keyword="click" status="pass"
      loop_id="lp_001" loop_type="for_each"
      loop_iteration="0/3" loop_item="result_0">
  <param name="locator">#item-${item.index}</param>
</step>
<step index="3" keyword="click" status="pass"
      loop_id="lp_001" loop_type="for_each"
      loop_iteration="1/3" loop_item="result_1">
  <param name="locator">#item-${item.index}</param>
</step>
```

---

## 四、Schema 变更

### 4.1 Case XSD 扩展

**文件**: `schemas/case.xsd`

```xml
<!-- 条件执行: 在 step 上添加 condition 属性 -->
<xs:attribute name="condition" type="xs:string" use="optional"/>

<!-- 循环执行: 在 step 上添加 loop 属性 -->
<xs:attribute name="loop" type="xs:string" use="optional"/>

<!-- 动态步骤声明 -->
<xs:element name="dynamic_steps">
  <xs:complexType>
    <xs:sequence>
      <xs:element name="step" maxOccurs="unbounded">
        <xs:complexType>
          <xs:sequence>
            <xs:element name="param" minOccurs="0" maxOccurs="unbounded"/>
          </xs:sequence>
          <xs:attribute name="id" type="xs:string" use="required"/>
          <xs:attribute name="keyword" type="xs:string" use="required"/>
          <xs:attribute name="position" type="xs:string" use="optional"/>
          <xs:attribute name="trigger" type="xs:string" use="optional"/>
          <xs:attribute name="trigger_locator" type="xs:string" use="optional"/>
          <xs:attribute name="target_step_index" type="xs:integer" use="optional"/>
          <xs:attribute name="condition" type="xs:string" use="optional"/>
          <xs:attribute name="timeout" type="xs:integer" use="optional"/>
          <xs:attribute name="retry_on_fail" type="xs:integer" use="optional"/>
        </xs:complexType>
      </xs:element>
    </xs:sequence>
  </xs:complexType>
</xs:element>
```

---

## 五、数据流总览

```
Case XML (with condition/loop/dynamic_steps)
  │
  ├── CaseParser 解析 XML
  ├── DynamicStepParser 解析 dynamic_steps → List[DynamicStep]
  ├── LoopParser 解析 loop 属性 → LoopConfiguration
  │
  ▼
SKIExecutor._execute_step()
  │
  ├── 检查 step.condition → ConditionEvaluator
  │     └── 不满足 → StepResult(status=skipped)
  │
  ├── 检查 step.loop → LoopExecutor
  │     └── 循环执行 N 次 → List[LoopIterationResult]
  │
  ├── 执行主步骤
  │
  ├── _inject_steps(pre/post/on-error) → DynamicStep 执行
  │
  ▼
Result XML (with skipped/loop/dynamic step records)
```
