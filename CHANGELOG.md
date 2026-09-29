# Changelog


## [11.5.1] - 2026-09-29

文档修正版本：修复 CORE_DESIGN_CONSTRAINTS.md 中的约束矛盾、与代码实现不一致、结构问题，补齐 6 个 demo README。

### Fixed

- 附录 A.2「自检不使用 pytest」与 §9.1/§9.2 矛盾，已删除该条（单元测试允许 pytest）
- §7.0/§7.1 误将已废弃的 data.xsd 列为运行时校验对象，已删除（data.xml 自 v6.0.0 废弃）
- §7.3 数据表示例字段数不一致（第 1 行 4 字段、第 2 行 3 字段），已统一为 4 字段
- 附录 A.2 plan 省略 file 规则写成「有歧义时报 SKI207」，与决策 C2「多文件模块必报」不符，已修正
- §7.7 缺少边界说明「ID 不存在时记为 stale 引用」，已补充
- Agent 契约摘要：关键字集合漏 close/get_text（实际 17 个），已补齐
- Agent 契约摘要：输出契约写成 `execution_summary.json` 和 `result/execution.log`，已改为实际路径 `result/{run}/result.xml` 等
- §1.4 已注册内置函数只列网络拦截 3 个，漏 start_js_coverage/stop_js_coverage 等，已补齐（实际 7 个）
- §15.1/§15.3/§17.1 示例命令使用 `from rodski_cli import main` 导致 ModuleNotFoundError，已改为 `rodski run ...`
- §14.3 cassmall/thdh/ 示例在仓库中不存在，已删除
- 补写 6 个缺失的 demo README：browser_plugin、browser_plugin_baidu、demo_v11_enhancement、demo_v7_features、qq_music、vscode_plugin

### Changed

- 版本更新记录按时间倒序排列（v11.5.0 → v11.4.0 → v11.3.0）
- 章节编号：2.5/2.6/2.7 改为三级标题 `###`；§22 统一运行时上下文（原「§10」重复）
- §6.3 固定文件夹职责表补 `business/` 行
- §14.2 补全 24 个 demo 项目清单
- 页眉日期统一为 2026-09-29


## [11.5.0] - 2026-09-29

用例目录多级嵌套，面向大型产品的用例组织。设计：`.pb/specs/v11.5.0-nested-case-directory-design.md`；迭代：`.pb/iterations/iteration-63/`。

### Added

- `case/` 支持任意多级子目录，执行、解析、plan、dry-run、queue、explain 统一递归发现用例文件（新增 `core/case_discovery.py`）；按相对路径逐段排序，忽略以 `.` 开头的目录/文件与非 `.xml` 文件，不跟随目录符号链接。
- 用例身份 = 用例文件（相对 `case/` 的 POSIX 路径）+ 用例 ID；用例字典新增 `case_file`、`case_uid`。
- plan：`<case file="..." id="..."/>` 精确选择；新增可选 `<case_dir path="..."/>` 按目录递归选入；`rodski plan add-case <plan> <file> <id>`、`add-dir`、`migrate`（为缺 `file` 的引用自动补全，歧义项列出待人工处理）。
- CLI：`rodski run` 支持执行 `case/` 下任意子目录；新增 `--case-id`（须与单个用例文件路径一起使用，与 `@plan_id` 固定互斥）；在 `case/` 嵌套子目录中执行 `@plan_id` 可定位模块根；`rodski roam --case-file/--case-id`。
- 结果目录镜像 case 目录：用例级截图（含场景子目录、失败截图）与录像写入 `result/{run}/case/<用例文件去 .xml>/screenshots|recordings/`，跨文件同名用例互不覆盖；汇总文件仍在运行目录根。`result.xsd` 新增 `case_file`，HTML 报告新增按目录视图。
- 维护工具：`rodski case lint`、`rodski model lint`、`rodski data dump`（只读，可作 git textconv）、`rodski data validate --orphans`、`rodski data add-field`。
- 错误码：`SKI205` 同一用例文件内 ID 重复、`SKI206` `case/` 子目录使用保留名、`SKI207` 多用例文件模块中 plan 省略 `file`、`SKI208` `--case-id` 用法错误；均在启动驱动前抛出。
- `rodski-demo` 新增验收模块 `demo_nested_case`（3 层嵌套、跨文件同名 ID、18 项自动化验收 `run_acceptance.py`）、`demo_nested_case_single`、`demo_nested_case_dup_id`。

### Changed

- 用例 ID 唯一性范围改为「所属用例文件内」（CORE §7.2）。
- plan 的 `<case>` 必须写 `file`；唯一兼容例外：模块 `case/` 下（递归）只有一个用例文件。引用在任何文件中都不存在的 ID 记为 stale 引用。
- `ModelParser` 检测同名 model 与同一 model 内同名 element 并报错（此前后者静默覆盖前者）。
- 迁移 `rodski-demo` 存量 plan（demo_full、demo_load、mobile_app 补 `file`；demo_perception 的 plan 改为符合 `plan.xsd` 的 `<test_plan>` 格式）。
- 文档：CORE_DESIGN_CONSTRAINTS、TEST_CASE_WRITING_GUIDE（目录与命名规范、plan、CLI、结果目录）、AGENT_INTEGRATION；`rodski-skills` 相关参考同步更新；web 用例解析支持嵌套目录。


## [11.4.1] - 2026-09-28

### Added

- VS Code 扩展新增业务模型流程图面板（`rodski-vscode`）。
- 用例编写指南新增第 17 章「业务模型」：`business/*.xml` 结构、静态校验规则、条件表达式白名单、`B` / `B_verify` 数据表约定、`<business_call>` 用法、结果与 `rodski business` CLI。
- `rodski-skills`：case-writer 新增 `references/business-model.md`；test-guide 新增 `17_business_model.md` 切片；rodski skill 补充 `business` 子命令。

### Changed

- 核心设计约束 §2.7 补充目录与表名约定、不新增关键字、确定性分支、校验先于副作用四条；模块目录规范加入可选 `business/`。
- `rodski-skills` 去除业务相关内容：`$HOME/TestCase` 固定路径、`/opt/homebrew/bin/rodski` 固定入口、具体业务流程示例、内部 Registry 地址和 improve 笔记索引；case-writer 脚本默认改为当前目录 / `RODSKI_BIN` / `PATH`。

### Fixed

- `demo_load/README.md` 中无法执行的 `@plan_id=` 命令改为 `rodski run @api_load_basic`。

### Validation

- 单元测试 2504 passed, 3 xfailed。
- `demo_full` 13 个用例文件 56/56 PASS；`demo_business_model` 3 条正式 Case PASS + 1 条预期失败；`demo_hooks`、`demo_runtime_control`、`demo_pause_takeover`、`demo_roaming_test`、`demo_v11_enhancement`（4/4）、`demo_v7_features`、`demo_load`（466 请求 0 错误）全部通过。

## [11.4.0] - 2026-09-27

### Added

- 新增业务模型（Business Model）场景法能力：节点、条件边、基本流、备选流和异常流。
- 支持 Case 通过 `business_call` 显式引用业务模型、选择业务流并绑定 SQLite Data/Verify 数据表。
- 新增业务模型 XML Schema、静态图校验、JSON/Mermaid 图、coverage 汇总和 debug CLI。
- 新增 `rodski-demo/DEMO/demo_business_model` 验收 Demo，覆盖成功、凭据错误、账号锁定及路径错配负向场景。

### Validation

- 业务模型 Demo：3 条正式 Case 通过，1 条路径错配样例按预期失败；节点/边/flow 覆盖 6/6、5/5、3/3。
- 专项兼容测试：163 passed。
- 可运行的无外部依赖 Demo 已完成验收，`demo_full` 默认回归 19/19 PASS。

All notable changes to RodSki will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [10.0.0] - 2026-08-21

### 🚀 Major Changes

**探索测试架构简化（三层 → 两层）**

- 废弃 `rodski-agent/explore` 中间层
- 新架构：Claude Code + Skill → `rodski explore-step` CLI
- 决策层上移到 AI Agent（Claude Code/Codex/AutoGPT）

### ✨ Added

**核心功能**
- `rodski explore-step` - 单步探索命令 CLI
- 会话管理模块（`rodski/core/explore/session.py`）
  - `ExploreSession`: 会话状态数据结构
  - `ExploreSessionStore`: 会话持久化（原子写入）
  - `BudgetGuard`: 预算控制（步数/时长/token/成本）+ 去重
- `ExploreExecutor` 增强：浏览器错误采集、证据增强

**Skill 文档**
- `rodski-skill--explore`: 完整的探索测试 skill（515 行）
  - 5 个阶段执行纪律
  - 数据唯一性处理指南
  - 框架无关设计（支持任何 Markdown skill Agent）
- 参考文档：charter-design.md、finding-classification.md、budget-tuning.md

**核心特性**
- ✅ 基于已通过用例建立基线
- ✅ 探索合理业务边界线下的异常
- ✅ 数据唯一性处理（避免重复主键误判）
- ✅ 框架无关设计
- ✅ 预算控制和去重机制

### 🔧 Changed

- CLI 注册：新增 `explore-step` 子命令
- 版本号：9.2.3 → 10.0.0 (MAJOR)

### 🗑️ Deprecated

- `rodski-agent/explore` - 标记为废弃
  - 原因：架构简化，决策层上移到 Claude Code
  - 短期保留代码，长期（v11.x）可能移除
  - 替代方案：使用 `rodski-skill--explore` + `rodski explore-step` CLI

### 📝 Documentation

- PRD: `.pb/requirements/v10-explore-testing-prd.md`
- 迭代总结: `.pb/iterations/iteration-v10.0.0/SUMMARY.md`
- Skill 文档: `.claude/skills/rodski-skill--explore/SKILL.md`

### 🧪 Tests

- 单元测试：16/16 passed（会话管理模块完整覆盖）
- 覆盖率：> 80%

### 🐛 Fixed

- CLI 导出问题：`rodski_cli/__init__.py` 添加 `explore` 导出

### 💔 Breaking Changes

**不兼容 v9 的变化**
- 废弃 `rodski-agent/explore` Python API
- 探索测试需要使用新的 `rodski explore-step` CLI
- 需要 Python >= 3.8

### 📦 Migration Guide

**从 v9 迁移到 v10**

```python
# v9 (已废弃)
from rodski_agent.explore.executor import ExploreAgent
agent = ExploreAgent(execute_command_fn=...)
session = agent.explore_loop()

# v10 (推荐)
# 方式 1: 在 Claude Code 中使用 /explore skill
# 方式 2: 直接调用 CLI
import subprocess
result = subprocess.run([
    "rodski", "explore-step",
    "--module", "path/to/module",
    "--session", "session_id",
    "--action", "navigate",
    "--data", "http://..."
], capture_output=True)
```

---

## [9.2.3] - 2026-08-13

### Fixed
- 探索测试集成问题修复
- 证据采集增强

---

## [9.0.0] - 2026-08-10

### Added
- 探索式测试完整实现（三层架构）
- ExploreExecutor: execute_command() API

---

## [8.4.0] - 2026-08-01

### Added
- roam 漫游测试（基于已通过用例的数据漫游）

---

[10.0.0]: https://github.com/your-org/rodski/compare/v9.2.3...v10.0.0
[9.2.3]: https://github.com/your-org/rodski/compare/v9.0.0...v9.2.3
[9.0.0]: https://github.com/your-org/rodski/compare/v8.4.0...v9.0.0
[8.4.0]: https://github.com/your-org/rodski/releases/tag/v8.4.0
