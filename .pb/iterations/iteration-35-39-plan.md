# 迭代 35-39 总体规划: v6.3.0 Scenario 与测试计划 XML

**规划日期**: 2026-05-07  
**当前版本基线**: v6.1.8  
**目标版本**: v6.3.0  
**来源**: `.pb/design/v6.3.0-scenario-plan-discussion-draft.md`  
**目标**: 将“静态执行范围选择”从 case XML 的 `<if>` 中移出，形成 `<scenario>`、显式 `plan/*.xml` 与 tag/group 临时选择器三层清晰边界。

---

## 拆分原则

1. **先 XML 基座，后执行选择** — `<scenario>` 必须先成为 case 树的一等结构，再引入 plan 和 selector。
2. **一个最终执行模型** — 显式 plan 与 tag/group selector 都编译为 `TestPlanSelection`，执行器只消费确定后的选择结果。
3. **事实来源边界固定** — 测试计划只在 `plan/*.xml`，不进入 `data/data.sqlite`，不作为测试数据加载。
4. **显式 plan 与临时 selector 固定互斥** — 不支持在同一次 `rodski run` 中同时提供 `@plan_id` 与 `--tag` / `--group` / `--exclude-tag` / `--priority` 等执行范围 selector。
5. **调试能力最后收口** — scenario/step debug 依赖 plan、selection、CLI 和报告层级全部稳定。
6. **阶段 6 不进 v6.3.0 第一阶段** — VSCode 页面、失败重跑计划和计划数据库讨论进入后续版本 backlog；plan 与 selector 同时执行不进入 backlog。

---

## 版本与分支规划

| 迭代 | 版本号 | 分支名 | 预计工时 | 主要内容 |
|------|--------|--------|----------|----------|
| iteration-35 | v6.3.0-alpha.1 | feature/iteration-35-scenario-xml | 6h | `<scenario>` XML、CaseParser、兼容执行、depends 基础语义 |
| iteration-36 | v6.3.0-alpha.2 | feature/iteration-36-plan-runtime | 6h | `plan.xsd`、PlanParser、`TestPlanSelection`、`rodski run @plan_id` |
| iteration-37 | v6.3.0-beta.1 | feature/iteration-37-selector-runtime | 5h | `--tag/--group/--exclude-tag` 临时 selector 与固定互斥裁决 |
| iteration-38 | v6.3.0-beta.2 | feature/iteration-38-plan-cli | 6h | `rodski plan` 初始化、查看、校验、创建、启停与 from-tag/from-group |
| iteration-39 | v6.3.0 | feature/iteration-39-plan-debug-release | 6h | scenario/step debug、报告层级、demo 验收与发布收口 |

**总计**: 29h

---

## 迭代间依赖

```text
iteration-35 (Scenario XML 基座)
       │
       ▼
iteration-36 (Plan XML + TestPlanSelection)
       │
       ▼
iteration-37 (Tag/Group 临时选择器)
       │
       ▼
iteration-38 (Plan CLI 管理)
       │
       ▼
iteration-39 (Debug 执行 + 报告 + 发布)
```

---

## v6.3.0 范围

### 必做

1. `case.xsd` 支持 `<scenario>`。
2. CaseParser 解析 case/scenario/step 树。
3. 旧 case 无 `<scenario>` 时继续兼容执行。
4. `plan/{测试目的}_{测试类型}.xml` 成为测试计划事实来源。
5. `plan.xsd`、PlanParser、`TestPlanSelection`。
6. `rodski run @plan_id` 与默认 `plan/project_full.xml` 规则。
7. `--tag`、`--group`、`--exclude-tag` 临时 selector。
8. `@plan_id` 与 `--tag` / `--group` / `--exclude-tag` / `--priority` 等执行范围 selector 固定互斥。
9. `rodski plan init/list/show/validate/preview/create/add/enable/disable`。
10. `rodski plan create --from-tag/--from-group`。
11. `kind="scenario_debug"` 与 `kind="step_debug"` 调试执行。
12. 执行报告体现 Project → TestPlan → Case → Scenario 与明确 skipped 原因。

### 不做

1. 不新增 SQLite 测试计划表。
2. 不把 plan XML 写入 `data/data.sqlite`。
3. 不把 plan XML 作为测试数据加载。
4. 不开发 rodski-vscode 可视化计划配置页。
5. 不支持 `@plan_id` 与 tag/group/priority selector 同时执行。
6. 不支持 `--filter-tag` 形式的 plan 后过滤。
7. 不生成失败重跑计划。
8. 不支持跨 Project 执行。

---

## 验收测试映射

| 迭代 | 覆盖用例 | 重点 |
|------|----------|------|
| iteration-35 | TC040-TC044 | scenario 解析、属性、裸步骤兼容、scenario 内 if、depends 跳过 |
| iteration-36 | TC046、TC049-TC054 | plan schema、显式 plan 执行、默认执行、关闭优先级、stale 引用 |
| iteration-37 | TC055-TC060、TC078 | tag/group 临时执行、exclude、继承、固定互斥、dry-run preview、不支持 filter-tag |
| iteration-38 | TC045、TC047-TC048、TC061-TC068 | plan init/list/show/validate/preview/create/add/enable/disable/from-tag/from-group |
| iteration-39 | TC069-TC077 | debug plan 创建、scenario/step 调试、prepare、step_mode、cleanup |

---

## 关键风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| `plan/` 是新增标准目录 | 核心约束文档仍可能只列旧目录 | iteration-36 同步更新 `CORE_DESIGN_CONSTRAINTS.md` 与项目初始化文档 |
| `<if>` 历史上被当作静态开关 | 用户迁移认知成本高 | iteration-35 文档明确 `<if>` 回归运行时分支，提供迁移示例 |
| selector 与 plan 同时使用 | 执行范围不可预测 | iteration-37 直接报错，覆盖 `--tag`、`--group`、`--exclude-tag`、`--priority` 和 `--filter-tag` 验收 |
| `depends` 与 skipped 统计 | 报告和结果数据可能不一致 | iteration-35 先定义同 case 内依赖，iteration-39 统一报告 skipped 原因 |
| plan 引用 stale case/scenario/step | 删除 XML 后历史计划残留 | iteration-36/38 分别覆盖 run 行为与 validate 行为 |
| debug step prepare 语义复杂 | 可能破坏现场状态 | iteration-39 分别测试 `auto/case/none` 与 `all/from/only` |

---

## v6.4+ 后续 backlog

| 候选迭代 | 候选版本 | 内容 | 前置条件 |
|----------|----------|------|----------|
| iteration-40 | v6.4.0 | rodski-vscode 页面读写 `plan/*.xml` | v6.3.0 plan XML 与 CLI 稳定 |
| iteration-41 | v6.5.0 | 失败重跑计划生成 | 需要结果报告能稳定映射 failed scenario/step |
| 待定 | 待定 | 计划数据库或执行历史数据库 | 只有在 XML plan 无法满足协作/查询需求后再重新设计 |

这些 backlog 只登记方向，不在本次创建开发任务。