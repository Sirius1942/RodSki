# Iteration 10: evaluate 结构化修复 — 任务清单

## 阶段一: 修复 store_return 调用

### T10-001: 修复 evaluate 的 store_return 调用
**文件**: `rodski/core/keyword_engine.py`（或 evaluate 实现所在文件）

- 定位 evaluate 关键字实现，找到 `str(result)` 转换处
- 将 `store_return(str(result) if result is not None else "")` 改为 `store_return(result)`
- `None` 情况直接 `store_return(None)`，不转为空字符串

**约束**: 只改 store_return 调用，不改 evaluate 的执行逻辑

**预计**: 0.5h | **Owner**: 待分配

---

## 阶段二: Web-only 约束

### T10-002: 非 Web driver 调用 evaluate 时抛出明确错误
**文件**: `rodski/core/keyword_engine.py`

- evaluate 入口处检查当前 driver 类型
- 若非 PlaywrightDriver（Web），抛出明确异常，信息说明 evaluate 仅支持 Web 浏览器驱动
- 不影响 Web 场景的正常执行

**预计**: 0.5h | **Owner**: 待分配

---

## 阶段三: 文档更新

### T10-003: 更新 evaluate 相关文档
**文件**: `rodski/docs/API_REFERENCE.md`（或关键字参考文档）

- 补充 Web-only 标注
- 补充使用优先级说明（低于自动提取和 get）
- 补充结构化返回值保留说明

**预计**: 0.5h | **Owner**: 待分配

---

## 阶段四: 验证

### T10-004: 验证 evaluate 结构化返回
**文件**: `rodski-demo` 示例网站

- 执行 `evaluate` 返回 JS 对象（如 `{title: document.title}`）
- 确认 history 中保留 dict 结构，未被 str() 降级
- 确认 `${Return[-1].title}` 可正常访问
- 运行现有回归用例，确认无破坏

**预计**: 0.5h | **Owner**: 待分配

---

## 任务汇总

| 任务 | 名称 | 预计 | 阶段 |
|------|------|------|------|
| T10-001 | 修复 evaluate store_return 调用 | 0.5h | 1 |
| T10-002 | 非 Web driver 调用时抛出明确错误 | 0.5h | 2 |
| T10-003 | 更新 evaluate 文档 | 0.5h | 3 |
| T10-004 | 验证结构化返回 | 0.5h | 4 |

**总预计**: 2h
