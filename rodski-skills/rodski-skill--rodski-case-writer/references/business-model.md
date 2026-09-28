# RodSki 业务模型（Business Model）编写规则

当任务涉及 `business/*.xml`、`<business_call>`，或一个业务存在多条分支路径（成功 / 失败 / 异常）需要按场景法逐条覆盖时使用本文。完整契约以 `TEST_CASE_WRITING_GUIDE.md` 第 17 章（业务模型）、`business.xsd` 和当前 `rodski business --help` 为准。

## 何时用业务模型

- 适合：同一业务入口按真实结果分叉成多条路径（登录成功/凭据错误/锁定、提交通过/校验失败/超限等），且希望每条路径都有稳定 ID、可看图、可统计覆盖率。
- 不适合：只有一条直线流程、只是几个步骤的复用，或需要循环/回退的流程（业务图必须是无环图）。这些场景写普通 Case 步骤即可。

## 资产分工

| 资产 | 写什么 | 不写什么 |
|---|---|---|
| `business/*.xml` | 节点、节点步骤、条件边、flow 路径 | 字段定义、账号密码、URL、端口 |
| `model/model.xml` | 节点步骤引用的 UI/接口/DB 模型 | 业务分支 |
| `data/data.sqlite` | 表 `B`（输入）和 `B_verify`（期望，可含 `expected_path`） | 业务专用元表、flow 表 |
| `case/*.xml` | `<business_call ref flow input expect>` | 边条件、路径控制 |

`B` 即 `business_model@id`。

## 编写顺序

1. 盘点模块：`rodski business list <module>`；已有模型先 `rodski business graph <module> --id <B> --format mermaid` 看图。
2. 画图：一个入口 → 动作节点 → 判定节点 → 若干终点。判定字段必须来自真实输出（接口响应字段、`auto_capture` 捕获值等）。
3. 写 XML：
   - 节点步骤用普通 `<test_step action model data>`，关键字仍是 SUPPORTED 列表中的那些；输入行用 `data="${Business.InputDataID}"`，框架会把输入表中与模型元素同名的字段投影给该模型。
   - 多条出边时每条都写 `condition`，互斥且覆盖全部可能结果；条件变量写 `${Business.Actual.<字段>}`。
   - 每条合法路径一个 `<flow>`，至少一条 `type="basic"`，其余用 `alternative` / `exception` / `boundary`；`path` 用 `&gt;` 连接节点 ID，从入口到终点。
4. 校验：`rodski business validate <module> --id <B>`。
5. 数据：用 `rodski data` 命令在 `data.sqlite` 建 `B`、`B_verify` 两张普通表；每条 flow 准备一对 DataID（建议输入/期望同名）。`B_verify` 中每个字段都会与实际输出比较，`expected_path` 与实际路径比较。
6. Case：每条 flow 一个 Case：

```xml
<case execute="是" id="TC-BM-XXX-OK" title="xxx 基本流">
  <test_case>
    <business_call id="xxx_ok" ref="B" flow="F_XXX_OK" input="XXX_OK_01" expect="XXX_OK_01"/>
  </test_case>
</case>
```

7. 运行：`rodski run <module>/case/<file>.xml`；需要时 `rodski business debug <module> --id B --flow F --input D --expect V` 单独调试（不计入正式结果）。
8. 覆盖：`rodski business coverage <module> --id B`，节点/边/flow 应覆盖到计划范围。

## 条件表达式

白名单：`==` `!=` `<` `<=` `>` `>=` `in` `not in` `and` `or` `not`，字符串/数字常量，`${Business.Actual.<字段>}`。不支持函数调用、下标、算术、任意 Python。运行时每个节点的出边必须**恰好命中 1 条**。

## 常见错误

| 现象 | 原因 / 处理 |
|---|---|
| 写成 `<test_step action="business_call">` | `business_call` 是 Case 元素，不是关键字 |
| `business_call` 缺属性被 XSD 拒绝 | `ref`、`flow`、`input`、`expect` 四个都必填 |
| `graph must have exactly one start node` | 有多个无入边节点，或孤立节点 |
| `every branch from X needs a condition` | 多出边中有无条件边 |
| `expected exactly one matching edge, got 0/2` | 条件未覆盖实际值，或条件不互斥；检查实际输出字段名和取值 |
| `Path mismatch` | 输入真实触发了另一条路径：修数据或修 flow 选择，**不要**改边条件去迁就 |
| `Field 'x': expected ..., got None` | `B_verify` 中字段在实际输出里不存在；检查模型 `auto_capture` / 响应字段名 |
| `Missing data table 'B_verify'` | 表名必须与 `business_model@id` 严格一致 |

## 禁止事项

- 不要在 `business.xml` 里写字段、账号、端口、URL。
- 不要用 `flow` 或伪造的 `evaluate` 输出强制走某条边。
- 不要把 `business debug` 的结果当作正式验收结果。
- 不要为业务模型新增关键字或数据表类型。
