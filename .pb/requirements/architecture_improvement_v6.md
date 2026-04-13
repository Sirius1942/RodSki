# RodSki 架构改进设计与需求文档

**版本**: v6.0  
**日期**: 2026-04-13  
**来源**: Agent 架构评审（`.pb/design/agent_architecture_review_20260413.md`）  
**状态**: 待审批

---

## 1. 背景与目标

### 1.1 评审结论

经过架构评审，确认 RodSki 存在 5 个核心问题：

1. **产品定位不统一** — README 说的是传统测试框架，AGENT_INTEGRATION 说的是 Agent 执行引擎
2. **文档契约不一致** — 定位器格式、元素定义格式在多个文档中互相矛盾，对 Agent 致命
3. **Excel/XML 双叙事** — 代码已全面 XML 化，但文档和依赖仍残留 Excel 引用
4. **LLM 能力分散** — 有统一 LLMClient 但多处直接调 SDK，3 个配置文件
5. **Agent 示例不是产品能力** — examples/agent/ 只是参考示例，不应作为正式框架能力

### 1.2 改进目标

将 RodSki 从"定位模糊的测试框架"收敛为：

> **面向 AI Agent 的跨平台确定性执行引擎 + 活文档协议层**

### 1.3 用户决策

| # | 问题 | 决策 |
|---|------|------|
| P1 | 定位不统一 | 主定位 = AI Agent 执行内核 + 活文档协议，修改相关文档 |
| P2 | 契约不一致 | 统一为 `<location>` 格式，**代码+文档都改**，去掉简化写法，不向后兼容 |
| P3 | Excel 残留 | 去掉 Excel，统一 XML，包括代码、文档、依赖全部删除 |
| P4 | LLM 分散 | 统一到 LLMClient，3 个配置合并为 1 个 `llm_config.yaml` |
| P5 | Agent 示例 | 移到 `.pb/archive/` 归档，后续独立子项目实现 |

### 1.4 设计原则（用户确认）

1. **不做 Agent 框架** — RodSki 是 Agent 的"工具"和"协议"，不是 Agent 本身
2. **契约第一优先** — 输入/输出格式必须唯一、稳定、Agent 友好
3. **AI 能力可选层** — 核心执行层保持确定性，LLM 能力可插拔
4. **强化 Agent 接口** — run/validate/explain/dry-run 等正式能力
5. **文档围绕 Agent 友好** — 叙事统一，示例是示例，规范是规范

---

## 2. 改进概览

| Phase | 内容 | 工作项 | 说明 |
|-------|------|--------|------|
| Phase 0 | 契约统一 | WI-01 ~ WI-04 | 最高优先级，定位器格式统一 |
| Phase 1 | 清理历史包袱 | WI-05 ~ WI-07 | Excel 移除 + Agent 示例归档 |
| Phase 2 | LLM 统一服务层 | WI-08 ~ WI-12 | 统一 LLM 调用和配置 |
| Phase 3 | 定位叙事统一 | WI-13 ~ WI-15 | README 重写 + 文档统一叙事 |

---

## 3. Phase 0: 契约统一（P2 — 最高优先级）

### WI-01: model_parser.py 移除旧定位器格式 [M]

**目标**：只保留 `<location type="...">value</location>` 多定位器格式。

**改动文件**：
- `rodski/core/model_parser.py`
  - 删除 `locator` 属性解析（lines 143-164）
  - 删除 `type+value` 简化格式解析（lines 195-209）
  - 保留 `<location>` 子元素解析（lines 166-193）
  - `<element type="web">` 的 type 仅表示 driver 类型，不再有 locator 含义

**Breaking Change**：所有使用旧格式的 XML 文件将不可用，须先完成 WI-02。

**验证**：`pytest rodski/tests/unit/test_model_parser.py`（需同步更新测试用例）

---

### WI-02: 迁移所有 model XML 到 `<location>` 格式 [M]

**目标**：所有项目内 XML 文件使用唯一定位器格式。

**改动文件**：
- `rodski-demo/DEMO/vision_desktop/model/model.xml` — 15 个元素
- `rodski-demo/DEMO/vision_web/model/model.xml` — 3 个元素
- `rodski-demo/` 下所有其他 model.xml
- `cassmall/` 下所有 model.xml（如有旧格式）

**转换规则**：

```xml
<!-- Before: locator 属性 -->
<element name="textArea" locator="vision:文本编辑区域"/>
<!-- After: location 子元素 -->
<element name="textArea">
  <location type="vision">文本编辑区域</location>
</element>

<!-- Before: type+value 简化 -->
<element name="usernameById" type="id" value="userName" desc="..."/>
<!-- After: location 子元素 -->
<element name="usernameById">
  <location type="id">userName</location>
  <desc>...</desc>
</element>
```

**验证**：更新后的 XML 能被 WI-01 修改后的 ModelParser 正确解析。

---

### WI-03: vision/locator.py 移除旧前缀解析 [S]

**依赖**：WI-01

**改动文件**：
- `rodski/vision/locator.py`
  - `locate_legacy()` / `locate_with_driver()` 添加 deprecation warning
  - `is_vision_locator(locator_str)` 前缀检查方法标记废弃
  - 保留 `locate(locator_type, locator_value, screenshot)` 作为唯一 API

**验证**：`pytest rodski/tests/unit/test_vision_locator.py`

---

### WI-04: 统一所有文档到 `<location>` 格式 [L]

**依赖**：WI-01, WI-02

**需要核对修改的文档清单**：

| 文档 | 问题位置 | 要改的内容 |
|------|---------|-----------|
| `rodski/docs/AGENT_INTEGRATION.md` | lines 94-103, 382-408 | `locator="vision:xxx"` → `<location>` 格式 |
| `rodski/docs/VISION_LOCATION.md` | lines 25-39, 51, 109-139 | 全文 `locator="..."` → `<location>` 格式 |
| `rodski/docs/TEST_CASE_WRITING_GUIDE.md` | lines 1099-1207 | 第 11 节视觉定位示例全部更新 |
| `rodski/docs/CORE_DESIGN_CONSTRAINTS.md` | line 194 | 删除简化格式"正确"标记，标注为已移除 |
| `rodski/docs/ADVANCED_TIPS.md` | lines 55-108 | 删除单定位器简化写法，只保留 `<location>` |
| `rodski/docs/SKILL_REFERENCE.md` | 全文检查 | 确保无旧格式 |
| `rodski/docs/API_REFERENCE.md` | 全文检查 | 确保无旧格式 |

**验证**：`grep -r 'locator="' rodski/docs/` 返回零结果。

---

## 4. Phase 1: 移除历史包袱（P3 + P5）

### WI-05: 移除 Excel 相关代码 [S]

**改动文件**：

| 文件 | 改动 |
|------|------|
| `rodski/requirements.txt` line 1 | 删除 `openpyxl>=3.1.0` |
| `rodski/tests/conftest.py` line 7 | 删除 openpyxl warning filter |
| `rodski/rodski_cli/run.py` help text | `.xlsx` → `.xml` |
| `rodski/tests/unit/test_cli_ux.py` | `.xlsx` → `.xml` |
| `rodski/tests/unit/test_keyword_engine.py` | `.xlsx` → `.xml` |
| `rodski/tests/integration/test_cli_commands.py` | `.xlsx` → `.xml` |
| `rodski/core/result_writer.py` line 3 | 更新注释去掉 Excel 引用 |
| `rodski/core/ski_executor.py` line 3 | 更新注释去掉 Excel 引用 |
| `rodski/core/global_value_parser.py` line 3 | 更新注释去掉 Excel 引用 |

**验证**：`grep -r "xlsx\|openpyxl" rodski/ --include="*.py"` 返回零结果。

---

### WI-06: 移除文档中所有 Excel 引用 [M]

**改动文件**：

| 文档 | 改动 |
|------|------|
| `README.md` | `rodski run case.xlsx` → `rodski run case/` |
| `rodski/docs/ARCHITECTURE.md` | 移除 Excel 文件结构图、excel_parser.py 引用、CLI .xlsx 示例 |
| `rodski/docs/TEST_CASE_WRITING_GUIDE.md` | Excel 映射节标记为历史或删除 |
| `rodski/docs/json_support_design.md` | "Excel 数据表" → "XML 数据表" |

**验证**：`grep -ri "excel\|\.xlsx" rodski/docs/ README.md` 返回零结果。

---

### WI-07: Agent 示例归档 [S]

**操作**：
```
rodski/examples/agent/  →  .pb/archive/agent_examples/
```

**移动文件**：
- `multi_agent_example.py`
- `claude_code_integration.py`
- `opencode_integration.py`
- `README.md`

**后续**：更新引用这些文件的文档。

**验证**：`rodski/examples/agent/` 目录不存在。

---

## 5. Phase 2: LLM 统一服务层（P4）

### WI-08: BaseProvider 增加 call_text() 方法 [S]

**改动文件**：
- `rodski/llm/providers/base.py` — 新增 `call_text(prompt, **kwargs)` 抽象方法
- `rodski/llm/providers/claude.py` — 实现 `call_text()`
- `rodski/llm/providers/openai.py` — 实现 `call_text()`
- `rodski/llm/client.py` — 新增 `call_text()` 代理方法

---

### WI-09: 新增 screenshot_verifier 能力 [M]

**依赖**：WI-08

**新建文件**：
- `rodski/llm/capabilities/screenshot_verifier.py`
  - `ScreenshotVerifierCapability`
  - `verify(screenshot_path, expected) -> (bool, str)`

**重构文件**：
- `rodski/vision/ai_verifier.py` — 接收 `LLMClient`，委托给 capability
- `rodski/llm/client.py` — 注册 `screenshot_verifier` capability

---

### WI-10: 新增 test_reviewer 能力 [M]

**依赖**：WI-08

**新建文件**：
- `rodski/llm/capabilities/test_reviewer.py`
  - `TestReviewerCapability`
  - `review(log, result_xml, screenshots, case_xml) -> dict`

**重构文件**：
- `rodski/reviewers/llm_reviewer.py` — 接收 `LLMClient`，委托给 capability

---

### WI-11: llm_analyzer.py 移除遗留回退代码 [S]

**依赖**：WI-09

**改动文件**：
- `rodski/vision/llm_analyzer.py`
  - 删除 `_call_claude()`, `_call_openai()`, `_call_qwen()` 遗留函数
  - 删除 `_load_llm_config()`, `_resolve_api_key()` 等遗留辅助
  - 删除 `_DEFAULT_LLM_CONFIG` 常量
  - `LLMAnalyzer.analyze()` 只走 LLMClient 路径

---

### WI-12: 合并配置文件 + 更新 diagnosis_engine [M]

**依赖**：WI-09, WI-10

**合并后 llm_config.yaml 结构**：

```yaml
provider: claude
providers:
  claude:
    model: claude-opus-4-6
    base_url: ""
    api_key_env: ANTHROPIC_API_KEY
    timeout: 10
    max_tokens: 1024
  openai:
    model: gpt-4o
    base_url: ""
    api_key_env: OPENAI_API_KEY
    timeout: 10
    max_tokens: 2000

capabilities:
  vision_locator:
    provider: claude
  screenshot_verifier:
    provider: claude
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

**改动文件**：
- `rodski/config/llm_config.yaml` — 合并后的完整配置
- `rodski/config/vision_config.yaml` — 标记 DEPRECATED
- `rodski/config/reviewer_config.yaml` — 标记 DEPRECATED
- `rodski/llm/config.py` — 支持加载 `omniparser` 和 `capabilities` 节
- `rodski/core/diagnosis_engine.py` — 支持接收 `LLMClient`

---

## 6. Phase 3: 定位叙事统一（P1）

### WI-13: 重写 README.md [M]

**依赖**：WI-04, WI-06

**核心改动**：
- 标题/定位：从"关键字驱动测试框架" → "面向 AI Agent 的跨平台确定性执行引擎"
- 特性列表：围绕 Agent 协议重写（结构化 XML 协议、多平台执行、视觉定位、Agent 友好 CLI、活文档模式）
- 快速开始：展示 Agent 集成流，不是手动测试流
- CLI 示例：`rodski run case/ --output-format json`

---

### WI-14: 重写 AGENT_INTEGRATION.md 为主入口文档 [L]

**依赖**：WI-04, WI-13

**核心改动**：
- 所有 XML 示例使用 `<location>` 格式
- 新增 "Agent 接口契约" 节（CLI 命令、输入格式、输出格式）
- 新增 dry-run / validate / explain 使用说明
- 强调 RodSki 是工具/协议，不是 Agent 框架

---

### WI-15: 其他文档叙事统一 [M]

**依赖**：WI-13, WI-14

**改动文件**：
- `rodski/docs/ARCHITECTURE.md` — 从"测试框架架构"改为"执行引擎架构"
- `rodski/docs/CORE_DESIGN_CONSTRAINTS.md` — 新增 Agent 契约子节
- `CLAUDE.md` — 更新项目描述
- `rodski/docs/SKILL_REFERENCE.md` — 确保 Agent 友好叙事

---

## 7. 依赖关系图

```
Phase 0 (契约):
  WI-01 ──┬── WI-02 (并行)
           │
           ├── WI-03 (WI-01 之后)
           └── WI-04 (WI-01 + WI-02 之后)

Phase 1 (清理):              ← 可与 Phase 0 并行
  WI-05 ── WI-06 ── WI-07   (三个并行)

Phase 2 (LLM 统一):
  WI-08 ──┬── WI-09 ── WI-11
           └── WI-10
           WI-12 (WI-09 + WI-10 之后)

Phase 3 (定位):
  WI-13 ── WI-14 ── WI-15
```

---

## 8. 工作量估算

| WI | 名称 | 大小 | Phase |
|----|------|------|-------|
| WI-01 | model_parser 移除旧格式 | M | 0 |
| WI-02 | 迁移 XML 文件 | M | 0 |
| WI-03 | vision/locator 移除旧 API | S | 0 |
| WI-04 | 文档格式统一 | L | 0 |
| WI-05 | 移除 Excel 代码 | S | 1 |
| WI-06 | 移除 Excel 文档 | M | 1 |
| WI-07 | Agent 示例归档 | S | 1 |
| WI-08 | Provider 增加 call_text | S | 2 |
| WI-09 | screenshot_verifier 能力 | M | 2 |
| WI-10 | test_reviewer 能力 | M | 2 |
| WI-11 | llm_analyzer 移除遗留 | S | 2 |
| WI-12 | 合并配置 + diagnosis | M | 2 |
| WI-13 | 重写 README | M | 3 |
| WI-14 | 重写 AGENT_INTEGRATION | L | 3 |
| WI-15 | 其他文档统一 | M | 3 |

**合计**：4S + 7M + 2L = 15 个工作项

---

## 9. 风险分析

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| WI-01 是 Breaking Change | 所有旧格式 XML 失效 | WI-02 必须同批次提交，测试全部更新 |
| WI-09/10 新能力可能初始化失败 | 现有调用方中断 | 过渡期保留 fallback，WI-11 确认后再移除 |
| 文档量大，遗漏可能 | Agent 仍学到错误格式 | 用 grep 审计验证，确保零残留 |

---

## 10. 验证方案

1. **单元测试**：每个 WI 完成后运行相关 pytest
2. **全量回归**：Phase 0 完成后 `pytest rodski/tests/`
3. **格式审计**：
   - `grep -r 'locator="' rodski/ --include="*.xml" --include="*.md"` → 零结果
   - `grep -ri 'excel\|\.xlsx' rodski/ --include="*.py" --include="*.md"` → 零结果
   - `grep -r 'from openai\|import openai\|import anthropic' rodski/ --include="*.py"` → 仅在 `llm/providers/`
4. **XML 解析**：所有 rodski-demo/ 下的 model.xml 能被更新后的 ModelParser 正确解析
5. **LLM 能力**：`LLMClient.get_capability("screenshot_verifier")` 和 `get_capability("test_reviewer")` 正常返回

---

## 11. 关键文件索引

| 文件 | 涉及 WI |
|------|---------|
| `rodski/core/model_parser.py` | WI-01 |
| `rodski/vision/locator.py` | WI-03 |
| `rodski/llm/client.py` | WI-08, WI-09, WI-10, WI-12 |
| `rodski/llm/config.py` | WI-12 |
| `rodski/vision/ai_verifier.py` | WI-09 |
| `rodski/reviewers/llm_reviewer.py` | WI-10 |
| `rodski/vision/llm_analyzer.py` | WI-11 |
| `rodski/core/diagnosis_engine.py` | WI-12 |
| `rodski/config/llm_config.yaml` | WI-12 |
| `README.md` | WI-06, WI-13 |
| `rodski/docs/AGENT_INTEGRATION.md` | WI-04, WI-14 |
| `rodski/docs/VISION_LOCATION.md` | WI-04 |
| `rodski/docs/ARCHITECTURE.md` | WI-06, WI-15 |
