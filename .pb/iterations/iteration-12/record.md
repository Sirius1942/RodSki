# Iteration 12: 自动返回值提取（Auto Capture）— type + send

**版本**: v4.1.3  
**日期**: 2026-04-07  
**分支**: V4.1.3  
**需求来源**: `.pb/specs/return_value_unified_design.md` §5  
**优先级覆盖**: P4  
**前置依赖**: iteration-09（RuntimeContext）、iteration-11（set/get 命名访问）

---

## 迭代目标

为 `type`（UI）和 `send`（接口）两个关键字增加模型驱动的自动返回值提取能力（Auto Capture）：步骤执行成功后，根据模型中定义的提取规则自动读取关键业务值，写入当前步骤的 history，使后续步骤可直接通过 `${Return[-1].field}` 使用，无需额外补 `get` 步骤。

---

## 核心约束（不可违反）

> - `type` / `send` 关键字的核心语义不变
> - 自动提取是**模型能力**，规则定义在模型文件中，不在 case 步骤中重复声明
> - 自动提取失败不允许 silent fail，必须作为可见错误暴露
> - 不改变 `${Return[-N]}` 的基本写法
> - 首版 type 聚焦 UI（Web）场景，不强制扩展到桌面端

---

## 设计决策

### D12-01: 模型 XML 中定义 auto_capture 规则

**现有模型 XML 结构**（以 `LoginForm` 为例）：

```xml
<model name="LoginForm" servicename="">
    <element name="username" type="web">
        <type>input</type>
        <location type="id">loginUsername</location>
    </element>
    <element name="loginBtn" type="web">
        <type>button</type>
        <location type="id">loginBtn</location>
    </element>
</model>
```

**扩展方案**：在 `<model>` 内新增 `<auto_capture>` 子节点，与 `<element>` 并列：

```xml
<model name="InquiryCreate" servicename="">
    <!-- 原有 element 定义不变 -->
    <element name="inquiryType" type="web">
        <type>select</type>
        <location type="id">inquiryType</location>
    </element>
    <element name="submitBtn" type="web">
        <type>button</type>
        <location type="id">submitBtn</location>
    </element>

    <!-- 新增：自动返回值提取规则 -->
    <auto_capture trigger="type">
        <field name="inquiryNo">
            <location type="id">inquiryNo</location>
        </field>
        <field name="status">
            <location type="css">.status-badge</location>
        </field>
    </auto_capture>
</model>
```

**字段说明**：
- `<auto_capture trigger="type">` — `trigger` 指定由哪个关键字触发，首版支持 `type` 和 `send`
- `<field name="...">` — 提取后写入 history dict 的 key 名
- `<location type="...">` — 复用现有 location 格式（`id` / `css` / `xpath` 等），与 element 定义一致

**Why**: 复用现有 `<location>` 格式，模型解析器改动最小；`trigger` 属性明确区分 type 触发和 send 触发，一个模型可同时定义两种提取规则。

---

### D12-02: send 关键字的 auto_capture — 从接口响应 body 提取

**场景**：接口返回值 body 中包含关键业务字段，用户希望自动提取而无需额外步骤。

**模型定义示例**（接口模型）：

```xml
<model name="LoginAPI" servicename="">
    <element name="_method" type="interface">
        <location type="static">POST</location>
    </element>
    <element name="_url" type="interface">
        <location type="static">http://localhost:8000/api/login</location>
    </element>
    <element name="username" type="interface">
        <location type="field">username</location>
    </element>
    <element name="password" type="interface">
        <location type="field">password</location>
    </element>

    <!-- 新增：从接口响应 body 自动提取 -->
    <auto_capture trigger="send">
        <field name="token" path="data.token"/>
        <field name="userId" path="data.userId"/>
    </auto_capture>
</model>
```

**字段说明**：
- `trigger="send"` — 由 send 关键字触发
- `<field name="..." path="...">` — `path` 为响应 body 的 JSON 路径（点分隔），支持嵌套访问
- 提取结果组装为 dict，作为当前步骤的 `store_return` 值

**接口响应示例**：
```json
{"code": 0, "data": {"token": "abc123", "userId": 42}}
```

提取后 history 写入：
```python
{"token": "abc123", "userId": 42}
```

后续步骤直接使用：
```xml
<field name="Authorization">${Return[-1].token}</field>
```

**Why**: 接口场景的提取来源是响应 body（已有结构化 dict），用 `path` 做 JSON 路径访问比 locator 更自然；与 UI 场景的 `<location>` 区分，语义清晰。

---

### D12-03: type 执行成功后触发 auto_capture（UI）

**决策**: `_batch_type` 完成后检查模型是否有 `trigger="type"` 的 `auto_capture`：
- 有 → 逐字段按 `<location>` 读取元素文本，组装 dict，`store_return(dict)`
- 无 → 维持现有 `store_return(True)` 行为

---

### D12-04: send 执行成功后触发 auto_capture（接口）

**决策**: `send` 完成后检查模型是否有 `trigger="send"` 的 `auto_capture`：
- 有 → 从响应 body dict 按 `path` 逐级取值，组装提取 dict
- 将提取 dict **合并**到原始响应 dict 的顶层，或作为独立 `_capture` 字段，`store_return` 整体结果
- 无 → 维持现有行为（`store_return` 完整响应 dict）

**合并策略**：提取字段直接提升到返回 dict 顶层，同时保留原始响应：

```python
# 原始响应
{"code": 0, "data": {"token": "abc123", "userId": 42}}

# auto_capture 后的 store_return 值
{
    "code": 0,
    "data": {"token": "abc123", "userId": 42},
    "_capture": {"token": "abc123", "userId": 42}
}
```

用户可通过 `${Return[-1]._capture.token}` 或直接 `${Return[-1].data.token}` 访问。

**Why**: 保留完整响应不破坏现有 verify 步骤对响应 body 的引用；`_capture` 作为提取结果的明确入口，语义清晰。

---

### D12-05: auto_capture 失败处理

**决策**: 任一字段提取失败（元素不存在 / JSON path 不存在 / 超时等）：
- 抛出明确异常 `AutoCaptureError`
- 错误信息包含：字段名、locator/path、失败原因
- 不允许 silent fail，不允许返回部分结果

**Why**: 规范 §5.8，提取失败应尽早暴露。

---

## 实施任务

### T12-001: 模型解析器支持 auto_capture 节点
- `model_parser.py` 解析 `<auto_capture trigger="...">` 节点
- UI 字段：解析 `<field name> + <location type>`，复用现有 location 解析逻辑
- 接口字段：解析 `<field name path="...">`
- 返回 `model.auto_capture_type` 和 `model.auto_capture_send`（各为 list[dict] 或 None）

### T12-002: type 执行后触发 UI auto_capture
- `_batch_type` 完成后检查 `model.auto_capture_type`
- 逐字段调用 driver 读取文本（复用现有 get_text 逻辑）
- 组装 dict，`store_return(dict)`

### T12-003: send 执行后触发接口 auto_capture
- `send` 完成后检查 `model.auto_capture_send`
- 从响应 body 按 path 逐级取值
- 将提取结果写入响应 dict 的 `_capture` 字段，`store_return` 整体

### T12-004: 定义 AutoCaptureError
- 统一异常类，包含字段名、来源、失败原因

### T12-005: rodski-demo 补充演示页面和接口
- 表单页面：提交后展示 `resultId`，对应模型定义 `trigger="type"` auto_capture
- 登录接口：响应包含 `token`，对应模型定义 `trigger="send"` auto_capture

### T12-006: 验证用例
- 场景 A（UI 表单提交后自动返回关键值）
- 场景 C（自动提取失败时立即暴露）
- 验收用例 1、2（UI auto_capture）
- 验收用例 6（失败可见报错）
- 新增：send auto_capture 验证（登录后直接使用 `${Return[-1]._capture.token}`）

---

## 验收标准

1. UI 模型定义 `trigger="type"` auto_capture 后，type 执行成功时自动提取字段写入 history
2. 接口模型定义 `trigger="send"` auto_capture 后，send 执行成功时响应 dict 包含 `_capture` 字段
3. 后续步骤可直接使用 `${Return[-1].field}` / `${Return[-1]._capture.field}`，无需额外 `get`
4. 无 auto_capture 定义的模型行为不变
5. 提取失败时抛出 `AutoCaptureError`，不 silent fail
6. 现有回归用例全部通过

---

## 遗留与后续

- 桌面端（OCR 文本提取）的 auto_capture 扩展在后续迭代按需实现
- 结构化日志（Info/Debug 模式）在 iteration-13 完成
