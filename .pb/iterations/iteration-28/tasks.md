# Iteration 28 任务清单

**版本**: v5.6.0  
**分支**: release/v5.6.0  
**依赖**: iteration-27 完成

---

## T28-001: BaseProvider 增加 call_text() 方法 [0.5h]

### 任务

1. `rodski/llm/providers/base.py` — 新增 `call_text(prompt: str, **kwargs) -> str` 抽象方法
2. `rodski/llm/providers/claude.py` — 实现 `call_text()`，使用 `client.messages.create()` 纯文本模式
3. `rodski/llm/providers/openai.py` — 实现 `call_text()`，使用 `client.chat.completions.create()` 纯文本模式
4. `rodski/llm/client.py` — 新增 `call_text(prompt, **kwargs)` 代理方法
5. 支持 `temperature` 和 `max_tokens` kwargs 覆盖

### 改动文件

| 文件 | 改动 |
|------|------|
| `rodski/llm/providers/base.py` | 新增抽象方法 |
| `rodski/llm/providers/claude.py` | 实现 call_text |
| `rodski/llm/providers/openai.py` | 实现 call_text |
| `rodski/llm/client.py` | 新增代理方法 |

### 验证

```bash
pytest rodski/tests/unit/test_llm_providers.py -v
pytest rodski/tests/unit/test_llm_client.py -v
```

---

## T28-002: 新增 screenshot_verifier 能力 [1.5h]

> 依赖 T28-001。

### 任务

1. **新建** `rodski/llm/capabilities/screenshot_verifier.py`
   - `ScreenshotVerifierCapability` 类
   - `verify(screenshot_path: str, expected: str) -> tuple[bool, str]`
   - 内部：图片 base64 编码 → 构建验证 prompt → `self.client.call_vision()` → 解析响应
   - prompt 模板复用 `ai_verifier.py` 现有逻辑

2. **重构** `rodski/vision/ai_verifier.py`
   - `__init__()` 新增可选参数 `llm_client: LLMClient = None`
   - `verify()` 方法：有 `llm_client` 则委托 capability，否则走原有直接 SDK 逻辑（过渡期）
   - `verify_with_reference()` 保留不动（SSIM 不用 LLM）

3. **注册** capability
   - `rodski/llm/client.py` `get_capability()` 新增 `"screenshot_verifier"` 分支

4. **导出**
   - `rodski/llm/capabilities/__init__.py` 新增导出

### 改动文件

| 文件 | 改动 |
|------|------|
| `rodski/llm/capabilities/screenshot_verifier.py` | **新建** |
| `rodski/llm/capabilities/__init__.py` | 新增导出 |
| `rodski/vision/ai_verifier.py` | 重构，接收 LLMClient |
| `rodski/llm/client.py` | 注册新 capability |

### 验证

```bash
pytest rodski/tests/unit/test_ai_verifier.py -v
# 新增 test_screenshot_verifier_capability.py
```

---

## T28-003: 新增 test_reviewer 能力 [1h]

> 依赖 T28-001。可与 T28-002 并行。

### 任务

1. **新建** `rodski/llm/capabilities/test_reviewer.py`
   - `TestReviewerCapability` 类
   - `review(log: str, result_xml: str, screenshots: list[str], case_xml: str = None) -> dict`
   - prompt 构建逻辑从 `llm_reviewer.py` 迁移
   - 有截图时用 `call_vision()`，无截图时用 `call_text()`
   - reviewer 专属参数（system_prompt, temperature）从 config capabilities 节读取

2. **重构** `rodski/reviewers/llm_reviewer.py`
   - `__init__()` 新增可选参数 `llm_client: LLMClient = None`
   - 有 `llm_client` 则委托 capability，否则走原有 OpenAI 直接调用（过渡期）

3. **注册** capability
   - `rodski/llm/client.py` `get_capability()` 新增 `"test_reviewer"` 分支

### 改动文件

| 文件 | 改动 |
|------|------|
| `rodski/llm/capabilities/test_reviewer.py` | **新建** |
| `rodski/llm/capabilities/__init__.py` | 新增导出 |
| `rodski/reviewers/llm_reviewer.py` | 重构，接收 LLMClient |
| `rodski/llm/client.py` | 注册新 capability |

### 验证

```bash
pytest rodski/tests/unit/test_llm_reviewer.py -v
```

---

## T28-004: llm_analyzer.py 移除遗留回退代码 [0.5h]

> 依赖 T28-002 完成。

### 任务

1. 删除遗留函数：
   - `_call_claude()`, `_call_openai()`, `_call_qwen()`
   - `_load_llm_config()`, `_resolve_api_key()`
   - `_encode_image()`, `_build_prompt()`
   - `_DEFAULT_LLM_CONFIG` 常量, `_CONFIG_PATH` 常量
2. `LLMAnalyzer.__init__()` 移除 `except` fallback 块
3. `LLMAnalyzer.analyze()` 删除 `if self._use_new_arch` 分支，只保留新架构路径

### 改动文件

| 文件 | 改动 |
|------|------|
| `rodski/vision/llm_analyzer.py` | 大量删除遗留代码 |
| `rodski/tests/unit/test_vision_llm.py` | 更新测试（移除旧路径测试） |

### 验证

```bash
pytest rodski/tests/unit/test_vision_llm.py -v
```

---

## T28-005: 合并配置文件 + 更新 diagnosis_engine [1h]

> 依赖 T28-002 + T28-003 完成。

### 任务

1. **合并配置**：将 `vision_config.yaml` 和 `reviewer_config.yaml` 的内容合并到 `llm_config.yaml`

   最终 `llm_config.yaml` 结构：
   ```yaml
   provider: claude
   providers:
     claude: { model, base_url, api_key_env, timeout, max_tokens }
     openai: { model, base_url, api_key_env, timeout, max_tokens }
   capabilities:
     vision_locator: { provider: claude }
     screenshot_verifier: { provider: claude }
     test_reviewer:
       provider: openai
       temperature: 0.1
       max_tokens: 2000
       enable_vision: true
       max_screenshots: 10
       system_prompt: |
         你是一个专业的自动化测试结果审查员...
   omniparser:
     url: http://...
     box_threshold: 0.18
     iou_threshold: 0.7
     timeout: 5
   ```

2. **标记废弃**：
   - `rodski/config/vision_config.yaml` — 文件头加 `# DEPRECATED: 配置已迁移到 llm_config.yaml`
   - `rodski/config/reviewer_config.yaml` — 文件头加 `# DEPRECATED: 配置已迁移到 llm_config.yaml`

3. **更新 config 加载**：
   - `rodski/llm/config.py` `load_config()` 支持读取 `capabilities` 和 `omniparser` 节
   - 每个 capability 可指定独立的 `provider` 覆盖全局默认

4. **更新 diagnosis_engine**：
   - `rodski/core/diagnosis_engine.py` `__init__()` 新增可选 `llm_client: LLMClient` 参数
   - `_try_visual_analysis()` 优先使用 `llm_client.get_capability("screenshot_verifier")`

5. **更新 VisionLocator**：
   - `rodski/vision/locator.py` 中 OmniParser 配置改从 `llm_config.yaml` 的 `omniparser` 节读取

### 改动文件

| 文件 | 改动 |
|------|------|
| `rodski/config/llm_config.yaml` | 合并完整配置 |
| `rodski/config/vision_config.yaml` | 标记 DEPRECATED |
| `rodski/config/reviewer_config.yaml` | 标记 DEPRECATED |
| `rodski/llm/config.py` | 支持新配置结构 |
| `rodski/core/diagnosis_engine.py` | 接收 LLMClient |
| `rodski/vision/locator.py` | OmniParser 配置来源更新 |

### 验证

```bash
pytest rodski/tests/unit/test_llm_config.py -v
pytest rodski/tests/ -v  # 全量回归
```

---

## T28-006: LLM 层审计 [0.5h]

### 验证

```bash
# 直接 SDK 调用审计：应只出现在 llm/providers/ 中
grep -r 'from openai\|import openai\|import anthropic' rodski/ --include="*.py"

# 能力注册验证
python -c "
from rodski.llm import LLMClient
c = LLMClient()
print('vision_locator:', c.get_capability('vision_locator'))
print('screenshot_verifier:', c.get_capability('screenshot_verifier'))
print('test_reviewer:', c.get_capability('test_reviewer'))
"
```

---

## 执行顺序

```
T28-001 (call_text)
    ↓
T28-002 (screenshot_verifier) ──┬── T28-003 (test_reviewer)  [并行]
    ↓                            ↓
T28-004 (移除遗留)              │
    ↓                            ↓
T28-005 (合并配置)  ← 依赖 T28-002 + T28-003
    ↓
T28-006 (审计)
```

## 工时估算

| 任务 | 预估 |
|------|------|
| T28-001 | 0.5h |
| T28-002 | 1.5h |
| T28-003 | 1.0h |
| T28-004 | 0.5h |
| T28-005 | 1.0h |
| T28-006 | 0.5h |
| **合计** | **5h** |
