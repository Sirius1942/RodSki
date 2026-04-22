# 迭代规划总览

**最近更新**: 2026-04-21

---

## 已完成迭代

| 迭代 | 版本 | 状态 | 主要内容 |
|------|------|------|----------|
| iteration-14 ~ 19 | v4.6.0 ~ v4.11.0 | ✅ 已完成 | P0修复、清理、demosite、关键字、视觉定位、负面测试 |
| iteration-20 | v5.0.0 | ✅ 已完成 | DB 关键字重写 |
| iteration-21 | v5.1.0 | ✅ 已完成 | DB demo 迁移 |
| iteration-22 | v5.2.0 | ✅ 已完成 | 文档更新 |
| iteration-23 | v5.3.1 | ✅ 已完成 | 数据文件组织修正 |
| iteration-24 | v5.3.1 | ✅ 已完成 | verify 空校验修复 |
| iteration-25 | v5.3.1 | ✅ 已完成 | 框架文档修正 |

---

## 架构改进迭代 (iteration-26 ~ 29)

**规划来源**: `.pb/requirements/architecture_improvement_v6.md`  
**总体规划**: `.pb/iterations/iteration-26-29-plan.md`  
**目标**: 将 RodSki 收敛为"面向 AI Agent 的确定性执行引擎 + 活文档协议层"

| 迭代 | 版本 | 工时 | 状态 | 主要内容 |
|------|------|------|------|----------|
| iteration-26 | v5.4.0 | 5h | 📋 待开始 | 契约统一（代码）+ Excel 移除 + Agent 示例归档 |
| iteration-27 | v5.5.0 | 4h | 📋 待开始 | 文档契约统一（定位器 + Excel） |
| iteration-28 | v5.6.0 | 5h | 📋 待开始 | LLM 统一服务层（capabilities + config 合并） |
| iteration-29 | v5.7.0 | 4h | 📋 待开始 | 定位叙事统一（README + AGENT_INTEGRATION 重写） |

**合计**: 18h

### 迭代依赖

```
iteration-26 → iteration-27 → iteration-28 → iteration-29
```

---

## 当前进行中

| 迭代 | 版本 | 状态 | 主要内容 |
|------|------|------|----------|
| iteration-30 | v7.0 | 🚧 进行中 | rodski-agent Wave 1 优化：报告、Trace/Network、记忆与文档 |

---

## 已规划待执行

### SQLite 测试数据与 CLI 收口 (iteration-31 ~ 33)

**规划来源**: `.pb/specs/sqlite_testdata_coexistence_design.md`  
**目标**: 在不改变现有 DSL 语义的前提下，引入 SQLite 测试数据、数据查询 CLI 与项目初始化 CLI

| 迭代 | 版本 | 工时 | 状态 | 主要内容 |
|------|------|------|------|----------|
| iteration-31 | v5.9.0 | 6h | ✅ 已完成 | XML + SQLite 统一数据 facade、SQLite source、schema validator、运行时接线 |
| iteration-32 | v5.10.0 | 4h | ✅ 已完成 | `rodski data` CLI（list/schema/show/query/validate） |
| iteration-33 | v5.10.0 | 4h | ✅ 已完成 | `rodski init` CLI、SQLite 元表初始化、demo 验收与发布前收口 |

**合计**: 14h

### 迭代依赖

```
iteration-31 → iteration-32 → iteration-33
```

### 执行说明

- 采用 **feature 分支开发，main 分支发布**
- `iteration-31` 对应分支：`feature/iteration-31-sqlite-runtime`
- `iteration-32` 对应分支：`feature/iteration-32-data-cli`
- `iteration-33` 对应分支：`feature/iteration-33-init-cli`
- `v5.9.0` / `v5.10.0` release tag 只从 `main` 打出

---

## 关键原则

1. **按顺序执行** — 不要跳过或并行
2. **每个迭代独立交付** — 完成后立即发布版本
3. **任务失败立即停止** — 记录问题，调整计划
4. **文档同步更新** — 每个迭代都要更新 record.md
5. **回归测试必做** — 确保无回归问题
6. **分支开发主干发布** — 功能在 feature 分支完成，release 从 `main` 产出

---

## 历史规划

- `.pb/iterations/iteration-14-19-plan.md` — 迭代 14-19 总体规划
- `.pb/iterations/iteration-26-29-plan.md` — 迭代 26-29 架构改进规划
- `.pb/specs/sqlite_testdata_coexistence_design.md` — SQLite 测试数据共存设计
