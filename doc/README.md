# RodSki 文档索引

本目录为 RodSki **正式文档**的根目录，按用途分为三类，便于需求评审、架构评审与交付验收。

---

## 目录说明

| 英文目录 | 中文含义 | 用途 |
|----------|----------|------|
| **requirements/** | 需求文档 | 记录 RodSki 的**原始需求与目的**、**要解决的关键问题**、**如何验收**；是需求基线与验收依据的上游。 |
| **design/** | 设计文档 | 记录**实现策略**、**架构**与**关键设计约束**；与代码实现一致，变更需评审。 |
| **user-guides/** | 用户指南 | 面向**最终用户**的操作与编写手册；**验收测试**应以本目录中的规范与步骤为准（辅以用例与结果约定）。 |

---

## 快速导航

### 需求（requirements）

| 文档 | 说明 |
|------|------|
| [RODSKI_REQUIREMENTS.md](requirements/RODSKI_REQUIREMENTS.md) | **需求总览**：目的、关键问题、验收原则（单一事实源入口） |
| [RODSKI_REQUIREMENTS_HISTORY_2026-03-20.md](requirements/RODSKI_REQUIREMENTS_HISTORY_2026-03-20.md) | 历史需求与文档资产梳理记录 |

### 设计（design）

| 文档 | 说明 |
|------|------|
| [核心设计约束.md](design/核心设计约束.md) | 框架权威设计约束（关键字、数据、XML、动态步骤等） |
| [ARCHITECTURE.md](design/ARCHITECTURE.md) | 模块与执行链路 |
| [AGENT_AUTOMATION_DESIGN.md](design/AGENT_AUTOMATION_DESIGN.md) | 通用 AI Agent 与 RodSki 集成设计 |
| [json_support_design.md](design/json_support_design.md) | JSON 数据支持设计 |
| [CI_CD_GUIDE.md](design/CI_CD_GUIDE.md) | CI/CD 与流水线集成说明 |
| [人工提出问题的笔记.md](design/人工提出问题的笔记.md) | 设计讨论与问题记录 |

### 用户指南（user-guides）

| 文档 | 说明 |
|------|------|
| [QUICKSTART.md](user-guides/QUICKSTART.md) | 快速入门 |
| [GUI_USAGE.md](user-guides/GUI_USAGE.md) | GUI 使用说明 |
| [TEST_CASE_WRITING_GUIDE.md](user-guides/TEST_CASE_WRITING_GUIDE.md) | 用例编写指南（**验收测试依据之一**） |
| [TEST_CASE_BEST_PRACTICES.md](user-guides/TEST_CASE_BEST_PRACTICES.md) | 用例最佳实践 |
| [CLI_DESIGN.md](user-guides/CLI_DESIGN.md) | CLI 使用说明 |
| [REPORT_GUIDE.md](user-guides/REPORT_GUIDE.md) | 报告与趋势 |
| [API_TESTING_GUIDE.md](user-guides/API_TESTING_GUIDE.md) | 接口测试 |
| [MOBILE_GUIDE.md](user-guides/MOBILE_GUIDE.md) | 移动端 |
| [PARALLEL_EXECUTION.md](user-guides/PARALLEL_EXECUTION.md) | 并行执行 |
| [PERFORMANCE.md](user-guides/PERFORMANCE.md) | 性能 |
| [TROUBLESHOOTING.md](user-guides/TROUBLESHOOTING.md) | 故障排查 |

---

## 与 `rodski/docs/` 的关系

历史路径 `rodski/docs/` 仅保留**跳转说明**（见该目录下 `README.md`），**请勿在新文档中继续写死旧路径**。新文档请放在本 `doc/` 目录对应分类下。

---

## 文档版本

各 Markdown 文件头部保留各自版本与日期；本索引以仓库内最新提交为准。
