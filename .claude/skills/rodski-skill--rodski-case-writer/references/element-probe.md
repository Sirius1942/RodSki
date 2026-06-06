# 前端控件探查（写 UI 定位器前用真实 DOM）

编写或修复 Web UI `model.xml` 定位器前使用本文。目的：在写 `<location>` 前先看真实页面，按
`style.md` 的定位器阶梯挑选**已确认存在且稳定**的选择器，从源头消除"凭描述瞎猜定位器 → locate 超时"。

实时契约仍以 `TEST_CASE_WRITING_GUIDE.md` 为准；定位器优先级仍以 `style.md` 阶梯为准。

## 何时探查

- 新增 Web UI 元素，且 DOM 属性未由用户/现有 model 提供。
- 现有定位器 locate 超时、命中严格模式，或失败截图显示元素其实存在但选择器对不上。
- 动态 ID/hash class、弹窗内重复文本、活动 tab 内重复控件等高风险场景。

仅当你确实拿不到稳定 DOM 信息时才探查。用户已给定位器、现有 model 已有稳定选择器，或目标站点
此刻不可达（需登录态/内网）时，不要为探查而探查——按已知信息写，或先问用户要访问方式。

## 探查后端：Playwright MCP

`$HOME/TestCase/.mcp.json` 已注册 `@playwright/mcp`（stdio，`npx @playwright/mcp@latest`）。
本机已装 node、npx 和 playwright 浏览器。MCP 工具仅在**新会话**加载；当前会话看不到 `browser_*`
工具时，说明 MCP 尚未在本会话生效，需新开会话或改用离线脚本路径（见末节）。

关键工具（写 rodski 定位器只需这几个）：

- `browser_navigate` — 打开目标页（带登录态时先导航到登录页操作，或复用浏览器 profile）。
- `browser_snapshot` — 返回可访问性树快照，含每个可交互元素的 role、accessible name 和稳定属性。
  **这是首选**：直接对应 rodski 的 `text` / role-based css 定位。
- `browser_generate_locator` — 对指定元素生成 Playwright 推荐定位器，可反推出 css/xpath/text。
- `browser_evaluate` — 在页面内跑 JS 取 `data-testid`、`id`、`aria-label`、`name` 等属性原值。
- `browser_click` / `browser_fill_form` — 仅用于走到目标状态（打开弹窗、切到目标 tab）再快照，
  不是用来代替 rodski 执行。

## 探查 → 落地流程

1. `browser_navigate` 到目标页；需要时用 `browser_click` 走到元素所在状态（弹窗已开、tab 已激活）。
2. `browser_snapshot` 拿可访问性树，定位目标元素的 role + accessible name。
3. 对候选元素用 `browser_evaluate` 读真实属性，按 `style.md` 阶梯择优：
   `data-testid` → 稳定 `id` → `aria-label`/role → 业务 `data-*` → `name` → 稳定 css → xpath → 唯一可见文本。
4. 把选中的属性**编码成 rodski 定位器子节点**（注意：`data-testid`/`aria-label`/`role` 都不是 rodski
   locator type，要写进 `<location type="css">`）：
   - `data-testid="login-btn"` → `<location type="css">[data-testid="login-btn"]</location>`
   - `id="username"` → `<location type="id">username</location>`
   - `aria-label="搜索"` → `<location type="css">[aria-label="搜索"]</location>`
   - 唯一可见文本"登录" → `<location type="text">登录</location>`
5. 多个候选时写多个 `<location>` 并加 `priority`，稳定命中快的放最低 priority 值。
6. 探查只为**确认选择器**，不要把 MCP 抓到的临时 DOM 顺手写成固定坐标，除非确属 `vision_bbox` 兜底场景。

## 与视觉定位的分工

- DOM 规范、有稳定属性 → 探查后写传统定位器（css/id/text），运行快、零模型开销。**默认走这条。**
- 动态 canvas、无任何稳定属性、跨语言 UI → 才考虑视觉定位（见 `vision-locators.md`）。
- 不要因为一次 locate 失败就跳到视觉定位；先探查确认是不是选择器写错或页面未就绪。

## 无 MCP 时的离线兜底

首选始终是新开会话用 Playwright MCP；以下离线脚本路径仅在确实无法新开会话时才用。

**前置检查（不通就别走这条路）**：离线脚本用的是 playwright 的 **Python** 包，不是 MCP 的 node 包，
本机未必装了。先确认目标解释器里能导入：`python -c "import playwright"`。
- 不通 → 不要硬写 Python 脚本。改用 node 侧 `npx playwright`（已随 MCP 装），或直接新开会话走 MCP。

通过后可写一次性脚本：`browser_navigate` 等价于 `page.goto`，`browser_snapshot` 等价于
`page.accessibility.snapshot()`，属性读取等价于 `page.eval_on_selector_all`。把候选定位器打印出来供填
`model.xml`，用完删脚本。不要把临时探查脚本留在用例仓库里。
