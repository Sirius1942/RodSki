# RodSki 数据库驱动支持

**版本**: v5.0+  
**最后更新**: 2026-04-10

---

## 快速开始

RodSki 通过 DB 关键字支持多种数据库操作。使用步骤：

1. 在 GlobalValue 中配置数据库连接
2. 创建 `type="database"` 的模型，指定 `connection` 属性
3. 在测试用例中使用 `action="DB"` 执行查询

详细使用指南请参考：[DB_USAGE_GUIDE.md](./DB_USAGE_GUIDE.md)

---

## 当前支持的数据库

RodSki 通过 `keyword_engine.py` 中的 `_create_connection` 方法支持以下数据库：

### 1. SQLite ✅

**配置示例：**
```xml
<group name="sqlite_db">
    <var name="type" value="sqlite"/>
    <var name="database" value="demo.db"/>
</group>
```

**依赖库：** `sqlite3`（Python 内置）

**特性：**
- 文件路径自动解析（相对于项目根目录）
- 使用 `Row` 工厂返回字典格式结果

---

### 2. MySQL / MariaDB ✅

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

**依赖库：** `pymysql`

**安装：** `pip install pymysql`

**特性：**
- 使用 `DictCursor` 返回字典格式结果
- 默认字符集 `utf8mb4`
- 默认端口 3306

---

### 3. PostgreSQL ✅

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

**依赖库：** `psycopg2`

**安装：** `pip install psycopg2-binary`

**别名：** `postgres`, `pg`

**默认端口：** 5432

---

### 4. SQL Server ✅

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

**依赖库：** `pymssql`

**安装：** `pip install pymssql`

**别名：** `mssql`

**默认端口：** 1433

---

## 连接管理

### 连接复用
- 同一个连接配置在测试执行期间会复用连接
- 连接存储在 `_db_connections` 字典中
- 每次使用前会执行 `SELECT 1` 检测连接是否存活

### 连接关闭
- 测试执行完成后自动关闭所有数据库连接
- 在 `SKIExecutor.close()` 方法中统一清理

---

## 待支持的数据库

以下数据库可在后续版本中添加支持：

### Oracle
**依赖库：** `cx_Oracle` 或 `oracledb`

### MongoDB
**依赖库：** `pymongo`

### Redis
**依赖库：** `redis`

### Cassandra
**依赖库：** `cassandra-driver`

---

## 扩展新数据库支持

在 `keyword_engine.py` 的 `_create_connection` 方法中添加新的数据库类型：

```python
elif db_type == 'oracle':
    import cx_Oracle
    return cx_Oracle.connect(
        user=username,
        password=password,
        dsn=f"{host}:{port_int or 1521}/{database}"
    )
```

---

## 使用示例

### 基本用法

```xml
<!-- 1. GlobalValue 配置连接 -->
<globalvalue>
    <group name="sqlite_db">
        <var name="type" value="sqlite"/>
        <var name="database" value="demo.db"/>
    </group>
</globalvalue>

<!-- 2. 模型定义 -->
<model name="OrderQuery" type="database" connection="sqlite_db">
    <query name="list">
        <sql>SELECT * FROM orders LIMIT :limit</sql>
    </query>
</model>

<!-- 3. 测试用例 -->
<test_step action="DB" model="OrderQuery" data="Q001"/>

<!-- 4. 数据表 -->
<datatable name="OrderQuery">
    <row id="Q001">
        <field name="query">list</field>
        <field name="limit">10</field>
    </row>
</datatable>
```

<!-- 待 iteration-21 完成后验证 -->

---

## 代码位置

- **连接创建：** `rodski/core/keyword_engine.py` → `_create_connection()`
- **连接获取：** `rodski/core/keyword_engine.py` → `_get_db_connection()`
- **SQL执行：** `rodski/core/keyword_engine.py` → `_execute_db_sql()`
- **DB关键字：** `rodski/core/keyword_engine.py` → `_kw_db()`

---

## 相关文档

- [DB_USAGE_GUIDE.md](./DB_USAGE_GUIDE.md) - 数据库使用指南
- [SKILL_REFERENCE.md](./SKILL_REFERENCE.md) - DB 关键字语法参考
