# Iteration 06: LLM 能力统一架构 - 需求文档

## 一、背景

### 1.1 现状

RodSki 目前有两个独立的 LLM 应用：

| 能力 | 位置 | 配置 | 问题 |
|------|------|------|------|
| 视觉定位 | `rodski/vision/llm_analyzer.py` | `vision_config.yaml` | 配置分散 |
| 结果审查 | `rodski/reviewers/llm_reviewer.py` | `llm_config.yaml` | 客户端重复 |

### 1.2 视觉定位技术栈

**两阶段架构**
```
截图 → OmniParser → 元素列表 → LLM → 匹配结果
```

**分工**
- **OmniParser**：图像解析，识别所有 UI 元素（文本/图标）+ 坐标
- **LLM**：语义理解，根据用户描述匹配最合适的元素

**示例**
```python
# 1. OmniParser 解析截图
elements = omniparser.parse(screenshot)
# 返回: [{"type": "text", "content": "登录", "bbox": [0.5, 0.6, 0.6, 0.7]}, ...]

# 2. LLM 语义匹配
result = llm.match(query="登录按钮", elements=elements)
# 返回: {"bbox": [0.5, 0.6, 0.6, 0.7], "confidence": 0.95}
```

### 1.3 问题

- 配置分散：两个配置文件，重复配置 API key/model
- 客户端重复：各自实现 OpenAI/Claude 客户端
- 能力孤立：无法复用调用逻辑、提示词、缓存
- 扩展困难：新增能力需重新实现基础设施

---

## 二、功能需求

### FR1: 统一配置管理

**需求描述**
- 单一配置文件 `rodski/config/llm_config.yaml`
- 支持多 provider（OpenAI、Claude、Azure、本地模型）
- 支持多 profile（不同场景使用不同模型）
- 环境变量优先级：`RODSKI_LLM_API_KEY` > 配置文件

**验收标准**
- [ ] 所有 LLM 配置集中在 `llm_config.yaml`
- [ ] 支持至少 2 个 provider（OpenAI + Claude）
- [ ] 环境变量可覆盖配置文件

### FR2: 统一 LLM 客户端

**需求描述**
- 抽象 LLM 接口，屏蔽不同 provider 差异
- 支持文本对话、视觉分析（multimodal）
- 统一错误处理、重试、超时机制

**验收标准**
- [ ] `LLMClient` 提供统一接口
- [ ] 支持 `chat()` 和 `chat_with_vision()`
- [ ] 自动重试失败请求（最多 3 次）

### FR3: 能力模块化

**需求描述**
- 视觉定位：`rodski.llm.capabilities.vision_locator`
- 结果审查：`rodski.llm.capabilities.result_reviewer`
- 智能断言：`rodski.llm.capabilities.smart_assertion`（未来）

**验收标准**
- [ ] 实现 `BaseCapability` 抽象基类
- [ ] 迁移视觉定位能力
- [ ] 迁移结果审查能力
- [ ] 新增能力只需继承 `BaseCapability`

### FR4: 缓存机制

**需求描述**
- 相同输入返回缓存结果（降低成本）
- 支持内存缓存和 Redis
- 可配置 TTL

**验收标准**
- [ ] 实现内存缓存
- [ ] 缓存命中率 > 60%（相同截图+描述）
- [ ] 可配置开启/关闭

### FR5: 日志与监控

**需求描述**
- 记录所有 LLM 调用（请求/响应/耗时）
- 支持调试模式

**验收标准**
- [ ] 记录每次调用的耗时和 token 数
- [ ] 调试模式保存完整对话历史

---

## 三、非功能需求

### NFR1: 向后兼容

**需求描述**
- 现有 `vision:` 定位器无需修改
- 现有 `vision_config.yaml` 平滑迁移

**验收标准**
- [ ] 现有测试用例无需修改
- [ ] 提供配置迁移脚本

### NFR2: 性能

**需求描述**
- LLM 调用不应显著增加测试时间
- 缓存命中时响应 < 100ms

**验收标准**
- [ ] 缓存命中率 > 60%
- [ ] 缓存响应时间 < 100ms

### NFR3: 可测试性

**需求描述**
- Mock LLM 响应用于单元测试
- 离线模式（无 API key 时降级）

**验收标准**
- [ ] 提供 Mock Provider
- [ ] 单元测试覆盖率 > 80%

---

## 四、用例示例

### 用例 1：视觉定位（用户视角）

**场景**：测试人员编写测试用例，使用视觉定位器

**测试用例 XML**
```xml
<case id="login_test" title="用户登录测试">
  <steps>
    <step id="1" keyword="navigate" data="https://example.com/login"/>
    <step id="2" keyword="click" model="LoginPage" element="loginBtn"/>
  </steps>
</case>
```

**页面模型 XML**
```xml
<model id="LoginPage" title="登录页">
  <elements>
    <!-- 传统定位器 -->
    <element name="username" locator="css=#username" action="input"/>

    <!-- 视觉定位器（LLM 驱动） -->
    <element name="loginBtn" locator="vision:登录按钮" action="click"/>

    <!-- OCR 定位器 -->
    <element name="title" locator="ocr:欢迎登录" action="verify"/>
  </elements>
</model>
```

**用户体验**
- 无需修改现有用例
- `vision:` 前缀自动触发 LLM 视觉定位
- 失败时自动降级到传统定位器（如果配置）

### 用例 2：结果审查（命令行）

**场景**：测试执行完成后，使用 LLM 审查结果真实性

**命令行使用**
```bash
# 执行测试
python -m rodski.ski_run cases/login_test.xml

# 审查结果
python -m rodski.reviewers.cli \
  result/run_20260403_084451 \
  cases/login_test.xml
```

**输出示例**
```
正在审查: result/run_20260403_084451
============================================================
审查结果: SUSPICIOUS
置信度: 75%
理由: 虽然测试标记为 PASS，但截图显示登录后页面出现错误提示
发现的问题:
  - 截图 05 显示 "网络连接失败" 提示
  - 日志中有 timeout 警告
============================================================
```

### 用例 3：智能断言（未来）

**场景**：使用 LLM 进行语义断言

**测试用例 XML**
```xml
<case id="checkout_test" title="购物车结算">
  <steps>
    <step id="1" keyword="navigate" data="https://example.com/cart"/>
    <step id="2" keyword="click" model="CartPage" element="checkoutBtn"/>

    <!-- 智能断言：LLM 判断页面状态 -->
    <step id="3" keyword="llm_assert"
          data="页面显示订单确认信息，包含商品列表和总价"/>
  </steps>
</case>
```

**内部实现**
```python
# keyword_engine.py 中新增关键字
def llm_assert(self, data: str):
    """LLM 智能断言"""
    screenshot = self.driver.screenshot()
    asserter = get_capability('smart_assertion')
    result = asserter.execute(
        screenshot=screenshot,
        expected=data
    )
    if not result['passed']:
        raise AssertionError(result['reason'])
```

### 用例 4：Agent 探索模式 - 自动切图

**场景**：Agent 探索页面时，自动识别关键按钮并切图保存

**探索流程**
```python
# agent 探索模式
from rodski.llm import get_capability

# 1. 截取全屏
screenshot = driver.screenshot()

# 2. LLM 识别所有可交互元素
locator = get_capability('vision_locator')
elements = locator.batch_locate(
    screenshot=screenshot,
    queries=["所有按钮", "所有输入框", "所有链接"]
)

# 3. 根据坐标切图保存
for elem in elements:
    x1, y1, x2, y2 = elem['bbox']
    crop_image = screenshot.crop((x1, y1, x2, y2))
    crop_image.save(f"images/{elem['name']}.png")

    # 4. 生成模型 XML
    print(f'<element name="{elem["name"]}" '
          f'locator="vision:{elem["name"]}.png" action="click"/>')
```

**输出示例**
```xml
<!-- 自动生成的页面模型 -->
<model id="LoginPage" title="登录页">
  <elements>
    <!-- 使用切图作为定位器 -->
    <element name="loginBtn" locator="vision:loginBtn.png" action="click"/>
    <element name="registerLink" locator="vision:registerLink.png" action="click"/>
    <element name="usernameInput" locator="vision:usernameInput.png" action="input"/>
  </elements>
</model>
```

**优势**
- 自动化页面建模
- 图片定位器更稳定（不受文字变化影响）
- 可视化元素库

### 用例 5：图片对比定位（未来实现）

**场景**：使用切图作为定位器，通过图片模板匹配查找坐标

**页面模型 XML**
```xml
<model id="LoginPage">
  <elements>
    <!-- 图片路径定位器 -->
    <element name="loginBtn" locator="vision:images/loginBtn.png" action="click"/>
  </elements>
</model>
```

**实现逻辑**
```python
# 检测 locator 是否为图片路径
if locator.startswith("vision:") and locator.endswith(".png"):
    template_path = locator.replace("vision:", "")
    screenshot = driver.screenshot()
    bbox = image_matcher.match(screenshot, template_path)
    return bbox
```

**优势**
- 不依赖 LLM（降低成本）
- 定位速度快
- 适合 UI 稳定的场景

**限制**
- UI 变化时需更新切图
- 对分辨率敏感

**注**：此功能暂不实现，优先级低于 LLM 语义定位


## 五、配置示例

### 5.1 基础配置

```yaml
# rodski/config/llm_config.yaml

default:
  provider: openai
  api_key_env: RODSKI_LLM_API_KEY
  timeout: 30
  max_retries: 3

providers:
  openai:
    base_url: https://api.openai.com/v1
    model: gpt-4o
    temperature: 0.1

  claude:
    base_url: https://api.anthropic.com
    model: claude-opus-4-6
    temperature: 0.1

capabilities:
  vision_locator:
    profile: openai
    max_tokens: 1024
    enable_cache: true
    cache_ttl: 300

  result_reviewer:
    profile: openai
    max_tokens: 2000
    enable_vision: true
    max_screenshots: 10
```

### 5.2 高级配置（多环境）

```yaml
# 开发环境：使用便宜的模型
capabilities:
  vision_locator:
    profile: openai
    model: gpt-4o-mini  # 覆盖 provider 默认模型

# 生产环境：使用高精度模型
capabilities:
  vision_locator:
    profile: claude
    model: claude-opus-4-6
```

---

## 六、成本估算

| 能力 | 调用频率 | 单次成本 | 月成本（1000用例） |
|------|----------|----------|-------------------|
| 视觉定位 | 每个 vision: | $0.01 | $10-50 |
| 结果审查 | 可选 | $0.05 | $50 |
| **总计** | - | - | **$60-100** |

**优化措施**
- 缓存命中率 > 60%，实际成本降低 40%
- 可选启用（默认关闭结果审查）

---

## 七、待讨论问题

1. **降级策略**：LLM 失败时是否自动回退到传统定位器？
2. **成本控制**：是否需要设置每月调用上限？
3. **提示词管理**：提示词是否需要支持多语言？
4. **批量处理**：多个 vision: 定位器是否合并为一次 LLM 调用？
5. **离线模式**：是否支持本地部署的 LLM 模型？







