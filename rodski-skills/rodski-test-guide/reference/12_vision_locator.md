<!-- 自动生成 from rodski/docs/TEST_CASE_WRITING_GUIDE.md  请勿手工编辑 -->

## 12. 视觉定位器（vision / vision_bbox）

### 12.1 概念

视觉定位器通过 **OmniParser 服务** + **多模态 LLM** 实现语义定位，无需编写 xpath/css 选择器。

**RodSki 职责**：执行 XML 定义的操作，支持视觉定位器  
**Agent 职责**：探索页面，生成包含视觉定位器的 XML

### 12.2 定位器格式

在 `model.xml` 中使用 `<location type="...">` 子元素：

```xml
<!-- 语义定位 -->
<element name="loginBtn">
    <location type="vision">登录按钮</location>
</element>

<!-- 坐标定位（Agent 探索后生成） -->
<element name="submitBtn">
    <location type="vision_bbox">100,200,150,250</location>
</element>
```

**格式约束**：
- `<location type="vision">描述</location>` — 语义描述，由 LLM 匹配
- `<location type="vision_bbox">x1,y1,x2,y2</location>` — 像素坐标（Web）或屏幕绝对坐标（Desktop）

### 12.3 Web 平台完整示例

**model.xml**：
```xml
<models>
  <model name="LoginPage">
    <element name="username">
        <location type="vision">用户名输入框</location>
    </element>
    <element name="password">
        <location type="vision">密码输入框</location>
    </element>
    <element name="loginBtn">
        <location type="vision">登录按钮</location>
    </element>
  </model>
</models>
```

**case.xml**：
```xml
<test_step action="navigate" model="" data="https://example.com/login"/>
<test_step action="type" model="LoginPage" data="L001"/>
```

**data.sqlite 中的 LoginPage 表**：
```xml
<row id="L001">
  <field name="username">admin</field>
  <field name="password">admin123</field>
  <field name="loginBtn">click</field>
</row>
```

### 12.4 配置要求

**vision_config.yaml**（`rodski/config/vision_config.yaml`）：
```yaml
omniparser:
  url: http://14.103.175.167:7862/parse/
  timeout: 5

llm:
  provider: claude
  model: claude-opus-4-6
  api_key_env: ANTHROPIC_API_KEY
  timeout: 10
```

**环境变量**：
```bash
export ANTHROPIC_API_KEY=your_api_key
```

### 12.5 适用场景

| 场景 | 推荐定位器 |
|------|-----------|
| 动态 ID/class | `<location type="vision">描述</location>` |
| 无明显属性的元素 | `<location type="vision">描述</location>` |
| 跨语言测试 | `<location type="vision">描述</location>`（描述用目标语言） |
| 已知坐标（Agent探索后） | `<location type="vision_bbox">x1,y1,x2,y2</location>` |
| 传统 Web 元素 | xpath/css（更快） |


---
