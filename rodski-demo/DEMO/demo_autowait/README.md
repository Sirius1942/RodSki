# demo_autowait — v11.7.0 自动等待（AutoWait）统一接管元素查找验收

设计：`.pb/specs/v11.7.0-autowait-unified-design.md`（§4.1 / §4.2）
基线：`.pb/iterations/iteration-65/baseline.md`

配套边界模块：`../demo_autowait_zero/`（不设置 `AutoWait` = 不自动等待）、`../demo_autowait_long/`（`AutoWait=12000`）。
本模块的 `data/globalvalue.xml` 显式写 `<var name="AutoWait" value="5000"/>`。
AutoWait **没有默认时长**（v11.7.1）：不设置或写 `0` 都表示不自动等待，要自动等待必须显式写时长。

## 运行

```bash
python3 rodski-demo/DEMO/demo_autowait/run_acceptance.py            # 全部 W01~W30
python3 rodski-demo/DEMO/demo_autowait/run_acceptance.py W11 W17    # 指定编号
```

脚本在 `127.0.0.1:8767` 以 `fun/site/` 为根目录起静态服务（三个模块共用），逐项真实调用
`rodski run <用例文件> --case-id <ID> --headless --trace`，断言结果、**步骤级**耗时窗口
（从 `trace.json` 的 `keyword.*` span 读取，扣除浏览器启动与 navigate）与错误信息
（须含 `AutoWait=<ms>` 与元素名）。手工单跑用例时先自行起站点：

```bash
cd rodski-demo/DEMO/demo_autowait/fun/site && python3 -m http.server 8767
```

数据只在 `data/data.sqlite` 中（同表字段集合一致，缺字段显式 `BLANK`）。
`fun/build_data.py` 是三个模块 `data.sqlite` 的可复现生成器；增删改行也可直接用
`rodski data add-row / set / delete-row`。

## 测试站点 `fun/site/`（`?d=毫秒` 控制延迟，`d<0` 表示永不发生）

| 页面 | 时间线 | 自证机制 |
|------|--------|---------|
| `late_input.html` | 输入框 d 后插入 | 输入实时回显 `#echo` |
| `late_button.html` | 按钮 d 后插入 | 点击计数 `#clickCount`（证明只点一次） |
| `disabled_button.html` | 按钮 disabled，d 后 enabled | 结果 + 计数 |
| `overlay.html` | 全屏遮罩（`pointer-events:auto`）d 后移除 | 按钮计数 / 遮罩拦截计数；force/JS 点击才会绕过遮罩 |
| `hidden_button.html` | 按钮 `display:none`，d 后显示 | 计数 |
| `async_select.html` | option d 后异步填充；`?sd=` 控制 select 本身出现时间 | `#selected` |
| `late_hover.html` | 悬停目标 d 后出现 | mouseenter → `#menuState=已展开` |
| `late_dblclick.html` / `late_contextmenu.html` | 目标 d 后出现 | dblclick / contextmenu 计数 |
| `late_iframe.html` + `frame_inner.html` | iframe d 后插入 | frame 内回显 |
| `chain_form.html` | A 于 d 出现；输入 A 后 d 出现 B；点 B 后 d 出现 C | `#chainResult` + B/C 点击计数 |
| `multi_locator.html` | `#realBtn` d 后出现（模型第 1 个 location 永不命中） | 计数 |
| `late_get.html` | 文本 d 后出现，参考值立即显示 | verify 参考值 = `${Return[-1].lateValue}` |
| `late_clear.html` | 预填输入框 d 后出现 | `#clearEcho=值:[...]` |
| `late_upload.html` | file input d 后出现 | `#fileName` |
| `ready.html` | 全部立即就绪（10 字段） | `#summary` 汇总 |

## 验收项

| 编号 | 模块 / 用例 | 断言 |
|------|------------|------|
| W01–W10 | `case/positive/late_elements.xml` TC001–TC010 | 输入 / click / disabled / 遮罩 / 隐藏 / select / hover / double_click / right_click / iframe，d=2s，通过且 type 步骤 ≤4.5s |
| W11 | `case/positive/chain_form.xml` | 一行 type A/B/C 通过，type 步骤 ∈ [9, 13.5]s（逐字段独立计时） |
| W12 | `case/positive/multi_locator.xml` | 通过，type 步骤 ∈ [1.5, 4.0]s（≈ d，不是 AutoWait + d） |
| W13–W15 | `case/positive/read_keywords.xml` | get / clear / upload_file，d=2s，通过且步骤 ≤4.5s |
| W16 | `case/positive/ready.xml` | 10 字段 type ≤2.5s（G4 命中即走） |
| W17–W22 | `case/negative/late_20s.xml` | click / 输入 / select / hover / get / clear 对 20s 元素失败，耗时 ∈ [4.5, 7.5]s，错误含 `AutoWait=5000` + 元素名 |
| W23 | `case/negative/overlay_never.xml` | 遮罩永不移除 → click 失败（无 force/JS 降级），同上窗口与错误信息 |
| W24 | `case/negative/multi_locator_miss.xml` | 两个 location 全不命中 → ≈1 × AutoWait 失败 |
| W25–W27 | `../demo_autowait_zero/case/autowait_zero.xml` | 不设置 `AutoWait`（= 不自动等待）：1.5s 元素 click / 输入 <1.5s 失败（含 `AutoWait=0`）；就绪元素通过 |
| W28–W30 | `../demo_autowait_long/case/autowait_long.xml` | `AutoWait=12000`：8s 元素 click / 输入通过；20s 按钮失败耗时 ∈ [11.5, 14.5]s（含 `AutoWait=12000`） |

UI 原子动作（click / select【值】/ hover / double_click / right_click）只写在 type 数据表字段值中；用例中没有任何 `wait` 步骤。
