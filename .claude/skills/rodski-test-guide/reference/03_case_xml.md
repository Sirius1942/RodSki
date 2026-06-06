<!-- 自动生成 from rodski/docs/TEST_CASE_WRITING_GUIDE.md  请勿手工编辑 -->

## 3. Case XML — 用例编写

### 3.1 文件格式（三阶段容器 + 多 `test_step`）

每个 `<case>` 下有三个**阶段容器**（见 `case.xsd`）：

1. **`<pre_process>`**（可选）— 预处理，内含 **0～n** 个 `<test_step>`
2. **`<test_case>`**（**必选，且每个 case 仅 1 个**）— 用例主体，内含 **至少 1 个** `<test_step>`；v6.3.0 起可混合编排裸 `<test_step>` 与 `<scenario>`
3. **`<post_process>`**（可选）— 后处理，内含 **0～n** 个 `<test_step>`

早期单文件格式中「测试步骤」「预期结果」等多行语义，在 XML 中统一为 **`<test_case>` 内多条 `<test_step>`**（先 `type` 再 `verify` 等，按书写顺序执行）。

```xml
<?xml version="1.0" encoding="UTF-8"?>
<cases tags="smoke,login">
  <case execute="是" id="c001" title="登录测试" description="验证登录"
        component_type="界面" priority="P0">
    <pre_process>
      <test_step action="navigate" model="" data="GlobalValue.DefaultValue.URL/login"/>
    </pre_process>
    <test_case>
      <test_step action="type" model="Login" data="L001"/>
      <test_step action="verify" model="Login" data="V001"/>
    </test_case>
    <post_process>
      <test_step action="close" model="" data=""/>
    </post_process>
  </case>
</cases>
```

### 3.2 属性说明

#### `<cases>` 套件属性

| 属性 | 必需 | 说明 | 取值规则 |
|------|------|------|---------|
| `step_wait` | 否 | 步骤间等待时间（毫秒） | 如 `500`，覆盖 GlobalValue 中的 WaitTime |
| `tags` | 否 | 套件标签 | 逗号分隔，如 `smoke,login`。文件内所有用例共享此标签，CLI 可按标签过滤 |

#### `<case>` 用例属性

| 属性 | 必需 | 说明 | 取值规则 |
|------|------|------|---------|
| `execute` | 是 | 是否执行 | 只有 `是` 才执行，`否` 跳过 |
| `id` | 是 | 用例编号 | 如 `c001`、`c002`，用于日志和结果回填 |
| `title` | 是 | 用例标题 | 用于日志和报告显示 |
| `description` | 否 | 用例描述 | 详细说明（可选） |
| `component_type` | 否 | 测试类别 | `界面` / `接口` / `数据库`（与 `case.xsd` 一致），仅做分类标记 |
| `priority` | 否 | 优先级 | `P0` / `P1` / `P2` / `P3`，CLI 可按优先级过滤 |
| `expect_fail` | 否 | 预期失败 | `是` / `否`（默认 `否`），标记为预期失败的用例失败时不计入 FAIL |

#### `<metadata>` 可选子元素

每个 `<case>` 可包含一个 `<metadata>` 子元素（位于 `<pre_process>` 之前），用于记录用例元信息：

| 属性 | 说明 |
|------|------|
| `created_by` | 创建者 |
| `created_at` | 创建时间 |
| `updated_by` | 最后修改者 |
| `updated_at` | 最后修改时间 |
| `success_rate` | 历史成功率 |
| `last_run` | 最后执行时间 |

```xml
<case execute="是" id="c001" title="登录测试">
  <metadata created_by="agent" created_at="2026-05-20" success_rate="95%"/>
  <test_case>
    <test_step action="type" model="Login" data="L001"/>
  </test_case>
</case>
```

### 3.3 三阶段执行顺序与失败语义

```
预处理（pre_process 内各 test_step）→ 用例（test_case 内各 test_step）→ 后处理（post_process 内各 test_step）
```

| 规则 | 说明 |
|------|------|
| 顺序 | 先执行完 `pre_process` 中所有步骤，再执行 `test_case`，最后执行 `post_process` |
| 预处理失败 | 跳过 **用例阶段**，**仍执行后处理** |
| **用例阶段失败** | **仍执行后处理**（保证 `close`、DB 清理等能跑） |
| 后处理失败 | 整条用例记为失败 |

### 3.4 `scenario` 容器（v6.3.0）

`<scenario>` 是 `<test_case>` 内的步骤分组容器，用于把同一 case 的主链路拆成可命名、可依赖的验收片段。它不替代 `<case>`：一个 case 仍只有一个 `<test_case>`，`<scenario>` 只在该 `<test_case>` 内组织步骤。

```xml
<test_case>
  <!-- 裸 test_step 仍按原有逻辑执行 -->
  <test_step action="type" model="LoginForm" data="L001"/>

  <scenario id="S001" title="进入功能页" group="smoke" tag="nav,ui">
    <test_step action="type" model="NavMenu" data="N001"/>
  </scenario>

  <scenario id="S002" title="提交表单" group="smoke" tag="form" depends="S001">
    <test_step action="type" model="TestForm" data="T001"/>
    <test_step action="verify" model="TestForm" data="V001"/>
  </scenario>
</test_case>
```

| 属性 | 必需 | 说明 |
|------|------|------|
| `id` | 是 | scenario 在当前 case 内的唯一标识，用于日志、结果状态和 `depends` 引用 |
| `title` | 否 | scenario 标题，用于日志/报告展示 |
| `group` | 否 | 分组标签，如 `smoke`、`negative` |
| `tag` | 否 | 逗号分隔的标签列表，如 `smoke,p0` |
| `depends` | 否 | 逗号分隔的依赖 scenario id；第一版仅支持同一 case 内依赖 |

执行语义：

- `<test_case>` 中的裸 `<test_step>` 与 `<scenario>` 按书写顺序混合执行。
- `<scenario>` 内可继续使用 `<test_step>`、`<if>/<elif>/<else>`、`<loop>` 等已有步骤结构。
- `depends` 只判断同一 case 内已经执行过的 scenario：依赖未通过（`FAIL` 或 `SKIP`）时，当前 scenario 不执行并标记为 `SKIP`。
- scenario 失败会导致 case 失败；后处理阶段仍按原有语义执行。

### 3.5 `test_step` 属性（与旧版单行步骤含义相同）

| 属性 | 必需 | 说明 |
|------|------|------|
| `action` | 是 | 关键字名称，**必须为** `case.xsd` 中 `ActionType` 枚举值之一（见 [3.6](#36-action-与-casexsd-枚举一致)） |
| `model` | 否 | 模型名。type/verify/send/DB → 模型名；DB 要求该模型为 `type="database"`；navigate/close/wait 等可留空 |
| `data` | 否 | 数据引用或直接值。DataID / GlobalValue 引用 / URL / CSS 选择器 / 秒数等 |

### 3.6 `action` 与 `case.xsd` 枚举一致

下列取值与 `rodski/schemas/case.xsd` 中 `ActionType` **完全一致**（大小写敏感）；不在表内的字符串无法通过 XSD 校验。

| 取值 | 常见用途（简述） |
|------|------------------|
| `close` | 关闭浏览器 |
| `type` | UI 批量输入 |
| `verify` | 批量验证（UI / 接口）；严格全匹配，任一字段不一致即步骤失败 |
| `wait` | 等待 |
| `navigate` | 打开 URL |
| `assert` | 断言 |
| `upload_file` | 上传文件 |
| `clear` | 清空输入 |
| `get_text` | **已废弃**，请改用 `get` |
| `get` | 三模式取值：`get ModelName D001`（模型模式，推荐）/ `get #selector`（UI 选择器，低级补充）/ `get var_name`（命名访问） |
| `evaluate` | 执行 JS 表达式（**仅 Web**，低优先级，结构化结果保留原类型） |
| `send` | 发 HTTP 请求 |
| `set` | 写入命名变量：`set \| key=value`，写入 context.named 并写入 history |
| `DB` | 执行 SQL |
| `run` | 执行 `fun/` 下脚本 |
| `check` | 与 `verify` 等价（兼容） |
| `screenshot` | 截图 |

详细参数约定仍以 [第 8 节](#8-关键字手册) 为准。

### 3.7 用例示例

```xml
<cases>
  <!-- UI 登录测试 -->
  <case execute="是" id="c001" title="登录测试" description="验证登录" component_type="界面">
    <pre_process>
      <test_step action="navigate" model="" data="GlobalValue.DefaultValue.URL/login"/>
    </pre_process>
    <test_case>
      <test_step action="type" model="Login" data="L001"/>
      <test_step action="verify" model="Login" data="V001"/>
    </test_case>
    <post_process>
      <test_step action="close" model="" data=""/>
    </post_process>
  </case>

  <!-- DB 验证（仅 test_case 内一步也可） -->
  <case execute="是" id="c002" title="DB验证" description="查询验证" component_type="数据库">
    <test_case>
      <test_step action="DB" model="QuerySQL" data="Q001"/>
    </test_case>
  </case>

  <!-- 接口测试 -->
  <case execute="是" id="c003" title="API登录" description="接口测试" component_type="接口">
    <test_case>
      <test_step action="send" model="LoginAPI" data="D001"/>
      <test_step action="verify" model="LoginAPI" data="V001"/>
    </test_case>
  </case>
</cases>
```

### 3.8 控制流结构（if/elif/else/loop）

`case.xsd` 支持在 `<pre_process>`、`<test_case>`、`<post_process>` 及 `<scenario>` 内使用条件分支和循环容器。这些结构**不是独立关键字**，不在 SUPPORTED 列表中。

#### `<if>` 条件分支

```xml
<test_case>
  <test_step action="send" model="QueryAPI" data="Q001"/>
  <if condition="${Return[-1].status} == 200">
    <test_step action="verify" model="QueryAPI" data="V001"/>
  <else>
    <test_step action="screenshot" data="error.png"/>
  </else>
  </if>
</test_case>
```

| 属性 | 必需 | 说明 |
|------|------|------|
| `condition` | 是 | 条件表达式，支持 `${Return[-N]}` 和变量引用 |

**嵌套规则**：`<if>` 最多嵌套 2 层（外层 `<if>` 内可再嵌套一层 `<if>`，但第 2 层内不可再嵌套）。

#### `<loop>` 循环

```xml
<test_case>
  <loop range="1,5" var="i">
    <test_step action="type" model="ItemForm" data="D00${i}"/>
    <test_step action="verify" model="ItemForm" data="V00${i}"/>
  </loop>
</test_case>
```

| 属性 | 必需 | 说明 |
|------|------|------|
| `range` | 是 | 循环范围，如 `1,5`（从 1 到 5） |
| `var` | 否 | 循环变量名，可在内部步骤中通过 `${var}` 引用 |

---
