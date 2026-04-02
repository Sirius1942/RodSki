---
name: design_decisions
description: 视觉定位关键设计决策
type: reference
---

视觉定位的关键设计决策：

**locator 格式统一**：
- 视觉定位通过 `location type` 属性实现，不新增关键字
- `vision` — 图片模板匹配（图片路径相对于 `images/` 目录）
- `ocr` — OCR 文字识别（文字内容）
- `vision_bbox` — 坐标定位（`x1,y1,x2,y2` 像素坐标）

**桌面端操作**：
- 关键字统一使用 `type`/`verify`/`launch`
- 不在 SUPPORTED 中引入 `clipboard`、`key_combination` 等独立关键字
- 桌面特有操作（剪贴板、组合键）通过 `run` 关键字调用脚本实现

**Why:** 这些决策已在 CORE_DESIGN_CONSTRAINTS.md 中固化，所有实现必须遵循。
**How to apply:** 设计桌面端自动化时，优先使用 `launch` + `type`，特殊操作用 `run`。
