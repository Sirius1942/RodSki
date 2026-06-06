---
name: rodski-case-writer
description: 在任意 RodSki 用例仓库中编写、修改、调试或审查 RodSki 自动化测试模块。Codex 处理 RodSki case/*.xml、model/model.xml、data/globalvalue.xml、data/data.sqlite、plan/*.xml、TEST_CASE_WRITING_GUIDE.md 合规、RodSki CLI 校验、UI/API/DB 测试用例，或 AI 生成 RodSki 用例的风格一致性时使用。中文触发：写测试用例、修改用例、修复用例、调试失败结果、审查 RodSki 用例、检查 guide 合规、修改 case/model/data/plan、处理 data.sqlite/globalvalue.xml、运行 rodski dry-run 或 data validate。
---

# RodSki 用例编写器

## 范围与上下文

在任意 RodSki 用例仓库中处理测试用例工作时使用本技能：`case/*.xml`、`model/*.xml`、`data/globalvalue.xml`、`data/data.sqlite`、`plan/*.xml`、guide 合规、UI/API/DB 用例编写、审查、调试和 CLI 校验。处理 RodSki 框架源码或协议工作时，使用范围更广的 `rodski` 技能。

任务位于 `$HOME/TestCase` 时，遵守该仓库的 `CLAUDE.md`，并优先使用其中声明的全局 RodSki CLI。在其他 RodSki 用例仓库中，使用目标仓库的本地说明和 RodSki CLI（如果存在）。

编辑 RodSki 产物前：
1. 确认本地 CLI 版本；不要信任本技能或历史会话里的版本信息
2. 起手打一份 capabilities 快照锚定 live 事实：当前 CLI 顶层 `--help` 列出 `capabilities` 子命令即可调用 `rodski capabilities`，把 `supported_keywords`/`locator_types`/`special_values` 作为关键字、定位器类型、特殊值的权威清单；再按需查看相关 CLI help（`--help`、`run --help`、`data --help`、`plan --help`）
3. 用 `scripts/rodski_guide_slice.py` 只加载相关 guide 章节
4. 查看目标模块现有 `case/`、`model/`、`data/`、`plan/` 风格；用 `scripts/rodski_module_inventory.py` 快速汇总三元结构
5. 仅在需要时读取最小相关参考：`ui-patterns.md`、`api-db-patterns.md`、`table-controls.md`、`locator-failures.md`、`element-probe.md`、`vision-locators.md` 或 `style.md`
   - 新增/修复 Web UI 定位器，且 DOM 属性未由用户或现有 model 提供时，先读 `element-probe.md`：用 Playwright MCP（`.mcp.json` 已注册）打开真实页面、`browser_snapshot` 取可访问性树、按 `style.md` 阶梯挑已确认存在的稳定选择器，不要凭描述瞎猜定位器。传统 DOM 定位失效（动态 canvas、无属性、跨语言）时再读 `vision-locators.md`。
6. 当任务是长流程、跨角色、端到端、询价/订单/履约/售后，或其他检查点驱动任务时，读取 `references/long-flow.md`

在 `$HOME/TestCase` 中，`TEST_CASE_WRITING_GUIDE.md` 是只读参考文档，也是 RodSki 用例编写的核心约束。用它设计和审查用例，并确保编写的用例符合其要求。用例工作期间不要修改、同步覆盖、追加笔记或以其他方式编辑它。

```bash
RODSKI_BIN="/path/to/target/rodski"
"$RODSKI_BIN" --version

# $HOME/TestCase 默认：
/opt/homebrew/bin/rodski --version
```

## Guide 新鲜度

用例工作期间不要下载、同步覆盖或编辑本地 guide。在 `$HOME/TestCase` 中，guide 是用户持有的只读参考材料，也是用例编写的核心约束。如果 guide 缺失、明显过期，或用户要求同步它，说明用例编写器将 `TEST_CASE_WRITING_GUIDE.md` 视为只读文件，并且不要在该工作流中修改它。下面的辅助工具仅用于普通用例编写之外的显式维护，最好先带 `--dry-run`；任何真实写入都必须按 guide 维护处理，而不是按用例编写处理：

```bash
python3 scripts/sync_test_case_guide.py \
  --repo /path/to/rodski-case-repo \
  --rodski /path/to/target/rodski
```

## 失败运行排查顺序

当用户指向失败的 RodSki 结果目录，或要求诊断失败的用例运行时，先检查已编写的用例内容是否符合 `TEST_CASE_WRITING_GUIDE.md`，然后再追查运行产物。按以下顺序处理：

1. `scripts/rodski_guide_slice.py --mode debug`，并在相关时同时查看目标 `case/`、`data/data.sqlite`、`model/model.xml` 和 `plan/` 文件：确认已写用例符合当前 guide 约束，尤其是 case/model/data 三元结构、受支持关键字、数据引用、通过 `type` 执行 UI 原子操作、定位器语法，以及不存在旧式或伪关键字。
2. `scripts/rodski_result_diagnose.py --result-dir <result-dir>`：手动追日志前，先拿到首个失败步骤、last-ok/next-failed 步骤、截图路径和可能的编辑面。
3. 用例慢、不稳定或属于长流程时运行 `scripts/rodski_slow_steps.py --result-dir <result-dir>`：识别定位器 fallback、固定等待和重试热点。
4. `execution_summary.json`：重建步骤时间线；确认哪些步骤通过，以及失败前最后已知状态。
5. `result.xml`：查看最终 FAIL 原因、失败关键字、失败截图路径和录像路径。
6. `execution.log`：搜索 `ERROR`、`FAIL`、`SKI302` 和 `SKI313`；检查失败附近的真实执行细节。
7. `screenshots/*failure.png` 以及失败前紧邻的几张截图：检查实际页面状态。
8. `recordings/*.webm`：仅当截图无法解释动态跳转时使用。
9. `case/<case-name>.xml`：看到运行失败步骤后，将其映射回精确的用例编排。
10. `data/data.sqlite`：检查失败步骤引用的表达式、输入值和期望值。
11. `model/model.xml`：仅当失败涉及 click、locate、verify、type 或类似模型绑定行为时检查定位器。
12. `data/globalvalue.xml`：仅当怀疑环境、URL、账号或全局变量值时检查。

## 编写规则

- 将本地 `TEST_CASE_WRITING_GUIDE.md` 视为只读参考材料和用例编写核心约束：用例设计必须符合其要求。结合当前 CLI `--version`/`--help` 和目标模块现有风格，把它们作为实时事实来源。受支持关键字、定位器类型和特殊值的**权威清单以 `rodski capabilities` 为准**（当前 CLI 顶层 `--help` 列出 `capabilities` 时调用，取其 `supported_keywords`/`locator_types`/`special_values`）；本技能、`CLAUDE.md`/`AGENTS.md`、参考笔记和 guide 里出现的关键字名单只是示例和常见幻觉提示，不要当成完整白名单或硬编码事实来源。如果本技能、参考笔记、capabilities 输出、XSD 或 guide 相互冲突，不要静默猜测；运行最窄的 dry-run/help 检查并报告不一致。
- 保持 RodSki 三元结构一致：Case 只编排动作，Model 定义 UI 元素/API 字段/DB 字段，输入和期望数据放在 `data/data.sqlite`；全局变量放在 `data/globalvalue.xml`。
- 导航使用 `navigate`。不要写 `open`。
- 对于跨平台或跨角色 UI 流程，例如在修理厂、商户和管理端门户之间切换，不要只在同一浏览器会话里用 `navigate` 跳到另一个 URL 来切换身份。当当前 guide/CLI/dry-run 确认支持的浏览器生命周期后，使用 `close -> navigate -> login -> verify`：切换平台/角色前关闭当前浏览器，让下一个 `navigate` 创建新浏览器，以新角色认证，并验证角色特定首页或身份标识。仅在同一平台、同一已认证角色内使用普通 `navigate`。
- 对于 Desktop 启动或应用切换，仅当当前 CLI/guide/dry-run 确认目标环境支持时才使用 `launch`。
- API 使用 `send` 加 `verify`。不要创建 `http_get`、`http_post`、`assert_json` 或 `assert_status`。
- 将 `click`、`hover`、`select`、`key_press`、`drag`、`scroll` 等 UI 原子操作放入由 `type` 执行的数据行中，而不是放在 `test_step@action`。
- 优先使用状态/状态文本等待，而不是固定等待：先使用稳定定位器、面向状态的 `verify`、框架 wait/retry 行为，或等待可观察就绪状态的 model/data 设计。尽量减少显式 `<test_step action="wait">`；只有在无法表达为条件的真实异步边界才保留，并避免连续等待、长等待，或在一个用例中出现多次等待，除非有明确理由。
- 只使用定位器子节点：`<location type="...">value</location>`。不要使用旧式 `locator="..."`、`type="xpath" value="..."`、`type="locator" value="..."` 或 `<location value="...">`。
- 在 `test_step@data` 中只使用 `DataID`；除 `GlobalValue.Group.Var` 引用外，不要写 `ModelName.DataID`。
- Case 文件名应遵循目标模块现有命名风格。不要只为了改变语言、大小写或 snake_case/CamelCase 风格而重命名稳定用例文件。
- 涉及“业务规则说明”“规则说明”“说明”等需要为当前规则命名或描述的字段时，名称应贴合当前用例表达的业务语义，避免泛泛写成占位词；描述应简明扼要，只保留支撑当前验证点的关键信息。
- Case 文件名前缀应反映实际执行类型：纯界面用 `UI`，纯接口用 `API`，纯数据库用 `DB`；混合用例用组合前缀，如 `UI+DB`、`API+DB`、`UI+API+DB`。判定以实际 `test_step action` 为准：`navigate`/`type`/`evaluate`/`screenshot`/`get` 等归 UI，`send` 归 API，`DB` 或明确数据库检查脚本归 DB。纯 DB 用例的 `component_type` 应为 `数据库`。
- 当存在 `send`、`type` 或 `verify` 的 model/data 路径时，不要用宽泛的 `evaluate` 代码伪造通过。

## 工作流

1. 编辑前说明任务目标、约束和验证计划。
2. 将相关 guide 切片作为只读参考读取，并在修改 case/model/data/plan 产物前检查目标模块文件。用例设计必须满足 `TEST_CASE_WRITING_GUIDE.md`；不要把编辑 guide 本身作为用例编写或修复的一部分。对于大模块，先运行 `rodski_module_inventory.py`，避免手工重复发现三元结构。面对超大单 case 判定表（数十个 `<scenario>`、300KB+）时，用 `rodski_scenario_slice.py list` 定位目标场景行范围，再用 `show --id` 只读取该场景，避免整文件载入上下文。对于较慢的长流程重跑，在重跑全链路前用 `rodski_checkpoint_plan.py` 建议或生成窄范围 debug plan。
3. 在 `$HOME/TestCase` 中，不要把 `improve/` 作为新用例编写来源。它是历史笔记和失败复盘归档，不是实时指导。只有当用户明确要求历史经验，或在检查 guide、当前 CLI/schema/help、目标模块文件和最新运行证据后继续调查失败模式时，才查阅 `references/improve-index.md` 和一个具体笔记。
4. 做满足任务的最小改动。匹配周围 XML 风格；不要格式化无关文件、重命名稳定 ID 或重排既有步骤，除非请求行为确实需要。
5. 对改动模块或文件运行 guard，然后运行最小有意义的 RodSki 校验。整模块校验时，优先用 `rodski_preflight.py` 一条龙跑完 capabilities → guard → data validate → dry-run；它在首个失败步骤短路并指出失败点：

```bash
python3 scripts/rodski_preflight.py \
  "/path/to/module" --repo "/path/to/rodski-case-repo"
```

需要逐步控制（例如只 dry-run 单个 case 文件以缩窄范围），再手动分步：

```bash
python3 scripts/rodski_case_guard.py \
  --repo "/path/to/rodski-case-repo" \
  --target "/path/to/changed/module-or-file" \
  --rodski-bin "/path/to/target/rodski"
"/path/to/target/rodski" data validate "/path/to/module"
"/path/to/target/rodski" run "/path/to/module/case" --dry-run --output-format json
```

如果目标是单个 case 文件，且 dry-run 该文件范围更窄，就 dry-run 该文件。不要静默跳过校验；如果无法运行，报告准确命令和原因。如果用户明确要求不运行 RodSki，只做静态检查，并在最终答复中说明跳过的命令。

## 资源

- `references/style.md`：本仓库的简明风格锚点、定位器阶梯和审查锚点。
- `references/long-flow.md`：长流程、跨角色、检查点驱动业务自动化的紧凑规则。
- `references/element-probe.md`：写 Web UI 定位器前用 Playwright MCP 探查真实 DOM、按阶梯挑稳定选择器，解决"找不到控件/locate 超时"。
- `references/vision-locators.md`：视觉定位器（vision/vision_image/ocr/vision_bbox）本机实测现状，并覆盖 guide §11.4 过时的 OmniParser 配置。
- `references/ui-patterns.md`：UI 流程、等待、验证和 evaluate 桥接模式的紧凑说明。
- `references/api-db-patterns.md`：API/DB send/verify/run/DB 指导。
- `references/table-controls.md`：表格、弹窗、下拉框、富文本和复杂控件模式。
- `references/locator-failures.md`：定位失败、优先级、等待、重试和性能分诊模式。
- `references/improve-index.md`：`$HOME/TestCase/improve` 下归档笔记的可选索引；不要用于新用例编写，默认不要读取。
- `scripts/rodski_case_guard.py`：常见 RodSki 幻觉、过多固定 `wait`、结构漂移的静态 guard；并校验 case 内 `@model`/裸 DataID/`GlobalValue.Group.Var` 能否在同模块 model.xml、data.sqlite、globalvalue.xml 解析（dry-run 不查这些跨文件引用）。
- `scripts/rodski_preflight.py`：用例完成前的一条龙校验，按序跑 capabilities → guard → data validate → dry-run，首个失败步骤短路并指出失败点。整模块收尾校验优先用它。
- `scripts/rodski_guide_slice.py`：只打印 UI/API/DB/plan/long-flow/debug 工作相关的 guide 章节。
- `scripts/rodski_module_inventory.py`：汇总模块的 case/model/data/plan 三元结构和常见交叉引用缺口。
- `scripts/rodski_scenario_slice.py`：对大型单 case 判定表 XML（数十个 `<scenario>`、300KB+）按 scenario 切片。`list` 列出每个 scenario 的 id/行范围/字节数，`show --id PC_001` 只打印单个场景原文，避免整文件读入。
- `scripts/rodski_result_diagnose.py`：将 RodSki 结果目录汇总为首个失败、日志线索、截图和可能编辑面。
- `scripts/rodski_slow_steps.py`：分析较慢的 RodSki 结果目录，找出定位器 fallback、固定等待和重试热点。

报告类脚本（`rodski_module_inventory.py`、`rodski_result_diagnose.py`、`rodski_slow_steps.py`）只要目录存在就恒返回 0，发现内容在 stdout/JSON 里，不要用退出码 gate；`rodski_case_guard.py`（有 FAIL 即非 0）和 `rodski_preflight.py`（首个失败短路）才能用退出码判断通过与否。
- `scripts/rodski_checkpoint_plan.py`：在当前 CLI 支持时，建议窄范围长流程重跑，并生成 step_debug plan。
- `scripts/sync_test_case_guide.py`：版本兼容检查后用于同步本地 guide 的显式维护辅助工具。
