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
| open | 打开页面 | 模型名 | URL 或 GlobalValue 引用 |
| type | 输入文本 | 模型名.元素名 或 模型名 | 数据表引用 |
| click | 点击元素 | 模型名.元素名 | - |
| wait | 插入等待时间（见下方说明） | - | 秒数 |
| verify | 验证 | 模型名.元素名 或 空 | 验证条件 |
| close | 关闭浏览器 | - | - |
| screenshot | 截图 | - | 文件名(可选) |

> **wait 关键字说明**：`wait` 是一个**独立的等待步骤**，用于在特定位置插入精确的等待时间。它与 `DefaultValue.WaitTime`（全局默认步骤等待）互不影响——`wait` 步骤执行后**不会**再叠加默认等待。详见 [6.4 特殊项：DefaultValue.WaitTime](#64-️-特殊项defaultvaluewaittime默认步骤等待时间)。

### 7.2 verify 验证条件

| 条件 | 说明 | 示例 |
|------|------|------|
| visible | 元素可见 | `visible` |
| hidden | 元素隐藏 | `hidden` |
| text_contains:xxx | 文本包含 | `text_contains:成功` |
| text_equals:xxx | 文本等于 | `text_equals:登录` |
| title_contains:xxx | 标题包含 | `title_contains:首页` |
| title_equals:xxx | 标题等于 | `title_equals:开思` |

### 7.3 HTTP 关键字

| 关键字 | 说明 | 数据格式 |
|--------|------|----------|
| http_get | GET 请求 | URL |
| http_post | POST 请求 | URL\|body |
| http_put | PUT 请求 | URL\|body |
| http_delete | DELETE 请求 | URL |

### 7.4 数据库关键字

| 关键字 | 说明 | 数据格式 |
|--------|------|----------|
| db_query | 查询数据 | SQL\|变量名 |
| db_insert | 插入数据 | SQL |
| db_update | 更新数据 | SQL |
| db_delete | 删除数据 | SQL |

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