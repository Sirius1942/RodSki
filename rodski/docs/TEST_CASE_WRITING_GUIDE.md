# RodSki 用例编写指南

**版本**: v3.3  
**日期**: 2026-03-24  
**适用框架**: RodSki v3.0+

---

## 目录

1. [核心概念：关键字 + 模型 + 数据](#1-核心概念关键字--模型--数据)
2. [目录结构](#2-目录结构)
3. [Case XML — 用例编写](#3-case-xml--用例编写)
4. [model.xml — 模型编写](#4-modelxml--模型编写)
5. [数据表 XML — 测试数据编写](#5-数据表-xml--测试数据编写)
6. [GlobalValue XML — 全局变量](#6-globalvalue-xml--全局变量)
7. [数据引用与变量解析](#7-数据引用与变量解析)
8. [关键字手册](#8-关键字手册)
9. [完整示例](#9-完整示例)
10. [固定与动态测试步骤（规划）](#10-固定与动态测试步骤规划)
11. [视觉定位器（vision / vision_bbox）](#11-视觉定位器vision--vision_bbox)
12. [桌面端自动化（Desktop）](#12-桌面端自动化desktop)
13. [附录：常见问题](#附录常见问题)
14. [附录：测试结果 XML（result.xsd）](#附录测试结果-xmlresultxsd)

---

## 1. 核心概念：关键字 + 模型 + 数据

RodSki 的用例由三部分组成：

```
用例 = 关键字（做什么动作） + 模型（对哪些元素） + 数据（用什么值）
```

| 组成部分 | 作用 | 存储位置 |
|---------|------|---------|
| 关键字 | 定义操作类型（type UI输入 / send 接口请求 / verify 批量验证 …） | Case XML 的 `action` 属性 |
| 模型 | 定义页面元素 / 接口字段的定位信息 | model.xml 文件 |
| 数据 | 定义输入值 / 期望值 / 配置参数 | data/ 目录下的 XML 文件 + globalvalue.xml |

这三者的协作方式：

- **type（UI 写入）**：关键字 `type` + 模型 `Login` + 数据 `L001` → 框架遍历 Login 模型的每个元素，从 Login.xml 取对应字段的值，逐一输入到界面
- **send（接口请求）**：关键字 `send` + 模型 `LoginAPI` + 数据 `D001` → 框架从 LoginAPI 模型获取请求方式和 URL，从 LoginAPI.xml 取字段值，发送 HTTP 请求
- **verify（验证）**：关键字 `verify` + 模型 `Login` + 数据 `V001` → 框架遍历 Login 模型的每个元素，从界面/接口读取实际值，与 Login_verify.xml 的期望值逐字段比较

**关键规则：模型元素 name = 数据表字段 name**。这是整个框架运转的基础。

---

## 2. 目录结构

v3.0 版本使用 XML 文件替代 Excel，每个测试模块按如下固定结构组织：

```
product/                           ← 产品根目录（最顶层）
└── {测试项目名}/                   ← 测试项目
    └── {测试模块名}/               ← 测试模块（业务）
        ├── case/                  ← 测试用例 XML
        │   └── demo_case.xml
        ├── model/                 ← 模型 XML
        │   └── model.xml
        ├── fun/                   ← 代码工程（run 关键字）
        │   └── data_gen/
        │       └── gen_phone.py
        ├── data/                  ← 数据 XML + 全局变量
        │   ├── globalvalue.xml    ← 全局变量（固定文件名）
        │   ├── Login.xml          ← 数据表（与模型同名）
        │   ├── Login_verify.xml   ← 验证数据表
        │   └── QuerySQL.xml       ← SQL 数据表
        └── result/                ← 测试结果（框架自动生成）
            └── result_20260321_100000.xml
```

### 2.1 原 Excel 到 XML 的映射

| 原 Excel | 新 XML | 位置 |
|---------|--------|------|
| Case Sheet | case/*.xml | `case/` 目录 |
| GlobalValue Sheet | globalvalue.xml | `data/` 目录 |
| 数据表 Sheet（如 Login） | {模型名}.xml | `data/` 目录 |
| 验证数据表 Sheet（如 Login_verify） | {模型名}_verify.xml | `data/` 目录 |
| TestResult Sheet | result_*.xml | `result/` 目录 |
| model.xml | model.xml（不变） | `model/` 目录 |

### 2.2 Schema 约束（与 `rodski/schemas` 对齐）

手工编写的 XML 建议用本仓库 XSD 做校验，约束以 XSD 为准；下面是与**用例编写**直接相关的摘要（完整定义见各文件内 `<xs:annotation>`）。

| XSD 文件 | 根元素 | 编写方 | 核心约束（摘要） |
|----------|--------|--------|------------------|
| `case.xsd` | `<cases>` | 人工 | 每个 `<case>` **必须且仅有 1 个** `<test_case>` 容器，其内 **至少 1 个** `<test_step>`；`<pre_process>` / `<post_process>` 各 **0～1 个**容器，内为 **0～n 个** `<test_step>`。`execute` 只能是 `是` \| `否`。`component_type`（可选）只能是 `界面` \| `接口` \| `数据库`。每个 `test_step` 的 `action` 为 `ActionType` 枚举（见 [3.5](#35-action-与-casexsd-枚举一致)）。 |
| `model.xsd` | `<models>` | 人工 | `<model>` 须 `name`；`<element>` 须 `name`。支持**完整格式**（子节点 `<type>` / `<location>` / `<desc>`）与**简化格式**（`element` 上 `type`+`value`，此时 `type` 为定位类型）。`DriverType` / `LocatorType` 取值见 [4.2](#42-元素属性说明)、[4.3](#43-定位类型)。接口保留元素名：`_method`、`_url`、`_header_*`（与数据字段一一对应）。 |
| `data.xsd` | `<datatable>` | 人工 | `datatable@name` **必须与文件名一致**（不含 `.xml`）。每个 `<row>` 须 `id`（DataID）；**同一数据表内** `row@id` **全局唯一**（XSD `xs:unique`）。每行至少一个 `<field>`，`field@name` 须与对应模型元素 `name` 一致。验证表文件名为 `{模型名}_verify.xml`。 |
| `globalvalue.xsd` | `<globalvalue>` | 人工 | 每个 `<group>` 须 `name`；**所有 group 的 `name` 全局唯一**。每组内至少一个 `<var>`，每个 `var` 须同时具备 `name` 与 `value`；**同一 group 内** `var@name` **唯一**（XSD `xs:unique`）。引用格式：`GlobalValue.组名.变量名`。 |
| `result.xsd` | `<testresult>` | **框架生成** | 手工一般无需编写；结构见 [附录：测试结果 XML](#附录测试结果-xmlresultxsd)。 |

本地校验示例（需安装 `xmllint`，Mac 可用 Xcode 命令行工具）：

```bash
xmllint --noout --schema rodski/schemas/case.xsd product/DEMO/demo_site/case/demo_case.xml
```

---

## 3. Case XML — 用例编写

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
| `get_text` | 已废弃，请改用 `get` |
| `get` | 双模式取值（CSS 选择器 → UI 文本；变量名 → 命名变量） |
| `evaluate` | 执行 JS 表达式（**仅 Web**，低优先级，结构化结果保留原类型） |
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

## 4. model.xml — 模型编写

### 4.1 文件结构

```xml
<?xml version="1.0" encoding="UTF-8"?>
<models>
  <model name="模型名称" servicename="">
    <element name="元素名称" interfacename="" group="" type="web">
      <type>元素类型</type>
      <location type="定位类型" item="">定位值</location>
      <desc>描述（可选）</desc>
    </element>
  </model>
</models>
```

### 4.2 元素属性说明

**与 `model.xsd` 一致**：`<element>` 上 **`name` 为唯一必填属性**；`type`（属性）、`value`、`interfacename`、`group` 均为可选（有默认值时可省略）。

| 属性/子节点 | XSD | 实践建议 | 说明 |
|------------|-----|----------|------|
| `name` | **必填** | **必填** | 元素名称，**必须与数据表字段 name 一致**（区分大小写） |
| `type`（element 属性） | 可选 | Web/接口模型建议填 | **完整格式**：驱动类型 `web` / `interface` / `other`。**简化格式**：与 `LocatorType` 相同，表示定位类型，需配合 `value` |
| `value` | 可选 | 简化格式建议成对出现 | 与简化格式 `type` 配对，表示定位值 |
| `<type>` 子节点 | 可选 | Web 常用 | UI 控件语义：input / button / select / text / textarea |
| `<location type="...">` | 可选 | 完整格式常用 | `location@type` 取值见 [4.3](#43-定位类型)（`LocatorType`） |
| `<desc>` | 可选 | — | 元素描述，便于维护 |

> **运行时**：除 XSD 外，实际执行仍需要可用的定位信息——**完整格式**建议写 `type="web|interface|other"` + `<location>`；**简化格式**写 `type`（定位类型）+ `value`。

### 4.3 定位器类型（完整）

RodSki 支持 12 种定位器类型，分为传统定位器和视觉定位器两大类。

#### 4.3.1 传统定位器

| type 值 | 转换规则 | 示例 |
|---------|---------|------|
| `id` | → CSS `#定位值` | `<location type="id">username</location>` → `#username` |
| `class` | → CSS `.定位值` | `<location type="class">btn-submit</location>` → `.btn-submit` |
| `css` | → 原样使用 | `<location type="css">input[name="user"]</location>` |
| `xpath` | → 原样使用 | `<location type="xpath">//input[@id='user']</location>` |
| `text` | → Playwright `text=...` | `<location type="text">登录</location>` → `text=登录` |
| `tag` | → 标签名选择器 | `<location type="tag">button</location>` |
| `name` | name 属性选择器 | 按框架解析规则使用 |
| `static` | 静态字面量 | 常用于接口 `_method`、固定 URL 等 |
| `field` | 接口字段映射 | 常用于接口 body / query 字段名 |

#### 4.3.2 视觉定位器

| type 值 | 格式 | 说明 | 示例 |
|---------|------|------|------|
| `vision` | 图片匹配 | 通过截图/图片模板匹配定位 | `<location type="vision">img/login_btn.png</location>` |
| `ocr` | 文字识别 | 通过 OCR 识别文字定位 | `<location type="ocr">登录</location>` |
| `vision_bbox` | 坐标定位 | 直接使用坐标 `x1,y1,x2,y2` | `<location type="vision_bbox">100,200,150,250</location>` |

**视觉定位器说明**：

- **`vision` 图片定位器**：
  - 值为图片路径（相对于 `images/` 目录）
  - 通过图像匹配算法定位
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

#### 4.3.3 定位器格式约束

**格式规范**：
1. 所有定位器使用 `<location type="类型">值</location>` 格式
2. `type` 属性必须为 LocatorType 枚举值之一
3. 值写在 location 标签内容中

**正确示例**：
```xml
<!-- ✅ 正确：完整格式 -->
<element name="loginBtn" type="web">
    <type>button</type>
    <location type="id">loginBtn</location>
</element>

<!-- ✅ 正确：简化格式 -->
<element name="loginBtn" type="id" value="loginBtn"/>
```

**错误示例**：
```xml
<!-- ❌ 错误：不要使用 locator 属性 -->
<element name="loginBtn" locator="vision:登录按钮"/>
```

**示例对比**：
```xml
<!-- 同一个登录按钮，三种定位方式 -->

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

### 4.4 简化格式

对于简单场景，也支持单行格式：

```xml
<element name="username" type="id" value="userName"/>
```

此格式下 **属性** `type` 为 **`LocatorType` 定位类型**（不是 `web`），`value` 为定位值；驱动语义由框架按场景处理（一般为 Web）。

### 4.5 多定位器格式（自动切换）

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

### 4.6 核心约束：元素名 = 数据表字段名

```
model.xml 元素 name  ===  数据表 XML 的 field name
```

这是 `type`（批量输入）和 `verify`（批量验证）的运转基础。框架遍历模型元素时，用 `name` 去数据表中查找对应字段的值。

正确示例：

```xml
<!-- model.xml -->
<element name="username"><location type="id">userName</location></element>
<element name="password"><location type="id">password</location></element>
```

```xml
<!-- data/Login.xml -->
<datatable name="Login">
  <row id="L001" remark="有效">
    <field name="username">admin</field>     ← name 与 model 一致
    <field name="password">admin123</field>  ← name 与 model 一致
  </row>
</datatable>
```

### 4.6 完整示例

```xml
<?xml version="1.0" encoding="UTF-8"?>
<models>
<model name="Login" servicename="">
    <element name="username" interfacename="" group="" type="web">
        <type>input</type>
        <location type="id" item="">username</location>
        <desc>用户名输入框</desc>
    </element>
    <element name="password" interfacename="" group="" type="web">
        <type>input</type>
        <location type="id" item="">password</location>
        <desc>密码输入框</desc>
    </element>
    <element name="loginBtn" interfacename="" group="" type="web">
        <type>button</type>
        <location type="id" item="">login-btn</location>
        <desc>登录按钮</desc>
    </element>
</model>
</models>
```

---

## 5. 数据表 XML — 测试数据编写

### 5.1 文件格式

每个数据表是一个独立的 XML 文件，存放在 `data/` 目录下。**文件名 = 数据表名**（不含 .xml 后缀）。

```xml
<?xml version="1.0" encoding="UTF-8"?>
<datatable name="Login">
  <row id="L001" remark="管理员登录">
    <field name="username">admin</field>
    <field name="password">admin123</field>
    <field name="loginBtn">click</field>
  </row>
  <row id="L002" remark="普通用户">
    <field name="username">testuser</field>
    <field name="password">test123</field>
  </row>
</datatable>
```

### 5.2 结构规则

| 属性/元素 | 必需 | 说明 |
|-----------|------|------|
| `datatable.name` | 是 | 数据表名，**必须与文件名一致**（与 `data.xsd` 文档说明一致） |
| `row.id` | 是 | DataID（数据行唯一标识） |
| **同一表内 `row.id` 唯一** | 是 | **XSD 约束**（`xs:unique`）：任意两行不得重复同一 `id` |
| `row.remark` | 否 | 备注说明（框架不使用） |
| `field.name` | 是 | 字段名，**必须与 model 元素 name 一致** |
| field 文本 | — | 字段值（空值表示跳过） |

### 5.3 数据表命名与引用规则

> **核心规则**：模型名 = 数据表文件名，强制一致。数据列只写 DataID，不写表名。

| 关键字 | Case 写法 | 数据文件（自动推导） |
|--------|-----------|---------------------|
| `type` | `type Login L001` | `data/Login.xml` |
| `verify` | `verify Login V001` | `data/Login_verify.xml` |

### 5.4 批量输入时的特殊值

在数据表的字段值中，以下值有特殊含义：

#### 控制值

| 特殊值 | Web 行为 | 接口行为 |
|--------|---------|---------|
| `.Password` 后缀 | 输入时去掉后缀，日志中显示 `***` | — |
| 空值（省略 field） | 跳过该元素（不输入） | — |
| `BLANK` | 跳过（UI）/ 空字符串（接口） | 传空字符串 |
| `NULL` / `NONE` | 跳过（UI） | 传 null / none |

#### UI 动作关键字

数据表 field 中可以写入以下 **UI 动作关键字**，`type` 批量模式会自动识别并执行对应操作：

| 动作值 | 说明 | 示例 |
|--------|------|------|
| `click` | 点击该元素 | `<field name="loginBtn">click</field>` |
| `double_click` | 双击该元素 | `<field name="item">double_click</field>` |
| `right_click` | 右键点击该元素 | `<field name="menu">right_click</field>` |
| `hover` | 鼠标悬停到该元素 | `<field name="tooltip">hover</field>` |
| `select【选项值】` | 下拉选择指定值 | `<field name="role">select【管理员】</field>` |
| `key_press【按键】` | 按下键盘按键 | `<field name="password">key_press【Tab】</field>` |
| `key_press【组合键】` | 按下组合键 | `<field name="input">key_press【Control+C】</field>` |
| `drag【目标定位器】` | 拖拽元素到目标位置 | `<field name="card">drag【#drop-zone】</field>` |
| `scroll` | 默认滚动（向下 300px） | `<field name="page">scroll</field>` |
| `scroll【x,y】` | 自定义滚动距离 | `<field name="page">scroll【0,500】</field>` |

> **注意**：动作关键字使用中文方括号 **【】** 包裹参数。

#### key_press 按键参考

`key_press` 支持 Playwright 的所有按键名称：

| 分类 | 按键名 | 示例写法 |
|------|--------|---------|
| 功能键 | `Tab` `Enter` `Escape` `Backspace` `Delete` | `key_press【Tab】` |
| 方向键 | `ArrowUp` `ArrowDown` `ArrowLeft` `ArrowRight` | `key_press【ArrowDown】` |
| 修饰键组合 | `Control+A` `Control+C` `Control+V` `Control+Z` | `key_press【Control+A】` |
| Shift 组合 | `Shift+Tab` `Shift+Enter` | `key_press【Shift+Tab】` |
| Alt 组合 | `Alt+F4` | `key_press【Alt+F4】` |
| 多键组合 | `Control+Shift+I` | `key_press【Control+Shift+I】` |
| F 功能键 | `F1` `F5` `F12` | `key_press【F5】` |

> 组合键使用 `+` 连接，修饰键在前、普通键在后。macOS 上 `Control` 对应 `Command` 键行为。

#### 示例：含动作关键字的数据表

```xml
<!-- data/Login.xml -->
<datatable name="Login">
  <row id="L001" remark="管理员登录">
    <field name="username">admin</field>
    <field name="password">admin123</field>
    <field name="loginBtn">click</field>
    <field name="roleSelect">select【管理员】</field>
  </row>
  <row id="L002" remark="Tab切换">
    <field name="username">admin</field>
    <field name="password">key_press【Tab】</field>
    <field name="loginBtn">click</field>
  </row>
</datatable>
```

Case XML 写 `type Login L001` 时，框架遍历 Login 模型：
1. `username` → 输入 "admin"
2. `password` → 输入 "admin123"
3. `loginBtn` → 执行点击
4. `roleSelect` → 下拉选择 "管理员"

### 5.5 SQL 数据表

DB 关键字使用的 SQL 也放在数据 XML 中：

```xml
<!-- data/QuerySQL.xml -->
<datatable name="QuerySQL">
  <row id="Q001" remark="查询总数">
    <field name="sql">SELECT COUNT(*) as cnt FROM items</field>
    <field name="operation">query</field>
  </row>
  <row id="Q002" remark="插入数据">
    <field name="sql">INSERT INTO items (name) VALUES ('test')</field>
    <field name="operation">execute</field>
  </row>
</datatable>
```

| 字段名 | 说明 |
|--------|------|
| sql | 要执行的 SQL 语句 |
| operation | `query`（查询，返回结果集）或 `execute`（增删改，返回受影响行数） |
| var_name | 可选，将结果存入变量 |

### 5.6 数据表中使用 Return 引用

Return 引用**应写在数据表的字段值中**，不应直接写在 Case XML。

示例：验证上一步创建的物品

```xml
<!-- data/VerifyData.xml -->
<datatable name="VerifyData">
  <row id="V001" remark="验证新物品名称">
    <field name="itemName">${Return[-1]}</field>
  </row>
</datatable>
```

Case XML 写法（验证写在 `<test_case>` 内，作为一条 `test_step`）：

```xml
<test_case>
  <test_step action="verify" model="ItemDetail" data="VerifyData.V001"/>
</test_case>
```

---

## 6. GlobalValue XML — 全局变量

### 6.1 文件格式

全局变量文件固定命名为 `globalvalue.xml`，存放在 `data/` 目录下。

**与 `globalvalue.xsd` 一致**：全文件内 **`<group name="...">` 不得重名**；同一 `<group>` 内 **`<var name="...">` 不得重名**；每个 `<var>` 必须同时有 `name` 与 `value` 属性。

```xml
<?xml version="1.0" encoding="UTF-8"?>
<globalvalue>
  <group name="DefaultValue">
    <var name="URL" value="http://127.0.0.1:5555"/>
    <var name="BrowserType" value="chromium"/>
    <var name="WaitTime" value="2"/>
  </group>
  <group name="demodb">
    <var name="type" value="sqlite"/>
    <var name="database" value="product/DEMO/demo_site/demo.db"/>
  </group>
</globalvalue>
```

### 6.2 引用语法

```
GlobalValue.组名.变量名
```

示例：

```
GlobalValue.DefaultValue.URL          → "http://127.0.0.1:5555"
GlobalValue.DefaultValue.WaitTime     → "2"
```

### 6.3 框架内置全局变量

| 组名 | Key | 说明 | 示例值 |
|------|-----|------|--------|
| DefaultValue | URL | 测试环境地址 | http://127.0.0.1:5555 |
| DefaultValue | BrowserType | 浏览器类型 | chromium / firefox / webkit |
| DefaultValue | WaitTime | 每步执行后自动等待秒数 | 2 |
| DefaultValue | Headless | 无头模式 | True / False |

### 6.4 WaitTime — 默认步骤等待时间

设置 `DefaultValue.WaitTime` 后，框架在**每个步骤执行完成后**自动等待指定秒数。

| 关键字 | 是否应用 WaitTime |
|--------|-----------------|
| navigate / type / click / verify 等 | 是 |
| wait | 否（wait 自身已包含等待） |
| close | 否（浏览器已关闭） |

### 6.5 数据库连接配置

DB 关键字通过 GlobalValue 中的组名获取连接参数：

| 组名 | Key | 说明 |
|------|-----|------|
| demodb | type | 数据库类型：sqlite / mysql / postgresql / sqlserver |
| demodb | host | 主机地址（sqlite 不需要） |
| demodb | port | 端口号（sqlite 不需要） |
| demodb | database | 数据库名或文件路径 |
| demodb | username | 用户名 |
| demodb | password | 密码 |

Case XML 中 DB 关键字的 `model` 属性填写组名（如 `demodb`），框架根据该组名查找连接配置。

---

## 7. 数据引用与变量解析

### 7.1 解析顺序

框架在执行步骤前，对 Case XML `data` 属性的值按以下顺序解析：

1. **GlobalValue 引用**：`GlobalValue.组名.变量名` → 替换为对应值
2. **数据表字段引用**：`表名.DataID.字段名` → 替换为数据表中的值
3. **Return 引用**：`Return[-1]` / `Return[0]` → 替换为步骤返回值

### 7.2 支持的引用格式

| 格式 | 说明 | 示例 |
|------|------|------|
| `GlobalValue.组名.Key` | 全局变量 | `GlobalValue.DefaultValue.URL` |
| `表名.DataID` | 整行数据（用于 type/verify） | `Login.L001` |
| `表名.DataID.字段名` | 单个字段值 | `Login.L001.username` |
| `${Return[-1]}` | 上一步返回值 | 写在**数据表 field**中 |
| `${Return[-2]}` | 上上步返回值 | 写在**数据表 field**中 |
| `${Return[0]}` | 第一步返回值 | 写在**数据表 field**中 |

### 7.3 Return 引用的正确用法

Return 引用**只应出现在数据表 XML 的 field 值中**，不要写在 Case XML 的 `data` 属性。

原因：Case XML `data` 属性中如果写 `${Return[-1]}`，会在进入关键字前被替换成字符串，导致 verify 无法走批量验证模式。

正确做法：

```xml
<!-- data/VerifyData.xml -->
<datatable name="VerifyData">
  <row id="V001" remark="验证订单">
    <field name="orderNo">${Return[-1]}</field>
  </row>
</datatable>
```

```xml
<!-- Case XML：verify 作为 test_case 内一步 -->
<test_case>
  <test_step action="verify" model="OrderDetail" data="VerifyData.V001"/>
</test_case>
```

**与动态步骤（规划）**：若未来支持「CLI/运行时插入步骤」，`${Return[-1]}` 仍表示**固定步骤**管线中的「上一步」；**不要**在数据表中用 `${Return}` 引用仅由动态步骤产生的数据。详见 **[§10](#10-固定与动态测试步骤规划)** 与《核心设计约束》第 8 节。

### 7.4 哪些关键字会产生 Return 值

| 关键字 | 返回值内容 |
|--------|-----------|
| get / get_text | 元素文本（get_text 已废弃，请使用 get） |
| verify | 批量验证时的实际值字典 |
| assert | 断言结果 |
| type（批量模式） | 本次输入使用的完整数据行 |
| send | HTTP 响应（含 `status` 状态码 + 响应体字段） |
| DB | query → 结果集列表；execute → 受影响行数 |
| run | 脚本 stdout 输出（自动尝试 JSON 解析） |

---

## 8. 关键字手册

### 8.1 UI 操作关键字

| 关键字 | 说明 | model 属性 | data 属性 |
|--------|------|-----------|-----------|
| **navigate** | 导航到 URL（无浏览器时自动创建） | — | URL 或 GlobalValue 引用 |
| **close** | 关闭浏览器 | — | — |
| **type** | UI 批量输入（PC 端 / 移动端统一） | 模型名 | DataID |
| **verify** | 批量验证（UI / 接口通用） | 模型名 | DataID（自动查 `模型名_verify` 表） |
| **wait** | 等待指定秒数 | — | 秒数（如 `3`） |
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

## 9. 完整示例

### 9.1 项目结构

```
product/DEMO/demo_site/
├── model/
│   └── model.xml
├── case/
│   └── demo_case.xml
├── data/
│   ├── globalvalue.xml
│   ├── Login.xml
│   ├── Login_verify.xml
│   └── QuerySQL.xml
├── fun/
└── result/
```

### 9.2 model.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<models>
<model name="Login" servicename="">
    <element name="username" type="web">
        <type>input</type>
        <location type="id">username</location>
    </element>
    <element name="password" type="web">
        <type>input</type>
        <location type="id">password</location>
    </element>
    <element name="loginBtn" type="web">
        <type>button</type>
        <location type="id">login-btn</location>
    </element>
</model>
</models>
```

### 9.3 globalvalue.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<globalvalue>
  <group name="DefaultValue">
    <var name="URL" value="http://127.0.0.1:5555"/>
    <var name="WaitTime" value="2"/>
  </group>
  <group name="demodb">
    <var name="type" value="sqlite"/>
    <var name="database" value="product/DEMO/demo_site/demo.db"/>
  </group>
</globalvalue>
```

### 9.4 Login.xml（数据表）

```xml
<?xml version="1.0" encoding="UTF-8"?>
<datatable name="Login">
  <row id="L001" remark="管理员">
    <field name="username">admin</field>
    <field name="password">admin123</field>
    <field name="loginBtn">click</field>
  </row>
</datatable>
```

### 9.5 Login_verify.xml（验证数据表）

```xml
<?xml version="1.0" encoding="UTF-8"?>
<datatable name="Login_verify">
  <row id="V001" remark="验证管理员登录">
    <field name="welcome_text">欢迎, admin</field>
  </row>
</datatable>
```

### 9.6 demo_case.xml（用例）

```xml
<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="c001" title="登录" description="验证登录" component_type="界面">
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

### 9.7 运行命令

```bash
cd rodski

# 方式1：指定 case XML 文件
python ski_run.py product/DEMO/demo_site/case/demo_case.xml

# 方式2：指定 case 目录（执行所有 XML）
python ski_run.py product/DEMO/demo_site/case/

# 方式3：指定测试模块目录
python ski_run.py product/DEMO/demo_site/
```

---

## 10. 固定与动态测试步骤（规划）

本节面向**用例编写者**：说明未来「固定 Case 步骤 + 动态插入步骤」并存时的**使用预期**与**编写约束**。具体架构与实现以《核心设计约束》**第 8 节**为准。

### 10.1 你将看到什么

| 类型 | 说明 |
|------|------|
| **固定步骤** | 写在 `case/*.xml` 里的 `<test_step>`，与今天用法相同 |
| **动态步骤** | 由命令行或运行时策略在**执行过程中**插入的步骤（例如额外一次 `navigate`、临时 `run`），不一定出现在 XML 文件中 |

两者将组成**一条实际执行序列**；日志与截图会使用**运行时序号**（包含动态步），而 Case 文件中的行序仍对应**固定步骤序号**。

### 10.2 编写侧建议

- 仍优先把**可重复、可评审**的步骤写进 Case XML；动态步骤适合「调试、探活、临时补一刀」等场景。
- 需要在固定步与动态步之间传数据时，首版请使用 **GlobalValue** 或 **`set`** 等已有机制，**不要**在数据表字段里写依赖「动态步返回值」的 `${Return[...]}`（过渡期不支持）。

### 10.3 `${Return[-1]}` 与 `-1` 语义（重要）

- **`${Return[-1]}`**（及现有负索引）表示**固定步骤**执行链路上的「上一步」返回值，与当前版本语义一致。
- **动态步骤**：在数据表 XML 中**不要**使用 `${Return}` 去引用动态步骤产生的结果；若框架后续支持，会在《核心设计约束》与本文单独发版说明。

### 10.4 结果报告

- 当前 `result/*.xml` 以**用例级**结果为主；若未来增加步骤级节点，会同步更新 **result.xsd** 与本文附录。

### 10.5 暂停、插入、终止与服务端命令（规划）

在固定步骤**执行过程中**，可通过外部手段（CLI、GUI、**服务端**等）下发**控制类命令**，改变后续执行：

| 命令 | 含义（用户视角） |
|------|------------------|
| **暂停** | 先跑完当前逻辑，再停住，不自动执行后面的固定步骤，直到有人让你继续 |
| **插入** | 在流程里**多执行几步**，这几步的写法和 Case 里一样（仍是 `action` / `model` / `data`）；模型和数据可以是**临时的**（不长期放进仓库），但**步骤格式不变** |
| **终止** | 结束当前用例或会话；若未勾选「强制」，一般会**等当前这一步跑完**再停 |

**服务端下发命令时**：若**正在执行某一步**（例如页面操作、接口请求、`run` 脚本还在跑），**默认会等这一步结束**再处理你的暂停/插入/普通终止；只有**强制终止**才会尽量立刻停下（具体行为以《核心设计约束》第 8.7 节为准）。

---


---

## 11. 视觉定位器（vision / vision_bbox）

### 11.1 概念

视觉定位器通过 **OmniParser 服务** + **多模态 LLM** 实现语义定位，无需编写 xpath/css 选择器。

**RodSki 职责**：执行 XML 定义的操作，支持视觉定位器  
**Agent 职责**：探索页面，生成包含视觉定位器的 XML

### 11.2 定位器格式

在 `model.xml` 中使用 `locator` 属性：

```xml
<!-- 语义定位 -->
<element name="loginBtn" locator="vision:登录按钮"/>

<!-- 坐标定位（Agent 探索后生成） -->
<element name="submitBtn" locator="vision_bbox:100,200,150,250"/>
```

**格式约束**：
- `vision:描述` — 语义描述，由 LLM 匹配
- `vision_bbox:x1,y1,x2,y2` — 像素坐标（Web）或屏幕绝对坐标（Desktop）

### 11.3 Web 平台完整示例

**model.xml**：
```xml
<models>
  <model name="LoginPage">
    <element name="username" locator="vision:用户名输入框"/>
    <element name="password" locator="vision:密码输入框"/>
    <element name="loginBtn" locator="vision:登录按钮"/>
  </model>
</models>
```

**case.xml**：
```xml
<test_step action="navigate" model="" data="https://example.com/login"/>
<test_step action="type" model="LoginPage" data="L001"/>
```

**data/LoginPage.xml**：
```xml
<row id="L001">
  <field name="username">admin</field>
  <field name="password">admin123</field>
  <field name="loginBtn">click</field>
</row>
```

### 11.4 配置要求

**vision_config.yaml**（`rodski/config/vision_config.yaml`）：
```yaml
omniparser:
  url: http://14.103.175.167:7862/parse/
  timeout: 5

llm:
  provider: claude
  model: claude-opus-4-6
  api_key_env: ANTHROPIC_API_KEY
  timeout: 10
```

**环境变量**：
```bash
export ANTHROPIC_API_KEY=your_api_key
```

### 11.5 适用场景

| 场景 | 推荐定位器 |
|------|-----------|
| 动态 ID/class | vision:描述 |
| 无明显属性的元素 | vision:描述 |
| 跨语言测试 | vision:描述（描述用目标语言） |
| 已知坐标（Agent探索后） | vision_bbox:x,y,w,h |
| 传统 Web 元素 | xpath/css（更快） |


---

## 12. 桌面端自动化（Desktop）

### 12.1 平台标识

桌面平台使用操作系统类型作为 `driver_type`：

```xml
<model name="NotepadPage" driver_type="windows">
  <element name="textArea" locator="vision:文本编辑区域"/>
</model>

<model name="TextEditPage" driver_type="macos">
  <element name="textArea" locator="vision:文本编辑区域"/>
</model>
```

### 12.2 launch 关键字

启动桌面应用（与 `navigate` 功能相同，场景不同）：

```xml
<!-- Windows -->
<test_step action="launch" model="" data="notepad.exe"/>

<!-- macOS -->
<test_step action="launch" model="" data="TextEdit.app"/>
```

### 12.3 vision_bbox 坐标约定

桌面场景下 `vision_bbox` 使用**屏幕绝对坐标**：

```xml
<element name="closeBtn" locator="vision_bbox:1850,50,1900,100"/>
```

**约束**：
- 坐标为屏幕绝对像素坐标（左上角为 0,0）
- 桌面应用执行时**默认全屏**，避免窗口位置变化导致坐标偏移

### 12.4 桌面操作脚本（run 关键字）

桌面特有操作（剪贴板、组合键、窗口管理）通过 `run` 调用脚本：

```xml
<!-- 组合键 -->
<test_step action="run" model="" data="fun/desktop/key_combo.py Ctrl+V"/>

<!-- 剪贴板 -->
<test_step action="run" model="" data="fun/desktop/clipboard_copy.py"/>

<!-- 窗口切换 -->
<test_step action="run" model="" data="fun/desktop/switch_window.py 记事本"/>
```

脚本返回 JSON 格式：
```json
{"status": "success", "result": "..."}
```

### 12.5 完整示例

**case/desktop_demo.xml**：
```xml
<case execute="是" id="d001" title="桌面演示">
  <pre_process>
    <test_step action="launch" model="" data="notepad.exe"/>
    <test_step action="wait" model="" data="2"/>
  </pre_process>
  <test_case>
    <test_step action="type" model="NotepadPage" data="D001"/>
    <test_step action="run" model="" data="fun/desktop/key_combo.py Ctrl+A"/>
  </test_case>
  <post_process>
    <test_step action="run" model="" data="fun/desktop/key_combo.py Alt+F4"/>
  </post_process>
</case>
```

### 12.6 约束

- ❌ 桌面端不支持接口测试（无 `send` 关键字）
- ❌ 不新增 `clipboard`、`key_combination`、`window` 等独立关键字
- ✅ 桌面操作通过 `run` 调用脚本实现
- ✅ 视觉定位为主，辅以命令行工具

## 附录：常见问题

### Q1: 用例没有执行？

1. 检查 Case XML 的 `execute` 属性是否为 `是`（不是 `Y`、`true`；XSD 仅允许 `是` / `否`）
2. 检查 XML 文件编码是否为 UTF-8
3. 检查 XML 格式是否合法（可用浏览器打开验证）
4. 可选：用 `xmllint` 对照 `rodski/schemas/case.xsd` 校验（见上文 **§2.2 Schema 约束**）

### Q2: type 批量输入失败？

1. 检查 model.xml 元素 `name` 是否与数据表 field `name` **完全一致**（区分大小写）
2. 检查定位方式是否正确（用浏览器 F12 验证）
3. 数据表中未定义的字段会被跳过

### Q3: verify 报错"缺少验证目标"？

verify 必须同时填写 **model 和 data** 属性，走批量验证模式。不支持只传 locator 的简单模式。

### Q4: DB 连接失败？

1. 检查 globalvalue.xml 中是否有对应组名的连接配置
2. SQLite：确认 `database` 路径正确且文件存在
3. MySQL/PostgreSQL：确认已安装对应驱动（pymysql / psycopg2）

### Q5: Return 引用没有生效？

Return 引用只应写在**数据表 XML 的 field 值中**，不要直接写在 Case XML。如果 Return 引用的索引不存在，原文保持不变。

### Q6: 数据引用不生效？

1. 检查数据文件名是否正确（必须与 datatable name 一致）
2. 检查 DataID（row id）是否存在
3. 引用格式：`表名.DataID`（整行）或 `表名.DataID.字段名`（单字段）

### Q7: XSD 校验报错「元素 test_step 缺失」？

`case.xsd` 要求每个 `<case>` **必须**包含恰好一个 `<test_step>`。仅写 `<pre_process>` 等而不写 `<test_step>` 不会通过校验。

---

## 附录：关键字速查清单

下列 **`action` 取值**与 `rodski/schemas/case.xsd` 中 **`ActionType` 枚举**一致（共 16 个；`check` 为合法枚举值，语义上等同 `verify`）。

### A. UI 与通用

| 关键字 | 用途 |
|--------|------|
| `navigate` | 导航到 URL（无浏览器时自动创建） |
| `close` | 关闭浏览器 |
| `type` | UI 批量输入（PC/移动端统一） |
| `verify` | 批量验证（UI + 接口通用） |
| `check` | 与 `verify` 等价（XSD 枚举中的兼容项） |
| `assert` | 断言元素值 |
| `wait` | 等待指定秒数 |
| `upload_file` | 上传文件 |
| `clear` | 清空输入框 |
| `get_text` | 已废弃，请改用 `get` |
| `get` | 双模式取值：CSS 选择器 → UI 元素文本（低级补充）；变量名 → 命名变量读取（主路径） |
| `screenshot` | 手动截图 |

### B. 接口关键字

| 关键字 | 用途 |
|--------|------|
| `send` | 发送接口请求（模型 + 数据），响应含 status + body |

### C. 数据与高级关键字

| 关键字 | 用途 |
|--------|------|
| `set` | 设置变量 |
| `DB` | 执行数据库操作（query/execute） |
| `run` | 沙箱执行 Python 代码，stdout → Return |

> UI 原子动作（click、select 等）**不是**独立 `action`，而是写在数据表 `field` 值中，由 `type` 批量模式识别（见 [5.4](#54-批量输入时的特殊值)）。  
> 接口测试通过 `send` + `verify`（或 `check`）完成，与 UI 的 `type` + `verify` 对称。

---

## 附录：测试结果 XML（result.xsd）

`rodski/schemas/result.xsd` 描述框架写入的 **`result/*.xml`**，手工一般**不需要**编写，了解结构即可排查报告问题。

| 约束 | 说明 |
|------|------|
| 根元素 | `<testresult>` |
| 子元素顺序 | 先 `<summary>`（1 个），再 `<results>`（1 个） |
| `<summary>` | `total` / `passed` / `failed` 必填；`skipped`、`errors` 等有默认值 |
| `<results>` 下 `<result>` | `case_id`、`status` 必填；`status` 只能是 `PASS` \| `FAIL` \| `SKIP` \| `ERROR` |

---

**文档版本**: v3.3
**最后更新**: 2026-03-26
