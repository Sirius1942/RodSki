# RodSki测试用例编写经验与规范

**版本**: v1.0
**日期**: 2026-03-24
**基于**: RodSki v3.0+ 实战经验总结

---

## 1. 核心原则

### 1.1 模型-数据分离
- **模型（model.xml）**：定义页面元素/接口字段的定位信息
- **数据（data/*.xml）**：定义输入值和期望值
- **用例（case/*.xml）**：定义测试步骤和流程

**关键规则**：模型元素 name = 数据表字段 name（必须完全一致）

### 1.2 XSD Schema约束
所有XML文件必须符合对应的XSD约束：
- `case.xsd` - 测试用例
- `model.xsd` - 模型定义
- `data.xsd` - 数据表
- `globalvalue.xsd` - 全局变量

**验证方法**：
```bash
xmllint --noout --schema rodski/schemas/case.xsd case/demo_case.xml
```

---

## 2. 测试用例编写规范

### 2.1 Case XML结构

```xml
<case execute="是" id="TC001" title="测试标题" component_type="界面">
    <pre_process>
        <!-- 前置步骤（可选） -->
    </pre_process>
    <test_case>
        <!-- 测试步骤（必须） -->
    </test_case>
    <post_process>
        <!-- 后置步骤（可选） -->
    </post_process>
</case>
```

**必填属性**：
- `execute`: "是" 或 "否"
- `id`: 用例ID（唯一）
- `title`: 用例标题

**component_type取值**：
- `界面` - Web UI测试
- `接口` - API接口测试
- `数据库` - 数据库测试

### 2.2 test_step属性

```xml
<test_step action="关键字" model="模型名" data="数据ID"/>
```

**常见错误**：
- ❌ 使用 `desc` 属性（XSD不支持）
- ❌ 使用 `locator` 属性（应在model中定义）
- ✅ 只使用 `action`、`model`、`data` 三个属性

---

## 3. 模型定义规范

### 3.1 Web UI模型

**完整格式**（推荐）：
```xml
<model name="LoginForm" servicename="">
    <element name="username" type="web">
        <type>input</type>
        <location type="id">loginUsername</location>
    </element>
</model>
```

**简化格式**：
```xml
<element name="username" type="id" value="loginUsername"/>
```

### 3.2 API接口模型

**保留元素名**：
- `_method` - HTTP方法（GET/POST/PUT/DELETE）
- `_url` - 请求地址
- `_header_*` - 请求头（如 `_header_Authorization`）

```xml
<model name="LoginAPI" servicename="">
    <element name="_method" type="interface">
        <location type="static">POST</location>
    </element>
    <element name="_url" type="interface">
        <location type="static">http://localhost:8000/api/login</location>
    </element>
    <element name="username" type="interface">
        <location type="field">username</location>
    </element>
</model>
```

### 3.3 定位类型（LocatorType）

| type值 | 说明 | 示例 |
|--------|------|------|
| `id` | ID选择器 | `loginBtn` → `#loginBtn` |
| `class` | Class选择器 | `btn-submit` → `.btn-submit` |
| `css` | CSS选择器 | `input[name="user"]` |
| `xpath` | XPath | `//button[@id='login']` |
| `text` | 文本匹配 | `登录` |
| `static` | 静态值 | 用于接口的固定值 |
| `field` | 字段映射 | 用于接口字段 |

---

## 4. 数据表编写规范

### 4.1 命名规则

**数据表文件名 = 模型名**
- 输入数据：`{模型名}.xml`
- 验证数据：`{模型名}_verify.xml`

**示例**：
- 模型：`LoginForm`
- 输入数据：`data/LoginForm.xml`
- 验证数据：`data/LoginForm_verify.xml`

### 4.2 数据表结构

```xml
<?xml version="1.0" encoding="UTF-8"?>
<datatable name="LoginForm">
    <row id="L001">
        <field name="username">admin</field>
        <field name="password">123456</field>
        <field name="loginBtn">click</field>
    </row>
</datatable>
```

**关键约束**：
- `datatable@name` 必须与文件名一致
- `row@id` 在同一数据表内唯一
- `field@name` 必须与模型元素name一致
- 每个row至少包含一个field

### 4.3 特殊值

| 值 | 说明 |
|---|------|
| `click` | 点击操作 |
| `admin` | 选择下拉框选项值为admin |
| 普通文本 | 输入文本内容 |

---

## 5. 关键字使用规范

### 5.1 Web UI关键字

**navigate** - 页面导航
```xml
<test_step action="navigate" model="" data="http://localhost:8000"/>
```

**type** - UI批量输入
```xml
<test_step action="type" model="LoginForm" data="L001"/>
```
- 遍历模型所有元素
- 从数据表获取对应字段值
- 自动识别操作类型（输入/点击/选择）

**verify** - 批量验证
```xml
<test_step action="verify" model="Dashboard" data="V001"/>
```
- 自动查找 `{模型名}_verify.xml`
- 读取界面实际值与期望值比较

### 5.2 API接口关键字

**send** - 发送请求
```xml
<test_step action="send" model="LoginAPI" data="D001"/>
```
- 从模型获取 `_method` 和 `_url`
- 从数据表获取请求参数
- 自动发送HTTP请求

**verify** - 验证响应
```xml
<test_step action="verify" model="LoginAPI" data="V001"/>
```
- 验证响应状态码（`status`字段）
- 验证响应字段值

### 5.3 数据库关键字

**DB** - 执行SQL
```xml
<test_step action="DB" model="demo_db" data="QuerySQL.Q001"/>
```
- `model`: GlobalValue中的数据库连接组名
- `data`: SQL数据表引用

**GlobalValue配置**：
```xml
<group name="demo_db">
    <var name="type" value="sqlite"/>
    <var name="database" value="path/to/demo.db"/>
</group>
```

### 5.4 代码执行关键字

**run** - 执行Python代码
```xml
<test_step action="run" model="data_gen" data="gen_data.py"/>
```
- `model`: fun/目录下的工程名
- `data`: Python文件路径
- 通过print()输出返回值

---

## 6. 常见错误与解决

### 6.1 XSD校验错误

**错误1：attribute not allowed**
```
'desc' attribute not allowed for element
```
**解决**：移除不支持的属性（如desc、locator）

**错误2：missing required attribute**
```
missing required attribute 'title'
```
**解决**：case元素使用`title`而不是`name`

**错误3：value must be one of**
```
component_type='其他': value must be one of ['界面', '接口', '数据库']
```
**解决**：使用允许的枚举值

### 6.2 运行时错误

**错误1：模型不存在**
```
模型不存在: 'LoginForm'
```
**解决**：检查model.xml中是否定义了该模型

**错误2：数据不存在**
```
表 'LoginForm' 中找不到 DataID='L001'
```
**解决**：检查data/LoginForm.xml中是否有id="L001"的row

**错误3：字段名不匹配**
```
字段 'username' 在模型中不存在
```
**解决**：确保数据表field name与模型element name完全一致

### 6.3 数据库问题

**错误：no such table**
```
SQL 执行失败: no such table: orders
```
**解决**：
1. 检查数据库文件路径
2. 检查表名拼写
3. 确认数据库已初始化

**错误：no such column**
```
no such column: order_id
```
**解决**：检查SQL中的列名与实际表结构是否一致

---

## 7. 最佳实践

### 7.1 用例组织

**按功能模块组织**：
```
case/
├── login_test.xml      # 登录相关
├── order_test.xml      # 订单相关
└── user_test.xml       # 用户相关
```

**用例ID命名**：
- 格式：`TC{模块}{序号}`
- 示例：`TC001`, `TC002`, `TC003`

### 7.2 数据管理

**数据复用**：
```xml
<datatable name="LoginForm">
    <row id="L001" remark="管理员">
        <field name="username">admin</field>
        <field name="password">123456</field>
    </row>
    <row id="L002" remark="普通用户">
        <field name="username">user</field>
        <field name="password">123456</field>
    </row>
</datatable>
```

**GlobalValue使用**：
```xml
<group name="env">
    <var name="base_url" value="http://localhost:8000"/>
</group>
```

引用：`GlobalValue.env.base_url`

### 7.3 模型设计

**单一职责**：
- 一个模型对应一个页面/接口
- 避免模型过大

**命名规范**：
- 页面模型：`{页面名}Form`、`{页面名}Page`
- 接口模型：`{功能名}API`
- 数据库模型：`Query{功能名}`

### 7.4 测试步骤

**避免冗余等待**：
- ❌ 每步都加wait
- ✅ 框架有统一等待机制

**前置处理复用**：
```xml
<pre_process>
    <test_step action="navigate" model="" data="http://localhost:8000"/>
    <test_step action="type" model="LoginForm" data="L001"/>
</pre_process>
```

---

## 8. 调试技巧

### 8.1 XSD校验

```bash
# 校验case文件
xmllint --noout --schema rodski/schemas/case.xsd case/demo_case.xml

# 校验model文件
xmllint --noout --schema rodski/schemas/model.xsd model/model.xml

# 校验data文件
xmllint --noout --schema rodski/schemas/data.xsd data/LoginForm.xml
```

### 8.2 日志分析

运行测试时关注：
- 📌 用例步骤执行顺序
- ❌ 错误信息中的keyword和具体原因
- ✅ 通过的用例执行时间

### 8.3 逐步验证

1. 先验证XSD格式正确
2. 再验证模型定义正确
3. 最后验证数据匹配正确

---

## 9. 检查清单

### 用例编写前
- [ ] 确认测试目标和范围
- [ ] 设计模型结构
- [ ] 准备测试数据

### 用例编写中
- [ ] case使用title而非name
- [ ] component_type使用允许值
- [ ] test_step只用action/model/data
- [ ] 模型element name与数据field name一致

### 用例编写后
- [ ] XSD校验通过
- [ ] 本地运行通过
- [ ] 添加必要注释

---

## 10. 参考资源

- [TEST_CASE_WRITING_GUIDE.md](./TEST_CASE_WRITING_GUIDE.md) - 官方编写指南
- [API_TESTING_GUIDE.md](./API_TESTING_GUIDE.md) - API测试指南
- `rodski/schemas/*.xsd` - XSD约束定义
- `rodski/examples/` - 官方示例

---

**编写者**：基于demo_full实战经验总结
**适用版本**：RodSki v3.0+
