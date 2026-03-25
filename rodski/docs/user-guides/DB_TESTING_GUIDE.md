# 数据库测试指南

## 概述

RodSki 使用 **DB** 关键字执行数据库操作。数据库连接信息配置在 `globalvalue.xml` 中，不需要在 `model.xml` 中定义。

## 支持的数据库

### SQLite

**依赖：** Python 内置，无需安装

**配置示例：**
```xml
<group name="sqlite_db">
    <var name="type" value="sqlite"/>
    <var name="database" value="demo.db"/>
</group>
```

### MySQL / MariaDB

**依赖：** `pip install pymysql`

**配置示例：**
```xml
<group name="mysql_db">
    <var name="type" value="mysql"/>
    <var name="host" value="localhost"/>
    <var name="port" value="3306"/>
    <var name="user" value="root"/>
    <var name="password" value="password"/>
    <var name="database" value="test_db"/>
</group>
```

### PostgreSQL

**依赖：** `pip install psycopg2-binary`

**配置示例：**
```xml
<group name="pg_db">
    <var name="type" value="postgresql"/>
    <var name="host" value="localhost"/>
    <var name="port" value="5432"/>
    <var name="user" value="postgres"/>
    <var name="password" value="password"/>
    <var name="database" value="test_db"/>
</group>
```

**别名：** `postgres`, `pg`

### SQL Server

**依赖：** `pip install pymssql`

**配置示例：**
```xml
<group name="mssql_db">
    <var name="type" value="sqlserver"/>
    <var name="host" value="localhost"/>
    <var name="port" value="1433"/>
    <var name="user" value="sa"/>
    <var name="password" value="password"/>
    <var name="database" value="test_db"/>
</group>
```

**别名：** `mssql`

## 定义 SQL 数据表

在 `data/` 目录下创建 SQL 数据表文件（如 `QuerySQL.xml`）：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<datatable name="QuerySQL">
    <row id="Q001" remark="查询订单列表">
        <field name="sql">SELECT order_no, customer_name, total_amount FROM orders LIMIT 10</field>
        <field name="operation">query</field>
    </row>
    <row id="Q002" remark="查询单个订单">
        <field name="sql">SELECT * FROM orders WHERE order_no = 'ORD001'</field>
        <field name="operation">query</field>
    </row>
    <row id="E001" remark="插入订单">
        <field name="sql">INSERT INTO orders (order_no, customer_name) VALUES ('ORD999', '测试')</field>
        <field name="operation">execute</field>
    </row>
</datatable>
```

## 数据表字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| `sql` | 是 | SQL 语句 |
| `operation` | 否 | 操作类型：`query`（查询，默认）或 `execute`（执行） |
| `var_name` | 否 | 结果变量名，将结果保存到变量中 |

## 编写测试用例

在 `case/` 目录下的用例文件中使用 DB 关键字：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<cases>
    <case execute="是" id="TC001" title="数据库查询测试" component_type="数据库">
        <test_case>
            <test_step action="DB" model="sqlite_db" data="QuerySQL.Q001"/>
            <test_step action="DB" model="sqlite_db" data="QuerySQL.Q002"/>
        </test_case>
    </case>
</cases>
```

## 参数说明

- **action**: 固定为 `DB`
- **model**: GlobalValue 中的数据库配置组名（如 `sqlite_db`）
- **data**: 数据表引用（格式：`表名.DataID`）或直接 SQL 语句

## 使用返回值

查询结果自动保存到 `${Return[-1]}`，可在后续步骤中引用。

## 注意事项

1. **连接配置**：数据库连接信息必须在 `globalvalue.xml` 中配置
2. **路径解析**：SQLite 的 `database` 路径相对于测试项目根目录
3. **操作类型**：`query` 用于 SELECT，`execute` 用于 INSERT/UPDATE/DELETE
4. **返回值**：查询结果保存在 `${Return[-1]}`
5. **连接复用**：同一配置在测试期间会复用连接

## 完整示例

参考 `rodski-demo/DEMO/demo_full/` 目录：
- `data/globalvalue.xml`：数据库连接配置
- `data/QuerySQL.xml`：SQL 数据表
- `case/demo_case.xml`：TC006 数据库测试用例
