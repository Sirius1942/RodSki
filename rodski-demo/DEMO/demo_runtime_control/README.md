# demo_runtime_control

演示 **运行时控制队列**（`RuntimeCommandQueue`）：在固定测试步骤执行过程中，于**步骤边界**
执行**暂停 / 恢复 / 插入**（与《核心设计约束》§8.6–8.7 一致）。

`case/runtime_case.xml` 含 3 个用例：

| case | 演示 | 固定步骤 | 运行时控制 |
|------|------|---------|-----------|
| `RT_INSERT` | 步骤边界插入 | `navigate about:blank` → `wait 1` | 在 `wait 1` 执行中 insert `wait 0.2` |
| `RT_PAUSE` | 暂停 / 恢复 | `navigate about:blank` → `wait 0.2` → `wait 1` | navigate 后 pause，确认无新步骤启动，再 resume |
| `RT_PAUSE_INSERT` | 暂停期间插入 | 同上 | navigate 后 pause，暂停期间 insert `wait 0.2` ×3，再 resume |

## 行为说明

- 所有运行时命令（pause / resume / insert）都**排入队列，在步骤边界生效**：
  - `pause`：当前步骤执行结束后停住执行流，不再继续后续步骤，直到 `resume` 或 `terminate`。
  - 暂停期间**不会启动任何新步骤**，但控制队列**仍被周期性消费**，因此暂停期间可继续
    `resume` / `insert` / `terminate`。
  - `resume`：解除暂停，执行流从下一固定步骤继续。
  - `insert`：在 `resume` 后**先执行插入的步骤**（排到队首），再回到剩余固定步骤。
- `run_demo.py` 用一个挂在 `before_keyword` 的**步骤日志** + 控制器线程轮询
  `rq.wait_unpaused()`（返回 `False` 即暂停已生效）来验证：
  暂停生效后开一个观察窗，若未真正暂停，剩余 wait 步会在窗口内启动、日志长度增长；
  断言窗口内日志长度不变 + 各用例最终 `PASS` + 插入步骤顺序正确，避免"空洞通过"。

## 运行

在仓库根目录（`RodSki/`）下：

```bash
python3 rodski-demo/DEMO/demo_runtime_control/run_demo.py
```

预期输出：三个用例均 `PASS`，控制器打印 `pause 生效于 t=…`、`观察窗内无新步骤启动 → resume` 等证据行。

依赖：已安装 Playwright 浏览器（与主项目一致）。

## 裸 CLI 运行注意

`rodski run rodski-demo/DEMO/demo_runtime_control/case/` 在未加 `--insert-steps` 时**不会注入任何
运行时控制命令**（CLI 仅在 `--insert-steps` 时才创建 `RuntimeCommandQueue`），因此三个用例都会
自然执行到结束并 `PASS`，不会挂起。暂停/恢复语义验证只发生在 `run_demo.py`（其控制器线程才
会 `pause()/resume()`，并通过观察窗断言暂停确实停住了执行流）。
