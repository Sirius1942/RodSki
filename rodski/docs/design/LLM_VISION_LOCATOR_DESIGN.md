# RodSki LLM 视觉定位接口设计

**版本**: v1.0
**日期**: 2026-03-25

## 1. 背景与目标

### 1.1 问题
传统 RPA 元素定位方式的痛点：
- **脆弱性**: UI 变化导致定位失效
- **维护成本高**: 需要频繁更新定位器
- **学习曲线**: 需要理解 XPath、CSS Selector 等
- **跨平台差异**: 不同平台定位方式不统一

### 1.2 解决方案
利用 **LLM 视觉模型** (GPT-4V, Claude Vision, Gemini Vision) 实现：
- 自然语言描述元素 ("点击登录按钮")
- 自动识别屏幕截图中的元素位置
- 返回坐标或区域，驱动鼠标/键盘操作

### 1.3 目标
为 RodSki 设计一套**通用的 LLM 视觉定位接口**，支持：
1. 多种 LLM 提供商 (OpenAI, Anthropic, Google, 本地模型)
2. 与现有驱动层无缝集成
3. 降级策略 (LLM 失败时回退到传统定位)
4. 缓存优化 (减少 API 调用成本)

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    KeywordEngine                            │
│  (关键字引擎 - 统一入口)                                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  ElementLocator                             │
│  (元素定位器 - 策略路由)                                      │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Traditional  │  │ LLM Vision   │  │ Hybrid       │      │
│  │ Locator      │  │ Locator      │  │ Locator      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  LLMVisionProvider                          │
│  (LLM 提供商抽象层)                                          │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ OpenAI   │  │ Anthropic│  │ Google   │  │ Local    │   │
│  │ Provider │  │ Provider │  │ Provider │  │ Provider │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  BaseDriver                                 │
│  (驱动层 - 执行操作)                                         │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 核心组件

#### A. ElementLocator (元素定位器)
- 统一的元素定位接口
- 支持多种定位策略
- 自动降级和重试

#### B. LLMVisionProvider (LLM 提供商)
- 抽象 LLM API 调用
- 统一输入输出格式
- 支持多个提供商

#### C. VisionCache (视觉缓存)
- 缓存截图和定位结果
- 减少 API 调用
- 支持过期策略

---

## 3. 接口定义

### 3.1 定位器语法

在 model.xml 中使用 `vision:` 前缀标识 LLM 视觉定位：

```xml
<!-- 传统定位 -->
<element name="loginBtn" locator="id:btn_login" />

<!-- LLM 视觉定位 -->
<element name="loginBtn" locator="vision:蓝色的登录按钮" />
<element name="submitBtn" locator="vision:页面右下角的提交按钮" />
<element name="avatar" locator="vision:用户头像，在页面右上角" />
```

### 3.2 混合定位 (降级策略)

```xml
<!-- 优先使用传统定位，失败时使用 LLM -->
<element name="loginBtn"
         locator="id:btn_login"
         fallback="vision:蓝色的登录按钮" />
```

### 3.3 区域限定

```xml
<!-- 在指定区域内查找 -->
<element name="confirmBtn"
         locator="vision:确认按钮"
         region="x:100,y:200,w:800,h:600" />
```

---

## 4. 核心类设计

### 4.1 ElementLocator

```python
# core/element_locator.py
from typing import Optional, Tuple, Dict, Any
from enum import Enum

class LocatorStrategy(Enum):
    TRADITIONAL = "traditional"  # id, xpath, css
    VISION = "vision"            # LLM 视觉
    HYBRID = "hybrid"            # 混合策略

class ElementLocation:
    """元素位置信息"""
    def __init__(self, x: int, y: int, width: int, height: int,
                 confidence: float = 1.0):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.confidence = confidence

    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)

class ElementLocator:
    """统一元素定位器"""

    def __init__(self, driver, llm_provider=None, cache=None):
        self.driver = driver
        self.llm_provider = llm_provider
        self.cache = cache or VisionCache()

    def locate(self, locator: str, **kwargs) -> Optional[ElementLocation]:
        """定位元素

        Args:
            locator: 定位器字符串
                - "id:btn_login" (传统)
                - "vision:蓝色的登录按钮" (LLM)
            **kwargs: 额外参数 (region, fallback, etc.)

        Returns:
            ElementLocation 或 None
        """
        strategy = self._parse_strategy(locator)

        if strategy == LocatorStrategy.TRADITIONAL:
            return self._locate_traditional(locator, **kwargs)
        elif strategy == LocatorStrategy.VISION:
            return self._locate_vision(locator, **kwargs)
        elif strategy == LocatorStrategy.HYBRID:
            return self._locate_hybrid(locator, **kwargs)

    def _locate_vision(self, locator: str, **kwargs) -> Optional[ElementLocation]:
        """LLM 视觉定位"""
        description = locator.replace("vision:", "").strip()

        # 1. 截图
        screenshot = self._capture_screenshot(kwargs.get("region"))

        # 2. 检查缓存
        cache_key = self._make_cache_key(screenshot, description)
        if cached := self.cache.get(cache_key):
            return cached

        # 3. 调用 LLM
        if not self.llm_provider:
            raise ValueError("LLM provider not configured")

        location = self.llm_provider.locate_element(screenshot, description)

        # 4. 缓存结果
        if location:
            self.cache.set(cache_key, location)

        return location
```

### 4.2 LLMVisionProvider (抽象基类)

```python
# core/llm_vision_provider.py
from abc import ABC, abstractmethod
from typing import Optional
from PIL import Image

class LLMVisionProvider(ABC):
    """LLM 视觉提供商抽象接口"""

    @abstractmethod
    def locate_element(self, screenshot: Image.Image,
                      description: str) -> Optional[ElementLocation]:
        """定位元素

        Args:
            screenshot: 屏幕截图 (PIL Image)
            description: 元素描述 (自然语言)

        Returns:
            ElementLocation 或 None
        """
        pass

    @abstractmethod
    def verify_element(self, screenshot: Image.Image,
                      location: ElementLocation,
                      expected: str) -> bool:
        """验证元素内容

        Args:
            screenshot: 屏幕截图
            location: 元素位置
            expected: 期望内容

        Returns:
            是否匹配
        """
        pass
```

---

## 5. LLM 提供商实现

### 5.1 OpenAI Provider

```python
# core/llm_providers/openai_provider.py
import base64
from io import BytesIO
from openai import OpenAI

class OpenAIVisionProvider(LLMVisionProvider):
    """OpenAI GPT-4V 提供商"""

    SYSTEM_PROMPT = """你是一个 UI 元素定位助手。
用户会给你一张屏幕截图和元素描述，你需要：
1. 找到描述的元素在截图中的位置
2. 返回 JSON 格式: {"x": 100, "y": 200, "width": 80, "height": 40, "confidence": 0.95}
3. 如果找不到，返回 {"found": false}
坐标原点在左上角。"""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def locate_element(self, screenshot: Image.Image,
                      description: str) -> Optional[ElementLocation]:
        # 转换图片为 base64
        buffered = BytesIO()
        screenshot.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()

        # 调用 API
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"请定位: {description}"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_base64}"
                            }
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"}
        )

        # 解析结果
        result = json.loads(response.choices[0].message.content)
        if result.get("found") == False:
            return None

        return ElementLocation(
            x=result["x"],
            y=result["y"],
            width=result["width"],
            height=result["height"],
            confidence=result.get("confidence", 1.0)
        )
```

### 5.2 Anthropic Provider

```python
# core/llm_providers/anthropic_provider.py
import anthropic

class AnthropicVisionProvider(LLMVisionProvider):
    """Anthropic Claude Vision 提供商"""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def locate_element(self, screenshot: Image.Image,
                      description: str) -> Optional[ElementLocation]:
        # 实现类似 OpenAI，使用 Claude API
        pass
```

---

## 6. 缓存策略

### 6.1 VisionCache

```python
# core/vision_cache.py
import hashlib
from typing import Optional
from datetime import datetime, timedelta

class VisionCache:
    """视觉定位缓存"""

    def __init__(self, ttl_seconds: int = 300):
        self._cache = {}
        self._ttl = timedelta(seconds=ttl_seconds)

    def _make_key(self, screenshot: Image.Image, description: str) -> str:
        """生成缓存键"""
        img_hash = hashlib.md5(screenshot.tobytes()).hexdigest()
        desc_hash = hashlib.md5(description.encode()).hexdigest()
        return f"{img_hash}:{desc_hash}"

    def get(self, key: str) -> Optional[ElementLocation]:
        if key in self._cache:
            entry = self._cache[key]
            if datetime.now() - entry["time"] < self._ttl:
                return entry["location"]
            else:
                del self._cache[key]
        return None

    def set(self, key: str, location: ElementLocation):
        self._cache[key] = {
            "location": location,
            "time": datetime.now()
        }
```

---

## 7. 配置管理

### 7.1 配置文件

```yaml
# config/llm_vision.yaml
llm_vision:
  enabled: true
  provider: openai  # openai | anthropic | google | local

  openai:
    api_key: ${OPENAI_API_KEY}
    model: gpt-4o
    base_url: https://api.openai.com/v1

  anthropic:
    api_key: ${ANTHROPIC_API_KEY}
    model: claude-3-5-sonnet-20241022

  cache:
    enabled: true
    ttl_seconds: 300
    max_size: 100

  fallback:
    enabled: true
    retry_traditional: true
```

### 7.2 环境变量

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export RODSKI_LLM_PROVIDER="openai"
```

---

## 8. 关键字集成

### 8.1 扩展现有关键字

```python
# keyword_engine.py
def _kw_click(self, params: Dict) -> bool:
    """点击操作 - 支持 LLM 视觉定位"""
    locator = params.get("locator")

    # 使用 ElementLocator 统一定位
    location = self.element_locator.locate(locator)

    if location:
        # 点击元素中心
        return self.driver.click_at(location.center)
    else:
        raise ElementNotFoundError(f"无法定位元素: {locator}")
```

### 8.2 新增视觉验证关键字

```python
def _kw_vision_verify(self, params: Dict) -> bool:
    """视觉验证

    用法:
    <action keyword="vision_verify"
            description="页面显示欢迎信息"
            expected="true" />
    """
    description = params["description"]
    screenshot = self._capture_screenshot()

    result = self.llm_provider.verify_element(
        screenshot, None, description
    )

    return result == (params.get("expected", "true") == "true")
```

---

## 9. 使用示例

### 9.1 基础用例

```xml
<!-- case/login_vision.xml -->
<case name="登录测试 (LLM 视觉)">
  <action keyword="navigate" url="https://example.com/login" />

  <!-- 使用 LLM 定位输入框 -->
  <action keyword="type" model="LoginPage" data="L001" />

  <!-- 使用 LLM 定位按钮 -->
  <action keyword="click" locator="vision:蓝色的登录按钮" />

  <!-- 视觉验证 -->
  <action keyword="vision_verify"
          description="页面显示用户名"
          expected="true" />
</case>
```

### 9.2 模型定义

```xml
<!-- model/LoginPage.xml -->
<model name="LoginPage" driver_type="web">
  <!-- 混合定位: 优先传统，失败时用 LLM -->
  <element name="username"
           locator="id:username"
           fallback="vision:用户名输入框" />

  <element name="password"
           locator="id:password"
           fallback="vision:密码输入框" />

  <!-- 纯 LLM 定位 -->
  <element name="loginBtn"
           locator="vision:蓝色的登录按钮，在表单底部" />
</model>
```

---

## 10. 成本优化

### 10.1 成本估算

| 提供商 | 模型 | 输入成本 | 输出成本 | 单次调用 |
|--------|------|---------|---------|---------|
| OpenAI | GPT-4o | $2.5/1M tokens | $10/1M tokens | ~$0.01 |
| Anthropic | Claude 3.5 Sonnet | $3/1M tokens | $15/1M tokens | ~$0.01 |
| Google | Gemini 1.5 Pro | $1.25/1M tokens | $5/1M tokens | ~$0.005 |

### 10.2 优化策略

1. **缓存**: 相同截图+描述不重复调用
2. **区域裁剪**: 只发送必要区域，减少图片大小
3. **批量定位**: 一次调用定位多个元素
4. **降级**: 优先使用传统定位，LLM 作为后备
5. **本地模型**: 使用开源视觉模型 (LLaVA, CogVLM)

---

## 11. 实施计划

### Phase 1: 基础框架 (1 周)
- [ ] ElementLocator 接口设计
- [ ] LLMVisionProvider 抽象类
- [ ] VisionCache 实现
- [ ] 配置管理

### Phase 2: OpenAI 集成 (1 周)
- [ ] OpenAIVisionProvider 实现
- [ ] 关键字集成
- [ ] 基础测试用例

### Phase 3: 多提供商支持 (1 周)
- [ ] Anthropic Provider
- [ ] Google Provider
- [ ] 提供商切换逻辑

### Phase 4: 优化与测试 (1 周)
- [ ] 缓存优化
- [ ] 成本监控
- [ ] 完整测试套件
- [ ] 文档编写

**总计**: 约 4 周

---

## 12. 风险与限制

### 12.1 技术风险
- **准确性**: LLM 可能定位错误
- **延迟**: API 调用增加执行时间
- **成本**: 大量调用成本高

### 12.2 缓解措施
- 提供置信度阈值，低于阈值时告警
- 使用缓存和降级策略减少调用
- 提供成本监控和预算限制

---

## 13. 未来扩展

1. **本地模型**: 集成开源视觉模型，零成本
2. **主动学习**: 用户纠正后自动优化
3. **多模态**: 结合 OCR、图像识别等
4. **录制生成**: 录制操作自动生成描述

---

## 附录: Prompt 工程

### A.1 定位 Prompt 模板

```
你是一个 UI 元素定位专家。用户会给你：
1. 一张屏幕截图
2. 元素的自然语言描述

请找到该元素的位置，返回 JSON:
{
  "found": true,
  "x": 100,        // 左上角 x 坐标
  "y": 200,        // 左上角 y 坐标
  "width": 80,     // 宽度
  "height": 40,    // 高度
  "confidence": 0.95  // 置信度 (0-1)
}

如果找不到，返回: {"found": false, "reason": "原因"}

注意:
- 坐标原点在左上角
- 返回元素的边界框 (bounding box)
- 如果有多个匹配，返回最可能的一个
```

### A.2 验证 Prompt 模板

```
你是一个 UI 验证专家。用户会给你：
1. 一张屏幕截图
2. 期望看到的内容描述

请判断截图中是否包含该内容，返回 JSON:
{
  "match": true,
  "confidence": 0.95,
  "reason": "在页面右上角找到了用户头像"
}
```
