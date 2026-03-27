# 迭代 01 - 视觉定位功能需求

**版本**: v1.0
**日期**: 2026-03-20
**对齐**: 核心设计约束 v3.6

## 背景

RodSki 当前仅支持传统定位器（XPath、CSS、ID等），在以下场景存在局限：

1. **动态页面**：元素属性频繁变化，传统定位器失效
2. **无障碍性差**：缺少语义化属性的页面难以定位
3. **桌面应用**：Windows/macOS 原生应用无法使用Web定位器
4. **跨平台一致性**：不同平台需要不同的定位策略

需要引入视觉定位能力，通过图像识别和语义理解实现更灵活的元素定位。

## 目标

实现基于 **OmniParser + 多模态 LLM** 的视觉定位能力，支持 Web 和 Desktop 平台。

**核心原则**：
- 不新增关键字，通过 `locator` 属性扩展
- 桌面操作使用 `run` 关键字调用脚本
- 保持向后兼容，不影响现有功能

## 功能需求

### 1. 视觉定位器支持

#### 1.1 定位器格式

视觉定位器使用 `<location type="...">` 格式，与传统定位器保持一致：

**图片定位 (vision)**：
```xml
<element name="loginBtn" type="web">
    <type>button</type>
    <location type="vision">img/login_btn.png</location>
</element>
```
- 通过图片模板匹配定位
- 图片存放在 `images/` 目录
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

#### 1.3 与传统定位器对比

| 定位类型 | 格式 | 示例 |
|---------|------|------|
| ID | `<location type="id">` | `<location type="id">loginBtn</location>` |
| XPath | `<location type="xpath">` | `<location type="xpath">//button[@id='login']</location>` |
| Vision | `locator="vision:"` | `locator="vision:登录按钮"` |
| VisionBBox | `locator="vision_bbox:"` | `locator="vision_bbox:100,200,150,250"` |

#### 1.3 多定位器自动切换

每个元素可定义多个定位器，按优先级依次尝试，失败自动切换：

```xml
<element name="loginBtn">
    <locator type="id" priority="1">loginBtn</locator>
    <locator type="xpath" priority="2">//button[@class='login']</locator>
    <locator type="vision" priority="3">登录按钮</locator>
</element>
```

**切换规则**：
1. 按 `priority` 从小到大依次尝试
2. 当前定位器定位失败时，自动切换到下一个
3. 所有定位器都失败时，抛出元素未找到异常

**使用场景**：
- 传统定位器作为首选，视觉定位作为兜底
- 动态页面优先使用视觉定位
- 提高测试用例的健壮性

### 2. 平台支持

#### 2.1 Web 平台
- 浏览器截图（Selenium/Playwright）
- 页面像素坐标
- 通过 JavaScript 执行点击

#### 2.2 Desktop 平台
- 全屏截图（pyautogui）
- 屏幕绝对坐标
- 支持 Windows 和 macOS
- 新增 `launch` 关键字启动应用

### 3. 桌面操作脚本

桌面端的辅助操作通过 `run` 关键字调用 Python 脚本：

```xml
<step action="run" script="desktop/clipboard_copy.py"/>
<step action="run" script="desktop/key_combo.py" data="ctrl+v"/>
```

**支持操作**：
- 剪贴板操作（复制/粘贴）
- 组合键（Ctrl+C, Cmd+V等）
- 窗口切换

### 4. 配置管理

#### 4.1 全局变量配置
```xml
<var name="ANTHROPIC_API_KEY" value="sk-xxx"/>
<var name="OPENAI_API_KEY" value="sk-xxx"/>
<var name="OPENAI_BASE_URL" value="http://..."/>
<var name="OPENAI_MODEL" value="qwen3-coder-plus"/>
<var name="OMNIPARSER_URL" value="http://..."/>
```

#### 4.2 配置优先级
全局变量 > 环境变量 > vision_config.yaml > 默认值

## 非功能需求

### 1. 性能要求
- 视觉定位响应时间 < 3秒
- 支持结果缓存（30秒TTL）
- vision_bbox 模式无AI调用，响应 < 100ms

### 2. 可靠性
- OmniParser 服务不可用时降级到传统定位器
- LLM 调用失败时返回明确错误信息
- 支持重试机制

### 3. 可维护性
- 模块化设计，各组件独立
- 完整的单元测试和集成测试
- 清晰的错误提示和日志

### 4. 兼容性
- 支持 Python 3.9-3.13
- 支持多种 LLM（Claude/OpenAI/Qwen）
- 向后兼容现有定位器

## 约束条件

参考: #[[file:../../conventions/PROJECT_CONSTRAINTS.md]]

### 核心约束
1. **不新增关键字**：视觉定位通过 `locator` 属性实现
2. **桌面操作用 run**：不为桌面操作新增独立关键字
3. **launch 与 navigate 算一个**：场景化变体，非独立关键字
4. **保持向后兼容**：不影响现有测试用例

---

**创建日期**: 2026-03-27

