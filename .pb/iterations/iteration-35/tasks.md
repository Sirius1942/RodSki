# Iteration 35 任务清单

**版本**: v6.3.0-alpha.1  
**分支**: feature/iteration-35-scenario-xml  
**依赖**: iteration-34 完成，v6.3.0 设计稿确认

---

## T35-001: 更新 case.xsd 支持 `<scenario>` [1h]

### 任务

1. 修改 `rodski/schemas/case.xsd`。
2. 允许 `<scenario>` 作为 `<test_case>` 的子元素。
3. 允许 `<scenario>` 内包含 `test_step`、`if`、`elif`、`else`、`loop` 等运行时结构。
4. 新增 scenario 属性约束：
   - `id` 必填
   - `title` 可选
   - `group` 可选
   - `tag` 可选
   - `depends` 可选
5. 补充 schema 单元测试或 XML fixture。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests/unit -k "case_xsd or scenario" -v
```

---

## T35-002: CaseParser 解析 case/scenario/step 树 [1.5h]

### 任务

1. 修改 `rodski/core/case_parser.py`。
2. 为 `<scenario>` 建立内部数据结构，保留 `id/title/group/tag/depends`。
3. 保留 scenario 内步骤 XML 顺序。
4. 为后续 plan/selector 编译保留 case/scenario/step 层级信息。
5. 不改变现有 case 级 `pre_process`、`test_case`、`post_process` 解析语义。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests/unit/test_case_parser.py -v
```

---

## T35-003: 保持旧 case 与裸步骤兼容执行 [1h]

### 任务

1. 更新执行器对 `<test_case>` 内容的遍历逻辑。
2. 不含 `<scenario>` 的旧 case 继续按原有步骤执行。
3. 含 `<scenario>` 的 case 按 XML 顺序执行 scenario。
4. `<test_case>` 内裸 `test_step` 继续按 case 级步骤执行，不受后续 scenario 选择影响。
5. 保证 `pre_process` 与 `post_process` 生命周期不变。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests/unit/test_ski_executor.py -k "scenario or execute" -v
python3 rodski/selftest.py
```

---

## T35-004: 实现 scenario 内运行时控制结构兼容 [0.8h]

### 任务

1. 确认 `<scenario>` 内的 `<if>` / `<elif>` / `<else>` / `<loop>` 复用现有运行时执行逻辑。
2. 确认 `<if>` 不再被文档描述为静态执行开关。
3. 增加 scenario 内嵌运行时分支测试。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests/unit/test_ski_executor.py -k "if or elif or scenario" -v
```

---

## T35-005: 支持同 case 内 scenario depends 跳过 [1h]

### 任务

1. 解析 `depends="SC-001,SC-002"` 为同 case 内依赖列表。
2. 依赖 scenario 失败或跳过时，当前 scenario 标记为 skipped。
3. skipped 原因中保留依赖来源。
4. 第一版不支持跨 case 或跨 project 依赖。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests/unit/test_ski_executor.py -k "depends or skipped" -v
```

---

## T35-006: 文档与 demo 验收补齐 [0.7h]

### 任务

1. 更新 `rodski/docs/TEST_CASE_WRITING_GUIDE.md` 的 scenario 写法。
2. 更新 `rodski/docs/SKILL_REFERENCE.md` 中 `<if>` 与 `<scenario>` 的边界说明。
3. 在 `rodski-demo/` 增加或扩展 TC040-TC044 验收用例。
4. 确认不新增 `rodski/examples/`。

### 验证

```bash
python3 rodski/selftest.py
PYTHONPATH=rodski python3 -m pytest rodski/tests/unit -k "scenario" -v
```

---

## 执行顺序

```text
T35-001 (case.xsd)
    ↓
T35-002 (CaseParser)
    ↓
T35-003 (兼容执行)
    ↓
T35-004 (scenario 内运行时控制)
    ↓
T35-005 (depends 跳过)
    ↓
T35-006 (文档与 demo)
```

## 工时估算

| 任务 | 预估 |
|------|------|
| T35-001 | 1.0h |
| T35-002 | 1.5h |
| T35-003 | 1.0h |
| T35-004 | 0.8h |
| T35-005 | 1.0h |
| T35-006 | 0.7h |
| **合计** | **6.0h** |