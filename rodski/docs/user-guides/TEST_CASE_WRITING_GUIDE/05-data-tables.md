# 5. 数据表 XML — 测试数据编写

> **来源**: RodSki 测试用例编写指南 v3.4  
> 本文档为独立章节，完整指南请见 [TEST_CASE_WRITING_GUIDE.md](../TEST_CASE_WRITING_GUIDE.md)

---


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

