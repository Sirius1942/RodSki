# Iteration 12: Auto Capture — 任务清单

## 阶段一: 模型解析器扩展

### T12-001: 模型解析器支持 auto_capture 节点
**文件**: `rodski/core/model_parser.py`

- 解析 `<auto_capture trigger="type|send">` 节点
- UI 字段（trigger=type）：解析 `<field name> + <location type>`，复用现有 location 解析逻辑
- 接口字段（trigger=send）：解析 `<field name path="...">`
- 解析结果挂载到 model 对象：`model.auto_capture_type: list[dict] | None`，`model.auto_capture_send: list[dict] | None`

**预计**: 1.5h | **Owner**: 待分配

---

## 阶段二: type Auto Capture

### T12-002: type 执行后触发 UI auto_capture
**文件**: `rodski/core/keyword_engine.py`

- `_batch_type` 完成后检查 `model.auto_capture_type`
- 有规则时：逐字段调用 driver 读取元素文本（复用 get_text 逻辑），组装 dict
- 调用 `store_return(dict)`
- 无规则时：维持现有 `store_return` 行为不变

**预计**: 1.5h | **Owner**: 待分配

---

## 阶段三: send Auto Capture

### T12-003: send 执行后触发接口 auto_capture
**文件**: `rodski/core/keyword_engine.py`

- `send` 完成后检查 `model.auto_capture_send`
- 从响应 body dict 按 `path`（点分隔）逐级取值
- 将提取结果写入响应 dict 的 `_capture` 字段
- `store_return` 整体响应 dict（含 `_capture`）
- 无规则时：维持现有行为

**预计**: 1.5h | **Owner**: 待分配

---

## 阶段四: 错误处理

### T12-004: 定义 AutoCaptureError
**文件**: `rodski/core/exceptions.py`（或现有异常文件）

- 定义 `AutoCaptureError`，包含字段名、来源（locator/path）、失败原因
- type 和 send 的 auto_capture 失败均使用此异常

**预计**: 0.5h | **Owner**: 待分配

---

## 阶段五: rodski-demo 补充

### T12-005: rodski-demo 补充演示页面和接口
**文件**: `rodski-demo/` 相关文件

- 表单页面：提交后展示 `resultId`，对应模型定义 `trigger="type"` auto_capture
- 登录接口响应包含 `token`，对应模型定义 `trigger="send"` auto_capture

**预计**: 1h | **Owner**: 待分配

---

## 阶段六: 验证

### T12-006: 验证 Auto Capture
**文件**: `rodski-demo` 示例用例

- 场景 A：UI 表单提交后自动返回 `resultId`，后续直接 `${Return[-1].resultId}`
- 场景 C：auto_capture 字段不存在时抛出 `AutoCaptureError`，不 silent fail
- send auto_capture：登录后 `${Return[-1]._capture.token}` 可正常访问
- 回归：现有用例全部通过

**预计**: 1h | **Owner**: 待分配

---

## 任务汇总

| 任务 | 名称 | 预计 | 阶段 |
|------|------|------|------|
| T12-001 | 模型解析器支持 auto_capture 节点 | 1.5h | 1 |
| T12-002 | type 执行后触发 UI auto_capture | 1.5h | 2 |
| T12-003 | send 执行后触发接口 auto_capture | 1.5h | 3 |
| T12-004 | 定义 AutoCaptureError | 0.5h | 4 |
| T12-005 | rodski-demo 补充演示页面和接口 | 1h | 5 |
| T12-006 | 验证 Auto Capture | 1h | 6 |

**总预计**: 7h
