# RodSki 视觉定位能力开发任务（v4）

**版本**: v4.0
**日期**: 2026-03-26
**修正说明**: 按核心设计约束 v3.6 调整，统一定位器格式，明确桌面平台约束

---

## 核心原则

1. **RodSki 是执行层**，不是 Agent
2. **Agent 负责探索**，使用自己的视觉能力
3. **RodSki 执行 XML**，支持视觉定位器（`locator="vision:描述"` 格式）
4. **桌面操作通过 `run` 实现**，不新增独立关键字
5. **提供辅助工具**，帮助 Agent 生成 XML

---

## 设计约束对齐

### 定位器格式统一
- ✅ `locator="vision:登录按钮"`（语义定位）
- ✅ `locator="vision_bbox:100,200,150,250"`（坐标定位）
- ❌ 不使用 `type="vision" value="..."`

### 桌面平台
- ✅ `driver_type="windows"` / `driver_type="macos"`
- ✅ `vision_bbox` = 屏幕绝对坐标
- ✅ 桌面应用默认全屏执行
- ❌ 桌面端不支持接口测试（无 `send`）

### 关键字约束
- ✅ 使用 `launch` 启动桌面应用（与 `navigate` 功能相同，场景不同）
- ✅ 桌面操作（剪贴板/组合键/窗口）通过 `run` 调用脚本
- ❌ 不新增 `clipboard`、`key_combination`、`window` 等关键字

---

## 阶段一：基础服务集成（P0）

### Task 1.1: OmniParser 客户端封装
**优先级**: P0
**预计工时**: 2h

**目标**：封装 OmniParser HTTP 调用

**交付物**：
- `rodski/vision/omni_client.py`
- 单元测试

**验收标准**：
- 成功调用服务
- 正确解析元素列表
- 超时控制（5秒）

---

### Task 1.2: 坐标工具（Web + Desktop）
**优先级**: P0
**预计工时**: 1.5h

**目标**：支持 Web 像素坐标和 Desktop 屏幕绝对坐标

**交付物**：
- `rodski/vision/coordinate_utils.py`

**验收标准**：
- Web: 归一化坐标 → 像素坐标
- Desktop: 屏幕绝对坐标处理
- 边界情况处理

---

### Task 1.3: 截图工具（多平台）
**优先级**: P0
**预计工时**: 2h

**目标**：支持 Web / Desktop 截图

**交付物**：
- `rodski/vision/screenshot.py`

**验收标准**：
- Web: 浏览器截图
- Desktop: 全屏截图（Windows/macOS）
- 自动清理旧截图

---

## 阶段二：LLM 语义识别（P0）

### Task 2.1: 多模态 LLM 客户端
**优先级**: P0
**预计工时**: 3h

**目标**：支持 Claude/GPT-4V/Qwen-VL，可配置 base_url、api_key、model

**交付物**：
- `rodski/vision/llm_analyzer.py`
- `rodski/config/vision_config.yaml`

**验收标准**：
- 识别元素类型
- 生成语义标签
- 超时控制（10秒）
- 配置文件生效

---

### Task 2.2: 目标匹配算法
**优先级**: P0
**预计工时**: 2h

**目标**：根据 `vision:描述` 匹配元素

**交付物**：
- `rodski/vision/matcher.py`

**验收标准**：
- 准确匹配目标
- 返回置信度
- 多匹配返回候选

---

## 阶段三：定位器集成（P0）

### Task 3.1: model.xsd 扩展
**优先级**: P0
**预计工时**: 1h

**目标**：支持 `locator="vision:..."` 和 `locator="vision_bbox:..."`

**交付物**：
- 修改 `rodski/schemas/model.xsd`

**验收标准**：
- XSD 校验通过
- 向后兼容现有定位器
- 支持新格式 `locator` 属性

---

### Task 3.2: BaseDriver 定位体系扩展
**优先级**: P0
**预计工时**: 4h

**目标**：扩展 `_locate_element()` 方法支持视觉定位

**交付物**：
- 修改 `drivers/base_driver.py`
- `rodski/vision/locator.py`

**验收标准**：
- `vision:描述` 语义定位成功
- `vision_bbox:x,y,w,h` 坐标定位成功
- 缓存机制生效

---

### Task 3.3: 桌面坐标驱动器
**优先级**: P0
**预计工时**: 3h

**目标**：支持 Windows/macOS 屏幕绝对坐标操作

**交付物**：
- `rodski/vision/desktop_driver.py`

**验收标准**：
- Windows: pyautogui 坐标点击
- macOS: pyautogui 坐标点击
- 坐标准确性验证

---

## 阶段四：桌面操作脚本库（P1）

### Task 4.1: 桌面操作脚本模板
**优先级**: P1
**预计工时**: 3h

**目标**：提供常用桌面操作脚本（通过 `run` 调用）

**交付物**：
- `fun/desktop/clipboard_copy.py`
- `fun/desktop/clipboard_paste.py`
- `fun/desktop/key_combo.py`
- `fun/desktop/switch_window.py`

**验收标准**：
- Windows/macOS 双平台支持
- 返回 JSON 格式结果
- 错误处理完善

---

### Task 4.2: launch 关键字实现
**优先级**: P1
**预计工时**: 2h

**目标**：实现桌面应用启动关键字

**交付物**：
- 修改 `core/keyword_engine.py`（添加 `launch` 到 SUPPORTED）
- 实现 `launch` 逻辑（启动或切换应用）

**验收标准**：
- Windows: 启动 .exe 或应用名
- macOS: 启动 .app 或应用名
- 已运行应用自动切换

---

## 阶段五：错误处理与优化（P1）

### Task 5.1: 视觉定位错误处理
**优先级**: P1
**预计工时**: 2h

**交付物**：
- `rodski/vision/exceptions.py`

**验收标准**：
- 定义错误类型（元素未找到、服务超时、坐标无效）
- 包含上下文信息
- 提供修复建议

---

### Task 5.2: 缓存优化
**优先级**: P1
**预计工时**: 2h

**交付物**：
- `rodski/vision/cache.py`

**验收标准**：
- 缓存 OmniParser 结果
- 缓存 LLM 识别结果
- 自动过期清理

---

## 阶段六：测试与文档（P1）

### Task 6.1: 集成测试
**优先级**: P1
**预计工时**: 3h

**交付物**：
- `tests/integration/test_vision_web.py`
- `tests/integration/test_vision_desktop.py`

**验收标准**：
- Web 视觉定位测试通过
- Desktop 视觉定位测试通过
- 覆盖率 > 80%

---

### Task 6.2: Demo 演示用例
**优先级**: P1
**预计工时**: 3h

**目标**：在 rodski-demo 项目中补充视觉定位演示用例

**交付物**：
- `rodski-demo/DEMO/vision_web/` - Web 视觉定位演示
  - `case/vision_demo.xml`
  - `model/model.xml`（包含 vision 定位器）
  - `data/VisionPage.xml`
- `rodski-demo/DEMO/vision_desktop/` - Desktop 视觉定位演示
  - `case/desktop_demo.xml`
  - `model/model.xml`（包含 vision_bbox 定位器）
  - `fun/desktop/` 脚本示例

**验收标准**：
- Web demo 执行通过
- Desktop demo 执行通过（Windows/macOS）
- 包含完整的 README 说明

---

### Task 6.2: 用户手册更新
**优先级**: P1
**预计工时**: 2h

**目标**：更新 TEST_CASE_WRITING_GUIDE.md

**交付物**：
- 视觉定位器使用说明
- 桌面端示例

**验收标准**：
- 文档清晰完整
- 示例可运行

---

### Task 6.3: Agent 使用指南
**优先级**: P1
**预计工时**: 3h

**交付物**：
- `rodski/docs/agent-guides/AGENT_SKILL_GUIDE.md`

**验收标准**：
- 包含完整的 Skill 定义
- 包含 XML 生成示例
- 包含错误处理示例

---

## 任务统计

### 按阶段统计

| 阶段 | 任务数 | 工时 | 优先级 |
|------|--------|------|--------|
| 阶段一：基础服务 | 3 | 5.5h | P0 |
| 阶段二：LLM 识别 | 2 | 5h | P0 |
| 阶段三：定位器集成 | 3 | 8h | P0 |
| 阶段四：桌面操作 | 2 | 5h | P1 |
| 阶段五：错误优化 | 2 | 4h | P1 |
| 阶段六：测试文档 | 4 | 11h | P1 |
| **总计** | **16** | **38.5h** | - |

### 按优先级统计

- **P0**: 8 个任务，18.5h（核心功能）
- **P1**: 8 个任务，20h（优化和文档）

---

## 依赖关系

### 关键路径
```
Task 1.1 → Task 2.1 → Task 2.2 → Task 3.2 → Task 6.1
```

### 并行任务
- Task 1.2 和 Task 1.3 可并行
- Task 3.1 和 Task 3.3 可并行
- 阶段四、五、六可并行

---

## 外部依赖

1. **OmniParser 服务**: 需要部署并可访问
2. **LLM API**: 需要配置 API 密钥
3. **测试环境**: Web/Desktop 环境

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| OmniParser 不稳定 | 高 | 降级到标准定位 |
| LLM 成本高 | 中 | 缓存优化 |
| 桌面坐标不准确 | 中 | 全屏执行 + 调试工具 |

---

## v4 与 v3 的主要变化

### 新增约束
- ✅ 定位器格式统一为 `locator="vision:..."` 
- ✅ 桌面平台明确为 `windows` / `macos`
- ✅ 桌面操作通过 `run` 实现，不新增关键字
- ✅ 新增 `launch` 关键字（与 `navigate` 场景化双关键字）

### 任务调整
- Task 1.2: 增加桌面坐标支持（+0.5h）
- Task 1.3: 增加桌面截图支持（+1h）
- Task 3.1: 修改为 `locator` 属性格式
- Task 4.1: 新增桌面操作脚本库
- Task 4.2: 新增 `launch` 关键字实现
- Task 6.2: 新增 Demo 演示用例（rodski-demo 项目）

### 工时变化
- v3: 32h → v4: 38.5h（+6.5h，增加桌面支持 + Demo演示用例）

---

## 下一步行动

1. 评审本任务清单（v4）
2. 确认 OmniParser 服务部署
3. 启动阶段一开发（P0）
4. 并行编写 Agent 使用指南（Task 6.3）
