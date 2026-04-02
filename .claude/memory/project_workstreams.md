---
name: project_workstreams
description: RodSki 项目当前工作主线和迭代状态
type: project
---

**当前迭代状态**：

| 迭代 | 主题 | 状态 |
|------|------|------|
| iteration-03 | Bug 修复与依赖完善 | 已完成 |
| iteration-04 | Agent 集成基础设施 | 已完成 |
| iteration-05 | 活文档增强 | 待开始 |
| iteration-06 | 动态执行能力 | 待开始 |
| iteration-07 | 文档体系重构 | 待开始 |

**当前分支**：
- `main` — 主干
- `acceptance-validation` — 验收分支（从 main 拉取）
- `fix/click-locator-bug` — 已合并到 main 的 Bug 修复分支

**待处理事项**：
- 修复 P0 Bug：`driver.type` 方法不存在导致批量输入失败
- 修复 P1 违规：移除 pytest 依赖，改用 selftest.py
- 按优先级修复设计约束审计中发现的问题

**Why:** 了解当前迭代状态有助于判断哪些工作可以并行、哪些有依赖关系。
**How to apply:** 选择任务时优先处理 P0 Bug，然后 P1 违规。
