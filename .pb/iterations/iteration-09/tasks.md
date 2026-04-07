# Iteration 09: 统一运行时上下文 — 任务清单

## 阶段一: RuntimeContext 基础模型

### T9-001: 新建 RuntimeContext 类
**文件**: `rodski/core/runtime_context.py`（新建）

- 定义 `RuntimeContext` 类，包含 `history: list`、`named: dict`、`objects: dict`（预留空）
- 实现 `append_history(value)` — 追加到 history
- 实现 `get_history(n)` — 支持负索引，返回 `history[n]`，越界时返回 `None`
- `objects` 首版不实现任何访问逻辑，仅占位

**预计**: 1h | **Owner**: 待分配

---

## 阶段二: KeywordEngine 迁移

### T9-002: KeywordEngine 迁移到 RuntimeContext
**文件**: `rodski/core/keyword_engine.py`

- 将 `self._return_values`（或现有 Return 列表）替换为 `self._context = RuntimeContext()`
- `store_return(value)` 内部改为调用 `self._context.append_history(value)`
- `get_return(n)` 内部改为调用 `self._context.get_history(n)`
- 对外接口签名不变，不影响现有调用方

**约束**: 不改变 `${Return[-N]}` 的解析逻辑，只替换底层存储

**预计**: 1h | **Owner**: 待分配

---

## 阶段三: 补全关键字 history 写入

### T9-003: 补全 navigate / launch 的 history 写入
**文件**: `rodski/core/keyword_engine.py`

- `navigate` 执行成功后调用 `store_return(True)`
- `launch` 执行成功后调用 `store_return(True)`

**预计**: 0.5h | **Owner**: 待分配

### T9-004: 补全 wait / close / clear / upload_file / assert 的 history 写入
**文件**: `rodski/core/keyword_engine.py`

- 以上关键字执行成功后各调用 `store_return(True)`
- 失败时维持现有异常语义，不强制写入

**预计**: 0.5h | **Owner**: 待分配

### T9-005: 确认 verify / send / run / DB 的 history 写入
**文件**: `rodski/core/keyword_engine.py`

- 阅读现有实现，逐一确认已调用 `store_return`
- 如有遗漏，补全
- 确认 send 写入完整响应 dict，run 写入 JSON/stdout/None，DB 写入结果/None

**预计**: 0.5h | **Owner**: 待分配

---

## 阶段四: 回归验证

### T9-006: 回归测试
**文件**: 现有示例用例

- 运行 `CassMall_examples/login` 或等效 Web 用例
- 确认 `${Return[-1]}` / `${Return[-2]}` 行为与迭代前完全一致
- 确认所有步骤执行后 history 均有记录

**预计**: 0.5h | **Owner**: 待分配

---

## 任务汇总

| 任务 | 名称 | 预计 | 阶段 |
|------|------|------|------|
| T9-001 | 新建 RuntimeContext 类 | 1h | 1 |
| T9-002 | KeywordEngine 迁移到 RuntimeContext | 1h | 2 |
| T9-003 | 补全 navigate/launch history 写入 | 0.5h | 3 |
| T9-004 | 补全 wait/close/clear/upload_file/assert history 写入 | 0.5h | 3 |
| T9-005 | 确认 verify/send/run/DB history 写入 | 0.5h | 3 |
| T9-006 | 回归测试 | 0.5h | 4 |

**总预计**: 4h
