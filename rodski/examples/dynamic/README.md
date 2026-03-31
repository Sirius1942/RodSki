# 动态执行示例

本目录包含 RodSki 动态执行能力的示例用例：

- `conditional_case.xml` - 条件执行示例：演示 `condition` 属性在不同条件下的步骤执行
- `loop_case.xml` - 循环执行示例：演示固定次数、for_each、until、while 四种循环类型
- `dynamic_injection_case.xml` - 动态步骤注入示例：演示在 pre-step / post-step / on-error 注入动态步骤

## 运行示例

```bash
# 执行条件执行示例
ski run examples/dynamic/conditional_case.xml

# 执行循环示例
ski run examples/dynamic/loop_case.xml

# 执行动态步骤注入示例
ski run examples/dynamic/dynamic_injection_case.xml
```
