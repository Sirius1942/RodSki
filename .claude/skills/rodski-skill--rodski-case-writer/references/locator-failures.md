# RodSki 定位失败与性能模式

当日志显示定位器超时、严格模式、备用链路缓慢、SKI302、SKI313，或 RodSki UI 运行异常缓慢时使用本文。实时契约仍以 `TEST_CASE_WRITING_GUIDE.md` 为准。

## 先看证据

- 先用 `rodski_result_diagnose.py` 看首个失败，用 `rodski_slow_steps.py` 看慢步骤。
- 使用最新的 `execution.log`、`result.xml`、失败截图，并在需要时查看录像。
- 修复最新运行中的第一个真实失败。避免同时修改大量定位器、等待和期望值。

## 严格模式

- 严格模式表示定位器太宽，不代表页面需要更多等待。
- 缩窄到最深唯一节点、目标表格行/列、弹窗、区块、活动 tab 或业务 ID。
- 避免在大容器上使用 `//*[contains(., 'text')]`；它经常匹配包含混合动态文本的祖先节点。
- 验证时定位稳定文本叶子节点，而不是父级面板。

## 定位器优先级

- 将可靠且命中快的定位器放在最低 priority 值。
- 将已知缓慢或试探性的备用定位器放到稳定定位器之后；如果它们只浪费重试，就删除。
- 除非是有意的临时桥接，否则不要把绝对 XPath 作为 priority 1。
- 如果后面的 fallback 总能在几秒内成功，问题是优先级顺序，不是浏览器速度。

## XPath fallback / querySelector 慢等待

- 日志里出现 `querySelector`、`document.querySelector`、`xpath`、`fallback`、`所有定位器均失败`，且步骤耗时集中在某个 `Model.Element` 时，优先怀疑无效 locator 兜底链路，而不是页面真的慢。
- 先用 `rodski_slow_steps.py --result-dir <result>` 看 `signals`、`edit` 和 `next`；它会把疑似编辑点指向 `model/model.xml::<Model.Element>` 或对应 data row。
- 修复顺序：保留最新运行中已验证秒中的稳定 locator；把稳定 locator 放到最小 priority；删除长期不命中、会进入 JS/querySelector 分支、或只制造等待的 XPath 兜底。
- 重新添加 locator 前必须有证据：现有 model、截图、可访问性树、DOM 探查或上一轮成功日志。不要凭肉眼描述新增宽 XPath。
- 如果第一个问题修完后失败转移到提交/确定，检查是否缺少业务状态等待：例如校验完成行、回填字段、主表新增行或 toast/状态文本。按钮可点击不等于数据已落表。

## 弹窗与重复文本失败

- 将重复按钮和字段限定到当前可见弹窗/对话框内。
- 对包含重复控件的页面区块，用区块标题加控件文本锚定。
- 对活动 tab，在定位器中包含活动 tab/container。
- 对隐藏 radio/checkbox，用稳定 input 属性锚定，但点击可见父节点/label。

## 等待与重试

- 定位器失败后，不要在截图证明元素尚未渲染前添加固定等待。
- 用面向状态的 `verify`、就绪定位器或有界 evaluate 轮询替代机械等待。
- 保持 `step_wait` 较小，只在真实异步边界使用显式等待。
- 连续等待和长等待是风险信号；检查它们掩盖的状态转换。

## 层级映射

- `type` 失败：检查数据行动作值和模型定位器。
- `verify` 失败且 actual 为空：检查模型定位器和页面状态。
- `verify` 失败且 actual 错误：检查 `_verify` 期望值和提取粒度。
- `send` 失败：检查接口 model/data 和认证/session 状态。
- `DB` 失败：检查数据库 model/data 和 globalvalue 连接。

## 性能工作流

- 运行 `rodski_slow_steps.py --result-dir <result>`。
- 对定位器备用链路缓慢，先重排或移除定位器备用链路，再修改等待。
- 对固定等待导致的缓慢，用就绪验证或更窄的 debug plan 替代。
- 对重试导致的缓慢，用失败截图判断元素是缺失、重复、隐藏，还是页面状态错误。
- 对长流程，用 `rodski_checkpoint_plan.py` 生成 step/scenario debug plan，只重跑目标片段。
