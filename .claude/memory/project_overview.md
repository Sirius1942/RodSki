---
name: project_overview
description: RodSki 项目概述、架构和当前版本状态
type: project
---

RodSki 是一个关键字驱动的自动化测试框架，当前版本 v2.1.0，支持 Web UI + 接口自动化测试。

**核心架构**：
- 用例格式：XML（Case / Data / Model / GlobalValue），已从 Excel 迁移
- 关键字体系：`type`（UI批量操作）/ `send`（接口）/ `verify`（通用验证）等 15 个关键字
- 平台支持：Web / Mobile / Desktop
- 驱动层：Playwright、Appium、Pywinauto、Vision

**权威项目文档**（`phoenixbear/`）：
- `phoenixbear/design/CORE_DESIGN_CONSTRAINTS.md` — ⭐ 核心设计约束，不可违反
- `phoenixbear/design/TEST_CASE_WRITING_GUIDE.md` — ⭐ 用例编写指南，不可违反
- `phoenixbear/conventions/PROJECT_CONSTRAINTS.md` — 项目约束与规范

**代码位置**：
- 框架主体：`rodski/`
- 测试用例：`rod_ski_format/`（第三方测试用例）
- 项目管理：`phoenixbear/`

**Why:** 了解框架定位有助于区分执行层（RodSki）与 Agent 层的职责边界。
**How to apply:** 做任何功能设计时，RodSki 只做执行，不做探索/感知决策。
