# Skill 参考文档

**版本**: v2.0
**日期**: 2026-04-10
**目标读者**: AI Agent

---

## 1. 核心 Skill

### 1.1 navigate - 页面导航

**用途**: 打开 URL 或切换页面

**语法**:
```xml
<test_step action="navigate" model="" data="https://example.com"/>
```

**参数**:
- `model`: 留空
- `data`: URL 地址

**示例**:
```xml
<test_step action="navigate" model="" data="https://github.com/login"/>
```

---

### 1.2 type - 输入文本

**用途**: 在输入框中输入文本

**语法**:
```xml
<test_step action="type" model="PageModel" data="DataRowID"/>
```

**参数**:
- `model`: 页面模型名称
- `data`: 数据行 ID

**数据表结构**:
```xml
<datatable name="PageModel">
  <row id="DataRowID">
    <field name="elementName">输入内容</field>
  </row>
</datatable>
```

**示例**:
```xml
<!-- 用例 -->
<test_step action="type" model="LoginPage" data="L001"/>

<!-- 数据 -->
<row id="L001">
  <field name="username">admin</field>
  <field name="password">123456</field>
</row>
```

---

### 1.3 click - 点击元素

**用途**: 点击按钮、链接等元素

**语法**:
```xml
<test_step action="click" model="PageModel" data="DataRowID"/>
```

**数据表结构**:
```xml
<field name="elementName">click</field>
```

**示例**:
```xml
<test_step action="click" model="LoginPage" data="C001"/>

<row id="C001">
  <field name="loginBtn">click</field>
</row>
```

---

### 1.4 verify - 验证元素

**用途**: 验证元素文本或状态；`verify` 一旦存在即执行**严格全匹配**，任一字段不一致都会导致该步骤失败并使 case FAIL。

**语法**:
```xml
<test_step action="verify" model="PageModel" data="DataRowID"/>
```

**数据表结构**:
```xml
<field name="elementName">期望文本</field>
```

**示例**:
```xml
<test_step action="verify" model="HomePage" data="V001"/>

<row id="V001">
  <field name="welcomeMsg">欢迎, admin</field>
</row>
```

> 注意：接口/DB 模型的 _verify 数据表禁止使用 ${Return[-1]}，详见 CORE_DESIGN_CONSTRAINTS 4.3 节。

---

### 1.5 wait - 等待

**用途**: 等待指定时间或元素出现

**语法**:
```xml
<test_step action="wait" model="" data="秒数"/>
```

**示例**:
```xml
<test_step action="wait" model="" data="3"/>
```

---

### 1.6 close - 关闭浏览器

**用途**: 关闭浏览器或应用

**语法**:
```xml
<test_step action="close" model="" data=""/>
```

---

## 2. 桌面自动化 Skill

### 2.1 launch - 启动应用

**用途**: 启动桌面应用程序

**语法**:
```xml
<test_step action="launch" model="" data="应用路径或名称"/>
```

**示例**:
```xml
<test_step action="launch" model="" data="notepad.exe"/>
<test_step action="launch" model="" data="/Applications/Calculator.app"/>
```

---

### 2.2 run - 执行脚本

**用途**: 调用桌面操作脚本（键盘快捷键、鼠标操作等）

**语法**:
```xml
<test_step action="run" model="" data="脚本路径 参数"/>
```

**示例**:
```xml
<!-- 复制粘贴 -->
<test_step action="run" model="" data="fun/desktop/key_combo.py Ctrl+C"/>
<test_step action="run" model="" data="fun/desktop/key_combo.py Ctrl+V"/>

<!-- 鼠标操作 -->
<test_step action="run" model="" data="fun/desktop/mouse_click.py 100,200"/>
```

---

## 3. 高级 Skill

### 3.1 switch_window - 切换窗口

**用途**: 在多窗口/标签页间切换

**语法**:
```xml
<test_step action="switch_window" model="" data="窗口索引"/>
```

**示例**:
```xml
<test_step action="switch_window" model="" data="1"/>
```

---

### 3.2 switch_frame - 切换 iframe

**用途**: 切换到 iframe 内部

**语法**:
```xml
<test_step action="switch_frame" model="PageModel" data="DataRowID"/>
```

**示例**:
```xml
<test_step action="switch_frame" model="MainPage" data="F001"/>

<row id="F001">
  <field name="contentFrame">switch</field>
</row>
```

---

### 3.3 screenshot - 截图

**用途**: 保存当前页面截图

**语法**:
```xml
<test_step action="screenshot" model="" data="文件名"/>
```

**示例**:
```xml
<test_step action="screenshot" model="" data="login_page.png"/>
```

---

## 4. Skill 组合模式

### 4.1 登录流程

```xml
<test_case>
  <test_step action="navigate" model="" data="https://example.com/login"/>
  <test_step action="wait" model="" data="2"/>
  <test_step action="type" model="LoginPage" data="L001"/>
  <test_step action="click" model="LoginPage" data="C001"/>
  <test_step action="wait" model="" data="3"/>
  <test_step action="verify" model="HomePage" data="V001"/>
</test_case>
```

### 4.2 表单填写

```xml
<test_case>
  <test_step action="type" model="FormPage" data="F001"/>
  <test_step action="click" model="FormPage" data="C001"/>
  <test_step action="verify" model="FormPage" data="V001"/>
</test_case>
```

### 4.3 桌面应用操作

```xml
<test_case>
  <test_step action="launch" model="" data="notepad.exe"/>
  <test_step action="wait" model="" data="2"/>
  <test_step action="type" model="NotepadPage" data="T001"/>
  <test_step action="run" model="" data="fun/desktop/key_combo.py Ctrl+S"/>
  <test_step action="close" model="" data=""/>
</test_case>
```

---

## 4. 数据库操作 Skill

### 4.1 DB - 数据库查询和操作

**用途**: 执行数据库查询、插入、更新、删除操作

**语法**:
```xml
<test_step action="DB" model="DatabaseModel" data="DataRowID"/>
```

**参数**:
- `model`: 数据库模型名称（`type="database"`）
- `data`: 数据行 ID

**模型定义**:
```xml
<model name="OrderQuery" type="database" connection="sqlite_db" servicename="订单查询">
    <!-- 查询模板定义 -->
    <query name="list" remark="查询订单列表">
        <sql><![CDATA[
            SELECT order_no, customer_name, total_amount
            FROM orders
            WHERE status = :status
            LIMIT :limit
        ]]></sql>
        <params>
            <param name="status" type="string" default="completed"/>
            <param name="limit" type="int" default="10"/>
        </params>
    </query>
    
    <!-- 结果字段定义（用于 verify） -->
    <element name="order_no" type="database">
        <location type="field">order_no</location>
        <desc>订单号</desc>
    </element>
</model>
```

**数据表结构（模板模式）**:
```xml
<datatable name="OrderQuery">
    <row id="Q001" remark="查询已完成订单">
        <field name="query">list</field>
        <field name="status">completed</field>
        <field name="limit">5</field>
    </row>
</datatable>
```

**数据表结构（直接 SQL 模式）**:
```xml
<datatable name="OrderQuery">
    <row id="Q001" remark="查询订单">
        <field name="sql"><![CDATA[
            SELECT * FROM orders WHERE status = 'completed' LIMIT 5
        ]]></field>
        <field name="operation">query</field>
    </row>
</datatable>
```

**返回值**:
- 查询操作：返回列表 `[{row1}, {row2}, ...]`，自动保存到 `${Return[-1]}`
- 执行操作：返回 `{"affected_rows": N}`

**示例**:
```xml
<!-- 查询订单 -->
<test_step action="DB" model="OrderQuery" data="Q001"/>

<!-- 验证结果 -->
<test_step action="assert" condition="${len(Return[-1])} == 5"/>
<test_step action="assert" condition="${Return[-1][0].order_no} == 'ORD001'"/>

<!-- 插入订单 -->
<test_step action="DB" model="OrderQuery" data="Q002"/>
```

**连接配置（GlobalValue）**:
```xml
<globalvalue>
    <group name="sqlite_db">
        <var name="type" value="sqlite"/>
        <var name="database" value="demo.db"/>
    </group>
</globalvalue>
```

**注意事项**:
- SQL 必须定义在模型或数据表中，不能在测试用例中直接写 SQL
- 推荐使用模型定义查询模板，数据表只提供参数
- 查询结果默认最多返回 1000 行，超出会自动截断
- 参数化查询使用 `:param` 语法

<!-- 待 iteration-21 完成后验证示例可运行性 -->

---

## 5. 使用建议

### 5.1 Skill 选择策略

| 场景 | 推荐 Skill |
|------|-----------|
| 打开页面 | navigate |
| 填写表单 | type + click |
| 验证结果 | verify |
| 等待加载 | wait |
| 桌面应用 | launch + run |

### 5.2 常见错误

| 错误 | 原因 | 解决方案 |
|------|------|---------|
| 元素未找到 | 定位器错误 | 检查 vision 描述或坐标 |
| 操作超时 | 页面加载慢 | 增加 wait 步骤 |
| 验证失败 | 期望值不匹配 | 更新数据表中的期望值 |

---

**文档版本**: v2.0
**最后更新**: 2026-04-10
