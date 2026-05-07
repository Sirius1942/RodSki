# Iteration 39 任务清单

**版本**: v6.3.0  
**分支**: feature/iteration-39-plan-debug-release  
**依赖**: iteration-38 完成

---

## T39-001: 实现 `plan debug-scenario/debug-step` [1h]

### 任务

1. `plan debug-scenario plan_id --case case_id --scenario scenario_id` 创建 `kind="scenario_debug"` 计划。
2. 支持 `--prepare auto|case|none`。
3. 支持 `--cleanup 是|否`。
4. `plan debug-step plan_id --case case_id --scenario scenario_id --step N` 创建 `kind="step_debug"` 计划。
5. 支持 `--step-mode all|from|only`。
6. 生成的 plan 通过 `plan.xsd` 与 `plan validate`。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests/unit -k "debug_scenario or debug_step" -v
```

---

## T39-002: 支持 `kind="scenario_debug"` 执行 [1h]

### 任务

1. `rodski run @plan_id --debug` 识别 `scenario_debug`。
2. 要求 plan 至少包含一个 case/scenario 选择。
3. 默认执行被选中的完整 scenario。
4. 根据 `prepare` 决定是否执行 `pre_process`。
5. 根据 `cleanup` 决定是否执行 `post_process`。
6. 不修改任何测试项目输入文件。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests/unit -k "scenario_debug" -v
```

---

## T39-003: 支持 `kind="step_debug"` 执行 [1.5h]

### 任务

1. `rodski run @plan_id --debug` 识别 `step_debug`。
2. 定位 case/scenario/step。
3. `prepare=auto` 执行 `pre_process` 与当前 scenario 中目标 step 前置步骤。
4. `prepare=case` 只执行 `pre_process`。
5. `prepare=none` 不执行前置。
6. `step_mode=all` 执行整个 scenario。
7. `step_mode=from` 从指定 step 执行到 scenario 结束。
8. `step_mode=only` 只执行指定 step。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests/unit -k "step_debug or step_mode or prepare" -v
```

---

## T39-004: cleanup 与现场保留语义收口 [0.8h]

### 任务

1. `cleanup="是"` 时执行 `post_process`。
2. `cleanup="否"` 时保留现场，不执行 `post_process`。
3. 调试失败时仍输出明确错误与报告条目。
4. 与录制、截图、结果路径等现有执行生命周期兼容。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests/unit -k "cleanup or post_process or debug" -v
```

---

## T39-005: 报告层级与 skipped 原因 [1h]

### 任务

1. 报告输出 Project → TestPlan → Case → Scenario 层级。
2. Summary 区分 passed/failed/skipped scenario。
3. skipped 原因能指向来源：
   - XML case 硬关闭
   - test_plan 关闭
   - plan case/scenario/step 关闭
   - depends 未满足
   - stale 引用
4. 保持 JSON/HTML/文本报告的一致语义。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests/unit -k "report or skipped" -v
```

---

## T39-006: v6.3.0 文档、demo 与发布前回归 [0.7h]

### 任务

1. 补齐 TC069-TC077 验收用例。
2. 更新 `rodski/docs/API_REFERENCE.md`、`TEST_CASE_WRITING_GUIDE.md`、`AGENT_INTEGRATION.md`。
3. 确认 v6.3.0 不包含阶段 6 backlog。
4. 运行完整单元测试与 rodski-demo 验收。
5. 整理 release record。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests/unit -q
python3 rodski/selftest.py
```

---

## 执行顺序

```text
T39-001 (debug plan CLI)
    ↓
T39-002 (scenario_debug)
    ↓
T39-003 (step_debug)
    ↓
T39-004 (cleanup 语义)
    ↓
T39-005 (报告层级)
    ↓
T39-006 (文档 + demo + 发布收口)
```

## 工时估算

| 任务 | 预估 |
|------|------|
| T39-001 | 1.0h |
| T39-002 | 1.0h |
| T39-003 | 1.5h |
| T39-004 | 0.8h |
| T39-005 | 1.0h |
| T39-006 | 0.7h |
| **合计** | **6.0h** |