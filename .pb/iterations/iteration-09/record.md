# Iteration 09: 统一运行时上下文 — 基础模型定义与 history 写入补全

**版本**: v4.1.0  
**日期**: 2026-04-07  
**分支**: V4.1.0  
**需求来源**: `.pb/specs/return_value_unified_design.md`  
**优先级覆盖**: P0 + P1

---

## 迭代目标

建立统一运行时上下文（RuntimeContext）的基础数据模型，并补全所有关键字的 history 写入，确保步骤链连续。这是后续所有迭代的基础，必须首先完成。

---

## 核心约束（不可违反）

> 本迭代所有实现必须遵守 `rodski/docs/CORE_DESIGN_CONSTRAINTS.md` 的全部约束，特别是：
> - 关键字职责划分不变（type/send/verify/run 等语义不改变）
> - `${Return[-N]}` 的基本写法和语义保持不变
> - 不引入新的独立关键字体系
> - 不跨 case 共享运行时上下文

---

## 设计决策

### D9-01: RuntimeContext 数据结构

**决策**: 在 `rodski/core/` 新增 `runtime_context.py`，定义统一运行时上下文类：

```python
class RuntimeContext:
    def __init__(self):
        self.history: list = []      # Return[-N] 访问
        self.named: dict = {}        # set/get 命名访问
        # objects 预留，首版不实现
```

**Why**: 将现有分散的 Return 列表与未来 named/objects 统一到一个对象，便于后续扩展，同时不改变现有 `${Return[-N]}` 语义。

### D9-02: 现有 Return 机制迁移到 RuntimeContext.history

**决策**: 将 KeywordEngine 中现有的 `self._return_values` 列表替换为 `RuntimeContext.history`，保持 `store_return()` / `get_return()` 接口不变（内部委托给 context）。

**Why**: 对外接口不变，兼容现有代码；内部统一到 RuntimeContext，为后续 named/objects 扩展打基础。

### D9-03: 补全所有关键字的 history 写入

**决策**: 按规范表（第 8 节）逐一检查并补全以下关键字的 `store_return()` 调用：
- `navigate` → `True`
- `launch` → `True`
- `wait` → `True`
- `close` → `True`
- `clear` → `True`
- `upload_file` → `True`
- `assert` → `True`
- `verify` → 验证结果 list（已有，确认）
- `send` → 响应结果 dict（已有，确认）
- `run` → JSON 结果 / stdout / None（已有，确认）
- `DB` → SQL 结果 / None（已有，确认）

**Why**: 保证 `${Return[-N]}` 语义连续，任意步骤都可作为后续步骤的数据来源。

---

## 实施任务

### T9-001: 新建 RuntimeContext 类
- 文件：`rodski/core/runtime_context.py`
- 包含 `history: list`、`named: dict`
- 提供 `append_history(value)`、`get_history(n)` 方法
- `objects` 预留为空 dict，首版不实现任何访问逻辑

### T9-002: KeywordEngine 迁移到 RuntimeContext
- 将 `self._return_values` 替换为 `self._context = RuntimeContext()`
- `store_return(value)` → `self._context.append_history(value)`
- `get_return(n)` → `self._context.get_history(n)`
- 对外接口签名不变，不影响现有调用方

### T9-003: 补全 navigate / launch 的 history 写入
- 执行成功后调用 `store_return(True)`

### T9-004: 补全 wait / close / clear / upload_file / assert 的 history 写入
- 执行成功后调用 `store_return(True)`

### T9-005: 验证现有 verify / send / run / DB 的 history 写入
- 阅读现有实现，确认已写入
- 如有遗漏，补全

### T9-006: 回归测试
- 运行现有 Web 用例（如 `CassMall_examples/login`）
- 确认 `${Return[-N]}` 语义未被破坏

---

## 验收标准

1. `RuntimeContext` 类存在，包含 `history` 和 `named` 字段
2. 所有关键字执行后均有 history 记录（无空洞）
3. `${Return[-1]}` / `${Return[-2]}` 行为与迭代前完全一致
4. 现有回归用例全部通过

---

## 遗留与后续

- `named` 字段在本迭代中建立但不使用，由 iteration-11（set/get 重构）填充
- `evaluate` 的结构化修复在 iteration-10 完成
- 自动返回值提取在 iteration-12 完成
