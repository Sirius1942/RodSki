# Iteration 35: Scenario XML 基座

**版本**: v6.3.0-alpha.1  
**分支**: feature/iteration-35-scenario-xml  
**预计工时**: 6h  
**优先级**: P0  
**状态**: 待开始  
**依赖**: iteration-34 完成，v6.3.0 设计稿确认

---

## 目标

1. 在 case XML 中引入 `<scenario>`，让 case 内测试场景成为一等结构。
2. 更新 schema 与 CaseParser，形成 case/scenario/step 树。
3. 保持旧 case 无 `<scenario>` 时的兼容执行。
4. 明确 `<if>` 只表达运行时动态分支，不再承担静态执行开关语义。
5. 支持同一 case 内 scenario `depends` 基础跳过语义。

## 包含工作项

| WI | 名称 | 大小 | 来源 |
|----|------|------|------|
| WI-80 | case.xsd 支持 scenario | M | v6.3.0 scenario plan design |
| WI-81 | CaseParser scenario 树解析 | L | v6.3.0 scenario plan design |
| WI-82 | scenario 兼容执行 | M | v6.3.0 scenario plan design |
| WI-83 | scenario depends 基础语义 | M | v6.3.0 scenario plan design |
| WI-84 | scenario 文档与验收用例 | S | v6.3.0 scenario plan design |

## 设计约束

- 不含 `<scenario>` 的旧 case 必须继续按原有 case 级步骤执行。
- `<test_case>` 内允许 scenario 与裸 `test_step` 共存，裸步骤按兼容规则执行。
- `<scenario>` 内允许 `<if>` / `<loop>` 等运行时控制结构。
- scenario `id` 在同一 case 内必须唯一。
- v6.3.0 第一阶段只支持同一 case 内 `depends`。
- 本迭代不引入 plan XML、tag/group selector 或 debug plan。

## 验收标准

- TC040: `<scenario>` 正确解析，多个 scenario 按 XML 顺序执行。
- TC041: `id/title/group/tag/depends` 属性正确读取。
- TC042: scenario 与裸 `test_step` 共存时兼容执行。
- TC043: scenario 内嵌套 `<if>` 仍按运行时条件分支执行。
- TC044: 被依赖 scenario 失败或跳过时，依赖方标记为 skipped。
- 旧 rodski-demo 用例无 scenario 时行为不变。

## 参考文档

- `.pb/design/v6.3.0-scenario-plan-discussion-draft.md`
- `rodski/docs/TEST_CASE_WRITING_GUIDE.md`
- `rodski/docs/SKILL_REFERENCE.md`