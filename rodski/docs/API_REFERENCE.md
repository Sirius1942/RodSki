# OmniParser 远程服务 API 文档

本文档描述了 OmniParser 视觉解析服务的接口规范。

## 快速开始

- **接口地址**: `http://<server_ip>:7862/parse/`
- **请求方法**: `POST`
- **Content-Type**: `application/json`

### 最简请求示例 (推荐)

绝大多数情况下，您只需要发送图片即可，服务端会使用推荐的默认参数（Box=0.18, IOU=0.7）。

```json
{
  "base64_image": "iVBORw0KGgoAAAANSUhEUgAA..."
}
```

## 请求参数详解

### 1. 核心参数 (必填)

| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `base64_image` | `string` | 待解析图片的 Base64 编码字符串。 |

### 2. 高级调优参数 (选填)

仅在默认效果不佳或需要特定功能（如提取输入框）时使用。

| 字段名 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `return_input_fields` | `false` | **是否提取输入框**。设为 `true` 时，响应中会额外包含 `input_fields` 字段，专门列出用户名/密码等输入框的坐标。 |
| `box_threshold` | `0.18` | **检测灵敏度** (0.0-1.0)。<br>• 调低 (e.g. 0.05)：能检出更多元素，但噪点变多。<br>• 调高 (e.g. 0.30)：只检出最明显的元素，可能漏检。 |
| `iou_threshold` | `0.7` | **重叠过滤** (0.0-1.0)。<br>• 控制重叠框的合并程度，通常保持默认即可。 |
| `merge_ocr_inside_icon` | `true` | **图标文字合并**。<br>• `true`: 将图标内的文字（如按钮上的字）视为图标的一部分。<br>• `false`: 图标和文字作为两个独立元素返回。 |
| `enable_caption` | `false` | **生成描述**。<br>• `true`: 对每个元素生成文字描述（速度较慢）。 |

## 响应结构 (Response)

响应体为 JSON 对象：

```json
{
  "som_image_base64": "...",       // 标注了红框的图片 Base64 (可直接在网页或工具中展示)
  "parsed_content_list": [         // 所有检测到的页面元素列表 (核心数据)
    {
      "type": "text",              // 元素类型: "text" (文本) 或 "icon" (图标)
      "bbox": [0.1, 0.2, 0.3, 0.4],// 归一化坐标 [x1, y1, x2, y2] (0.0~1.0)
      "content": "登录",            // 识别出的文本内容或图标描述
      "interactivity": false,      // 是否可交互 (点击等)
      "source": "box_ocr_content_ocr" // 识别来源
    },
    ...
  ],
  "input_fields": [ ... ],         // (可选) 专门提取的输入框列表，仅当 return_input_fields=true 时返回
  "latency": 0.85                  // 服务端处理耗时 (秒)
}
```

### 1. parsed_content_list 字段详解

这是服务返回的最核心数据，包含了页面上所有被识别出的 UI 元素。

| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `type` | `string` | **元素类型**。<br>• `"text"`: 文字元素。<br>• `"icon"`: 图标或图片元素。 |
| `bbox` | `array` | **归一化坐标** `[x1, y1, x2, y2]`。<br>• 范围 0.0-1.0，表示相对于图片宽高的比例。<br>• 例如 `[0.5, 0.5, 0.6, 0.6]` 表示在图片中心区域。 |
| `content` | `string` | **识别内容**。<br>• 对于 `text` 类型，是 OCR 识别出的文字。<br>• 对于 `icon` 类型，如果启用了 `enable_caption`，则是图标的描述；否则可能为空或包含简单的分类标签。 |
| `interactivity` | `bool` | **交互性**。<br>• 指示该元素是否可能是一个可点击的控件（如按钮、链接）。 |

### 2. input_fields 字段详解

当请求中 `return_input_fields: true` 时返回，专用于自动化填表场景：

| 字段名 | 说明 |
| :--- | :--- |
| `content` | 输入框用途，如 `"输入框:①用户名/手机号"` |
| `bbox_px` | 像素坐标 `[x1, y1, x2, y2]` |
| `bbox_norm` | 归一化坐标 `[0.1, 0.2, 0.3, 0.4]` |

---

## 调试工具

如需调整参数测试效果，可使用提供的 PowerShell 脚本：

```powershell
# 示例：设置自定义阈值并测试
$env:OMNI_URL='http://14.103.175.167:7862/parse/'; $env:OMNI_IMG='E:\path\to\img.png'; $env:OMNI_BOX='0.18'; python tools/http_test_parse.py
```

## RodSki 集成说明

RodSki 调用 OmniParser 服务实现图像识别定位能力。详细设计请参考：[VISION_LOCATION.md](./VISION_LOCATION.md)

---

# DB 关键字 API 文档

本文档描述了 RodSki 数据库操作关键字的 API 规范。

**版本**: v5.0+  
**最后更新**: 2026-04-10

---

## 快速开始

### 基本调用

```xml
<test_step action="DB" model="DatabaseModel" data="DataRowID"/>
```

### 参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `action` | string | 是 | 固定值 `"DB"` |
| `model` | string | 是 | 数据库模型名称（`type="database"`） |
| `data` | string | 是 | 数据行 ID |

---

## 模型定义 API

### 基本结构

```xml
<model name="ModelName" type="database" connection="ConnectionName" servicename="描述">
    <!-- 查询模板（可选） -->
    <query name="QueryName" remark="说明">
        <sql>SQL语句</sql>
        <params>
            <param name="参数名" type="类型" default="默认值" required="true/false"/>
        </params>
    </query>
    
    <!-- 结果字段定义（用于 verify） -->
    <element name="FieldName" type="database">
        <location type="field">字段名</location>
        <desc>字段描述</desc>
    </element>
</model>
```

### 模型属性

| 属性 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 模型名称 |
| `type` | string | 是 | 固定值 `"database"` |
| `connection` | string | 是 | 连接配置名称（GlobalValue 中的 group name） |
| `servicename` | string | 否 | 模型描述 |

### 查询模板 API

#### `<query>` 标签

| 属性 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 查询名称（唯一标识） |
| `remark` | string | 否 | 查询说明 |

#### `<sql>` 标签

包含 SQL 语句，支持：
- 多行格式（使用 CDATA）
- 参数占位符（`:param` 语法）

```xml
<sql><![CDATA[
    SELECT * FROM orders 
    WHERE status = :status 
    LIMIT :limit
]]></sql>
```

#### `<params>` 标签

定义查询参数：

| 属性 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 参数名称（对应 SQL 中的 `:param`） |
| `type` | string | 否 | 参数类型：`string`, `int`, `decimal`, `bool` |
| `default` | string | 否 | 默认值 |
| `required` | bool | 否 | 是否必填，默认 `false` |

---

## 数据表 API

### 模式 1: 直接 SQL

```xml
<datatable name="ModelName">
    <row id="DataID" remark="说明">
        <field name="sql">SQL语句</field>
        <field name="operation">query/execute</field>
    </row>
</datatable>
```

#### 字段说明

| 字段 | 类型 | 必填 | 说明 | 默认值 |
|------|------|------|------|--------|
| `sql` | string | 是 | SQL 语句 | - |
| `operation` | string | 否 | 操作类型：`query`（查询）/ `execute`（执行） | `query` |

### 模式 2: 引用查询模板

```xml
<datatable name="ModelName">
    <row id="DataID" remark="说明">
        <field name="query">QueryName</field>
        <field name="param1">value1</field>
        <field name="param2">value2</field>
    </row>
</datatable>
```

#### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `query` | string | 是 | 模型中定义的查询名称 |
| 其他字段 | any | 否 | 查询参数（对应模板中的 `:param`） |

---

## 连接配置 API

在 GlobalValue 中定义数据库连接：

### SQLite

```xml
<group name="ConnectionName">
    <var name="type" value="sqlite"/>
    <var name="database" value="文件路径"/>
</group>
```

### MySQL

```xml
<group name="ConnectionName">
    <var name="type" value="mysql"/>
    <var name="host" value="主机地址"/>
    <var name="port" value="端口"/>
    <var name="user" value="用户名"/>
    <var name="password" value="密码"/>
    <var name="database" value="数据库名"/>
</group>
```

### PostgreSQL

```xml
<group name="ConnectionName">
    <var name="type" value="postgresql"/>
    <var name="host" value="主机地址"/>
    <var name="port" value="端口"/>
    <var name="user" value="用户名"/>
    <var name="password" value="密码"/>
    <var name="database" value="数据库名"/>
</group>
```

### SQL Server

```xml
<group name="ConnectionName">
    <var name="type" value="sqlserver"/>
    <var name="host" value="主机地址"/>
    <var name="port" value="端口"/>
    <var name="user" value="用户名"/>
    <var name="password" value="密码"/>
    <var name="database" value="数据库名"/>
</group>
```

---

## 返回值 API

### 自动保存

所有 DB 查询结果自动保存到 `${Return[-1]}`。

### 返回格式

#### 查询操作（query）

```python
[
    {"field1": "value1", "field2": "value2"},
    {"field1": "value3", "field2": "value4"}
]
```

#### 执行操作（execute）

```python
{"affected_rows": 1}
```

#### 大数据量截断

当查询结果超过 1000 行时：

```python
{
    "_truncated": True,
    "_total_rows": 5000,
    "data": [...]  # 前 1000 行
}
```

### 访问返回值

```xml
<!-- 访问第一条记录的字段 -->
<test_step action="assert" condition="${Return[-1][0].field_name} == 'expected'"/>

<!-- 获取记录数量 -->
<test_step action="assert" condition="${len(Return[-1])} == 5"/>

<!-- 检查是否被截断 -->
<test_step action="assert" condition="${Return[-1].get('_truncated', False)} == False"/>
```

---

## 错误处理

### 常见错误码

| 错误类型 | 说明 | 解决方案 |
|---------|------|---------|
| `ConnectionError` | 数据库连接失败 | 检查连接配置、网络、数据库服务状态 |
| `SQLSyntaxError` | SQL 语法错误 | 检查 SQL 语句语法 |
| `ParameterError` | 参数缺失或类型错误 | 检查数据表中的参数定义 |
| `ModelNotFound` | 模型未找到 | 检查模型名称是否正确 |
| `QueryNotFound` | 查询模板未找到 | 检查 query name 是否在模型中定义 |

### 错误日志

错误信息会输出到日志，包含：
- SQL 语句
- 参数值
- 错误堆栈

---

## 性能优化

### 连接复用

- 同一连接配置在测试执行期间会复用连接
- 连接存储在内存中，避免重复创建
- 测试结束后自动关闭所有连接

### 查询优化建议

1. **使用 LIMIT 控制返回量**
   ```sql
   SELECT * FROM orders LIMIT 100
   ```

2. **使用索引字段作为查询条件**
   ```sql
   SELECT * FROM orders WHERE order_no = :order_no  -- order_no 有索引
   ```

3. **避免 SELECT ***
   ```sql
   SELECT order_no, customer_name FROM orders  -- 只查询需要的字段
   ```

4. **使用参数化查询**
   ```sql
   SELECT * FROM orders WHERE status = :status  -- 使用参数，避免 SQL 注入
   ```

---

## 安全性

### SQL 注入防护

**强制使用参数化查询**：

```xml
<!-- ✅ 安全：使用参数占位符 -->
<sql>SELECT * FROM orders WHERE status = :status</sql>

<!-- ❌ 危险：直接拼接字符串 -->
<sql>SELECT * FROM orders WHERE status = 'completed'</sql>
```

### 权限控制

建议为测试账号配置最小权限：
- 只读账号：只授予 SELECT 权限
- 测试账号：授予 SELECT, INSERT, UPDATE, DELETE 权限
- 避免使用 root/sa 等超级管理员账号

---

## 相关文档

- [DB_USAGE_GUIDE.md](./DB_USAGE_GUIDE.md) - 数据库使用指南
- [DB_DRIVER_SUPPORT.md](./DB_DRIVER_SUPPORT.md) - 数据库驱动支持
- [SKILL_REFERENCE.md](./SKILL_REFERENCE.md) - DB 关键字语法参考

---

**API 版本**: v5.0  
**最后更新**: 2026-04-10
