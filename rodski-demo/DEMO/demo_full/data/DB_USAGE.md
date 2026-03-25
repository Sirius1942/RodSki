# DB 关键字使用说明

## 概述

DB 关键字用于执行数据库操作（查询/更新）。数据库连接信息配置在 `globalvalue.xml` 中，不需要在 `model.xml` 中定义。

## 配置方式

### 1. 在 globalvalue.xml 中配置数据库连接

```xml
<?xml version="1.0" encoding="UTF-8"?>
<globalvalue>
    <group name="demo_db">
        <var name="type" value="sqlite"/>
        <var name="database" value="rodski-demo/DEMO/demo_full/demo.db"/>
    </group>

    <group name="mysql_db">
        <var name="type" value="mysql"/>
        <var name="host" value="localhost"/>
        <var name="port" value="3306"/>
        <var name="user" value="root"/>
        <var name="password" value="password"/>
        <var name="database" value="test_db"/>
    </group>
</globalvalue>
```

### 2. 在数据表 XML 中定义 SQL

```xml
<?xml version="1.0" encoding="UTF-8"?>
<datatable name="QuerySQL">
    <row id="Q001" remark="查询订单列表">
        <field name="sql">SELECT order_no, customer_name, total_amount FROM orders LIMIT 3</field>
        <field name="operation">query</field>
    </row>
    <row id="Q002" remark="插入订单">
        <field name="sql">INSERT INTO orders (order_no, customer_name) VALUES ('ORD999', '测试')</field>
        <field name="operation">execute</field>
    </row>
</datatable>
```

### 3. 在用例中使用

```xml
<case execute="是" id="TC006" title="数据库查询" component_type="数据库">
    <test_case>
        <test_step action="DB" model="demo_db" data="QuerySQL.Q001"/>
    </test_case>
</case>
```

## 参数说明

- **model**: GlobalValue 中的数据库连接配置组名（如 `demo_db`）
- **data**: 数据表引用（如 `QuerySQL.Q001`）或直接 SQL 语句

## 数据表字段

- **sql**: SQL 语句（必填）
- **operation**: 操作类型（可选，默认 `query`）
  - `query`: 查询操作，返回结果集
  - `execute`: 执行操作（INSERT/UPDATE/DELETE），返回影响行数
- **var_name**: 结果变量名（可选），将结果保存到变量

## 返回值

查询结果自动保存到 `${Return[-1]}`，可在后续步骤中引用。
