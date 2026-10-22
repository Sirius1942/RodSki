# Skill 参考文档

**版本**: v11.10.0
**日期**: 2026-10-22
**目标读者**: AI Agent

> 本文是常用关键字的速查。关键字共 17 个（另有兼容项 `check`，等同 `verify`），完整清单与语义以 TEST_CASE_WRITING_GUIDE §3.6、§8 和 CORE_DESIGN_CONSTRAINTS §5 为准。
>
> 文中 `<datatable>` / `<row>` / `<field>` 只用于示意数据行内容。测试数据实际存放在 `data/data.sqlite`（用 `rodski data add-row` / `rodski data set` 写入），`data.xml` 已废弃。

---

## 1. 核心 Skill

### 1.1 navigate - 页面导航

**用途**: 打开 URL 或切换页面

**语法**:
```xml
<test_step action="navigate" model="" data="https://example.com"/>
```

**参数**:
- `model`: 留空
- `data`: URL 地址

**示例**:
```xml
<test_step action="navigate" model="" data="https://github.com/login"/>
```

---

### 1.2 type - 输入文本

**用途**: 在输入框中输入文本

**语法**:
```xml
<test_step action="type" model="PageModel" data="DataRowID"/>
```

**参数**:
- `model`: 页面模型名称
- `data`: 数据行 ID

**数据表结构**:
```xml
<datatable name="PageModel">
  <row id="DataRowID">
    <field name="elementName">输入内容</field>
  </row>
</datatable>
```

**示例**:
```xml
<!-- 用例 -->
<test_step action="type" model="LoginPage" data="L001"/>

<!-- 数据 -->
<row id="L001">
  <field name="username">admin</field>
  <field name="password">123456</field>
</row>
```

**注意**:
- 字段值为空串时跳过该字段，**不会清空**输入框（v11.8.21）；`BLANK` / `NULL` / `NONE` 同样跳过。要清空输入框请用 `clear`（见 1.10）。

---

### 1.3 click - 点击元素（数据表字段值，不是关键字）

**用途**: 点击按钮、链接等元素

> `click` / `double_click` / `right_click` / `hover` / `select【值】` / `key_press【键】` / `drag【目标】` / `scroll` **不是关键字**，不能写在 `action` 中（CORE §1.2）。它们写在数据表字段值里，由 `type` 批量执行。

**语法**:
```xml
<test_step action="type" model="PageModel" data="DataRowID"/>
```

**数据表结构**:
```xml
<field name="elementName">click</field>
```

**示例**:
```xml
<test_step action="type" model="LoginPage" data="C001"/>

<row id="C001">
  <field name="username">admin</field>
  <field name="loginBtn">click</field>
</row>
```

**key_press 说明**（v11.8.27）:
- `key_press【键】` 作用于本字段对应的元素：先聚焦该元素再按键，不是发给页面当前焦点。
- Web（Playwright）在 macOS 上执行时，组合键里的 `Control`（如 `key_press【Control+A】`）按 Command 执行；单独按 `Control` 不转换。

---

### 1.4 verify - 验证元素

**用途**: 按 `模型名_verify` 表中 DataID 行的期望值批量验证；参与比较的字段任一不一致，步骤失败并使 case FAIL。

**语法**:
```xml
<test_step action="verify" model="PageModel" data="DataRowID"/>
```

**数据表结构**:
```xml
<field name="elementName">期望文本</field>
```

**示例**:
```xml
<test_step action="verify" model="HomePage" data="V001"/>

<row id="V001">
  <field name="welcomeMsg">欢迎, admin</field>
</row>
```

**比较哪些字段**:

| 模型类型 | 比较范围 |
|---------|---------|
| UI 模型 | 默认 `match_mode="strict"`：比较模型的全部元素，`_verify` 行必须包含全部字段（不比较的字段填 `BLANK`，否则报错）。`match_mode="subset"`：只比较行内写出、且模型已声明的字段 |
| 接口模型 | 不受 `match_mode` 影响：只比较行内写出、且模型已声明的字段；`status` 即使模型未声明也比较，恒为 HTTP 状态码（响应体里的同名字段写 `body.status`）；`_` 前缀的控制元素不比较 |
| DB 模型 | 不受 `match_mode` 影响：只比较行内写出的字段，实际值取查询结果的第一行 |

- `NONE` 在任何模型中都跳过该字段；`BLANK` 在 UI 模型中跳过，在接口模型中表示期望空串，在 DB 模型中跳过。
- 一行只剩被跳过的字段、实际比较字段数为 0 时，步骤失败。

> 注意：接口/DB 模型的 _verify 数据表禁止使用 ${Return[-1]}，详见 CORE_DESIGN_CONSTRAINTS 4.3 节。

**自动等待（AutoWait）**:

- UI 模型的 `verify` 在 `DefaultValue.AutoWait`（单位毫秒）内自动重试，直到全部字段匹配；异步页面**不需要**先写 `wait`。v11.10.0 起：不设置或空值时默认最多等待 10000ms；填 `0` 关闭自动等待；统一每 1000ms 探测一次。接口 / DB 模型只比对一次。
- v11.7.0 起 `AutoWait` 同样作用于 `type` 批量的**每一个字段**（输入、click、select、hover 等）以及 `get` / `clear` / `upload_file`：元素出现即操作，超时报 `SKI326`。
- 字段值可写操作符：`{"$gt": 100}`、`{"$contains": "x"}`，以及元素级 `{"$count": 10}`、`{"$count_gte": 1}`、`{"$count_lte": 5}`、`{"$exists": true}`、`{"$visible": false}`；0 匹配按实际 0 判定。元素级操作符只能用于 UI 模型。
- URL / 路径 / 标题 / 弹窗文本：模型元素用 `<location type="page">url|path|title|dialog</location>`。
- 详见 TEST_CASE_WRITING_GUIDE §5.7、CORE §4.6。

---

### 1.5 wait - 等待

**用途**: 固定等待指定秒数

> 等异步结果不要用 `wait`：UI `verify` 会自动重试到期望值（v11.6.0）。`wait` 只用于演示、录屏或确需固定时长的场景；用例中出现数字字面量 `wait` 时 `rodski case lint` 给出 WARNING。

**语法**:
```xml
<test_step action="wait" model="" data="秒数"/>
```

**示例**:
```xml
<test_step action="wait" model="" data="3"/>
```

---

### 1.6 close - 关闭浏览器

**用途**: 关闭浏览器或应用

**语法**:
```xml
<test_step action="close" model="" data=""/>
```

---

### 1.7 set - 命名变量

**用途**: 把表达式结果存为命名变量，供后续步骤通过 `${key}` 引用

**语法**:
```xml
<test_step action="set" model="" data="key=value_expr"/>
```

`model` 必须为空。`data` 为 `key=表达式` 形式，表达式里可用 `${Return[-N]}` 和
**纯函数类**内置函数（`encodeURI` / `toUpperCase` / `toString36` / ...）。

**示例**:
```xml
<!-- 保存接口返回的 token -->
<test_step action="send" model="LoginAPI" data="L001"/>
<test_step action="set" model="" data="auth_token=${Return[-1].token}"/>

<!-- 分步表达式（内置函数不支持嵌套，用多次 set 替代） -->
<test_step action="set" model="" data="raw=Hello"/>
<test_step action="set" model="" data="up=${toUpperCase(${raw})}"/>
<test_step action="set" model="" data="enc=${encodeURI(${up})}"/>
```

**注意**:
- `set` **不产生 Return 值** —— 它不改变 `${Return[-N]}` 的指向。上例中 set 之后
  `${Return[-1]}` 仍指 send 的响应。
- 读回变量用 `${key}`、`get | | key`，或 `context.named`。
- `random` / `date` / `timestamp*` 属**数据生成类**，写在 `set` 的 `data` 里会报错
  （会让用例不可复现）。这类数据放 `data.sqlite` 字段值中。

---

### 1.8 get - 取值

**用途**: 按三种模式取值并写入 Return 历史

**语法**:
```xml
<test_step action="get" model="模型名" data="DataID"/>   <!-- 模型模式 -->
<test_step action="get" model="" data="#selector"/>      <!-- UI 选择器模式 -->
<test_step action="get" model="" data="varName"/>        <!-- 命名访问模式 -->
```

| 模式 | 触发条件 | 返回 |
|------|---------|------|
| 模型模式 | `model` 非空 + `data` 为 DataID | 该 UI 模型各元素文本的 dict |
| UI 选择器模式 | `model` 空 + `data` 以 `#` `.` `//` `css=` `xpath=` `id=` `text=` 开头 | 元素文本 |
| 命名访问模式 | `model` 空 + `data` 为普通标识符 | 之前 `set` 存入的值 |

**示例**:
```xml
<test_step action="set" model="" data="mykey=world"/>
<test_step action="get" model="" data="mykey"/>     <!-- Return[-1] == "world" -->
```

**注意**: `get_text` 仍在 17 个关键字中，但已废弃：执行时发 DeprecationWarning 并按 `get` 处理，请改用 `get`。命名访问模式下
key 不存在会抛 `InvalidParameterError`。

---

### 1.9 send - 发送接口请求

**用途**: 按接口模型（`type="interface"`）和数据行组装并发送 HTTP 请求，与 UI 的 `type` 对称

**语法**:
```xml
<test_step action="send" model="LoginAPI" data="L001"/>
```

- `model` 必须是接口模型；`data` 只写 DataID。
- 模型中 `_method`、`_url`、`_header_*` 为保留元素，其余元素为请求字段（POST/PUT/PATCH 作为 JSON body，GET/DELETE 拼成查询参数）。
- 响应写入 Return：`status` 为 HTTP 状态码，响应字段平铺，完整响应体在 `body`。之后用 `verify` 同一模型名校验。
- 详见 TEST_CASE_WRITING_GUIDE §8.2、§8.3。

---

### 1.10 clear - 清空输入框

**语法**:
```xml
<test_step action="clear" model="" data="#username"/>
```

- `model` 留空；`data` 写元素定位（CSS 选择器，或 `id=`、`xpath=` 等前缀写法）。
- 受 AutoWait 约束：等待元素出现后清空。

---

### 1.11 upload_file - 上传文件

**语法**:
```xml
<test_step action="upload_file" model="#fileInput" data="fun/site/upload_sample.txt"/>
```

- `model` 写 file input 的元素定位（CSS 选择器等），`data` 写文件路径；相对路径按执行时的当前工作目录解析。
- 受 AutoWait 约束：等待 file input 出现后上传。

---

### 1.12 evaluate - 执行 JavaScript（仅 Web）

**语法**:
```xml
<test_step action="evaluate" model="" data="document.title"/>
<test_step action="evaluate" model="" data="file:fun/js/check_rows.js"/>
```

- 在当前页面执行表达式，返回值写入 Return；脚本抛异常时步骤失败。
- `file:` 后写模块目录内的相对路径，脚本内容原样执行；绝对路径或越出模块目录会被拒绝。
- 它是逃生舱：数量、存在、可见、URL、标题、弹窗等有原生写法（GUIDE §5.7.4），优先用 `verify`。详见 GUIDE §8.7。

---

### 1.13 assert - 图片 / 视频视觉断言

**用途**: 截图（或录像关键帧）与预期图片比对相似度。值断言请用 `verify`，`assert` 不支持表达式。

**语法**:
```xml
<test_step action="assert" model="" data="assert[type=image,reference=login_ok.png,threshold=0.85]"/>
```

- `type`：`image`（默认）或 `video`。
- `reference`：预期图片，相对路径按 `<模块>/images/assert/` 解析。
- `threshold` 默认 0.8；`scope=full|element`（element 时配 `element_bbox=x,y,w,h`）；`wait` 为秒，默认 0。
- `type=video` 另有 `video_source`（默认 `recording`）、`position=start|middle|end|any`、`time_range=起,止`。
- 相似度低于阈值时步骤失败（v11.8.17 起）。运行环境需要安装 OpenCV（`cv2`）与 NumPy，缺失时报错。
- `case.xsd` 中 `test_step` 只有 `action` / `model` / `data` / `match_mode` 四个属性，没有 `condition` 属性。

---

## 2. 桌面自动化 Skill

### 2.1 launch - 启动应用

**用途**: 启动桌面应用程序；在 Web 下也可打开 http(s) 页面

**启动桌面应用**：使用 `driver_type="windows"` 或 `"macos"` 的 Desktop 模型，`data` 写 DataID，数据行提供 `app_path` 或 `app_name` 字段。

```xml
<!-- model.xml -->
<model name="NotepadApp" driver_type="windows"/>

<!-- 用例 -->
<test_step action="launch" model="NotepadApp" data="A001"/>
```

```xml
<!-- 数据（data.sqlite 中 NotepadApp 表，示意） -->
<datatable name="NotepadApp">
  <row id="A001">
    <field name="app_path">notepad.exe</field>
  </row>
</datatable>
```

**Web 模型或 `model` 为空时**：`data` 只接受完整的 `http://` / `https://` URL，效果等同 `navigate`。写应用名、应用路径、`ftp://` 或漏写协议都会报参数错误（v11.8.26 起）。

```xml
<test_step action="launch" model="" data="https://example.com"/>
```

- 接口模型不能用 `launch`（报错，改用 `send`）。

---

### 2.2 run - 执行脚本

**用途**: 调用 `fun/` 下的脚本（键盘快捷键、鼠标操作、数据生成等），或调用框架内置函数

**语法**:
```xml
<test_step action="run" model="" data="脚本路径 参数"/>
```

**示例**:
```xml
<!-- 复制粘贴 -->
<test_step action="run" model="" data="fun/desktop/key_combo.py Ctrl+C"/>
<test_step action="run" model="" data="fun/desktop/key_combo.py Ctrl+V"/>

<!-- 鼠标操作 -->
<test_step action="run" model="" data="fun/desktop/mouse_click.py 100,200"/>
```

- `model` 非空时表示 `fun/` 下的工程名，脚本路径相对该工程目录；脚本的 stdout 作为返回值（尝试按 JSON 解析）。

**内置函数**（进程内执行，**`model` 必须为空**）:

`data` 写成 `函数名(参数...)` 且 `model=""` 时，先按内置函数查找；`model` 非空时会被当作 `fun/` 下的工程名和脚本路径，找不到即报错。

```xml
<test_step action="run" model="" data="mock_route(url_pattern='**/api/users', status=200, body='[]')"/>
```

| 函数 | 参数与默认值 | 说明 |
|------|------------|------|
| `mock_route` | `url_pattern`, `status=200`, `body=''`, `content_type='application/json'` | 拦截匹配的请求并返回自定义响应。`url_pattern` 按 Playwright glob 匹配，加 `re:` 前缀表示正则。仅 Web |
| `clear_routes` | 无 | 清除所有 mock route（需 Playwright ≥ 1.29，否则返回 False） |
| `wait_for_response` | `url_pattern`, `timeout=30`（秒） | 等待**调用之后**到达、URL 包含 `url_pattern`（子串匹配）的响应；调用前已返回的响应不会被匹配。返回 `{url, status, body, json?}`，超时步骤失败 |
| `start_js_coverage` | 无 | 开始采集 JS 覆盖率（仅 Chromium） |
| `stop_js_coverage` | `output='coverage.json'` | 停止采集并写出结果；相对路径按当前工作目录解析 |
| `save_auth_state` | `name` | 把当前登录态保存到本次 run 的内存中（不落盘） |
| `use_auth_state` | `name` | 为当前用例加载已保存的登录态，须在 `navigate` 之前调用 |

以上 7 个是当前注册的全部内置函数（`rodski/builtin_ops/__init__.py`）。详见 TEST_CASE_WRITING_GUIDE §8.6、§8.8。

---

## 3. 高级 Skill

### 3.1 switch_window - 切换窗口（不是关键字）

> `switch_window` **不在** 17 个关键字中（CORE §5），不能写在 `action` 中，写了会在 XSD 校验阶段报错。

---

### 3.2 iframe 内元素（`location@frame`，v11.6.0）

> `switch_frame` **不是关键字**。iframe 内的元素在模型的 `<location>` 上加 `frame` 属性（定位 iframe 的 CSS 选择器，多层用 ` >> ` 串联），`type` / `verify` 照常使用。

**模型**:
```xml
<element name="cardNo" type="web">
    <location type="css" frame="#payFrame">#cardNo</location>
</element>
<element name="agree" type="web">
    <location type="id" frame="#outerFrame >> #termsFrame">agree</location>
</element>
```

**用例**:
```xml
<test_step action="type" model="PayFrame" data="P001"/>
<test_step action="verify" model="PayFrame" data="V001"/>
```

---

### 3.3 screenshot - 截图

**用途**: 保存当前页面截图

**语法**:
```xml
<test_step action="screenshot" model="" data="文件名"/>
```

**示例**:
```xml
<test_step action="screenshot" model="" data="login_page.png"/>
```

---

## 4. Skill 组合模式

### 4.1 登录流程

```xml
<test_case>
  <test_step action="navigate" model="" data="https://example.com/login"/>
  <!-- L001：username / password 填输入值，loginBtn 填 click -->
  <test_step action="type" model="LoginPage" data="L001"/>
  <test_step action="verify" model="HomePage" data="V001"/>
</test_case>
```

### 4.2 表单填写

```xml
<test_case>
  <!-- F001：各输入字段填值，提交按钮字段填 click -->
  <test_step action="type" model="FormPage" data="F001"/>
  <test_step action="verify" model="FormPage" data="V001"/>
</test_case>
```

### 4.3 桌面应用操作

```xml
<test_case>
  <test_step action="launch" model="NotepadApp" data="A001"/>
  <test_step action="type" model="NotepadPage" data="T001"/>
  <test_step action="run" model="" data="fun/desktop/key_combo.py Ctrl+S"/>
  <test_step action="close" model="" data=""/>
</test_case>
```

---

## 5. 数据库操作 Skill

### 5.1 DB - 数据库查询和操作

**用途**: 执行数据库查询、插入、更新、删除操作

**语法**:
```xml
<test_step action="DB" model="DatabaseModel" data="DataRowID"/>
```

**参数**:
- `model`: 数据库模型名称（`type="database"`）
- `data`: 数据行 ID

**模型定义**:
```xml
<model name="OrderQuery" type="database" connection="sqlite_db" servicename="订单查询">
    <!-- 查询模板定义：<query> 下只有 <sql>，参数值取自数据行的同名字段 -->
    <query name="list" remark="查询订单列表">
        <sql><![CDATA[
            SELECT order_no, customer_name, total_amount
            FROM orders
            WHERE status = :status
            LIMIT :limit
        ]]></sql>
    </query>

    <!-- 结果字段定义（用于 verify） -->
    <element name="order_no" type="database">
        <location type="field">order_no</location>
        <desc>订单号</desc>
    </element>
</model>
```

**数据表结构（模板模式）**:
```xml
<datatable name="OrderQuery">
    <row id="Q001" remark="查询已完成订单">
        <field name="query">list</field>
        <field name="status">completed</field>
        <field name="limit">5</field>
    </row>
</datatable>
```

**数据表结构（直接 SQL 模式）**:
```xml
<datatable name="OrderQuery">
    <row id="Q001" remark="查询订单">
        <field name="sql"><![CDATA[
            SELECT * FROM orders WHERE status = 'completed' LIMIT 5
        ]]></field>
        <field name="operation">query</field>
    </row>
</datatable>
```

> 同一逻辑表所有行的字段集合必须一致（v6.7.6）。两种模式写在同一张表时，用不到的字段填 `BLANK` / `NULL` / `NONE`：DB 关键字把这三个值和空串都视为未提供。

**返回值**:
- 查询操作：返回列表 `[{row1}, {row2}, ...]`，自动保存到 `${Return[-1]}`
- 执行操作：返回 `{"affected_rows": N}`

**示例**:
```xml
<!-- 查询订单 -->
<test_step action="DB" model="OrderQuery" data="Q001"/>

<!-- 验证结果：OrderQuery_verify.V001 写 order_no=ORD001，与查询结果第一行比较 -->
<test_step action="verify" model="OrderQuery" data="V001"/>

<!-- 插入订单 -->
<test_step action="DB" model="OrderQuery" data="Q002"/>
```

**连接配置（GlobalValue）**:
```xml
<globalvalue>
    <group name="sqlite_db">
        <var name="type" value="sqlite"/>
        <var name="database" value="demo.db"/>
    </group>
</globalvalue>
```

**注意事项**:
- SQL 必须定义在模型或数据表中，不能在测试用例中直接写 SQL
- 推荐使用模型定义查询模板，数据表只提供参数
- 查询结果默认最多返回 1000 行，超出会自动截断
- 参数化查询使用 `:param` 语法；SQL 引用的参数在数据行中不存在时报错

---

## 6. 控制结构

### 6.1 `<if>` / `<elif>` / `<else>` 条件块

**用途**: 在当前步骤序列中按条件执行分支。`<if>` 不是关键字动作，不写 `action`；它是 case XML 的控制容器。

**语法**:
```xml
<if condition="${Return[-1]} != ''">
  <test_step action="verify" model="TestForm" data="V001"/>
  <else>
    <test_step action="wait" model="" data="1"/>
  </else>
</if>
```

`<elif>` 写在 `</if>` 之后（与 `<if>` 同级），`<else>` 可以写在 `<if>` 内部末尾，也可以紧跟在 `<if>` / `<elif>` 之后：

```xml
<if condition="${Return[-1].status} == 200">
  <test_step action="send" model="OrderAPI" data="D001"/>
</if>
<elif condition="${Return[-1].status} == 401">
  <test_step action="send" model="LoginAPI" data="D001"/>
</elif>
<else>
  <test_step action="set" model="" data="error_msg=unknown"/>
</else>
```

**条件写法**（以 `rodski/core/dynamic_executor.py` 为准）:

| 写法 | 说明 |
|------|------|
| `${Return[-1].status} == 200`、`${Return[-1].status == 200}` | Return 字段比较，两种写法等价。Return 下标不存在时按 False；字段不存在时按空串比较 |
| `${var} == 值` | 引用 `set` 变量或 `<loop>` 的循环变量 |
| `==` `!=` `contains` | 按字符串比较；值可加引号（`'abc'`） |
| `>` `<` `>=` `<=` | 按数值比较 |
| `verify_fail` | 上一步 verify 失败 |
| `element_exists(定位)` / `element_not_exists(定位)` | 页面元素是否存在；定位写 `id=` / `class=` / `css=` / `xpath=` / `text=` / `name=` / `tag=` 前缀，或直接写 CSS 选择器（如 `#dialog`） |
| `text_contains(文本)` / `text_not_contains(文本)` | 页面文本是否包含 |
| `A AND B`、`A OR B`、`NOT A` | 逻辑组合；不支持括号分组，不要在同一条件里混用 AND 与 OR |

**条件无法评估时的当前行为**（引用了未定义的变量、`>` 等两侧无法转成数字、`element_exists` 定位出错等）:
- `<if>` 的条件无法评估：记录警告并截图，跳过整个 if 链（含 elif / else）。
- `<elif>` 的条件无法评估：跳过该 elif，继续判断后面的 elif，都不成立时执行 else。
- 无法识别的条件写法按 False 处理。

该行为可能调整，写条件时应保证引用的变量已定义。

**边界**:
- `<if>` 可出现在 `<test_case>` 的裸步骤序列中，也可出现在 `<scenario>`、`<loop>`、`<pre_process>`、`<post_process>` 内。
- `<if>` 只控制自身内部的 `test_step` / `business_call` / 嵌套 `if`（最多 2 层），不会跨出当前 `<scenario>` 或当前阶段。
- `<elif>` / `<else>` 必须紧跟对应 `<if>` 链；不要把一个分支拆到其他 `<scenario>` 中。

### 6.2 `<scenario>` 场景容器

**用途**: 在同一个 case 的 `<test_case>` 内，把步骤分组成可命名、可依赖的验收片段。`<scenario>` 不是关键字动作，不写 `action`。

**语法**:
```xml
<test_case>
  <test_step action="type" model="LoginForm" data="L001"/>

  <scenario id="S001" title="进入功能页" group="smoke" tag="nav,ui">
    <test_step action="type" model="NavMenu" data="N001"/>
  </scenario>

  <scenario id="S002" title="提交表单" group="smoke" tag="form" depends="S001">
    <if condition="${Return[-1]} != ''">
      <test_step action="type" model="TestForm" data="T001"/>
      <else>
        <test_step action="wait" model="" data="1"/>
      </else>
    </if>
  </scenario>
</test_case>
```

**边界**:
- `<test_case>` 中裸 `<test_step>` 与 `<scenario>` 按书写顺序混合执行。
- `<scenario>` 内可使用 `<test_step>`、`<if>/<elif>/<else>`、`<loop>`；`<if>` 的作用域仅限当前 scenario 内部。
- `depends` 第一版只支持同一 case 内的 scenario id。依赖 scenario 为 `FAIL` 或 `SKIP` 时，当前 scenario 标记为 `SKIP` 且内部步骤不执行。
- scenario 不是独立 case；case 级预处理、后处理、截图、录制等仍按原 case 语义处理。

---

## 7. 使用建议

### 7.1 Skill 选择策略

| 场景 | 推荐 Skill |
|------|-----------|
| 打开页面 | navigate |
| 填写表单 | type（数据表中按钮字段填 `click`） |
| 验证结果 | verify |
| 等待加载 | verify（UI 自动重试，v11.6.0）；不要用 wait |
| 接口请求 | send + verify |
| 桌面应用 | launch（Desktop 模型）+ run |

### 7.2 常见错误

| 错误 | 原因 | 解决方案 |
|------|------|---------|
| 元素未找到 | 定位器错误 | 检查 vision 描述或坐标 |
| 操作超时 / `SKI326 元素 X 在 AutoWait=Nms 内未找到` | 元素出现慢、定位器写错、元素被遮挡 | 先核对定位器与页面；确实慢时调大 `DefaultValue.AutoWait`（毫秒，不设置默认 10000，作用于所有查找测试对象的步骤），不要增加 wait 步骤 |
| 验证失败 | 期望值不匹配 | 更新数据表中的期望值 |
| `launch` 报参数错误 | Web 模型或 `model=""` 时写了应用名 / 非 http(s) 目标 | 打开页面写完整 URL；启动桌面应用改用 Desktop 模型 |

---

**文档版本**: v11.10.0
**最后更新**: 2026-10-22
