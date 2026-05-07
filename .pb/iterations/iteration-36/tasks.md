# Iteration 36 任务清单

**版本**: v6.3.0-alpha.2  
**分支**: feature/iteration-36-plan-runtime  
**依赖**: iteration-35 完成

---

## T36-001: 新增 plan.xsd 与 PlanParser [1.2h]

### 任务

1. 新增 `rodski/schemas/plan.xsd`。
2. 支持根节点 `<test_plan>`。
3. 约束 `id/title/kind/execute/default_execute`。
4. 约束 `<case>` / `<scenario>` / `<step>` 引用结构。
5. 预留 `<debug prepare="..." step_mode="..." cleanup="..."/>` schema 结构。
6. 新增 PlanParser，解析 `plan/{测试目的}_{测试类型}.xml`。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests/unit -k "plan_xsd or plan_parser" -v
```

---

## T36-002: 建立 TestPlanSelection 内存模型 [1.5h]

### 任务

1. 新增或扩展执行前选择模型，表示最终 case/scenario/step 列表。
2. 输入包含 case/scenario/step 树与显式 plan XML。
3. 输出保持 XML 顺序。
4. 为每个 skipped 项保留原因。
5. 不新增持久文件格式。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests/unit -k "test_plan_selection or selection" -v
```

---

## T36-003: 实现显式 plan 优先级与 default_execute [1.2h]

### 任务

1. 实现显式 plan 模式优先级：
   - XML case `execute="否"`
   - `test_plan.execute="否"`
   - plan case `execute="否"`
   - plan scenario `execute="否"`
   - plan step `execute="否"`
   - `test_plan.default_execute`
2. 支持 `default_execute="是"` 的 full 计划。
3. 支持 `default_execute="否"` 的 smoke/negative/debug 计划。
4. 明确只要上层为否，下层开启不生效。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests/unit -k "default_execute or plan_execute or skipped" -v
```

---

## T36-004: 接入 `rodski run @plan_id` 与默认计划解析 [1.2h]

### 任务

1. 修改 `rodski run` 参数解析，识别 `@plan_id`。
2. 映射 `@invoice_tax_point_smoke` 到 `plan/invoice_tax_point_smoke.xml`。
3. 校验 `<test_plan id>` 与文件名 stem 一致。
4. 未指定计划时优先读取 `plan/project_full.xml`。
5. 若不存在 `project_full` 但 `plan/*_full.xml` 只有一个，则使用该 full 计划。
6. 若存在多个 full 计划，提示用户显式指定 `@plan_id`。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests/unit -k "run_plan or default_plan" -v
```

---

## T36-005: 定义 stale 引用的 run 与 dry-run 行为 [0.5h]

### 任务

1. plan 引用不存在 case/scenario/step 时，实际 run 忽略该项并记录日志。
2. `rodski run @plan_id --dry-run` 输出 stale 引用提示。
3. 为后续 `rodski plan validate` 复用 stale 检查逻辑。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests/unit -k "stale or dry_run" -v
```

---

## T36-006: 核心约束与数据组织文档同步 [0.4h]

### 任务

1. 更新 `rodski/docs/CORE_DESIGN_CONSTRAINTS.md`，登记 `plan/` 是标准测试项目目录。
2. 更新 `rodski/docs/DATA_FILE_ORGANIZATION.md`，明确 plan XML 不属于测试数据。
3. 更新 `rodski/docs/TEST_CASE_WRITING_GUIDE.md` 中显式 plan 执行入口。

### 验证

```bash
grep -R "plan/" rodski/docs/CORE_DESIGN_CONSTRAINTS.md rodski/docs/DATA_FILE_ORGANIZATION.md rodski/docs/TEST_CASE_WRITING_GUIDE.md
```

---

## 执行顺序

```text
T36-001 (plan.xsd + PlanParser)
    ↓
T36-002 (TestPlanSelection)
    ↓
T36-003 (优先级 + default_execute)
    ↓
T36-004 (run @plan_id)
    ↓
T36-005 (stale + dry-run)
    ↓
T36-006 (文档同步)
```

## 工时估算

| 任务 | 预估 |
|------|------|
| T36-001 | 1.2h |
| T36-002 | 1.5h |
| T36-003 | 1.2h |
| T36-004 | 1.2h |
| T36-005 | 0.5h |
| T36-006 | 0.4h |
| **合计** | **6.0h** |