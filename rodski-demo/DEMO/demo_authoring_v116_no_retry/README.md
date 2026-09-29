# demo_authoring_v116_no_retry — AutoWait=0 关闭自动重试

`globalvalue.xml` 设置 `DefaultValue.AutoWait=0`，验证 `verify` 恢复为单次比对（v11.6.0 A2 / Owner 决策 D1 的关闭开关）。

页面为内嵌 `data:` URL，文本 1 秒后才出现。用例为 `expect_fail`：重试被关闭时 verify 立即失败 → 用例判定通过；若重试未被关闭，verify 会在 1 秒后成功 → 用例反而判定不通过。

由 `../demo_authoring_v116/run_acceptance.py V21` 驱动验收。
