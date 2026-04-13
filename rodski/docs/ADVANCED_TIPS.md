# RodSki 高级技巧实用指南

**版本**: v1.0
**日期**: 2026-04-05
**适用框架**: RodSki v3.0+

---

## 目录

1. [定位器自动切换](#1-定位器自动切换)
2. [传统单定位器 vs 多定位器对照](#2-传统单定位器-vs-多定位器对照)
3. [完整示例：登录页定位器切换](#3-完整示例登录页定位器切换)
4. [执行结果说明](#4-执行结果说明)

---

## 1. 定位器自动切换

### 功能说明

RodSki 支持为**同一个元素定义多个定位器**，按 `priority` 从小到大依次尝试。当首选定位器因页面 DOM 变化而失败时，框架**不会直接报错**，而是自动尝试下一个定位器，直到成功或全部失败。

### 工作流程

```
priority=1 定位器 → 成功？→ 执行操作，结束
                      ↓ 失败
priority=2 定位器 → 成功？→ 执行操作，结束
                      ↓ 失败
priority=3 定位器 → 成功？→ 执行操作，结束
                      ↓ 失败
... 全部失败 → 抛出 ElementNotFoundError
```

### 日志表现

执行时可以在日志中观察到切换过程：

```
定位器 id=loginBtn 成功 (priority=1)       ← 首选命中，直接成功
```

或降级时：

```
定位器 id=loginBtn 失败，尝试下一个...
定位器 xpath=//button[@class='login'] 成功 (priority=2)  ← 降级成功
```

---

## 2. 定位器格式说明

### ~~单定位器（传统写法）~~ — 已移除（v5.4.0）

> **⚠️ 已移除（v5.4.0）**：以下简化格式已从解析器中移除，不再支持。保留此节仅供历史参考。

~~每个元素只定义一种定位方式，`<element>` 标签直接写 `type` + `value`~~：

```xml
<!-- ❌ 已移除（v5.4.0）：此格式不再支持 -->
<element name="loginBtn" type="class" value="btn-submit" desc="登录按钮"/>
```

~~**特点**：简单直接，但定位器失败就报错，没有回退机制。~~

### 多定位器（唯一支持的格式）

使用 `<location>` 子节点，为同一元素定义定位策略。这是 **v5.4.0 起唯一支持的定位器格式**：

```xml
<element name="loginBtn" type="web">
  <type>button</type>
  <location type="class" priority="1">btn-submit</location>
  <location type="css" priority="2">.btn-submit</location>
  <location type="xpath" priority="3">//button[contains(@class,'btn-submit')]</location>
</element>
```

**特点**：首选失败后自动降级，提高用例在页面变化时的存活率。支持单个或多个 `<location>` 子节点。

### 格式说明

> **v5.4.0 起**，`<location>` 子节点格式是唯一支持的定位器格式。

| 维度 | ~~单定位器（已移除）~~ | 多定位器（`<location>` 子节点） |
|------|---------|---------|
| 写法 | ~~`type="id" value="xxx"`~~ 已移除（v5.4.0） | `<location>` 子节点 |
| 失败处理 | ~~直接报错~~ | 自动尝试下一个 |
| 适用场景 | ~~已不再支持~~ | **所有场景（唯一格式）** |
| 推荐策略 | ~~不可用~~ | **必须使用** |

---

## 3. 完整示例：登录页定位器切换

以下示例来自 `CassMall_examples/login/`，演示如何在登录场景中使用定位器自动切换。

### 3.1 模型定义（model.xml）

**~~模型 1 — `LoginPage`（传统单定位器）~~ — 已移除（v5.4.0）**

> **⚠️ 已移除（v5.4.0）**：以下单定位器简化格式已从解析器中移除，仅供历史参考。请使用模型 2 的 `<location>` 子节点格式。

```xml
<!-- ❌ 已移除（v5.4.0）：以下格式不再支持 -->
<model name="LoginPage">
  <element name="usernameById"       type="id"    value="userName"         desc="用户名输入框 - id 定位器"/>
  <element name="passwordByName"     type="name"  value="password"         desc="密码输入框 - name 定位器"/>
  <element name="agreeCheckboxByCss" type="css"   value="label.br-checkbox" desc="同意协议复选框 - css 定位器"/>
  <element name="loginBtnByClass"    type="class" value="btn-submit"       desc="登录按钮 - class 定位器"/>
  <element name="accountTabByXpath"  type="xpath" value="//span[@type='PASSWORD']" desc="账号登录页签 - xpath 定位器"/>
  <element name="accountTabByText"   type="text"  value="账号登录"         desc="账号登录标签 - text 定位器"/>
  <element name="formByTag"          type="tag"   value="form"             desc="登录表单容器 - tag 定位器"/>
</model>
```

**模型 2 — `LoginPageSwitch`（多定位器自动切换）**

```xml
<model name="LoginPageSwitch">

  <!-- 账号登录页签：id → xpath → css → text -->
  <element name="accountTab" type="web">
    <type>span</type>
    <location type="id" priority="1">accountTab</location>
    <location type="xpath" priority="2">//span[@type='PASSWORD']</location>
    <location type="css" priority="3">span[type=PASSWORD]</location>
    <location type="text" priority="4">账号登录</location>
  </element>

  <!-- 用户名输入框：id → name → css → xpath -->
  <element name="username" type="web">
    <type>input</type>
    <location type="id" priority="1">userName</location>
    <location type="name" priority="2">userName</location>
    <location type="css" priority="3">#userName</location>
    <location type="xpath" priority="4">//input[@id='userName']</location>
  </element>

  <!-- 密码输入框：id → name → css → xpath -->
  <element name="password" type="web">
    <type>input</type>
    <location type="id" priority="1">password</location>
    <location type="name" priority="2">password</location>
    <location type="css" priority="3">#password</location>
    <location type="xpath" priority="4">//input[@id='password']</location>
  </element>

  <!-- 同意协议复选框：css → xpath -->
  <element name="agreeCheckbox" type="web">
    <type>label</type>
    <location type="css" priority="1">label.br-checkbox</location>
    <location type="xpath" priority="2">//label[contains(@class,'br-checkbox')]</location>
  </element>

  <!-- 登录按钮：class → css → xpath -->
  <element name="loginBtn" type="web">
    <type>button</type>
    <location type="class" priority="1">btn-submit</location>
    <location type="css" priority="2">.btn-submit</location>
    <location type="xpath" priority="3">//button[contains(@class,'btn-submit')]</location>
  </element>

</model>
```

### 3.2 测试数据（data.xml）

```xml
<!-- LoginPageSwitch 数据表：引用多定位器模型的元素 -->
<datatable name="LoginPageSwitch">
  <row id="S001" remark="自动切换定位器 - 小李账号">
    <field name="accountTab">click</field>
    <field name="username">15521344075</field>
    <field name="password">Cass2025</field>
    <field name="agreeCheckbox">click</field>
    <field name="loginBtn">click</field>
  </row>
  <row id="S002" remark="自动切换定位器 - 小辉账号">
    <field name="accountTab">click</field>
    <field name="username">13395432251</field>
    <field name="password">Cass2025</field>
    <field name="agreeCheckbox">click</field>
    <field name="loginBtn">click</field>
  </row>
</datatable>
```

注意：数据行中的 `field name` 引用的是**模型中的元素名**（如 `accountTab`、`username`），而非定位器类型。框架在运行时自动处理定位器选择。

### 3.3 测试用例（case/locator_switch_demo.xml）

```xml
<cases>
  <!-- 测试 1：小李账号 -->
  <case id="locator_switch_xiaoli" title="定位器自动切换 - 小李账号"
        execute="是" component_type="界面">
    <pre_process>
      <test_step action="navigate" data="https://ec-hwbeta.casstime.com/passport/login"/>
      <test_step action="wait" data="3"/>
    </pre_process>
    <test_case>
      <!-- 使用 LoginPageSwitch 模型（多定位器） -->
      <test_step action="type" model="LoginPageSwitch" data="S001"/>
      <test_step action="wait" data="5"/>
      <test_step action="screenshot" data="locator_switch_xiaoli_result.png"/>
    </test_case>
  </case>

  <!-- 测试 2：小辉账号 -->
  <case id="locator_switch_xiaohui" title="定位器自动切换 - 小辉账号"
        execute="是" component_type="界面">
    <pre_process>
      <test_step action="navigate" data="https://ec-hwbeta.casstime.com/passport/login"/>
      <test_step action="wait" data="3"/>
    </pre_process>
    <test_case>
      <test_step action="type" model="LoginPageSwitch" data="S002"/>
      <test_step action="wait" data="5"/>
      <test_step action="screenshot" data="locator_switch_xiaohui_result.png"/>
    </test_case>
  </case>
</cases>
```

### 3.4 逐步执行流程

以 `locator_switch_xiaoli` 为例，执行过程如下：

**阶段 1 — 预处理（pre_process）**

| 步骤 | action | 说明 |
|------|--------|------|
| 1 | `navigate` → 登录页 URL | 打开浏览器，导航到登录页面 |
| 2 | `wait 3` | 等待 3 秒，页面完全加载 |

**阶段 2 — 用例（test_case）**

执行 `<test_step action="type" model="LoginPageSwitch" data="S001"/>`：

框架解析数据行 `S001`，对每个字段执行定位 → 操作：

| 字段 | 值 | 定位尝试过程 | 最终结果 |
|------|----|-------------|---------|
| `accountTab` | click | id=`accountTab` → **成功** | 点击账号登录页签 |
| `username` | 15521344075 | id=`userName` → **成功** | 输入手机号 |
| `password` | Cass2025 | id=`password` → **成功** | 输入密码 |
| `agreeCheckbox` | click | css=`label.br-checkbox` → **成功** | 勾选同意协议 |
| `loginBtn` | click | class=`btn-submit` → **成功** | 点击登录 |

> 正常情况下所有 priority=1 命中，流程和普通登录无区别。

| 步骤 | action | 说明 |
|------|--------|------|
| | `wait 5` | 等待 5 秒登录跳转 |
| | `screenshot` | 截图保存为 `locator_switch_xiaoli_result.png` |

**当页面 DOM 变化时（假设 id 被移除）**

| 字段 | 定位尝试过程 | 结果 |
|------|-------------|------|
| `username` | id=`userName` **失败** → name=`userName` → **成功** | 自动降级到 name 定位 |

框架日志中会体现降级过程，无需修改用例即可适应页面变化。

---

## 4. 执行结果说明

### 结果目录结构

```
login/
└── result/
    └── rodski_20260405_201948/          ← 执行结果目录
        ├── result.xml                   ← 执行结果报告
        └── screenshots/
            ├── locator_switch_xiaoli_01_预处理_*.png
            ├── locator_switch_xiaoli_failure.png      ← 失败截图（如有）
            ├── locator_switch_xiaohui_01_预处理_*.png
            └── locator_switch_xiaohui_failure.png     ← 失败截图（如有）
```

### 如何验证自动切换生效

1. **查看执行日志**：搜索 `定位器` 关键字，观察是否出现降级尝试
2. **对比两组用例**：`login_xiaoli.xml`（单定位器）vs `locator_switch_demo.xml`（多定位器），如果单定位器失败但多定位器成功，说明自动切换机制生效
3. **故意破坏首选定位器**：将模型中 priority=1 的值改为不存在的值，验证是否自动降级到 priority=2

### 推荐的定位器降级策略

| Priority | 定位器类型 | 说明 |
|----------|-----------|------|
| 1 | `id` / `name` | 最快最稳定，首选 |
| 2 | `class` / `css` | 次选，CSS 选择器 |
| 3 | `xpath` | 兜底传统定位器 |
| 4 | `text` | 文本匹配 |
| 5 | `ocr` / `vision` / `vision_bbox` | 视觉定位，最后防线 |
