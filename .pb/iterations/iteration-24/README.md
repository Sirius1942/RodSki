# Iteration 24: verify 空校验修复

> 版本: v5.3.1
> 分支: fix/v5.3.1-validation
> 日期: 2026-04-11
> 工时: 2h
> 优先级: P0
> 前置依赖: iteration-23（data_verify.xml 已创建）
> 设计文档: `.pb/specs/verify-data-organization-fix.md` 第二部分

---

## 需求

### 业务需求

- `_verify` 数据表中 10 处使用 `${Return[-1]}` 导致"自己跟自己比"空校验，断言永远通过
- 需要将空校验替换为具体的期望字面值，恢复断言价值
- 需要在代码层增加自引用检测警告，防止后续复现

### 技术需求

- 修改 `data_verify.xml` 中 10 处 `${Return[-1]}` 为字面期望值
- 在 `keyword_engine.py` 的 `_batch_verify` 增加自引用检测 warning

---

## 受影响用例清单

| 数据表 | 行ID | 字段 | 当前值 | 修正为 |
|--------|------|------|--------|--------|
| `EvaluateResult_verify` | V001 | title | `${Return[-1].title}` | 具体字面值（需从测试环境确认） |
| `ReturnTest_verify` | V001 | result | `${Return[-1]}` | 具体字面值 |
| `SetGetVerify_verify` | V001 | value | `${Return[-1]}` | 具体字面值 |
| `GetVerify_verify` | V001 | result | `${Return[-1]}` | 具体字面值 |
| `GetModelVerify_verify` | V001 | formResult | `${Return[-1].formResult}` | 具体字面值 |
| `DemoFormVerify_verify` | V001 | resultId | `${Return[-1].resultId}` | 具体字面值 |
| `KeywordTest_verify` | V002 | formResult | `${Return[-1]}` | 具体字面值 |
| `QuerySQL_verify` | V001 | order_no | `${Return[-1][0].order_no}` | 具体字面值 |
| `QuerySQL_verify` | V003 | total | `${Return[-1][0].total}` | 具体字面值 |
| `QueryMySQL_verify` | V001 | order_no | `${Return[-1][0].order_no}` | 具体字面值 |

**注意**: 某些用例（如 TC009 ReturnTest、TC010 SetGetVerify、TC011 GetVerify、TC012 EvaluateResult、TC012B GetModelVerify、TC013 DemoFormVerify）的 verify 步骤前是 UI 操作 + get/evaluate，verify 的模型可能是 UI 类型。需要逐个确认模型类型，只修正接口/DB 类型的空校验。UI 类型的 verify 使用 `${Return[-1]}` 是跨源比对，属于合法用法。

---

## 开发任务

### T24-001: 确认模型类型与修正范围 (预计 30min)

**文件**: `rodski-demo/DEMO/demo_full/model/model.xml`、`rodski-demo/model/model.xml`

**任务**:
1. 对照受影响清单中每个 `_verify` 表对应的模型，检查其 `__model_type__` 属性
2. 仅 `interface` 或 `database` 类型的 verify 为空校验需修正
3. `ui` 类型的 verify 使用 `${Return[-1]}` 是合法跨源比对，**不修改**
4. 确定每个需修正字段的具体期望字面值（从测试用例上下文 + demosite 行为推导）

**验收**:
- [ ] 每个待修正字段已确认模型类型
- [ ] 每个字面值已确认

### T24-002: 修复 demo_full data_verify.xml 空校验 (预计 30min)

**文件**: `rodski-demo/DEMO/demo_full/data/data_verify.xml`

**任务**:
1. 按 T24-001 确认结果，将接口/DB 模型的 `${Return[-1]}` 替换为具体字面值
2. 保留 UI 模型的 `${Return[-1]}` 引用（合法用法）

**验收**:
- [ ] 接口/DB 类型 verify 不再有 `${Return[-1]}` 自引用
- [ ] UI 类型 verify 保持不变

### T24-003: 修复 rodski-demo 根目录 data_verify.xml 空校验 (预计 15min)

**文件**: `rodski-demo/data/data_verify.xml`

**任务**:
1. 同 T24-002 操作

**验收**:
- [ ] 同 T24-002

### T24-004: keyword_engine.py 自引用检测 (预计 30min)

**文件**: `rodski/core/keyword_engine.py` — `_batch_verify` 方法

**任务**:
1. 在 `_batch_verify` 中，`resolve_with_return` 调用之前，增加自引用检测逻辑
2. 当模型类型为非 UI 且期望值包含 `${Return[-1]}` 时，输出 warning 日志
3. 不阻断执行，仅警告

**代码**:
```python
# 在 resolve_with_return 之前
raw_expected = str(data_row[element_name])

# 自引用检测：非 UI 模型的 verify 数据中不应使用 ${Return[-1]}
if model_type != MODEL_TYPE_UI and '${Return[-1]}' in raw_expected:
    logger.warning(
        f"[空校验警告] {element_name}: 期望值 '{raw_expected}' "
        f"引用了 Return[-1]，但 verify 在接口/DB 模式下实际值也取自 "
        f"Return[-1]，这会导致自己跟自己比较，断言永远通过。"
        f"请改为具体的期望字面值。"
    )
```

**验收**:
- [ ] 代码已添加，语法正确
- [ ] 不影响正常 verify 流程
- [ ] warning 仅在非 UI + `${Return[-1]}` 时触发

### T24-005: 验证测试 (预计 15min)

**任务**: 同 T23-006，运行全量测试确认修正后无回归

**验收**:
- [ ] 通过率与修改前一致
- [ ] 结果记录到 `record.md`

---

## 验收标准

1. **空校验消除**: 接口/DB 模型的 `_verify` 表不再有 `${Return[-1]}` 自引用
2. **代码防护**: `_batch_verify` 能检测并警告自引用
3. **无回归**: 测试通过率与修改前一致
4. **合法用法保留**: UI 模型的 `${Return[-1]}` 不受影响

---

## 风险与注意事项

1. **关键**: 必须逐个确认模型类型，不能盲目修改。UI 模型的 `${Return[-1]}` 是合法跨源比对
2. 字面期望值需要从业务逻辑推导，不能随意填写
3. `keyword_engine.py` 修改需确认 `model_type` 和 `MODEL_TYPE_UI` 变量在 `_batch_verify` 作用域内可用
