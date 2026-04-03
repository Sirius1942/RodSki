# 8. 关键字手册

> **来源**: RodSki 测试用例编写指南 v3.4  
> 本文档为独立章节，完整指南请见 [TEST_CASE_WRITING_GUIDE.md](../TEST_CASE_WRITING_GUIDE.md)

---


### 8.1 UI 操作关键字

| 关键字 | 说明 | model 属性 | data 属性 |
|--------|------|-----------|-----------|
| **navigate** | 导航到 URL（无浏览器时自动创建） | — | URL 或 GlobalValue 引用 |
| **close** | 关闭浏览器 | — | — |
| **type** | UI 批量输入（PC 端 / 移动端统一） | 模型名 | DataID |
| **verify** | 批量验证（UI / 接口通用） | 模型名 | DataID（自动查 `模型名_verify` 表） |
| **wait** | 等待指定秒数 | — | 秒数（如 `3`） |
| **clear** | 清空输入框 | — | CSS 选择器 |
| **get_text** / **get** | 获取元素文本 | — | CSS 选择器 |
| **screenshot** | 手动截图 | — | 文件路径 |
| **upload_file** | 上传文件 | — | 文件路径 |

> `click`、`select`、`hover`、`scroll`、`double_click`、`right_click`、`key_press`、`drag` 等 UI 原子动作不作为独立关键字使用，而是写在**数据表的 field 值**中，由 `type` 批量模式自动识别执行。详见 [5.4 批量输入时的特殊值](#54-批量输入时的特殊值)。

> **type 统一 UI 测试**：无论 PC Web、移动端（Android/iOS），所有 UI 输入操作都使用 `type`，不区分平台。

### 8.2 type / send / verify — 核心关键字详解

框架有三个核心批量关键字，分工明确：

| | type（UI） | send（接口） | verify（通用验证） |
|--|-----------|-------------|-------------------|
| 作用 | 数据 → 写入 UI 界面 | 数据 → 发送 HTTP 请求 | 界面/响应 → 读取并比较 |
| 适用场景 | PC Web / 移动端 | REST API 接口 | UI 验证 + 接口验证 |
| model 属性 | UI 模型名（必填） | 接口模型名（必填） | 模型名（必填） |
| data 属性 | DataID | DataID | DataID |
| 数据文件 | `{模型名}.xml` | `{模型名}.xml` | `{模型名}_verify.xml` |
| 匹配规则 | 元素 name = field name | 元素 name = field name | 元素 name = field name |

> **数据表命名规则**：模型名 = 数据表文件名（强制一致）。data 属性只写 `DataID`，不写表名前缀。

#### 接口测试：send + verify

接口测试不再使用独立 HTTP 关键字，而是通过 **send / verify** 批量模式完成：

1. **接口模型**：在 model.xml 中定义接口元素，包含 `_method`（请求方式）、`_url`（请求地址）、`_header_*`（请求头）以及接口字段
2. **send 发送请求**：`send LoginAPI D001` → 从 `LoginAPI` 模型获取请求方式和 URL，从 `LoginAPI.xml` 取值，发送 HTTP 请求
3. **verify 验证响应**：`verify LoginAPI V001` → 从 `LoginAPI_verify.xml` 取期望值，与 send 的响应比较

**接口模型元素命名约定**：

| 元素名 | 作用 | 说明 |
|--------|------|------|
| `_method` | HTTP 请求方式 | 值为 GET / POST / PUT / DELETE，在模型中定义默认值 |
| `_url` | 请求地址 | 绝对 URL 或相对路径 |
| `_header_*` | 请求头 | 如 `_header_Authorization`、`_header_Content-Type` |
| 其他 | 请求体字段 | POST/PUT → JSON body；GET/DELETE → 查询参数 |

**接口模型示例**：

```xml
<model name="LoginAPI" servicename="">
    <element name="_method" type="interface">
        <location type="static">POST</location>
    </element>
    <element name="_url" type="interface">
        <location type="static">http://api.example.com/login</location>
    </element>
    <element name="username" type="interface">
        <location type="field">username</location>
    </element>
    <element name="password" type="interface">
        <location type="field">password</location>
    </element>
</model>
```

**数据文件 `data/LoginAPI.xml`**：

```xml
<datatable name="LoginAPI">
  <row id="D001" remark="管理员登录">
    <field name="username">admin</field>
    <field name="password">admin123</field>
  </row>
</datatable>
```

**验证数据文件 `data/LoginAPI_verify.xml`**：

```xml
<datatable name="LoginAPI_verify">
  <row id="V001" remark="验证管理员登录">
    <field name="status">200</field>
    <field name="username">admin</field>
  </row>
</datatable>
```

> `status` 字段：期望的 HTTP 状态码。其他字段：期望的响应字段值。

**Case XML 写法**：

```xml
<test_case>
  <test_step action="send" model="LoginAPI" data="D001"/>
  <test_step action="verify" model="LoginAPI" data="V001"/>
</test_case>
```

### 8.3 接口测试关键字

| 关键字 | 说明 | model 属性 | data 属性 |
|--------|------|-----------|-----------|
| **send** | 发送接口请求（模型 + 数据） | 接口模型名 | DataID |

> send 是接口测试的核心关键字，与 UI 的 type 对称。响应自动保存为步骤返回值（含 `status` 和响应体字段），可通过 `verify` 验证。

### 8.4 数据库关键字

| 关键字 | 说明 | model 属性 | data 属性 |
|--------|------|-----------|-----------|
| **DB** | 执行 SQL | GlobalValue 中的连接组名 | SQL 数据表引用或直接 SQL |

DB 用例格式：

```xml
<test_case>
  <test_step action="DB" model="demodb" data="QuerySQL.Q001"/>
</test_case>
```

- **model 属性**：填写 GlobalValue 中配置的数据库连接组名（如 `demodb`）
- **data 属性**：填写 SQL 数据表引用（如 `QuerySQL.Q001`），或直接写 SQL

### 8.5 高级关键字

| 关键字 | 说明 | model 属性 | data 属性 |
|--------|------|-----------|-----------|
| **set** | 设置变量 | — | — |
| **run** | 沙箱执行 Python 代码 | 工程名（fun/ 下的子目录） | 代码文件路径 |

### 8.6 run — 沙箱代码执行

`run` 在独立子进程中执行 Python 脚本，脚本的 **stdout 输出**自动保存为步骤返回值。

#### 目录结构

代码文件以"工程"形式组织，存放在与 `case/` 同级的 `fun/` 目录下：

```
{测试模块}/
├── case/
├── model/
├── data/
├── result/
└── fun/                   ← 代码工程根目录
    ├── data_gen/          ← 工程名（model 属性填写）
    │   ├── gen_phone.py   ← data 属性填写
    │   └── utils.py
    └── crypto/
        └── encrypt.py
```

#### Case XML 写法

```xml
<test_step action="run" model="data_gen" data="gen_phone.py"/>
```

#### 脚本编写规范

脚本通过 `print()` 输出返回值。框架会自动尝试 JSON 解析。

---

