# Iteration 41 任务清单 — 契约对齐：决策与 Schema 基础

**版本**: v6.7.6  
**分支**: `feature/iteration-41-contract-alignment`  
**依赖**: iteration-40 完成；`.pb/specs/v6.7.6-contract-alignment-fix.md` 已确认  
**设计文档**: `.pb/specs/v6.7.6-contract-alignment-fix.md`  
**目标**: 敲定悬而未决的设计决策，修复打包基线和 XSD 层契约漂移  
**范围**: 本迭代只做 Schema/Parser/Packaging 层，不改运行时执行语义

---

## T41-001: 前置设计决策 [0.5h]

### 任务

在开始编码前，确认以下三个悬而未决的决策并记录到设计文档：

1. **`run` builtin_call 去留**（P1-3）：
   - 选项 A：保留 `_try_builtin_call()`，写入 `CORE_DESIGN_CONSTRAINTS.md` 作为 `run` 的 in-process 扩展点，补充测试。
   - 选项 B：移除，将 network mock 等能力迁移为 `fun/builtin_ops/*.py` 脚本。
   - **需要确认**：选哪个？

2. **DB verify 字段路径规范格式**（P0-5）：
   - 当前三种写法：`field`、`0.field`、`[0].field`
   - **需要确认**：统一推荐哪种？其余是否保留兼容还是直接拒绝？

3. **根 demo (`rodski-demo/data/`) 处置**：
   - 选项 A：归档为 `rodski-demo/DEMO/_archive/`，不纳入 strict 验收。
   - 选项 B：补齐字段后纳入 strict 验收（与 `demo_full` 并行维护）。
   - **建议**：选 A，避免维护两套 demo 数据。

### 验证

决策结果写入 `.pb/specs/v6.7.6-contract-alignment-fix.md` 对应章节，标注"已确认"。

---

## T41-002: 发布入口与打包基线收口 [1.0h]

### 任务

1. 确认唯一发布入口为仓库根目录 `pyproject.toml`。
2. 统一版本号到 `6.7.6`（根 `pyproject.toml`、`rodski/__init__.py`）。
3. 处理 `rodski/pyproject.toml`：删除或标记为开发用途，CI 不从此构建发布包。
4. 确认运行时 dependencies 完整：`xmlschema`、`pyyaml`、`tqdm`、`psutil`、`requests`。
5. 确认 wheel/sdist 包含 `rodski/schemas/*.xsd`。
6. 确认 CLI 版本读取路径正确。

### 验证

```bash
python3 -m build
python3 -m venv /tmp/rodski-676-install
/tmp/rodski-676-install/bin/pip install dist/rodski-6.7.6-*.whl
/tmp/rodski-676-install/bin/python -c "
import rodski; print(rodski.__version__)
from rodski.core.model_parser import ModelParser
import importlib.resources as r
assert (r.files('rodski') / 'schemas' / 'model.xsd').is_file()
print('OK')
"
```

---

## T41-003: `launch` schema 与运行时修复 [1.0h]

### 任务

1. 在 `rodski/schemas/case.xsd` 的 `ActionType` 中加入 `launch`。
2. 修复 `_kw_launch` 中未定义 `model_type` 的引用。
3. 明确 `launch model="" data="应用名/路径"` 的 Desktop 行为。
4. 接口模型使用 `launch` 时直接失败并给出错误信息。
5. 增加 schema 合法性测试 + 最小运行时单测（不触发 NameError）。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests -k "launch or case_schema" -v
```

---

## T41-004: `model.xsd` 移除旧定位器格式 [1.2h]

### 任务

1. 从 `model.xsd` 移除 `element@value` 和 `element@locator` 属性。
2. 禁止 `element@type` 作为旧定位器格式入口。
3. 可执行 element 至少包含一个 `<location type="...">value</location>`。
4. `ModelParser` 遇到旧格式时抛出明确错误（不再静默丢弃）。
5. 接口模型保留 `_method`/`_url`/`_header_*` 语义，仍使用 `<location type="static/field">`。
6. 增加 XSD 拒绝旧格式 + 接受完整格式的测试。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests -k "model_schema or model_parser or locator" -v
```

---

## T41-005: plan validator 与 `rodski init` 骨架收口 [0.8h]

### 任务

1. `RodskiXmlValidator` 增加 `plan` kind 与 `plan.xsd` 映射。
2. `PlanParser` 统一使用公共 XML validator。
3. `rodski init` 默认创建 `plan/` 目录。
4. `rodski init` 默认创建 `data/data.sqlite` 和 `data/globalvalue.xml`。
5. `--no-sqlite` 打印废弃警告，不破坏 v6.0+ 数据契约。
6. 增加 init skeleton 和 plan validator 单元测试。

### 验证

```bash
PYTHONPATH=rodski python3 -m pytest rodski/tests -k "plan_validator or plan_parser or init" -v
```

---

## 执行顺序

```text
T41-001 (前置决策) ← 必须最先完成
    ↓
T41-002 (打包基线)
    ↓
T41-003 (launch schema)
    ↓
T41-004 (model.xsd)
    ↓
T41-005 (plan/init)
```

## 工时估算

| 任务 | 预估 |
|------|------|
| T41-001 前置设计决策 | 0.5h |
| T41-002 发布入口与打包基线 | 1.0h |
| T41-003 launch schema 与运行时 | 1.0h |
| T41-004 model.xsd 移除旧定位器格式 | 1.2h |
| T41-005 plan validator 与 init 骨架 | 0.8h |
| **合计** | **4.5h** |

---

## 完成定义

1. 三个前置决策已确认并写入设计文档。
2. 干净 venv 安装 wheel 后 CLI、依赖、`schemas/*.xsd` 可用。
3. `case.xsd` 接受 `launch`，拒绝 UI 原子动作。
4. `model.xsd` 拒绝旧格式，`ModelParser` 给出明确错误。
5. `rodski init` 生成完整骨架含 `plan/` 和 `data.sqlite`。
6. 所有新增单元测试通过。

---

## 后续迭代预告

- **Iteration 42**: 运行时严格化（SQLite strict、type/verify 缺字段、verify 语义、run 路径）~5.8h
- **Iteration 43**: Demo 迁移与文档交付（demo_full 清理、迁移指南、老用例失败排查文档）~4.0h
