# Iteration 11: get / set 关键字重构 — 统一运行时上下文命名访问

**版本**: v4.1.2  
**日期**: 2026-04-07  
**分支**: V4.1.2  
**需求来源**: `.pb/specs/return_value_unified_design.md` §2.3、§4.2、§4.3、§12.1  
**优先级覆盖**: P3  
**前置依赖**: iteration-09（RuntimeContext.named 字段已建立）

---

## 迭代目标

重构 `get` 为双模式关键字（UI 文本获取 + 命名值读取），废弃 `get_text`；明确 `set` 的写入语义；两者执行后均写入 history，保证步骤链连续。

---

## 核心约束（不可违反）

> - 不改变 `type`/`send`/`verify` 等核心关键字的语义
> - `${Return[-N]}` 语义不变
> - 原 `get` 的 UI 文本获取能力保留在 `get` 自身（双模式），**废弃 `get_text`**
> - `set`/`get` 执行后必须写入 history（步骤链连续约束）
> - 不引入新的独立存储空间，named 是 RuntimeContext 的一部分

---

## 设计决策

### D11-01: 废弃 get_text，get 统一承接两种能力

**决策**:
- **废弃 `get_text`**，不新增该关键字
- 重构 `get` 为双模式关键字，根据 data 格式自动判断：
  - data 为 CSS/XPath 选择器（含 `#`、`.`、`//` 等前缀）→ UI 元素文本获取（低级补充手段）
  - data 为普通标识符（无选择器前缀）→ 从 `context.named` 读取命名值（主路径）
- 两种模式执行后均调用 `store_return(value)`，写入 history

**重要约束**：
- UI 元素文本获取的**推荐方式**是通过 `verify` + model + 数据表完成
- `get #selector` 直接获取 UI 元素文本属于**低级补充手段**，不推荐在常规业务用例主链路中使用
- 用户应优先通过 auto_capture（iteration-12）或 verify 获取页面值，而不是 `get #selector`

**Why**: 减少关键字数量，降低用户心智负担；明确推荐路径，避免 `get #selector` 被滥用为主路径取值手段。

### D11-02: set 写入 named + history

**决策**: `set` 执行逻辑：
1. 解析 `data="key=${Return[-1].field}"` 格式，解析出 key 和 value
2. 写入 `context.named[key] = value`
3. 调用 `store_return(value)`（写入 history）

**Why**: 规范第 4.2 节要求，set 执行后也必须写入 history，保证步骤链连续。

### D11-03: get 三模式执行逻辑

**决策**: `get` 根据 model 和 data 格式自动判断模式：

| model | data | 模式 | 行为 |
|-------|------|------|------|
| 空 | CSS/XPath 选择器（含 `#`、`.`、`//`、`css=`、`xpath=` 前缀） | UI 选择器模式（低级补充） | 直接用选择器读取元素文本 |
| 空 | 普通标识符（无选择器前缀） | 命名访问模式（主路径） | 从 `context.named[key]` 读取 |
| 模型名 | DataID | 模型模式（推荐 UI 取值方式） | 按模型元素定位，读取对应元素文本，返回 dict |

三种模式执行后均调用 `store_return(value)`，写入 history。

**推荐优先级**：
1. **模型模式**（`get ModelName D001`）— 推荐，与 type/verify 范式一致，可读性最高
2. **命名访问模式**（`get var_name`）— 读取 set 保存的命名变量
3. **UI 选择器模式**（`get #selector`）— 低级补充，不推荐在主链路使用

**Why**: 与框架整体"关键字 + 模型 + 数据"范式保持一致；模型模式是 UI 元素取值的推荐方式，选择器模式仅作兜底。

---

## 实施任务

### T11-001: 重构 get 关键字为双模式
- data 含选择器前缀（`#`、`.`、`//`、`css=`、`xpath=`）→ UI 文本获取模式（原有逻辑）
- data 为普通标识符 → 命名访问模式，从 `context.named[key]` 读取
- 两种模式均调用 `store_return(value)`
- 命名访问模式下 key 不存在时抛出明确错误

### T11-002: 废弃 get_text
- 从 SUPPORTED 关键字列表移除 `get_text`（或标记为 deprecated，执行时提示改用 `get`）
- 更新 API_REFERENCE.md 和 TEST_CASE_WRITING_GUIDE.md

### T11-003: 重构 set 关键字
- 解析 `key=value_expr` 格式（value_expr 支持 `${Return[-1].field}` 等模板）
- 写入 `context.named[key]`
- 调用 `store_return(value)`

### T11-004: 更新文档
- `API_REFERENCE.md`：更新 get/set/get_text 说明
- `TEST_CASE_WRITING_GUIDE.md`：补充 set/get 命名访问用法示例

### T11-005: 验证用例
- 场景 B（连续创建两条记录并分别保存）
- 验收用例 3（set 保存多个同类值）
- 验收用例 4（get 读取统一运行时上下文值）

---

## 验收标准

1. `set key=${Return[-1].field}` 能正确写入 `context.named` 并写入 history
2. `get key`（命名访问模式）能读取 named 值并写入 history，后续 `${Return[-1]}` 指向该值
3. `get #selector`（UI 文本模式）能读取元素文本并写入 history
4. UI 文本获取推荐通过 `verify` + model + 数据表完成，`get #selector` 仅作为低级补充手段
5. key 不存在时 get 抛出明确错误
6. 现有回归用例全部通过

---

## 遗留与后续

- `get` 的路径访问能力（`get Order.first.orderNo`）在 iteration-13 按需扩展
- 自动返回值提取（type 步骤后自动写入 named）在 iteration-12 完成
