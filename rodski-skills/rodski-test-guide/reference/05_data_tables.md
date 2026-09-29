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

# 行级编辑（v11.6.0）：直接改 data.sqlite，改完即可重跑，无需 import
rodski data set <module> <table> <data_id> field=value [field=value ...]   # 修改已有行
rodski data add-row <module> <table> <data_id> field=value [...] [--remark 备注]   # 新增行：必须给出完整字段集合
rodski data delete-row <module> <table> <data_id>                          # 删除行
```

例如接口返回的订单数由 1 变为 2，只改期望值：

```bash
rodski data set product/shop/order OrderDB_verify V_OK n=2
```

- `data set` 只能修改 schema 中已声明的字段；写错字段名会报错并列出合法字段。
- `data add-row` 缺字段时报错，提示为缺少的字段填 `BLANK` / `NULL` / `NONE`（字段集合一致约束，见 5.1）。
- 值中含空格时整体加引号：`rodski data set <module> Login_verify V001 "welcomeMsg=欢迎, admin"`。


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
| `accept` / `dismiss` / `accept:文本` | 仅用于 `page=dialog` 元素（v11.6.0）：为下一次原生弹窗注册一次性处理器 | `<field name="dialog">accept:加急</field>`，见 [4.3.4](#434-页面属性定位器-pagev1160) |

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
<!-- data.sqlite 中的 QuerySQL 表：同表混用 query 行和 sql 行时，所有行都带齐 query/sql/operation，不用的填 BLANK -->
<datatable name="QuerySQL">
  <row id="Q001" remark="查询总数">
    <field name="query">count</field>
    <field name="sql">BLANK</field>
    <field name="operation">BLANK</field>
  </row>
  <row id="Q002" remark="插入数据">
    <field name="query">BLANK</field>
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
- SQLite 方案下，数据库逻辑表同样必须固定字段集合；同表混用 `query` 行和 `sql` 行时，每行都要带齐这些字段，不用的填 `BLANK`
- `sql` / `query` 的取值为 `BLANK` / `NULL` / `NONE` / 空时视为**未提供**（v11.5.2 起）：先看 `sql`，没有有效 `sql` 再看 `query`；两者都没有则报错
- **参数占位符**为 `:name`，`name` 必须以字母或下划线开头（v11.5.2 起）。写在单引号 / 双引号字符串里的冒号不是参数，例如 `created_at >= '2026-01-01 00:00:00'` 中的 `:00`；PostgreSQL 的 `::type` 类型转换也不是参数

**校验查询结果**：数据库模型中用 `type="database"`、`<location type="field">列名</location>` 声明要校验的列，执行 `DB` 后用 `verify 模型名 行ID` 比对（读取 `模型名_verify` 表，与第一行结果比较），不要用 `<if>` 或 `evaluate` 判断：

```xml
<test_step action="DB" model="OrderDB" data="Q_TIME"/>
<test_step action="verify" model="OrderDB" data="V_TIME"/>
```

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

### 5.7 verify 期望值：操作符、原生断言与自动重试（v11.6.0）

`_verify` 表的字段值除了写字面期望值，还可以写**单键 JSON 操作符**。

#### 5.7.1 操作符一览

| 操作符 | 适用 | 含义 | 字段值示例 |
|--------|------|------|-----------|
| `$gt` / `$gte` / `$lt` / `$lte` | UI / 接口 / DB | 数值比较 | `{"$gte": 100}` |
| `$contains` | UI / 接口 / DB | 字符串包含 / 数组包含 | `{"$contains": "/order/"}` |
| `$count` | UI 元素 | 定位器匹配的元素数量 = N | `{"$count": 10}` |
| `$count_gte` / `$count_lte` | UI 元素 | 匹配数量 ≥ N / ≤ N | `{"$count_gte": 1}` |
| `$exists` | UI 元素 | 元素存在 / 不存在 | `{"$exists": true}` / `{"$exists": false}` |
| `$visible` | UI 元素 | 元素可见 / 不可见 | `{"$visible": true}` |

- 每个字段值只能有一个操作符；操作符右侧只能是字面量（不能写 `${Return[-1]}`）。
- `$count*` / `$exists` / `$visible` 作用于该字段对应模型元素的定位器（支持 `frame`），**只用于 UI 模型的 DOM 元素**；接口返回数组的长度用 `字段.length` + `$gt` 等数值操作符。
- **0 匹配不会被跳过**：选择器失效、元素一个都没找到时，按「实际 0 / 不存在」判定。`{"$count": 10}` 会失败并报「期望 10，实际 0」。这正是原生断言比 `evaluate` 断言可靠的地方。

**示例：异步表格有 10 行**（`AsyncTable` 模型的 `rows` 元素定位 `#orderBody tr.order-row`）：

| AsyncTable_verify | rows | total |
|-------------------|------|-------|
| V_ROWS | `{"$count": 10}` | `共 10 条` |
| V_EXISTS | `{"$exists": true}` | `BLANK` |

```xml
<test_step action="navigate" model="" data="GlobalValue.Site.URL/async_table.html"/>
<test_step action="verify" model="AsyncTable" data="V_ROWS"/>   <!-- 不需要 wait -->
```

#### 5.7.2 UI verify 自动重试（替代 `wait`）

UI 模型的 `verify` 会在自动等待 `DefaultValue.AutoWait` 毫秒内（默认 `5000`，即 5 秒；每 200ms 一轮）反复读取**全部**字段并比对，全部匹配立即通过；超时后按最后一次读到的值报失败，逐字段列出期望 / 实际。

- 因此异步加载、跳转后的页面**直接写 `verify`**，不要在前面插 `wait 1`/`wait 2`。等元素消失写 `{"$exists": false}` 或 `{"$visible": false}`。
- 接口 / DB 模型的 `verify` 不重试（结果是一次性的）。
- `DefaultValue.AutoWait=0` 关闭重试，恢复单次比对；页面特别慢时可调大（如 `10000` = 10 秒），见 [§6.4](#64-waittime-与执行策略配置v1160)。
- 预期失败（`expect_fail="是"`）的 UI 用例要等到超时才判定失败，耗时约等于 `AutoWait`。

#### 5.7.3 strict / subset 与 BLANK

- 默认 `strict`：`_verify` 行必须包含模型的全部字段。只关心部分字段时，在步骤上写 `match_mode="subset"`，或在不校验的字段填 `BLANK`（UI / DB 模型中 `BLANK` 表示跳过该字段；接口模型中 `BLANK` 表示期望空字符串）。

```xml
<test_step action="verify" model="Login" data="V001" match_mode="subset"/>
```

- strict 模式下某行一半以上字段都是 `BLANK` 时，`rodski case lint` 会提示改用 `match_mode="subset"`（INFO）。
- 缺字段的报错会直接给出这两种修法。

#### 5.7.4 什么时候还用 evaluate

`evaluate` 是逃生舱：只有原生断言表达不了的检查才用它。脚本里有 `&&`、`<`、引号时，不要写在 XML 属性里，放到模块内的 `fun/js/*.js`，用 `file:` 引用（见 [§8.7](#87-evaluate--逃生舱与-file-脚本v1160)）。

| 想断言的内容 | 推荐写法 | 不推荐（lint 会提示） |
|--------------|----------|----------------------|
| 列表行数 | `{"$count": 10}` | `evaluate` 中 `querySelectorAll(...).length` |
| 元素出现 / 消失 | `{"$exists": true/false}` | `evaluate` 中 `querySelector(...)` 判空 |
| 当前路径 / URL / 标题 | `page` 元素 + `verify`（4.3.4） | `evaluate` 中 `location.pathname` |
| 弹窗 | `DialogPolicy` + `page=dialog` 元素 | `evaluate` 中 `window.confirm = ...` |
| 查询结果 | `DB` + `verify`（5.5） | `evaluate` / `<if>` 判断 |

---
