# REQ-012 调试与部分执行 — 验收模块

- 需求：`.pb/requirements/REQ-012-debugging-and-partial-execution-v2.md`（§5 验收清单 37 项）
- 交互/输出约定：`.pb/specs/SPEC-012-user-guide.md`、`.pb/specs/SPEC-012-debugging-design-constraints.md`
- 被测用例模块：[`../debug_partial_execution_targets/`](../debug_partial_execution_targets/)

## 验收方式

每条验收用例只有一步 `run`，调用 `fun/ac_runner.py AC-xxx`。脚本以子进程**真实执行**被测用例
（`rodski run <被测用例> --headless <调试参数>`），并通过 stdin 输入 `c / s / q / Y / 1` 交互，判定依据：

| 依据 | 来源 |
|------|------|
| 执行轨迹 | 被测用例中的 `run mark.py <标签>` 把标签写入 `RODSKI_DEBUG_MARKER` 指向的临时文件——"哪些步骤真的执行了"不依赖框架自报 |
| 是否真的暂停 | 出现断点提示行（含 `[Breakpoint]` 或 `已暂停`）后 2.5 秒内进程仍存活且轨迹不再增长 |
| 结果产物 | 被测模块 `result/` 下本次新生成目录中的 `execution_summary.json`、`execution.log`、`driver_actions.jsonl`、`trace.json`、HTML 报告、截图 |
| 另一个终端 | 暂停期间在另一进程执行 `rodski debug status/queue/objects/context/get-object` |

页面由脚本在 `127.0.0.1:18765` 自动提供（`../debug_partial_execution_targets/fun/pages/`）。
未通过时步骤报错信息中逐项列出 ✅/❌ 检查点、执行的命令和输出末尾。

## 运行

```bash
# 全部 37 条
rodski run rodski-demo/local/debug_partial_execution/case/

# 单组 / 单条（调试验收脚本时直接执行，输出更直观）
rodski run rodski-demo/local/debug_partial_execution/case/ac_a_pause_resume.xml
cd rodski-demo/local/debug_partial_execution/fun && python3 ac_runner.py AC-001
```

被测数据库变更后重建：`python3 rodski-demo/local/debug_partial_execution_targets/data/init_data.py`

## 验收用例清单

被测用例步骤序号均为全局序号（含 pre_process / post_process），见各被测用例注释。

### A. 基础暂停与继续 — `case/ac_a_pause_resume.xml`

| ID | 执行 | 判定 |
|----|------|------|
| AC-001 | `dbg_steps.xml --break-at step:5` → 输入 `c` | 提示含 `Step 5/12` 与 Case；暂停时只执行了第 1~4 步；继续后 12 步全部通过；只暂停 1 次 |
| AC-002 | `dbg_steps.xml --break-at step:9` → 停 10 秒 → `c` | 暂停 10 秒期间阻塞；继续后依赖原页面的第 9~10 步通过；全程只启动一次浏览器 |
| AC-003 | `dbg_steps.xml --break-at step:5` → `s` | 第 5 步未执行且 summary 为 skipped，其余步骤通过；终端提示跳过 |
| AC-004 | `dbg_steps.xml --break-at step:5` → `q` | 第 5 步起都未执行；终端提示中止；summary 无第 5~12 步通过记录 |
| AC-005 | `dbg_steps.xml --break-at step:3,step:7,step:11` | 依次在 3/7/11 暂停，每次暂停时轨迹正确；共 3 次 |

### B. 多层级断点 — `case/ac_b_breakpoint_levels.xml`

| ID | 执行 | 判定 |
|----|------|------|
| AC-006 | `dbg_biz.xml --break-at node:fill_vin` | 两次调用 debug_flow 各在 fill_vin 节点前暂停（共 2 次），轨迹位置正确 |
| AC-007 | `dbg_biz.xml --break-at flow:F_INVOICE_PLATFORM` | 在 invoice_flow 第一个节点前暂停 1 次 |
| AC-008 | `dbg_steps.xml --break-at scenario:S002` | S001 全部完成、S002 未开始时暂停 |
| AC-009 | `dbg_steps.xml --break-at driver:click` | 两次 type 中的 click 各暂停 1 次；提示含 click 与 loginBtn |
| AC-010 | `dbg_rows.xml --break-at batch:row:3` | 前 2 行完成、第 3 行未开始；提示含 row 3 与 USER003 |
| AC-011 | `dbg_biz.xml --break-at business_call:call_again.node:fill_vin` | 只在第三次调用（call_again）的 fill_vin 前暂停，同名节点在 call_main 中不命中 |

### C. 部分执行 — `case/ac_c_partial_execution.xml`

| ID | 执行 | 判定 |
|----|------|------|
| AC-012 | `dbg_marks.xml --start-from 6` | 只执行 m6~m10；第 1~5 步 skipped 且原因含 start-from；终端提示跳过 |
| AC-013 | `dbg_biz_from.xml`（`business_call start_from="submit"`） | 只执行 submit/confirm 节点；调用通过；open/fill_vin 记录为 skipped |
| AC-014 | `dbg_biz_to.xml`（`stop_at="fill_vin"`） | 只执行 open/fill_vin；submit/confirm 记录为 skipped |
| AC-015 | `dbg_biz_range.xml`（`start_from="fill_vin" stop_at="submit"`） | 只执行 fill_vin/submit |
| AC-016 | ① `dbg_steps.xml --break-at step:9` → `q`；② `dbg_steps.xml --start-from 9` → `Y` | ② 提示"检测到现有浏览器对象 DBG_STEPS.browser_obj_1 … [Y/n]"；复用后第 9~10 步在原页面通过 |
| AC-017 | `dbg_needs_browser.xml --start-from 3` → `1` | 提示对象缺失并给出 [1] 中止 / [2] 继续；选 1 后退出码非 0、无步骤执行 |
| AC-018 | `dbg_steps.xml --group grp_second` | 只执行 S002（s8 执行、S001 的 s3/s5/s7 未执行，步骤记录中无 S001）；S002 的 run/type/verify 全部通过 |

### D. 单步执行 — `case/ac_d_step_mode.xml`

| ID | 执行 | 判定 |
|----|------|------|
| AC-019 | `dbg_marks.xml --step-mode`，每次 `c` | 至少暂停 9 次；相邻两次暂停之间恰好执行 1 步；最终全部执行 |
| AC-020 | `dbg_marks.xml --step-mode`，第 4 步前输入 `s` | m4 未执行、其余执行；summary 第 4 步 skipped |
| AC-021 | `dbg_driver.xml --step-mode --driver-level` | type 步骤内按驱动动作暂停 ≥3 次，提示中出现 fill 与 click |

### E. 驱动级别控制 — `case/ac_e_driver_control.xml`

| ID | 执行 | 判定 |
|----|------|------|
| AC-022 | `dbg_driver.xml --break-at step:4`，暂停时 `rodski debug queue [--filter pending/failed]` | 队列含 find_element/fill/click、≥4 个 ✅、耗时 ms；pending 过滤不含已完成项；failed 过滤可用 |
| AC-023 | `dbg_driver.xml --break-at driver:fill` | 两次 fill 各暂停 1 次，分别指向 username / password |
| AC-024 | `dbg_driver.xml` | 生成合法 `driver_actions.jsonl`：字段齐全、seq 连续、含 navigate_to/find_element/fill/click、context 含 case/phase/step；execution.log 含 `[DriverAction]` |
| AC-025 | `dbg_driver_fail.xml`（预期失败） | jsonl 中有 status=failed 的动作，参数含 missing_button、有 error 与 Case/步骤上下文；有 `driver_action_<seq>_failed.png`；日志显示 `[Driver Action #<seq>] … 失败` |
| AC-026 | `dbg_driver.xml --trace --report html` | jsonl duration_ms 均为数值；生成 trace.json；HTML 报告包含驱动动作与最慢动作统计 |

### F. 对象生命周期 — `case/ac_f_object_lifecycle.xml`

| ID | 执行 | 判定 |
|----|------|------|
| AC-027 | `dbg_steps.xml --break-at step:9`，暂停时 `rodski debug objects` → `c` | 对象池含 `DBG_STEPS.browser_obj_1`、alive、当前 URL；继续后第 9~10 步通过且未新建浏览器 |
| AC-028 | `dbg_driver.xml` 连续完整执行两次 | 每次提示"新建浏览器对象 DBG_DRIVER.browser_obj_N … rodski debug get-object"，两次对象名不同 |
| AC-029 | `dbg_multi.xml --break-at step:3`（`launch id=` + `target=`） | 对象池同时有 buyer_browser / seller_browser 及各自 URL；target 指定对象的 type/verify 通过 |
| AC-030 | `dbg_driver.xml --break-at step:4` → `c` | 暂停时对象仍 alive；结束后日志 `[Object] DBG_DRIVER.browser_obj_N closed (total lifetime: Ns)` |

### G. 执行查看与日志 — `case/ac_g_inspect_and_logs.xml`

| ID | 执行 | 判定 |
|----|------|------|
| AC-031 | `dbg_steps.xml --break-at step:5`，`rodski debug status` | 显示 DBG_STEPS、5/12、暂停状态、完成/待执行统计 |
| AC-032 | 同上，`rodski debug context` | 显示 Return[-1]/Return[-2]、第 3 步真实返回值 s3、GlobalValue（含 Site.URL 真实值）、scenario S001 |
| AC-033 | 同上，`rodski debug get-object DBG_STEPS.browser_obj_1` | 显示 URL、状态、Python 访问示例 `get_object(`；不存在的对象返回非 0 |
| AC-034 | `dbg_biz.xml` | execution.log 含 Case/Phase/BusinessCall/Flow/Node/Step/DriverAction 各层级、完成耗时 `(Nms)`、DriverAction 缩进；同时生成 jsonl |

### H. 与数据驱动联动 — `case/ac_h_data_rows.xml`

数据行只由调试命令动态指定（`--rows <data_id>`、`batch:row:N`），被测用例 `dbg_rows.xml` 用现有 `<loop>` 逐行 `type`，不新增 XML 语法。

| ID | 执行 | 判定 |
|----|------|------|
| AC-035 | `dbg_rows.xml --rows USER003 --break-at driver:fill`，暂停时 `rodski debug context` | 提示含 Row 与 USER003；只执行 USER003 行；context 显示 `${ROW.*}` |
| AC-036 | ① `--rows USER003 --break-at step:3` → `q`；② `--rows USER003 --start-from 3` → `Y` | ② 提示"检测到数据行 USER003 上次执行到 Step 2 … [Y/n]"；复用浏览器，第 3 步 verify 在原页面通过 |
| AC-037 | `dbg_rows.xml` | 10 次 fill 的 context 记录 row 1~5 与对应 data_id；按 row==2 过滤只得到 USER002 |

## 前置缺陷（v11.8.1 已修复）

- `<loop var="i">` 的 `${i}` 在 `data` 属性中不被替换 → 曾阻塞 AC-010、AC-035~037。
- `TEST_CASE_WRITING_GUIDE.md` 曾写 `range="1,5"` 表示 1 到 5，实际为列表 `[1, 5]`；文档已改为 `1-5`。
- `--group` 选择 scenario 时整条用例被标记为跳过 → 曾导致 AC-018 失败。
