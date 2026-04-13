# Iteration 26: 契约统一 + 历史包袱清理

**版本**: v5.4.0  
**分支**: release/v5.4.0  
**预计工时**: 5h  
**优先级**: P0  
**状态**: 📋 待开始

---

## 目标

1. model_parser.py 移除旧定位器格式，只保留 `<location>` 多定位器格式
2. 迁移所有项目内 XML 文件到唯一格式
3. vision/locator.py 移除旧前缀解析
4. 移除 Excel 相关代码和依赖
5. Agent 示例归档

## 包含工作项

| WI | 名称 | 大小 | 来源 |
|----|------|------|------|
| WI-01 | model_parser.py 移除旧定位器格式 | M | Phase 0 |
| WI-02 | 迁移所有 model XML 到 `<location>` 格式 | M | Phase 0 |
| WI-03 | vision/locator.py 移除旧前缀解析 | S | Phase 0 |
| WI-05 | 移除 Excel 相关代码 | S | Phase 1 |
| WI-07 | Agent 示例归档 | S | Phase 1 |

## Breaking Changes

- 所有使用 `locator="..."` 属性或 `type="id" value="xxx"` 简化格式的 XML 将不再被解析
- `openpyxl` 依赖移除
