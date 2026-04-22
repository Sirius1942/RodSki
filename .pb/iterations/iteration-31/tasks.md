# Iteration 31 任务清单

**版本**: v5.9.0  
**分支**: feature/iteration-31-sqlite-runtime  
**依赖**: iteration-30 完成

---

## T31-001: 升级 DataTableParser 为统一数据 facade [1.5h]

### 任务

1. 修改 `rodski/core/data_table_parser.py`
   - 同时加载 `data.xml`、`data_verify.xml`、`testdata.sqlite`
   - 建立统一逻辑表索引
   - 保持 `parse_all_tables()`、`get()`、`get_data()` 接口不变
2. 补齐 `tables` / `merge_table()` 等兼容层，避免破坏 `SKIExecutor`
3. 明确空字符串与缺字段的区分语义

### 验证

```bash
pytest rodski/tests/unit/test_data_table_parser.py -v
```

---

## T31-002: 新增 SQLite data source [1.5h]

### 任务

1. 新建 `rodski/core/sqlite_data_source.py`
2. 读取 `rs_datatable`、`rs_datatable_field`、`rs_row`、`rs_field`
3. 输出逻辑表 schema、行数据、来源元信息
4. 不让 SQLite 细节泄漏到关键字层

### 验证

```bash
pytest rodski/tests/unit/test_sqlite_data_source.py -v
```

---

## T31-003: 新增 schema validator [1.5h]

### 任务

1. 新建 `rodski/core/data_schema_validator.py`
2. 校验跨源同名逻辑表冲突
3. 校验 SQLite schema 完整性与行字段一致性
4. 校验逻辑表命名规则、`db_query` / `db_sql` 必需字段约束
5. 为后续 CLI `validate --strict` 预留 XML 列漂移检查接口

### 验证

```bash
pytest rodski/tests/unit/test_data_schema_validator.py -v
```

---

## T31-004: 运行时接线与兼容回归 [1h]

### 任务

1. 修改 `rodski/core/ski_executor.py` 以接入统一 data manager
2. 检查 `rodski/data/data_resolver.py`、`rodski/rodski_cli/explain.py` 等调用链兼容性
3. 确保 `verify` 自动拼接 `_verify`、`DB` 数据读取语义保持不变

### 验证

```bash
pytest rodski/tests/unit/test_data_resolver.py -v
pytest rodski/tests/unit/test_ski_executor.py -v
```

---

## T31-005: 运行时回归与自检 [0.5h]

### 验证

```bash
python3 rodski/selftest.py
pytest rodski/tests/unit/test_data_table_parser.py rodski/tests/unit/test_sqlite_data_source.py rodski/tests/unit/test_data_schema_validator.py -v
```

---

## 执行顺序

```
T31-001 (统一 facade)
    ↓
T31-002 (SQLite source) ──┐
T31-003 (validator)      ├── 可并行
    ↓                    │
T31-004 (运行时接线)  ←──┘
    ↓
T31-005 (回归)
```

## 工时估算

| 任务 | 预估 |
|------|------|
| T31-001 | 1.5h |
| T31-002 | 1.5h |
| T31-003 | 1.5h |
| T31-004 | 1.0h |
| T31-005 | 0.5h |
| **合计** | **6h** |
