---
name: project_overview
description: RodSki 项目定位更新：文档与工具系统，辅助 AI Agent 工作
type: project
---

**RodSki 定位**：文档与工具系统，核心是**辅助 AI Agent 工作**。不是传统测试框架，而是 Agent 的执行工具 + 活文档生成器。

**四个核心能力**：
- **探索** — Vision/OmniParser 视觉感知界面元素
- **记录** — XML 活文档（Case + Model + Data）替代静态文档
- **执行** — 关键字驱动（type/send/verify/run）执行操作
- **观测** — 结构化结果（JSON）、日志、截图供 Agent 决策

**代码位置**：
- 框架主体：`rodski/`
- 测试用例示例：`rod_ski_format/`
- 项目管理：`phoenixbear/`
- Web 管理界面：`src/`（Flask app）、`static/`、`templates/`、`config.yaml`

**权威项目文档**：
- `phoenixbear/design/CORE_DESIGN_CONSTRAINTS.md` — ⭐ 核心设计约束，不可违反
- `phoenixbear/design/TEST_CASE_WRITING_GUIDE.md` — ⭐ 用例编写指南，不可违反
- `phoenixbear/conventions/PROJECT_CONSTRAINTS.md` — 项目约束与规范

**启动 Web 管理界面**：
```bash
cd /Users/sirius05/Documents/project/RodSki
pip install flask pyyaml
python src/app.py
# 访问 http://localhost:5002
```
