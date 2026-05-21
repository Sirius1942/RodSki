# RodSki vs Browser-Use 对比分析

> 分析日期：2026-05-21  
> Browser-Use 版本：0.12.7  
> RodSki 版本：7.0.0

---

## 一、核心定位

| 维度 | RodSki | Browser-Use |
|------|--------|-------------|
| **本质** | 关键字驱动的**确定性测试框架** | LLM 驱动的**自主浏览器 Agent** |
| **执行模式** | 人写 XML 用例 → 框架顺序执行 | 人给自然语言任务 → LLM 动态决策 → 执行 |
| **控制权** | 测试工程师完全掌控每一步 | LLM 自主规划和决策 |
| **目标用户** | QA 工程师 / 测试团队 | AI Agent 开发者 |

---

## 二、架构设计对比

### 2.1 浏览器协议层

**RodSki**：使用 Playwright 高层 API（Python SDK），Playwright 内部封装了 CDP，但 RodSki 不直接接触 CDP 协议。

```
RodSki → PlaywrightDriver → playwright.Page → [Playwright 内部 CDP] → Chromium
```

**Browser-Use**：完全绕过 Playwright 运行时，直接通过 WebSocket 操作 CDP 协议。

```
Browser-Use → cdp-use.CDPClient → WebSocket → Chromium CDP 端点
```

`cdp-use` 是 Browser-Use 团队自研的类型安全 CDP Python 客户端，从官方 CDP 规范自动生成绑定，覆盖 50+ 个 CDP domain（DOM、Page、Network、Runtime、Input、Accessibility 等）。

### 2.2 浏览器状态感知

这是两者最核心的架构差异。

**RodSki**：被动感知。通过 Playwright locator 定位元素，视觉定位时截图 + LLM 分析。

**Browser-Use**：主动构建完整状态，每步都向 LLM 提供：

```
BrowserStateSummary
├── dom_state          ← CDP DOMSnapshot.captureSnapshot() + Accessibility.getFullAXTree()
│   └── llm_representation()  → 带 index 的可交互元素文本
│       [1]<button>Submit</button>
│       [2]<input placeholder="Search"/>
├── screenshot         ← CDP Page.captureScreenshot() → base64 PNG
├── page_info          ← Runtime.evaluate(JS) → 滚动位置、页面尺寸
├── tabs               ← Target.* 事件维护的内存状态
├── pending_network_requests  ← performance API
└── page_stats         ← 链接数、交互元素数、iframe 数等统计
```

发给 LLM 的消息结构：

```xml
<agent_history>历史步骤摘要</agent_history>
<agent_state>任务 / 文件系统 / 步骤信息</agent_state>
<browser_state>
  <page_stats>12 links, 8 interactive, 0 iframes</page_stats>
  Interactive elements:
  [1]<button>Submit</button>
  [2]<input placeholder="Search"/>
</browser_state>
[截图 base64]
```

LLM 输出 `click(2)` → 通过 `selector_map[2]` 找到 DOM 节点 → CDP 执行点击。

### 2.3 事件驱动架构

**RodSki**：同步顺序执行，无事件总线。

**Browser-Use**：基于 `bubus`（Pydantic 驱动的异步事件总线）+ Watchdog 架构：

```
BrowserSession (EventBus)
├── LocalBrowserWatchdog    → 管理浏览器子进程生命周期
├── DOMWatchdog             → 构建 DOM 树、截图、页面信息
├── SecurityWatchdog        → 域名白名单/黑名单
├── CaptchaWatchdog         → 验证码检测
├── PopupsWatchdog          → 自动关闭弹窗
├── DownloadsWatchdog       → 文件下载管理
├── HarRecordingWatchdog    → HAR 网络录制
├── RecordingWatchdog       → 视频录制
└── StorageStateWatchdog    → Cookie/Storage 持久化
```

每个 Watchdog 监听特定事件，解耦且可独立扩展。

---

## 三、作为自动化测试框架 PK

### 3.1 RodSki 优势

| 优势 | 说明 |
|------|------|
| **确定性** | 每步固定，结果可预期，适合回归测试和 CI/CD |
| **可维护性** | XML 用例 + model 分离，非开发人员也能编写和维护 |
| **多平台** | Web（Playwright）+ Mobile（Appium）+ Desktop（PyAutoGUI）统一框架 |
| **数据驱动** | SQLite 支持大量参数化测试，数据与逻辑完全分离 |
| **结构化报告** | XML 测试报告，天然 CI/CD 集成，断言明确 |
| **企业级特性** | Schema 校验、重试机制、三阶段执行（pre/test/post）、并行执行 |
| **成本可控** | 不依赖 LLM API，执行成本固定 |

### 3.2 RodSki 劣势

| 劣势 | 说明 |
|------|------|
| **脆弱性** | 依赖固定 locator，页面改版就要改 model.xml |
| **无自愈能力** | 元素找不到就失败，不会自动尝试其他定位方式 |
| **用例编写成本** | 需要手动维护 case.xml + model.xml + data.sqlite |
| **CDP 能力受限** | 通过 Playwright 高层 API，无法直接使用底层 CDP 能力 |
| **探索性测试弱** | 无法处理未知页面结构，不适合冒烟测试 |

### 3.3 Browser-Use 优势

| 优势 | 说明 |
|------|------|
| **自愈性** | LLM 理解页面语义，locator 变了也能找到元素 |
| **零用例编写** | 只需自然语言描述任务 |
| **探索性测试** | 能处理未知页面，适合冒烟测试和探索性测试 |
| **CDP 全能力** | 网络拦截、HAR 录制、性能监控、JS 覆盖率等 |
| **双模态感知** | DOM 文本 + 截图同时提供给 LLM，理解更准确 |

### 3.4 Browser-Use 劣势

| 劣势 | 说明 |
|------|------|
| **不确定性** | LLM 决策有随机性，同一任务两次结果可能不同 |
| **成本高** | 每步调 LLM API，token 消耗大 |
| **速度慢** | LLM 推理延迟 + DOM 序列化，每步 2-5 秒 |
| **无结构化报告** | 不适合 CI/CD 断言，结果难以量化 |
| **仅 Web** | 不支持 Mobile / Desktop |
| **调试困难** | LLM 决策过程不透明，失败原因难定位 |

---

## 四、RodSki 可借用 Browser-Use 的能力

RodSki 目前通过 Playwright 高层 API 操作浏览器，但 Playwright 本身暴露了 CDP 接口（`page.context.new_cdp_session()`），可以直接接入 Browser-Use 的底层能力。

### 4.1 DOM 序列化替代视觉定位

**现状**：RodSki 的 `vision` 定位器靠截图 + LLM 分析，速度慢且依赖视觉模型。

**改进方案**：引入 Browser-Use 的 `DomService`，用 CDP `DOMSnapshot.captureSnapshot()` + `Accessibility.getFullAXTree()` 构建带 index 的元素文本，给 LLM 提供文本 + 截图双模态输入。

```python
# 在 VisionLocatorCapability 中集成
from browser_use.dom.service import DomService
# 构建 DOM 序列化文本，替代纯截图分析
dom_text = dom_state.llm_representation()
# 文本 + 截图双模态，定位准确率大幅提升
```

**收益**：定位准确率提升，不依赖视觉模型，速度更快。

### 4.2 网络请求拦截（CDP Fetch Domain）

**现状**：RodSki 无网络拦截能力，无法 Mock API 响应。

**改进方案**：通过 Playwright 的 `page.route()` 或直接 CDP `Fetch.enable` 拦截请求。

```python
# playwright_driver.py 中新增
def mock_response(self, url_pattern: str, response_body: dict):
    self.page.route(url_pattern, lambda route: route.fulfill(json=response_body))
```

**收益**：支持异常场景测试（网络超时、500 错误、Mock 数据）。

### 4.3 HAR 网络录制

**现状**：RodSki 只有视频录制，无网络请求记录。

**改进方案**：借鉴 Browser-Use 的 `HarRecordingWatchdog`，在测试执行期间录制 HAR 文件。

**收益**：测试报告中附带完整网络请求记录，辅助 debug 接口问题。

### 4.4 页面性能指标

**现状**：RodSki 测试报告无性能数据。

**改进方案**：在 `post_process` 阶段通过 CDP `Performance.getMetrics` 采集性能指标。

```python
# 通过 Playwright CDP session
cdp = await self.page.context.new_cdp_session(self.page)
metrics = await cdp.send("Performance.getMetrics")
# 写入测试报告
```

**收益**：测试报告中加入 FCP、LCP、JS Heap 等性能指标，兼顾功能和性能测试。

### 4.5 自动重连机制

**现状**：RodSki 浏览器断连后测试直接失败。

**改进方案**：借鉴 Browser-Use 的 `_auto_reconnect` 模式，检测到 WebSocket 断连后自动重启浏览器并恢复状态。

**收益**：提升长时间测试的稳定性，减少因浏览器崩溃导致的误报。

---

## 五、总结

RodSki 和 Browser-Use 是**互补而非竞争**的关系：

- **RodSki** 适合：有明确验收标准的回归测试、需要 CI/CD 集成的自动化测试、多平台（Web+Mobile+Desktop）测试
- **Browser-Use** 适合：探索性测试、需要自愈能力的场景、AI Agent 执行复杂任务

最有价值的融合方向是：**用 Browser-Use 的 DOM 感知能力增强 RodSki 的 vision 定位器**，以及**引入 CDP 网络拦截能力扩展 RodSki 的测试场景覆盖**。
