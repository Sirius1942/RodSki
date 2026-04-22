# Iteration 32 任务清单

**版本**: v5.10.0  
**分支**: feature/iteration-32-data-cli  
**依赖**: iteration-31 完成

---

## T32-001: 新增 rodski data CLI 模块 [1.5h]

### 任务

1. 新建 `rodski/rodski_cli/data.py`
2. 实现子命令：
   - `list`
   - `schema`
   - `show`
   - `query`
   - `validate`
3. 直接复用统一 data facade / validator

### 验证

```bash
pytest rodski/tests/unit/test_data_cli.py -v
```

---

## T32-002: CLI 注册点同步 [0.5h]

### 任务

1. 修改 `rodski/cli_main.py`
2. 修改 `rodski/rodski_cli/__init__.py`
3. 确保两个入口都能识别 `data` 子命令

### 验证

```bash
python -m rodski.cli_main data --help
python -c "from rodski.rodski_cli import main; import sys; sys.argv=['rodski','data','--help']; main()"
```

---

## T32-003: validate 严格模式与输出优化 [1h]

### 任务

1. `validate` 输出统一 OK/FAIL 语义
2. `--strict` 增加 XML 列漂移检查
3. 使错误信息能明确指出逻辑表、数据源、缺失/多余字段

### 验证

```bash
pytest rodski/tests/unit/test_data_cli.py -k validate -v
```

---

## T32-004: data CLI 回归 [1h]

### 验证

```bash
rodski data list rodski-demo/
rodski data schema rodski-demo/ Login
rodski data show rodski-demo/ Login L001
rodski data query rodski-demo/ Login --limit 20
rodski data validate rodski-demo/
rodski data validate rodski-demo/ --strict
```

---

## 执行顺序

```
T32-001 (data CLI)
    ↓
T32-002 (CLI 注册)
    ↓
T32-003 (strict validate)
    ↓
T32-004 (CLI 回归)
```

## 工时估算

| 任务 | 预估 |
|------|------|
| T32-001 | 1.5h |
| T32-002 | 0.5h |
| T32-003 | 1.0h |
| T32-004 | 1.0h |
| **合计** | **4h** |
