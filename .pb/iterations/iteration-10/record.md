# Iteration 10: evaluate 结构化修复 + 使用约束落地

**版本**: v4.1.1  
**日期**: 2026-04-07  
**分支**: V4.1.1  
**需求来源**: `.pb/specs/return_value_unified_design.md` §6、§7  
**优先级覆盖**: P2  
**前置依赖**: iteration-09 完成（RuntimeContext 基础已建立）

---

## 迭代目标

修复 `evaluate` 关键字将 dict/list 结果无条件 `str()` 的问题，使其与 `send`/`run`/`DB` 的结构化返回行为一致；同时在文档和代码注释中落地 evaluate 的使用约束。

---

## 核心约束（不可违反）

> - `evaluate` 仍然是 Web-only 能力，不扩展到其他平台
> - 不改变 `evaluate` 的关键字名称和 DSL 语法
> - 不改变其他关键字的返回值行为
> - 修复范围严格限定在 evaluate 的 `store_return` 调用处

---

## 设计决策

### D10-01: evaluate 返回值保留结构

**现状问题**:
```python
result_str = str(result) if result is not None else ""
self.store_return(result_str)
```

**修复方案**:
```python
self.store_return(result)  # 直接存入，不做 str() 转换
```

对 `None` 也直接存入（`store_return(None)`），与其他关键字行为一致。

**Why**: dict/list 被 `str()` 后，`${Return[-1].field}` 路径访问能力丢失，与 send/run/DB 的结构化返回不一致。

### D10-02: evaluate Web-only 约束在代码层显式标注

**决策**: 在 evaluate 实现入口处添加注释，明确标注 Web-only 约束，并在非 Web driver 调用时抛出明确错误（而非静默失败）。

**Why**: 防止未来开发者误将 evaluate 扩展到桌面端或接口测试场景。

---

## 实施任务

### T10-001: 修复 evaluate 的 store_return 调用
- 定位 evaluate 关键字实现（`keyword_engine.py` 或专用文件）
- 将 `store_return(str(result))` 改为 `store_return(result)`
- `None` 情况：`store_return(None)`，不再转为空字符串

### T10-002: evaluate 非 Web driver 调用时抛出明确错误
- 检查当前 driver 类型，若非 PlaywrightDriver（Web），抛出 `UnsupportedDriverError` 或类似异常
- 错误信息明确说明：`evaluate` 仅支持 Web 浏览器驱动

### T10-003: 更新 API_REFERENCE.md 中 evaluate 的说明
- 补充 Web-only 标注
- 补充使用优先级说明（低于自动提取和 get）
- 补充结构化返回值说明

### T10-004: 验证用例
- 在 `rodski-demo` 或现有示例网站执行 `evaluate` 返回 JS 对象
- 确认 dict/list 不被 str() 降级
- 确认 `${Return[-1].field}` 可正常访问

---

## 验收标准

1. `evaluate` 返回 dict/list 时，history 中保留原始结构
2. `${Return[-1].field}` 对 evaluate 结果可正常解析
3. 在非 Web driver 下调用 evaluate 时，抛出明确错误
4. API_REFERENCE.md 中 evaluate 有 Web-only 标注和使用约束说明
5. 现有回归用例全部通过

---

## 遗留与后续

- evaluate 的"优先级低于自动提取"在用户文档层面体现，自动提取能力在 iteration-12 实现
