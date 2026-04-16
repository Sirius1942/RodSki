# Agent 集成指南

**版本**: v3.0
**日期**: 2026-04-13
**目标读者**: AI Agent 开发者

---

## 1. 概述

### 1.1 集成模式

RodSki 作为执行引擎，Agent 作为智能层：

```
Agent (探索/决策) → XML (活文档) → RodSki (执行) → 结果 → Agent (分析)
```

**重要**：RodSki 是 Agent 的执行工具和协议层，不是 Agent 框架。RodSki 不编排 Agent，不管理对话，不做规划决策。Agent 调用 RodSki，RodSki 返回确定性结果。

### 1.2 核心职责

| 组件 | 职责 |
|------|------|
| Agent | 页面探索、XML 生成、结果分析、策略调整 |
| RodSki | XML 解析、操作执行、结果返回 |

---

## 2. 集成步骤

### 2.1 环境准备

```bash
# 克隆项目
git clone <repo>
cd rodski

# 安装依赖
pip install -r requirements.txt

# 验证安装
python rodski/ski_run.py --version
```

### 2.2 基础调用

```python
import subprocess
from pathlib import Path

# 执行测试
result = subprocess.run(
    ["python", "rodski/ski_run.py", "case/test.xml"],
    capture_output=True,
    text=True
)

# 检查结果
if result.returncode == 0:
    print("执行成功")
else:
    print(f"执行失败: {result.stderr}")
```

### 2.3 结果解析

```python
import xml.etree.ElementTree as ET

# 读取结果文件
result_file = "result/result_<timestamp>.xml"
tree = ET.parse(result_file)
root = tree.getroot()

# 提取摘要
summary = root.find("summary")
total = summary.get("total")
passed = summary.get("passed")
failed = summary.get("failed")

# 分析失败用例
for result in root.findall(".//result[@status='FAIL']"):
    case_id = result.get("case_id")
    error = result.find("error").text
    # Agent 分析错误并决策
```

---

## Agent 接口契约

### CLI 命令

| 命令 | 用途 | 输出 |
|------|------|------|
| `rodski run <path> [--output-format json]` | 执行测试 | JSON 结构化结果 |
| `rodski run <path> --dry-run` | 干跑验证（不执行） | 验证结果 |
| `rodski explain <case.xml>` | 用例自然语言解释 | 文本说明 |
| `rodski validate <path>` | XML 格式校验 | 校验结果 |
| `rodski run <path> --headless` | 无头模式执行 | JSON 结果 |

### 唯一输入格式

所有输入均为 XML 文件：
- `case/*.xml` — 用例定义
- `model/model.xml` — 元素模型（唯一定位器格式：`<location type="...">值</location>`）
- `data/data.xml` — 操作数据
- `data/data_verify.xml` — 验证数据（可选）
- `data/globalvalue.xml` — 全局变量

### 唯一输出格式

执行结果为 `execution_summary.json`，结构见 §8。

### 错误契约

| 错误类型 | exit_code | Agent 处理策略 |
|---------|-----------|---------------|
| 元素未找到 | 1 | 重新探索页面，更新 model XML |
| 超时 | 1 | 添加 wait 步骤或增加超时配置 |
| 断言失败 | 1 | 检查预期值或页面状态 |
| XML 格式错误 | 2 | 校验并修复 XML |
| 配置缺失 | 2 | 检查 config 文件 |

---

## 3. XML 生成策略

### 3.1 模型 XML

```python
def generate_model_xml(page_name, elements):
    """
    elements: [{"name": "loginBtn", "loc_type": "vision", "loc_value": "登录按钮"}]
    """
    xml = f'<models>\n  <model name="{page_name}">\n'
    for elem in elements:
        xml += f'    <element name="{elem["name"]}">'
        xml += f'<location type="{elem["loc_type"]}">{elem["loc_value"]}</location>'
        xml += '</element>\n'
    xml += '  </model>\n</models>'

    Path(f"model/{page_name}.xml").write_text(xml)
    return xml
```

### 3.2 用例 XML

```python
def generate_case_xml(case_id, title, steps):
    """
    steps: [{"action": "type", "model": "LoginPage", "data": "L001"}]
    """
    xml = f'<cases>\n  <case execute="是" id="{case_id}" title="{title}">\n'
    xml += '    <test_case>\n'
    for step in steps:
        xml += f'      <test_step action="{step["action"]}" model="{step["model"]}" data="{step["data"]}"/>\n'
    xml += '    </test_case>\n  </case>\n</cases>'

    Path(f"case/{case_id}.xml").write_text(xml)
    return xml
```

### 3.3 数据表 XML

```python
def generate_data_xml(model_name, data_rows):
    """
    data_rows: [{"id": "L001", "fields": {"username": "admin", "password": "123"}}]
    """
    xml = f'<datatable name="{model_name}">\n'
    for row in data_rows:
        xml += f'  <row id="{row["id"]}">\n'
        for name, value in row["fields"].items():
            xml += f'    <field name="{name}">{value}</field>\n'
        xml += '  </row>\n'
    xml += '</datatable>'

    Path(f"data/{model_name}.xml").write_text(xml)
    return xml
```

---

## 4. 关键字与数据规则（Agent 必读）

> Agent 生成 XML 时必须遵循以下规则。完整细节见 `TEST_CASE_WRITING_GUIDE.md`。

### 4.1 数据引用格式

Case XML `data` 属性支持三种引用：

| 格式 | 说明 | 示例 |
|------|------|------|
| `GlobalValue.组名.变量名` | 全局变量 | `GlobalValue.DefaultValue.URL` |
| `表名.DataID` | 整行数据（用于 type/verify） | `Login.L001` |
| `表名.DataID.字段名` | 单个字段值 | `Login.L001.username` |

**解析顺序**：GlobalValue → 数据表字段 → Return。

### 4.2 Return 引用机制

Return 引用用于在步骤间传递数据。

| 格式 | 说明 |
|------|------|
| `${Return[-1]}` | 上一步返回值 |
| `${Return[-2]}` | 上上步返回值 |
| `${Return[0]}` | 第一步返回值 |

**关键规则**：Return 引用 **只能写在数据表 XML 的 `<field>` 值中**，不能写在 Case XML 的 `data` 属性。

```xml
<!-- ✅ 正确：Return 在数据表 field 中 -->
<field name="orderNo">${Return[-1]}</field>

<!-- ❌ 错误：Return 在 Case XML data 属性中 -->
<test_step action="verify" model="Order" data="${Return[-1]}"/>
```

### 4.3 哪些关键字产生 Return 值

| 关键字 | 返回值内容 |
|--------|-----------|
| `get` / `get_text` | 元素文本 |
| `verify` | 批量验证时的实际值字典 |
| `assert` | 断言结果 |
| `type`（批量模式） | 本次输入使用的完整数据行 |
| `send` | HTTP 响应（`status` 状态码 + 响应体字段） |
| `DB` | query → 结果集列表；execute → 受影响行数 |
| `run` | 脚本 stdout 输出（自动尝试 JSON 解析） |

### 4.3.1 推荐：Agent 生成 XML 时优先使用 set/get

Agent 生成用例 XML 时，**步骤间数据传递优先使用 `set`/`get` 命名变量**，而非 Return 索引。

**生成规则：**

1. 当一个步骤的返回值需要被后续步骤引用时，紧跟一条 `set` 步骤将其存入命名变量
2. 后续步骤在数据表 `<field>` 中通过 `${变量名}` 引用
3. 仅当步骤紧邻且无歧义时，才使用 `${Return[-1]}`

**Agent 生成示例：**

```xml
<!-- Agent 生成的接口测试用例 -->
<test_case>
  <!-- 1. 登录获取 token -->
  <test_step action="send" model="LoginAPI" data="D001"/>
  <test_step action="set" model="" data="auth_token=${Return[-1].token}"/>

  <!-- 2. 使用 token 创建订单（${auth_token} 在 data.xml 中引用） -->
  <test_step action="send" model="OrderAPI" data="D001"/>
  <test_step action="set" model="" data="order_id=${Return[-1].orderId}"/>

  <!-- 3. 查询并验证订单（${order_id} 在 data.xml 中引用） -->
  <test_step action="send" model="QueryOrderAPI" data="D001"/>
  <test_step action="verify" model="QueryOrderAPI" data="V001"/>
</test_case>
```

**为什么 Agent 应优先 set/get：**

- **避免索引计算错误**：Agent 生成多步用例时，Return 索引容易因步骤增删而错位
- **提升可维护性**：`${auth_token}` 自描述，无需回溯步骤编号
- **适合迭代修复**：修复失败用例时插入新步骤不影响已有变量引用

> Return 索引仍然支持，适合步骤紧邻的简单场景。

### 4.4 数据表 field 特殊值

`type` 批量输入时，数据表 `<field>` 值中的以下内容有特殊含义：

#### UI 动作关键字

| 动作值 | 说明 |
|--------|------|
| `click` | 点击该元素 |
| `double_click` | 双击 |
| `right_click` | 右键点击 |
| `hover` | 鼠标悬停 |
| `select【选项值】` | 下拉选择（中文方括号） |
| `key_press【按键】` | 键盘按键（如 `Tab`、`Enter`、`Control+A`） |
| `drag【目标定位器】` | 拖拽到目标位置 |
| `scroll` | 默认向下滚动 300px |
| `scroll【x,y】` | 自定义滚动距离 |

```xml
<!-- 示例：含动作关键字的数据行 -->
<row id="L001">
  <field name="username">admin</field>
  <field name="password">admin123</field>
  <field name="loginBtn">click</field>
  <field name="roleSelect">select【管理员】</field>
</row>
```

#### 控制值

| 值 | 说明 |
|----|------|
| `.Password` 后缀 | 输入时去掉后缀，日志中显示 `***` |
| `BLANK` | UI 跳过 / 接口传空字符串 |
| `NULL` / `NONE` | UI 跳过 / 接口传 null |
| 空值（省略 field） | 跳过该元素（不输入） |

### 4.5 send — 接口模型约定

接口模型在 model.xml 中定义，使用以下保留元素名：

| 元素名 | 作用 | 说明 |
|--------|------|------|
| `_method` | HTTP 请求方式 | GET / POST / PUT / DELETE |
| `_url` | 请求地址 | 绝对 URL 或相对路径 |
| `_header_*` | 请求头 | 如 `_header_Authorization`、`_header_Content-Type` |
| 其他 | 请求体/查询参数字段 | POST/PUT → JSON body；GET/DELETE → query 参数 |

```xml
<!-- 接口模型示例 -->
<model name="LoginAPI" servicename="">
    <element name="_method" type="interface">
        <location type="static">POST</location>
    </element>
    <element name="_url" type="interface">
        <location type="static">http://api.example.com/login</location>
    </element>
    <element name="username" type="interface">
        <location type="field">username</location>
    </element>
</model>
```

Case XML 写法：

```xml
<test_step action="send" model="LoginAPI" data="D001"/>
<test_step action="verify" model="LoginAPI" data="V001"/>
```

验证数据文件 `data/LoginAPI_verify.xml`：

```xml
<datatable name="LoginAPI_verify">
  <row id="V001">
    <field name="status">200</field>
    <field name="username">admin</field>
  </row>
</datatable>
```

### 4.6 DB — 数据库关键字

```xml
<test_step action="DB" model="demodb" data="QuerySQL.Q001"/>
```

| 属性 | 说明 |
|------|------|
| `model` | GlobalValue 中的数据库连接组名 |
| `data` | SQL 数据表引用（`表名.DataID`）或直接 SQL |

SQL 数据表格式：

```xml
<datatable name="QuerySQL">
  <row id="Q001" remark="查询总数">
    <field name="sql">SELECT COUNT(*) as cnt FROM items</field>
    <field name="operation">query</field>
    <field name="var_name">total_count</field>  <!-- 可选：结果存入变量 -->
  </row>
</datatable>
```

`operation` 取值：`query`（查询，返回结果集）/ `execute`（增删改，返回受影响行数）。

### 4.7 verify 与 _verify 表名推导

`verify` 关键字的 data 属性 **只写 DataID**，框架自动从 `{模型名}_verify.xml` 查找验证数据。

```xml
<!-- Case XML -->
<test_step action="verify" model="Login" data="V001"/>
<!-- 框架自动读取 data/Login_verify.xml 中 id="V001" 的行 -->
```

### 4.8 三阶段容器与失败语义

```xml
<case execute="是" id="c001" title="示例">
  <pre_process>     <!-- 可选：预处理 -->
    <test_step action="navigate" ... />
  </pre_process>
  <test_case>        <!-- 必选：用例主体，至少 1 个 test_step -->
    <test_step action="type" ... />
    <test_step action="verify" ... />
  </test_case>
  <post_process>     <!-- 可选：后处理 -->
    <test_step action="close" ... />
  </post_process>
</case>
```

| 规则 | 说明 |
|------|------|
| 预处理失败 | 跳过用例阶段，**仍执行后处理** |
| 用例阶段失败 | **仍执行后处理**（保证 close/清理能跑） |
| 后处理失败 | 整条用例记为失败 |

> Agent 应将 `close` 等清理操作放在 `post_process` 中。

### 4.9 run — 沙箱代码执行

```xml
<test_step action="run" model="data_gen" data="gen_phone.py"/>
```

- `model`：`fun/` 目录下的工程子目录名
- `data`：脚本文件路径
- 脚本通过 `print()` 输出返回值，框架自动尝试 JSON 解析
- stdout 内容保存为步骤 Return 值

目录结构：

```
{测试模块}/
└── fun/
    └── data_gen/          ← model="data_gen"
        └── gen_phone.py   ← data="gen_phone.py"
```

### 4.10 关键字速查表

| 关键字 | model 属性 | data 属性 | 说明 |
|--------|-----------|-----------|------|
| `navigate` | — | URL 或 GlobalValue | 导航到 URL |
| `close` | — | — | 关闭浏览器 |
| `type` | UI 模型名 | DataID | UI 批量输入 |
| `verify` | 模型名 | DataID | 批量验证（自动查 _verify 表） |
| `send` | 接口模型名 | DataID | 发送 HTTP 请求 |
| `DB` | 连接组名 | SQL 表引用或 SQL | 执行数据库操作 |
| `run` | fun/ 工程名 | 脚本路径 | 沙箱执行 Python |
| `set` | — | — | 设置变量 |
| `wait` | — | 秒数 | 等待 |
| `get` / `get_text` | — | CSS 选择器 | 获取元素文本 |
| `assert` | — | — | 断言 |
| `clear` | — | CSS 选择器 | 清空输入框 |
| `upload_file` | — | 文件路径 | 上传文件 |
| `screenshot` | — | 文件路径 | 手动截图 |
| `check` | 同 verify | 同 verify | verify 的兼容别名 |

> `click`、`select`、`hover` 等不是独立关键字，而是写在数据表 `<field>` 值中（见 §4.4）。

---

## 5. 视觉定位集成

### 5.1 探索与定位

```python
# Agent 探索页面（使用自己的视觉能力）
screenshot = capture_screen()
elements = agent.analyze_screenshot(screenshot)

# 生成 vision 定位器
for elem in elements:
    if elem["has_bbox"]:
        loc_type = "vision_bbox"
        loc_value = f"{elem['x']},{elem['y']},{elem['w']},{elem['h']}"
    else:
        loc_type = "vision"
        loc_value = elem['description']

    # 写入模型 XML
    generate_model_xml(page_name, [{"name": elem["name"], "loc_type": loc_type, "loc_value": loc_value}])
```

### 5.2 定位器选择

```python
def choose_locator(element_info):
    """根据元素特征选择定位器类型，返回 (loc_type, loc_value) 元组"""
    if element_info.get("has_stable_id"):
        return ("xpath", f"//[@id='{element_info['id']}']")
    elif element_info.get("has_bbox"):
        return ("vision_bbox", element_info['bbox'])
    else:
        return ("vision", element_info['description'])
```

---

## 6. 错误处理

### 6.1 常见错误

| 错误类型 | 原因 | Agent 处理策略 |
|---------|------|---------------|
| 元素未找到 | vision 描述不准确 | 重新探索，更新描述 |
| 超时 | 页面加载慢 | 添加 wait 步骤 |
| 坐标偏移 | 窗口大小变化 | 使用 vision 替代 vision_bbox |
| XML 格式错误 | 生成逻辑错误 | 验证 XML 格式 |

### 6.2 重试机制

```python
def execute_with_retry(case_xml, max_retries=3):
    for attempt in range(max_retries):
        result = subprocess.run(
            ["python", "rodski/ski_run.py", case_xml],
            capture_output=True
        )

        if result.returncode == 0:
            return result

        # 分析失败原因
        error = parse_error(result.stderr)

        if error["type"] == "element_not_found":
            # 重新探索并更新 XML
            update_model_xml(error["element"])
        elif error["type"] == "timeout":
            # 增加等待时间
            add_wait_step(case_xml)

    return result
```

---

## 7. 最佳实践

### 7.1 活文档维护

- 每次探索后更新 XML
- 保持 XML 与实际页面同步
- 使用版本控制跟踪变化

### 7.2 性能优化

- 优先使用传统定位器（xpath/css）
- vision_bbox 比 vision 快
- 批量执行减少启动开销

### 7.3 调试技巧

```python
# 启用详细日志
result = subprocess.run(
    ["python", "rodski/ski_run.py", "case/test.xml", "--verbose"],
    capture_output=True
)

# 保存截图用于分析
# RodSki 会在失败时自动保存截图到 result/screenshots/
```

---

## 8. 示例：完整工作流

```python
# 1. Agent 探索页面
page_elements = agent.explore("https://example.com/login")

# 2. 生成模型 XML
generate_model_xml("LoginPage", page_elements)

# 3. 生成数据 XML
generate_data_xml("LoginPage", [
    {"id": "L001", "fields": {"username": "admin", "password": "123"}}
])

# 4. 生成用例 XML
generate_case_xml("c001", "登录测试", [
    {"action": "navigate", "model": "", "data": "https://example.com/login"},
    {"action": "type", "model": "LoginPage", "data": "L001"},
    {"action": "verify", "model": "LoginPage", "data": "V001"}
])

# 5. 执行测试
result = execute_with_retry("case/c001.xml")

# 6. 分析结果
if result.returncode == 0:
    print("测试通过")
else:
    # Agent 分析失败原因并调整策略
    analyze_and_adjust(result)
```

---

**文档版本**: v3.0
**最后更新**: 2026-04-13
**框架版本**: v5.7.0

## execution_summary.json 消费说明

每次 case 执行完成后，结果目录下生成 `execution_summary.json`，结构如下：

```json
{
  "case": "TC001",
  "steps": [
    {
      "index": 1,
      "action": "type",
      "model": "InquiryCreate",
      "status": "ok",
      "return_source": "auto_capture",
      "return_value": {"inquiryNo": "XJ001"},
      "named_writes": {}
    }
  ],
  "context_snapshot": {
    "named": {"inquiryNo": "XJ001"}
  }
}
```

### return_source 字段含义

| 值 | 含义 |
|----|------|
| `keyword_result` | 关键字直接返回值（True/list/dict） |
| `auto_capture` | 模型 auto_capture 规则自动提取 |
| `get_named` | get 命名访问模式读取 context.named |
| `evaluate` | evaluate JS 表达式返回值 |

### AI Agent 判断用例质量的参考指标

- `return_source=auto_capture` 比例越高，用例越符合框架推荐范式
- `return_source=evaluate` 出现说明用了低优先级逃生舱，可建议改用 auto_capture
- `context_snapshot.named` 为空说明用例未使用命名变量，可能存在步骤间数据传递问题
