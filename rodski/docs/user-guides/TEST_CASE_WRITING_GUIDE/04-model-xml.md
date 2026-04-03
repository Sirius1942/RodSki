# 4. model.xml — 模型编写

> **来源**: RodSki 测试用例编写指南 v3.4  
> 本文档为独立章节，完整指南请见 [TEST_CASE_WRITING_GUIDE.md](../TEST_CASE_WRITING_GUIDE.md)

---


### 4.1 文件结构

```xml
<?xml version="1.0" encoding="UTF-8"?>
<models>
  <model name="模型名称" servicename="">
    <element name="元素名称" interfacename="" group="" type="web">
      <type>元素类型</type>
      <location type="定位类型" item="">定位值</location>
      <desc>描述（可选）</desc>
    </element>
  </model>
</models>
```

### 4.2 元素属性说明

**与 `model.xsd` 一致**：`<element>` 上 **`name` 为唯一必填属性**；`type`（属性）、`value`、`interfacename`、`group` 均为可选（有默认值时可省略）。

| 属性/子节点 | XSD | 实践建议 | 说明 |
|------------|-----|----------|------|
| `name` | **必填** | **必填** | 元素名称，**必须与数据表字段 name 一致**（区分大小写） |
| `type`（element 属性） | 可选 | Web/接口模型建议填 | **完整格式**：驱动类型 `web` / `interface` / `other`。**简化格式**：与 `LocatorType` 相同，表示定位类型，需配合 `value` |
| `value` | 可选 | 简化格式建议成对出现 | 与简化格式 `type` 配对，表示定位值 |
| `<type>` 子节点 | 可选 | Web 常用 | UI 控件语义：input / button / select / text / textarea |
| `<location type="...">` | 可选 | 完整格式常用 | `location@type` 取值见 [4.3](#43-定位类型)（`LocatorType`） |
| `<desc>` | 可选 | — | 元素描述，便于维护 |

> **运行时**：除 XSD 外，实际执行仍需要可用的定位信息——**完整格式**建议写 `type="web|interface|other"` + `<location>`；**简化格式**写 `type`（定位类型）+ `value`。

### 4.3 定位器类型（完整）

RodSki 支持 12 种定位器类型，分为传统定位器和视觉定位器两大类。

#### 4.3.1 传统定位器

| type 值 | 转换规则 | 示例 |
|---------|---------|------|
| `id` | → CSS `#定位值` | `<location type="id">username</location>` → `#username` |
| `class` | → CSS `.定位值` | `<location type="class">btn-submit</location>` → `.btn-submit` |
| `css` | → 原样使用 | `<location type="css">input[name="user"]</location>` |
| `xpath` | → 原样使用 | `<location type="xpath">//input[@id='user']</location>` |
| `text` | → Playwright `text=...` | `<location type="text">登录</location>` → `text=登录` |
| `tag` | → 标签名选择器 | `<location type="tag">button</location>` |
| `name` | name 属性选择器 | 按框架解析规则使用 |
| `static` | 静态字面量 | 常用于接口 `_method`、固定 URL 等 |
| `field` | 接口字段映射 | 常用于接口 body / query 字段名 |

#### 4.3.2 视觉定位器

| type 值 | 格式 | 说明 | 示例 |
|---------|------|------|------|
| `vision` | 图片匹配 | 通过截图/图片模板匹配定位 | `<location type="vision">img/login_btn.png</location>` |
| `ocr` | 文字识别 | 通过 OCR 识别文字定位 | `<location type="ocr">登录</location>` |
| `vision_bbox` | 坐标定位 | 直接使用坐标 `x1,y1,x2,y2` | `<location type="vision_bbox">100,200,150,250</location>` |

**视觉定位器说明**：

- **`vision` 图片定位器**：
  - 值为图片路径（相对于 `images/` 目录）
  - 通过图像匹配算法定位
  - 适用于：按钮图标、Logo、固定 UI 元素

- **`ocr` 文字定位器**：
  - 值为要识别的文字内容
  - 通过 OmniParser OCR 能力识别文字位置
  - 适用于：按钮文字、标签、链接文字

- **`vision_bbox` 坐标定位器**：
  - 值为坐标 `x1,y1,x2,y2`（逗号分隔）
  - 无需 AI 调用，性能最高
  - Web 用页面像素坐标，Desktop 用屏幕绝对坐标
  - 适用于：坐标固定的元素

#### 4.3.3 定位器格式约束

**格式规范**：
1. 所有定位器使用 `<location type="类型">值</location>` 格式
2. `type` 属性必须为 LocatorType 枚举值之一
3. 值写在 location 标签内容中

**正确示例**：
```xml
<!-- ✅ 正确：完整格式 -->
<element name="loginBtn" type="web">
    <type>button</type>
    <location type="id">loginBtn</location>
</element>

<!-- ✅ 正确：简化格式 -->
<element name="loginBtn" type="id" value="loginBtn"/>
```

**错误示例**：
```xml
<!-- ❌ 错误：不要使用 locator 属性 -->
<element name="loginBtn" locator="vision:登录按钮"/>
```

**示例对比**：
```xml
<!-- 同一个登录按钮，三种定位方式 -->

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

### 4.4 简化格式

对于简单场景，也支持单行格式：

```xml
<element name="username" type="id" value="userName"/>
```

此格式下 **属性** `type` 为 **`LocatorType` 定位类型**（不是 `web`），`value` 为定位值；驱动语义由框架按场景处理（一般为 Web）。

### 4.5 多定位器格式（自动切换）

每个元素可定义多个定位器，失败时自动切换：

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
3. 所有定位器都失败时，抛出 `ElementNotFoundError`

**使用场景**：
- 传统定位器作为首选，视觉定位作为兜底
- 动态页面优先使用视觉定位
- 提高测试用例的健壮性

### 4.6 核心约束：元素名 = 数据表字段名

```
model.xml 元素 name  ===  数据表 XML 的 field name
```

这是 `type`（批量输入）和 `verify`（批量验证）的运转基础。框架遍历模型元素时，用 `name` 去数据表中查找对应字段的值。

正确示例：

```xml
<!-- model.xml -->
<element name="username"><location type="id">userName</location></element>
<element name="password"><location type="id">password</location></element>
```

```xml
<!-- data/Login.xml -->
<datatable name="Login">
  <row id="L001" remark="有效">
    <field name="username">admin</field>     ← name 与 model 一致
    <field name="password">admin123</field>  ← name 与 model 一致
  </row>
</datatable>
```

### 4.6 完整示例

```xml
<?xml version="1.0" encoding="UTF-8"?>
<models>
<model name="Login" servicename="">
    <element name="username" interfacename="" group="" type="web">
        <type>input</type>
        <location type="id" item="">username</location>
        <desc>用户名输入框</desc>
    </element>
    <element name="password" interfacename="" group="" type="web">
        <type>input</type>
        <location type="id" item="">password</location>
        <desc>密码输入框</desc>
    </element>
    <element name="loginBtn" interfacename="" group="" type="web">
        <type>button</type>
        <location type="id" item="">login-btn</location>
        <desc>登录按钮</desc>
    </element>
</model>
</models>
```

---

