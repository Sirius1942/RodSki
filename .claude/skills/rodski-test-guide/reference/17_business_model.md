<!-- 自动生成 from rodski/docs/TEST_CASE_WRITING_GUIDE.md  请勿手工编辑 -->

## 17. 业务模型（Business Model，v11.4.0）

业务模型是基于**黑盒测试场景法**的业务流程图：用节点、条件边描述一个业务的完整分支，用有稳定 ID 的业务流（基本流 / 备选流 / 异常流 / 边界流）固化合法路径。Case 通过 `<business_call>` 选择一条业务流并绑定输入/期望数据，框架按真实业务结果走图，再断言实际路径与期望一致。

> 业务模型不是工作流执行器，也不是用例集合。它只能**嵌套在 Case 中**正式执行；`rodski business` CLI 仅用于列表、校验、看图、覆盖率和调试。

### 17.1 四层职责

| 资产 | 位置 | 负责 |
|------|------|------|
| 业务模型 | `business/*.xml` | 节点、条件边、合法业务流（路径） |
| 执行模型 | `model/model.xml` | 节点步骤引用的 UI / 接口 / DB 模型（与普通 Case 相同） |
| 数据 | `data/data.sqlite` | 业务输入表 `<业务模型id>`、期望表 `<业务模型id>_verify` |
| Case | `case/*.xml` | 测试意图：选哪条 flow、用哪行输入、对照哪行期望 |

### 17.2 目录

```
product/{项目}/{模块}/
├── business/          ← 可选；使用业务模型时才需要
│   └── business.xml   ← 可含多个 business_model；也可拆成多个 *.xml
├── case/  model/  data/  fun/  plan/  result/
```

解析器扫描 `business/` 下全部 `*.xml`，`business_model@id` 在模块内必须全局唯一。

### 17.3 业务模型 XML（`business.xsd`）

```xml
<business_models version="0.1">
  <business_model id="login_flow" name="用户登录流程" version="1">
    <description>登录后按真实响应进入首页、错误提示或锁定提示</description>
    <nodes>
      <node id="open_login" title="开始登录"/>
      <node id="submit_login" title="提交登录">
        <steps>
          <test_step action="send" model="LoginAPI" data="${Business.InputDataID}"/>
        </steps>
      </node>
      <node id="validate_login" title="读取结果"/>
      <node id="home"   title="登录成功"/>
      <node id="error"  title="凭据无效"/>
      <node id="locked" title="账号锁定"/>
    </nodes>
    <edges>
      <edge from="open_login"   to="submit_login"/>
      <edge from="submit_login" to="validate_login"/>
      <edge from="validate_login" to="home"   condition="${Business.Actual.login_status} == 'success'"/>
      <edge from="validate_login" to="error"  condition="${Business.Actual.login_status} == 'invalid_credentials'"/>
      <edge from="validate_login" to="locked" condition="${Business.Actual.login_status} == 'locked'"/>
    </edges>
    <flows>
      <flow id="F_LOGIN_SUCCESS" type="basic"       path="open_login&gt;submit_login&gt;validate_login&gt;home"/>
      <flow id="F_LOGIN_INVALID" type="alternative" path="open_login&gt;submit_login&gt;validate_login&gt;error"/>
      <flow id="F_LOGIN_LOCKED"  type="exception"   path="open_login&gt;submit_login&gt;validate_login&gt;locked"/>
    </flows>
  </business_model>
</business_models>
```

| 元素 / 属性 | 必填 | 说明 |
|-------------|:---:|------|
| `business_models@version` | 是 | 格式版本，当前 `0.1` |
| `business_model@id / name / version` | 是 | `id` 为 NCName，模块内唯一；决定数据表名 |
| `business_model@lifecycle / idempotent` | 否 | 描述性元数据 |
| `node@id` | 是 | 模型内唯一；`title`、`<description>` 可选 |
| `node/steps/test_step` | 否 | 与 Case 的 `test_step` 同一套关键字契约（`action` / `model` / `data`）；无步骤的节点仅作为判定点或终点 |
| `edge@from / to` | 是 | 必须引用本模型已声明的节点；`condition`、`label` 可选 |
| `flow@id / type / path` | 是 | `type` ∈ `basic` \| `alternative` \| `exception` \| `boundary`；`path` 用 `>` 连接节点 ID（XML 中写作 `&gt;`） |

### 17.4 静态校验规则（`rodski business validate`）

- 图必须有且只有 **1 个入口节点**（无入边），且为**无环图（DAG）**，不得有不可达节点或悬空边引用
- 一个节点有多条出边时，**每条出边都必须写 `condition`**；不允许多条无条件出边
- 每个模型**至少 1 条 `basic` 流**
- 每条 flow 的 `path` 至少 2 个节点、不重复，从入口开始，相邻两节点之间必须有边，最后一个节点必须是**终点**（无出边）

### 17.5 条件表达式与变量

边条件是**白名单表达式**，不是 Python，不支持函数调用、下标、算术或任意代码：

- 比较：`==` `!=` `<` `<=` `>` `>=` `in` `not in`
- 逻辑：`and` `or` `not`
- 取值：字符串 / 数字常量，以及下列变量

| 变量 | 可用位置 | 含义 |
|------|---------|------|
| `${Business.InputDataID}` | 节点步骤 `data` | 本次 `business_call@input` |
| `${Business.ExpectDataID}` | 节点步骤 `data` | 本次 `business_call@expect` |
| `${Business.Actual.<字段>}` | 边 `condition` | 已执行步骤产生的实际输出（接口响应字段、`auto_capture` 捕获值等） |

运行时在每个节点后评估出边条件：**必须恰好命中 1 条**，0 条或多条命中都会直接失败，不会默认走第一条边。

节点步骤中 `send` / `type` 的 `data` 为 `${Business.InputDataID}` 时，框架把输入表该行中**与目标模型元素同名的字段**投影给该模型使用，不需要为执行模型再复制一份数据行。

### 17.6 数据表约定

业务模型 `id="B"` 固定对应两张**普通** SQLite 逻辑表，不需要专用元表，也不在业务 XML 中声明字段：

| 逻辑表 | `table_kind` | 内容 |
|--------|--------------|------|
| `B` | `data` | 业务输入字段（如 `username`、`password`） |
| `B_verify` | `verify` | 期望输出字段；可含保留列 `expected_path` |

- Verify 行中每个字段都会与 `${Business.Actual.<字段>}` 逐一比较
- `expected_path` 是保留字段，与实际路径（`a>b>c` 格式）比较
- 字段集合一致性等规则与普通数据表相同（见第 5 章）；仍用 `rodski data` 命令维护

### 17.7 在 Case 中调用：`<business_call>`

```xml
<case execute="是" id="TC-BM-LOGIN-OK" title="登录成功基本流">
  <test_case>
    <business_call id="login_success" ref="login_flow" flow="F_LOGIN_SUCCESS"
                   input="LOGIN_OK_01" expect="LOGIN_OK_01"/>
  </test_case>
</case>
```

| 属性 | 必填 | 说明 |
|------|:---:|------|
| `ref` | 是 | 业务模型 `id` |
| `flow` | 是 | 本 Case 要验证的业务流 `id` |
| `input` | 是 | 输入表 `B` 中的 DataID |
| `expect` | 是 | 期望表 `B_verify` 中的 DataID |
| `id` | 否 | 本次调用 ID，用于结果与日志关联 |

规则：

- `<business_call>` 是 Case 元素，**不是关键字**，不进入 SUPPORTED；可出现在 `pre_process` / `test_case` / `post_process`、`scenario`、`if/elif/else`、`loop` 中
- `flow` 只是**测试目标和断言**，不会强制选边或跳过节点；实际路径由输入数据和真实业务结果决定
- 以下任一情况 `business_call` 失败，Case 随之失败：实际路径 ≠ flow 路径；Verify 字段不一致；边条件未唯一命中；节点步骤执行失败
- 一个 Case 通常只验证一条 flow；覆盖多条路径请写多个 Case（如成功 / 凭据错误 / 账号锁定各一个）

### 17.8 结果与覆盖率

`result.xml` 中 `business_call` 步骤带 `<business_result>` 子元素，记录 `ref`、`flow`、`input`、`expect`、`passed`、实际路径、期望路径、实际/期望字段、各节点步骤输出和断言错误。`rodski business coverage` 只从这些正式结果汇总节点 / 边 / flow 覆盖率。

### 17.9 CLI

```bash
rodski business list      <module>                     # 列出业务模型
rodski business flow-list <module> --id login_flow     # 列出业务流
rodski business validate  <module> [--id login_flow]   # XSD + 图静态校验
rodski business graph     <module> --id login_flow [--format mermaid|json] [--flow F_LOGIN_SUCCESS]
rodski business coverage  <module> [--id login_flow] [--result <result.xml|目录>] [--format text|json]
rodski business debug     <module> --id login_flow --flow F_LOGIN_SUCCESS \
                          --input LOGIN_OK_01 --expect LOGIN_OK_01   # 仅调试，不产生正式结果
```

正式执行仍用 `rodski run <module>/case/...`。完整可运行示例见 `rodski-demo/DEMO/demo_business_model/`。

### 17.10 编写顺序建议

1. 先画业务图：入口 → 动作节点 → 判定点 → 各终点，确认每个分支的判定字段来自真实响应
2. 写 `business/business.xml`，为每条合法路径定义 flow（至少一条 `basic`）
3. 运行 `rodski business validate`，再用 `graph --format mermaid` 目视检查
4. 在 `data.sqlite` 建 `B` / `B_verify` 表，按 flow 准备成对的 DataID
5. 每条 flow 写一个 Case 的 `<business_call>`，运行后用 `business coverage` 检查覆盖

---
