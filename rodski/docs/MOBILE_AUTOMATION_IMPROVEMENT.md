# RodSki 移动端自动化现状分析与改进方向

> 分析日期：2026-05-21  
> 参考项目：mobile-use、AppAgent（腾讯）、MobileAgent（阿里）、mobile-mcp

---

## 一、类 Browser-Use 的移动端工具

App 自动化领域已有与 Browser-Use 高度对称的工具生态，核心原理一致：**采集 UI 结构 → 序列化给 LLM → LLM 决策动作 → 执行**。

| 工具 | 定位 | UI 感知方式 | 执行层 |
|------|------|------------|--------|
| [mobile-use](https://github.com/minitap-ai/mobile-use) | Browser-Use 的移动端直接对标 | Accessibility Tree + 截图 | Appium / ADB |
| [AppAgent](https://github.com/TencentQQGYLab/AppAgent)（腾讯） | 纯视觉方案 | 截图 + 视觉标注编号 | ADB 坐标 |
| [MobileAgent](https://github.com/X-PLUG/MobileAgent)（阿里） | 视觉感知 + 规划 | 截图 + 视觉模型定位 | ADB |
| [mobile-mcp](https://github.com/mobile-next/mobile-mcp) | MCP Server 形式 | Accessibility Tree 快照 + 截图 | Appium |

### 核心原理

移动端的 **Accessibility Tree** 就是 App 版的 DOM Tree：

```
Android: UIAutomator2 → driver.page_source() → XML View Hierarchy
iOS:     XCUITest / WebDriverAgent → page_source() → XML

每个节点包含：
  resource-id / name    ← 元素 ID（类似 HTML id）
  text / label          ← 可见文本
  content-desc          ← 无障碍描述
  bounds                ← 坐标 [x1,y1][x2,y2]
  clickable / enabled   ← 交互状态
  class                 ← 控件类型（Button/TextView/EditText...）
```

序列化后喂给 LLM（类比 Browser-Use 的 `[1]<button>Submit</button>`）：

```
[0]<Button clickable=true>登录</> bounds=[100,200][300,260]
[1]<EditText clickable=true>请输入手机号</> bounds=[50,300][400,360]
[2]<TextView clickable=false>忘记密码</> bounds=[280,380][400,410]
```

LLM 输出 `tap(0)` → 解析 bounds → ADB/Appium 执行坐标点击。

### 两种技术路线对比

| 路线 | 原理 | 适用场景 | 缺点 |
|------|------|---------|------|
| **Accessibility Tree** | 结构化 XML → 文本序列化 → LLM | 原生 Android/iOS App | Flutter/游戏 Tree 为空 |
| **纯视觉（AppAgent 模式）** | 截图 → 视觉模型标注编号 → LLM | Flutter/游戏/任意 App | 坐标不稳定，速度慢 |

---

## 二、RodSki 移动端当前架构

```
XML 用例
  → KeywordEngine._try_locators()
  → AppiumDriver.locate_element(type, value)
      支持：id / xpath / name / class / text
  → Appium Server → UIAutomator2 / XCUITest
  → 返回 bbox → 坐标点击 / 输入
```

vision 定位器路径（**当前断路**）：
```
vision locator
  → LLMAnalyzer.analyze(screenshot, omniparser_elements)
  → VisionLocatorCapability → OmniParser + LLM 打语义标签
  ↑
  AppiumDriver.locate_element() 里没有调用此路径 ← 断路点
```

---

## 三、当前不足

### 3.1 无 Accessibility Tree 感知（最严重）

`AppiumDriver` 完全没有调用 `driver.page_source()`。Appium 可以返回完整的 XML View Hierarchy，但 RodSki 没有利用。现在 vision 定位只靠截图 + OmniParser（视觉模型），精度和速度都不如结构化 Tree。

### 3.2 vision 定位器在移动端断路

`VisionLocatorCapability` 的输入依赖 OmniParser 解析的 `elements`，但 `AppiumDriver.locate_element()` 里没有触发 OmniParser 的逻辑——移动端 `vision` 类型的 locator 实际走不通，直接返回 `None`。

### 3.3 只用 ADB 不够

ADB 原生能力：截图、坐标点击、文字输入、按键。  
**无法获取 UI 结构**——View Hierarchy 必须走 UIAutomator2（Appium），不是 ADB 原生能力。  
对于 Flutter/React Native/游戏这类 Accessibility Tree 为空的 App，纯 ADB 坐标操作是唯一选择，但需要视觉模型辅助定位。

### 3.4 `get_text()` 返回空字符串

```python
def get_text(self, x1, y1, x2, y2) -> str:
    return ""  # ← 直接返回空，get 关键字在移动端完全不可用
```

### 3.5 无自愈能力

locator 失败直接报错，不会尝试语义匹配或视觉降级。

---

## 四、改进方案

### 4.1 接入 Accessibility Tree（最高优先级）

在 `AppiumDriver` 新增 Tree 序列化方法，把 `page_source()` 的 XML 转为带 index 的文本：

```python
# drivers/appium_driver.py 新增
def get_accessibility_tree_text(self) -> tuple[str, dict[int, tuple]]:
    """序列化 Accessibility Tree，返回 (文本, index→bounds 映射)"""
    import xml.etree.ElementTree as ET
    source = self.driver.page_source
    root = ET.fromstring(source)
    lines = []
    index_map = {}  # index → (x1, y1, x2, y2)
    idx = 0
    for elem in root.iter():
        text = elem.get('text', '') or elem.get('label', '') or elem.get('content-desc', '')
        rid = elem.get('resource-id', '') or elem.get('name', '')
        cls = (elem.get('class', '') or elem.get('type', '')).split('.')[-1]
        clickable = elem.get('clickable', 'false') == 'true'
        bounds_str = elem.get('bounds', '')
        if not (text or (clickable and rid)):
            continue
        # 解析 bounds: "[x1,y1][x2,y2]"
        import re
        m = re.findall(r'\d+', bounds_str)
        if len(m) == 4:
            bbox = tuple(int(v) for v in m)
            index_map[idx] = bbox
        lines.append(f"[{idx}]<{cls} clickable={clickable}>{text or rid}</>")
        idx += 1
    return '\n'.join(lines), index_map
```

在 `VisionLocatorCapability` 里，移动端路径改为 **Tree 文本 + 截图** 双模态输入 LLM：

```
Tree 文本 + 截图 → LLM
LLM 输出：{"index": 2, "reason": "登录按钮"}
→ index_map[2] → bbox → 坐标点击
```

### 4.2 修复 vision 定位器在移动端的断路

在 `AppiumDriver.locate_element()` 补上 vision 分支：

```python
def locate_element(self, locator_type, locator_value):
    if locator_type in ('vision', 'ocr', 'vision_bbox'):
        return self._locate_with_vision(locator_value)
    # ... 原有 id/xpath/name 逻辑

def _locate_with_vision(self, semantic_label: str):
    screenshot = self.take_screenshot()
    tree_text, index_map = self.get_accessibility_tree_text()
    if len(index_map) < 5:
        # Tree 为空（Flutter/游戏），降级到纯视觉模式
        return self._locate_visual_only(screenshot, semantic_label)
    # Tree + 截图双模态
    from rodski.vision.llm_analyzer import LLMAnalyzer
    analyzer = LLMAnalyzer()
    idx = analyzer.locate_by_label(screenshot, tree_text, semantic_label)
    return index_map.get(idx)
```

### 4.3 Flutter / 游戏 App 纯视觉降级

检测到 Tree 节点数 < 10 时，自动切换 AppAgent 模式：

```
截图 → OmniParser 标注可点击区域编号
     → 截图（含标注）+ semantic_label → LLM
     → LLM 选择编号 → 解析坐标 → ADB tap
```

### 4.4 修复 `get_text()`

```python
def get_text(self, x1, y1, x2, y2) -> str:
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    elems = self.driver.find_elements(AppiumBy.XPATH, '//*[@text!="" or @content-desc!=""]')
    for e in elems:
        r = e.rect
        if r['x'] <= cx <= r['x'] + r['width'] and r['y'] <= cy <= r['y'] + r['height']:
            return e.text or e.get_attribute('content-desc') or ''
    return ''
```

### 4.5 locator 失败自动降级到 vision

在 `KeywordEngine._try_locators()` 里，所有 locator 失败后自动触发 vision 降级：

```python
# 所有 locator 失败后
if not bbox and hasattr(self.driver, '_locate_with_vision'):
    logger.info(f"所有 locator 失败，尝试 vision 降级: {element_name}")
    bbox = self.driver._locate_with_vision(element_name)
```

---

## 五、改进优先级总结

| 问题 | 严重程度 | 改进方式 | 工作量 |
|------|---------|---------|--------|
| 无 Accessibility Tree 序列化 | 高 | 新增 `get_accessibility_tree_text()`，接入 LLM 双模态定位 | 中 |
| vision 定位器移动端断路 | 高 | `locate_element()` 补 vision 分支 | 小 |
| `get_text()` 返回空 | 中 | 坐标反查最近元素的 text 属性 | 小 |
| Flutter/游戏 App 无法处理 | 中 | Tree 为空时降级到纯视觉坐标模式 | 大 |
| 无自愈能力 | 低 | locator 失败后自动触发 vision 降级 | 小 |

---

## 六、与 Browser-Use 的原理对应关系

| Browser-Use（Web） | RodSki 移动端改进后 |
|-------------------|-------------------|
| `CDP DOMSnapshot.captureSnapshot()` | `driver.page_source()` → XML View Hierarchy |
| `CDP Accessibility.getFullAXTree()` | UIAutomator2 / XCUITest AX 属性 |
| `[1]<button>Submit</button>` 文本序列化 | `[1]<Button clickable=true>登录</>` |
| `CDP Page.captureScreenshot()` | `driver.save_screenshot()` |
| `selector_map[index] → DOM 节点 → CDP 点击` | `index_map[index] → bounds → Appium tap` |
| 文本 + 截图双模态 → LLM | Tree 文本 + 截图双模态 → LLM |
