# DB 关键字设计方案 v2.0

**版本**: v2.0  
**日期**: 2026-04-10  
**状态**: 草案 - 待讨论

---

## 背景

当前 DB 关键字存在以下问题：
1. **语义混乱**：`model` 参数指向数据库连接配置，与其他关键字的 `model` 语义不一致
2. **数据表结构繁琐**：简单查询也需要完整的数据表定义
3. **模型定义冗余**：为了 verify 必须定义 `type="interface"` 的模型
4. **SQL 可读性差**：不支持多行格式，复杂查询难以阅读
5. **缺少文档**：SKILL_REFERENCE.md 中没有说明

---

## 设计目标

1. **model 参数语义调整**：指向数据模型（描述数据库表结构和查询意图）
2. **model内增加 connection 参数**：明确指定数据库连接配置
3. **提升 SQL 可读性**：支持多行格式、查询模板、参数化查询
4. **保持连接配置不变**：继续使用 GlobalValue 存储连接信息

---

## ⚠️ 重大变更说明

### 不兼容旧版本

**本次重构是破坏性更新，不向后兼容旧语法。**

**旧语法（v4.x 及以前）**：
```xml
<test_step action="DB" model="sqlite_db" data="QuerySQL.Q001"/>
```

**新语法（v5.0+）**：
```xml
<test_step action="DB" model="OrderQuery" data="Q001"/>
```

**影响范围**：
- 所有使用 DB 关键字的测试用例必须修改
- 所有数据库相关的模型必须重新定义为 `type="database"`
- 数据表中的 `sql` 字段需要改为 `query` 字段（如果使用模板模式）

**迁移要求**：
- 升级到 v5.0 前，必须完成所有测试用例的迁移
- 旧代码将在 v5.0 中完全移除，不提供兼容模式

**迁移时间表**：
- v5.0.0 (iteration-20): 移除旧代码，实现新语法
- v5.1.0 (iteration-21): rodski-demo 完成迁移
- v5.2.0 (iteration-22): 文档更新完成

---

## 关键性约束 ⚠️

### 约束 1：SQL 必须定义在模型或数据表中

**禁止**：测试用例中直接出现 SQL 语句

```xml
<!-- ❌ 错误示例：测试用例中直接写 SQL -->
<test_step action="DB" connection="sqlite_db">
    SELECT * FROM orders LIMIT 3
</test_step>

<!-- ❌ 错误示例：test_step 中包含 sql 属性 -->
<test_step action="DB" 
           connection="sqlite_db"
           sql="SELECT * FROM orders LIMIT 3"/>
```

**强制**：SQL 必须定义在模型或数据表中

```xml
<!-- ✅ 正确示例：SQL 在数据表中定义 -->
<test_step action="DB" connection="sqlite_db" model="OrderQuery" data="Q001"/>

<!-- 数据表定义 -->
<datatable name="OrderQuery">
    <row id="Q001">
        <field name="sql">SELECT * FROM orders LIMIT 3</field>
    </row>
</datatable>
```

```xml
<!-- ✅ 正确示例：SQL 在模型中定义（推荐） -->
<test_step action="DB" connection="sqlite_db" model="OrderQuery" data="Q001"/>

<!-- 模型定义 -->
<model name="OrderQuery" type="database">
    <query name="list">
        <sql>SELECT * FROM orders LIMIT :limit</sql>
    </query>
</model>

<!-- 数据表只提供参数 -->
<datatable name="OrderQuery">
    <row id="Q001">
        <field name="query">list</field>
        <field name="limit">3</field>
    </row>
</datatable>
```

### 约束 2：推荐使用模型定义查询模板

对于需要复用的 SQL，强烈推荐使用模型定义查询模板：

- **简单查询**（一次性使用）：可以在数据表中直接写 SQL
- **复杂查询**（多表 JOIN、复杂逻辑）：必须在模型中定义
- **需要复用的查询**：必须在模型中定义

### 约束 3：参数化查询必须使用 :param 语法

```xml
<!-- ✅ 正确：使用 :param 占位符 -->
<sql>SELECT * FROM orders WHERE status = :status LIMIT :limit</sql>

<!-- ❌ 错误：直接拼接字符串 -->
<sql>SELECT * FROM orders WHERE status = 'completed' LIMIT 10</sql>
```

### 约束 4：查询结果自动保存到 Return

所有 DB 查询的结果会自动保存到 `${Return[-1]}`，无需手动指定 `var_name`。

**查询结果格式**：
- **query 操作**：返回列表 `[{row1}, {row2}, ...]`
- **execute 操作**：返回 `{"affected_rows": N}`

**大数据量处理策略**：
1. **默认限制**：查询结果默认最多返回 1000 行
2. **超出限制**：自动截断并输出警告日志
3. **分页查询**：建议在 SQL 中使用 LIMIT 控制返回行数
4. **流式处理**：超大数据量场景不适合用 DB 关键字，应使用专门的数据处理脚本

```xml
<!-- ✅ 推荐：使用 LIMIT 控制返回量 -->
<sql>SELECT * FROM orders WHERE status = :status LIMIT 100</sql>

<!-- ⚠️ 警告：可能返回大量数据 -->
<sql>SELECT * FROM orders</sql>  <!-- 如果超过 1000 行会被截断 -->
```

---

## 核心改进

### 改进 1：连接配置移到模型定义

**旧方案**：测试用例中指定 `connection` 参数
```xml
<test_step action="DB" connection="sqlite_db" model="OrderQuery" data="Q001"/>
```

**新方案**：连接配置在模型中定义
```xml
<!-- 测试用例 -->
<test_step action="DB" model="OrderQuery" data="Q001"/>

<!-- 模型定义 -->
<model name="OrderQuery" type="database" connection="sqlite_db">
    ...
</model>
```

**优势**：
- 测试用例更简洁
- 连接配置集中管理
- 同一模型的所有查询使用相同连接
- 便于切换环境（只需修改模型的 connection 属性）

---

### 改进 2：查询结果自动保存到 Return

**自动保存机制**：
- 所有 DB 查询结果自动保存到 `${Return[-1]}`
- 无需在数据表中指定 `var_name` 字段
- 支持链式引用：`${Return[-1][0].order_no}`

**返回值格式**：

| 操作类型 | 返回格式 | 示例 |
|---------|---------|------|
| query（查询） | `[{row1}, {row2}, ...]` | `[{"order_no": "ORD001", "total": 999}]` |
| execute（插入/更新/删除） | `{"affected_rows": N}` | `{"affected_rows": 1}` |

**大数据量处理策略**：

1. **默认限制**：查询结果最多返回 **1000 行**
2. **超出处理**：
   - 自动截断到 1000 行
   - 输出警告日志：`WARNING: 查询结果超过 1000 行，已截断`
   - 返回值中添加标记：`{"_truncated": true, "_total_rows": 5000}`
3. **推荐做法**：
   - 在 SQL 中使用 `LIMIT` 控制返回量
   - 使用分页查询（`LIMIT` + `OFFSET`）
   - 大数据量场景使用专门的数据处理脚本

**示例**：

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

**大数据量示例**：

```xml
<!-- ✅ 推荐：使用 LIMIT 控制 -->
<datatable name="OrderQuery">
    <row id="Q001">
        <field name="sql"><![CDATA[
            SELECT * FROM orders 
            WHERE status = 'completed'
            LIMIT 100
        ]]></field>
    </row>
</datatable>

<!-- ⚠️ 警告：可能返回大量数据 -->
<datatable name="OrderQuery">
    <row id="Q002">
        <field name="sql">SELECT * FROM orders</field>
        <!-- 如果表中有 5000 行，只返回前 1000 行 -->
    </row>
</datatable>

<!-- 验证是否被截断 -->
<test_step action="DB" model="OrderQuery" data="Q002"/>
<test_step action="assert" condition="${Return[-1]._truncated} == true"/>
<test_step action="evaluate" code="
    if Return[-1].get('_truncated'):
        print(f'警告：结果被截断，实际行数: {Return[-1]['_total_rows']}')
"/>
```

---

### 改进 3：参数调整

#### 旧语法
```xml
<test_step action="DB" model="sqlite_db" data="QuerySQL.Q001"/>
```

#### 新语法
```xml
<test_step action="DB" model="OrderQuery" data="Q001"/>
```

**关键改进**：
1. **去掉 connection 参数**：连接配置移到模型定义中
2. **简化用例语法**：测试用例只需指定 model 和 data

#### 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| action | 固定值 `DB` | `DB` |
| model | 数据模型名称（定义查询结构、连接配置） | `OrderQuery` |
| data | 数据行 ID（引用数据表中的具体查询） | `Q001` |

---

## 使用方式

### 方式 1：数据表直接写 SQL（推荐用于简单查询）

#### 测试用例
```xml
<test_step action="DB" model="OrderQuery" data="Q001"/>
<test_step action="verify" model="OrderQuery" data="V001"/>
```

#### 模型定义（包含连接配置）
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

**说明**：
- `connection="sqlite_db"` 指定数据库连接（GlobalValue 中的 group name）
- 测试用例中不再需要指定 connection，由模型统一管理

#### 数据表定义
```xml
<datatable name="OrderQuery">
    <row id="Q001" remark="查询前3条订单">
        <field name="sql"><![CDATA[
            SELECT 
                order_no,
                customer_name,
                total_amount,
                status
            FROM orders
            WHERE status = 'completed'
            ORDER BY created_at DESC
            LIMIT 3
        ]]></field>
        <field name="operation">query</field>
        <field name="var_name">order_list</field>
    </row>
    
    <row id="Q002" remark="插入新订单">
        <field name="sql"><![CDATA[
            INSERT INTO orders (order_no, customer_name, total_amount, status)
            VALUES ('ORD999', '张三', 1999.00, 'pending')
        ]]></field>
        <field name="operation">execute</field>
    </row>
    
    <row id="Q003" remark="更新订单状态">
        <field name="sql">UPDATE orders SET status = 'completed' WHERE order_no = 'ORD999'</field>
        <field name="operation">execute</field>
    </row>
</datatable>
```

#### 数据表字段说明

| 字段 | 必填 | 说明 | 示例 |
|------|------|------|------|
| sql | 是 | SQL 语句（支持 CDATA 多行） | `SELECT * FROM orders` |
| operation | 否 | 操作类型：`query`（查询）/ `execute`（执行），默认 `query` | `query` |
| var_name | 否 | 结果保存到变量名 | `order_list` |

#### 验证数据表
```xml
<datatable name="OrderQuery_verify">
    <row id="V001" remark="验证查询结果">
        <field name="order_no">${Return[-1][0].order_no}</field>
        <field name="customer_name">${Return[-1][0].customer_name}</field>
    </row>
</datatable>
```

---

### 方式 2：模型定义查询模板（推荐用于复杂查询和复用）

#### 模型定义
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
    <element name="total_amount" type="database">
        <location type="field">total_amount</location>
        <desc>订单金额</desc>
    </element>
    <element name="status" type="database">
        <location type="field">status</location>
        <desc>订单状态</desc>
    </element>
</model>
```

#### 数据表引用模板
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

#### 数据表字段说明（模板模式）

| 字段 | 必填 | 说明 | 示例 |
|------|------|------|------|
| query | 是 | 模型中定义的查询名称 | `list` |
| 其他字段 | 否 | 查询参数（对应模板中的 :param） | `status`, `limit` |

---

### 连接配置（GlobalValue）

```xml
<globalvalue>
    <!-- SQLite 连接 -->
    <group name="sqlite_db">
        <var name="type" value="sqlite"/>
        <var name="database" value="demo.db"/>
    </group>
    
    <!-- MySQL 连接 -->
    <group name="mysql_db">
        <var name="type" value="mysql"/>
        <var name="host" value="localhost"/>
        <var name="port" value="3306"/>
        <var name="user" value="root"/>
        <var name="password" value="password"/>
        <var name="database" value="test_db"/>
    </group>
    
    <!-- PostgreSQL 连接 -->
    <group name="pg_db">
        <var name="type" value="postgresql"/>
        <var name="host" value="localhost"/>
        <var name="port" value="5432"/>
        <var name="user" value="postgres"/>
        <var name="password" value="password"/>
        <var name="database" value="test_db"/>
    </group>
</globalvalue>
```

---

## SQL 可读性提升方案

### 1. 使用 CDATA 支持多行格式
```xml
<field name="sql"><![CDATA[
    SELECT 
        o.order_no,
        o.customer_name,
        o.total_amount,
        s.status_name
    FROM orders o
    LEFT JOIN order_status s ON o.status = s.status_code
    WHERE o.created_at >= '2024-01-01'
      AND o.status IN ('completed', 'shipped')
    ORDER BY o.created_at DESC
    LIMIT 10
]]></field>
```

### 2. 添加 remark 说明查询意图
```xml
<row id="Q001" remark="查询2024年已完成和已发货的订单，按创建时间倒序">
    <field name="sql">...</field>
</row>
```

### 3. 模型中定义查询模板（复用 + 参数化）
```xml
<query name="list_by_status" remark="按状态查询订单">
    <sql><![CDATA[
        SELECT * FROM orders 
        WHERE status = :status 
        ORDER BY created_at DESC 
        LIMIT :limit
    ]]></sql>
    <params>
        <param name="status" type="string" default="completed"/>
        <param name="limit" type="int" default="10"/>
    </params>
</query>
```

### 4. 自动生成 .md 文档
框架自动为每个数据表生成说明文档：

**model/OrderQuery.md**
```markdown
# OrderQuery

## 用途
订单查询相关的数据库操作

## 涉及表
- orders: 订单主表（order_no, customer_name, total_amount, status, created_at）
- order_status: 订单状态表（status_code, status_name）

## SQL 说明

| DataID | 用途 | 操作类型 |
|--------|------|----------|
| Q001 | 查询2024年已完成和已发货的订单 | query |
| Q002 | 插入新订单 | execute |
| Q003 | 更新订单状态 | execute |
```

---

## 完整示例

### 场景：订单管理测试

#### 1. 测试用例
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

#### 2. 模型定义
```xml
<model name="OrderQuery" type="database" connection="sqlite_db" servicename="订单查询">
    <element name="order_no" type="database">
        <location type="field">order_no</location>
    </element>
    <element name="customer_name" type="database">
        <location type="field">customer_name</location>
    </element>
    <element name="total_amount" type="database">
        <location type="field">total_amount</location>
    </element>
</model>
```

#### 3. 数据表
```xml
<datatable name="OrderQuery">
    <row id="Q001" remark="查询已完成订单">
        <field name="sql"><![CDATA[
            SELECT order_no, customer_name, total_amount
            FROM orders
            WHERE status = 'completed'
            LIMIT 5
        ]]></field>
        <field name="operation">query</field>
    </row>
    
    <row id="Q002" remark="插入测试订单">
        <field name="sql"><![CDATA[
            INSERT INTO orders (order_no, customer_name, total_amount, status)
            VALUES ('TEST001', '测试用户', 999.00, 'pending')
        ]]></field>
        <field name="operation">execute</field>
    </row>
    
    <row id="Q003" remark="查询刚插入的订单">
        <field name="sql">SELECT * FROM orders WHERE order_no = 'TEST001'</field>
        <field name="operation">query</field>
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

---

## 迁移指南

### ⚠️ 不兼容变更

**本次重构不提供向后兼容，旧语法将完全失效。**

### 旧语法（v4.x，已废弃）
```xml
<test_step action="DB" model="sqlite_db" data="QuerySQL.Q001"/>

<!-- 旧模型定义 -->
<model name="QuerySQL" type="interface">
    <element name="sql" type="interface">
        <location type="field">sql</location>
    </element>
</model>

<!-- 旧数据表 -->
<datatable name="QuerySQL">
    <row id="Q001">
        <field name="sql">SELECT * FROM orders LIMIT 3</field>
        <field name="operation">query</field>
    </row>
</datatable>
```

### 新语法（v5.0+，强制使用）
```xml
<test_step action="DB" model="OrderQuery" data="Q001"/>

<!-- 新模型定义 -->
<model name="OrderQuery" type="database" connection="sqlite_db">
    <query name="list">
        <sql>SELECT * FROM orders LIMIT :limit</sql>
    </query>
    
    <element name="order_no" type="database">
        <location type="field">order_no</location>
    </element>
</model>

<!-- 新数据表 -->
<datatable name="OrderQuery">
    <row id="Q001">
        <field name="query">list</field>
        <field name="limit">3</field>
    </row>
</datatable>
```

### 变化点
1. **测试用例**：`model` 参数从连接名改为模型名
2. **模型定义**：从 `type="interface"` 改为 `type="database"`，新增 `connection` 属性
3. **模型内容**：新增 `<query>` 标签定义 SQL 模板
4. **数据表**：从 `sql` 字段改为 `query` 字段 + 参数字段
5. **data 格式**：从 `TableName.DataID` 简化为 `DataID`

### 迁移步骤

#### 步骤 1: 备份旧文件
```bash
mkdir -p archive/v4.x
cp model/model.xml archive/v4.x/
cp case/tc_database.xml archive/v4.x/
cp data/data.xml archive/v4.x/
```

#### 步骤 2: 创建新模型
- 创建 `model/model_db.xml`
- 定义 `type="database"` 模型
- 添加 `connection` 属性
- 定义 `<query>` 模板

#### 步骤 3: 修改测试用例
- 将 `model="sqlite_db"` 改为 `model="OrderQuery"`
- 将 `data="QuerySQL.Q001"` 改为 `data="Q001"`

#### 步骤 4: 修改数据表
- 将 `<field name="sql">` 改为 `<field name="query">`
- 添加参数字段（如 `<field name="limit">3</field>`）
- 移除 `operation` 字段（自动判断）

#### 步骤 5: 测试验证
- 运行所有数据库测试用例
- 确认全部通过
- 删除旧文件

### 不兼容处理

**v5.0 将完全移除旧代码**：
- 移除 `_resolve_db_sql` 中的旧逻辑
- 移除 `data="TableName.DataID"` 解析
- 移除 `type="interface"` 的数据库模型支持
- 旧语法将直接报错，不提供降级处理

---

## 优势总结

1. **语义清晰**：model 指向数据模型，连接配置在模型中定义
2. **用例简洁**：测试用例只需 `action="DB" model="..." data="..."`
3. **可读性强**：支持多行 SQL、查询模板、参数化
4. **易于维护**：模型定义查询模板，数据表只传参数
5. **向后兼容**：保持 GlobalValue 连接配置不变
6. **自动保存**：查询结果自动保存到 Return，无需手动指定
7. **安全可控**：大数据量自动截断，避免内存溢出
8. **灵活性高**：支持直接写 SQL 和模板两种模式

---

## 实施计划

### 迭代 20-22：DB 关键字重构

**总工时**: 约 12-15 小时  
**版本**: v5.0.0 - v5.2.0  
**优先级**: P0

#### Iteration 20: 核心引擎重构 (v5.0.0)

**工时**: 5-6h

| 任务 | 内容 | 预计 | 文件 |
|------|------|------|------|
| T20-001 | 修改 keyword_engine.py 支持 connection 参数 | 2h | `rodski/core/keyword_engine.py` |
| T20-002 | 支持模型中的 query 定义解析 | 2h | `rodski/core/model_parser.py` |
| T20-003 | 支持参数化查询（:param 替换） | 1h | `rodski/core/keyword_engine.py` |
| T20-004 | 向后兼容旧语法 | 0.5h | `rodski/core/keyword_engine.py` |
| T20-005 | 单元测试 | 0.5h | `tests/` |

**验收标准**:
- 支持新语法 `action="DB" connection="..." model="..." data="..."`
- 支持旧语法向后兼容
- 支持模型中的 `<query>` 定义
- 支持参数化查询 `:param` 替换
- 单元测试通过

#### Iteration 21: rodski-demo 迁移 (v5.1.0)

**工时**: 4-5h

| 任务 | 内容 | 预计 | 文件 |
|------|------|------|------|
| T21-001 | 创建 OrderQuery 模型（database 类型） | 1h | `rodski-demo/model/model_db.xml` |
| T21-002 | 迁移 tc_database.xml 到新语法 | 1.5h | `rodski-demo/case/tc_database.xml` |
| T21-003 | 更新数据表（移除 sql 字段，改为 query + 参数） | 1h | `rodski-demo/data/data.xml` |
| T21-004 | 回归测试 | 1h | 运行所有数据库测试用例 |

**验收标准**:
- TC020-TC024 全部通过
- 使用新语法 `connection="sqlite_db" model="OrderQuery"`
- SQL 定义在模型中，数据表只有参数
- 旧的 tc_database.xml 备份到 archive/

#### Iteration 22: 文档更新 (v5.2.0)

**工时**: 3-4h

| 任务 | 内容 | 预计 | 文件 |
|------|------|------|------|
| T22-001 | 更新 SKILL_REFERENCE.md 添加 DB 关键字说明 | 1.5h | `rodski/docs/SKILL_REFERENCE.md` |
| T22-002 | 更新 DB_DRIVER_SUPPORT.md | 0.5h | `rodski/docs/DB_DRIVER_SUPPORT.md` |
| T22-003 | 创建 DB_USAGE_GUIDE.md 用户使用指南 | 1.5h | `rodski/docs/DB_USAGE_GUIDE.md` |
| T22-004 | 更新 API_REFERENCE.md | 0.5h | `rodski/docs/API_REFERENCE.md` |

**验收标准**:
- SKILL_REFERENCE.md 包含完整的 DB 关键字说明
- DB_USAGE_GUIDE.md 包含详细的使用示例
- 文档中的示例代码可以直接运行
- 所有文档更新日期正确

---

## 迁移检查清单

### 代码修改
- [ ] keyword_engine.py 支持 connection 参数
- [ ] keyword_engine.py 支持模型 query 定义
- [ ] keyword_engine.py 支持参数化查询
- [ ] model_parser.py 支持 type="database" 模型
- [ ] model_parser.py 支持 `<query>` 标签解析
- [ ] 向后兼容旧语法

### 测试用例迁移
- [ ] rodski-demo/case/tc_database.xml 迁移到新语法
- [ ] rodski-demo/model/model_db.xml 创建数据库模型
- [ ] rodski-demo/data/data.xml 更新数据表
- [ ] TC020-TC024 全部测试通过

### 文档更新
- [ ] SKILL_REFERENCE.md 添加 DB 关键字
- [ ] DB_DRIVER_SUPPORT.md 更新说明
- [ ] DB_USAGE_GUIDE.md 创建使用指南
- [ ] API_REFERENCE.md 更新 API 说明

---

**文档版本**: v2.0  
**状态**: 已批准 - 待实施  
**最后更新**: 2026-04-10
