# Checkpoint 切分与 verify 写法

把一条完整流程切成「① 跑到目标页 → ② Agent 接管 → ③ RodSki 继续 verify」，两个 XML case
各守一边。核心纪律：**part1 到 checkpoint 即停，part2 只做断言**。

## part1：跑到 checkpoint 即停

- 只放「进入目标页 + 前置登录」这类稳定步骤，用 `type Model DataID` 批量做。
- **不要以 `close` 结尾**：`--cdp` 下 executor 结束 driver 仅断连，页面/登录态留在共享 context。
- 不改被测站会导致 part2 失效的状态（登录不算，登出/重置算）。

```xml
<test_step action="navigate" model="" data="http://localhost:8000/"/>
<test_step action="type" model="LoginForm" data="L001"/>
<!-- 到这里是自然 checkpoint：页面停在已登录 dashboard，浏览器保活 -->
```

## part2：只做断言

- 用 `verify Model DataID match_mode="subset"`：只验 Agent 会改动的字段，不要求全表一致。
- 期望值 = Agent 操作后的**确切界面文本**（先跑一次看实际渲染，再写死期望）。
- 字段不想校验就填 `BLANK`（UI 期望 BLANK = 跳过该字段）。

```xml
<!-- TakeoverForm_verify 表：formResult='提交成功！用户名: 接管人角色: admin'，其余 BLANK -->
<test_step action="verify" model="TakeoverForm" data="V001" match_mode="subset"/>
<!-- Dashboard_verify 表：totalOrders=3 completedOrders=2 pendingOrders=1（登录态判据） -->
<test_step action="verify" model="Dashboard" data="V001"/>
```

## 互补断言：防「空洞通过」

单验 Agent 写入值还不够——part2 可能**自己重做一遍 Agent 动作**来造假；单验登录态也不够——
part2 可能**自己登录后**再操作。所以要两条互补：

| 断言 | 排除的假通过 |
|------|-------------|
| 验 Agent 写入的字段（`#formResult`） | 排除「part2 另起炉灶、完全没看到 Agent 操作」 |
| 验登录/会话态（dashboard 卡片） | 排除「part2 重新登录后自己操作表单」 |

两者都 PASS，才证明「接管真的作用于共享会话」。

## 数据表最小自包含示例（model + data 行）

Model（`model/model.xml`）：

```xml
<model name="TakeoverForm">
  <element name="formResult" type="web">
    <location type="id">formResult</location>
  </element>
</model>
```

verify 数据行（`data.sqlite` 中 `TakeoverForm_verify` 表）：

| data_id | formResult | 其余字段 |
|---------|-----------|---------|
| V001 | 提交成功！用户名: 接管人角色: admin | BLANK |

> `subset` 模式下 `_verify` 表声明的字段就是要验的全部；同一逻辑表所有行字段集合必须一致
> （v6.7.6 起），新增字段要么给值要么显式 BLANK。

## 先跑一遍，再固化期望

Agent 段的界面文本（弹窗/提示词格式）易受被测站版本影响。第一次联调时先让 Agent 段
`print(page.text_content(...))` 输出实际值，把输出原样写进 `<Model>_verify` 表，再固化进 XML。
