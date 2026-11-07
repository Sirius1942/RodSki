# RodSki API 参考

**版本**: v11.12.0  
**最后更新**: 2026-10-22

本文档包含两部分，彼此独立：

| 部分 | 内容 | 性质 |
|------|------|------|
| [第一部分](#第一部分omniparser-远程服务接口外部视觉服务) | OmniParser 视觉解析服务的 HTTP 接口 | **外部服务**的接口说明，不是 RodSki 框架自身的 API。v7.1.0 起 RodSki 核心已删除内置的 OmniParser 客户端，视觉定位改走 `PerceptionBackend`（见 VISION_LOCATION.md）；本部分仅供直接调用该服务或自建 backend 时参考 |
| [第二部分](#第二部分db-关键字-api) | `DB` 关键字的模型、数据表、连接配置与返回值 | RodSki 关键字 API |

其他关键字的语法见 [SKILL_REFERENCE.md](./SKILL_REFERENCE.md) 与 [TEST_CASE_WRITING_GUIDE.md](./TEST_CASE_WRITING_GUIDE.md) §8。

---

# 第一部分：OmniParser 远程服务接口（外部视觉服务）

本部分描述 OmniParser 视觉解析服务的接口规范。

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

如需调整参数测试效果，可直接向服务 POST 一张图片。仓库根目录的 `tools/test_omniparser.py` 是一个最小调用示例（`test_omniparser(image_path, omni_url=...)`，把 `omni_url` 换成你的服务地址）：

```bash
# 示例：用 curl 发送 base64 图片（<server_ip> 替换为实际服务地址）
python3 -c "import base64,json;print(json.dumps({'base64_image':base64.b64encode(open('img.png','rb').read()).decode(),'box_threshold':0.18}))" \
  | curl -s -X POST -H 'Content-Type: application/json' -d @- http://<server_ip>:7862/parse/
```

## RodSki 集成说明

v7.1.0 起 RodSki 核心不再直接调用 OmniParser：内置的 OmniParser 客户端（OmniClient）已删除，`vision_config.yaml` 中的 `omniparser` 配置段在加载时被丢弃。`vision` / `ocr` 等视觉定位由 `PerceptionBackend` 提供。详细设计请参考：[VISION_LOCATION.md](./VISION_LOCATION.md)

---

# 第二部分：DB 关键字 API

本部分描述 RodSki 数据库操作关键字 `DB` 的 API 规范。当前语法（`model` 填数据库模型名、`data` 只写 DataID）自 v5.0 起使用；旧写法 `model="连接名" data="表名.DataID"` 会直接报错。

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

#### 查询参数

`<query>` 下只有一个 `<sql>` 子元素，**没有** `<params>` 标签（`model.xsd` 会拒绝）。参数不在模型中声明，也没有默认值：

- SQL 中的 `:name` 取数据行中同名字段的值；`name` 须以字母或下划线开头，写在引号内的冒号（如 `'00:00:00'`）不会被当作参数。
- SQL 引用的参数在数据行中不存在时，步骤报参数错误。
- 字段值为 `NULL` 时替换为 SQL `NULL`；数字类型的值原样替换；其余值按字符串加单引号替换（单引号自动转义）。

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

> 同一逻辑表所有行的字段集合必须一致（v6.7.6）。两种模式混用一张表时，用不到的 `sql` / `query` 等字段填 `BLANK` / `NULL` / `NONE`：DB 关键字把这三个值和空串都视为未提供。数据行实际存放在 `data/data.sqlite`，上面的 `<datatable>` 只是示意。

---

## 连接配置 API

在 GlobalValue 中定义数据库连接（组名即模型的 `connection` 属性值）。可用的键：`type`（默认 `sqlite`）、`host`（默认 `localhost`）、`port`、`database`、`username`、`password`。`type` 取值：`sqlite`、`mysql` / `mariadb`、`postgresql` / `postgres` / `pg`、`sqlserver` / `mssql`。

### SQLite

```xml
<group name="ConnectionName">
    <var name="type" value="sqlite"/>
    <var name="database" value="文件路径"/>
</group>
```

SQLite 的相对路径按测试模块目录（`case/` 的上级）解析。

### MySQL

```xml
<group name="ConnectionName">
    <var name="type" value="mysql"/>
    <var name="host" value="主机地址"/>
    <var name="port" value="端口"/>
    <var name="username" value="用户名"/>
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
    <var name="username" value="用户名"/>
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
    <var name="username" value="用户名"/>
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
    "_limit": 1000,
    "data": [...]  # 前 1000 行
}
```

### 访问返回值

`assert` 是图片 / 视频视觉断言，`test_step` 也没有 `condition` 属性，不能用来断言查询结果。校验查询结果用 `verify` 配合 DB 模型的 `_verify` 表：

```xml
<!-- 查询 -->
<test_step action="DB" model="OrderQuery" data="Q001"/>
<!-- OrderQuery_verify.V001 中写期望值，如 order_no=ORD001、total_amount={"$gt": 100} -->
<test_step action="verify" model="OrderQuery" data="V001"/>
```

- DB 的 `verify` 只比较 `_verify` 行中写出的字段，实际值取查询结果的**第一行**；`BLANK` / `NONE` 跳过该字段；查询结果为空时失败。
- `_verify` 表中禁止引用 `${Return[-1]}`（CORE §4.3）。
- 后续步骤要使用查询结果时，在该步骤数据行的字段值中引用：`${Return[-1][0].order_no}` 取第一行字段，`${Return[-1].length}` 取行数。

---

## 错误处理

### 常见错误码

| 错误码 / 异常类 | 触发场景 | 解决方案 |
|---------|------|---------|
| `SKI312` `InvalidParameterError` | 缺少 `model` / `data`；`data` 写成旧语法 `表名.DataID`；模型不存在或不是 `type="database"`；模型缺 `connection`；数据行不存在；`query` 引用的查询未定义；数据行既无有效 `sql` 也无有效 `query`；SQL 引用的参数在数据行中不存在 | 按报错信息修正模型或数据行 |
| `SKI302` `DriverError` | 数据库连接失败（连接组未配置或连不上）；SQL 执行失败（含语法错误） | 检查 GlobalValue 连接组、网络、数据库服务状态和 SQL |
| `SKI331` `AssertionFailedError` | DB 结果的 `verify` 不通过（字段不一致、结果为空、缺字段、比较字段数为 0） | 核对 `_verify` 期望值或查询 |

### 错误日志

执行日志记录：
- 执行的 SQL（已替换参数，截取前 80 个字符）和操作类型
- SQL 执行失败的原因

---

## 性能优化

### 连接复用

- 同一连接配置在测试执行期间会复用连接（复用前用 `SELECT 1` 检测存活，失效则重建）
- 连接存储在内存中，避免重复创建
- 执行结束后自动关闭所有连接

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

**推荐使用参数占位符**（框架不强制）。注意：`:param` 是框架在发送前做的文本替换（字符串值加单引号并转义单引号），不是数据库驱动层的参数绑定：

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

**文档版本**: v11.10.0  
**最后更新**: 2026-10-22
