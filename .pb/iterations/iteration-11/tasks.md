# Iteration 11: get/set 重构 — 任务清单

## 阶段一: get 重构为双模式

### T11-001: 重构 get 关键字为三模式
**文件**: `rodski/core/keyword_engine.py`

- model 非空 + data 为 DataID → 模型模式：按模型元素定位，读取各元素文本，返回 dict
- model 空 + data 含选择器前缀（`#`、`.`、`//`、`css=`、`xpath=`）→ UI 选择器模式（低级补充）
- model 空 + data 为普通标识符 → 命名访问模式，从 `self._context.named[key]` 读取
- 三种模式均调用 `store_return(value)`
- 命名访问模式下 key 不存在时抛出明确错误

**预计**: 2h | **Owner**: 待分配

### T11-002: 废弃 get_text
**文件**: `rodski/core/keyword_engine.py`

- `get_text` 标记为 deprecated，执行时输出 warning 提示改用 `get`
- 后续版本可从 SUPPORTED 列表移除

**预计**: 0.5h | **Owner**: 待分配

---

## 阶段二: set 重构

### T11-003: 重构 set 关键字
**文件**: `rodski/core/keyword_engine.py`

- 解析 `key=value_expr` 格式（value_expr 支持 `${Return[-1].field}` 等模板）
- 写入 `self._context.named[key]`
- 调用 `store_return(value)`

**约束**: 不改变模板解析逻辑，复用现有 `${...}` 解析器

**预计**: 1h | **Owner**: 待分配

---

## 阶段三: 文档更新

### T11-004: 更新关键字文档
**文件**: `rodski/docs/TEST_CASE_WRITING_GUIDE.md`

- 更新 `get` 说明：双模式（UI 文本获取 vs 命名访问），明确推荐路径
- 标注 `get #selector` 为低级补充手段，推荐使用 `verify` + model + 数据表
- 废弃 `get_text`，说明改用 `get`
- 补充 `set` 命名访问用法示例

**预计**: 1h | **Owner**: 待分配

---

## 阶段四: 验证

### T11-005: 验证 set/get 命名访问
**文件**: `rodski-demo` 示例用例

- set 保存 `first_result` / `second_result`，get 读取，verify 验证
- get 读取不存在 key 时报错
- get #selector UI 文本获取模式正常工作
- 回归：现有用例全部通过

**预计**: 1h | **Owner**: 待分配

---

## 任务汇总

| 任务 | 名称 | 预计 | 阶段 |
|------|------|------|------|
| T11-001 | 重构 get 关键字为双模式 | 1.5h | 1 |
| T11-002 | 废弃 get_text | 0.5h | 1 |
| T11-003 | 重构 set 关键字 | 1h | 2 |
| T11-004 | 更新关键字文档 | 1h | 3 |
| T11-005 | 验证 set/get | 1h | 4 |

**总预计**: 5h
