# DB 关键字使用说明

## 概述

DB 关键字用于执行数据库操作（查询/更新）。v5+ 语法中，数据库连接配置在 `globalvalue.xml`，并由 `model.xml` 中的 `type="database"` 模型通过 `connection` 属性引用。

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

### 2. 在 model.xml 中定义数据库模型和查询模板

```xml
<model name="QuerySQL" type="database" connection="demo_db">
    <query name="list">
        <sql>SELECT order_no, customer_name, total_amount FROM orders LIMIT :limit</sql>
    </query>
    <query name="insert">
        <sql>INSERT INTO orders (order_no, customer_name) VALUES (:order_no, :customer_name)</sql>
    </query>
</model>
```

### 3. 在数据表 XML 中定义参数数据

```xml
<?xml version="1.0" encoding="UTF-8"?>
<datatable name="QuerySQL">
    <row id="Q001" remark="查询订单列表">
        <field name="query">list</field>
        <field name="limit">3</field>
    </row>
    <row id="Q002" remark="插入订单">
        <field name="query">insert</field>
        <field name="order_no">ORD999</field>
        <field name="customer_name">测试</field>
    </row>
</datatable>
```

### 4. 在用例中使用

```xml
<case execute="是" id="TC006" title="数据库查询" component_type="数据库">
    <test_case>
        <test_step action="DB" model="QuerySQL" data="Q001"/>
    </test_case>
</case>
```

## 参数说明

- **model**: 数据库模型名（`type="database"`，如 `QuerySQL`）
- **data**: 数据行 ID（如 `Q001`）

## 数据表字段（v5+）

- **query**: 查询模板名称（来自 model 中 `<query name="...">`）
- **参数字段**: 与 SQL 中 `:param` 对应（如 `limit`、`order_no`）
- **sql**: 可选，直接 SQL 模式（不推荐，仅用于临时场景）

## 返回值

查询结果自动保存到 `${Return[-1]}`，可在后续步骤中引用。
