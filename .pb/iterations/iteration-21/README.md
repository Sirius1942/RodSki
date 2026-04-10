# Iteration 21: rodski-demo 迁移到新 DB 语法

**版本**: v5.1.0  
**分支**: release/v5.1.0  
**日期**: 2026-04-10  
**工时**: 5h  
**优先级**: P0  
**前置依赖**: iteration-20

---

## ⚠️ 重大变更

**本迭代是强制迁移，旧语法已在 v5.0 中移除。**

- rodski-demo 中的所有 DB 测试用例必须修改
- 旧的模型定义必须删除
- 旧的数据表必须重写

---

## 需求

### 业务需求

**问题**：
1. rodski-demo 项目使用旧的 DB 语法
2. 模型定义为 `type="interface"`，不符合新规范
3. 数据表中直接写 SQL，不利于复用
4. 测试用例使用 `model="sqlite_db"` 指向连接配置

**目标**：
1. 将所有 DB 测试用例迁移到新语法
2. 创建 `type="database"` 模型
3. 使用查询模板实现 SQL 复用
4. 验证所有测试用例通过

### 技术需求

**迁移范围**：
- `rodski-demo/case/tc_database.xml` - 5个测试用例（TC020-TC024）
- `rodski-demo/model/model_e.xml` - 删除旧的 QuerySQL/QueryMySQL 模型
- `rodski-demo/DEMO/demo_full/data/data.xml` - 重写 QuerySQL/QueryMySQL 数据表

**新文件**：
- `rodski-demo/model/model_db.xml` - 新的数据库模型定义

---

## 设计

### 模型设计

**QuerySQL 模型**（SQLite）：
```xml
<model name="QuerySQL" type="database" connection="sqlite_db">
    <query name="list">
        <sql>SELECT order_no, customer_name, total_amount FROM orders LIMIT :limit</sql>
    </query>
    <query name="insert">
        <sql>INSERT INTO orders (order_no, customer_name, total_amount, status) 
             VALUES (:order_no, :customer_name, :total_amount, :status)</sql>
    </query>
    <query name="get_by_id">
        <sql>SELECT * FROM orders WHERE order_no = :order_no</sql>
    </query>
    <query name="count">
        <sql>SELECT COUNT(*) as total FROM orders</sql>
    </query>
</model>
```

**QueryMySQL 模型**（MySQL）：
```xml
<model name="QueryMySQL" type="database" connection="mysql_db">
    <query name="list">
        <sql>SELECT order_no, customer_name, total_amount FROM orders LIMIT :limit</sql>
    </query>
    <query name="insert">
        <sql>INSERT INTO orders (order_no, customer_name, total_amount, status) 
             VALUES (:order_no, :customer_name, :total_amount, :status)</sql>
    </query>
    <query name="get_by_id">
        <sql>SELECT * FROM orders WHERE order_no = :order_no</sql>
    </query>
</model>
```

### 数据表设计

**旧数据表**（直接写 SQL）：
```xml
<row id="Q001">
    <field name="sql">SELECT order_no, customer_name, total_amount FROM orders LIMIT 3</field>
    <field name="operation">query</field>
</row>
```

**新数据表**（引用查询模板）：
```xml
<row id="Q001">
    <field name="query">list</field>
    <field name="limit">3</field>
</row>
```

### 测试用例设计

**旧语法**：
```xml
<test_step action="DB" model="sqlite_db" data="QuerySQL.Q001"/>
```

**新语法**：
```xml
<test_step action="DB" model="QuerySQL" data="Q001"/>
```

---

## 开发任务

### T21-001: 创建 model_db.xml（database 类型模型）

**预计**: 1.5h  
**文件**: `rodski-demo/model/model_db.xml`

**任务**:
1. 创建新文件 `model_db.xml`
2. 定义 QuerySQL 模型：
   - 设置 `type="database"`
   - 设置 `connection="sqlite_db"`
   - 定义 4 个查询模板：list, insert, get_by_id, count
   - 定义结果字段：order_no, customer_name, total_amount, total
3. 定义 QueryMySQL 模型：
   - 设置 `type="database"`
   - 设置 `connection="mysql_db"`
   - 定义 3 个查询模板：list, insert, get_by_id
   - 定义结果字段：order_no, customer_name, total_amount

**验收**:
- [ ] model_db.xml 创建成功
- [ ] 包含 QuerySQL 和 QueryMySQL 两个模型
- [ ] 每个模型定义 connection 属性
- [ ] 查询模板使用 `:param` 占位符
- [ ] XML 格式正确

---

### T21-002: 迁移 tc_database.xml 到新语法

**预计**: 1h  
**文件**: `rodski-demo/case/tc_database.xml`

**任务**:
1. 备份旧文件到 `archive/v4.x/tc_database.xml`
2. 修改所有 DB 测试步骤：
   - TC020: `model="sqlite_db"` → `model="QuerySQL"`
   - TC021: `model="sqlite_db"` → `model="QuerySQL"`
   - TC022: `model="sqlite_db"` → `model="QuerySQL"`
   - TC023: `model="mysql_db"` → `model="QueryMySQL"`
   - TC024: `model="mysql_db"` → `model="QueryMySQL"`
3. 修改 data 格式：
   - `data="QuerySQL.Q001"` → `data="Q001"`
   - `data="QuerySQL.Q002"` → `data="Q002"`
   - 等等

**验收**:
- [ ] 旧文件已备份
- [ ] 所有 `action="DB"` 使用新语法
- [ ] `model` 参数指向数据库模型
- [ ] `data` 格式为 `DataID`（不含表名）
- [ ] XML 格式正确

---

### T21-003: 更新数据表（使用查询模板）

**预计**: 1.5h  
**文件**: `rodski-demo/DEMO/demo_full/data/data.xml`

**任务**:
1. 备份旧的 QuerySQL 数据表定义
2. 重写 QuerySQL 数据表：
   - Q001: 使用 `query="list"`, `limit=3`
   - Q002: 使用 `query="insert"`, 提供订单参数
   - Q003: 使用 `query="get_by_id"`, `order_no=TEST001`
   - Q004: 使用 `query="count"`
3. 重写 QueryMySQL 数据表：
   - Q001: 使用 `query="list"`, `limit=3`
   - Q002: 使用 `query="insert"`, 提供订单参数
   - Q003: 使用 `query="get_by_id"`, `order_no=MYSQL_TEST001`
4. 更新验证数据表：
   - 使用 `${Return[-1][0].field}` 访问结果

**验收**:
- [ ] 数据表使用 `query` 字段引用模板
- [ ] 移除 `sql` 和 `operation` 字段
- [ ] 参数字段与模板中的 `:param` 对应
- [ ] 验证数据表使用 `${Return[-1]}` 引用
- [ ] XML 格式正确

---

### T21-004: 清理旧文件

**预计**: 0.5h  
**文件**: `rodski-demo/model/model_e.xml`

**任务**:
1. 从 `model_e.xml` 中删除旧的 QuerySQL/QueryMySQL 模型定义
2. 或者直接删除 `model_e.xml`（如果只包含数据库模型）
3. 验证没有旧语法残留：
   ```bash
   grep -r 'action="DB" model="sqlite_db"' case/
   grep -r 'data="QuerySQL\.' case/
   ```

**验收**:
- [ ] 旧的模型定义已删除
- [ ] 代码库中没有旧语法残留
- [ ] 旧文件已备份到 archive/v4.x

---

## 测试任务

### T21-T001: 回归测试 - SQLite 测试用例

**预计**: 0.3h  
**测试用例**: TC020, TC021, TC022

**测试步骤**:
1. 运行 TC020（查询订单）
   ```bash
   cd rodski-demo
   python -m rodski.cli run case/tc_database.xml --case TC020
   ```
2. 运行 TC021（插入并验证）
   ```bash
   python -m rodski.cli run case/tc_database.xml --case TC021
   ```
3. 运行 TC022（聚合查询）
   ```bash
   python -m rodski.cli run case/tc_database.xml --case TC022
   ```

**验收**:
- [ ] TC020 通过
- [ ] TC021 通过
- [ ] TC022 通过
- [ ] 查询结果保存到 `${Return[-1]}`
- [ ] 验证步骤正确

---

### T21-T002: 功能测试 - 查询模板复用

**预计**: 0.2h  

**测试内容**:
1. 验证同一个查询模板可以被多个数据行复用
2. 验证参数替换正确
3. 验证不同参数产生不同结果

**验收**:
- [ ] 查询模板正确复用
- [ ] 参数替换正确
- [ ] 结果符合预期

---

### T21-T003: 功能测试 - Return 自动保存

**预计**: 0.2h  

**测试内容**:
1. 验证查询结果自动保存到 `${Return[-1]}`
2. 验证可以通过 `${Return[-1][0].field}` 访问字段
3. 验证 verify 步骤可以正确验证

**验收**:
- [ ] 结果自动保存
- [ ] 可以访问字段
- [ ] verify 步骤通过

---

### T21-T004: 日志检查

**预计**: 0.1h  

**检查内容**:
1. 确认使用新语法
2. 确认连接配置从模型读取
3. 确认参数替换正确
4. 没有旧语法的警告或错误

**验收**:
- [ ] 日志输出清晰
- [ ] 没有错误或警告
- [ ] 显示正确的 SQL 语句

---

## 验收标准

### 功能验收
- [ ] 创建 model_db.xml 包含数据库模型
- [ ] tc_database.xml 迁移到新语法
- [ ] 数据表使用查询模板
- [ ] TC020-TC022 全部通过
- [ ] 查询结果自动保存到 Return

### 文件验收
- [ ] `rodski-demo/model/model_db.xml` 创建
- [ ] `rodski-demo/case/tc_database.xml` 更新
- [ ] `rodski-demo/DEMO/demo_full/data/data.xml` 更新
- [ ] 旧文件备份到 `archive/v4.x/`
- [ ] 旧的模型定义已删除

### 测试验收
- [ ] 所有数据库测试用例通过
- [ ] 验证步骤正确
- [ ] 日志输出清晰
- [ ] 没有旧语法残留

### 代码质量
- [ ] XML 格式正确
- [ ] 查询模板清晰易读
- [ ] 参数命名规范
- [ ] 注释完整

---

## 工作流程

1. 确认 iteration-20 已完成
2. 创建分支: `git checkout -b release/v5.1.0`
3. 执行开发任务 T21-001 ~ T21-004
4. 执行测试任务 T21-T001 ~ T21-T004
5. 运行所有数据库测试用例
6. 更新 record.md
7. 合并到 main: `git merge release/v5.1.0`
8. 打标签: `git tag v5.1.0`

---

## 交付物

1. 新增的 `model_db.xml`
2. 更新的 `tc_database.xml`
3. 更新的 `data.xml`
4. 备份的旧文件（archive/v4.x/）
5. 测试报告
6. 迭代记录文档 `record.md`

---

## 风险与注意事项

### 风险
1. **数据表字段名变化** - 从 `sql` 改为 `query`，需要全部修改
2. **参数名不匹配** - 数据表参数必须与模板中的 `:param` 一致
3. **验证步骤失败** - Return 格式变化可能影响验证
4. **测试数据库不存在** - demo.db 必须存在且有数据

### 注意事项
1. 备份旧文件到 `archive/v4.x/` 目录
2. 逐个测试用例验证，不要批量修改
3. 确保 demo.db 数据库存在且有数据
4. 参数名必须与 SQL 中的 `:param` 完全一致

---

## 参考文档

- `.pb/specs/db_keyword_design_v2.md` - DB 关键字设计方案
- `.pb/iterations/iteration-20/README.md` - 核心引擎重构
- `rodski/docs/DB_DRIVER_SUPPORT.md` - 数据库驱动支持
- `rodski/docs/TEST_CASE_WRITING_GUIDE.md` - 用例编写指南
