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
| 关键字 | 定义操作类型（type UI输入 / send 接口请求 / verify 批量验证 …） | Case Sheet 的「动作」列 |
| 模型 | 定义页面元素 / 接口字段的定位信息 | model.xml 文件 |
| 数据 | 定义输入值 / 期望值 / 配置参数 | Excel 数据表 Sheet + GlobalValue Sheet |

这三者的协作方式：

- **type（UI 写入）**：关键字 `type` + 模型 `Login` + 数据 `L001` → 框架遍历 Login 模型的每个元素，从 Login 表取对应字段的值，逐一输入到界面
- **send（接口请求）**：关键字 `send` + 模型 `LoginAPI` + 数据 `D001` → 框架从 LoginAPI 模型获取请求方式和 URL，从 LoginAPI 表取字段值，发送 HTTP 请求
- **verify（验证）**：关键字 `verify` + 模型 `Login` + 数据 `V001` → 框架遍历 Login 模型的每个元素，从界面/接口读取实际值，与 Login_verify 表的期望值逐字段比较

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
| 预处理 | 打开页面、准备环境 | `navigate` / `DB`（初始化数据） |
| 测试步骤 | 核心操作 | `type`（UI 批量输入）/ `send`（接口请求） |
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
| 是 | c001 | 登录测试 | 验证登录 | 界面 | navigate | | GlobalValue.DefaultValue.URL/login | type | Login | L001 | verify | Login | V001 | close | | |
| 是 | c002 | DB验证 | 查询验证 | 数据库 | | | | DB | demodb | QuerySQL.Q001 | verify | QueryResult | V001 | | | |

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

**Sheet 名: Login**（与模型同名，强制一致）

| DataID | Remark | username | password |
|--------|--------|----------|----------|
| L001 | 管理员登录 | admin | admin123 |
| L002 | 普通用户 | testuser | test123 |
| L003 | 空密码 | admin | |

**Sheet 名: Login_verify**（验证数据表，自动匹配）

| DataID | Remark | welcome_text |
|--------|--------|-------------|
| V001 | 验证管理员登录 | 欢迎, admin |
| V002 | 验证普通用户 | 欢迎, testuser |

### 5.3 数据表命名与引用规则

> **核心规则**：模型名 = 数据表 Sheet 名，强制一致。数据列只写 DataID，不写表名。

| 关键字 | Case 写法 | 数据表名（自动推导） |
|--------|-----------|---------------------|
| `type` | `type Login L001` | Sheet = `Login` |
| `verify` | `verify Login V001` | Sheet = `Login_verify` |

示例：

```
type Login L001       → 在 Login 表中查找 DataID=L001
verify Login V001     → 在 Login_verify 表中查找 DataID=V001
```

### 5.4 批量输入时的特殊值

在数据表的字段值中，以下值有特殊含义：

#### 控制值

| 特殊值 | Web 行为 | 接口行为 |
|--------|---------|---------|
| `.Password` 后缀 | 输入时去掉后缀，日志中显示 `***` | — |
| 空值 | 跳过该元素（不输入） | — |
| `BLANK` | 跳过（UI）/ 空字符串（接口） | 传空字符串 |
| `NULL` / `NONE` | 跳过（UI） | 传 null / none |

#### UI 动作关键字

数据表单元格中可以写入以下 **UI 动作关键字**，`type` 批量模式会自动识别并执行对应操作，而非输入文本：

| 动作值 | 说明 | 示例 |
|--------|------|------|
| `click` | 点击该元素 | `click` |
| `double_click` | 双击该元素 | `double_click` |
| `right_click` | 右键点击该元素 | `right_click` |
| `hover` | 鼠标悬停到该元素 | `hover` |
| `select【选项值】` | 下拉选择指定值 | `select【管理员】` |
| `key_press【按键】` | 按下键盘按键 | `key_press【Tab】` |
| `key_press【组合键】` | 按下组合键 | `key_press【Control+C】` |
| `drag【目标定位器】` | 拖拽元素到目标位置 | `drag【#drop-zone】` |
| `scroll` | 默认滚动（向下 300px） | `scroll` |
| `scroll【x,y】` | 自定义滚动距离 | `scroll【0,500】` |

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

**Sheet 名: Login**（与模型同名）

| DataID | Remark | username | password | loginBtn | roleSelect |
|--------|--------|----------|----------|----------|------------|
| L001 | 管理员登录 | admin | admin123 | click | select【管理员】 |
| L002 | Tab 切换 | admin | key_press【Tab】 | click | — |

Case Sheet 写 `type Login L001` 时，框架遍历 Login 模型：
1. `username` → 输入 "admin"
2. `password` → 输入 "admin123"
3. `loginBtn` → 执行点击
4. `roleSelect` → 下拉选择 "管理员"

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
| send | HTTP 响应（含 `status` 状态码 + 响应体字段） |
| DB | query → 结果集列表；execute → 受影响行数 |
| run | 脚本 stdout 输出（自动尝试 JSON 解析） |

---

## 8. 关键字手册

### 8.1 UI 操作关键字

| 关键字 | 说明 | 模型列 | 数据列 |
|--------|------|--------|--------|
| **navigate** | 导航到 URL（无浏览器时自动创建） | — | URL 或 GlobalValue 引用 |
| **close** | 关闭浏览器 | — | — |
| **type** | UI 批量输入（PC 端 / 移动端统一） | 模型名 | DataID |
| **verify** | 批量验证（UI / 接口通用） | 模型名 | DataID（自动查 `模型名_verify` 表） |
| **wait** | 等待指定秒数 | — | 秒数（如 `3`） |
| **clear** | 清空输入框 | — | CSS 选择器 |
| **get_text** / **get** | 获取元素文本 | — | CSS 选择器 |
| **screenshot** | 手动截图 | — | 文件路径 |
| **upload_file** | 上传文件 | — | 文件路径 |

> `click`、`select`、`hover`、`scroll`、`double_click`、`right_click`、`key_press`、`drag` 等 UI 原子动作不作为独立关键字使用，而是写在**数据表的字段值**中，由 `type` 批量模式自动识别执行。详见 [5.4 批量输入时的特殊值](#54-批量输入时的特殊值)。

> **type 统一 UI 测试**：无论 PC Web、移动端（Android/iOS），所有 UI 输入操作都使用 `type`，不区分平台。

### 8.2 type / send / verify — 核心关键字详解

框架有三个核心批量关键字，分工明确：

| | type（UI） | send（接口） | verify（通用验证） |
|--|-----------|-------------|-------------------|
| 作用 | 数据 → 写入 UI 界面 | 数据 → 发送 HTTP 请求 | 界面/响应 → 读取并比较 |
| 适用场景 | PC Web / 移动端 | REST API 接口 | UI 验证 + 接口验证 |
| 模型列 | UI 模型名（必填） | 接口模型名（必填） | 模型名（必填） |
| 数据列 | DataID | DataID | DataID |
| 数据表 | 模型名（同名） | 模型名（同名） | 模型名_verify（自动拼接） |
| 匹配规则 | 元素 name = 数据表列名 | 元素 name = 数据表列名 | 元素 name = 数据表列名 |

> **数据表命名规则**：模型名 = 数据表 Sheet 名（强制一致）。数据列只写 `DataID`，不写表名前缀。

#### 接口测试：send + verify

接口测试不再使用独立 HTTP 关键字，而是通过 **send / verify** 批量模式完成：

1. **接口模型**：在 model.xml 中定义接口元素，包含 `_method`（请求方式）、`_url`（请求地址）、`_header_*`（请求头）以及接口字段
2. **send 发送请求**：`send LoginAPI D001` → 从 `LoginAPI` 模型获取请求方式和 URL，从 `LoginAPI` 数据表取值，组装并发送 HTTP 请求
3. **verify 验证响应**：`verify LoginAPI V001` → 从 `LoginAPI_verify` 表取期望值，与 send 的响应进行比较

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

**数据表 LoginAPI**（与模型同名）：

| DataID | Remark | username | password |
|--------|--------|----------|----------|
| D001 | 管理员登录 | admin | admin123 |
| D002 | 普通用户 | testuser | test123 |

**验证数据表 LoginAPI_verify**：

| DataID | Remark | status | username | role |
|--------|--------|--------|----------|------|
| V001 | 验证管理员登录 | 200 | admin | 管理员 |
| V002 | 验证普通用户 | 200 | testuser | 普通用户 |

> `status` 列：期望的 HTTP 状态码。其他列：期望的响应字段值。

**Case Sheet 写法**：

| 测试动作 | 测试模型 | 测试数据 | 预期动作 | 预期模型 | 预期数据 |
|---------|---------|---------|---------|---------|---------|
| send | LoginAPI | D001 | verify | LoginAPI | V001 |

### 8.3 接口测试关键字

| 关键字 | 说明 | 模型列 | 数据列 |
|--------|------|--------|--------|
| **send** | 发送接口请求（模型 + 数据） | 接口模型名 | DataID |

> send 是接口测试的核心关键字，与 UI 的 type 对称。响应自动保存为步骤返回值（含 `status` 和响应体字段），可通过 `verify` 验证。详见 [8.2 接口测试：send + verify](#接口测试send--verify)。

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
- **返回值**：待实现
- **db模版文件**：在model目录下必须以db_template.md命名，用于生成db模版文件。db_template必须与数据表的sheet名称一致。如数据表为QuerySQL，则db_template为QuerySQL.md。

### 8.5 高级关键字

| 关键字 | 说明 | 模型列 | 数据列 |
|--------|------|--------|--------|
| **set** | 设置变量 | — | — |
| **run** | 沙箱执行 Python 代码 | 工程名（fun/ 下的子目录） | 代码文件路径 |

### 8.6 run — 沙箱代码执行

`run` 在独立子进程中执行 Python 脚本，脚本的 **stdout 输出**自动保存为步骤返回值，可在后续步骤中通过 `Return[-1]` 引用。

#### 目录结构

代码文件以"工程"形式组织，存放在与 `case/` 同级的 `fun/` 目录下：

```
test_project/
├── case/                  ← 用例文件
│   └── test_login.xlsx
├── model/
├── data/
└── fun/                   ← 代码工程根目录
    ├── data_gen/          ← 工程名（模型列填写）
    │   ├── gen_phone.py   ← 数据列填写
    │   └── utils.py       ← 可供 gen_phone.py import
    └── crypto/
        └── encrypt.py
```

#### Case Sheet 写法

| Execute | CaseID | Title | PreProcess | TestStep | ExpectedResult |
|---------|--------|-------|------------|----------|----------------|
| 是 | TC001 | 注册 | navigate\|\|url=https://... | run\|data_gen\|gen_phone.py | verify\|RegResult\|VerifyData.V001 |

对应解析：
- **关键字** = `run`
- **模型列** = `data_gen`（fun/ 下的工程目录名）
- **数据列** = `gen_phone.py`（工程内的 Python 文件路径）

#### 脚本编写规范

脚本通过 `print()` 输出返回值。框架会自动尝试 JSON 解析，解析失败则作为纯文本保存。

**返回简单值**：

```python
# fun/data_gen/gen_phone.py
import random
phone = f"138{random.randint(10000000, 99999999)}"
print(phone)
```

后续步骤可通过 `Return[-1]` 获取该手机号。

**返回结构化数据**：

```python
# fun/data_gen/gen_user.py
import json
import random
user = {
    "username": f"user_{random.randint(1000, 9999)}",
    "phone": f"138{random.randint(10000000, 99999999)}",
    "email": f"test{random.randint(100, 999)}@example.com"
}
print(json.dumps(user, ensure_ascii=False))
```

后续步骤数据表中可通过 `Return[-1]` 获取完整字典。

#### 执行环境说明

| 特性 | 说明 |
|------|------|
| 解释器 | 与框架运行的 Python 解释器相同 |
| 工作目录 | 工程目录（`fun/<工程名>/`），支持工程内相对 import |
| 超时 | 默认 300 秒，超时自动终止 |
| 隔离性 | 独立子进程，不共享框架内存空间 |
| 目前支持 | 仅 Python（`.py`） |

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
| 是 | c001 | 登录 | 验证登录 | 界面 | navigate | | GlobalValue.DefaultValue.URL/login | type | Login | LoginData.L001 | wait | | 2 | close | | |

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

## 附录：关键字速查清单（代码对齐版）

以下清单基于当前实现（`core/keyword_engine.py`）整理，可直接用于快速查询。

### A. UI 关键字

| 关键字 | 用途 |
|--------|------|
| `navigate` | 导航到 URL（无浏览器时自动创建） |
| `close` | 关闭浏览器 |
| `type` | UI 批量输入（PC/移动端统一） |
| `verify` | 批量验证（UI + 接口通用） |
| `assert` | 断言元素值 |
| `wait` | 等待指定秒数 |
| `upload_file` | 上传文件 |
| `clear` | 清空输入框 |
| `get_text` | 获取元素文本 |
| `get` | `get_text` 的别名 |

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

### D. 兼容关键字（实现已支持）

| 关键字 | 说明 |
|--------|------|
| `check` | 兼容写法，内部等同于 `verify` |

> 合计：14 个主关键字（`SUPPORTED` 列表）+ 1 个兼容关键字（`check`）。
> UI 原子动作（click / select / hover / drag / scroll / double_click / right_click / key_press）通过数据表字段值在 `type` 批量模式中使用。
> 接口测试通过 `send`（发送请求）+ `verify`（验证响应）完成，与 UI 的 `type` + `verify` 完全对称。

---

**文档版本**: v2.0  
**最后更新**: 2026-03-20
