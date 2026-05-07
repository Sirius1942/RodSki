# Iteration 38: Plan CLI 管理命令

**版本**: v6.3.0-beta.2  
**分支**: feature/iteration-38-plan-cli  
**预计工时**: 6h  
**优先级**: P0  
**状态**: 待开始  
**依赖**: iteration-37 完成

---

## 目标

1. 新增 `rodski plan` 命令族，支持测试计划初始化、查看、校验、预览与修改。
2. CLI 直接复用 PlanParser、TestPlanSelection 与 selector 编译逻辑。
3. 支持从 tag/group 临时选择结果生成持久 plan XML。
4. 让 Agent 可以通过 CLI 安全读写 `plan/*.xml`，不直接改 case XML 静态开关。

## 包含工作项

| WI | 名称 | 大小 | 来源 |
|----|------|------|------|
| WI-94 | plan init/list/show | M | v6.3.0 scenario plan design |
| WI-95 | plan validate/preview | M | v6.3.0 scenario plan design |
| WI-96 | plan create/add-case/add-scenario | M | v6.3.0 scenario plan design |
| WI-97 | plan enable/disable | S | v6.3.0 scenario plan design |
| WI-98 | plan create --from-tag/--from-group | M | v6.3.0 scenario plan design |

## 设计约束

- `rodski plan` 只读写 `plan/*.xml`。
- `plan validate` 负责跨文件引用校验，XSD 只负责单文件结构约束。
- `plan preview` 输出最终执行范围，不实际执行步骤。
- `create --from-tag/--from-group` 使用 selector 结果生成显式 plan 后落盘。
- 默认不覆盖已有 plan 文件，只有显式 `--force` 可以覆盖初始化结果。
- 本迭代不实现 scenario/step debug 执行，只创建常规 suite plan 管理能力。

## 验收标准

- `rodski plan init` 创建 `plan/project_full.xml`。
- `rodski plan list/show` 正确列出和展示计划。
- `rodski plan validate` 发现 stale case/scenario/step 引用。
- `rodski plan preview` 输出最终将执行的 case/scenario/step。
- `plan create/add-case/add-scenario` 能生成和修改 suite plan。
- `plan enable/disable case/scenario` 正确更新 execute 属性。
- `plan create --from-tag/--from-group` 生成可被 `rodski run @plan_id` 执行的 plan。

## 参考文档

- `.pb/design/v6.3.0-scenario-plan-discussion-draft.md`
- `rodski/docs/API_REFERENCE.md`
- `rodski/docs/AGENT_INTEGRATION.md`