# RodSki 数据库使用指南

**版本**: v5.0+  
**最后更新**: 2026-04-10  
**目标读者**: 测试工程师、自动化开发者

---

## 目录

1. [快速开始](#快速开始)
2. [连接配置](#连接配置)
3. [使用方式](#使用方式)
4. [返回值处理](#返回值处理)
5. [完整示例](#完整示例)
6. [最佳实践](#最佳实践)
7. [常见问题](#常见问题)

---

## 快速开始

### 最简示例

```xml
<!-- 1. 配置数据库连接 -->
<globalvalue>
    <group name="sqlite_db">
        <var name="type" value="sqlite"/>
        <var name="database" value="demo.db"/>
    </group>
</globalvalue>

<!-- 2. 定义数据库模型 -->
<model name="OrderQuery" type="database" connection="sqlite_db">
    <element name="order_no" type="database">
        <location type="field">order_no</location>
    </element>
</model>

<!-- 3. 定义查询数据 -->
<datatable name="OrderQuery">
    <row id="Q001">
        <field name="sql">SELECT * FROM orders LIMIT 5</field>
    </row>
</datatable>

<!-- 4. 执行查询 -->
<test_step action="DB" model="OrderQuery" data="Q001"/>

<!-- 5. 验证结果 -->
<test_step action="assert" condition="${len(Return[-1])} == 5"/>
```

<!-- 待 iteration-21 完成后验证 -->

---

## 连接配置

### 支持的数据库类型

RodSki 支持以下数据库：

| 数据库 | type 值 | 默认端口 | 依赖库 |
|--------|---------|---------|--------|
| SQLite | `sqlite` | - | `sqlite3` (内置) |
| MySQL | `mysql` | 3306 | `pymysql` |
| PostgreSQL | `postgresql`, `postgres`, `pg` | 5432 | `psycopg2` |
| SQL Server | `sqlserver`, `mssql` | 1433 | `pymssql` |

### 配置示例

#### SQLite

```xml
<group name="sqlite_db">
    <var name="type" value="sqlite"/>
    <var name="database" value="demo.db"/>
</group>
```

**说明**:
- `database`: 数据库文件路径（相对于项目根目录）

#### MySQL

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

#### PostgreSQL

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

#### SQL Server

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

---

## 使用方式

RodSki 提供两种使用方式：

### 方式 1: 数据表直接写 SQL（推荐用于简单查询）

适用场景：
- 一次性查询
- 简单的 SQL 语句
- 不需要复用的查询

#### 步骤 1: 定义模型

```xml
<model name="OrderQuery" type="database" connection="sqlite_db" servicename="订单查询">
    <!-- 结果字段定义（用于 verify） -->
    <element name="order_no" type="database">
        <location type="field">order_no</location>
        <desc>订单号</desc>
    </element>
    <element name="customer_name" type="database">
        <location type="field">customer_name</location>
        <desc>客户姓名</desc>
    </element>
</model>
```

**关键点**:
- `type="database"`: 标识为数据库模型
- `connection="sqlite_db"`: 指定连接配置（GlobalValue 中的 group name）
- `<element>`: 定义结果字段，用于 verify 验证

#### 步骤 2: 定义数据表

```xml
<datatable name="OrderQuery">
    <row id="Q001" remark="查询前5条订单">
        <field name="sql"><![CDATA[
            SELECT 
                order_no,
                customer_name,
                total_amount,
                status
            FROM orders
            WHERE status = 'completed'
            ORDER BY created_at DESC
            LIMIT 5
        ]]></field>
        <field name="operation">query</field>
    </row>
    
    <row id="Q002" remark="插入新订单">
        <field name="sql"><![CDATA[
            INSERT INTO orders (order_no, customer_name, total_amount, status)
            VALUES ('ORD999', '张三', 1999.00, 'pending')
        ]]></field>
        <field name="operation">execute</field>
    </row>
</datatable>
```

**字段说明**:

| 字段 | 必填 | 说明 | 默认值 |
|------|------|------|--------|
| `sql` | 是 | SQL 语句（支持 CDATA 多行） | - |
| `operation` | 否 | 操作类型：`query`（查询）/ `execute`（执行） | `query` |

**提示**: 使用 `<![CDATA[...]]>` 包裹多行 SQL，提高可读性

#### 步骤 3: 执行查询

```xml
<test_step action="DB" model="OrderQuery" data="Q001"/>
```

---

### 方式 2: 模型定义查询模板（推荐用于复杂查询和复用）

适用场景：
- 需要复用的查询
- 复杂的多表 JOIN
- 参数化查询
- 需要维护的查询逻辑

#### 步骤 1: 定义模型（包含查询模板）

```xml
<model name="OrderQuery" type="database" connection="sqlite_db" servicename="订单查询模型">
    <!-- 查询模板定义 -->
    <query name="list" remark="查询订单列表">
        <sql><![CDATA[
            SELECT 
                order_no,
                customer_name,
                total_amount,
                status,
                created_at
            FROM orders
            WHERE status = :status
            ORDER BY created_at DESC
            LIMIT :limit
        ]]></sql>
        <params>
            <param name="status" type="string" default="completed"/>
            <param name="limit" type="int" default="10"/>
        </params>
    </query>
    
    <query name="get_by_id" remark="根据订单号查询">
        <sql>SELECT * FROM orders WHERE order_no = :order_no</sql>
        <params>
            <param name="order_no" type="string" required="true"/>
        </params>
    </query>
    
    <query name="insert" remark="插入订单">
        <sql><![CDATA[
            INSERT INTO orders (order_no, customer_name, total_amount, status)
            VALUES (:order_no, :customer_name, :total_amount, :status)
        ]]></sql>
        <params>
            <param name="order_no" type="string" required="true"/>
            <param name="customer_name" type="string" required="true"/>
            <param name="total_amount" type="decimal" required="true"/>
            <param name="status" type="string" default="pending"/>
        </params>
    </query>
    
    <!-- 结果字段定义（用于 verify） -->
    <element name="order_no" type="database">
        <location type="field">order_no</location>
        <desc>订单号</desc>
    </element>
    <element name="customer_name" type="database">
        <location type="field">customer_name</location>
        <desc>客户姓名</desc>
    </element>
</model>
```

**关键点**:
- `<query name="...">`: 定义查询模板，name 是模板名称
- `:param`: 参数占位符，使用冒号前缀
- `<params>`: 参数定义，支持类型、默认值、必填校验

#### 步骤 2: 数据表引用模板

```xml
<datatable name="OrderQuery">
    <row id="Q001" remark="查询已完成订单">
        <field name="query">list</field>
        <field name="status">completed</field>
        <field name="limit">5</field>
    </row>
    
    <row id="Q002" remark="查询待处理订单">
        <field name="query">list</field>
        <field name="status">pending</field>
        <field name="limit">10</field>
    </row>
    
    <row id="Q003" remark="查询指定订单">
        <field name="query">get_by_id</field>
        <field name="order_no">ORD001</field>
    </row>
    
    <row id="Q004" remark="插入新订单">
        <field name="query">insert</field>
        <field name="order_no">ORD999</field>
        <field name="customer_name">李四</field>
        <field name="total_amount">2999.00</field>
        <field name="status">pending</field>
    </row>
</datatable>
```

**字段说明**:

| 字段 | 必填 | 说明 |
|------|------|------|
| `query` | 是 | 模型中定义的查询名称 |
| 其他字段 | 否 | 查询参数（对应模板中的 `:param`） |

#### 步骤 3: 执行查询

```xml
<test_step action="DB" model="OrderQuery" data="Q001"/>
```

---

## 返回值处理

### 自动保存机制

所有 DB 查询结果自动保存到 `${Return[-1]}`，无需手动指定变量名。

### 返回值格式

| 操作类型 | 返回格式 | 示例 |
|---------|---------|------|
| query（查询） | `[{row1}, {row2}, ...]` | `[{"order_no": "ORD001", "total": 999}]` |
| execute（插入/更新/删除） | `{"affected_rows": N}` | `{"affected_rows": 1}` |

### 使用返回值

```xml
<!-- 查询订单 -->
<test_step action="DB" model="OrderQuery" data="Q001"/>

<!-- 验证第一条记录 -->
<test_step action="assert" condition="${Return[-1][0].order_no} == 'ORD001'"/>

<!-- 验证记录数量 -->
<test_step action="assert" condition="${len(Return[-1])} == 3"/>

<!-- 遍历结果 -->
<test_step action="evaluate" code="
    for order in Return[-1]:
        print(f'订单号: {order['order_no']}, 金额: {order['total_amount']}')
"/>
```

### 大数据量处理

**默认限制**: 查询结果最多返回 **1000 行**

**超出处理**:
- 自动截断到 1000 行
- 输出警告日志：`WARNING: 查询结果超过 1000 行，已截断`
- 返回值中添加标记：`{"_truncated": true, "_total_rows": 5000}`

**推荐做法**:

```xml
<!-- ✅ 推荐：使用 LIMIT 控制返回量 -->
<field name="sql"><![CDATA[
    SELECT * FROM orders 
    WHERE status = 'completed'
    LIMIT 100
]]></field>

<!-- ⚠️ 警告：可能返回大量数据 -->
<field name="sql">SELECT * FROM orders</field>
<!-- 如果表中有 5000 行，只返回前 1000 行 -->
```

**检测截断**:

```xml
<test_step action="DB" model="OrderQuery" data="Q001"/>
<test_step action="assert" condition="${Return[-1].get('_truncated', False)} == False"/>
<test_step action="evaluate" code="
    if Return[-1].get('_truncated'):
        print(f'警告：结果被截断，实际行数: {Return[-1]['_total_rows']}')
"/>
```

---

## 完整示例

### 场景：订单管理测试

#### 1. GlobalValue 配置

```xml
<globalvalue>
    <group name="sqlite_db">
        <var name="type" value="sqlite"/>
        <var name="database" value="demo.db"/>
    </group>
</globalvalue>
```

#### 2. 模型定义

```xml
<model name="OrderQuery" type="database" connection="sqlite_db" servicename="订单查询">
    <query name="list">
        <sql><![CDATA[
            SELECT order_no, customer_name, total_amount, status
            FROM orders
            WHERE status = :status
            LIMIT :limit
        ]]></sql>
        <params>
            <param name="status" type="string" default="completed"/>
            <param name="limit" type="int" default="10"/>
        </params>
    </query>
    
    <query name="insert">
        <sql><![CDATA[
            INSERT INTO orders (order_no, customer_name, total_amount, status)
            VALUES (:order_no, :customer_name, :total_amount, :status)
        ]]></sql>
    </query>
    
    <element name="order_no" type="database">
        <location type="field">order_no</location>
    </element>
    <element name="customer_name" type="database">
        <location type="field">customer_name</location>
    </element>
</model>
```

#### 3. 数据表定义

```xml
<datatable name="OrderQuery">
    <row id="Q001" remark="查询已完成订单">
        <field name="query">list</field>
        <field name="status">completed</field>
        <field name="limit">5</field>
    </row>
    
    <row id="Q002" remark="插入测试订单">
        <field name="query">insert</field>
        <field name="order_no">TEST001</field>
        <field name="customer_name">测试用户</field>
        <field name="total_amount">999.00</field>
        <field name="status">pending</field>
    </row>
    
    <row id="Q003" remark="查询刚插入的订单">
        <field name="sql">SELECT * FROM orders WHERE order_no = 'TEST001'</field>
    </row>
</datatable>

<datatable name="OrderQuery_verify">
    <row id="V001" remark="验证查询结果不为空">
        <field name="order_no">${Return[-1][0].order_no}</field>
    </row>
    
    <row id="V002" remark="验证插入的订单">
        <field name="order_no">TEST001</field>
        <field name="customer_name">测试用户</field>
        <field name="total_amount">999.00</field>
    </row>
</datatable>
```

#### 4. 测试用例

```xml
<case execute="是" id="TC025" title="订单查询和插入" description="测试订单的查询和插入功能">
    <test_case>
        <!-- 查询现有订单 -->
        <test_step action="DB" model="OrderQuery" data="Q001"/>
        <test_step action="verify" model="OrderQuery" data="V001"/>
        
        <!-- 插入新订单 -->
        <test_step action="DB" model="OrderQuery" data="Q002"/>
        
        <!-- 验证插入结果 -->
        <test_step action="DB" model="OrderQuery" data="Q003"/>
        <test_step action="verify" model="OrderQuery" data="V002"/>
    </test_case>
</case>
```

<!-- 待 iteration-21 完成后验证 -->

---

## 最佳实践

### 1. SQL 必须定义在模型或数据表中

**❌ 错误示例**：测试用例中直接写 SQL

```xml
<!-- 禁止这样做 -->
<test_step action="DB" connection="sqlite_db">
    SELECT * FROM orders LIMIT 3
</test_step>
```

**✅ 正确示例**：SQL 在数据表或模型中定义

```xml
<test_step action="DB" model="OrderQuery" data="Q001"/>
```

### 2. 推荐使用模型定义查询模板

**适用场景**：
- 需要复用的查询
- 复杂的多表 JOIN
- 参数化查询

**优势**：
- 查询逻辑集中管理
- 数据表只需提供参数
- 易于维护和修改

### 3. 使用 CDATA 提高 SQL 可读性

```xml
<field name="sql"><![CDATA[
    SELECT 
        o.order_no,
        o.customer_name,
        s.status_name
    FROM orders o
    LEFT JOIN order_status s ON o.status = s.status_code
    WHERE o.created_at >= '2024-01-01'
    ORDER BY o.created_at DESC
    LIMIT 10
]]></field>
```

### 4. 添加 remark 说明查询意图

```xml
<row id="Q001" remark="查询2024年已完成和已发货的订单，按创建时间倒序">
    <field name="sql">...</field>
</row>
```

### 5. 使用参数化查询防止 SQL 注入

**❌ 错误示例**：直接拼接字符串

```xml
<field name="sql">SELECT * FROM orders WHERE status = 'completed'</field>
```

**✅ 正确示例**：使用参数占位符

```xml
<sql>SELECT * FROM orders WHERE status = :status</sql>
<params>
    <param name="status" type="string"/>
</params>
```

### 6. 控制查询返回量

```xml
<!-- 推荐：使用 LIMIT 控制 -->
<sql>SELECT * FROM orders WHERE status = :status LIMIT :limit</sql>

<!-- 避免：可能返回大量数据 -->
<sql>SELECT * FROM orders</sql>
```

---

## 常见问题

### Q1: 如何切换数据库环境（开发/测试/生产）？

**方案 1**: 使用不同的 GlobalValue 配置文件

```bash
# 开发环境
python rodski/main.py --globalvalue config/dev_globalvalue.xml

# 测试环境
python rodski/main.py --globalvalue config/test_globalvalue.xml
```

**方案 2**: 在模型中使用变量

```xml
<model name="OrderQuery" type="database" connection="${env.DB_CONNECTION}">
    ...
</model>
```

### Q2: 如何处理查询结果为空的情况？

```xml
<test_step action="DB" model="OrderQuery" data="Q001"/>
<test_step action="assert" condition="${len(Return[-1])} > 0" 
           message="查询结果为空"/>
```

### Q3: 如何验证插入/更新/删除操作是否成功？

```xml
<!-- 执行插入 -->
<test_step action="DB" model="OrderQuery" data="Q001"/>

<!-- 验证影响行数 -->
<test_step action="assert" condition="${Return[-1].affected_rows} == 1"/>

<!-- 查询验证数据是否插入 -->
<test_step action="DB" model="OrderQuery" data="Q002"/>
<test_step action="assert" condition="${Return[-1][0].order_no} == 'TEST001'"/>
```

### Q4: 如何处理事务？

RodSki 默认每个 SQL 语句自动提交。如需事务控制，建议：

1. 在数据库层面使用存储过程
2. 使用 `evaluate` 关键字编写 Python 代码控制事务

```xml
<test_step action="evaluate" code="
    conn = executor._get_db_connection('sqlite_db')
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO orders ...')
        cursor.execute('UPDATE inventory ...')
        conn.commit()
    except:
        conn.rollback()
        raise
"/>
```

### Q5: 如何调试 SQL 执行错误？

1. 查看日志输出（SQL 语句和参数会打印到日志）
2. 使用数据库客户端工具单独测试 SQL
3. 检查参数类型是否匹配
4. 确认连接配置是否正确

---

## 相关文档

- [SKILL_REFERENCE.md](./SKILL_REFERENCE.md) - DB 关键字语法参考
- [DB_DRIVER_SUPPORT.md](./DB_DRIVER_SUPPORT.md) - 数据库驱动支持列表
- [API_REFERENCE.md](./API_REFERENCE.md) - API 参考文档

---

**文档版本**: v5.0  
**最后更新**: 2026-04-10
