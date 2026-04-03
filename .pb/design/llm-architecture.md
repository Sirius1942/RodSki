# RodSki LLM 能力统一架构设计

## 一、现状与问题

### 1.1 现有 LLM 能力

| 能力 | 位置 | 配置 | 用途 |
|------|------|------|------|
| 视觉定位 | `rodski/vision/llm_analyzer.py` | `vision_config.yaml` | LLM 分析截图识别 UI 元素 |
| 结果审查 | `rodski/reviewers/llm_reviewer.py` | `llm_config.yaml` | 审查测试结果真实性 |

### 1.2 问题

- 配置分散：两个配置文件，重复配置 API key/model
- 客户端重复：各自实现 OpenAI/Claude 客户端
- 能力孤立：无法复用调用逻辑、提示词、缓存
- 扩展困难：新增能力需重新实现基础设施

---

## 二、与 RodSki 框架的关系

### 2.1 架构定位

```
RodSki 测试框架
│
├── 核心层 (rodski/core/)
│   ├── case_parser.py          # 解析用例 XML
│   ├── model_parser.py         # 解析模型 XML
│   ├── ski_executor.py         # 执行引擎
│   └── keyword_engine.py       # 关键字引擎
│
├── 驱动层 (rodski/drivers/)
│   ├── playwright_driver.py    # Web
│   ├── appium_driver.py        # Mobile
│   └── desktop_driver.py       # Desktop
│
├── LLM 层 (rodski/llm/)        ← 新增：统一 LLM 基础设施
│   ├── client.py               # 统一客户端
│   ├── providers/              # OpenAI/Claude/Azure
│   └── capabilities/           # 可插拔能力
│
└── 增强层 (调用 LLM 层)
    ├── vision/                 # 视觉定位
    └── reviewers/              # 结果审查
```

### 2.2 集成方式

**视觉定位集成**
```
用例: <element locator="vision:登录按钮" action="click"/>
  ↓
model_parser 解析
  ↓
driver.click() → vision.locator.locate()
  ↓
llm.capabilities.VisionLocator → 返回坐标
  ↓
driver 执行点击
```

**结果审查集成**
```
ski_executor 执行完成 → result.xml + 截图
  ↓
reviewers.LLMReviewer.review_result()
  ↓
llm.capabilities.ResultReviewer → 判断
  ↓
生成审查报告
```

### 2.3 依赖关系

- **LLM 模块独立**：不依赖 RodSki 核心，可单独使用
- **增强层依赖 LLM**：vision/reviewers 依赖 llm 模块

---

## 三、统一架构设计

### 3.1 分层架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    RodSki 测试框架                           │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ 视觉定位     │  │ 结果审查     │  │ 智能断言     │ ← 能力层│
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         └─────────────────┴─────────────────┘                │
│                           │                                   │
│         ┌─────────────────▼─────────────────┐                │
│         │  LLM Capability Manager           │ ← 管理层       │
│         │  - 能力注册  - 提示词  - 上下文   │                │
│         └─────────────────┬─────────────────┘                │
│                           │                                   │
│         ┌─────────────────▼─────────────────┐                │
│         │  Unified LLM Client               │ ← 客户端层     │
│         │  - Provider 抽象  - 标准化接口    │                │
│         └─────────────────┬─────────────────┘                │
│                           │                                   │
│         ┌─────────────────▼─────────────────┐                │
│         │  Infrastructure                   │ ← 基础设施     │
│         │  - 配置  - 缓存  - 日志  - Mock   │                │
│         └───────────────────────────────────┘                │
│                           │                                   │
└───────────────────────────┼───────────────────────────────────┘
                            │
                   ┌────────▼────────┐
                   │  External LLM   │
                   │  OpenAI/Claude  │
                   └─────────────────┘
```

### 3.2 目录结构

```
rodski/
├── config/
│   └── llm_config.yaml              # 统一配置
├── llm/                              # LLM 统一模块
│   ├── __init__.py
│   ├── client.py                     # 统一客户端
│   ├── providers/
│   │   ├── base.py
│   │   ├── openai_provider.py
│   │   └── claude_provider.py
│   ├── capabilities/
│   │   ├── base.py
│   │   ├── vision_locator.py
│   │   └── result_reviewer.py
│   ├── prompts/                      # 提示词模板
│   ├── cache.py
│   └── config.py
├── vision/                           # 调用 llm.capabilities
└── reviewers/                        # 调用 llm.capabilities
```

### 3.3 统一配置文件

```yaml
# rodski/config/llm_config.yaml

# 默认配置
default:
  provider: openai
  api_key_env: RODSKI_LLM_API_KEY
  timeout: 30
  max_retries: 3

# Provider 配置
providers:
  openai:
    base_url: https://api.openai.com/v1
    base_key: your-key
    model: gpt-4o
    temperature: 0.1

# 能力配置
capabilities:
  vision_locator:
    profile: openai
    max_tokens: 1024
    enable_cache: true

  result_reviewer:
    profile: openai
    max_tokens: 2000
    enable_vision: true
    max_screenshots: 10

# 缓存配置
cache:
  backend: memory
  ttl: 300
```

### 3.4 核心接口设计

**统一客户端**
```python
class LLMClient:
    def chat(self, messages: List[Dict]) -> str:
        """文本对话"""

    def chat_with_vision(self, messages: List[Dict], images: List[str]) -> str:
        """多模态对话"""
```

**Provider 抽象**
```python
class BaseProvider(ABC):
    @abstractmethod
    def call(self, messages: List[Dict], **kwargs) -> Dict:
        """调用 LLM API"""

    @abstractmethod
    def supports_vision(self) -> bool:
        """是否支持视觉"""
```

**能力抽象**
```python
class BaseCapability(ABC):
    def __init__(self, client: LLMClient, config: Dict):
        self.client = client
        self.config = config

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """执行能力"""
```

### 3.5 调用流程

```
用户代码
   │
   └─→ vision.locator.locate("vision:登录按钮")
          │
          └─→ llm.capabilities.VisionLocator.execute()
                 │
                 ├─→ 加载提示词
                 ├─→ 构建上下文
                 └─→ llm.client.chat_with_vision()
                        │
                        ├─→ 检查缓存
                        ├─→ provider.call()
                        └─→ 返回结果
```

---

## 四、使用示例

### 4.1 视觉定位（用户无感知）

```python
# 测试用例（无需修改）
<element locator="vision:登录按钮" action="click"/>

# 内部实现
from rodski.llm import get_capability
locator = get_capability('vision_locator')
bbox = locator.execute(screenshot=img, query="登录按钮")
```

### 4.2 结果审查

```python
from rodski.llm import get_capability

reviewer = get_capability('result_reviewer')
result = reviewer.execute(
    result_dir="/path/to/result",
    case_xml="/path/to/case.xml"
)
print(result['verdict'])  # PASS/FAIL/SUSPICIOUS
```

---

## 五、迁移方案

### 5.1 分阶段实施

**阶段 1：基础设施（Week 1）**
- 创建 `rodski/llm/` 模块
- 实现配置加载、Provider、统一客户端

**阶段 2：能力迁移（Week 2）**
- 迁移视觉定位到 `llm.capabilities.vision_locator`
- 迁移结果审查到 `llm.capabilities.result_reviewer`
- 保留原接口作为适配器

**阶段 3：优化（Week 3）**
- 实现缓存、日志、测试

### 5.2 向后兼容

```python
# rodski/vision/llm_analyzer.py (适配器)
from rodski.llm.capabilities import VisionLocator

def analyze_screenshot(image, description):
    """保留原接口，内部调用新架构"""
    capability = VisionLocator.from_config()
    return capability.execute(image=image, query=description)
```

---

## 六、总结

### 6.1 核心价值

1. **统一管理**：一个配置，一套客户端
2. **能力复用**：新增能力只需实现 Capability 接口
3. **灵活扩展**：支持多 provider、多场景
4. **向后兼容**：现有代码无需修改

### 6.2 成本估算

| 能力 | 调用频率 | 单次成本 | 月成本（1000用例） |
|------|----------|----------|-------------------|
| 视觉定位 | 每个 vision: | $0.01 | $10-50 |
| 结果审查 | 可选 | $0.05 | $50 |
| **总计** | - | - | **$60-100** |

### 6.3 下一步

1. Review 本设计文档
2. 创建 `rodski/llm/` 骨架
3. 实现基础设施层
4. 迁移现有能力
5. 测试和文档



