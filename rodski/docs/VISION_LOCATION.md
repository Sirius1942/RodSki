# RodSki 视觉定位能力设计

**版本**: v2.0
**日期**: 2026-03-26
**对齐**: 核心设计约束 v3.6

## 概述

RodSki 调用 **OmniParser 服务**获取页面元素坐标，结合多模态 LLM 进行语义理解，实现视觉定位能力。

> OmniParser 是基于 YOLO 实现的视觉解析服务，提供元素坐标识别能力。

**核心原则**：
- RodSki 是执行层，不做探索
- Agent 负责探索和生成 XML
- 视觉定位作为定位器类型，不新增关键字
- 桌面操作通过 `run` 调用脚本

---

## 定位器格式（统一）

### 语义定位
```xml
<element name="loginBtn">
    <location type="vision">登录按钮</location>
</element>
```

### 坐标定位
```xml
<!-- Web: 像素坐标 -->
<element name="submitBtn">
    <location type="vision_bbox">100,200,150,250</location>
</element>

<!-- Desktop: 屏幕绝对坐标 -->
<element name="closeBtn">
    <location type="vision_bbox">1850,50,1900,100</location>
</element>
```

**格式约束**：
- 使用 `<location type="...">值</location>` 子元素格式
- `vision_bbox` 坐标为 `x1,y1,x2,y2`（逗号分隔）
- Web: 像素坐标；Desktop: 屏幕绝对坐标

---

## 核心流程

```
截图 → OmniParser → 元素坐标 → LLM 语义识别 → 匹配目标 → 坐标操作
```

**流程说明**：
1. 框架读取模型定义，识别 `<location type="vision">` 或 `<location type="vision_bbox">` 元素
2. 自动截图（Web 浏览器截图 / Desktop 全屏截图）
3. 调用 OmniParser 服务获取元素坐标列表
4. 使用 LLM 进行语义匹配（仅 `vision` 类型）
5. 返回目标元素坐标
6. 使用坐标驱动器执行操作

---

## 平台支持

### Web 平台
- **截图**: Selenium/Playwright 浏览器截图
- **坐标**: 页面像素坐标
- **驱动**: `driver.execute_script("document.elementFromPoint(x,y).click()")`

### Desktop 平台（Windows/macOS）
- **截图**: 全屏截图（pyautogui）
- **坐标**: 屏幕绝对坐标
- **驱动**: `pyautogui.click(x, y)`
- **约束**: 应用默认全屏执行，避免坐标偏移

---

## 实现架构

### 技术栈

- **OmniParser 服务**：元素坐标识别
- **多模态 LLM**：Claude/GPT-4V/Qwen-VL 语义理解
- **坐标驱动**：
  - Web: Selenium/Playwright
  - Desktop: pyautogui (Windows/macOS)

### 核心模块

```
rodski/vision/
├── omni_client.py          # OmniParser HTTP 客户端
├── llm_analyzer.py         # 多模态 LLM 客户端
├── matcher.py              # 语义匹配算法
├── coordinate_utils.py     # 坐标转换工具
├── screenshot.py           # 截图工具（多平台）
├── desktop_driver.py       # 桌面坐标驱动
├── locator.py              # 定位器集成
├── cache.py                # 缓存优化
└── exceptions.py           # 错误处理
```

---

## 使用示例

### Web 平台示例

**模型定义**（`model/model.xml`）：
```xml
<model name="LoginPage" driver_type="web">
  <element name="username">
      <location type="vision">用户名输入框</location>
  </element>
  <element name="password">
      <location type="vision">密码输入框</location>
  </element>
  <element name="loginBtn">
      <location type="vision">登录按钮</location>
  </element>
</model>
```

**用例定义**（`case/login.xml`）：
```xml
<test_step action="navigate" model="" data="https://example.com/login"/>
<test_step action="type" model="LoginPage" data="L001"/>
```

**数据表**（`data/LoginPage.xml`）：
```xml
<row id="L001">
  <field name="username">admin</field>
  <field name="password">admin123</field>
  <field name="loginBtn">click</field>
</row>
```

---

### Desktop 平台示例

**模型定义**（`model/model.xml`）：
```xml
<model name="Notepad" driver_type="windows">
  <element name="textArea">
      <location type="vision">文本编辑区</location>
  </element>
  <element name="saveBtn">
      <location type="vision_bbox">100,50,150,80</location>
  </element>
</model>
```

**用例定义**（`case/notepad.xml`）：
```xml
<test_step action="launch" model="" data="notepad.exe"/>
<test_step action="type" model="Notepad" data="N001"/>
<test_step action="run" model="" data="fun/desktop/key_combo.py Ctrl+S"/>
```

---

## 桌面操作脚本示例

桌面特有操作通过 `run` 关键字调用脚本（放置在 `fun/desktop/`）：

### 剪贴板操作
```python
# fun/desktop/clipboard_copy.py
import pyperclip
import json

text = pyperclip.paste()
print(json.dumps({"status": "success", "text": text}))
```

### 组合键
```python
# fun/desktop/key_combo.py
import sys
import pyautogui
import json

keys = sys.argv[1] if len(sys.argv) > 1 else "Ctrl+C"
pyautogui.hotkey(*keys.split('+'))
print(json.dumps({"status": "success", "keys": keys}))
```

---

## Agent 与 RodSki 协作

**Agent 职责**：
- 探索页面/应用（使用自己的视觉能力）
- 生成模型 XML（定义元素和定位器）
- 决策执行策略
- 处理执行结果并调整

**RodSki 职责**：
- 执行 XML 定义的操作
- 支持视觉定位器（vision/vision_bbox）
- 返回结构化执行结果

**协作流程**：
```
1. Agent 探索 → 发现元素
2. Agent 生成 XML → 记录为活文档
3. Agent 调用 RodSki → 执行 XML
4. RodSki 返回结果 → Agent 分析决策
```

---

## 性能优化

- **缓存**：相同页面复用 OmniParser 和 LLM 识别结果
- **超时**：OmniParser 5秒，LLM 10秒
- **降级**：视觉定位失败时降级到传统定位器

---

## 约束规则

- ❌ 不新增 `vision_click`、`vision_input` 等关键字
- ❌ 不在 Case XML 中直接写坐标
- ❌ 桌面端不新增 `clipboard`、`key_combination`、`window` 等关键字
- ✅ 视觉定位作为模型定位器类型（`<location type="...">` 子元素）
- ✅ 复用现有关键字（type/verify/navigate/launch）
- ✅ 桌面操作通过 `run` 调用脚本
- ✅ 坐标信息记录在模型 XML 中

---

*文档版本: v2.0 | 最后更新: 2026-03-26*
