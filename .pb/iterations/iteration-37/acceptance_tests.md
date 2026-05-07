# Iteration 37 验收测试：Plan 与 Selector 固定互斥

**版本**: v6.3.0-beta.1  
**测试目录**: `rodski-demo/DEMO/demo_full/`  
**目标**: 验证显式 plan 模式与 tag/group/priority selector 模式是两个独立入口，同一次 `rodski run` 不支持同时使用。

---

## 测试准备

### Demo 文件

依赖 v6.3.0 demo 验收文件：

```text
rodski-demo/DEMO/demo_full/
├── case/tc040_scenario_plan.xml
└── plan/v630_smoke.xml
```

`case/tc040_scenario_plan.xml` 至少包含：

- `SC-SMOKE-001`: `tag="smoke,p0"`, `group="positive"`
- `SC-SLOW-001`: `tag="slow"`, `group="positive"`
- `SC-NEG-001`: `tag="negative,p1"`, `group="negative"`

`plan/v630_smoke.xml` 至少显式选择 `SC-SMOKE-001`。

### 启动环境

```bash
cd rodski-demo/DEMO/demo_full
python3 init_db.py
python3 demosite/app.py
```

另一个终端执行验收命令。

---

## A37-001: 显式 plan 单独执行合法

**步骤**:

```bash
cd rodski-demo/DEMO/demo_full
rodski run @v630_smoke --dry-run
```

**期望**:

- 命令成功。
- 输出 `Plan: v630_smoke`。
- 输出被 plan 选择的 case/scenario。
- 不要求提供 tag/group selector。

**测试到的关键点**:

显式 plan 是独立执行入口，执行范围完全来自 `plan/v630_smoke.xml`。

---

## A37-002: selector 单独执行合法

**步骤**:

```bash
cd rodski-demo/DEMO/demo_full
rodski run --tag smoke --dry-run
```

**期望**:

- 命令成功。
- 输出临时 `TestPlanSelection`。
- 命中 `SC-SMOKE-001`。
- 不读取 `plan/v630_smoke.xml` 作为执行范围。

**测试到的关键点**:

selector 是独立临时入口，从 case XML scenario 元数据生成执行范围。

---

## A37-003: `@plan_id + --tag` 必须失败

**步骤**:

```bash
cd rodski-demo/DEMO/demo_full
rodski run @v630_smoke --tag smoke --dry-run
```

**期望**:

- 命令失败，退出码非 0。
- 错误信息包含：`@plan_id`、`--tag`、`不能同时使用`。
- 不生成执行结果目录。
- 不进入 case/scenario 执行。

**测试到的关键点**:

不支持“先按 plan，再按 tag 过滤”或“plan 与 tag 合并”的模式。

---

## A37-004: `@plan_id + --tags` 别名也必须失败

**步骤**:

```bash
cd rodski-demo/DEMO/demo_full
rodski run @v630_smoke --tags smoke --dry-run
```

**期望**:

- 命令失败，退出码非 0。
- 错误信息包含：`@plan_id`、`--tags` 或 `--tag`、`不能同时使用`。
- 不进入执行。

**测试到的关键点**:

兼容别名不能绕过互斥校验。

---

## A37-005: `@plan_id + --group` 必须失败

**步骤**:

```bash
cd rodski-demo/DEMO/demo_full
rodski run @v630_smoke --group negative --dry-run
```

**期望**:

- 命令失败，退出码非 0。
- 错误信息包含：`@plan_id`、`--group`、`不能同时使用`。
- 不进入执行。

**测试到的关键点**:

plan 不能与 group selector 同时作为执行范围来源。

---

## A37-006: `@plan_id + --exclude-tag` 必须失败

**步骤**:

```bash
cd rodski-demo/DEMO/demo_full
rodski run @v630_smoke --exclude-tag slow --dry-run
```

**期望**:

- 命令失败，退出码非 0。
- 错误信息包含：`@plan_id`、`--exclude-tag`、`不能同时使用`。
- 不进入执行。

**测试到的关键点**:

即使 `--exclude-tag` 看起来像过滤器，也不能和显式 plan 同时使用。

---

## A37-007: `@plan_id + --priority` 必须失败

**步骤**:

```bash
cd rodski-demo/DEMO/demo_full
rodski run @v630_smoke --priority P0 --dry-run
```

**期望**:

- 命令失败，退出码非 0。
- 错误信息包含：`@plan_id`、`--priority`、`不能同时使用`。
- 不进入执行。

**测试到的关键点**:

所有执行范围 selector 都与 plan 互斥，不只 tag/group。

---

## A37-008: `--filter-tag` 不被支持

**步骤**:

```bash
cd rodski-demo/DEMO/demo_full
rodski run @v630_smoke --filter-tag smoke --dry-run
```

**期望**:

- 命令失败，退出码非 0。
- 错误信息明确 `--filter-tag` 不支持，或被 CLI 参数校验拒绝。
- 不进入执行。

**测试到的关键点**:

当前设计不提供 plan 后过滤算子，避免产生“先 plan 后过滤”的第三种执行模式。

---

## A37-009: plan 可与非执行范围参数组合

**步骤**:

```bash
cd rodski-demo/DEMO/demo_full
rodski run @v630_smoke --dry-run --log-level INFO
```

如支持环境参数：

```bash
rodski run @v630_smoke --dry-run --env=staging
```

**期望**:

- 命令成功。
- 执行范围仍完全来自 `plan/v630_smoke.xml`。
- 日志级别、环境等参数只影响运行上下文，不参与选择 case/scenario。

**测试到的关键点**:

互斥只针对执行范围来源；非执行范围参数不受影响。

---

## 关键证据检查

| 证据 | 检查方式 | 通过标准 |
|------|----------|----------|
| 错误发生在执行前 | 查看 stdout/stderr 与 result 目录 | 冲突命令不生成新的 case 执行结果 |
| 错误信息可指导用户 | 查看 stderr | 包含“二选一”：`rodski run @plan_id` 或 `rodski run --tag smoke` |
| plan 文件未被修改 | `shasum plan/*.xml` 前后对比 | 冲突命令和 selector dry-run 都不修改 plan XML |
| selector 单独入口仍可用 | `rodski run --tag smoke --dry-run` | 能输出临时选择结果 |
| plan 单独入口仍可用 | `rodski run @v630_smoke --dry-run` | 能输出显式 plan 选择结果 |

---

## 验收通过标准

- A37-001、A37-002 成功。
- A37-003 ~ A37-008 全部失败且不进入执行。
- A37-009 成功。
- 错误信息明确说明 plan 与 selector 不能同时使用。
- 没有任何验收项要求或暗示支持 `@plan_id + --tag`、`@plan_id + --group` 或 `--filter-tag`。