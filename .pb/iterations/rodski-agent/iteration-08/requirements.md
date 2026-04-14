# Iteration 08: 视觉探索

## 目标

Design Agent 具备页面探索能力，通过 OmniParser 识别页面元素并生成视觉定位器。

## 前置依赖

- Iteration 06（Design Agent 基础）

## 任务列表

### T08-001: OmniParser 客户端封装 (60min)

- **文件**:
  - `rodski-agent/src/rodski_agent/common/omniparser_client.py`
  - `rodski-agent/tests/test_omniparser.py`
- **描述**: 封装 OmniParser HTTP API 调用。`parse_screenshot(image_path)` 返回元素列表 `[{label, bbox, confidence, text}]`。配置从 `agent_config.yaml` 读取 OmniParser URL。超时处理和重试。OmniParser 不可用时抛出 `OmniParserUnavailableError`。
- **验收标准**:
  - [ ] 能正确调用 OmniParser API
  - [ ] 返回结构化的元素列表
  - [ ] 超时和错误处理正确

### T08-002: 截图采集工具 (45min)

- **文件**: `rodski-agent/src/rodski_agent/common/screenshot.py`
- **描述**: `capture_web_page(url, output_path)` 使用 Playwright 截取页面。`capture_desktop(output_path)` 使用 pyautogui 截取桌面。截图存储到临时目录，返回路径。
- **验收标准**:
  - [ ] Web 截图功能可用
  - [ ] 截图文件存在且可读

### T08-003: explore_page 节点 (90min)

- **文件**: `rodski-agent/src/rodski_agent/design/nodes.py`（新增 explore_page 函数）
- **描述**: 实现 `explore_page(state)` 节点。流程：截取页面 -> 调用 OmniParser -> 获取元素列表。将元素列表存入 `state.page_elements`。若 OmniParser 不可用，跳过探索，使用纯 LLM 方式（fallback）。
- **rodski 知识依赖**:
  - `CORE_DESIGN_CONSTRAINTS.md` SS10（视觉定位设计约束 -- OmniParser 为核心）
- **验收标准**:
  - [ ] 能从 URL 探索出页面元素
  - [ ] 元素列表包含 label, bbox, text 信息
  - [ ] OmniParser 不可用时优雅降级

### T08-004: identify_elem 节点 -- LLM 语义增强 (90min)

- **文件**:
  - `rodski-agent/src/rodski_agent/design/nodes.py`（新增 identify_elem 函数）
  - `rodski-agent/src/rodski_agent/design/prompts.py`（新增提示词）
- **描述**: 实现 `identify_elem(state)` 节点。将 OmniParser 识别的元素 + 截图送给 LLM 做语义增强。输出 `enriched_elements`：每个元素带有语义标签（如 "用户名输入框"）和推荐定位器类型。为每个元素选择最佳定位器：有稳定属性则用 xpath/css，无属性则用 vision/ocr。生成 model XML 友好的元素名（遵循 element name = data field name 约束）。
- **rodski 知识依赖**:
  - `rodski_knowledge.LOCATOR_TYPES` -- 12 种定位器类型
  - `CORE_DESIGN_CONSTRAINTS.md` SS2.5（定位器选择策略：传统优先，视觉兜底）
  - `CORE_DESIGN_CONSTRAINTS.md` SS2.4（元素名 = 数据表字段名）
- **验收标准**:
  - [ ] LLM 能正确标注元素语义
  - [ ] 定位器选择策略合理（传统优先，视觉兜底）
  - [ ] 元素名合法（无特殊字符，可用作 data field name）

### T08-005: 更新 Design Graph (45min)

- **文件**:
  - `rodski-agent/src/rodski_agent/design/graph.py`（修改）
  - `rodski-agent/src/rodski_agent/common/state.py`（更新 DesignState）
- **描述**: 在 `analyze_req` 之后添加条件边：有 target_url 则进入 `explore_page` -> `identify_elem`，无 URL 则跳过。`identify_elem` -> `plan_cases`。`plan_cases` 现在可以使用 enriched_elements 信息。更新 DesignState 新增 page_elements、enriched_elements 字段。
- **验收标准**:
  - [ ] 提供 URL 时，图经过探索节点
  - [ ] 不提供 URL 时，跳过探索
  - [ ] 探索结果正确传递给后续节点

### T08-006: 视觉探索测试 (60min)

- **文件**: `rodski-agent/tests/test_vision.py`
- **描述**: Mock OmniParser 返回，测试 explore_page 节点。Mock LLM 返回，测试 identify_elem 节点。测试带 URL 的完整 design 流程。测试 OmniParser 不可用时的降级。
- **验收标准**:
  - [ ] 视觉探索全链路测试覆盖
  - [ ] pytest 全部通过

## 交付物

- OmniParser 集成
- explore_page 和 identify_elem 节点
- 视觉定位器生成能力
- Design Agent 完整图（含视觉探索）

## 约束检查

- [ ] 视觉定位器使用 `<location type="vision/ocr/vision_bbox">值</location>` 格式（SS2.5、SS10.2）
- [ ] 不新增 vision_click、vision_input 等关键字（SS10.7）
- [ ] 视觉定位作为模型定位器类型，不是独立关键字（SS10.1）
- [ ] 定位器选择策略：传统定位器优先，视觉定位作为兜底（SS2.5.4）
- [ ] 生成的 element name 遵循 element name = data field name 约束（SS2.4）
- [ ] OmniParser 不可用时有 fallback 策略（纯 LLM 方式）
- [ ] vision_bbox 坐标格式：Web 用页面像素坐标，Desktop 用屏幕绝对坐标（SS11.3）
