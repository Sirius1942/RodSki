<!-- 自动生成 from rodski/docs/TEST_CASE_WRITING_GUIDE.md  请勿手工编辑 -->

## 5. 数据表 — 测试数据编写

### 5.1 数据存储

所有测试数据统一存储在 `data/data.sqlite`，使用 EAV 元表结构：

| 元表 | 说明 |
|------|------|
| `rs_datatable` | 逻辑表注册（`table_name` = 模型名） |
| `rs_datatable_field` | 字段 schema（每张表的字段列表） |
| `rs_row` | 数据行（`data_id`） |
| `rs_field` | 字段值 |

**约束：**
- 逻辑表名必须与模型名一致
- 同一逻辑表所有行的字段集合必须完全一致（与 schema 一致）
- 验证数据表（`_verify` 后缀）`table_kind='verify'`，输入数据表 `table_kind='data'`
- v6.7.6 起，SQLite 数据表严格校验字段一致性。同一逻辑表的每一行必须包含 schema 声明的全部字段。缺字段必须显式填写 BLANK、NULL 或 NONE。

### 5.2 写入数据的方式

#### 方式一：从 XML 迁移（推荐用于历史数据）

```bash
rodski data import <module>            # 默认跳过已存在的表
rodski data import <module> --overwrite  # 覆盖已存在的表
```

XML 格式（仅用于迁移，不再作为运行时数据源）：
```xml
<?xml version="1.0" encoding="UTF-8"?>
<datatables>
  <datatable name="Login">
    <row id="L001" remark="管理员">
      <field name="username">admin</field>
      <field name="password">admin123</field>
    </row>
    <row id="L002">
      <field name="username">testuser</field>
      <field name="password">test123</field>
    </row>
  </datatable>
</datatables>
```

#### 方式二：直接写入 SQLite

```sql
-- 1. 注册逻辑表
INSERT INTO rs_datatable VALUES ('Login', 'Login', 'data', 'standard', '', CURRENT_TIMESTAMP);

-- 2. 声明字段 schema
INSERT INTO rs_datatable_field VALUES ('Login', 'username', 0);
INSERT INTO rs_datatable_field VALUES ('Login', 'password', 1);

-- 3. 插入数据行
INSERT INTO rs_row VALUES ('Login', 'L001', '管理员');
INSERT INTO rs_row VALUES ('Login', 'L002', '普通用户');

-- 4. 插入字段值
INSERT INTO rs_field VALUES ('Login', 'L001', 'username', 'admin');
INSERT INTO rs_field VALUES ('Login', 'L001', 'password', 'admin123');
INSERT INTO rs_field VALUES ('Login', 'L002', 'username', 'testuser');
INSERT INTO rs_field VALUES ('Login', 'L002', 'password', 'test123');
```

验证数据表（`_verify` 后缀）：
```sql
INSERT INTO rs_datatable VALUES ('Login_verify', 'Login_verify', 'verify', 'standard', '', CURRENT_TIMESTAMP);
INSERT INTO rs_datatable_field VALUES ('Login_verify', 'welcomeMsg', 0);
INSERT INTO rs_row VALUES ('Login_verify', 'V001', '');
INSERT INTO rs_field VALUES ('Login_verify', 'V001', 'welcomeMsg', '欢迎, admin');
```

### 5.3 数据表命名与引用规则

> **核心规则**：模型名 = 逻辑表名，强制一致。Case 的 `data` 只写 DataID，不写表名前缀。

| 关键字 | Case 写法 | 逻辑表（自动推导） |
|--------|-----------|---------------------|
| `type` | `type Login L001` | `Login` |
| `verify` | `verify Login V001` | `Login_verify` |
| `send` | `send LoginAPI D001` | `LoginAPI` |
| `DB` | `DB QuerySQL Q001` | `QuerySQL` |

**正确示例：**
```xml
<test_step action="send" model="RegisterAPI" data="L001"/>
```

**错误示例：**
```xml
<!-- 错误：data 不能写表名前缀 -->
<test_step action="send" model="RegisterAPI" data="RegisterAPI.L001"/>
```

### 5.3.1 rodski data 命令

```bash
# 列出模块中的所有逻辑表
rodski data list <module>

# 查看逻辑表字段列表
rodski data schema <module> <table>

# 查看指定数据行
rodski data show <module> <table> <data_id>

# 列出逻辑表中的前 N 行
rodski data query <module> <table> --limit 20

# 校验模块数据层
rodski data validate <module>

# 从 XML 迁移数据到 data.sqlite
rodski data import <module> [--overwrite]
```


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
<!-- data.sqlite 中的 Login 表 -->
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

DB 关键字使用的数据行也属于普通逻辑表，默认表名与数据库模型名一致，例如 `QuerySQL`。

```xml
<!-- data.sqlite 中的 QuerySQL 表 -->
<datatable name="QuerySQL">
  <row id="Q001" remark="查询总数">
    <field name="query">count</field>
  </row>
  <row id="Q002" remark="插入数据">
    <field name="sql">INSERT INTO items (name) VALUES ('test')</field>
    <field name="operation">execute</field>
  </row>
</datatable>
```

| 字段名 | 说明 |
|--------|------|
| query | 引用数据库模型中定义的 query 名称 |
| sql | 直接执行的 SQL 语句 |
| operation | 可选；直接写 SQL 时可显式指定 `query` / `execute` |
| 其他字段 | SQL 参数列，对应 `:param` 占位符 |

**约束：**
- Case 写法使用新语法：`<test_step action="DB" model="数据库模型名" data="Q001"/>`
- `model` 必须是 `type="database"` 的模型名，不再填写 GlobalValue 连接组名
- 连接信息来自数据库模型的 `connection` 属性，再映射到 `globalvalue.xml` 中对应组
- SQLite 方案下，数据库逻辑表同样必须固定字段集合；不能同表混用 `query` 行和 `sql` 行且字段集合不一致

### 5.6 数据表中使用 Return 引用

Return 引用**应写在数据表的字段值中**，不应直接写在 Case XML。

示例：验证上一步创建的物品

```xml
<!-- data.sqlite 中的 UI 验证表 -->
<datatable name="ItemDetail_verify">
  <row id="V001" remark="验证新物品名称">
    <field name="itemName">${Return[-1]}</field>
  </row>
</datatable>
```

Case XML 写法（验证写在 `<test_case>` 内，作为一条 `test_step`）：

```xml
<test_case>
  <test_step action="verify" model="ItemDetail" data="V001"/>
</test_case>
```

---
