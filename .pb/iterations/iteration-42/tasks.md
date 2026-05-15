# Iteration 42 任务清单 — 契约对齐：运行时严格化

**版本**: v6.7.6  
**分支**: `feature/iteration-42-runtime-strict`  
**依赖**: iteration-41 完成（Schema/Packaging 层已修复）  
**设计文档**: `.pb/specs/v6.7.6-contract-alignment-fix.md`  
**目标**: 让运行时执行引擎严格执行数据契约，消除静默跳过和空校验  
**范围**: 运行时行为变更（breaking change），不涉及 demo 数据修改

---

## T42-001: SQLite schema 严格字段一致性 [1.0h]

### 任务

1. 修改 `DataSchemaValidator.check_sqlite_schema()`，要求每行字段集合与 `rs_datatable_field` 完全一致。
2. 错误信息同时列出 missing 和 extra 字段，格式：`表名.行ID: missing=[a,b], extra=[c]`。
3. `rodski data validate --strict` 复用同一校验逻辑。
4. 错误提示中说明：缺字段必须显式填 `BLANK`/`NULL`/`NONE`，不能省略。
5. 增加缺字段、多字段、完全一致三类单元测试。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests -k "data_schema or sqlite or validate" -v
rodski data validate rodski-demo/DEMO/demo_full --strict
```

---

## T42-002: `type` / `verify` 缺字段失败 [1.0h]

### 任务

1. `type` 批量输入时，模型元素在数据行中缺字段 → 直接失败（不再 `continue`）。
2. `verify` 批量验证时，模型元素或验证字段缺失 → 直接失败。
3. 任意 `verify` 最终比较字段数为 0 → 失败，不允许空校验通过。
4. 保留 `BLANK`/`NULL`/`NONE` 的显式跳过语义不变。
5. 增加 UI `type`、UI `verify`、接口 `verify` 的缺字段单测。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests -k "batch_type or batch_verify or missing_field" -v
```

---

## T42-003: 接口/DB `_verify` 自引用失败 [0.8h]

### 任务

1. 非 UI 模型的 `_verify` 数据中出现 `${Return[-1]` → 直接失败（不再 warning 放行）。
2. 错误消息：`"接口/DB verify 的实际值已自动从 Return[-1] 读取，_verify 期望值必须写字面值或 GlobalValue"`。
3. UI 模型的 `${Return[-1]}` 保持现有语义，不在本任务扩大范围。
4. 增加单元测试覆盖：interface _verify 含 Return → 失败；ui _verify 含 Return → 通过。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests -k "return_self_reference or verify_return" -v
```

---

## T42-004: DB verify 语义修复 [1.2h]

### 任务

1. database 模型的 `verify` 改为按 `_verify` 数据行字段驱动比较（不依赖 model element 列表）。
2. 实际值从 `Return[-1]` 查询结果中读取。
3. 字段路径格式统一为 iteration-41 决策结果（T41-001 确认的规范格式）。
4. 查询结果缺字段 → 失败；结果为空 → 失败；比较字段数为 0 → 失败。
5. 增加 DB verify 测试：正常匹配、不匹配、缺字段、空结果、0 字段。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests -k "db_verify or database" -v
```

---

## T42-005: Case `data` 属性内置函数边界 [0.8h]

### 任务

1. Case XML `test_step@data` 中检测到 `${random(...)}`/`${date(...)}` → 直接失败。
2. Case `data` 仍允许：`GlobalValue.*`、命名变量、`Return` 引用。
3. SQLite 字段值继续支持内置函数（不受影响）。
4. 错误消息：`"内置函数 ${random/date} 只能写在 data.sqlite 字段值中，不能写在 Case XML data 属性"`。
5. 增加 Case data 禁止函数 + SQLite 字段允许函数的对比测试。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests -k "builtin_function or data_resolver or case_data" -v
```

---

## T42-006: `run` 路径归一化与 builtins 落地 [1.0h]

### 任务

1. `run` 支持 `data="fun/desktop/key_combo.py Ctrl+A"`（带 `fun/` 前缀）。
2. `run` 支持 `data="desktop/key_combo.py Ctrl+A"`（不带前缀）。
3. `run` 支持 `model="desktop_ops" data="key_combo.py command+a"`（model 指定子目录）。
4. 路径归一化后不允许脚本逃出模块 `fun/` 目录（防止 `../../` 路径穿越）。
5. 按 T41-001 决策结果处理 `_try_builtin_call()`：
   - 若保留：写入契约，补测试，明确调用格式。
   - 若移除：迁移为 `fun/` 脚本，删除 `_try_builtin_call`。
6. `vision_desktop` demo 中 3 条 `fun/` 前缀 run 作为回归样本。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests -k "run_keyword or fun_path" -v
rodski run rodski-demo/DEMO/vision_desktop/case/desktop_demo.xml --dry-run
```

---

## 执行顺序

```text
T42-001 (SQLite strict)
    ↓
T42-002 (type/verify 缺字段)
    ↓
T42-003 (verify 自引用)
    ↓
T42-004 (DB verify 语义)
    ↓
T42-005 (Case data 函数边界)
    ↓
T42-006 (run 路径)
```

## 工时估算

| 任务 | 预估 |
|------|------|
| T42-001 SQLite schema 严格字段一致性 | 1.0h |
| T42-002 type / verify 缺字段失败 | 1.0h |
| T42-003 接口/DB verify 自引用失败 | 0.8h |
| T42-004 DB verify 语义修复 | 1.2h |
| T42-005 Case data 内置函数边界 | 0.8h |
| T42-006 run 路径归一化与 builtins | 1.0h |
| **合计** | **5.8h** |

---

## 完成定义

1. SQLite 严格校验能发现任意缺字段行。
2. `type`/`verify` 不再静默跳过缺字段。
3. 非 UI `_verify` 中 `${Return[-1]}` 直接失败。
4. DB `verify` 至少比较一个字段，空比较失败。
5. Case `data` 中内置函数被拒绝并给出明确错误。
6. `run` 能正确执行带/不带 `fun/` 前缀的脚本路径。
7. 所有新增单元测试通过。

---

## 风险提示

本迭代包含 **breaking change**：原来静默通过的用例会开始失败。确保：
- iteration-43 的 demo 迁移紧跟本迭代完成。
- 如果发现 `demo_full` 在本迭代修改后无法 dry-run，优先修复 demo 数据而非回退运行时逻辑。
