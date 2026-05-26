# RodSki 视觉定位能力设计

**版本**: v3.0
**日期**: 2026-05-26
**对齐**: 核心设计约束 §2.5 / §2.6 (v7.1.0)

## 概述

RodSki v7.1.0 起将视觉定位重构为**正交插件机制**：
- rodski 核心提供 `vision_image`（OpenCV 模板匹配）/ `vision_bbox`（坐标）
  / `ocr`（文字）三类离线定位器
- VLM 语义定位（`vision` 类型）通过 `PerceptionBackend` 抽象 +
  Python `entry_points` 机制由独立的可选包（如 `rodski-perception`）提供
- 装了 rodski 但没装任何 backend 时，前三类定位器照常工作；`vision`
  执行时会抛 `PerceptionUnavailableError` 并附带安装指引

> v7.1.0 之前内置的 OmniParser HTTP 客户端（OmniClient）已删除。

**核心原则**：
- RodSki 是执行层，不做探索
- Agent 负责探索和生成 XML
- 视觉定位作为定位器类型，不新增关键字
- 桌面操作通过 `run` 调用脚本

---

## 定位器格式

```xml
<!-- vision: VLM 语义定位（需要 backend） -->
<element name="loginBtn">
    <location type="vision">登录按钮</location>
</element>

<!-- vision_image: 参考图模板匹配（离线、毫秒级、rodski 核心） -->
<element name="loginBtn">
    <location type="vision_image">assets/login_btn.png</location>
</element>

<!-- ocr: 文字定位（rodski 核心 + OCR provider） -->
<element name="loginLabel">
    <location type="ocr">登录</location>
</element>

<!-- vision_bbox: 固定坐标（兜底/调试，无任何依赖） -->
<element name="submitBtn">
    <location type="vision_bbox">100,200,150,250</location>
</element>
```

**格式约束**：
- 使用 `<location type="...">值</location>` 子元素格式
- `vision_bbox` 坐标为 `x1,y1,x2,y2`（逗号分隔）
- 同一 element 可声明多个 `<location>`：带 `priority` 顺序回退，
  不带 `priority` 走融合裁决（v7.1.0 §1.5 / 54d 实现）

---

## 核心模块

```
rodski/vision/
├── perception_interface.py    # v7.1.0 PerceptionBackend ABC + PerceptionResult + PerceptionUnavailableError
├── registry.py                # v7.1.0 PerceptionRegistry（entry_points 插件发现）
├── image_matcher.py           # v7.1.0 ImageTemplateMatcher（vision_image OpenCV 实现）
├── ocr_locator.py             # OCR provider-agnostic 适配层
├── bbox_locator.py            # vision_bbox 坐标解析
├── locator.py                 # VisionLocator 统一入口
├── llm_analyzer.py            # LLM 增强（legacy 路径，verify 用）
├── matcher.py                 # 语义匹配算法（legacy）
├── coordinate_utils.py        # 坐标转换工具
├── screenshot.py              # 截图工具（多平台）
├── desktop_driver.py          # 桌面坐标驱动
├── cache.py                   # 缓存
└── exceptions.py              # 错误类型
```

> **已删除**（v7.1.0）：`omni_client.py`。其能力由 `PerceptionBackend`
> 抽象 + 各 backend 实现项目提供。

---

## Perception 插件机制（v7.1.0 §2.6）

### 抽象接口

```python
from rodski.vision.perception_interface import (
    PerceptionBackend, PerceptionResult, PerceptionUnavailableError,
)
from rodski.vision.registry import PerceptionRegistry

# rodski 内部调用：
backend = PerceptionRegistry.get_backend(config)  # 自动发现可用 backend
result = backend.locate("/tmp/screen.png", "登录按钮")
# result.bbox / result.coordinates / result.confidence
```

### 第三方 backend 注册

任意 Python 包通过 `pyproject.toml` 的 entry_points 注册即可被发现，
**无需修改 rodski 源码**：

```toml
# 第三方包的 pyproject.toml
[project.entry-points."rodski.perception_backends"]
my_backend = "my_package.backend:MyPerceptionBackend"
```

### 安装方式

```bash
# 仅 rodski 核心（vision_image / vision_bbox / ocr 可用，vision 不可用）
pip install rodski

# 核心 + 本地 perception（推荐）
pip install rodski[perception]
brew install ollama && brew services start ollama
ollama pull qwen3-vl:2b
```

---

## 错误处理契约

| 情况 | 行为 |
|------|------|
| 未装任何 backend，调 `vision` | `PerceptionUnavailableError`（含 pip / ollama 指引） |
| backend 已装但 `is_available() == False` | 同上 + 诊断信息 |
| 指定的 `perception_backend=xxx` 不存在 | `PerceptionUnavailableError`（含已发现列表） |
| backend.locate 返回 None | 上层尝试下一个 location 或最终报"未找到" |

**禁止**：用例栈中出现裸 `ImportError` / `ConnectionError`，必须包装为
`PerceptionUnavailableError`。

---

## 平台支持

### Web 平台
- **截图**: Selenium/Playwright 浏览器截图
- **坐标**: 页面像素坐标（Retina/headed 模式下 keyword_engine 做 DPR 校正）

### Desktop 平台（Windows/macOS）
- **截图**: 全屏截图（pyautogui）
- **坐标**: 屏幕绝对坐标
- **约束**: 应用默认全屏执行，避免坐标偏移

---

## 性能优化

- **缓存**：相同截图复用解析结果（VisionCache）
- **延迟加载**：`ImageTemplateMatcher` / `OCRLocator` / backend 全部按需创建
- **离线优先**：`vision_image` 毫秒级；`vision`（VLM）秒级，仅在
  vision_image / ocr 无法满足时启用

---

## 约束规则

- ❌ 不新增 `vision_click`、`vision_input` 等关键字
- ❌ 不在 Case XML 中直接写坐标
- ❌ 桌面端不新增 `clipboard`、`key_combination`、`window` 等关键字
- ❌ rodski 核心**不直接**依赖任何 backend 实现（含 ollama / omni）
- ✅ 视觉定位作为模型定位器类型（`<location type="...">` 子元素）
- ✅ 复用现有关键字（type/verify/navigate/launch）
- ✅ 第三方 backend 通过 entry_points 注册，无需改 rodski 源码

---

*文档版本: v3.0 | 最后更新: 2026-05-26 | 对齐 v7.1.0 perception 插件机制*
