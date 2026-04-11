# Iteration 20: DB 关键字核心引擎重构

**版本**: v5.0.0  
**分支**: release/v5.0.0  
**日期**: 2026-04-10  
**工时**: 6h  
**优先级**: P0  
**前置依赖**: iteration-19

---

## ⚠️ 重大变更

**本次重构是破坏性更新，不向后兼容旧语法。**

- **移除旧代码**：完全删除旧的 DB 关键字实现
- **不提供兼容模式**：旧语法将直接报错
- **强制迁移**：所有使用 DB 关键字的测试用例必须修改

---

## 需求

### 业务需求

**问题**：
1. 当前 DB 关键字语义混乱，`model` 参数指向连接配置而非数据模型
2. SQL 可读性差，不支持多行格式和参数化查询
3. 查询结果需要手动指定变量名，使用不便
4. 缺少大数据量保护机制

**目标**：
1. 统一 `model` 参数语义，指向数据模型
2. 连接配置移到模型定义中（`connection` 属性）
3. 支持查询模板和参数化查询（`:param` 语法）
4. 查询结果自动保存到 `${Return[-1]}`
5. 大数据量自动截断（1000 行限制）

### 技术需求

**新语法**：
```xml
<!-- 测试用例 -->
<test_step action="DB" model="OrderQuery" data="Q001"/>

<!-- 模型定义 -->
<model name="OrderQuery" type="database" connection="sqlite_db">
    <query name="list">
        <sql>SELECT * FROM orders WHERE status = :status LIMIT :limit</sql>
    </query>
</model>

<!-- 数据表 -->
<datatable name="OrderQuery">
    <row id="Q001">
        <field name="query">list</field>
        <field name="status">completed</field>
        <field name="limit">10</field>
    </row>
</datatable>
```

**核心功能**：
1. 支持 `type="database"` 模型解析
2. 从模型读取 `connection` 属性
3. 从模型读取 `<query>` 定义
4. 支持 `:param` 占位符替换
5. 查询结果自动保存到 Return
6. 超过 1000 行自动截断并警告

---

## 设计

### 架构设计

**组件关系**：
```
KeywordEngine._kw_db()
    ↓
ModelParser.get_model() → 读取模型定义
    ↓
获取 connection 属性 → 连接数据库
    ↓
DataManager.get_data() → 读取数据表
    ↓
从模型读取 <query> 定义 → 获取 SQL 模板
    ↓
替换 :param 占位符 → 生成最终 SQL
    ↓
执行 SQL → 获取结果
    ↓
截断处理（>1000行） → 添加 _truncated 标记
    ↓
store_return() → 保存到 ${Return[-1]}
```

### 数据流设计

**输入**：
- `params`: `{"model": "OrderQuery", "data": "Q001"}`

**处理流程**：
1. 从 ModelParser 读取模型 → `{"type": "database", "connection": "sqlite_db", "queries": {...}}`
2. 从 DataManager 读取数据 → `{"query": "list", "status": "completed", "limit": 10}`
3. 从模型读取 SQL → `"SELECT * FROM orders WHERE status = :status LIMIT :limit"`
4. 替换参数 → `"SELECT * FROM orders WHERE status = 'completed' LIMIT 10"`
5. 执行 SQL → `[{"order_no": "ORD001", ...}, ...]`
6. 检查行数 → 如果 > 1000，截断并添加标记
7. 保存结果 → `self.store_return(result)`

**输出**：
- 查询成功：`[{row1}, {row2}, ...]` 保存到 `${Return[-1]}`
- 执行成功：`{"affected_rows": N}` 保存到 `${Return[-1]}`
- 超过 1000 行：`{"_truncated": true, "_total_rows": N, "data": [前1000行]}`

### 接口设计

**ModelParser 新增方法**：
```python
def get_database_model(self, model_name: str) -> Dict:
    """获取 database 类型模型
    
    Returns:
        {
            "type": "database",
            "connection": "sqlite_db",
            "queries": {
                "list": {
                    "sql": "SELECT ...",
                    "remark": "查询列表"
                }
            },
            "elements": {...}
        }
    """
```

**KeywordEngine 新增方法**：
```python
def _replace_sql_params(self, sql: str, params: Dict[str, Any]) -> str:
    """替换 SQL 中的 :param 占位符
    
    Args:
        sql: SQL 语句
        params: 参数字典
        
    Returns:
        替换后的 SQL
    """

def _truncate_result(self, result: List[Dict], limit: int = 1000) -> Dict:
    """截断查询结果
    
    Args:
        result: 查询结果列表
        limit: 最大行数
        
    Returns:
        截断后的结果（包含 _truncated 标记）
    """
```

---

## 开发任务

### T20-001: 完全重写 _kw_db 方法（移除旧代码）

**预计**: 2.5h  
**文件**: `rodski/core/keyword_engine.py`

**任务**:
1. 删除旧的 `_kw_db` 方法
2. 删除 `_resolve_db_sql` 方法
3. 删除 `_ensure_sql_doc` 方法
4. 重写 `_kw_db` 方法：
   - 从 model_parser 读取模型
   - 验证模型类型为 `database`
   - 获取 `connection` 属性
   - 从数据表读取 `query` 和参数
   - 从模型读取 SQL 模板
   - 替换参数
   - 执行 SQL
   - 处理结果（截断、保存）

**验收**:
- [ ] 旧代码完全删除
- [ ] 新方法实现完整
- [ ] 支持新语法
- [ ] 旧语法直接报错

---

### T20-002: 支持模型中的 query 定义解析

**预计**: 1.5h  
**文件**: `rodski/core/model_parser.py`

**任务**:
1. 在 ModelParser 中添加 `parse_database_model` 方法
2. 解析 `<query>` 标签：
   - 读取 `name` 属性
   - 读取 `remark` 属性
   - 读取 `<sql>` 内容（支持 CDATA）
3. 解析 `connection` 属性
4. 返回结构化数据

**验收**:
- [ ] 可以解析 `type="database"` 模型
- [ ] 可以读取 `<query>` 定义
- [ ] 可以读取 `connection` 属性
- [ ] 单元测试通过

---

### T20-003: 支持参数化查询（:param 替换）

**预计**: 1h  
**文件**: `rodski/core/keyword_engine.py`

**任务**:
1. 实现 `_replace_sql_params` 方法
2. 使用正则表达式匹配 `:param`
3. 根据参数类型添加引号：
   - 字符串：添加单引号
   - 数字：不添加引号
   - None：转为 NULL
4. 缺少参数时抛出异常

**验收**:
- [ ] 可以正确替换 `:param`
- [ ] 字符串自动加引号
- [ ] 数字不加引号
- [ ] 缺少参数时报错
- [ ] 单元测试通过

---

### T20-004: 实现大数据量截断机制

**预计**: 0.5h  
**文件**: `rodski/core/keyword_engine.py`

**任务**:
1. 实现 `_truncate_result` 方法
2. 检查结果行数
3. 如果超过 1000 行：
   - 截断到 1000 行
   - 添加 `_truncated: true` 标记
   - 添加 `_total_rows: N` 记录总行数
   - 输出警告日志

**验收**:
- [ ] 超过 1000 行自动截断
- [ ] 添加 `_truncated` 标记
- [ ] 输出警告日志
- [ ] 单元测试通过

---

### T20-005: 清理旧代码和旧测试用例

**预计**: 0.5h  
**文件**: `rodski/core/keyword_engine.py`, `tests/`

**任务**:
1. 删除旧方法的所有引用
2. 删除旧的单元测试
3. 添加旧语法检测：
   - 检测 `data` 中是否包含 `.`
   - 如果包含，直接报错并提示迁移
4. 更新错误信息，指向迁移文档

**验收**:
- [ ] 旧代码完全删除
- [ ] 旧测试完全删除
- [ ] 旧语法直接报错
- [ ] 错误信息清晰

---

## 测试任务

### T20-T001: 单元测试 - 新语法

**预计**: 0.5h  
**文件**: `tests/test_keyword_engine_db.py`

**测试用例**:
1. `test_db_new_syntax_query` - 测试查询操作
2. `test_db_new_syntax_execute` - 测试执行操作
3. `test_db_model_not_found` - 测试模型不存在
4. `test_db_model_wrong_type` - 测试模型类型错误
5. `test_db_missing_connection` - 测试缺少 connection 属性

**验收**:
- [ ] 所有测试通过
- [ ] 覆盖率 > 80%

---

### T20-T002: 单元测试 - 参数化查询

**预计**: 0.3h  
**文件**: `tests/test_keyword_engine_db.py`

**测试用例**:
1. `test_replace_params_string` - 测试字符串参数
2. `test_replace_params_number` - 测试数字参数
3. `test_replace_params_missing` - 测试缺少参数
4. `test_replace_params_multiple` - 测试多个参数

**验收**:
- [ ] 所有测试通过

---

### T20-T003: 单元测试 - 大数据量截断

**预计**: 0.2h  
**文件**: `tests/test_keyword_engine_db.py`

**测试用例**:
1. `test_truncate_under_limit` - 测试小于 1000 行
2. `test_truncate_over_limit` - 测试超过 1000 行
3. `test_truncate_exactly_limit` - 测试正好 1000 行

**验收**:
- [ ] 所有测试通过

---

### T20-T004: 集成测试 - 旧语法报错

**预计**: 0.2h  
**文件**: `tests/test_keyword_engine_db.py`

**测试用例**:
1. `test_old_syntax_error` - 测试旧语法直接报错
2. `test_old_syntax_error_message` - 测试错误信息包含迁移提示

**验收**:
- [ ] 旧语法直接报错
- [ ] 错误信息清晰

---

## 验收标准

### 功能验收
- [ ] 支持新语法 `model="..." data="..."`
- [ ] 模型中的 `connection` 属性正确读取
- [ ] 支持模型中的 `<query>` 定义
- [ ] 支持参数化查询 `:param` 替换
- [ ] 查询结果自动保存到 `${Return[-1]}`
- [ ] 超过 1000 行自动截断并警告
- [ ] 缺少参数时抛出清晰的异常

### 测试验收
- [ ] 所有单元测试通过
- [ ] 测试覆盖率 > 80%
- [ ] 旧的 tc_database.xml 运行失败并提示迁移
- [ ] 错误信息清晰指向迁移文档

### 代码清理验收
- [ ] 旧的 `_resolve_db_sql` 方法已删除
- [ ] 旧的 `_ensure_sql_doc` 方法已删除
- [ ] 旧的单元测试已删除
- [ ] 代码中没有旧语法的注释或示例

### 代码质量
- [ ] 代码符合 PEP 8 规范
- [ ] 添加完整的 docstring
- [ ] 日志输出清晰
- [ ] 异常信息友好

---

## 工作流程

1. 确认 iteration-19 已完成
2. 创建分支: `git checkout -b release/v5.0.0`
3. 执行开发任务 T20-001 ~ T20-005
4. 执行测试任务 T20-T001 ~ T20-T004
5. 运行所有单元测试
6. 更新 record.md
7. 合并到 main: `git merge release/v5.0.0`
8. 打标签: `git tag v5.0.0`

---

## 交付物

1. 重写的 `rodski/core/keyword_engine.py`
2. 更新的 `rodski/core/model_parser.py`
3. 新增的单元测试文件
4. 迭代记录文档 `record.md`

---

## 风险与注意事项

### 风险
1. **参数替换可能导致 SQL 注入** - 需要做好参数转义
2. **破坏性更新影响现有用例** - 需要提前通知并提供迁移指南
3. **模型解析可能影响性能** - 需要缓存解析结果
4. **大数据量截断可能丢失数据** - 需要明确警告用户

### 注意事项
1. **必须删除旧代码**，不保留任何向后兼容逻辑
2. 确保所有异常都有清晰的错误信息，并指向迁移文档
3. 日志输出要包含足够的调试信息
4. 旧语法必须直接报错，不能静默失败

---

## 参考文档

- `.pb/specs/db_keyword_design_v2.md` - DB 关键字设计方案
- `rodski/docs/CORE_DESIGN_CONSTRAINTS.md` - 核心设计约束
- `rodski/docs/DB_DRIVER_SUPPORT.md` - 数据库驱动支持
