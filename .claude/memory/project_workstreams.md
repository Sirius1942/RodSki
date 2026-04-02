---
name: project_workstreams
description: RodSki 项目当前工作主线和迭代状态
type: project
---

**项目定位更新（2026-04-02）**：

> RodSki 是文档与工具系统，核心是**辅助 AI Agent 工作**。
> 不是传统测试框架，而是 Agent 的执行工具 + 活文档生成器。

**当前迭代状态**：

| 迭代 | 主题 | 状态 |
|------|------|------|
| iteration-03 | Bug 修复与依赖完善 | 已完成 |
| iteration-04 | Agent 集成基础设施（JSON 输出/Python API） | 已完成 |
| iteration-05 | 活文档增强（XML 元数据） | 待开始 |
| iteration-06 | 动态执行能力（运行时步骤插入） | 待开始 |
| iteration-07 | 文档体系重构 | 待开始 |

**当前分支**：
- `main` — 主干
- `acceptance-validation` — 验收分支

**核心待修 Bug（P0）**：
- `driver.type` 方法不存在（PlaywrightDriver 只有 `type_locator`）
- pytest 依赖违反自检约束 §9

**Why:** 迭代路线图围绕"让 Agent 更好地工作"这一主线。
**How to apply:** 选择任务时优先修复阻塞 Agent 集成的 Bug。
