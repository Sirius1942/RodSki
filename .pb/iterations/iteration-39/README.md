# Iteration 39: 调试执行、报告与 v6.3.0 收口

**版本**: v6.3.0  
**分支**: feature/iteration-39-plan-debug-release  
**预计工时**: 6h  
**优先级**: P0  
**状态**: 待开始  
**依赖**: iteration-38 完成

---

## 目标

1. 支持 `kind="scenario_debug"` 与 `kind="step_debug"` 调试计划。
2. 支持 `prepare=auto|case|none`、`step_mode=all|from|only`、`cleanup=是|否`。
3. 新增 `rodski plan debug-scenario` 与 `debug-step` 创建调试计划。
4. 执行报告体现 Project → TestPlan → Case → Scenario 层级与 skipped 原因。
5. 完成 v6.3.0 文档、demo、单元测试和发布前回归收口。

## 包含工作项

| WI | 名称 | 大小 | 来源 |
|----|------|------|------|
| WI-99 | debug plan CLI 创建 | M | v6.3.0 scenario plan design |
| WI-100 | scenario_debug 执行 | M | v6.3.0 scenario plan design |
| WI-101 | step_debug 执行 | L | v6.3.0 scenario plan design |
| WI-102 | 报告层级与 skipped 原因 | M | v6.3.0 scenario plan design |
| WI-103 | v6.3.0 发布前收口 | M | v6.3.0 scenario plan design |

## 设计约束

- debug plan 不修改 case XML、model XML、data.sqlite 或 globalvalue.xml。
- `prepare=auto` 执行 `pre_process` 与目标 step 前置步骤。
- `prepare=case` 只执行 `pre_process`。
- `prepare=none` 不执行前置，直接执行目标步骤。
- `step_mode=only` 只执行指定 step。
- `step_mode=from` 从指定 step 执行到 scenario 结束。
- `step_mode=all` 执行整个 scenario。
- `cleanup="是"` 时执行 `post_process`，否则保留现场。

## 验收标准

- `rodski plan debug-scenario` 创建 `kind="scenario_debug"` 的 plan。
- `rodski run @*_scenario_debug --debug` 执行指定 scenario。
- `rodski plan debug-step` 创建 `kind="step_debug"` 的 plan。
- `step_mode=only/from/all` 语义正确。
- `prepare=auto/case/none` 语义正确。
- `cleanup=是` 时执行 `post_process`。
- 报告输出 Plan、Case、Scenario 层级与 skipped 来源。
- v6.3.0 相关文档、demo 和测试全部完成。

## 参考文档

- `.pb/design/v6.3.0-scenario-plan-discussion-draft.md`
- `rodski/docs/API_REFERENCE.md`
- `rodski/docs/TEST_CASE_WRITING_GUIDE.md`
- `rodski/docs/AGENT_INTEGRATION.md`