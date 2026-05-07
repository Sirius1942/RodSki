# Iteration 36: Plan XML 与 TestPlanSelection

**版本**: v6.3.0-alpha.2  
**分支**: feature/iteration-36-plan-runtime  
**预计工时**: 6h  
**优先级**: P0  
**状态**: 待开始  
**依赖**: iteration-35 完成

---

## 目标

1. 新增 `plan/` 目录约定与 `plan/{测试目的}_{测试类型}.xml` 测试计划格式。
2. 新增 `plan.xsd` 与 PlanParser。
3. 引入 `TestPlanSelection`，把显式 plan 应用到 case/scenario/step 树。
4. 支持 `rodski run @plan_id` 和默认计划解析规则。
5. 明确 plan 引用 stale case/scenario/step 时的 run 与 dry-run 行为。

## 包含工作项

| WI | 名称 | 大小 | 来源 |
|----|------|------|------|
| WI-85 | plan.xsd 与 PlanParser | L | v6.3.0 scenario plan design |
| WI-86 | TestPlanSelection 内存模型 | L | v6.3.0 scenario plan design |
| WI-87 | 显式 plan 执行规则 | M | v6.3.0 scenario plan design |
| WI-88 | `rodski run @plan_id` 接入 | M | v6.3.0 scenario plan design |
| WI-89 | stale 引用与 dry-run 行为 | S | v6.3.0 scenario plan design |

## 设计约束

- `plan/*.xml` 是测试计划唯一事实来源。
- plan XML 不进入 `data/data.sqlite`，也不作为测试数据加载。
- `<test_plan id="...">` 必须与文件名 stem 一致。
- `rodski run` 未指定计划时优先读取 `plan/project_full.xml`。
- XML `<case execute="否">` 是硬关闭，优先级最高。
- 本迭代只实现显式 plan 运行时，不实现 plan 管理 CLI 和 tag/group selector。

## 验收标准

- `plan.xsd` 能校验 suite/scenario_debug/step_debug 的基本结构。
- `rodski run @project_full` 读取 `plan/project_full.xml`。
- `default_execute="是"` 时执行 XML 中开启的 case/scenario。
- `default_execute="否"` 时只执行 plan 显式选择项。
- plan case/scenario/step 关闭能产生明确 skipped 原因。
- XML case `execute="否"` 优先于 plan 中的开启配置。
- stale plan item 不被实际执行，dry-run 能提示 stale 引用。

## 参考文档

- `.pb/design/v6.3.0-scenario-plan-discussion-draft.md`
- `rodski/docs/CORE_DESIGN_CONSTRAINTS.md`
- `rodski/docs/DATA_FILE_ORGANIZATION.md`