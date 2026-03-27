# 迭代 01 - 视觉定位功能

**迭代周期**: 2026-03-20 ~ 2026-03-27
**状态**: 🚧 进行中
**分支**: `feature/vision-location`
**类型**: 功能开发

## 目标

实现基于 **OpenCV + OmniParser** 的视觉定位能力，支持 Web 和 Desktop 平台。

## 核心设计

### 统一关键字，不同驱动

```
用例层: type / verify / launch ...（关键字统一，不区分平台）
    ↓
关键字引擎: 根据模型 type 属性分发
    ↓
驱动层: Web(Playwright) / Desktop(pyautogui) / Interface(Requests)
    ↓
定位器层: id/css/xpath/vision/ocr/vision_bbox（格式统一）
```

### 三种视觉定位器

| 定位器 | 格式 | 实现方式 | 适用场景 |
|--------|------|---------|---------|
| `vision` | `<location type="vision">img/xxx.png</location>` | OpenCV 模板匹配 | 按钮/图标/Logo |
| `ocr` | `<location type="ocr">文字</location>` | OmniParser OCR | 按钮文字/标签 |
| `vision_bbox` | `<location type="vision_bbox">x1,y1,x2,y2</location>` | 直接坐标 | 固定位置元素 |

### 关键字使用示例

**Web 平台**：
```xml
<test_step action="navigate" model="WebApp" data="L001"/>
<test_step action="type" model="LoginPage" data="T001"/>
```

**Desktop 平台**（关键字完全相同）：
```xml
<test_step action="launch" model="DesktopApp" data="L001"/>
<test_step action="type" model="LoginPage" data="T001"/>
```

**模型定义驱动类型**：
```xml
<!-- Web 模型 -->
<model name="LoginPage">
    <element name="loginBtn" type="web">...</element>
</model>

<!-- Desktop 模型 -->
<model name="LoginPage">
    <element name="loginBtn" type="windows">...</element>
</model>
```

## 文档

- [需求说明](requirements.md)
- [技术设计](design.md)
- [任务列表](tasks.md)

## 关键决策

1. **关键字统一**：type/verify/launch 等关键字跨平台通用
2. **驱动分离**：Web/Desktop 使用不同驱动实现
3. **格式统一**：所有定位器使用 `<location type="...">` 格式
4. **launch 与 navigate 算一个**：场景化变体，非独立关键字

## 任务概览

- Wave 1: 驱动层基础 (5任务, 10h)
- Wave 2: 视觉定位器实现 (5任务, 12h)
- Wave 3: Desktop 驱动实现 (4任务, 10h)
- Wave 4: 关键字引擎集成 (2任务, 4h)
- Wave 5: 测试和文档 (2任务, 6h)

**总计**: 18 任务, 42 小时

## 验收标准

```
✅ vision/ocr/vision_bbox 三种定位器可用
✅ Desktop 驱动可用
✅ launch 关键字可用
✅ type/verify 关键字跨平台统一
✅ 多定位器自动切换正常
✅ Demo 项目可执行
```

---

**创建日期**: 2026-03-27
**最后更新**: 2026-03-27

参考规范:
- [PROJECT_CONSTRAINTS](../../conventions/PROJECT_CONSTRAINTS.md)
- [GIT_WORKFLOW](../../conventions/GIT_WORKFLOW.md)