---
name: project_overview
description: RodSki 项目概述、架构和当前版本状态
type: project
---

RodSki 是一个**文档与工具系统**，核心定位是**辅助 AI Agent 工作**。

它不是传统意义的测试框架，而是一套让 AI Agent 能够：
- **探索**（Vision/OmniParser 视觉感知）
- **记录**（XML 活文档：Case + Model + Data）
- **执行**（关键字驱动：type/send/verify/run）
- **观测**（结构化结果、日志、截图）

**RodSki = Agent 的执行工具 + 活文档生成器**

**核心架构**：
- **Keyword 层**：14 个关键字（type/send/verify 等），驱动 AI 操作行为
- **Locator 层**：视觉定位支持（OmniParser + LLM），让 Agent 能感知界面
- **文档层**：XML 格式的 Case/Model/Data，活文档替代静态文档
- **Agent 层**：Python API + JSON 输出，Agent 可编程调用

**平台支持**：Web / Mobile / Desktop / API / DB

**权威项目文档**（`phoenixbear/`）：
- `phoenixbear/design/CORE_DESIGN_CONSTRAINTS.md` — ⭐ 核心设计约束，不可违反
- `phoenixbear/design/TEST_CASE_WRITING_GUIDE.md` — ⭐ 用例编写指南，不可违反
- `phoenixbear/conventions/PROJECT_CONSTRAINTS.md` — 项目约束与规范

**代码位置**：
- 框架主体：`rodski/`
- 测试用例示例：`rod_ski_format/`
- 项目管理：`phoenixbear/`

**Why:** 理解 RodSki 是 Agent 工具而非纯测试框架，有助于在设计时始终以"Agent 如何使用"为出发点。
**How to apply:** 任何功能设计时，问自己：Agent 能方便地调用吗？结果对 Agent 有用吗？
