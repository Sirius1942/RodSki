# 11. 视觉定位器（vision / vision_bbox）

> **来源**: RodSki 测试用例编写指南 v3.4  
> 本文档为独立章节，完整指南请见 [TEST_CASE_WRITING_GUIDE.md](../TEST_CASE_WRITING_GUIDE.md)

---


### 11.1 概念

视觉定位器通过 **OmniParser 服务** + **多模态 LLM** 实现语义定位，无需编写 xpath/css 选择器。

**RodSki 职责**：执行 XML 定义的操作，支持视觉定位器  
**Agent 职责**：探索页面，生成包含视觉定位器的 XML

### 11.2 定位器格式

在 `model.xml` 中使用 `locator` 属性：

```xml
<!-- 语义定位 -->
<element name="loginBtn" locator="vision:登录按钮"/>

<!-- 坐标定位（Agent 探索后生成） -->
<element name="submitBtn" locator="vision_bbox:100,200,150,250"/>
```

**格式约束**：
- `vision:描述` — 语义描述，由 LLM 匹配
- `vision_bbox:x1,y1,x2,y2` — 像素坐标（Web）或屏幕绝对坐标（Desktop）

### 11.3 Web 平台完整示例

**model.xml**：
```xml
<models>
  <model name="LoginPage">
    <element name="username" locator="vision:用户名输入框"/>
    <element name="password" locator="vision:密码输入框"/>
    <element name="loginBtn" locator="vision:登录按钮"/>
  </model>
</models>
```

**case.xml**：
```xml
<test_step action="navigate" model="" data="https://example.com/login"/>
<test_step action="type" model="LoginPage" data="L001"/>
```

**data/LoginPage.xml**：
```xml
<row id="L001">
  <field name="username">admin</field>
  <field name="password">admin123</field>
  <field name="loginBtn">click</field>
</row>
```

### 11.4 配置要求

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

### 11.5 适用场景

| 场景 | 推荐定位器 |
|------|-----------|
| 动态 ID/class | vision:描述 |
| 无明显属性的元素 | vision:描述 |
| 跨语言测试 | vision:描述（描述用目标语言） |
| 已知坐标（Agent探索后） | vision_bbox:x,y,w,h |
| 传统 Web 元素 | xpath/css（更快） |


---

