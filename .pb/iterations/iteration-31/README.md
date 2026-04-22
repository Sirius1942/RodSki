# Iteration 31: SQLite 测试数据运行时落地

**版本**: v5.9.0  
**分支**: feature/iteration-31-sqlite-runtime  
**预计工时**: 6h  
**优先级**: P0  
**状态**: ✅ 已完成  
**依赖**: iteration-30 完成

---

## 目标

1. 将 `DataTableParser` 升级为统一数据 facade，支持 XML + SQLite 共存
2. 新增 SQLite 数据源与 schema 校验器，落实“跨源冲突即报错”和“同表固定字段集合”约束
3. 在不改变现有 DSL 的前提下，保持 `type` / `send` / `verify` / `DB` 的数据读取语义不变
4. 完成核心约束文档、数据组织文档与实现对齐

## 包含工作项

| WI | 名称 | 大小 | 来源 |
|----|------|------|------|
| WI-31 | 统一数据管理 facade | L | sqlite testdata coexistence design |
| WI-32 | SQLite data source + schema validator | L | sqlite testdata coexistence design |
| WI-33 | 运行时接线与兼容层 | M | sqlite testdata coexistence design |
| WI-34 | 运行时单元测试基础覆盖 | M | sqlite testdata coexistence design |

## 设计约束

- `data.xml` 仍是唯一 XML 输入数据文件，`data_verify.xml` 仍是唯一验证 XML 文件
- `testdata.sqlite` 是可选且推荐的主测试数据存储
- XML + SQLite 可以共存，但混合模式仅兼容、不推荐作为常态
- 同一逻辑表不能同时由 XML 与 SQLite 拥有；跨源同名必须报错
- SQLite 逻辑表必须显式声明 schema，且所有数据行字段集合完全一致
- `globalvalue.xml` 保持独立，不进入 SQLite
- `get_data(table_name, data_id)` 等既有运行时语义必须保持稳定
