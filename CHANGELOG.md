# Changelog


## [11.8.14] - 2026-10-15

### Fixed

- BUG-A21/A22：接口模型 verify 的字段范围：strict 要求 _verify 行包含请求字段与 _method/_url 控制元素（GUIDE §8.2 示例照写即失败），且模型未声明 status 元素时 status 列被静默忽略；接口模型改为只比较行内出现且模型已声明的字段，status 列恒按 HTTP 状态码比较，_ 前缀控制元素不参与比较（CORE §4.7.4 第 6 条、GUIDE §5.7.3）（问题单 `.pb/iterations/iteration-66/BUG_REPORT.md`）

## [11.8.13] - 2026-10-15

### Fixed

- BUG-A19：case XML 步骤上的 match_mode="subset" 未传入 verify 参数，恒按 strict 校验；execute_step 将步骤 match_mode（解析器默认 strict、business_call 为 subset）传给关键字（问题单 `.pb/iterations/iteration-66/BUG_REPORT.md`）

## [11.8.12] - 2026-10-15

### Fixed

- BUG-A20：响应体同名 status 字段覆盖 HTTP 状态码；send 与压测驱动统一由 build_http_result 组装，status 恒为 HTTP 状态码，响应体自带 status 时完整响应体放在 body（body.status）（问题单 `.pb/iterations/iteration-66/BUG_REPORT.md`）

## [11.8.11] - 2026-10-15

### Fixed

- BUG-A10：不带用例路径的 rodski run --group/--tag 总是先解析默认计划，报 SKI703 冲突或未找到默认计划；有 selector 时改为在当前模块全部用例上临时选择（问题单 `.pb/iterations/iteration-66/BUG_REPORT.md`）

## [11.8.10] - 2026-10-15

### Fixed

- BUG-A08：--priority P0,P1 多值时 scenario 选择只取第一个值（执行与 --dry-run 均如此）；selector 编译接受优先级列表（问题单 `.pb/iterations/iteration-66/BUG_REPORT.md`）

## [11.8.9] - 2026-10-15

### Fixed

- BUG-A07：用例级 <case tags> 属性（case.xsd 允许）被解析器忽略；与 <cases tags> 合并后参与 --tags / --exclude-tags，GUIDE §3.2 属性表补充 tags（问题单 `.pb/iterations/iteration-66/BUG_REPORT.md`）

## [11.8.8] - 2026-10-15

### Fixed

- BUG-A09：--tag 先被当作 --tags 按文件级 tags 做用例级过滤，只写在 scenario 上的 tag 选不中任何用例；selector 模式下只在 selector 编译阶段统一选择一次（问题单 `.pb/iterations/iteration-66/BUG_REPORT.md`）

## [11.8.7] - 2026-10-15

### Fixed

- BUG-A06：selector 模式下不含 scenario 的用例一律 SKIP（--tags 0 条执行、退出码 0）；元数据为无 scenario 的用例生成用例级记录，命中时整条用例选中（问题单 `.pb/iterations/iteration-66/BUG_REPORT.md`）

## [11.8.6] - 2026-10-15

### Fixed

- BUG-A04：<loop> 内的 <if>/<elif>/<else> 被解析器静默丢弃；循环体改用与阶段容器相同的解析（支持 if/elif/else 链）（问题单 `.pb/iterations/iteration-66/BUG_REPORT.md`）

## [11.8.5] - 2026-10-15

### Fixed

- BUG-A03：element_exists 恒假 / element_not_exists 恒真：以单参调用 locate_element(type, value) 且异常被吞；改为按 CORE 约定拆分 type=value（否则按 CSS），定位异常按条件无法评估处理（问题单 `.pb/iterations/iteration-66/BUG_REPORT.md`）

## [11.8.4] - 2026-10-15

### Fixed

- BUG-A02：Return 条件恒为假：条件求值器持有的 Return 历史在构造时（空列表被替换）和用例间重建 KeywordEngine 时都与真实历史脱钩；改为共享并在重建时改绑，同时支持 GUIDE 写法 ${Return[-1].x} == v 与 CORE 写法 ${Return[-1].x == v}、嵌套字段（问题单 `.pb/iterations/iteration-66/BUG_REPORT.md`）

## [11.8.3] - 2026-10-15

### Fixed

- BUG-A01：条件中的 ${name} 变量引用不解析、set 定义的变量在条件里不可见；条件操作数改为从 loop 变量与 set 模板变量取值，未定义变量按条件无法评估处理（问题单 `.pb/iterations/iteration-66/BUG_REPORT.md`）

## [11.8.2] - 2026-10-15

### Fixed

- BUG-A05：条件运算符 >= / <= 被 > / < 先拆开导致整个条件块被跳过；改为按长度优先匹配运算符（问题单 `.pb/iterations/iteration-66/BUG_REPORT.md`）

## [11.8.1] - 2026-10-15

修复版本：调试参数接线、`--group` 选择、`loop` 变量解析；重写 REQ-012 验收用例为真实执行判定。

### Fixed

- `rodski run` 未把 `DebugSession` 传给执行器，`--break-at` / `--start-from` / `--stop-at` / `--step-mode` 在 11.8.0 中均不生效。
- `--group`（及 `--tag` / `--priority` 等 selector）选中 scenario 时整条用例被判为 `plan_not_selected` 跳过：selector 选择项缺少 `case_file`，与 v11.5.0 起的用例身份 `case_file::case_id` 不匹配。
- `<loop var="i">` 中 `data` 属性的 `${i}` 不被替换：循环变量未写入模板解析源（现与 `set` 关键字一致）。
- 调试钩子改为 `getattr(self, 'debug_session', None)`，修复 11.8.0 引入的 6 个单测失败。

### 文档

- `TEST_CASE_WRITING_GUIDE.md`：`loop range` 示例由 `1,5` 改为 `1-5`，并说明 `1-5` 为闭区间、`1,2,3` 为取值列表（`1,5` 只循环两次）。

### 验收

- 删除 11.8.0 中以 JS 自造数据自证的模拟验收；`rodski-demo/DEMO/debug_partial_execution/` 重写为 37 条真实验收：以子进程执行 `debug_partial_execution_targets/` 中的被测用例，按执行轨迹、结果产物与 `rodski debug` 输出判定。
- 当前通过 1/37（AC-018）；其余为 REQ-012 尚未实现的能力（断点暂停交互、驱动动作日志、对象池、`--rows` 等），待后续版本实现。

### 测试

- 新增 `rodski/tests/integration/test_v1181_regressions.py`（`--start-from`、`--group`、loop 变量）。


## [11.8.0] - 2026-10-14

REQ-012 调试功能正式发布。新增断点管理、部分执行、执行队列、步骤快照等调试能力，提升测试开发和故障排查效率。

### Added

- **断点管理**：通过 `--break-at` 参数在指定位置设置断点，支持 `step:N`（步骤编号）、`scenario:ID`（场景ID）、`node:NAME`（节点名称）、`flow:ID`（流程ID）、`driver:ACTION`（驱动动作）、`batch:row:N`（数据行）等多种断点类型。
- **部分执行**：通过 `--start-from N` 和 `--stop-at N` 参数精确控制执行范围，支持跳过前置步骤或在指定步骤后停止。
- **单步执行**：通过 `--step-mode` 参数启用单步执行模式，每执行一步自动暂停；配合 `--driver-level` 可在每个驱动动作后暂停。
- **执行队列**：自动记录多层级执行历史（Case → Scenario → Flow → Node → Step → Driver），支持查看完整的执行路径和上下文。
- **步骤快照**：在断点暂停时自动保存步骤状态（action, model, data, 场景信息等），支持查询和检索。
- **交互式调试命令**：暂停时支持 `continue` / `next` / `quit` / `list` / `context` / `help` 等命令，方便调试操作。
- **调试会话管理**：通过 `DebugSession` 单例管理调试状态，集成断点管理器、执行队列和对象池。
- **数据驱动调试支持**：断点和部分执行功能与数据驱动场景完全兼容，支持在数据循环中设置断点。

### Changed

- `SkiExecutor` 新增调试钩子：在每个测试步骤执行前检查断点，命中时暂停执行队列并保存步骤快照。
- `DebugSession` 新增 `step_snapshots` 字典和相关方法（`save_step_snapshot` / `get_step_snapshot` / `clear_snapshots`）。
- 执行队列暂停时不再阻塞后续测试，支持继续、下一步或退出执行。

### Fixed

- 修复 `BreakpointManager.should_break()` 方法不存在的问题，改为调用 `check_hit(step=step_index)`。
- 修复 `ObjectPool.save_step_snapshot()` 方法缺失的问题，步骤快照功能移至 `DebugSession`。

### 验收

- `rodski-demo/DEMO/debug_partial_execution/`（3 个验收用例，通过率 100%）：
  - AC-035：数据驱动场景的断点（测试断点在数据驱动循环中的触发）
  - AC-036：多步骤部分执行（测试 `--start-from` 和 `--stop-at` 参数）
  - AC-037：驱动器日志测试（测试驱动动作日志的自动记录）
- 完整的测试模块：7 个数据表、7 个页面模型、完整的元数据结构、详细的文档（README, TEST_REPORT, SUMMARY）

### 文档

- 新增 `rodski-demo/DEMO/debug_partial_execution/README.md` - 调试功能使用指南
- 新增 `rodski-demo/DEMO/debug_partial_execution/TEST_REPORT.md` - 详细测试报告
- 新增 `rodski-demo/DEMO/debug_partial_execution/SUMMARY.md` - 集成总结
- 新增 `REQ-012_COMPLETION_REPORT.md` - 完成报告

### 相关需求

- REQ-012：调试功能（断点、部分执行、执行队列、交互式调试）


## [11.7.1] - 2026-09-30

`AutoWait` 取消隐含默认时长，规则更简单（Owner 决策）。

### Changed

- **不设置 `DefaultValue.AutoWait` 或写 `0` = 不自动等待**：每个定位器只尝试一次，找不到立即失败；UI `verify` 单次比对。要自动等待必须在 `globalvalue.xml` 显式写时长，推荐 `<var name="AutoWait" value="5000"/>`。11.6.0 / 11.7.0 开发期的"不设置 = 5000ms"不再成立。
- 非数字取值（如 `default`）执行前报错并给出 `value="5000"` 示例。
- `rodski init` 生成的 `globalvalue.xml` 默认写 `AutoWait=5000`。
- rodski-demo 全部模块显式配置 `AutoWait=5000`（`demo_autowait_zero` 刻意不设置，验证不自动等待；`demo_authoring_v116_no_retry` 保持 `0`；`demo_autowait_long` 保持 `12000`）；原先没有 `globalvalue.xml` 的 5 个模块补建。
- 文档：CORE §4.6.5 / §7.4 / §13、GUIDE §5.7.2 / §6.4.2、SKILL_REFERENCE、AGENT_INTEGRATION、README、rodski-skills 同步。

### 升级须知

- **升级到 11.7.1 后，globalvalue 没写 `AutoWait` 的模块不再自动等待**（包括 11.6.0 的 UI `verify` 自动重试）。请在每个模块的 `globalvalue.xml` → `DefaultValue` 组加入 `<var name="AutoWait" value="5000"/>`。

## [11.7.0] - 2026-09-30（未单独发布，随 11.7.1 一起发布）

自动等待统一接管元素查找。不新增关键字（仍为 17 个），`case.xsd` / `model.xsd` 不变。设计：`.pb/specs/v11.7.0-autowait-unified-design.md`；迭代：`.pb/iterations/iteration-65/`。

### Changed

- `DefaultValue.AutoWait`（自动等待，毫秒）成为**所有驱动（Web / Android / iOS / 桌面视觉）、所有查找测试对象步骤**的唯一等待上限：`type` 单字段与批量的**每一个字段**（输入、`click` / `double_click` / `right_click` / `hover` / `select【】`、`key_press【】` 目标、`drag【】` 两端）、UI `verify` / `check`（含视觉定位字段）、`get` / `get_text`、`type` 后自动取值、`clear`、`upload_file`、视觉定位（每轮新截图）。
- 实现形态：公共层 `rodski/core/auto_wait.py` 的 `run_element` —— try 查找并执行 → 只捕获"未找到 / 不可操作 / 已失效 / 单次超时"（白名单）→ 等待 200ms（视觉 1000ms）→ 再执行；成功即继续，超过 AutoWait 抛 `ElementWaitTimeoutError`（SKI326），信息含元素名、尝试过的定位器与 `AutoWait=Nms`。其余异常立即抛出，不等待。
- 按元素计时：每个字段独立一份预算；同一元素的多个 `<location>` 共享这一份预算（失败耗时 ≈ 1 × AutoWait，不再是 N × 驱动超时）。
- PlaywrightDriver：删除 `wait_for_selector` 吞异常、硬编码 5000/3000ms、force 点击、JS 点击、JS 赋值降级；select / hover / dblclick / 右键 / drag / clear / upload / get_text 统一定位器转换并使用剩余预算；原生异常转换为 `ElementNotFoundError` / `ElementNotInteractableError`（SKI327）/ `StaleElementError` / `DriverStoppedError`。
- AppiumDriver：删除 `WebDriverWait(driver, 10)`（它还遮蔽了 `BaseDriver.wait()`），启动时 `implicitly_wait(0)`；每次调用一次即时查找 + 一次动作；`hover` / `select` / `long_press` 与 `click` / `type` 使用同一套定位器解析；新增 `clear_locator` / `get_text_locator`；`clear` / `get` / 自动取值改用模型对应的移动端驱动。
- DesktopDriver：视觉定位每轮强制新截图（绕过 0.5s 截图缓存），未匹配抛异常；补 `double_click_locator` / `right_click_locator` / `hover_locator` / `key_press`，`drag【】` 支持定位器；`select【】` 明确报不支持。PywinautoDriver 未实现的定位显式报错。
- 视觉定位截图改用模型对应的目标驱动（之前固定截 Web 页面）。
- 截图统一 10s 超时（修复 full 模式逐步截图偶发阻塞 30s）。
- `RetryExhaustedError` 文案：未配置步骤级重试时不再显示"重试 1 次"。

### Removed

- 从未生效的配置：`smart_wait_enabled` / `smart_wait_max_retries` / `smart_wait_retry_interval` / `smart_wait_log_retry` / `element_wait_timeout` / `element_retry_interval` / `retry` / `retry_delay` / `retry_on_errors`（`config.json` 与 `ConfigManager.DEFAULTS`）。用户配置中仍存在时打印一次废弃警告。CORE §13"智能等待机制"（所述机制在代码中从未接通）重写为"自动等待（AutoWait）机制"。

### Fixed

- `get` 模型模式 / `type` 后自动取值读不到元素时静默返回空值 → 现在 AutoWait 后失败。`demo_full` TC014A 因此暴露，按 `.pb/specs/rodski-demo-issues.md` 标为 `expect_fail`。
- 桌面端 `verify` 调用 4 参数 `get_text(locator)` 导致 TypeError。
- iOS `scroll` 与 `type` 批量 `scroll【x,y】` 调用签名不匹配。

### 兼容性影响

1. 元素查找不再使用驱动内置超时（Web 10s / 30s、移动端 10s），统一由 `AutoWait` 决定（11.7.1 起须显式设置）。
2. force 点击 / JS 点击 / JS 赋值降级已删除：被遮挡且遮挡不消失的元素现在会失败（正确行为）。
3. `get` 读不到元素由"静默空值 + warning"改为失败。
4. UI `verify` 含视觉字段时也会在 AutoWait 内重试。

### 验收

- `rodski-demo/DEMO/demo_autowait`（5000）/ `demo_autowait_zero`（不设置）/ `demo_autowait_long`（12000）：`run_acceptance.py` 30 项（15 个延迟测试页 × 各类动作、逐字段计时、多定位器共享预算、20s 元素 ≈5s 失败、遮罩不消失必须失败、AutoWait=0 立即失败、调大后可等到）。
- `mobile_app/case/autowait.xml` + `scripts/run_autowait_acceptance.py`（Android 模拟器，mock 延迟 `MOCK_DELAY_MS`）；`mobile_app/case/login.xml` 删除全部固定 `wait`。
- 桌面视觉：单元测试（mock 截图序列）覆盖，本机无感知服务未做 demo 实跑。

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
