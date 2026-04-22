# Iteration 33 任务清单

**版本**: v5.10.0  
**分支**: feature/iteration-33-init-cli  
**依赖**: iteration-32 完成

---

## T33-001: 新增 rodski init CLI 模块 [1.5h]

### 任务

1. 新建 `rodski/rodski_cli/init.py`
2. 创建标准目录：`case/`、`model/`、`fun/`、`data/`、`result/`
3. 创建模板文件：
   - `model/model.xml`
   - `data/data.xml`
   - `data/globalvalue.xml`
   - 可选 `data/data_verify.xml`
   - 可选 `data/testdata.sqlite`
4. 支持 `--with-verify`、`--with-sqlite`、`--force`

### 验证

```bash
pytest rodski/tests/unit/test_init_cli.py -v
```

---

## T33-002: SQLite 元表初始化 [0.8h]

### 任务

1. `--with-sqlite` 时初始化 `rs_datatable`、`rs_datatable_field`、`rs_row`、`rs_field`
2. 保证新创建模块可直接作为 `rodski data` / `rodski run` 的合法输入

### 验证

```bash
pytest rodski/tests/unit/test_init_cli.py -k sqlite -v
```

---

## T33-003: rodski-demo 验收补齐 [1h]

### 任务

1. 补充 XML-only / SQLite-only / coexistence / conflict 场景
2. 优先在现有 `rodski-demo/DEMO/demo_full/` 下扩展，不额外发散新 demo 根目录
3. 明确 `init_db.py` / 数据准备步骤

### 验证

```bash
# 按实际 demo 路径执行
python3 rodski/selftest.py
```

---

## T33-004: 发布前收口 [0.7h]

### 任务

1. 完成文档校对
2. 确认所有单元测试与 demo 验收通过
3. 按“feature 分支开发 → merge main → 从 main 发布 v5.10.0”收口

### 验证

```bash
pytest rodski/tests/unit -v
python3 rodski/selftest.py
```

---

## 执行顺序

```
T33-001 (init CLI)
    ↓
T33-002 (SQLite 元表初始化)
    ↓
T33-003 (demo 验收)
    ↓
T33-004 (发布前收口)
```

## 工时估算

| 任务 | 预估 |
|------|------|
| T33-001 | 1.5h |
| T33-002 | 0.8h |
| T33-003 | 1.0h |
| T33-004 | 0.7h |
| **合计** | **4h** |
