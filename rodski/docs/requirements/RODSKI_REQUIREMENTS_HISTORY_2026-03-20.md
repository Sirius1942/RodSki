# RodSki 需求与用户文档梳理（2026-03-20）

> **路径说明**：正式文档位于 **`rodski/docs/`** 下 **`requirements/`**、**`design/`**、**`user-guides/`**，见 [文档首页](../README.md)。清单中的路径以本文件所在目录为基准（如 `../user-guides/...`）。

## 1. 梳理范围

本次梳理覆盖 `rodski/` 目录下以下内容：

- 需求与能力说明（README、功能指南、设计文档）
- 用户使用文档（快速开始、GUI/CLI、测试用例编写、报告）
- 当前架构设计（模块分层、执行链路、扩展点）
- 历史记录（文档内版本信息 + Git 可见提交）

---

## 2. 文档资产清单（按用途）

### 2.1 用户入门与使用

- `rodski/README.md`：项目总览、安装、GUI/CLI 启动方式
- `../user-guides/QUICKSTART.md`：5 分钟上手
- `GUI_USAGE.md`（历史引用；若不存在则见 GUI 相关代码与 QUICKSTART）
- `../user-guides/TEST_CASE_WRITING_GUIDE.md`：用例编写规范
- `../user-guides/REPORT_GUIDE.md`：报告生成、趋势分析、PDF 导出

### 2.2 设计与实现说明

- `../design/ARCHITECTURE.md`：总体架构、执行流程、关键类职责
- `../user-guides/CLI_DESIGN.md`：CLI 子命令与交互设计
- `../design/json_support_design.md`：API JSON 数据支持设计
- `../user-guides/PARALLEL_EXECUTION.md`：并发执行能力说明
- `../user-guides/API_TESTING_GUIDE.md`：REST API 关键字与样例

---

## 3. 当前需求基线（从现有文档归纳）

### 3.1 核心业务需求

1. **关键字驱动测试执行**
   - 支持 UI、API、数据库等关键字执行
   - 支持四段式流程：预处理 -> 测试步骤 -> 预期结果 -> 后处理
2. **数据与模型分离**
   - Excel 用例主表（Case）
   - 数据表（按 Sheet）
   - `model.xml` 元素定位
   - `GlobalValue` 全局变量
3. **多端驱动统一接入**
   - Web（Playwright）
   - Mobile（Appium / Android / iOS）
   - Desktop（Pywinauto）
4. **结果沉淀**
   - Excel 回填（TestResult）
   - 日志记录
   - HTML/JSON/PDF 报告
   - 历史趋势记录（`logs/history/`）

### 3.2 工程与体验需求

1. CLI 子命令化（`run/model/config/log/report/profile`）
2. GUI 可视化执行与实时日志
3. Dry-run、verbose、重试、无头等运行选项
4. 失败自动截图
5. 支持并发执行以提升吞吐

---

## 4. 当前设计快照（架构层面）

### 4.1 分层结构

- **入口层**：`cli_main.py`、`ski_gui.py`、`ski_run.py`
- **核心层**：`core/`（`ski_executor`、`keyword_engine`、`task_executor`、`parallel_executor`）
- **驱动层**：`drivers/`（统一基类 + 多端实现）
- **解析层**：`case/model/data/global` 解析器 + `data_resolver`
- **输出层**：`result_writer`、`logger`、`profiler`

### 4.2 关键执行链路

1. 解析 Excel/Model/Global/Data
2. 构造并初始化 Driver + KeywordEngine
3. 执行用例步骤（含重试）
4. 失败路径触发截图与错误记录
5. 回填执行结果并生成报告

### 4.3 已明确的扩展机制

- 新驱动：继承 `BaseDriver` 并在 CLI 执行路径接入
- 新关键字：在 `KeywordEngine` 注册并实现 `_kw_xxx`
- API JSON 能力：支持内嵌 JSON、`@file:` 引用、变量替换

---

## 5. 用户文档现状评估

### 5.1 优点

- 入门路径完整（README -> QUICKSTART -> 细分指南）
- 用例编写规范较细，约束明确（尤其是 Case 双表头与元素名一致性）
- 报告文档包含运维级内容（趋势、历史记录、CI/CD 场景）

### 5.2 当前不一致点（建议后续统一）

1. **命令前缀混用**
   - 文档中同时出现 `ski` 与 `rodski`
2. **Python 版本口径不一致**
   - 有 `3.11+`、`3.8+`、`3.11+` 等不同表述
3. **关键字命名口径不完全一致**
   - 如 `verify` 与 `assert` 在不同文档中并存
4. **部分文档偏“设计预期”，需与代码行为持续对齐**
   - 尤其是 CLI 选项、报告能力、数据库关键字

---

## 6. 历史记录梳理

### 6.1 文档内可见里程碑

- **2026-03-15**：`json_support_design.md` 发布，定义 API JSON 支持方案（v1.0）
- **2026-03-19**：`ARCHITECTURE.md` 生成（含架构图与职责划分）
- **2026-03-20**：
  - `TEST_CASE_WRITING_GUIDE.md` 发布（v1.0）
  - `REPORT_GUIDE.md` 标记为 v1.2.3，新增趋势与 PDF 导出说明

### 6.2 Git 可见提交主线（`rodski/`）

- `8a5168e`（2026-03-20）  
  `refactor: rename ski_python to rodski, clean up for open source`
- `5ee9e59`（2026-03-20）  
  `fix: convert rodski from submodule to regular directory`
- `287872a`（2026-03-20）  
  `fix: 修复8个单元测试以匹配当前实现行为`

结论：当前仓库历史显示，`rodski` 在 2026-03-20 完成了命名与仓库结构层面的关键迁移，并进行了一轮测试行为对齐修复。

---

## 7. 建议的后续文档治理动作

1. 统一 CLI 命令前缀（建议全部使用 `rodski`）
2. 统一最低 Python 版本声明（README/CLI_DESIGN/安装说明同步）
3. 输出一份单独 `CHANGELOG.md`，避免历史信息散落在各文档
4. 为“需求基线”建立单一事实源（已实现 `RODSKI_REQUIREMENTS.md`）
5. 每次发布时执行“文档-代码一致性检查清单”

---

## 8. 本次梳理结论

`rodski` 已具备从“需求说明 -> 使用指南 -> 架构设计 -> 历史演进”的完整文档雏形；当前主要问题不在“有没有文档”，而在“多文档口径一致性”和“版本化治理”。本文件可作为后续整理与发布对外文档的统一入口。
