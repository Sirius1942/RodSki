# demo_runtime_control

演示 **运行时控制队列**（`RuntimeCommandQueue`）：在固定测试步骤执行过程中，于**步骤边界**插入额外步骤（与 `case/*.xml` 中 `test_step` 同构）。

## 行为说明

- 用例固定为：`navigate about:blank` → `wait 1s`。
- 后台线程在约 0.25s 后向队列提交 **insert**：再执行一次 `wait 0.2s`。
- 根据设计约束 §8.7：insert 在**当前步（此处为 1s wait）结束之后**才会被处理，因此总执行序列为三步。

## 运行

在仓库根目录（`RodSki/`）下：

```bash
python rodski-demo/DEMO/demo_runtime_control/run_demo.py
```

依赖：已安装 Playwright 浏览器（与主项目一致）。

## 扩展

- **暂停 / 继续**：对同一 `RuntimeCommandQueue` 调用 `pause()` / `resume()`。
- **优雅终止**：`terminate(force=False)` → 用例状态为 `SKIP`（结果 XSD 兼容）。
- **强制终止**：`terminate(force=True)` → 当前用例 `FAIL`。
