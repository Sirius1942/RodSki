# 活文档规范

**版本**: v1.0
**日期**: 2026-03-29
**目标读者**: AI Agent

---

## 1. 活文档概念

### 1.1 什么是活文档

活文档是 Agent 探索后生成的 XML 文件，记录：
- 页面元素定位信息
- 操作步骤
- 测试数据

特点：
- 可执行（RodSki 直接运行）
- 可维护（Agent 持续更新）
- 可复用（不同场景复用）

### 1.2 活文档 vs 传统文档

| 特性 | 活文档 | 传统文档 |
|------|--------|---------|
| 格式 | XML（可执行） | Markdown/Word（只读） |
| 维护 | Agent 自动更新 | 人工手动更新 |
| 验证 | 执行即验证 | 无法验证 |
| 复用 | 直接复用 | 需要重写 |

---

## 2. 文档结构

### 2.1 目录组织

```
rodski/
├── model/          # 页面模型（元素定位）
│   ├── LoginPage.xml
│   └── HomePage.xml
├── case/           # 测试用例（操作步骤）
│   ├── login.xml
│   └── search.xml
├── data/           # 测试数据
│   ├── LoginPage.xml
│   └── SearchPage.xml
└── result/         # 执行结果
    └── result_*.xml
```

### 2.2 文件命名规范

| 类型 | 命名规则 | 示例 |
|------|---------|------|
| 模型 | `{PageName}.xml` | `LoginPage.xml` |
| 用例 | `{功能}.xml` | `login.xml` |
| 数据 | `{PageName}.xml` | `LoginPage.xml` |

---

## 3. 模型文档

### 3.1 基础模板

```xml
<models>
  <model name="PageName" driver_type="web">
    <element name="elementName" locator="vision:描述"/>
  </model>
</models>
```

### 3.2 完整示例

```xml
<models>
  <model name="LoginPage" driver_type="web">
    <element name="username" locator="vision:用户名输入框"/>
    <element name="password" locator="vision:密码输入框"/>
    <element name="loginBtn" locator="vision_bbox:850,400,100,40"/>
    <element name="errorMsg" locator="vision:错误提示信息"/>
  </model>
</models>
```

### 3.3 更新策略

```python
def update_model_xml(page_name, elements):
    """Agent 探索后更新模型"""
    xml_path = f"model/{page_name}.xml"

    if Path(xml_path).exists():
        # 读取现有模型
        tree = ET.parse(xml_path)
        model = tree.find(f".//model[@name='{page_name}']")

        # 更新或添加元素
        for elem in elements:
            existing = model.find(f".//element[@name='{elem['name']}']")
            if existing is not None:
                existing.set("locator", elem["locator"])
            else:
                ET.SubElement(model, "element", elem)

        tree.write(xml_path)
    else:
        # 创建新模型
        generate_model_xml(page_name, elements)
```

---

## 4. 用例文档

### 4.1 三阶段结构

```xml
<cases>
  <case execute="是" id="c001" title="用例标题">
    <pre_process>
      <!-- 前置步骤：环境准备 -->
    </pre_process>
    <test_case>
      <!-- 核心步骤：业务操作 -->
    </test_case>
    <post_process>
      <!-- 后置步骤：清理环境 -->
    </post_process>
  </case>
</cases>
```

### 4.2 完整示例

```xml
<cases>
  <case execute="是" id="c001" title="用户登录">
    <pre_process>
      <test_step action="navigate" model="" data="https://example.com/login"/>
      <test_step action="wait" model="" data="2"/>
    </pre_process>
    <test_case>
      <test_step action="type" model="LoginPage" data="L001"/>
      <test_step action="click" model="LoginPage" data="C001"/>
      <test_step action="wait" model="" data="3"/>
      <test_step action="verify" model="HomePage" data="V001"/>
    </test_case>
    <post_process>
      <test_step action="close" model="" data=""/>
    </post_process>
  </case>
</cases>
```

### 4.3 复用模式

```python
def reuse_case_template(template_id, new_data):
    """复用用例模板，替换数据"""
    template = ET.parse(f"case/{template_id}.xml")
    case = template.find(".//case")

    # 修改 ID 和标题
    case.set("id", new_data["id"])
    case.set("title", new_data["title"])

    # 替换数据引用
    for step in case.findall(".//test_step"):
        if step.get("data") in new_data["data_mapping"]:
            step.set("data", new_data["data_mapping"][step.get("data")])

    template.write(f"case/{new_data['id']}.xml")
```

---

## 5. 数据文档

### 5.1 基础模板

```xml
<datatable name="PageName">
  <row id="RowID">
    <field name="elementName">值</field>
  </row>
</datatable>
```

### 5.2 完整示例

```xml
<datatable name="LoginPage">
  <row id="L001">
    <field name="username">admin</field>
    <field name="password">admin123</field>
  </row>
  <row id="C001">
    <field name="loginBtn">click</field>
  </row>
  <row id="V001">
    <field name="welcomeMsg">欢迎, admin</field>
  </row>
</datatable>
```

### 5.3 数据驱动

```python
def generate_data_driven_cases(base_case, data_rows):
    """基于数据生成多个用例"""
    for i, row in enumerate(data_rows):
        case_id = f"{base_case}_data{i+1}"

        # 添加数据行
        add_data_row(row["page_name"], row["row_id"], row["fields"])

        # 复用用例模板
        reuse_case_template(base_case, {
            "id": case_id,
            "title": f"{base_case} - 数据集{i+1}",
            "data_mapping": {base_case: row["row_id"]}
        })
```

---

## 6. 维护策略

### 6.1 增量更新

```python
def incremental_update(page_name):
    """Agent 探索后增量更新"""
    # 1. 探索页面
    new_elements = agent.explore(page_name)

    # 2. 对比现有模型
    existing_elements = load_model_xml(page_name)

    # 3. 只更新变化的元素
    for elem in new_elements:
        if elem not in existing_elements:
            add_element_to_model(page_name, elem)
        elif elem["locator"] != existing_elements[elem["name"]]:
            update_element_locator(page_name, elem["name"], elem["locator"])
```

### 6.2 版本控制

```python
def version_control_xml(xml_file):
    """使用 git 跟踪 XML 变化"""
    subprocess.run(["git", "add", xml_file])
    subprocess.run([
        "git", "commit", "-m",
        f"Agent 更新: {xml_file} - {datetime.now()}"
    ])
```

### 6.3 过期检测

```python
def detect_stale_documents():
    """检测过期文档"""
    for model_file in Path("model").glob("*.xml"):
        last_modified = model_file.stat().st_mtime
        age_days = (time.time() - last_modified) / 86400

        if age_days > 30:
            print(f"过期文档: {model_file} (已 {age_days:.0f} 天未更新)")
            # Agent 重新探索并更新
```

---

## 7. 最佳实践

### 7.1 文档粒度

- 一个页面一个模型文件
- 一个功能一个用例文件
- 相关数据放在同名数据文件

### 7.2 命名约定

```python
# 模型名称：大驼峰
model_name = "LoginPage"

# 元素名称：小驼峰
element_name = "loginBtn"

# 数据行 ID：前缀+序号
data_row_id = "L001"  # L=Login, 001=序号
```

### 7.3 注释规范

```xml
<!-- Agent 探索时间: 2026-03-29 -->
<!-- 页面 URL: https://example.com/login -->
<model name="LoginPage">
  <!-- 主要输入框 -->
  <element name="username" locator="vision:用户名输入框"/>

  <!-- 提交按钮 -->
  <element name="loginBtn" locator="vision_bbox:850,400,100,40"/>
</model>
```

---

**文档版本**: v1.0
**最后更新**: 2026-03-29
