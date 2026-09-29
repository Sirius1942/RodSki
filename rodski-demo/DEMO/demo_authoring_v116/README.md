# demo_authoring_v116 — AI 编写契约、断言可靠性与执行性能验收

设计：`.pb/specs/v11.6.0-ai-authoring-and-performance-design.md`（§9.1）
来源：AI 写用例对比实验（Playwright+pytest+PO vs RodSki）暴露的问题。
配套夹具：`../demo_authoring_v116_pitfalls/`（复现错误写法，供 lint / 兼容性验收）、`../demo_authoring_v116_no_retry/`（`AutoWait=0`）。

## 运行

```bash
source .venv/bin/activate
python3 rodski-demo/DEMO/demo_authoring_v116/run_acceptance.py        # 全部（19 项）
python3 rodski-demo/DEMO/demo_authoring_v116/run_acceptance.py V04    # 单项
```

脚本会在 `127.0.0.1:8766` 以 `fun/site/` 为根目录启动本地站点（登录态验收需要真实的 http origin），再真实调用 `rodski` 并断言。单独手工跑 UI 用例时，需要先自行启动该站点：

```bash
cd rodski-demo/DEMO/demo_authoring_v116/fun/site && python3 -m http.server 8766
```

## 验收项

| 编号 | 用例 | 能力 |
|------|------|------|
| V01 | `case/ui/assert/async_table.xml` | `$count` / `$exists` 原生断言 + `verify` 自动重试（用例不含 `wait`） |
| V02 | `case/negative/silent_pass_guard.xml` TC001 | 改版后选择器失效 → 断言必须失败（`expect_fail`），报期望 10 / 实际 0 |
| V03 | `case/ui/assert/page_info.xml` | `page` 定位类型断言 path / title |
| V04 | `case/ui/dialog/dialog.xml` | `dialog` 页面元素：accept / dismiss / `accept:文本`，弹窗文本可 verify |
| V05 | `case/negative/silent_pass_guard.xml` TC002 | `DialogPolicy=fail` 下未预期弹窗立即失败并报告文本 |
| V06 | `case/ui/iframe/pay_iframe.xml` | `<location frame="...">` 定位 iframe 内元素 |
| V07 | `case/ui/evaluate/evaluate_file.xml` | `evaluate file:fun/js/check_rows.js`（脚本含 `&&`） |
| V08 | `case/db/db_contract.xml` | 11.5.2：SQL 时间字面量、`sql=BLANK` 回落（防回退） |
| V10 | `case/ui/auth/auth_state.xml`（`--session-mode shared_browser`） | `save_auth_state` / `use_auth_state`；shared_browser 下用例隔离、浏览器只启动一次 |
| V12 | `case/`（`--workers 4`） | 并行结果与顺序一致，镜像目录无冲突 |
| V13 | `--report junit` | `junit.xml` |
| V14 | `rodski case lint` | 对夹具模块报出 6 类规则 |
| V15 | `rodski data set` | 修改期望值后直接重跑 |
| V16 | `--evidence concise` | 简洁记录模式：只保留失败截图，录像不受影响 |
| V17 | 夹具 `WaitTime=1` | 等待单位统一毫秒，旧值按秒兼容并告警 |
| V18 | `rodski capabilities` / skills | `pitfalls` 字段与「契约速查」 |
| **V19** | `case/ui/wait/dynamic_wait.xml` | **动态等待正向**：延迟出现、状态变化（读最新值）、逐条追加计数、多字段同时满足、遮罩消失、隐藏变可见；均不写 `wait`，满足即结束（单用例 < 5.5s） |
| **V20** | `case/negative/dynamic_wait_boundary.xml` | **动态等待边界**：超过 `AutoWait` 必须失败且在超时附近结束（4~15s）；DB `verify` 不重试、立即失败（< 3s） |
| **V21** | `../demo_authoring_v116_no_retry/` | `AutoWait=0` 关闭自动重试 |

### 动态等待测试页 `fun/site/dynamic_wait.html`

| 元素 | 时间线（自页面加载起） | 验证点 |
|------|------------------------|--------|
| `lateText` | 1500ms 出现「数据已加载」 | 延迟出现的文本 |
| `status` | 「处理中」→ 2000ms「已完成」 | 轮询读取最新值，不能停在第一次读到的值 |
| `items` | 每 250ms 追加一条，2500ms 满 10 条 | `$count` 在中途 1~9 条时不判通过 |
| `fieldA` / `fieldB` | 1000ms / 2500ms 变为期望值 | 同一次读取中所有字段同时满足 |
| `spinner` | 2000ms 从 DOM 移除 | `$exists: false` 等待消失 |
| `hiddenBtn` | 1500ms 由隐藏变可见 | `$visible: true` |
| `veryLate` | 20000ms 才出现 | 超过 `AutoWait` 必须失败且不卡死 |

`data/globalvalue.xml` 中 `WaitTime` 按毫秒（v11.6.0 起），显式声明了 `AutoWait`、`DialogPolicy`、`EvidenceMode` 的默认值作为示范。
