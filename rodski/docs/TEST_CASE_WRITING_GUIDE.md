# RodSki 测试用例编写规范与指南

**版本**: v1.0  
**日期**: 2026-03-20  
**适用框架**: RodSki v1.2.3+

---

## 目录

1. [概述](#1-概述)
2. [Excel 文件结构](#2-excel-文件结构)
3. [Case Sheet 编写规范](#3-case-sheet-编写规范)
4. [Model.xml 编写规范](#4-modelxml-编写规范)
5. [数据表编写规范](#5-数据表编写规范)
6. [GlobalValue 编写规范](#6-globalvalue-编写规范)
7. [关键字参考](#7-关键字参考)
8. [完整示例](#8-完整示例)

---

## 1. 概述

RodSki 是一个数据驱动的自动化测试框架，核心特点：

- **数据驱动**: 测试数据与用例分离，存储在数据表中
- **模型驱动**: 页面元素抽象为模型，提高可维护性
- **三段式结构**: 预处理 → 测试步骤 → 预期结果 → 后处理

### 核心概念

| 概念 | 说明 | 文件/Sheet |
|------|------|------------|
| 用例 | 测试场景的具体描述 | Case Sheet |
| 模型 | 页面元素的定位信息 | model.xml |
| 数据表 | 测试数据集合 | 以 Sheet 名为表名 |
| 全局变量 | 跨用例共享的配置 | GlobalValue Sheet |

---

## 2. Excel 文件结构

### 必需 Sheet

| Sheet 名称 | 必需 | 说明 |
|-----------|------|------|
| Case | ✅ 是 | 测试用例主表 |
| GlobalValue | ✅ 是 | 全局变量配置 |
| TestResult | ✅ 是 | 执行结果回填（可为空） |
| 数据表名 | 按需 | 如 Login、User 等 |

### 文件结构示例

```
casstime_login_case.xlsx
├── Case          # 用例主表（第一个Sheet）
├── GlobalValue   # 全局变量
├── Login         # 登录数据表
└── TestResult    # 结果回填表
```

---

## 3. Case Sheet 编写规范

### 3.1 表头结构

**重要**: Case Sheet 必须有 **2行表头**，数据从第3行开始！

```
Row 1: 主表头（合并单元格）
Row 2: 子表头
Row 3+: 用例数据
```

#### 表头布局

| 列 | 主表头 (Row 1) | 子表头 (Row 2) |
|----|---------------|---------------|
| A | 执行控制 | (合并) |
| B | 用例编号 | (合并) |
| C | 测试用例标题 | (合并) |
| D | 用例描述 | (合并) |
| E | 组件类型 | (合并) |
| F-H | **预处理** | 动作 \| 模型 \| 数据 |
| I-K | **测试步骤** | 动作 \| 模型 \| 数据 |
| L-N | **预期结果** | 动作 \| 模型 \| 数据 |
| O-Q | **后处理** | 动作 \| 模型 \| 数据 |

### 3.2 列定义详解

| 列 | 名称 | 说明 | 示例值 |
|----|------|------|--------|
| A | 执行控制 | 是否执行该用例 | `是` / `否` |
| B | 用例编号 | 唯一标识符 | `c001`, `c002` |
| C | 测试用例标题 | 简短描述 | `登录测试` |
| D | 用例描述 | 详细说明 | `验证正确账号密码登录` |
| E | 组件类型 | 测试类型 | `界面` / `接口` |
| F | 预处理-动作 | 预处理关键字 | `open` |
| G | 预处理-模型 | 模型名.元素名 | `Login` |
| H | 预处理-数据 | 数据引用 | `GlobalValue.DefaultValue.URL` |
| I-K | 测试步骤 | 同上 | - |
| L-N | 预期结果 | 同上 | - |
| O-Q | 后处理 | 同上 | - |

### 3.3 三段式结构

每个用例分为四个阶段：

```
预处理 → 测试步骤 → 预期结果 → 后处理
```

- **预处理**: 准备工作（如打开页面、初始化数据）
- **测试步骤**: 主要操作（如输入、点击）
- **预期结果**: 验证检查（如验证文本、验证元素）
- **后处理**: 清理工作（如关闭浏览器）

### 3.4 用例编写示例

| 执行控制 | 用例编号 | 标题 | 描述 | 类型 | 预处理动作 | 预处理模型 | 预处理数据 | 测试动作 | 测试模型 | 测试数据 | 预期动作 | 预期模型 | 预期数据 | 后处理动作 | 后处理模型 | 后处理数据 |
|---------|---------|------|------|------|-----------|-----------|-----------|---------|---------|---------|---------|---------|---------|-----------|-----------|-----------|
| 是 | c001 | 登录测试 | 验证登录功能 | 界面 | open | Login | GlobalValue.DefaultValue.URL | type | Login | Login.L001 | verify | | title_contains:首页 | close | | |
| 是 | c002 | 切换登录模式 | 验证模式切换 | 界面 | open | Login | GlobalValue.DefaultValue.URL | click | Login.verifyCodeLoginTab | | verify | Login.cellphone | visible | close | | |

---

## 4. Model.xml 编写规范

### 4.1 文件结构

```xml
<?xml version="1.0" encoding="UTF-8"?>
<models>
<model name="模型名称" servicename="">
    <element name="元素名称" ...>
        ...
    </element>
</model>
</models>
```

### 4.2 Element 元素定义

```xml
<element name="username" interfacename="" group="" type="web">
    <type>input</type>
    <location type="定位类型" item="">定位值</location>
    <desc>元素描述（可选）</desc>
</element>
```

### 4.3 元素属性说明

| 属性 | 必需 | 说明 |
|------|------|------|
| name | ✅ | **必须与数据表列名一致！** |
| type | ✅ | 元素类型（input/button/select/text...） |
| location | ✅ | 定位信息 |

### 4.4 定位类型 (location type)

| 类型 | 示例 | 说明 |
|------|------|------|
| id | `userName` | ID 定位，最常用 |
| class | `btn-submit` | Class 名称定位 |
| css | `input[name="user"]` | CSS 选择器 |
| xpath | `//input[@id='user']` | XPath 定位 |
| text | `登录` | 文本内容定位 |
| tag | `button` | 标签名定位 |

### 4.5 ⚠️ 关键约束：元素名 = 数据表列名

**这是最重要的规则！**

```
模型元素 name  === 数据表列名
```

**正确示例:**

```xml
<!-- model.xml -->
<element name="username">
    <type>input</type>
    <location type="id">userName</location>
</element>
<element name="password">
    <type>input</type>
    <location type="id">password</location>
</element>
```

```
# Login 数据表 (Sheet: Login)
| DataID | Remark | username | password |
|--------|--------|----------|----------|
| L001   | 有效   | testuser | 123456   |
```

**错误示例:**

```xml
<!-- 错误！元素名与数据表列名不匹配 -->
<element name="userInput">  <!-- 数据表列名是 username -->
    <location type="id">userName</location>
</element>
```

### 4.6 完整 Model 示例

```xml
<?xml version="1.0" encoding="UTF-8"?>
<models>
<!-- 开思平台登录页面模型 -->
<model name="Login" servicename="">
    <!-- 账号登录模式 -->
    <element name="username" interfacename="" group="" type="web">
        <type>input</type>
        <location type="id" item="">userName</location>
        <desc>用户名/手机号输入框</desc>
    </element>
    
    <element name="password" interfacename="" group="" type="web">
        <type>input</type>
        <location type="id" item="">password</location>
        <desc>密码输入框</desc>
    </element>
    
    <!-- 登录按钮 -->
    <element name="loginBtn" interfacename="" group="" type="web">
        <type>button</type>
        <location type="class" item="">btn-submit</location>
        <desc>登录按钮</desc>
    </element>
    
    <!-- 验证码登录模式 -->
    <element name="cellphone" interfacename="" group="" type="web">
        <type>input</type>
        <location type="id" item="">cellPhone</location>
        <desc>手机号输入框</desc>
    </element>
    
    <element name="verifycode" interfacename="" group="" type="web">
        <type>input</type>
        <location type="id" item="">verifyCode</location>
        <desc>验证码输入框</desc>
    </element>
    
    <element name="getVerifyCode" interfacename="" group="" type="web">
        <type>button</type>
        <location type="class" item="">acquire-verification-code</location>
        <desc>获取验证码按钮</desc>
    </element>
    
    <!-- 登录模式切换 -->
    <element name="accountLoginTab" interfacename="" group="" type="web">
        <type>text</type>
        <location type="text" item="">账号登录</location>
        <desc>账号登录标签</desc>
    </element>
    
    <element name="verifyCodeLoginTab" interfacename="" group="" type="web">
        <type>text</type>
        <location type="text" item="">验证码登录</location>
        <desc>验证码登录标签</desc>
    </element>
</model>
</models>
```

---

## 5. 数据表编写规范

### 5.1 数据表结构

数据表 = Excel 中的一个 Sheet，**Sheet 名 = 数据表名**

```
Sheet 名: Login  →  数据表名: Login
```

### 5.2 列定义

| 列 | 必需 | 说明 |
|----|------|------|
| DataID | ✅ | 数据行唯一标识 |
| Remark | 推荐 | 数据说明 |
| 其他列 | ✅ | **必须与 model 元素 name 一致** |

### 5.3 示例

**Sheet: Login**

| DataID | Remark | username | password |
|--------|--------|----------|----------|
| L001 | 有效账号登录 | testuser | Test@123456 |
| L002 | 空用户名 | | Test@123456 |
| L003 | 空密码 | testuser | |
| L004 | 错误密码 | testuser | wrongpassword |

### 5.4 数据引用语法

```
表名.DataID           # 引用整行数据
表名.DataID.字段名     # 引用特定字段
```

**示例:**

```
Login.L001            # 返回: {username: "testuser", password: "Test@123456"}
Login.L001.username   # 返回: "testuser"
Login.L002.password   # 返回: "Test@123456"
```

### 5.5 Return 引用 — 跨步骤传递运行时数据

在真实测试场景中，很多数据是在测试运行时才产生的（比如新建订单的订单号、注册用户的 ID）。这些数据无法提前写在数据表中。**Return 机制**解决了这个问题：框架自动保存每个步骤的关键返回值，后续步骤可以通过 `Return[index]` 引用它们。

#### 语法

```
Return[-1]    # 上一个步骤的返回值
Return[-2]    # 上上个步骤的返回值
Return[0]     # 第一个步骤的返回值
Return[3]     # 第四个步骤的返回值
```

#### 哪些关键字会产生返回值

| 关键字 | 返回值内容 |
|--------|-----------|
| get / get_text | 获取到的元素文本内容 |
| verify | 验证时获取到的实际值（元素文本、可见性等） |
| assert | 断言结果（True/False） |
| type（批量模式） | 本次输入使用的完整数据行 |
| http_get/post/put/delete | HTTP 响应 body 文本 |
| send | HTTP 响应 body 文本 |
| DB | 查询结果集或受影响行数 |

#### 典型场景：跨步骤数据传递

**场景**: 创建订单后验证订单号

| 阶段 | 动作 | 模型 | 数据 | 说明 |
|------|------|------|------|------|
| 测试步骤 | type | Order | Order.NEW001 | 填写订单信息并提交 |
| 预期结果 | get_text | | #order-number | 获取页面上的订单号 → 自动保存为 Return |
| 后处理 | verify | | Return[-1] | 验证订单号非空 |

**场景**: API 创建资源后用返回的 ID 做后续操作

| 阶段 | 动作 | 模型 | 数据 |
|------|------|------|------|
| 预处理 | http_post | | https://api.example.com/users |
| 测试步骤 | verify | | Return[-1] |

#### 注意事项

- Return 索引从 0 开始（正向），或从 -1 开始（反向取最新）
- 如果引用的 Return 索引不存在，原文保持不变（不会报错）
- Return 值在**同一个用例文件的所有用例**间共享（跨用例可用）
- 每次 `close` 后重建驱动不会清空 Return 值

---

## 6. GlobalValue 编写规范

### 6.1 结构

| GroupName | Key | Value |
|-----------|-----|-------|
| DefaultValue | URL | https://example.com |
| DefaultValue | BrowserType | chromium |
| DefaultValue | WaitTime | 5 |

### 6.2 引用语法

```
GlobalValue.组名.变量名
```

**示例:**

```
GlobalValue.DefaultValue.URL          # 返回: "https://example.com"
GlobalValue.DefaultValue.BrowserType  # 返回: "chromium"
GlobalValue.DefaultValue.WaitTime     # 返回: "5"
```

### 6.3 常用全局变量

| 组名 | Key | 说明 | 示例值 |
|------|-----|------|--------|
| DefaultValue | URL | 测试环境地址 | https://www.cassmall.com/passport/login |
| DefaultValue | BrowserType | 浏览器类型 | chromium / firefox / webkit |
| DefaultValue | **WaitTime** | **默认步骤等待时间(秒)** | 5 |
| DefaultValue | Headless | 无头模式 | True / False |

### 6.4 ⚠️ 特殊项：DefaultValue.WaitTime（默认步骤等待时间）

`WaitTime` 是一个**具有特殊行为的全局变量**，它不仅可以作为数据引用使用，还会**自动影响测试执行节奏**。

#### 作用

设置 `DefaultValue.WaitTime` 后，框架会在**每个测试步骤执行完成后**自动等待指定的秒数，为页面渲染和网络请求留出缓冲时间。

#### 生效规则

| 场景 | 是否自动等待 | 说明 |
|------|-------------|------|
| open / type / click 等 UI 操作 | ✅ 等待 | 步骤执行后自动等待 WaitTime 秒 |
| wait 关键字 | ❌ 不等待 | wait 自身已包含等待逻辑，不再叠加默认等待 |
| close 关键字 | ❌ 不等待 | 浏览器已关闭，无需等待 |

#### 示例

```
# GlobalValue Sheet
| GroupName    | Key      | Value |
|------------- |----------|-------|
| DefaultValue | WaitTime | 5     |

# 执行流程：
# open → 执行 → 自动等待5秒
# type → 执行 → 自动等待5秒
# click → 执行 → 自动等待5秒
# wait 3 → 等待3秒 → 不再叠加默认等待
# close → 执行 → 不等待
```

#### WaitTime 与 wait 关键字的区别

| 特性 | DefaultValue.WaitTime | wait 关键字 |
|------|----------------------|-------------|
| 作用范围 | 所有步骤（全局） | 仅当前步骤（局部） |
| 配置位置 | GlobalValue Sheet | Case Sheet 中的动作列 |
| 等待时机 | 步骤执行**后**自动触发 | 作为**独立步骤**执行 |
| 典型用途 | 统一控制页面加载缓冲 | 特定场景的精确等待（如等待弹窗、异步加载） |

#### 使用建议

- **推荐设置 2~5 秒**：适合大多数 Web 页面的加载速度
- **设为 0 或不设置**：禁用默认等待，适合追求执行速度的场景
- **需要精确控制时**：使用 `wait` 关键字插入特定等待时间

---

## 7. 关键字参考

### 7.1 常用关键字

| 关键字 | 说明 | 模型参数 | 数据参数 |
|--------|------|----------|----------|
| open | 打开页面 | - | URL 或 GlobalValue 引用 |
| type | 输入文本 | 模型名（批量）或空 | 数据表引用（批量）或 locator |
| click | 点击元素 | - | 元素定位器 |
| verify | 验证 | 期望值（文本匹配时） | 元素定位器或 Return 引用 |
| get / get_text | 获取元素文本 | - | 元素定位器 |
| wait | 等待指定秒数 | - | 秒数 |
| close | 关闭浏览器 | - | - |
| screenshot | 截图 | - | 文件名(可选) |
| set | 设置变量 | - | 变量名=值 |

> **wait 关键字说明**：`wait` 是一个**独立的等待步骤**，用于在特定位置插入精确的等待时间。它与 `DefaultValue.WaitTime`（全局默认步骤等待）互不影响——`wait` 步骤执行后**不会**再叠加默认等待。详见 [6.4 特殊项：DefaultValue.WaitTime](#64-️-特殊项defaultvaluewaittime默认步骤等待时间)。

### 7.2 verify 验证关键字

`verify` 是 RodSki 的核心验证关键字，与 `type` 完全对称：

- **`type`**: 按模型 + 数据表 → **写入**界面
- **`verify`**: 按模型 + 数据表 → **读取**界面并**比较**

#### 核心用法：批量验证（model + 数据引用）

```
动作: verify    模型: ModelName    数据: TableName.DataID
```

框架遍历模型中的每个元素：
1. 用元素的定位器去界面上读取实际文本
2. 与数据表中同名字段的值做比较
3. 全部匹配 → PASS，任一不匹配 → FAIL

**示例**：验证订单详情页各字段

model.xml 定义：
```xml
<element name="orderNo" type="web"><location type="id">order-number</location></element>
<element name="amount" type="web"><location type="id">order-amount</location></element>
<element name="status" type="web"><location type="id">order-status</location></element>
```

数据表 `OrderExpect`:

| DataID | orderNo | amount | status |
|--------|---------|--------|--------|
| E001 | ORD-2026001 | 10元 | 已完成 |

用例写法：

| 动作 | 模型 | 数据 |
|------|------|------|
| verify | OrderDetail | OrderExpect.E001 |

执行时框架自动：
- 读取 `#order-number` 的文本 → 比较是否为 `ORD-2026001`
- 读取 `#order-amount` 的文本 → 比较是否为 `10元`
- 读取 `#order-status` 的文本 → 比较是否为 `已完成`

接口类型同理：如果模型元素的 `type="interface"`，则从上一次接口返回值中取对应字段来比较。

#### 简单用法（无 model/data 时的降级模式）

| 用例 | 动作 | 模型 | 数据 | 效果 |
|------|------|------|------|------|
| 检查元素可见 | verify | | #login-form | 元素存在且可见 → PASS |
| 验证页面标题 | verify | 首页 | .page-title | 元素文本包含"首页" → PASS |
| 验证 Return 值 | verify | ORD-001 | Return[-1] | 上一步返回值 == "ORD-001" → PASS |
| 验证非空 | verify | | Return[-1] | 上一步返回值非空 → PASS |

### 7.3 HTTP 关键字

| 关键字 | 说明 | 数据格式 |
|--------|------|----------|
| http_get | GET 请求 | URL |
| http_post | POST 请求 | URL\|body |
| http_put | PUT 请求 | URL\|body |
| http_delete | DELETE 请求 | URL |

### 7.4 DB 数据库关键字

#### 用例格式

| 动作 | 模型 | 数据 |
|------|------|------|
| DB | 连接变量名 | SQL数据表引用 或 直接SQL |

- **模型** = GlobalValue 中数据库连接配置的组名（如 `cassdb`）
- **数据** = `TableName.DataID`（从数据表读取 SQL）或直接 SQL 语句

#### GlobalValue 连接配置

在 GlobalValue Sheet 中以组名定义数据库连接信息：

| GroupName | Key | Value |
|-----------|-----|-------|
| cassdb | type | mysql |
| cassdb | host | 192.168.1.100 |
| cassdb | port | 3306 |
| cassdb | database | testdb |
| cassdb | username | root |
| cassdb | password | secret123 |

支持的 `type` 值：

| type | 数据库 | 需安装 |
|------|--------|--------|
| mysql / mariadb | MySQL / MariaDB | `pip install pymysql` |
| postgresql / pg | PostgreSQL | `pip install psycopg2` |
| sqlite | SQLite | 内置，database 填文件路径 |
| sqlserver / mssql | SQL Server | `pip install pymssql` |

#### SQL 数据表

创建一个 Excel Sheet 存放 SQL，Sheet 名即表名（如 `QuerySQL`）：

| DataID | Remark | sql | operation | var_name |
|--------|--------|-----|-----------|----------|
| Q001 | 查询订单金额 | SELECT amount FROM orders WHERE id='ORD001' | query | order_amount |
| Q002 | 插入审计日志 | INSERT INTO audit_log (action) VALUES ('test') | execute | |
| Q003 | 按条件查询 | SELECT * FROM users WHERE name='Return[-1]' | query | user_info |

| 列名 | 必需 | 说明 |
|------|------|------|
| DataID | 是 | 数据行标识 |
| sql | 是 | 实际执行的 SQL 语句 |
| operation | 否 | `query`（查询，默认）或 `execute`（增删改） |
| var_name | 否 | 将结果存入变量名，后续可通过变量引用 |

SQL 中可以使用 `Return[-1]` 引用前序步骤的返回值。

#### SQL 数据表说明文件（.md）

每个 SQL 数据表 Sheet 应配套一个同名的 Markdown 说明文件，放在 model 目录下：

```
product/CASSTIME/login/
├── case/
│   └── casstime_login_case.xlsx
└── model/
    ├── model.xml
    ├── OrderSQL.md       ← 与 Sheet 名一致
    └── AuditSQL.md
```

说明文件内容应包括：该数据表的用途、涉及的业务场景、SQL 语句的设计意图、依赖的数据库表结构等。此文件不参与框架执行，但它是测试用例的组成部分——供测试设计者和 AI 辅助执行时作为上下文参考。

示例 `OrderSQL.md`：

```markdown
# OrderSQL - 订单查询 SQL 集

## 用途
用于订单管理模块的自动化测试，包含订单创建后的数据验证和测试数据清理。

## 涉及表
- orders: 订单主表 (order_no, amount, status, created_at)
- audit_log: 审计日志表 (action, operator, timestamp)

## SQL 说明
| DataID | 用途 |
|--------|------|
| Q001 | 按订单号查询金额，用于验证创建订单后金额是否正确 |
| Q002 | 插入审计日志，用于测试后处理阶段记录操作 |
| Q003 | 按用户名查询，配合 Return[-1] 获取前序步骤产生的用户名 |
```

#### 完整示例

**GlobalValue:**

| GroupName | Key | Value |
|-----------|-----|-------|
| cassdb | type | mysql |
| cassdb | host | 10.0.0.1 |
| cassdb | port | 3306 |
| cassdb | database | order_system |
| cassdb | username | tester |
| cassdb | password | Test@123 |

**SQL 数据表 (Sheet: OrderSQL):**

| DataID | Remark | sql | operation | var_name |
|--------|--------|-----|-----------|----------|
| S001 | 查询订单 | SELECT * FROM orders WHERE order_no='ORD001' | query | order_data |
| S002 | 清理测试数据 | DELETE FROM orders WHERE source='autotest' | execute | |

**Case Sheet:**

| 动作 | 模型 | 数据 |
|------|------|------|
| DB | cassdb | OrderSQL.S001 |
| verify | | Return[-1] |
| DB | cassdb | OrderSQL.S002 |

执行流程：
1. 从 GlobalValue 读取 `cassdb` 组的连接信息 → 连接 MySQL
2. 从 `OrderSQL` 表的 `S001` 行读取 SQL → 执行查询
3. 查询结果通过 `Return[-1]` 可供后续步骤引用

---

## 8. 完整示例

### 8.1 项目结构

```
product/CASSTIME/login/
├── case/
│   └── casstime_login_case.xlsx   # 测试用例文件
├── model/
│   └── model.xml                  # 页面模型文件
└── file/                          # 附件目录
```

### 8.2 model.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<models>
<model name="Login" servicename="">
    <element name="username" interfacename="" group="" type="web">
        <type>input</type>
        <location type="id" item="">userName</location>
    </element>
    <element name="password" interfacename="" group="" type="web">
        <type>input</type>
        <location type="id" item="">password</location>
    </element>
    <element name="loginBtn" interfacename="" group="" type="web">
        <type>button</type>
        <location type="class" item="">btn-submit</location>
    </element>
</model>
</models>
```

### 8.3 Excel 内容

**Case Sheet (部分):**

| 执行控制 | 用例编号 | 标题 | ... | 预处理动作 | 预处理模型 | 预处理数据 | 测试动作 | 测试模型 | 测试数据 | ... |
|---------|---------|------|-----|-----------|-----------|-----------|---------|---------|---------|-----|
| 是 | c001 | 登录测试 | ... | open | Login | GlobalValue.DefaultValue.URL | type | Login | Login.L001 | ... |

**Login Sheet:**

| DataID | Remark | username | password |
|--------|--------|----------|----------|
| L001 | 有效登录 | testuser | Test@123456 |

**GlobalValue Sheet:**

| GroupName | Key | Value |
|-----------|-----|-------|
| DefaultValue | URL | https://www.cassmall.com/passport/login |

### 8.4 运行命令

```bash
cd rodski
python3 ski_run.py ../product/CASSTIME/login/case/casstime_login_case.xlsx
```

---

## 附录：常见问题

### Q1: 用例没有执行？

检查：
1. Case Sheet 是否有 **2行表头**，数据从第3行开始
2. 执行控制列是否为 `是`（不是 `是/否`、`Y/N` 等）

### Q2: type 关键字输入失败？

检查：
1. model.xml 元素 name 是否与数据表列名一致
2. 定位方式是否正确（使用浏览器开发者工具验证）

### Q3: 数据引用不生效？

检查：
1. 数据表 Sheet 名是否正确
2. DataID 是否存在
3. 引用格式是否正确：`表名.DataID.字段名`

### Q4: open 关键字失败？

检查：
1. GlobalValue 中 URL 是否正确配置
2. URL 是否可访问
3. 使用完整引用：`GlobalValue.DefaultValue.URL`

---

**文档版本**: v1.0  
**最后更新**: 2026-03-20