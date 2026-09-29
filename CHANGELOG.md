# Changelog


## [11.6.0] - 2026-09-29

AI 编写效率、断言可靠性与执行性能。不新增关键字（仍为 17 个），`case.xsd` 不变；新能力只通过 `verify` 操作符、`model.xsd`、数据表字段值、`run` 内置函数、`globalvalue` 配置和 CLI 参数提供。设计：`.pb/specs/v11.6.0-ai-authoring-and-performance-design.md`（v0.2）；迭代：`.pb/iterations/iteration-64/`。

### Added

- `verify` 新增元素级操作符 `$count` / `$count_gte` / `$count_lte` / `$exists` / `$visible`（JSON 写法，如 `{"$count": 10}`）。定位器匹配 0 个元素时按实际数量 0 判定，不会跳过；期望值格式错误报契约错误并给出示例，不重试。
- UI 模型 `verify` 默认自动重试：每 200ms 轮询，直到全部字段匹配或超过自动等待 `DefaultValue.AutoWait`（毫秒，默认 5000 即 5 秒，`0` 关闭重试）。超时后按最后一次读到的值报错，并注明"已自动重试"。接口 / DB 模型的 `verify` 仍只比对一次；使用视觉定位器的字段不重试。
- `model.xsd`：新增定位类型 `page`，取值 `url` / `title` / `path` / `dialog`；`<location>` 新增可选属性 `frame`（iframe 的 CSS 选择器，多层用 `>>` 串联）。`page` 定位器不能带 `frame`。
- 原生弹窗：新增 `DefaultValue.DialogPolicy = accept | dismiss | fail`，默认 `fail`，即出现未预期弹窗时步骤立即失败并报告弹窗文本（`UnexpectedDialogError`，SKI325）。`page=dialog` 元素在 `type` 数据中填 `accept` / `dismiss` / `accept:文本`，为下一次弹窗注册一次性处理器；在 `verify` 中读取最近一次弹窗的文本。
- iframe：`type` / `verify` / `get_text` 等可以操作 `location@frame` 指定的 iframe 内元素。
- `evaluate` 的 `data` 支持 `file:<模块内相对路径>`，从模块目录读取脚本；越出模块目录或文件不存在时报错。
- `run` 内置函数 `save_auth_state(name)` / `use_auth_state(name)`：登录态只保存在本次 run 的内存中，不写盘。`use_auth_state` 必须在当前用例 `navigate` 之前调用，否则报错；名称不存在时报错并说明需先执行保存该登录态的用例。
- 会话模式 `DefaultValue.SessionMode` / `--session-mode`：`isolated`（默认，现状）、`shared_browser`（整个 run 复用一个浏览器进程，每个用例新建 BrowserContext，用例的 `close` 只关闭 context）、`shared_session`（用例间共用会话，run 结束时统一关闭）。
- 简洁记录模式 `DefaultValue.EvidenceMode` / `--evidence full|concise`：默认 `full` 不变；`concise` 只在失败时截图，录像不受影响。`result.xml` 的 `<summary>` 新增可选属性 `evidence_mode` / `session_mode`（`result.xsd` 同步），HTML 报告页眉显示这两个模式。
- `rodski run --workers N`：以用例文件为单位分给 N 个 worker 进程并行执行，同一文件内的用例在同一 worker 中顺序执行。结果合并到同一运行目录和同一个 `result.xml`；worker 异常退出时，为它负责的用例补 FAIL 结果。
- `--report junit`：在运行目录生成 `junit.xml`（每个用例文件一个 `<testsuite>`，`classname=case_file`，`name=case_id`，失败信息附截图相对路径）；可写成 `--report html,junit`。`--workers` / `--session-mode` / `--evidence` / `--report` 不是执行范围 selector，可与 `@plan_id` 同时使用。
- `rodski data set` / `data add-row` / `data delete-row`：直接修改 `data.sqlite` 中的数据行。新增行必须提供完整字段集合。
- `rodski case lint` 新增 6 条 AI 编写契约规则：`evaluate` 断言模式（WARNING）、数字字面量 `wait`（WARNING，附估算耗时）、`WaitTime > 0`（WARNING）、strict 模式下 `_verify` 行 BLANK 占比 > 50%（INFO）、`sql` 为 BLANK 且没有有效 `query`（ERROR）、`evaluate` 中的 `window.confirm/alert/prompt` 垫片（WARNING）。
- `rodski capabilities` 输出新增 `pitfalls` 字段（`rodski_cli/pitfalls.py`）；`rodski-skills` 的 case-writer / test-guide 新增"契约速查"一节，与 `pitfalls` 同源。
- 验收模块 `rodski-demo/DEMO/demo_authoring_v116/`（`run_acceptance.py` 共 19 项，其中 V19–V21 为动态等待专项）、夹具 `demo_authoring_v116_pitfalls/` 和 `demo_authoring_v116_no_retry/`（`AutoWait=0`）。

### Changed

- 所有等待类配置统一为毫秒：`DefaultValue.WaitTime`、`<cases step_wait>` 与新增的自动等待 `DefaultValue.AutoWait`。
- GUIDE 新增 §6.0「什么时候用全局变量」（该用 / 不该用 / 换环境只改 globalvalue 的示例），case-writer skill 同步补充对应规则。

- **等待单位统一为毫秒**：`DefaultValue.WaitTime` 与 `<cases step_wait>` 都按毫秒解释。过渡期内 `WaitTime` 在 0 到 30（含 30，不含 0）之间时仍按秒解释，并在每次 run 打印一次弃用告警；大于 30 按毫秒解释。
- `rodski init` 模板写 `WaitTime=0` 并注明单位为毫秒；GUIDE / CORE / skills 的示例同步改为毫秒。
- rodski-demo 存量 `globalvalue.xml` 中的 `WaitTime` 已迁移为毫秒，迁移后每个模块的实际每步等待不变：`demo_load` 1→1000、`mobile_app` 2→2000；`demo_full` / `demo_v7_features` / `rodski_website` / 根 `rodski-demo/data` 保持 500 / 500 / 300 / 500（大于 30，按毫秒解释）；`qq_music` 删除 `Mobile` 组中从未生效的 `WaitTime`。兼容性夹具 `demo_authoring_v116_pitfalls` 保留 `WaitTime=1`。
- `DefaultValue` 中 `WaitTime` / `AutoWait` 不是非负数，或 `DialogPolicy` / `SessionMode` / `EvidenceMode` 取值非法时，在启动驱动前报错，报错列出合法取值和修复写法，不再静默回落默认值。此前 `WaitTime` 写成非数字会被当作 0。
- `verify` 不匹配时，错误信息附上每个字段的操作符失败原因。
- 文档：CORE_DESIGN_CONSTRAINTS / TEST_CASE_WRITING_GUIDE / AGENT_INTEGRATION / SKILL_REFERENCE 覆盖以上能力（GUIDE §5.7 断言操作符与自动重试、§6.4 执行策略配置、§8.7–8.8、§9.9 CI 接入示例）。SKILL_REFERENCE 中与 CORE 矛盾的 `action="click"`、`switch_window` / `switch_frame` 写法已改正。

### Fixed

- 契约类报错附带修复提示（C4）：`action` 写成 `click` / `hover` / `select` 等 UI 原子动作或其他非关键字时，XSD 校验报错和 `UnknownKeywordError` 都会说明这些是 `type` 数据表的字段值，并给出最小示例。
- XML 非良构（例如属性中写了裸 `&&` / `<`）时报 `XmlSyntaxError`（SKI200），附上出错行，并提示改写为 `&amp;&amp;` / `&lt;` 或改用 `evaluate` 的 `file:` 引用。
- 两次 `rodski run` 在同一秒内先后启动时，会落进同一个 `result/rodski_<时间戳>/` 目录，后一次覆盖前一次的 `result.xml` / `execution.log`。现在目录已存在时，新目录名追加 `_2`、`_3` 等后缀；不冲突时目录名不变。


## [11.5.2] - 2026-09-29

修复 AI 写用例对比实验暴露的 DB 契约缺陷，改进报错提示。设计：`.pb/specs/v11.6.0-ai-authoring-and-performance-design.md` §4。

### Fixed

- SQL 命名参数改为按 SQL 词法扫描替换：参数名须以字母或下划线开头，引号内的内容与 `::type` 类型转换原样保留。此前 `'2026-01-01 00:00:00'` 中的 `:00` 会被当成参数，报"未提供参数 `:00`"。
- DB 数据行的 `sql` / `query` 取值为 `BLANK` / `NULL` / `NONE` / 空时视为未提供：先取有效 `sql`，没有再取 `query`。此前只要存在 `sql` 字段就执行，`sql=BLANK` 会报 `near "BLANK": syntax error`，导致同表混用 `sql` 行与 `query` 行时无法满足字段集合一致约束。
- `TEST_CASE_WRITING_GUIDE.md` §5.5 示例的两行字段集合不一致（违反其自身约束），已改为带齐 `query` / `sql` / `operation` 并填 `BLANK`。
- `CORE_DESIGN_CONSTRAINTS.md` §14.2：删除 11.5.1 遗留的"6 个 README 待补"过时说明，demo 清单改为实际的 23 个。

### Changed

- 报错附带修复提示：`verify` 缺字段时提示 `match_mode="subset"` 或填 `BLANK`；SQL 缺参数时给出位置片段并说明引号内冒号不是参数。
- GUIDE §5.5 补充 BLANK 回落规则、占位符规则，以及用 `DB` + `verify` 断言查询结果的写法。
- `rodski-skills` case-writer：补充 `verify` strict/subset、`WaitTime` 对耗时的影响、`evaluate` 断言"静默通过"风险，以及 DB 三条契约。
- 新增验收模块 `rodski-demo/DEMO/demo_authoring_v116/`（DB 契约用例，在 11.5.1 上 0/2、修复后 2/2）。


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
