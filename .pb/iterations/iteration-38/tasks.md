# Iteration 38 任务清单

**版本**: v6.3.0-beta.2  
**分支**: feature/iteration-38-plan-cli  
**依赖**: iteration-37 完成

---

## T38-001: 新增 `rodski plan init/list/show` [1h]

### 任务

1. 新建或扩展 `rodski/rodski_cli/plan.py`。
2. `plan init` 创建 `plan/project_full.xml` 或指定 plan。
3. 支持 `--kind`、`--default-execute`、`--force`。
4. `plan list` 列出 `plan/*.xml`。
5. `plan show plan_id` 输出单个 plan 定义。
6. 同步 CLI 注册入口。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests/unit -k "plan_cli and (init or list or show)" -v
python3 rodski/cli_main.py plan --help
```

---

## T38-002: 实现 `plan validate/preview` [1.2h]

### 任务

1. `plan validate` 校验全部 `plan/*.xml`。
2. `plan validate plan_id` 校验指定计划。
3. 校验 `<test_plan id>` 与文件名 stem 一致。
4. 校验引用的 case/scenario/step 是否存在。
5. `plan preview plan_id` 复用 TestPlanSelection 输出最终执行范围。
6. 输出 stale 引用、skipped 原因和 default_execute 影响。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests/unit -k "plan_validate or plan_preview" -v
```

---

## T38-003: 实现 `plan create/add-case/add-scenario` [1.2h]

### 任务

1. `plan create plan_id --kind suite --default-execute 否 --title ...` 创建常规测试计划。
2. `plan add-case plan_id case_id` 添加 case。
3. `plan add-scenario plan_id case_id scenario_id` 添加 scenario。
4. 写入前保持 XML 格式稳定，便于 Git diff。
5. 避免重复添加同一 case/scenario。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests/unit -k "plan_create or add_case or add_scenario" -v
```

---

## T38-004: 实现 `plan enable/disable` [0.8h]

### 任务

1. `plan disable-case plan_id case_id` 设置 case `execute="否"`。
2. `plan disable-scenario plan_id case_id scenario_id` 设置 scenario `execute="否"`。
3. `plan enable-case` 与 `plan enable-scenario` 设置 `execute="是"`。
4. 不修改 case XML。
5. 不复制 case/scenario title/group/tag 到 plan XML。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests/unit -k "enable_case or disable_case or enable_scenario or disable_scenario" -v
```

---

## T38-005: 支持 `plan create --from-tag/--from-group` [1.2h]

### 任务

1. `plan create plan_id --from-tag smoke` 复用 selector 编译结果生成 plan XML。
2. `plan create plan_id --from-group negative` 复用 group selector 生成 plan XML。
3. 生成计划后进入显式 plan 模式，可执行 `rodski run @plan_id`。
4. 生成 plan 时不复制 scenario title/group/tag。
5. 当 selector 命中为空时给出明确提示。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests/unit -k "from_tag or from_group" -v
```

---

## T38-006: CLI 文档、Agent 指南与验收补齐 [0.6h]

### 任务

1. 更新 `rodski/docs/API_REFERENCE.md` 中 `rodski plan` 命令。
2. 更新 `rodski/docs/AGENT_INTEGRATION.md`，说明 Agent 生成与维护 plan XML 的推荐入口。
3. 补齐 TC045、TC047-TC048、TC061-TC068。
4. 确认 `plan/` 不进入 `data/` 目录说明。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests/unit -k "plan_cli" -v
python3 rodski/selftest.py
```

---

## 执行顺序

```text
T38-001 (init/list/show)
    ↓
T38-002 (validate/preview)
    ↓
T38-003 (create/add)
    ↓
T38-004 (enable/disable)
    ↓
T38-005 (from-tag/from-group)
    ↓
T38-006 (文档与验收)
```

## 工时估算

| 任务 | 预估 |
|------|------|
| T38-001 | 1.0h |
| T38-002 | 1.2h |
| T38-003 | 1.2h |
| T38-004 | 0.8h |
| T38-005 | 1.2h |
| T38-006 | 0.6h |
| **合计** | **6.0h** |