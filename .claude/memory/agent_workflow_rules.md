---
name: agent_workflow_rules
description: Agent 自主开发工作流规范
type: feedback
---

Agent 在 RodSki 项目中自主开发时，必须严格遵循以下工作流：

**工作流程**：
1. 阅读 `phoenixbear/design/CORE_DESIGN_CONSTRAINTS.md` 确认设计约束
2. 从 `phoenixbear/iterations/` 选择下一个待处理迭代
3. 实现功能（最小化代码）
4. 运行 `python selftest.py` 测试
5. 使用 `.claude/templates/change_report.md` 生成报告
6. 创建 commit（Conventional Commits 格式）
7. 保存报告到 `.claude/reports/`
8. 等待人工确认后继续

**核心约束（绝对不可违反）**：
- ⭐ `CORE_DESIGN_CONSTRAINTS.md` 中任何约束条款
- ⭐ `TEST_CASE_WRITING_GUIDE.md` 中任何编写规范

**Agent 停止点（必须请求人工决策）**：
1. 测试失败
2. 修改核心接口（BaseDriver、KeywordEngine、VisionLocator）
3. 新增依赖
4. 覆盖率下降
5. Breaking Changes
6. 修改 XML Schema
