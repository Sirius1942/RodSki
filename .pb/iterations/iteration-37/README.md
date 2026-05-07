# Iteration 37: Tag/Group 临时选择器

**版本**: v6.3.0-beta.1  
**分支**: feature/iteration-37-selector-runtime  
**预计工时**: 5h  
**优先级**: P0  
**状态**: 待开始  
**依赖**: iteration-36 完成

---

## 目标

1. 支持 `rodski run --tag` / `--group` / `--exclude-tag` 临时选择器执行。
2. selector 从 case XML 元数据生成一次性 `TestPlanSelection`。
3. selector 模式不读取、不写入 `plan/*.xml`。
4. 禁止 `@plan_id` 与 `--tag` / `--group` / `--exclude-tag` / `--priority` 等执行范围 selector 同时使用。
5. 支持 selector dry-run preview。

## 包含工作项

| WI | 名称 | 大小 | 来源 |
|----|------|------|------|
| WI-90 | run selector CLI 参数 | S | v6.3.0 scenario plan design |
| WI-91 | scenario 元数据索引与继承 | M | v6.3.0 scenario plan design |
| WI-92 | 临时 TestPlanSelection 编译 | L | v6.3.0 scenario plan design |
| WI-93 | plan 与 selector 冲突裁决 | S | v6.3.0 scenario plan design |

## 设计约束

- `--tag` 与 `--tags` 都支持，推荐 `--tag`。
- `--exclude-tag` 与 `--exclude-tags` 都支持，推荐 `--exclude-tag`。
- `--tag smoke,p0` 是 OR 匹配。
- `--group negative` 是精确匹配。
- `<cases tags="...">` 与 `<scenario tag="...">` 合并为有效 tag 集合。
- v6.3.0 第一版不新增 case 级 `tag` 属性。
- selector 模式不读取 plan XML，不修改 case/model/data/globalvalue。
- 显式 plan 模式与 selector 模式是两个独立入口，同一次 `rodski run` 只能选择其中一种。
- 不实现 `--filter-tag`，也不允许用 `@plan_id + --tag/--group/--priority` 表达 plan 后过滤。

## 验收标准

- `rodski run --tag smoke` 按 scenario tag 生成临时选择结果。
- `rodski run --group negative` 只执行 group 命中的 scenario。
- `--exclude-tag slow` 从候选集中排除命中的 scenario。
- `<cases tags>` 与 `<scenario tag>` 继承规则正确。
- `rodski run @plan_id --tag smoke` 报错并给出明确修复建议。
- `rodski run @plan_id --group negative` 报错并给出明确修复建议。
- `rodski run @plan_id --exclude-tag slow` 报错并给出明确修复建议。
- `rodski run @plan_id --priority P0` 报错并给出明确修复建议。
- `rodski run @plan_id --filter-tag smoke` 报错，明确不支持 plan 后过滤。
- `rodski run --tag smoke --dry-run` 输出临时选择结果。

## 参考文档

- `.pb/design/v6.3.0-scenario-plan-discussion-draft.md`
- `.pb/iterations/iteration-37/acceptance_tests.md`
- `rodski/docs/TEST_CASE_WRITING_GUIDE.md`
- `rodski/docs/AGENT_INTEGRATION.md`