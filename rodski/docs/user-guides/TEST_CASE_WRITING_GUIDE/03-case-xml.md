# 3. Case XML — 用例编写

> **来源**: RodSki 测试用例编写指南 v3.4  
> 本文档为独立章节，完整指南请见 [TEST_CASE_WRITING_GUIDE.md](../TEST_CASE_WRITING_GUIDE.md)

---


### 3.1 文件格式（三阶段容器 + 多 `test_step`）

每个 `<case>` 下有三个**阶段容器**（见 `case.xsd`）：

1. **`<pre_process>`**（可选）— 预处理，内含 **0～n** 个 `<test_step>`
2. **`<test_case>`**（**必选，且每个 case 仅 1 个**）— 用例主体，内含 **至少 1 个** `<test_step>`
3. **`<post_process>`**（可选）— 后处理，内含 **0～n** 个 `<test_step>`

原 Excel 中「测试步骤」「预期结果」等多行语义，在 XML 中统一为 **`<test_case>` 内多条 `<test_step>`**（先 `type` 再 `verify` 等，按书写顺序执行）。

```xml
<?xml version="1.0" encoding="UTF-8"?>
<cases>
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
</cases>
```

### 3.2 属性说明（`case` 根）

| 属性 | 必需 | 说明 | 取值规则 |
|------|------|------|---------|
| `execute` | 是 | 是否执行 | 只有 `是` 才执行，`否` 跳过 |
| `id` | 是 | 用例编号 | 如 `c001`、`c002`，用于日志和结果回填 |
| `title` | 是 | 用例标题 | 用于日志和报告显示 |
| `description` | 否 | 用例描述 | 详细说明（可选） |
| `component_type` | 否 | 测试类别 | `界面` / `接口` / `数据库`（与 `case.xsd` 一致），仅做分类标记 |

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

### 3.4 `test_step` 属性（与旧版单行步骤含义相同）

| 属性 | 必需 | 说明 |
|------|------|------|
| `action` | 是 | 关键字名称，**必须为** `case.xsd` 中 `ActionType` 枚举值之一（见 [3.5](#35-action-与-casexsd-枚举一致)） |
| `model` | 否 | 模型名或连接名。type/verify → 模型名；DB → GlobalValue 连接组名 |
| `data` | 否 | 数据引用或直接值。DataID / GlobalValue 引用 / URL / CSS 选择器 / 秒数等 |

### 3.5 `action` 与 `case.xsd` 枚举一致

下列取值与 `rodski/schemas/case.xsd` 中 `ActionType` **完全一致**（大小写敏感）；不在表内的字符串无法通过 XSD 校验。

| 取值 | 常见用途（简述） |
|------|------------------|
| `close` | 关闭浏览器 |
| `type` | UI 批量输入 |
| `verify` | 批量验证（UI / 接口） |
| `wait` | 等待 |
| `navigate` | 打开 URL |
| `assert` | 断言 |
| `upload_file` | 上传文件 |
| `clear` | 清空输入 |
| `get_text` | 取元素文本 |
| `get` | 取文本（别名） |
| `send` | 发 HTTP 请求 |
| `set` | 设置变量 |
| `DB` | 执行 SQL |
| `run` | 执行 `fun/` 下脚本 |
| `check` | 与 `verify` 等价（兼容） |
| `screenshot` | 截图 |

详细参数约定仍以 [第 8 节](#8-关键字手册) 为准。

### 3.6 用例示例

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
      <test_step action="DB" model="demodb" data="QuerySQL.Q001"/>
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

---

