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

### 3. 在 data.sqlite 中定义参数数据

使用 `rodski data import` 从 XML 迁移，或直接通过 SQL 写入 `data.sqlite` 的 EAV 元表。

示例（QuerySQL 表，行 Q001）：
```sql
INSERT INTO rs_datatable VALUES ('QuerySQL','QuerySQL','data','standard','',CURRENT_TIMESTAMP);
INSERT INTO rs_datatable_field VALUES ('QuerySQL','limit',0),('QuerySQL','query',1);
INSERT INTO rs_row VALUES ('QuerySQL','Q001','查询订单列表');
INSERT INTO rs_field VALUES ('QuerySQL','Q001','query','list'),('QuerySQL','Q001','limit','3');
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

## SQLite 测试数据文件（data.sqlite）

`data/data.sqlite` 是唯一测试数据文件（v6.0.0 起，`data.xml` / `data_verify.xml` 已废弃）。逻辑表名必须与模型名强一致。

当前 demo 中包含的 SQLite 示例表：

| 表名 | 行数 | 说明 |
|------|------|------|
| `RegisterAPI` | 2 | 注册接口测试数据（L001/L002） |
| `RegisterAPIResult_verify` | 2 | 注册接口验证数据（V001/V002） |

对应验收用例：`case/tc030_sqlite_data.xml`

- `send RegisterAPI L001/L002` 直接从 `data/data.sqlite` 取数
- `verify RegisterAPIResult V001/V002` 从 `data.sqlite` 中的 `RegisterAPIResult_verify` 表校验响应

**查看数据：**

```bash
rodski data list rodski-demo/DEMO/demo_full/
rodski data schema rodski-demo/DEMO/demo_full/ RegisterAPI
rodski data show rodski-demo/DEMO/demo_full/ RegisterAPI L001
rodski data validate rodski-demo/DEMO/demo_full/
```

**使用约束：**
- Case 中 `data` 只写 DataID（如 `L001`），不写 `表名.DataID`
- `type` / `send` / `DB` 默认按模型名查找同名逻辑表
- `verify` 默认查找 `{模型名}_verify`
- 同一 `data/` 目录下的所有测试数据统一保存在 `data.sqlite`

**元表结构：** `rs_datatable` / `rs_datatable_field` / `rs_row` / `rs_field`
