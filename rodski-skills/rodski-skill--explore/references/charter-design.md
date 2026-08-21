# Charter 设计最佳实践

## 好的 Charter 特征

### 1. 目标明确
- ✅ "验证支付模块在边界条件下的健壮性"
- ❌ "测试支付功能"（太泛）

### 2. 基线清晰
- 列出参考的已通过用例
- 提取已验证的 Oracle

### 3. 探索维度具体
- ✅ "边界值（0、负数、超大）、并发、唯一性"
- ❌ "各种异常情况"（不具体）

### 4. 预算合理
- 10-50 步，5-15 分钟
- 根据模块复杂度调整

## Charter 模板

```json
{
  "goal": "验证 [模块名] 在 [场景] 下的 [质量属性]",
  "baseline_cases": ["TC_XXX", "TC_YYY"],
  "verified_oracles": ["已知的正常行为1", "已知的正常行为2"],
  "explore_dimensions": ["维度1", "维度2"],
  "uniqueness_fields": {"field": "说明"},
  "budget": {"steps": 30, "duration": 600}
}
```
