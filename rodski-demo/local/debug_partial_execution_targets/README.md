# REQ-012 被测用例模块

供 [`../debug_partial_execution/`](../debug_partial_execution/) 的验收脚本以子进程执行；不带调试参数时都是可独立运行的普通用例。

| 用例文件 | Case | 用途 |
|----------|------|------|
| `case/dbg_steps.xml` | DBG_STEPS | 12 步、两个 scenario（S001/grp_login、S002/grp_second），断点/跳过/中止/部分执行基准 |
| `case/dbg_marks.xml` | DBG_MARKS | 10 个纯标记步骤，无浏览器（start-from、单步） |
| `case/dbg_driver.xml` | DBG_DRIVER | type 展开为驱动原子动作（driver 断点、队列、日志、对象） |
| `case/dbg_driver_fail.xml` | DBG_DRIVER_FAIL | **预期失败**：定位不存在的 `missing_button`（失败定位） |
| `case/dbg_rows.xml` | DBG_ROWS | `<loop>` 逐行 type USER001~005（数据行断点/过滤） |
| `case/dbg_biz.xml` | DBG_BIZ | 三次 business_call：debug_flow → invoice_flow → debug_flow |
| `case/dbg_biz_from.xml` / `_to.xml` / `_range.xml` | DBG_BIZ_FROM / TO / RANGE | business_call 的 `start_from` / `stop_at`（需扩展 case.xsd） |
| `case/dbg_needs_browser.xml` | DBG_NEEDS_BROWSER | 第 3 步依赖第 1 步创建的浏览器（对象缺失检测） |
| `case/dbg_multi.xml` | DBG_MULTI | `launch id=` + `target=` 双浏览器（需扩展 case.xsd） |

- `fun/mark.py <标签>`：把标签写入 `RODSKI_DEBUG_MARKER` 指向的文件（验收脚本设置），并回显为步骤返回值。
- `fun/pages/`：被测页面；手动运行前执行 `python3 fun/serve_pages.py`（端口 18765，与 `data/globalvalue.xml` 的 `Site.URL` 一致）。
- `data/init_data.py`：重建 `data/data.sqlite`。
- 全量回归时 `DBG_DRIVER_FAIL` 失败属预期；`dbg_biz_from/to/range.xml`、`dbg_multi.xml` 在 case.xsd 扩展前无法通过校验。
