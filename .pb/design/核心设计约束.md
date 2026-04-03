# RodSki 核心设计约束

**版本**: v3.7
**日期**: 2026-03-27

本文档记录 RodSki 框架的核心设计决策与约束规则，所有后续开发必须遵循。

---

## 1. 关键字职责划分

### 1.1 三大核心关键字

| 关键字 | 职责 | 适用范围 |
|--------|------|---------|
| **type** | UI 批量输入 | PC Web / Android / iOS / 桌面端 — 所有 UI 平台统一 |
| **send** | 接口请求发送 | REST API 接口测试 |
| **verify** | 批量验证 | UI 验证 + 接口响应验证 — 通用 |

**约束**：

- `type` 只做 UI，`send` 只做接口，二者不混用
- `verify` 是通用的，根据模型的 `driver_type`（web / interface）自动判断从界面读值还是从接口响应读值
- 不存在 `http_get`、`http_post`、`http_put`、`http_delete`、`assert_json`、`assert_status` 等独立 HTTP 关键字

### 1.2 UI 原子动作不作为独立关键字

以下操作**不出现在 Case XML 的 action 属性中**，只能作为数据表字段值，由 `type` 批量模式自动识别执行：

```
click / double_click / right_click / hover / select【值】
key_press【按键】 / drag【目标】 / scroll / scroll【x,y】
```

**约束**：`SUPPORTED` 列表中不包含这些关键字，测试用例中不允许写 `click` 或 `hover` 等作为动作。

### 1.3 navigate / launch — 应用启动（场景化双关键字）

**`navigate`** 和 **`launch`** 在功能上完全相同，都是"启动或切换到目标应用/页面"，只是适用场景不同：

| 关键字 | 适用场景 | 参数格式 | 行为 |
|--------|---------|---------|------|
| **navigate** | Web / Mobile | URL 地址 | 如果当前没有浏览器实例 → 自动通过 `driver_factory` 创建；如果已有浏览器实例 → 复用现有实例，导航到目标 URL |
| **launch** | Desktop (Windows/macOS) | 应用路径或应用名 | 如果应用未运行 → 启动应用；如果应用已运行 → 切换到该应用窗口 |

**约束**：
- `navigate` 替代了 `open`（已废弃）
- `navigate` 和 `launch` 在关键字计数中**算作一个**（场景化变体，非独立关键字）
- 桌面端不使用 `navigate`，Web/Mobile 不使用 `launch`，避免语义混淆

### 1.4 run = 脚本调用能力

`run` 是与 `type`/`verify`/`send` 同级的通用关键字，为框架提供脚本调用能力：

**定义**：
- 在独立子进程中执行 Python 脚本
- 代码以工程形式组织在 `fun/` 目录下（与 `case/` 同级）
- 脚本 stdout 自动保存为步骤返回值（优先 JSON 解析）
- 目前仅支持 Python

**定位**：
- 是用例执行时预留的扩展能力
- 与其他关键字级别相同，任何平台都可使用
- 用于处理框架内置关键字无法覆盖的场景

**使用示例**：
```xml
<test_step action="run" model="" data="fun/utils/data_process.py"/>
```

---

## 2. 数据表命名与引用规则

### 2.1 数据表文件组织方式

**实际实现**：所有数据表合并在两个固定文件中：

```
data/data.xml          ← 所有操作数据表（type/send 使用）
data/data_verify.xml   ← 所有验证数据表（verify 使用，可选）
```

**文件结构**：
```xml
<!-- data/data.xml -->
<datatables>
    <datatable name="Login">
        <row id="L001">...</row>
    </datatable>
    <datatable name="LoginAPI">
        <row id="D001">...</row>
    </datatable>
    <datatable name="Login_verify">
        <row id="V001">...</row>
    </datatable>
</datatables>
```

**约束**：
- 模型名与数据表名（`datatable.name`）必须一致
- 不需要为每个模型创建独立的 XML 文件
- `data_verify.xml` 是可选的，可以将验证数据也放在 `data.xml` 中

### 2.2 验证数据表自动拼接 `_verify` 后缀

```
verify Login V001 → 自动查找表名为 "Login_verify" 的数据表
verify LoginAPI V001 → 自动查找表名为 "LoginAPI_verify" 的数据表
```

**注意**：验证数据表可以放在 `data.xml` 或 `data_verify.xml` 中，但如果两个文件中存在同名表，`data_verify.xml` 中的表会覆盖 `data.xml` 中的同名表。

### 2.3 数据列只写 DataID

Case XML 的 data 属性中，只需要写 DataID，不需要写表名前缀：

```
✅ type  Login    L001      → 在 Login.xml 中查找 id="L001"
✅ send  LoginAPI D001      → 在 LoginAPI.xml 中查找 id="D001"
✅ verify Login    V001      → 在 Login_verify.xml 中查找 id="V001"

❌ type  Login    LoginData.L001   ← 不需要写表名
```

### 2.4 元素名 = 数据表字段名

模型 XML 中的 `element name` 必须与数据表 XML 中 `<field name="...">` 完全一致（区分大小写），这是 `type`/`send`/`verify` 批量模式的匹配基础。

---

## 2.5 定位器类型（完整）

RodSki 支持 12 种定位器类型，分为传统定位器和视觉定位器两大类。

### 2.5.1 传统定位器

| 类型 | 格式 | 说明 | 示例 |
|------|------|------|------|
| `id` | CSS ID | 转换为 `#值` | `<location type="id">username</location>` → `#username` |
| `class` | CSS Class | 转换为 `.值` | `<location type="class">btn-submit</location>` → `.btn-submit` |
| `css` | CSS 选择器 | 原样使用 | `<location type="css">input[name="user"]</location>` |
| `xpath` | XPath | 原样使用 | `<location type="xpath">//input[@id='user']</location>` |
| `text` | 文本匹配 | Playwright `text=...` | `<location type="text">登录</location>` → `text=登录` |
| `tag` | 标签名 | HTML 标签 | `<location type="tag">button</location>` |
| `name` | name 属性 | 按 name 属性定位 | `<location type="name">username</location>` |
| `static` | 静态值 | 字面量，不定位 | 用于接口 `_method` 等 |
| `field` | 字段映射 | 接口请求字段 | 用于接口 body/query |

### 2.5.2 视觉定位器

| 类型 | 格式 | 说明 | 示例 |
|------|------|------|------|
| `vision` | 图片匹配 | 通过截图/图片模板匹配定位 | `<location type="vision">img/login_btn.png</location>` |
| `ocr` | 文字识别 | 通过 OCR 识别文字定位 | `<location type="ocr">登录</location>` |
| `vision_bbox` | 坐标定位 | 直接使用坐标 `x1,y1,x2,y2` | `<location type="vision_bbox">100,200,150,250</location>` |

**视觉定位器说明**：

- **`vision` 图片定位器**：
  - 值为图片路径（相对于 `images/` 目录）
  - 通过图像匹配算法（如 OpenCV 模板匹配）定位
  - 适用于：按钮图标、Logo、固定 UI 元素

- **`ocr` 文字定位器**：
  - 值为要识别的文字内容
  - 通过 OmniParser OCR 能力识别文字位置
  - 适用于：按钮文字、标签、链接文字

- **`vision_bbox` 坐标定位器**：
  - 值为坐标 `x1,y1,x2,y2`（逗号分隔）
  - 无需 AI 调用，性能最高
  - Web 用页面像素坐标，Desktop 用屏幕绝对坐标
  - 适用于：坐标固定的元素

### 2.5.3 定位器格式约束

**格式规范**：
1. 所有定位器使用 `<location type="类型">值</location>` 格式
2. `type` 属性必须为 LocatorType 枚举值之一
3. 值写在 location 标签内容中

**约束规则**：
```xml
<!-- ✅ 正确：完整格式 -->
<element name="loginBtn" type="web">
    <type>button</type>
    <location type="id">loginBtn</location>
</element>

<!-- ✅ 正确：简化格式 -->
<element name="loginBtn" type="id" value="loginBtn"/>

<!-- ❌ 错误：不要使用 locator 属性 -->
<element name="loginBtn" locator="vision:登录按钮"/>
```

### 2.5.4 多定位器格式

每个元素可定义多个定位器，失败时自动切换：

```xml
<element name="loginBtn" type="web">
    <type>button</type>
    <location type="id" priority="1">loginBtn</location>
    <location type="xpath" priority="2">//button[@class='login']</location>
    <location type="ocr" priority="3">登录</location>
</element>
```

**切换规则**：
1. 按 `priority` 从小到大依次尝试
2. 当前定位器定位失败时，自动切换到下一个
3. 所有定位器都失败时，抛出 `ElementNotFoundError`

**使用场景**：
- 传统定位器作为首选，视觉定位作为兜底
- 动态页面优先使用视觉定位
- 提高测试用例的健壮性

### 2.5.5 示例对比

同一个登录按钮的三种定位方式：

```xml
<!-- 方式1: 图片匹配 - 使用按钮截图 -->
<element name="loginBtn" type="web">
    <type>button</type>
    <location type="vision">img/login_btn.png</location>
</element>

<!-- 方式2: OCR文字识别 - 识别"登录"二字 -->
<element name="loginBtn" type="web">
    <type>button</type>
    <location type="ocr">登录</location>
</element>

<!-- 方式3: 坐标定位 - Agent探索后生成 -->
<element name="loginBtn" type="web">
    <type>button</type>
    <location type="vision_bbox">100,200,150,250</location>
</element>
```

---

## 3. 接口测试设计约束

### 3.1 接口模型定义请求属性

接口模型在 model.xml 中通过特殊命名的元素定义 HTTP 请求属性：

| 元素名 | 作用 | 说明 |
|--------|------|------|
| `_method` | 请求方式 | GET / POST / PUT / DELETE，模型中定义默认值 |
| `_url` | 请求地址 | 绝对 URL 或相对路径 |
| `_header_*` | 请求头 | 如 `_header_Authorization`、`_header_Content-Type` |
| 其他元素 | 请求体字段 | POST/PUT → JSON body；GET/DELETE → 查询参数 |

### 3.2 send 的响应存储格式

`send` 的响应自动保存为字典，包含 `status` 和响应体字段：

```python
{"status": 200, "token": "abc123", "username": "admin", ...}
```

### 3.3 verify 的接口验证

`verify` 在接口场景下从 `${Return[-1]}`（即 `send` 的响应）读取实际值，与 `_verify` 数据表中的期望值逐字段比较。`_verify` 数据表中 `status` 列用于验证 HTTP 状态码。

---

## 4. 特殊值约定

### 4.1 数据表中的控制值

| 值 | UI 行为（type） | 接口行为（send） | 验证行为（verify） |
|----|----------------|-----------------|-------------------|
| 空值 | 跳过 | — | — |
| `BLANK` | 跳过 | 发送空字符串 | 期望空字符串 |
| `NULL` | 跳过 | 发送 null | 期望 null |
| `NONE` | 跳过 | 不发送该字段 | 跳过验证 |
| `.Password` 后缀 | 输入，日志脱敏 | — | — |

### 4.2 Return 引用

- `${Return[-1]}`、`${Return[0]}` 等只应出现在**数据表 XML 的 field 值中**
- 使用的标准格式是 `${Return[x]}` 其中x代表测试步骤，0是当前测试步骤，也就是当前测试步骤执行完成后保存的执行结果变量.-1代表上一个测试步骤的执行结果。以此类推。
- 不要写在 Case XML 的 data 属性，否则会在进入关键字前被替换成字符串
- **与动态步骤的关系**：在「固定 + 动态」混合执行模型下，`${Return[-1]}` 的语义**仅绑定固定步骤管线**（见第 8 节）；动态插入步骤**暂不参与** `Return` 解析链，数据表中亦**不得**依赖动态步骤上的 `${Return[...]}`（见第 8.4 节）,但是动态步骤每一步的返回值也需要保存，区别于静态步骤的返回值

**暂停 / 插入**不改变上述「固定管线」语义：`${Return[-1]}` 仍指「最近一次完成执行的固定步骤」的返回值（插入步是否入栈见 8.4；若未入栈，则与插入前一致）。

---

## 5. 当前关键字清单（15 个）

```
SUPPORTED = [
    "close", "type", "verify", "wait", "navigate", "launch",
    "assert",
    "upload_file", "clear", "get_text", "get",
    "send", "set", "DB", "run",
]
```

加上 1 个兼容关键字 `check`（等同 `verify`）。

**设计原则**：关键字数量应保持精简，新增关键字前需评估是否可以通过现有批量模式（数据表字段值）实现。

**场景化关键字**：`navigate` 和 `launch` 功能完全相同，在计数中算作一个关键字（见 §1.3）。

---

## 6. 目录结构约束（强制）

### 6.1 产品目录层级

```
product/                           ← 产品根目录（顶层）
└── {测试项目名}/                   ← 测试项目（如 DEMO）
    └── {测试模块名}/               ← 测试模块/业务（如 demo_site）
        ├── case/                  ← 测试用例 XML 文件
        │   └── *.xml
        ├── model/                 ← 模型 XML 文件
        │   └── model.xml
        ├── fun/                   ← 代码工程目录（run 关键字使用）
        │   └── {工程名}/
        │       └── *.py
        ├── data/                  ← 数据 XML 文件 + 全局变量
        │   ├── globalvalue.xml    ← 全局变量（固定文件名）
        │   ├── data.xml           ← 所有数据表（固定文件名）
        │   └── data_verify.xml    ← 验证数据表（可选）
        └── result/                ← 测试结果 XML（框架自动生成）
            └── result_*.xml
```

### 6.2 层级说明

| 层级 | 说明 | 示例 |
|------|------|------|
| product/ | 产品根目录，固定名称，是最顶层目录 | `product/` |
| 测试项目 | 按产品/项目组织，可有多个 | `DEMO/`、`ERP/` |
| 测试模块 | 按业务模块划分，可有多个 | `demo_site/`、`user_module/` |
| 固定文件夹 | 每个测试模块下必须包含的 5 个目录 | `case/`、`model/`、`fun/`、`data/`、`result/` |

### 6.3 固定文件夹职责

| 目录 | 职责 | 文件类型 |
|------|------|---------|
| `case/` | 存放测试用例定义 | `*.xml`（符合 case.xsd） |
| `model/` | 存放页面/接口模型 | `model.xml`（符合 model.xsd） |
| `fun/` | 存放 run 关键字的代码工程 | `*.py` |
| `data/` | 存放数据表和全局变量 | `data.xml`、`data_verify.xml`（可选）、`globalvalue.xml`（符合 data.xsd / globalvalue.xsd） |
| `result/` | 存放测试执行结果 | `result_*.xml`（符合 result.xsd，框架自动生成） |

### 6.4 禁止变更

- **product 必须是最顶层目录**，不可将项目/模块提升到 product 之上
- **5 个固定文件夹名称不可更改**（case/model/fun/data/result）
- **固定文件夹只出现在测试模块层级下**，不可出现在测试项目层级
- **model.xml 是唯一的模型文件名**，不可改名

---

## 7. XML 文件格式约束

### 7.0 运行时 XSD 校验（强制）

框架在**读取**各类测试相关 XML 时，会按类型对照 `rodski/schemas/*.xsd` 做一次 **XML Schema 校验**（依赖 Python 包 `xmlschema`，见 `requirements.txt`）：

| 读取时机 | 文档类型 | 不符合 Schema 时 |
|---------|---------|------------------|
| 解析 `case/*.xml` | 用例 | 抛出 `XmlSchemaValidationError`（错误码 `SKI204`） |
| 解析 `data/*.xml`（不含 globalvalue） | 数据表 | 同上 |
| 解析 `data/globalvalue.xml` | 全局变量 | 同上 |
| 加载 `model/model.xml` | 模型 | 同上 |
| 写入 `result/result_*.xml` 前 | 测试结果 | 同上（保证输出符合 `result.xsd`） |

公共类 **`RodskiXmlValidator`**（`core.xml_schema_validator`）封装校验逻辑，也可在工具链中单独调用：

```python
from core.xml_schema_validator import RodskiXmlValidator

RodskiXmlValidator.validate_file("path/to/case.xml", RodskiXmlValidator.KIND_CASE)
```

校验失败时，异常信息中包含 `xml_path`、`document_kind`、`schema_path` 及 `validation_errors` 明细（若有）。

### 7.1 文件类型与 Schema 对照

| 文件类型 | Schema 文件 | 存放目录 | 对应原 Excel |
|---------|------------|---------|-------------|
| 用例 XML | `schemas/case.xsd` | `case/` | Case Sheet |
| 模型 XML | `schemas/model.xsd` | `model/` | model.xml（不变） |
| 数据表 XML | `schemas/data.xsd` | `data/` | 各数据表 Sheet |
| 全局变量 XML | `schemas/globalvalue.xsd` | `data/` | GlobalValue Sheet |
| 结果 XML | `schemas/result.xsd` | `result/` | TestResult + TestSummary Sheet |

### 7.2 Case XML 格式约束（三阶段 · 多 `test_step`）

每个 `<case>` 下**固定三个阶段容器**（XSD 顺序：`pre_process` → `test_case` → `post_process`）：

| 阶段容器 | XSD | 说明 |
|---------|-----|------|
| `<pre_process>` | 可选（0～1 个元素） | 预处理：内层 **0 个或多个** `<test_step>` |
| `<test_case>` | **必选且恰好 1 个** | 用例阶段：内层 **至少 1 个** `<test_step>`（原「测试步骤 + 预期验证」等均写在此阶段，按顺序多条步骤） |
| `<post_process>` | 可选（0～1 个元素） | 后处理：内层 **0 个或多个** `<test_step>` |

**执行语义（框架保证）**：

- 各阶段内按 `<test_step>` 出现顺序依次执行。
- **预处理**若某步失败：跳过**用例阶段**，**仍执行后处理**（便于清理）。
- **用例阶段**若某步失败：**仍执行后处理**（关闭浏览器、回滚等清理步骤）。
- **后处理**若失败：整条用例记为失败。

```xml
<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="c001" title="登录测试" description="..." component_type="界面">
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

| 属性/元素 | 必需 | 说明 |
|-----------|------|------|
| `case.execute` | 是 | `是` 或 `否`，只有 `是` 才执行 |
| `case.id` | 是 | 用例唯一编号 |
| `case.title` | 是 | 用例标题 |
| `case.description` | 否 | 用例描述 |
| `case.component_type` | 否 | `界面` / `接口` / `数据库` |
| `pre_process` | 否 | 预处理阶段容器；可省略或为空容器 |
| `test_case` | **是** | **每个 case 必须且仅有 1 个**；内至少 1 个 `test_step` |
| `post_process` | 否 | 后处理阶段容器 |
| `test_step`（子元素） | 每步 | `action` / `model` / `data` 与原先单行步骤含义相同 |
| `test_step.action` | 是 | 关键字名称（见第5节） |
| `test_step.model` | 否 | 模型名或连接名 |
| `test_step.data` | 否 | 数据引用或直接值 |

### 7.3 Data XML 格式约束

**支持两种格式**：

**格式1：合并文件（推荐）**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<datatables>
  <datatable name="Login">
    <row id="L001" remark="管理员登录">
      <field name="username">admin</field>
      <field name="password">admin123</field>
      <field name="loginBtn">click</field>
    </row>
  </datatable>
  <datatable name="Login_verify">
    <row id="V001">
      <field name="welcomeMsg">欢迎</field>
    </row>
  </datatable>
</datatables>
```

**格式2：单表文件**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<datatable name="Login">
  <row id="L001" remark="管理员登录">
    <field name="username">admin</field>
    <field name="password">admin123</field>
    <field name="loginBtn">click</field>
  </row>
</datatable>
```

| 属性/元素 | 必需 | 说明 |
|-----------|------|------|
| `datatables` | — | 合并文件的根元素，包含多个 `datatable` |
| `datatable` | — | 单表文件的根元素，或合并文件中的子元素 |
| `datatable.name` | 是 | 数据表名，**必须与模型名一致** |
| `row.id` | 是 | DataID，表内唯一 |
| `row.remark` | 否 | 备注说明 |
| `field.name` | 是 | 字段名，**必须与 model element name 一致** |
| field 文本内容 | — | 字段值（支持特殊值 BLANK/NULL/NONE、动作关键字、Return 引用） |

**文件覆盖规则**：
- 框架按顺序加载 `data.xml` → `data_verify.xml`
- 如果两个文件中存在同名表（`datatable.name` 相同），后加载的文件会**覆盖**先加载的表
- 建议：操作数据放 `data.xml`，验证数据使用 `{模型名}_verify` 表名

**多行多列表示**：
- **多行**：在同一 `<datatable>` 中定义多个 `<row>`，每个 row 有不同的 `id`
- **多列**：在同一 `<row>` 中定义多个 `<field>`，每个 field 有不同的 `name`
- 不同行可以有不同数量的字段

**完整示例**：
```xml
<datatables>
  <datatable name="Login">
    <!-- 第1行：管理员登录（4个字段） -->
    <row id="L001" remark="管理员登录">
      <field name="username">admin</field>
      <field name="password">admin123</field>
      <field name="userType">select【admin】</field>
      <field name="loginBtn">click</field>
    </row>
    <!-- 第2行：普通用户登录（3个字段） -->
    <row id="L002" remark="普通用户">
      <field name="username">testuser</field>
      <field name="password">test123</field>
      <field name="loginBtn">click</field>
    </row>
  </datatable>

  <datatable name="Login_verify">
    <row id="V001">
      <field name="welcomeMsg">欢迎</field>
    </row>
    <row id="V002">
      <field name="errorMsg">登录失败</field>
    </row>
  </datatable>
</datatables>
```

### 7.4 GlobalValue XML 格式约束

```xml
<?xml version="1.0" encoding="UTF-8"?>
<globalvalue>
  <group name="DefaultValue">
    <var name="URL" value="http://127.0.0.1:5555"/>
    <var name="WaitTime" value="2"/>
  </group>
</globalvalue>
```

| 属性/元素 | 必需 | 说明 |
|-----------|------|------|
| `group.name` | 是 | 变量组名，组内唯一 |
| `var.name` | 是 | 变量名，组内唯一 |
| `var.value` | 是 | 变量值 |

### 7.5 Model XML 格式约束（不变）

model.xml 格式与之前版本保持一致，支持完整格式和简化格式。详见 `schemas/model.xsd`。

### 7.6 Result XML 格式约束

```xml
<?xml version="1.0" encoding="UTF-8"?>
<testresult>
  <summary total="2" passed="1" failed="1" pass_rate="50.0%" .../>
  <results>
    <result case_id="c001" title="登录测试" status="PASS" execution_time="2.345" .../>
  </results>
</testresult>
```

结果 XML 由框架自动生成，用户不需要手动编写。

---

## 8. 固定与动态测试步骤（架构规划）

本节描述在「Case XML 固定步骤」与「CLI/运行时插入的动态步骤」并存时的**架构原则与约束**。实现可落在分支 `feature/dynamic-case-refactor` 上，落地前以本文为准。

### 8.1 目标与边界

| 能力 | 说明 |
|------|------|
| 固定步骤 | 来自 `case/*.xml` 的 `<test_step>`，顺序与内容在运行前已知 |
| 动态步骤 | 由 CLI 指令、扩展点或运行时策略在**执行过程中**插入的、与 Case 文件非一一对应的步骤 |
| 混合执行 | 同一用例阶段内，执行序列为「固定步骤流」与「动态步骤」的**可组合序列**（插入位置由策略决定，例如某固定步前后、或某关键字回调后） |
| 运行时控制 | 在固定步骤**执行过程中**，允许通过外部命令（如 CLI / 服务端下发）进行**暂停**、**插入**、**终止**，以改变后续执行路径（见 8.6） |

**非目标（首版可明确不做）**：在数据表 XML 中根据「动态步骤」解析 `Return[...]`（见 8.4）。

### 8.2 推荐设计模式（保障架构清晰）

| 模式 | 用途 |
|------|------|
| **Command（命令）** | 将单步执行抽象为统一对象（如 `StepCommand`）：携带 `action` / `model` / `data` 及元数据），`SKIExecutor` 只调用「执行一步」，不区分来源。 |
| **Strategy（策略）** | **步骤来源策略**：`StaticStepSource`（解析 XML）、`DynamicStepSource`（CLI/插件/钩子注入）。执行引擎依赖策略接口，而非具体来源。 |
| **Iterator / Pipeline（流水线）** | 对外表现为**统一的步骤迭代器**：先展开固定步骤，再在约定锚点**插入**动态步骤；遍历即执行，避免在执行循环里散落 `if cli` 分支。 |
| **Template Method（模板方法）** | `_run_steps` / `execute_case` 保持「阶段 → 遍历步骤 → 执行单步」骨架不变；**变化点**下放到「如何生成下一步」的策略与插入点配置。 |
| **Facade（可选）** | CLI / GUI 入口通过薄封装统一构造「策略组合 + 执行器」，避免调用方直接操作内部列表。 |

**原则**：执行主路径**只认「步骤序列」**，不认「文件行号」；XML 与 CLI 都**适配成同一套步骤描述结构**后再进入引擎。

### 8.3 步骤编号与结果留存（双轨）

为避免「动态插入」打乱追溯，采用**双轨编号**（实现时字段名可映射到代码/result 扩展）：

| 概念 | 含义 | 典型用途 |
|------|------|----------|
| **逻辑序号（固定）** | 仅针对 Case XML 中**固定** `<test_step>` 的顺序编号（如 1…N，可按阶段分别计数或全局计数，实现时需统一一种规则并文档化） | 与用例文件对齐、**Return 正索引**若表示「第 k 个固定步骤」则与此轨对齐 |
| **运行时序号** | 实际执行顺序的单调递增序号（1…M），**包含**所有固定 + 动态步骤 | 日志、自动截图命名、未来步骤级结果明细 |

**结果 XML（`result.xsd`）**：当前以**用例级**结果为主；若需步骤级追溯，应在后续版本中扩展 schema（例如每条用例下可选 `<steps>`，子节点带 `logical`、`runtime`、`source`），且须通过 XSD 校验。**不得**在未扩展 schema 的情况下写入非约定结构。

### 8.4 Return 关键字与 `-1` 语义（过渡期约束）

- **`${Return[-1]}`**：表示**固定步骤管线**中「上一步」的返回值（与当前 `KeywordEngine._return_values` 追加语义一致），**不**跨越动态插入步去指「物理上的上一步」，除非将来明确定义并实现「动态步是否入栈」。
- **动态步骤数据表**：**暂不支持**在数据表 XML 中使用 `${Return[...]}`引用动态步骤产生的数据；若需传参，首版应通过 **GlobalValue / 显式 set** 等既有机制传递。
- **正索引 `${Return[0]}` 等**：继续表示固定返回队列中的槽位；与动态步骤混跑时，**不得**假设与「运行时序号」一一对应。

### 8.5 CLI 与扩展点（约束）

- CLI 传入的动态命令应被解析为与 Case 同构的**步骤描述**（同一套关键字与参数规则），再进入 `StepCommand` 流水线。
- 插入点（在哪些固定步前后允许插入）应有**白名单或配置**，避免任意位置插入破坏预处理/用例/后处理语义。

### 8.6 运行时控制命令：暂停、插入、终止

在**固定步骤执行过程中**，执行器应支持一类**控制命令**（来源可为 CLI、本地 GUI、或**服务端**远程下发），用于改变测试执行行为。与「普通测试步骤」不同，控制命令属于**元操作**，不占用 Case XML 中的固定 `<test_step>` 行号。

| 命令 | 语义 | 实现要点 |
|------|------|----------|
| **暂停（pause）** | 当前执行流在**安全边界**（见 8.7）停住，不再继续执行后续步骤，直至收到**继续（resume）**或**终止** | 执行循环需可中断、可恢复；暂停期间可接受新命令（如插入） |
| **插入（insert）** | 在**当前固定步骤流**中插入一条或多条**新测试步骤**，立即执行或排队执行（由策略决定） | 插入的步骤**格式与现有 `<test_step>` 一致**（`action` / `model` / `data` 语义不变）；可附带**临时** `model` 片段与**临时**数据表（内存或临时目录中的 XML），经与正式模块相同的解析与校验流程后进入引擎 |
| **终止（terminate）** | 结束当前用例或当前执行会话 | 区分**正常终止**（在**当前步骤执行完成后**停止）与**强制终止**（见 8.7） |

**插入步骤的格式约束**：

- 与 Case XML 中 `test_step` **同一套**关键字与参数模型；不得引入第二套「动态专用」语法。
- 若使用临时模型 / 数据：应在执行上下文中**注册为临时资源**（生命周期限于本次插入或本会话），避免污染磁盘上的正式 `model/`、`data/`；或写入约定临时目录并在会话结束后清理。

### 8.7 服务端命令与「当前步骤执行中」的时序（默认排队）

当**服务端**（或远程控制端）下发控制命令，而**当前测试步骤正在执行**（例如一次 `type` 批量、一次 `send`、一次 `run` 子进程尚未返回）时：

| 情形 | 默认行为 |
|------|----------|
| **一般命令**（暂停、插入、非强制的终止） | **等待当前步骤执行结束**（进入关键字后的整步执行完成）后，再处理该命令。即命令进入**队列**，按到达顺序在**步骤边界**生效。 |
| **强制终止** | **不要求**等待当前步骤自然结束；执行器应在**安全前提下**尽快中止（如取消后续步骤、关闭浏览器/会话、必要时终止子进程）。具体可中断点与资源清理顺序需在实现中明确并文档化。 |

**设计理由**：

- 步骤内部往往是对驱动、子进程、数据库事务的**原子意图**；中途打断易导致状态不一致。
- 强制终止是**显式**的例外路径，用于卡死、超时或人工紧急停止。

**执行器侧**建议抽象「步骤边界」：单步 `execute_step` 前后为**可接受控制命令**的时机；步内除非强制终止，不处理队列中的暂停/插入。

---

### 8.8 动态机制中的多模态问题判别（规划，未来实现）

在动态用例机制下，框架应支持一个“问题判别器（Issue Classifier）”接口，用于判断失败根因，服务于自动处置策略。

#### 8.8.1 输入证据（可扩展）

- 步骤上下文：`case_id`、phase、action/model/data、运行时序号
- 执行证据：错误码、异常栈、日志片段
- 界面证据：失败截图（必要时可含前后对比）
- 网络/接口证据：请求与响应摘要（状态码、关键字段）
- 历史证据：同用例最近 N 次运行结果与变化趋势

#### 8.8.2 输出分类（标准化）

- `CASE_DEFECT`：用例/数据/断言定义问题
- `ENV_DEFECT`：环境或依赖服务异常
- `PRODUCT_DEFECT`：疑似产品缺陷
- `UNKNOWN`：证据不足，需人工确认

判别输出必须包含：

- `category`（上述分类）
- `confidence`（0~1）
- `evidence_refs`（引用的日志/截图/响应证据）
- `recommended_action`（建议动作：insert/pause/terminate/escalate）

#### 8.8.3 设计约束

- 判别器是**可替换组件**：可先规则引擎，再替换为多模态 LLM。
- 若接入多模态 LLM，必须保留“证据引用 + 置信度”，禁止裸结论。
- 低置信度（如 < 0.6）不得自动执行高风险动作（如 `force_terminate`），需降级为人工确认或仅 `pause`。
- 判别结果属于“策略输入”，不直接改写原始执行结果；最终状态仍由执行器语义决定（PASS/FAIL/SKIP/ERROR）。

---

## 9. 自检约束 — 不依赖外部测试框架

### 9.1 原则

RodSki 的**框架自身测试（自检）不得依赖任何外部测试框架**（`pytest`、`nose`、`unittest` runner 等）。
原因：

1. RodSki **本身就是测试执行器**，若自身的质量验证依赖外部框架，在概念上构成循环依赖。
2. 减少外部依赖 → 部署简单、CI 环境零配置。
3. 不需要 `PYTHONPATH=.` 或 `pip install -e .` 等额外步骤，直接 `python selftest.py` 即可。

### 9.2 自有测试执行器

| 文件 | 作用 |
|------|------|
| `core/test_runner.py` | **`RodskiTestRunner`** — 自动发现 `tests/` 下 `test_*.py` 中的 `Test*` 类与 `test_*` 方法，逐个执行，输出 PASS/FAIL 摘要 |
| `selftest.py` | 入口脚本，自动设置 `sys.path`，无需 `PYTHONPATH` 黑科技 |

### 9.3 运行方式

```bash
cd rodski

# 跑全部测试
python selftest.py

# 指定文件
python selftest.py tests/unit/test_case_parser.py

# 多文件
python selftest.py tests/unit/test_case_parser.py tests/unit/test_auto_screenshot.py tests/unit/test_xml_schema_validator.py

# 详细输出
python selftest.py -v
```

### 9.4 测试编写规范

| 规则 | 说明 |
|------|------|
| **禁止 `import pytest`** | 测试文件中不得出现 `pytest` 相关导入 |
| 临时目录 | 测试方法声明 `tmp_path` 参数，执行器自动注入 `pathlib.Path` 临时目录 |
| 异常断言 | 使用 `core.test_runner.assert_raises(ExcType, func, ...)` |
| 模式匹配 | 使用 `core.test_runner.assert_raises_match(ExcType, pattern, func, ...)` |
| setup/teardown | 类上定义 `setup_method()` / `teardown_method()`，每个测试方法前后调用 |
| 断言 | 直接使用 Python `assert` 语句 |
| Mock | 可使用标准库 `unittest.mock`（不引入外部包） |

### 9.5 禁止事项

- ❌ `requirements.txt` 中列出 `pytest` / `pytest-cov` 等
- ❌ `pyproject.toml` 中配置 `[tool.pytest]`
- ❌ 测试文件中使用 `@pytest.fixture`、`pytest.raises`、`pytest.mark` 等
- ❌ 需要 `PYTHONPATH=.` 才能运行测试

---

## 10. 视觉定位设计约束

### 10.1 OmniParser 作为图像坐标识别核心

**设计决策**: RodSki 使用 **OmniParser** 作为图像坐标识别的核心能力。

**架构原则**:
- OmniParser 提供页面元素的坐标和内容识别
- 多模态 LLM（Claude/GPT-4V/Qwen-VL）提供语义理解
- 视觉定位作为**定位器类型**，不是独立关键字

### 10.2 视觉定位器类型（统一格式）

视觉定位通过扩展模型 `location type` 属性实现，不新增关键字：

| 定位器类型 | 格式 | 说明 | 示例 |
|-----------|------|------|------|
| `vision` | `<location type="vision">图片路径</location>` | 图片模板匹配定位 | `<location type="vision">img/login_btn.png</location>` |
| `ocr` | `<location type="ocr">文字</location>` | OCR文字识别定位 | `<location type="ocr">登录</location>` |
| `vision_bbox` | `<location type="vision_bbox">x1,y1,x2,y2</location>` | 坐标定位（Agent 探索生成） | `<location type="vision_bbox">100,200,150,250</location>` |

### 10.3 模型定义格式

```xml
<!-- 图片定位 -->
<element name="loginBtn" type="web">
    <type>button</type>
    <location type="vision">img/login_btn.png</location>
</element>

<!-- OCR文字定位 -->
<element name="loginBtn" type="web">
    <type>button</type>
    <location type="ocr">登录</location>
</element>

<!-- 坐标定位（Agent 探索后生成） -->
<element name="submitBtn" type="web">
    <type>button</type>
    <location type="vision_bbox">100,200,150,250</location>
</element>
```

**约束**：
- 使用 `<location type="类型">值</location>` 格式，与传统定位器一致
- `vision` 值为图片路径（相对于 `images/` 目录）
- `ocr` 值为要识别的文字内容
- `vision_bbox` 坐标为像素坐标（Web）或屏幕绝对坐标（Desktop）

### 10.4 使用现有关键字

视觉定位复用现有关键字，不新增 `vision_click` 等：

```xml
<!-- 使用 type 关键字 -->
<test_step action="type" model="LoginPage" data="L001"/>
```

数据表：
```xml
<row id="L001">
  <field name="loginBtn">click</field>
  <field name="username">admin</field>
</row>
```

### 10.5 Agent 与 RodSki 的职责划分

**RodSki 的职责**：
- ✅ 执行 XML 定义的操作
- ✅ 支持视觉定位器类型（vision/vision_bbox）
- ✅ 返回结构化的执行结果
- ✅ 提供工具辅助 Agent 生成 XML

**Agent 的职责**：
- ✅ 探索页面/应用（使用自己的视觉能力）
- ✅ 生成模型 XML（使用 LLM 能力）
- ✅ 决策执行策略（选择用例、插入步骤）
- ✅ 处理执行结果并调整

**协作模式**：
```
1. Agent 探索 → 发现元素和操作路径
2. Agent 生成 XML → 记录为活文档
3. Agent 调用 RodSki → 执行 XML
4. RodSki 返回结果 → Agent 分析并决策下一步
```

### 10.6 辅助工具（可选）

RodSki 可提供工具辅助 Agent 生成 XML：

```bash
# 验证模型 XML 格式
rodski validate-model model/model.xml

# 从元素信息生成模型 XML 模板
rodski generate-model --elements elements.json \
                      --model-name LoginPage \
                      --output model_template.xml
```

**注意**：这些是辅助工具，不是探索功能。探索由 Agent 完成。

1. 框架读取模型定义，识别 `type="vision"` 或 `type="vision_bbox"`
2. 调用 OmniParser 服务获取页面元素坐标
3. 使用 LLM 进行语义匹配（仅 `vision` 类型）
4. 返回目标元素坐标
5. 使用坐标驱动器执行操作（点击/输入）

### 10.7 约束规则

- ❌ 不新增 `vision_click`、`vision_input` 等关键字
- ❌ 不在 Case XML 中直接写坐标
- ✅ 视觉定位作为模型定位器类型
- ✅ 复用现有 14 个关键字
- ✅ 坐标信息记录在模型 XML 中

---

## 11. 桌面平台约束

### 11.1 平台标识

桌面平台使用操作系统类型作为 `driver_type`：

| driver_type | 说明 | 适用场景 |
|------------|------|---------|
| `windows` | Windows 桌面应用 | Win10/Win11 桌面自动化 |
| `macos` | macOS 桌面应用 | macOS 桌面自动化 |

### 11.2 桌面端设计原则

**核心原则**：
- ✅ 关键字统一：type/verify/launch 与 Web 平台完全相同
- ✅ 驱动分离：桌面使用 pyautogui + OmniParser 驱动
- ✅ 视觉定位为主（vision/ocr/vision_bbox）
- ❌ 不支持接口测试（`send` 关键字不适用于桌面端）

**统一关键字示例**：

```xml
<!-- Web 平台 -->
<test_step action="navigate" model="WebApp" data="L001"/>
<test_step action="type" model="LoginPage" data="T001"/>

<!-- Desktop 平台（关键字完全相同） -->
<test_step action="launch" model="DesktopApp" data="L001"/>
<test_step action="type" model="LoginPage" data="T001"/>
```

**模型定义驱动类型**：
```xml
<!-- Web 模型 -->
<element name="loginBtn" type="web">
    <location type="id">loginBtn</location>
</element>

<!-- Desktop 模型 -->
<element name="loginBtn" type="windows">
    <location type="ocr">登录</location>
</element>
```

### 11.3 vision_bbox 坐标约定

桌面场景下 `vision_bbox` 使用**屏幕绝对坐标**：

```xml
<!-- 桌面应用元素 -->
<element name="closeBtn" type="windows">
    <type>button</type>
    <location type="vision_bbox">1850,50,1900,100</location>
</element>
```

**约束**：
- 坐标为屏幕绝对像素坐标（左上角为 0,0）
- 桌面应用执行时**默认全屏**，避免窗口位置变化导致坐标偏移
- 非全屏应用需在模型中记录窗口位置信息

### 11.4 Desktop 驱动实现

桌面驱动基于 pyautogui + OmniParser：

| 功能 | 实现方式 |
|------|---------|
| 启动应用 | pyautogui 或 subprocess |
| 截图 | pyautogui.screenshot() |
| 定位元素 | vision(OpenCV) / ocr(OmniParser) / vision_bbox(坐标) |
| 点击 | pyautogui.click(x, y) |
| 输入 | pyautogui.typewrite(text) |
| 获取文字 | OmniParser OCR |

**约束**：
- 桌面驱动仅支持视觉定位器（vision/ocr/vision_bbox）
- 传统定位器（id/css/xpath）在桌面端不可用

---

*文档版本: v3.7 | 最后更新: 2026-03-27*
