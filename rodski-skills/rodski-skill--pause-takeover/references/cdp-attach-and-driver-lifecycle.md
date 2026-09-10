# CDP 附加与 Driver 生命周期（RodSki v11.1.0+）

`rodski run --cdp` / `PlaywrightDriver(cdp_endpoint=...)` 让 RodSki 不再自己 `launch` 浏览器，
而是 **connect_over_cdp 到外部已启动的远程调试浏览器**，复用其默认 context 与页面状态。

## driver 语义：owning vs attached

| | owning（默认，无 --cdp） | attached（--cdp） |
|---|---|---|
| 浏览器来源 | `chromium.launch(...)`，driver **拥有**浏览器 | `chromium.connect_over_cdp(endpoint)`，driver **不拥有** |
| `close()` 行为 | 关 context + 关 browser + `_pw.stop()`（全部释放） | **只** `browser.close()`（= 断连）+ `_pw.stop()`；**不** `context.close()` |
| 为什么 | driver 独占，随手清理 | context/页面属于外部（用户/AI/上个 run），`context.close()` 会真关页面 → 毁掉保留状态 |
| headless/browser | 生效 | **不生效**（由远端浏览器决定） |

关键点：`connect_over_cdp` 返回的 `browser.close()` 在 Playwright 语义下只是**断开 CDP 连接**，
不会关闭用户启动的 Chrome；但 `context.close()` 是**真关**那个 context（连带页面）——所以
attached driver 的 `close()` 必须跳过 `context.close()`。实现见
`rodski/drivers/playwright_driver.py::_attach_cdp_browser` 与 `close()`。

## 为什么 part2 能见到 Agent 的状态（跨进程成立）

```
进程 A（run-1）  PlaywrightDriver(cdp) ──connect──▶  共享 Chrome (CDP :9222)
                 登录 → dashboard；close() 只断连 ────────▶ 页面/登录态仍留在 context
进程 B（Agent）  playwright.connect_over_cdp            ◀── 读到已登录 dashboard → 操作
进程 C（run-2）  PlaywrightDriver(cdp) ──connect──▶  同一 context 同一 page → verify
```

A / B / C 是三个独立 Python 进程，零共享状态；唯一通路就是 CDP 指向的**同一个浏览器进程**。
所以 run-2 读到 Agent 写入的 DOM、登录态 → 只能来自「共享浏览器真的被延续」。

## 页面与 context 复用规则

- 取 `browser.contexts[0]`（外部 Chrome 的默认 context）；有页面取 `pages[0]`，context 无页才 `new_page()`。
- 多个客户端**串行** connect；不要并发操作同一个 page（CDP target 冲突）。
- 同一进程内不要嵌套两次 `sync_playwright()`（`Sync API inside asyncio loop`）；共用一个实例或用子进程。

## 何时触发 browser.contexts 为空 / 需要 new_page

外部 Chrome 若被清空 context（全部标签关闭），`contexts[0].pages` 为空——driver 自动 `new_page()`
兜底。但那会是**新空白页**（登录态/跳转历史已丢），属预期：接管前提是共享浏览器进程一直活着、
默认 context 没被清空。

## CLI 归一化

`--cdp :9222` → `http://127.0.0.1:9222`；`--cdp localhost:9222` 同理；已带 scheme 原样透传。
