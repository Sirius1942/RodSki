# RodSki 文档索引

本目录 **`rodski/docs/`** 为 RodSki **正式文档根目录**，按用途分为三类，便于需求评审、架构评审与交付验收。

---

## ⚠️ 项目管理体系已迁移

> RodSki 的**项目管理体系**（需求、设计约束、迭代管理、Agent 开发规范）已迁移到项目根目录的 **`../phoenixbear/`** 目录。
>
> - ⭐ **核心设计约束**: `../phoenixbear/design/CORE_DESIGN_CONSTRAINTS.md`
> - ⭐ **用例编写指南**: `../phoenixbear/design/TEST_CASE_WRITING_GUIDE.md`
> - 项目规范: `../phoenixbear/conventions/`
> - 迭代管理: `../phoenixbear/iterations/`
> - Agent 开发: `../phoenixbear/agent/`
>
> **每个迭代的实现绝对不能违反** `CORE_DESIGN_CONSTRAINTS.md` 和 `TEST_CASE_WRITING_GUIDE.md` 中的约束条款。

---

## 需求文档 `requirements/`

| 文档 | 说明 |
|------|------|
| [RODSKI_REQUIREMENTS.md](requirements/RODSKI_REQUIREMENTS.md) | 需求基线与验收原则 |
| [RODSKI_REQUIREMENTS_HISTORY_2026-03-20.md](requirements/RODSKI_REQUIREMENTS_HISTORY_2026-03-20.md) | 需求与文档梳理纪要（历史） |
| [README.md](requirements/README.md) | 本目录说明 |

---

## 设计文档 `design/`

| 文档 | 说明 |
|------|------|
| [ARCHITECTURE.md](design/ARCHITECTURE.md) | 总体架构与执行流程 |
| [核心设计约束.md](design/核心设计约束.md) | 框架设计约束（权威） |
| [AGENT_AUTOMATION_DESIGN.md](design/AGENT_AUTOMATION_DESIGN.md) | Agent 自动化设计 |
| [CI_CD_GUIDE.md](design/CI_CD_GUIDE.md) | CI/CD 与流水线集成 |
| [json_support_design.md](design/json_support_design.md) | API JSON 数据支持设计 |
| **[RPA_ROADMAP_SUMMARY.md](../../doc/design/RPA_ROADMAP_SUMMARY.md)** | **RPA 能力提升路线图总结（新）** |
| [RPA_GAP_ANALYSIS.md](../../doc/design/RPA_GAP_ANALYSIS.md) | RPA 与主流系统差距分析（新） |
| [PC_AUTOMATION_ENHANCEMENT.md](../../doc/design/PC_AUTOMATION_ENHANCEMENT.md) | Windows/macOS 桌面自动化增强方案（新） |
| [LLM_VISION_LOCATOR_DESIGN.md](../../doc/design/LLM_VISION_LOCATOR_DESIGN.md) | LLM 视觉定位接口设计（新） |
| [人工提出问题的笔记.md](design/人工提出问题的笔记.md) | 设计讨论与问题记录 |
| [README.md](design/README.md) | 本目录说明 |

---

## 用户指南 `user-guides/`

| 文档 | 说明 |
|------|------|
| [QUICKSTART.md](user-guides/QUICKSTART.md) | 5 分钟快速入门 |
| [GUI_USAGE.md](user-guides/GUI_USAGE.md) | GUI 使用说明 |
| [CLI_DESIGN.md](user-guides/CLI_DESIGN.md) | CLI 子命令与交互 |
| [TEST_CASE_WRITING_GUIDE.md](user-guides/TEST_CASE_WRITING_GUIDE.md) | 用例编写规范 |
| [TEST_CASE_BEST_PRACTICES.md](user-guides/TEST_CASE_BEST_PRACTICES.md) | 用例最佳实践 |
| [REPORT_GUIDE.md](user-guides/REPORT_GUIDE.md) | 报告与趋势、PDF |
| [API_TESTING_GUIDE.md](user-guides/API_TESTING_GUIDE.md) | REST API 测试 |
| [PARALLEL_EXECUTION.md](user-guides/PARALLEL_EXECUTION.md) | 并行执行 |
| [PERFORMANCE.md](user-guides/PERFORMANCE.md) | 性能相关说明 |
| [MOBILE_GUIDE.md](user-guides/MOBILE_GUIDE.md) | 移动端测试 |
| [TROUBLESHOOTING.md](user-guides/TROUBLESHOOTING.md) | 常见问题 |
| [README.md](user-guides/README.md) | 本目录说明 |

---

## 路径约定

- **需求与设计约束文档**: 放入 `../phoenixbear/requirements/` 和 `../phoenixbear/design/`
- **用户指南文档**: 放入本目录 `user-guides/`
- **新增文档**请放入本目录下对应子目录：`requirements/`、`design/`、`user-guides/`。
- 仓库根目录 **`doc/`**（若存在）仅保留兼容跳转，**勿**再向其中新增正式文档。
