# Iteration 37 任务清单

**版本**: v6.3.0-beta.1  
**分支**: feature/iteration-37-selector-runtime  
**依赖**: iteration-36 完成

---

## T37-001: 扩展 `rodski run` selector 参数 [0.8h]

### 任务

1. 支持 `--tag` 与兼容别名 `--tags`。
2. 支持 `--group`。
3. 支持 `--exclude-tag` 与兼容别名 `--exclude-tags`。
4. 保留已有 `--priority` case 级过滤语义，并接入 scenario selector。
5. 帮助文案明确 selector 不读取 plan XML。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests/unit -k "run_cli or tag or group" -v
python3 rodski/cli_main.py run --help
```

---

## T37-002: 建立 scenario 有效元数据索引 [1h]

### 任务

1. 从 case XML 收集 scenario `tag`、`group`、`depends`。
2. 合并 `<cases tags="...">` 文件级 tag 与 scenario tag。
3. 支持 `--priority` 先过滤 case，再判断 scenario selector。
4. 不新增 case 级 `tag` 属性。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests/unit -k "tag_inheritance or selector_metadata" -v
```

---

## T37-003: 实现 selector 到临时 TestPlanSelection 的编译 [1.2h]

### 任务

1. `--tag smoke,p0` 按 OR 语义命中 scenario。
2. `--group negative` 按精确匹配命中 scenario。
3. `--exclude-tag slow` 从候选集中排除命中 scenario。
4. XML `<case execute="否">` 仍是硬关闭。
5. selector 编译结果只存在内存中，不写 plan XML。
6. selector 执行保持 XML 顺序。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests/unit -k "selector or temporary_plan" -v
```

---

## T37-004: 禁止 `@plan_id` 与 selector 同时使用 [1h]

### 任务

1. 检测 `@plan_id` 与 `--tag` / `--group` / `--exclude-tag` / `--priority` 同时出现。
2. 直接报错，不做合并、不做交集过滤、不做优先级推断。
3. 错误提示包含三种替代方式：
   - `rodski run @plan_id`
   - `rodski run --tag smoke`
   - `rodski plan create plan_id --from-tag smoke` 后再执行 plan
4. 覆盖 `--tags`、`--exclude-tags` 别名。
5. `--filter-tag` 不作为合法参数；如果实现了统一参数校验，必须报错说明不支持 plan 后过滤。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests/unit -k "plan_selector_conflict or mutually_exclusive" -v
```

---

## T37-005: selector dry-run preview 与验收补齐 [1h]

### 任务

1. `rodski run --tag smoke --dry-run` 输出临时选择结果。
2. dry-run 输出 case/scenario 层级与 skipped 原因。
3. 补齐 TC055-TC060、TC078 demo 或单元验收。
4. 按 `.pb/iterations/iteration-37/acceptance_tests.md` 覆盖 plan 与 selector 固定互斥场景。
5. 更新 Agent 集成文档，说明 selector 适合临时探索，不适合作为共享测试计划。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests/unit -k "dry_run or selector" -v
python3 rodski/selftest.py
```

---

## 执行顺序

```text
T37-001 (CLI 参数)
    ↓
T37-002 (元数据索引)
    ↓
T37-003 (selector 编译)
    ↓
T37-004 (互斥裁决)
    ↓
T37-005 (dry-run + 验收)
```

## 工时估算

| 任务 | 预估 |
|------|------|
| T37-001 | 0.8h |
| T37-002 | 1.0h |
| T37-003 | 1.2h |
| T37-004 | 1.0h |
| T37-005 | 1.0h |
| **合计** | **5.0h** |