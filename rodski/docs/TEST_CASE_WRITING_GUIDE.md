# RodSki 测试用例编写指南

**版本**: v2.0  
**日期**: 2026-03-20  
**适用框架**: RodSki v1.3+

---

## 目录

1. [核心概念：关键字 + 模型 + 数据](#1-核心概念关键字--模型--数据)
2. [Excel 文件结构](#2-excel-文件结构)
3. [Case Sheet — 用例编写](#3-case-sheet--用例编写)
4. [model.xml — 模型编写](#4-modelxml--模型编写)
5. [数据表 — 测试数据编写](#5-数据表--测试数据编写)
6. [GlobalValue — 全局变量](#6-globalvalue--全局变量)
7. [数据引用与变量解析](#7-数据引用与变量解析)
8. [关键字手册](#8-关键字手册)
9. [完整示例](#9-完整示例)
10. [附录：常见问题](#附录常见问题)

---

## 1. 核心概念：关键字 + 模型 + 数据

RodSki 的用例由三部分组成：

```
用例 = 关键字（做什么动作） + 模型（对哪些元素） + 数据（用什么值）
```

| 组成部分 | 作用 | 存储位置 |
|---------|------|---------|
| 关键字 | 定义操作类型（打开页面、输入、点击、验证…） | Case Sheet 的「动作」列 |
| 模型 | 定义页面元素的定位信息 | model.xml 文件 |
| 数据 | 定义输入值 / 期望值 / 配置参数 | Excel 数据表 Sheet + GlobalValue Sheet |

这三者的协作方式：

- **type（写入）**：关键字 `type` + 模型 `Login` + 数据 `LoginData.L001` → 框架遍历 Login 模型的每个元素，从 LoginData 表取对应字段的值，逐一输入到界面
- **verify（验证）**：关键字 `verify` + 模型 `ItemDetail` + 数据 `ExpectData.E001` → 框架遍历 ItemDetail 模型的每个元素，从界面读取实际值，与 ExpectData 表的期望值逐字段比较

**关键规则：模型元素 name = 数据表列名**。这是整个框架运转的基础。

---

## 2. Excel 文件结构

一个测试用例文件（.xlsx）包含以下 Sheet：

| Sheet 名称 | 必需 | 说明 |
|-----------|------|------|
| **Case** | 是 | 测试用例主表（第一个 Sheet） |
| **GlobalValue** | 是 | 全局变量配置 |
| **TestResult** | 是 | 执行结果回填（可为空，框架自动写入） |
| 自定义数据表 | 按需 | 如 LoginData、ItemData、QuerySQL 等 |

框架会自动跳过以下 Sheet 名：Main、Case、GlobalValue、TestResult、Logic。其余 Sheet 均视为数据表解析。

```
casstime_login_case.xlsx
├── Case          ← 用例主表
├── GlobalValue   ← 全局变量
├── LoginData     ← 登录数据表
├── ItemData      ← 物品数据表
├── QuerySQL      ← SQL 数据表
└── TestResult    ← 结果回填（框架自动写入）
```

---

## 3. Case Sheet — 用例编写

### 3.1 表头结构

Case Sheet 必须有 **2 行表头**，用例数据从第 3 行开始。

| 列 | 主表头 (Row 1) | 子表头 (Row 2) | 字段名 |
|----|---------------|---------------|--------|
| A | 执行控制 | — | execute_control |
| B | 用例编号 | — | case_id |
| C | 测试用例标题 | — | title |
| D | 用例描述 | — | description |
| E | 组件类型 | — | component_type |
| F | 预处理 | 动作 | pre_process.action |
| G | | 模型 | pre_process.model |
| H | | 数据 | pre_process.data |
| I | 测试步骤 | 动作 | test_step.action |
| J | | 模型 | test_step.model |
| K | | 数据 | test_step.data |
| L | 预期结果 | 动作 | expected_result.action |
| M | | 模型 | expected_result.model |
| N | | 数据 | expected_result.data |
| O | 后处理 | 动作 | post_process.action |
| P | | 模型 | post_process.model |
| Q | | 数据 | post_process.data |

### 3.2 四阶段执行流程

每个用例按顺序执行四个阶段：

```
预处理 → 测试步骤 → 预期结果 → 后处理
```

| 阶段 | 典型用途 | 示例 |
|------|---------|------|
| 预处理 | 打开页面、准备环境 | `open` / `navigate` / `DB`（初始化数据） |
| 测试步骤 | 核心操作 | `type`（批量输入）/ `click` / `http_post` |
| 预期结果 | 验证检查 | `verify`（批量验证）/ `DB`（查询验证） |
| 后处理 | 清理环境 | `close` / `DB`（清理数据） |

每个阶段只有一行（动作 + 模型 + 数据）。如果某阶段不需要，留空即可。

### 3.3 列字段详解

| 列 | 说明 | 取值规则 |
|----|------|---------|
| 执行控制 (A) | 是否执行 | 只有 `是` 才执行，其他值（否、空、Y）均跳过 |
| 用例编号 (B) | 唯一标识 | 如 `c001`、`c002`，用于日志和结果回填 |
| 组件类型 (E) | 测试类别 | `界面` / `接口` / `数据库`，仅做分类标记 |
| 动作 | 关键字名称 | 见第 8 节关键字手册 |
| 模型 | 模型名或连接名 | type/verify → 模型名；DB → GlobalValue 连接组名；其他 → 通常留空 |
| 数据 | 数据引用或直接值 | 数据表引用 / GlobalValue 引用 / URL / CSS 选择器 / 秒数等 |

### 3.4 用例示例

| 执行控制 | 编号 | 标题 | 描述 | 类型 | 预处理动作 | 预处理模型 | 预处理数据 | 测试动作 | 测试模型 | 测试数据 | 预期动作 | 预期模型 | 预期数据 | 后处理动作 | 后处理模型 | 后处理数据 |
|---------|------|------|------|------|-----------|-----------|-----------|---------|---------|---------|---------|---------|---------|-----------|-----------|-----------|
| 是 | c001 | 登录测试 | 验证登录 | 界面 | open | | GlobalValue.DefaultValue.URL/login | type | Login | LoginData.L001 | verify | Dashboard | ExpectDash.E001 | close | | |
| 是 | c002 | DB验证 | 查询验证 | 数据库 | | | | DB | demodb | QuerySQL.Q001 | verify | | QueryExpect.E001 | | | |

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

| 属性/子节点 | 必需 | 说明 |
|------------|------|------|
| `name` | 是 | 元素名称，**必须与数据表列名一致** |
| `type`（element 属性） | 是 | 驱动类型：`web`（Web 页面）/ `interface`（接口）/ `other` |
| `<type>` 子节点 | 否 | UI 元素类型：input / button / select / text / textarea |
| `<location type="...">` | 是 | 定位信息 |
| `<desc>` | 否 | 元素描述，便于维护 |

### 4.3 定位类型

| type 值 | 转换规则 | 示例 |
|---------|---------|------|
| `id` | → CSS `#定位值` | `<location type="id">username</location>` → `#username` |
| `class` | → CSS `.定位值` | `<location type="class">btn-submit</location>` → `.btn-submit` |
| `css` | → 原样使用 | `<location type="css">input[name="user"]</location>` |
| `xpath` | → 原样使用 | `<location type="xpath">//input[@id='user']</location>` |
| `text` | → Playwright `text=...` | `<location type="text">登录</location>` → `text=登录` |
| `tag` | → 标签名选择器 | `<location type="tag">button</location>` |

### 4.4 简化格式

对于简单场景，也支持单行格式：

```xml
<element name="username" type="id" value="userName"/>
```

此格式下 `type` 为定位类型，`value` 为定位值，驱动类型默认为 `web`。

### 4.5 核心约束：元素名 = 数据表列名

```
model.xml 元素 name  ===  数据表 Sheet 的列名
```

这是 `type`（批量输入）和 `verify`（批量验证）的运转基础。框架遍历模型元素时，用 `name` 去数据表中查找对应列的值。

正确示例：

```xml
<element name="username"><location type="id">userName</location></element>
<element name="password"><location type="id">password</location></element>
```

```
# LoginData Sheet
| DataID | Remark | username | password |    ← 列名与 model name 一致
|--------|--------|----------|----------|
| L001   | 有效   | admin    | admin123 |
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

## 5. 数据表 — 测试数据编写

### 5.1 结构规则

数据表 = Excel 中的一个 Sheet，**Sheet 名 = 数据表名**。

| 列位置 | 规则 |
|--------|------|
| 第 1 列 | **必须**为 `DataID`（数据行唯一标识） |
| 第 2 列 | 推荐为 `Remark`（备注说明，框架不使用） |
| 第 3 列起 | 数据字段，**列名必须与 model 元素 name 一致** |

数据从第 2 行开始（第 1 行为表头）。DataID 为空的行会被跳过。

### 5.2 示例：登录数据表

**Sheet 名: LoginData**

| DataID | Remark | username | password |
|--------|--------|----------|----------|
| L001 | 管理员登录 | admin | admin123 |
| L002 | 普通用户 | testuser | test123 |
| L003 | 空密码 | admin | |

### 5.3 数据表引用语法

在 Case Sheet 的「数据」列中使用：

```
表名.DataID           → 引用整行数据（用于 type / verify 批量模式）
```

示例：

```
LoginData.L001        → {username: "admin", password: "admin123"}
```

### 5.4 批量输入时的特殊值

在数据表的字段值中，以下值有特殊含义：

| 特殊值 | Web 行为 | 接口行为 |
|--------|---------|---------|
| `click` | 对该元素执行**点击**而非输入 | — |
| `.Password` 后缀 | 输入时去掉后缀，日志中显示 `***` | — |
| 空值 | 跳过该元素（不输入） | — |

示例：数据表中 `loginBtn` 列写 `click`，则 `type` 批量模式遇到该元素时执行点击。

### 5.5 SQL 数据表

DB 关键字使用的 SQL 也放在数据表中：

**Sheet 名: QuerySQL**

| DataID | Remark | sql | operation | var_name |
|--------|--------|-----|-----------|----------|
| Q001 | 查询总数 | SELECT COUNT(*) as cnt FROM items | query | |
| Q002 | 插入数据 | INSERT INTO items (name) VALUES ('test') | execute | |
| Q003 | 查询最新 | SELECT * FROM items ORDER BY id DESC LIMIT 1 | query | |

| 列名 | 说明 |
|------|------|
| sql | 要执行的 SQL 语句 |
| operation | `query`（查询，返回结果集）或 `execute`（增删改，返回受影响行数） |
| var_name | 可选，将结果存入变量 |

### 5.6 数据表中使用 Return 引用

Return 引用**应写在数据表的字段值中**，不应直接写在 Case Sheet。

示例：验证上一步创建的物品

**Sheet 名: VerifyData**

| DataID | Remark | itemName |
|--------|--------|----------|
| V001 | 验证新物品名称 | Return[-1] |

Case Sheet 写法：

| 预期动作 | 预期模型 | 预期数据 |
|---------|---------|---------|
| verify | ItemDetail | VerifyData.V001 |

框架执行时：先解析 VerifyData.V001 的 `itemName` 字段 → 发现 `Return[-1]` → 替换为上一步的返回值 → 再与界面实际值比较。

---

## 6. GlobalValue — 全局变量

### 6.1 结构

**Sheet 名: GlobalValue**

| GroupName | Key | Value |
|-----------|-----|-------|
| DefaultValue | URL | http://127.0.0.1:5555 |
| DefaultValue | BrowserType | chromium |
| DefaultValue | WaitTime | 2 |
| demodb | type | sqlite |
| demodb | database | product/DEMO/demo_site/demo.db |

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
| open / type / click / verify 等 | 是 |
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

Case Sheet 中 DB 关键字的「模型」列填写组名（如 `demodb`），框架根据该组名查找连接配置。

---

## 7. 数据引用与变量解析

### 7.1 解析顺序

框架在执行步骤前，对 Case Sheet「数据」列的值按以下顺序解析：

1. **GlobalValue 引用**：`GlobalValue.组名.变量名` → 替换为对应值
2. **数据表字段引用**：`表名.DataID.字段名` → 替换为数据表中的值
3. **Return 引用**：`Return[-1]` / `Return[0]` → 替换为步骤返回值

### 7.2 支持的引用格式

| 格式 | 说明 | 示例 |
|------|------|------|
| `GlobalValue.组名.Key` | 全局变量 | `GlobalValue.DefaultValue.URL` |
| `表名.DataID` | 整行数据（用于 type/verify） | `LoginData.L001` |
| `表名.DataID.字段名` | 单个字段值 | `LoginData.L001.username` |
| `Return[-1]` | 上一步返回值 | 写在**数据表**字段中 |
| `Return[-2]` | 上上步返回值 | 写在**数据表**字段中 |
| `Return[0]` | 第一步返回值 | 写在**数据表**字段中 |

### 7.3 Return 引用的正确用法

Return 引用**只应出现在数据表的单元格中**，不要写在 Case Sheet 的「数据」列。

原因：Case Sheet「数据」列中如果写 `Return[-1]`，会在进入关键字前被替换成字符串，导致 verify 无法走批量验证模式。

正确做法：

```
数据表 VerifyData:
| DataID | Remark | orderNo |
|--------|--------|---------|
| V001   | 验证订单 | Return[-1] |    ← Return 写在数据表中

Case Sheet:
| 预期动作 | 预期模型 | 预期数据 |
|---------|---------|---------|
| verify  | OrderDetail | VerifyData.V001 |    ← 走批量验证
```

### 7.4 哪些关键字会产生 Return 值

| 关键字 | 返回值内容 |
|--------|-----------|
| get / get_text | 元素文本 |
| verify | 批量验证时的实际值字典 |
| assert | 断言结果 |
| type（批量模式） | 本次输入使用的完整数据行 |
| http_get/post/put/delete | HTTP 响应 body |
| send | HTTP 响应 body |
| DB | query → 结果集列表；execute → 受影响行数 |

---

## 8. 关键字手册

### 8.1 Web 操作关键字

| 关键字 | 说明 | 模型列 | 数据列 |
|--------|------|--------|--------|
| **open** | 打开 URL | — | URL 或 GlobalValue 引用 |
| **navigate** | 导航到 URL | — | URL 或 GlobalValue 引用 |
| **close** | 关闭浏览器 | — | — |
| **click** | 点击元素 | — | CSS 选择器（如 `#login-btn`） |
| **type** | 输入文本 | 模型名（批量）或留空 | 数据表引用（批量）或留空 |
| **verify** | 批量验证 | 模型名 | 数据表引用（TableName.DataID） |
| **wait** | 等待指定秒数 | — | 秒数（如 `3`） |
| **select** | 下拉选择 | — | CSS 选择器 |
| **clear** | 清空输入框 | — | CSS 选择器 |
| **get_text** / **get** | 获取元素文本 | — | CSS 选择器 |
| **hover** | 鼠标悬停 | — | CSS 选择器 |
| **scroll** | 页面滚动 | — | — （默认向下 300px）|
| **double_click** | 双击 | — | CSS 选择器 |
| **right_click** | 右键点击 | — | CSS 选择器 |
| **key_press** | 按键 | — | 键名（如 `Tab`、`Enter`、`Escape`） |
| **screenshot** | 手动截图 | — | 文件路径 |
| **upload_file** | 上传文件 | — | 文件路径 |

### 8.2 type 和 verify — 批量模式详解

`type` 和 `verify` 是框架最核心的两个关键字，它们完全对称：

| | type | verify |
|--|------|--------|
| 方向 | 数据 → 写入界面 | 界面 → 读取并比较 |
| 模型列 | 模型名（必填） | 模型名（必填） |
| 数据列 | `表名.DataID`（必填） | `表名.DataID`（必填） |
| 执行逻辑 | 遍历模型每个元素，从数据表取值，输入到界面 | 遍历模型每个元素，从界面取实际值，与数据表期望值比较 |
| 匹配规则 | 元素 name = 数据表列名 | 元素 name = 数据表列名 |

### 8.3 API 测试关键字

| 关键字 | 说明 | 模型列 | 数据列 |
|--------|------|--------|--------|
| **http_get** | GET 请求 | — | URL |
| **http_post** | POST 请求 | — | URL |
| **http_put** | PUT 请求 | — | URL |
| **http_delete** | DELETE 请求 | — | URL |
| **send** | 通用 HTTP 请求 | — | URL |
| **assert_status** | 断言 HTTP 状态码 | — | 期望状态码（如 `200`） |
| **assert_json** | 断言 JSON 响应字段 | — | — |

### 8.4 数据库关键字

| 关键字 | 说明 | 模型列 | 数据列 |
|--------|------|--------|--------|
| **DB** | 执行 SQL | GlobalValue 中的连接组名 | SQL 数据表引用或直接 SQL |

DB 用例格式：

| 动作 | 模型 | 数据 |
|------|------|------|
| DB | demodb | QuerySQL.Q001 |

- **模型列**：填写 GlobalValue 中配置的数据库连接组名（如 `demodb`）
- **数据列**：填写 SQL 数据表引用（如 `QuerySQL.Q001`），或直接写 SQL

### 8.5 高级关键字

| 关键字 | 说明 | 模型列 | 数据列 |
|--------|------|--------|--------|
| **set** | 设置变量 | — | — |
| **run** | 运行 Logic 子用例 | — | 子用例名称 |

---

## 9. 完整示例

### 9.1 项目结构

```
product/DEMO/demo_site/
├── app.py              ← 测试网站
├── demo.db             ← SQLite 数据库
├── model/
│   └── model.xml       ← 页面模型
└── case/
    └── demo_test_case.xlsx  ← 测试用例
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

### 9.3 Excel 内容

**GlobalValue Sheet:**

| GroupName | Key | Value |
|-----------|-----|-------|
| DefaultValue | URL | http://127.0.0.1:5555 |
| DefaultValue | WaitTime | 2 |
| demodb | type | sqlite |
| demodb | database | product/DEMO/demo_site/demo.db |

**LoginData Sheet:**

| DataID | Remark | username | password | loginBtn |
|--------|--------|----------|----------|----------|
| L001 | 管理员 | admin | admin123 | click |

**Case Sheet:**

| 执行控制 | 编号 | 标题 | 描述 | 类型 | 预处理动作 | 预处理模型 | 预处理数据 | 测试动作 | 测试模型 | 测试数据 | 预期动作 | 预期模型 | 预期数据 | 后处理动作 | 后处理模型 | 后处理数据 |
|---------|------|------|------|------|-----------|-----------|-----------|---------|---------|---------|---------|---------|---------|-----------|-----------|-----------|
| 是 | c001 | 登录 | 验证登录 | 界面 | open | | GlobalValue.DefaultValue.URL/login | type | Login | LoginData.L001 | wait | | 2 | close | | |

### 9.4 运行命令

```bash
cd rodski
python ski_run.py product/DEMO/demo_site/case/demo_test_case.xlsx
```

---

## 附录：常见问题

### Q1: 用例没有执行？

1. 检查 Case Sheet 是否有 **2 行表头**，数据从第 3 行开始
2. 检查执行控制列是否为 `是`（不是 `Y`、`是/否`）

### Q2: type 批量输入失败？

1. 检查 model.xml 元素 `name` 是否与数据表列名**完全一致**（区分大小写）
2. 检查定位方式是否正确（用浏览器 F12 验证）
3. 数据表中空值的字段会被跳过

### Q3: verify 报错"缺少验证目标"？

verify 必须同时填写**模型列和数据列**，走批量验证模式。不支持只传 locator 的简单模式。

### Q4: DB 连接失败？

1. 检查 GlobalValue 中是否有对应组名的连接配置
2. SQLite：确认 `database` 路径正确且文件存在
3. MySQL/PostgreSQL：确认已安装对应驱动（pymysql / psycopg2）

### Q5: Return 引用没有生效？

Return 引用只应写在**数据表的字段值中**，不要直接写在 Case Sheet。如果 Return 引用的索引不存在，原文保持不变。

### Q6: 数据引用不生效？

1. 检查数据表 Sheet 名是否正确
2. 检查 DataID 是否存在
3. 引用格式：`表名.DataID`（整行）或 `表名.DataID.字段名`（单字段）

---

**文档版本**: v2.0  
**最后更新**: 2026-03-20
