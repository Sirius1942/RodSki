<!-- 自动生成 from rodski/docs/TEST_CASE_WRITING_GUIDE.md  请勿手工编辑 -->

## 8. 关键字手册

### 8.1 UI 操作关键字

| 关键字 | 说明 | model 属性 | data 属性 |
|--------|------|-----------|-----------|
| **navigate** | 导航到 URL（无浏览器时自动创建）；移动端支持 `app://android/包名/Activity` 和 `app://ios/BundleId` 格式启动 App | — | URL / GlobalValue 引用 / app:// URI |
| **close** | 关闭浏览器及移动端驱动（同时释放 android/ios 驱动缓存） | — | — |
| **type** | UI 批量输入（PC 端 / 移动端统一） | 模型名 | DataID |
| **verify** | 批量验证（UI / 接口通用）；UI 模型自动重试到期望值（v11.6.0，[§5.7](#57-verify-期望值操作符原生断言与自动重试v1160)） | 模型名 | DataID（自动查 `模型名_verify` 表） |
| **wait** | 等待指定秒数（固定等待，仅用于演示 / 确需固定时长；等异步结果请直接 `verify`） | — | 秒数（如 `3`） |
| **clear** | 清空输入框 | — | CSS 选择器 |
| **get** | 三模式取值：model+DataID → 模型元素文本（推荐）；CSS 选择器 → UI 元素文本（低级补充）；变量名 → 命名变量读取 | 模型名（可选） | DataID 或 CSS 选择器 或 变量名 |

> **UI 元素取值推荐方式**：优先使用 `get ModelName DataID`（模型模式）或 `verify` + model + 数据表。`get #selector` 直接获取 UI 元素文本属于低级补充手段，不推荐在常规业务用例主链路中使用。
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
| 逻辑表 | `{模型名}` | `{模型名}` | `{模型名}_verify` |
| 匹配规则 | 元素 name = field name | 元素 name = field name | 元素 name = field name |

> **数据表命名规则**：模型名 = 逻辑表名（强制一致）。Case 的 `data` 属性只写 `DataID`，不写表名前缀。逻辑表来自 `data.sqlite`。

#### 接口测试：send + verify

接口测试不再使用独立 HTTP 关键字，而是通过 **send / verify** 批量模式完成：

1. **接口模型**：在 model.xml 中定义接口元素，包含 `_method`（请求方式）、`_url`（请求地址）、`_header_*`（请求头）以及接口字段
2. **send 发送请求**：`send LoginAPI D001` → 从 `LoginAPI` 模型获取请求方式和 URL，从逻辑表 `LoginAPI` 取值（来源为 `data.sqlite`），发送 HTTP 请求
3. **verify 验证响应**：`verify LoginAPI V001` → 从逻辑表 `LoginAPI_verify` 取期望值（来源为 `data.sqlite`），与 send 的响应比较

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

**数据表（`data.sqlite` 中的 `LoginAPI` 表）**：

```xml
<datatable name="LoginAPI">
  <row id="D001" remark="管理员登录">
    <field name="username">admin</field>
    <field name="password">admin123</field>
  </row>
</datatable>
```

**验证数据表（`data.sqlite` 中的 `LoginAPI_verify` 表）**：

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
| **DB** | 执行 SQL | 数据库模型名 | DataID |

DB 用例格式：

```xml
<test_case>
  <test_step action="DB" model="QuerySQL" data="Q001"/>
</test_case>
```

- **model 属性**：填写 `type="database"` 的模型名（如 `QuerySQL`）
- **data 属性**：填写该模型对应逻辑表中的 DataID（如 `Q001`）
- 数据行可通过 `query` 字段引用模型内定义的 query，也可以通过 `sql` 字段直接提供 SQL
- 数据源为 `data.sqlite`

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

> **v6.7.6 起，`run` 支持带或不带 `fun/` 前缀的路径写法，两者等价：**
> - `data="fun/desktop/key_combo.py Ctrl+A"`
> - `data="desktop/key_combo.py Ctrl+A"`

#### 脚本编写规范

脚本通过 `print()` 输出返回值。框架会自动尝试 JSON 解析。

#### 内置函数（进程内执行，`model` 必须为空）

`data` 是已注册的内置函数调用时，`run` 在当前进程内直接执行（不走子进程）。**`model` 必须写空字符串**，否则会被当作 `fun/` 下的工程名：

```xml
<test_step action="run" model="" data="mock_route(url_pattern='/api/users', status=200, body='[]')"/>
```

| 函数 | 作用 |
|------|------|
| `mock_route(url_pattern, status, body, content_type)` / `clear_routes()` | Mock / 清除接口响应（仅 Playwright） |
| `wait_for_response(url_pattern, timeout)` | 等待网络请求完成 |
| `start_js_coverage()` / `stop_js_coverage(output)` | JS 覆盖率 |
| `reset_request_log()` / `get_request_log()` | 请求日志 |
| `save_auth_state(name)` / `use_auth_state(name)` | 登录态复用（v11.6.0），见 [§8.8](#88-登录态复用save_auth_state--use_auth_statev1160) |

### 8.7 evaluate — 逃生舱与 file: 脚本（v11.6.0）

`evaluate` 在页面中执行 JavaScript（仅 Web），返回值写入 Return。它是**逃生舱**：数量、存在、可见、URL、标题、弹窗、查询结果都有原生写法（见 [§5.7.4](#574-什么时候还用-evaluate) 对照表），`evaluate` 只留给原生能力覆盖不到的检查。

**XML 属性转义**：XML 属性里不能直接写 `&&`、`<`，要写成 `&amp;&amp;`、`&lt;`。脚本稍长时，推荐放到模块内的 `fun/js/` 目录，用 `file:` 引用，脚本里可以原样写 `&&`、`<` 和引号：

```xml
<test_step action="evaluate" model="" data="file:fun/js/check_rows.js"/>
```

```javascript
// fun/js/check_rows.js
(() => {
  const rows = document.querySelectorAll('#orderBody tr.order-row');
  if (rows.length === 10 && rows[0].innerText.trim() === 'ORD1') return rows.length;
  throw new Error('期望 10 行且首行为 ORD1，实际 ' + rows.length + ' 行');
})()
```

- `file:` 后的路径相对**模块目录**（`case/`、`fun/` 的上级）；只允许模块内的文件，绝对路径或 `..` 越界会被拒绝。
- 脚本抛出异常时步骤失败。
- XML 解析失败且问题出在属性里的 `&` / `<` 时，报错会提示上面两种改法。

### 8.8 登录态复用：save_auth_state / use_auth_state（v11.6.0）

一个用例做一次 UI 登录并保存登录态，后续用例直接加载，省掉重复登录：

```xml
<!-- TC001：UI 登录后保存 -->
<test_case>
  <test_step action="type" model="Login" data="L_ADMIN"/>
  <test_step action="verify" model="PageInfo" data="V_HOME"/>
  <test_step action="run" model="" data="save_auth_state(name='admin')"/>
</test_case>

<!-- TC002：先加载登录态，再 navigate 到登录后的页面 -->
<pre_process>
  <test_step action="run" model="" data="use_auth_state(name='admin')"/>
  <test_step action="navigate" model="" data="GlobalValue.Site.URL/home.html"/>
</pre_process>
```

- 保存的是浏览器 context 的 cookie + localStorage，只存在**本次 run 的内存**中，不写入结果目录或仓库；run 结束即失效。
- `use_auth_state` 必须写在该用例的 `navigate` **之前**（它作用于本用例新建的 context）。
- 找不到名字时报错：先确认保存该登录态的用例已经在前面执行（同一用例文件内按书写顺序执行；用 plan 时注意顺序）。
- 推荐与 `SessionMode=shared_browser` 搭配（[§6.4.4](#644-sessionmode--浏览器会话复用)）：浏览器只启动一次、用例之间仍然隔离，只有显式 `use_auth_state` 的用例才带登录态。
- `--workers` 并行时，保存和使用登录态的用例要放在**同一个用例文件**里（同一文件在同一 worker 中顺序执行）。

---
