# 迭代 01 - 视觉定位功能需求

**版本**: v1.1
**日期**: 2026-03-27
**对齐**: 核心设计约束 v3.6

## 背景

RodSki 当前仅支持传统定位器（XPath、CSS、ID等），在以下场景存在局限：

1. **动态页面**：元素属性频繁变化，传统定位器失效
2. **无障碍性差**：缺少语义化属性的页面难以定位
3. **桌面应用**：Windows/macOS 原生应用无法使用Web定位器
4. **跨平台一致性**：不同平台需要不同的定位策略

需要引入视觉定位能力，通过图像识别和文字识别实现更灵活的元素定位。

## 目标

实现基于 **OpenCV + OmniParser** 的视觉定位能力，支持 Web 和 Desktop 平台。

**核心原则**：
- 关键字层统一，不区分平台
- 驱动层分离，Web/Desktop 各自实现
- 模型定义驱动类型，定位器决定定位方式
- 视觉定位器与传统定位器格式统一

---

## 架构设计

### 统一关键字，不同驱动

```
┌─────────────────────────────────────────────────────────────┐
│                     用例层 (Case XML)                        │
│         type / verify / launch / send ...                   │
│         (关键字统一，不区分平台)                              │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                     关键字引擎                               │
│     根据模型 type 属性分发到对应驱动                          │
└────────────────────────────┬────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Web Driver    │  │ Interface Driver│  │ Desktop Driver  │
│   (Playwright)  │  │   (Requests)    │  │  (pyautogui +   │
│                 │  │                 │  │   OmniParser)   │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                     定位器层                                 │
│   传统定位器: id / css / xpath / text / name / ...          │
│   视觉定位器: vision / ocr / vision_bbox                    │
│   (所有定位器格式统一)                                       │
└─────────────────────────────────────────────────────────────┘
```

### 平台与驱动对应关系

| 平台 | 驱动类型 | 驱动实现 | 适用定位器 |
|------|---------|---------|-----------|
| Web | `web` | Playwright | id/css/xpath/text/vision/ocr/vision_bbox |
| Interface | `interface` | Requests | static/field |
| Windows | `windows` | pyautogui + OmniParser | vision/ocr/vision_bbox |
| macOS | `macos` | pyautogui + OmniParser | vision/ocr/vision_bbox |

---

## 功能需求

### 1. 视觉定位器支持

#### 1.1 定位器格式

所有定位器使用统一格式 `<location type="类型">值</location>`：

**图片定位 (vision)**：
```xml
<element name="loginBtn" type="web">
    <type>button</type>
    <location type="vision">img/login_btn.png</location>
</element>
```
- 通过图片模板匹配定位
- 图片存放在 `images/` 目录
- Web 用页面坐标，Desktop 用屏幕坐标
- 适用于按钮图标、Logo 等视觉元素

**文字定位 (ocr)**：
```xml
<element name="loginBtn" type="web">
    <type>button</type>
    <location type="ocr">登录</location>
</element>
```
- 通过 OCR 识别文字定位
- 支持中英文文字识别
- 适用于按钮文字、标签、链接

**坐标定位 (vision_bbox)**：
```xml
<element name="submitBtn" type="web">
    <type>button</type>
    <location type="vision_bbox">100,200,150,250</location>
</element>
```
- 直接使用坐标定位（x1,y1,x2,y2）
- 无需 AI 调用，性能最高
- 适用于坐标固定的场景

#### 1.2 三种定位方式对比

同一个登录按钮可以用三种方式定位：

```xml
<!-- 方式1: 图片匹配 - 使用按钮截图 -->
<element name="loginBtn" type="web">
    <type>button</type>
    <location type="vision">img/login_btn.png</location>
</element>

<!-- 方式2: OCR文字识别 - 识别"登录"二字 -->
<element name="loginBtn" type="web">
    <type>button</type>
    <location type="ocr">登录</location>
</element>

<!-- 方式3: 坐标定位 - Agent探索后生成 -->
<element name="loginBtn" type="web">
    <type>button</type>
    <location type="vision_bbox">100,200,150,250</location>
</element>
```

#### 1.3 多定位器自动切换

每个元素可定义多个定位器，按优先级依次尝试，失败自动切换：

```xml
<element name="loginBtn" type="web">
    <type>button</type>
    <location type="id" priority="1">loginBtn</location>
    <location type="xpath" priority="2">//button[@class='login']</location>
    <location type="ocr" priority="3">登录</location>
</element>
```

**切换规则**：
1. 按 `priority` 从小到大依次尝试
2. 当前定位器定位失败时，自动切换到下一个
3. 所有定位器都失败时，抛出元素未找到异常

---

### 2. 驱动层设计

#### 2.1 Web 驱动 (已有)

**现有能力**：
- Playwright 浏览器驱动
- 支持传统定位器（id/css/xpath/text等）
- 支持 type/verify/navigate 等关键字

**新增能力**：
- 支持 vision 定位器（OpenCV 模板匹配）
- 支持 ocr 定位器（OmniParser）
- 支持 vision_bbox 定位器（坐标点击）

**实现方式**：
```
vision/ocr/vision_bbox 定位器
    ↓
截图（Playwright page.screenshot）
    ↓
AI/算法处理
    ↓
返回坐标 (x1, y1, x2, y2)
    ↓
Playwright 执行点击/输入（page.mouse.click / page.keyboard.type）
```

#### 2.2 Desktop 驱动 (新增)

**驱动类型**：
- `windows` - Windows 桌面应用
- `macos` - macOS 桌面应用

**核心能力**：
- pyautogui 实现鼠标/键盘操作
- OmniParser 实现 OCR 文字识别
- OpenCV 实现图片模板匹配

**支持的关键字**：

| 关键字 | Desktop 行为 |
|--------|-------------|
| `launch` | 启动应用或切换窗口 |
| `type` | 在坐标位置输入文字或执行点击 |
| `verify` | 验证屏幕内容（OCR 提取文字） |
| `wait` | 等待元素出现 |
| `close` | 关闭应用窗口 |
| `get_text` | 通过 OCR 获取文字 |

**实现方式**：
```
launch 关键字
    ↓
pyautogui 或 subprocess 启动应用
    ↓
type/verify 关键字
    ↓
定位器定位元素 → 返回坐标
    ↓
pyautogui.click(x, y) / pyautogui.typewrite(text)
```

---

### 3. launch 关键字

#### 3.1 功能定义

`launch` 用于启动桌面应用或切换到已运行的应用窗口：

```xml
<!-- 启动应用 -->
<test_step action="launch" model="DesktopApp" data="L001"/>

<!-- 数据表 -->
<row id="L001">
    <field name="app_path">C:\Apps\Notepad.exe</field>
</row>

<!-- 或使用应用名（macOS） -->
<row id="L001">
    <field name="app_name">TextEdit</field>
</row>
```

#### 3.2 与 navigate 的关系

| 关键字 | 平台 | 行为 |
|--------|------|------|
| `navigate` | Web | 打开浏览器，导航到 URL |
| `launch` | Desktop | 启动桌面应用或切换窗口 |

**设计决策**：`launch` 和 `navigate` 在关键字计数中算作一个（场景化变体）。

#### 3.3 模型定义

```xml
<!-- Desktop 应用模型 -->
<model name="DesktopApp">
    <element name="app_path" type="static"/>
    <element name="app_name" type="static"/>
</model>

<!-- Web 应用模型 -->
<model name="WebApp">
    <element name="url" type="static"/>
</model>
```

---

### 4. Desktop 平台 type 关键字

#### 4.1 统一使用方式

Desktop 平台的 type 关键字使用方式与 Web 完全相同：

```xml
<!-- 用例 -->
<test_step action="launch" model="Notepad" data="L001"/>
<test_step action="type" model="NotepadEditor" data="T001"/>
<test_step action="verify" model="NotepadEditor" data="V001"/>

<!-- 模型 -->
<model name="NotepadEditor">
    <element name="editor_area" type="windows">
        <type>text</type>
        <location type="ocr" priority="1">此处键入</location>
        <location type="vision_bbox" priority="2">100,200,800,600</location>
    </element>
</model>

<!-- 数据表 -->
<row id="T001">
    <field name="editor_area">Hello World</field>
</row>

<row id="V001">
    <field name="editor_area">Hello World</field>
</row>
```

#### 4.2 数据表动作值

Desktop 支持的动作值与 Web 相同：

| 动作值 | 行为 |
|--------|------|
| `click` | 点击坐标 |
| `double_click` | 双击坐标 |
| `right_click` | 右键点击 |
| 输入值 | 在坐标位置输入文字 |

---

### 5. 配置管理

#### 5.1 全局变量配置

```xml
<group name="VisionConfig">
    <var name="OMNIPARSER_URL" value="http://localhost:8001"/>
    <var name="OPENCV_MATCH_THRESHOLD" value="0.8"/>
    <var name="VISION_CACHE_TTL" value="30"/>
</group>
```

#### 5.2 配置优先级

全局变量 > 环境变量 > 默认值

---

## 非功能需求

### 1. 性能要求

| 定位器 | 响应时间 | 说明 |
|--------|---------|------|
| vision | 100-300ms | OpenCV 本地计算 |
| ocr | 1-3s | OmniParser 网络调用 |
| vision_bbox | <1ms | 纯坐标计算 |

### 2. 可靠性

- OmniParser 服务不可用时降级到其他定位器
- 支持多定位器自动切换
- 清晰的错误提示

### 3. 兼容性

- 支持 Python 3.9-3.13
- 支持 Windows 10/11
- 支持 macOS 11+

---

## 约束条件

### 核心约束

1. **关键字统一**：type/verify/launch 等关键字跨平台通用
2. **格式统一**：所有定位器使用 `<location type="...">` 格式
3. **驱动分离**：Web/Desktop 使用不同驱动实现
4. **向后兼容**：不影响现有 Web 测试用例

### 不做的事

1. ❌ 不新增 `vision_click`、`desktop_type` 等平台特定关键字
2. ❌ 不在 Case XML 中区分平台，平台信息在模型中定义
3. ❌ 不为 Desktop 单独设计一套用例格式

---

**创建日期**: 2026-03-27
**最后更新**: 2026-03-27