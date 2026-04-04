# RodSki LLM 能力统一架构设计

## 一、现状分析

### 1.1 现有 LLM 相关能力

RodSki 目前有三个独立的 LLM 应用场景：

| 能力 | 位置 | 配置文件 | 用途 |
|------|------|----------|------|
| **视觉定位** | `rodski/vision/llm_analyzer.py` | `rodski/config/vision_config.yaml` | 通过 LLM 分析截图，识别 UI 元素位置 |
| **测试结果审查** | `rodski/reviewers/llm_reviewer.py` | `rodski/llm_config.yaml` | 审查测试结果真实性（日志+截图） |
| **未来扩展** | - | - | 智能断言、用例生成、bug 分析等 |

### 1.2 问题

1. **配置分散**：`vision_config.yaml` vs `llm_config.yaml`，重复配置 API key、model 等
2. **客户端重复**：每个模块独立实现 OpenAI/Claude 客户端
3. **能力孤立**：无法复用 LLM 调用逻辑、提示词管理、缓存等
4. **扩展困难**：新增 LLM 能力需要重新实现配置加载、客户端初始化

---

## 二、统一架构需求

### 2.1 功能需求

**FR1: 统一配置管理**
- 单一配置文件 `rodski/config/llm_config.yaml`
- 支持多 provider（OpenAI、Claude、Azure、本地模型）
- 支持多 profile（不同场景使用不同模型/配置）
- 环境变量优先级：`RODSKI_LLM_API_KEY` > 配置文件

**FR2: 统一 LLM 客户端**
- 抽象 LLM 接口，屏蔽不同 provider 差异
- 支持文本对话、视觉分析（multimodal）
- 统一错误处理、重试、超时机制

**FR3: 能力模块化**
- 视觉定位：`rodski.llm.capabilities.vision_locator`
- 结果审查：`rodski.llm.capabilities.result_reviewer`
- 智能断言：`rodski.llm.capabilities.smart_assertion`（未来）
- 用例生成：`rodski.llm.capabilities.case_generator`（未来）

**FR4: 提示词管理**
- 集中管理提示词模板
- 支持变量替换、多语言
- 版本控制和 A/B 测试

**FR5: 性能优化**
- 响应缓存（相同输入返回缓存结果）
- 批量请求支持
- 流式输出（长文本场景）

### 2.2 非功能需求

**NFR1: 向后兼容**
- 现有 `vision:` 定位器无需修改
- 现有 `vision_config.yaml` 平滑迁移

**NFR2: 可测试性**
- Mock LLM 响应用于单元测试
- 离线模式（无 API key 时降级）

**NFR3: 可观测性**
- 记录所有 LLM 调用（请求/响应/耗时/成本）
- 支持调试模式（保存完整对话历史）

---

## 三、与 RodSki 基础框架的关系

### 3.1 架构定位

```
RodSki 测试框架
├── 核心层 (rodski/core/)
│   ├── case_parser.py          # 解析测试用例 XML
│   ├── model_parser.py         # 解析页面模型 XML
│   ├── ski_executor.py         # 执行测试用例
│   └── keyword_engine.py       # 关键字引擎
│
├── 驱动层 (rodski/drivers/)
│   ├── playwright_driver.py    # Web 自动化
│   ├── appium_driver.py        # 移动端自动化
│   └── desktop_driver.py       # 桌面自动化
│
├── LLM 能力层 (rodski/llm/)    ← 新增统一 LLM 模块
│   ├── client.py               # 统一客户端
│   ├── providers/              # 多 provider 支持
│   └── capabilities/           # 可插拔能力
│
└── 增强层 (使用 LLM 能力)
    ├── vision/                 # 视觉定位（调用 llm.capabilities）
    └── reviewers/              # 结果审查（调用 llm.capabilities）
```

### 3.2 集成点

**集成点 1：视觉定位器 → 驱动层**
```
用户用例: <element locator="vision:登录按钮" action="click"/>
    ↓
model_parser 解析 → locator="vision:登录按钮"
    ↓
driver.click() → vision.locator.locate()
    ↓
llm.capabilities.VisionLocator → 返回坐标
    ↓
driver 执行点击操作
```

**集成点 2：结果审查 → 测试报告**
```
ski_executor 执行完成 → 生成 result.xml + 截图
    ↓
（可选）reviewers.LLMReviewer.review_result()
    ↓
llm.capabilities.ResultReviewer → 审查判断
    ↓
生成审查报告 → 附加到测试结果
```

### 3.3 依赖关系

- **LLM 模块独立**：不依赖 RodSki 核心，可单独使用
- **增强层依赖 LLM**：vision/reviewers 依赖 llm 模块
- **核心层可选依赖**：核心功能不依赖 LLM，LLM 是增强能力

---

### 3.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        RodSki 测试框架                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ 视觉定位      │  │ 结果审查      │  │ 智能断言      │  ← 能力层 │
│  │ VisionLocator│  │ResultReviewer│  │SmartAssertion│          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                  │                  │                   │
│         └──────────────────┴──────────────────┘                  │
│                            │                                      │
│         ┌──────────────────▼──────────────────┐                  │
│         │   LLM Capability Manager            │  ← 能力管理层    │
│         │  - 能力注册/发现                     │                  │
│         │  - 提示词模板管理                    │                  │
│         │  - 上下文构建                        │                  │
│         └──────────────────┬──────────────────┘                  │
│                            │                                      │
│         ┌──────────────────▼──────────────────┐                  │
│         │   Unified LLM Client                │  ← 客户端层      │
│         │  - Provider 抽象 (OpenAI/Claude)    │                  │
│         │  - 请求/响应标准化                   │                  │
│         │  - 错误处理/重试                     │                  │
│         └──────────────────┬──────────────────┘                  │
│                            │                                      │
│         ┌──────────────────▼──────────────────┐                  │
│         │   Infrastructure Layer              │  ← 基础设施层    │
│         │  - 配置管理 (llm_config.yaml)       │                  │
│         │  - 缓存 (Redis/内存)                │                  │
│         │  - 日志/监控                         │                  │
│         │  - Mock/测试支持                     │                  │
│         └─────────────────────────────────────┘                  │
│                            │                                      │
└────────────────────────────┼──────────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  External LLM   │
                    │  - OpenAI API   │
                    │  - Claude API   │
                    │  - 本地模型      │
                    └─────────────────┘
```

### 3.2 目录结构

```
rodski/
├── config/
│   └── llm_config.yaml              # 统一 LLM 配置
├── llm/                              # LLM 统一模块
│   ├── __init__.py
│   ├── client.py                     # 统一客户端接口
│   ├── providers/                    # Provider 实现
│   │   ├── __init__.py
│   │   ├── base.py                   # Provider 抽象基类
│   │   ├── openai_provider.py
│   │   ├── claude_provider.py
│   │   └── azure_provider.py
│   ├── capabilities/                 # 能力模块
│   │   ├── __init__.py
│   │   ├── base.py                   # Capability 抽象基类
│   │   ├── vision_locator.py         # 视觉定位能力
│   │   ├── result_reviewer.py        # 结果审查能力
│   │   └── smart_assertion.py        # 智能断言能力（未来）
│   ├── prompts/                      # 提示词模板
│   │   ├── vision_locator.txt
│   │   ├── result_reviewer.txt
│   │   └── smart_assertion.txt
│   ├── cache.py                      # 缓存管理
│   ├── config.py                     # 配置加载
│   └── telemetry.py                  # 日志/监控
├── vision/                           # 视觉模块（保留，调用 llm.capabilities）
│   ├── locator.py                    # 调用 llm.capabilities.vision_locator
│   └── llm_analyzer.py               # 废弃或重构为适配器
└── reviewers/                        # 审查模块（保留，调用 llm.capabilities）
    └── llm_reviewer.py               # 调用 llm.capabilities.result_reviewer
```

### 3.3 核心组件设计

#### 3.3.1 统一配置文件 (`llm_config.yaml`)

```yaml
# 全局默认配置
default:
  provider: openai
  api_key_env: RODSKI_LLM_API_KEY
  timeout: 30
  max_retries: 3

# Provider 配置
providers:
  openai:
    base_url: https://api.openai.com/v1
    model: gpt-4o
    temperature: 0.1

  claude:
    base_url: https://api.anthropic.com
    model: claude-opus-4-6
    temperature: 0.1

  azure:
    base_url: https://your-resource.openai.azure.com
    api_version: 2024-02-01
    deployment_name: gpt-4

# 能力配置（不同能力可使用不同 profile）
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

  smart_assertion:
    profile: claude
    max_tokens: 512

# 缓存配置
cache:
  backend: memory  # memory | redis
  redis_url: redis://localhost:6379/0

# 监控配置
telemetry:
  enabled: true
  log_requests: true
  log_responses: false  # 避免敏感信息泄露
```

#### 3.3.2 统一客户端接口

```python
# rodski/llm/client.py
class LLMClient:
    """统一 LLM 客户端，屏蔽不同 provider 差异"""

    def chat(self, messages: List[Dict], **kwargs) -> str:
        """文本对话"""

    def chat_with_vision(self, messages: List[Dict], images: List[str], **kwargs) -> str:
        """多模态对话（文本+图片）"""

    def stream_chat(self, messages: List[Dict], **kwargs) -> Iterator[str]:
        """流式对话"""
```

#### 3.3.3 Provider 抽象

```python
# rodski/llm/providers/base.py
class BaseProvider(ABC):
    """LLM Provider 抽象基类"""

    @abstractmethod
    def call(self, messages: List[Dict], **kwargs) -> Dict:
        """调用 LLM API"""

    @abstractmethod
    def supports_vision(self) -> bool:
        """是否支持视觉能力"""
```

#### 3.3.4 能力抽象

```python
# rodski/llm/capabilities/base.py
class BaseCapability(ABC):
    """LLM 能力抽象基类"""

    def __init__(self, client: LLMClient, config: Dict):
        self.client = client
        self.config = config

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """执行能力"""
```

### 3.4 调用流程图

```
用户代码
   │
   ├─→ vision.locator.locate("vision:登录按钮")
   │      │
   │      └─→ llm.capabilities.VisionLocator.execute()
   │             │
   │             ├─→ 加载提示词模板
   │             ├─→ 构建上下文（截图+描述）
   │             └─→ llm.client.chat_with_vision()
   │                    │
   │                    ├─→ 检查缓存
   │                    ├─→ providers.OpenAIProvider.call()
   │                    ├─→ 记录日志/监控
   │                    └─→ 返回结果
   │
   └─→ reviewers.LLMReviewer.review_result()
          │
          └─→ llm.capabilities.ResultReviewer.execute()
                 │
                 └─→ llm.client.chat_with_vision()
```

---

## 四、迁移方案

### 4.1 迁移步骤

**阶段 1：基础设施层（Week 1）**
1. 创建 `rodski/llm/` 目录结构
2. 实现统一配置加载 `config.py`
3. 实现 Provider 抽象和 OpenAI/Claude 实现
4. 实现统一客户端 `LLMClient`

**阶段 2：能力迁移（Week 2）**
1. 迁移视觉定位能力到 `llm.capabilities.vision_locator`
2. 迁移结果审查能力到 `llm.capabilities.result_reviewer`
3. 保留原有接口作为适配器（向后兼容）

**阶段 3：优化增强（Week 3）**
1. 实现缓存机制
2. 实现日志/监控
3. 添加单元测试和集成测试

### 4.2 兼容性保证

```python
# rodski/vision/llm_analyzer.py (适配器模式)
from rodski.llm.capabilities import VisionLocator

def analyze_screenshot(image_path, description):
    """保留原有接口，内部调用新架构"""
    capability = VisionLocator.from_config()
    return capability.execute(image=image_path, query=description)
```

---
