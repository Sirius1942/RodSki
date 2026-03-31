# RodSki 测试用例可读性提升技术设计

**版本**: v1.0
**日期**: 2026-03-31

---

## 1. 技术架构

### 1.1 模块结构

```
rodski/
├── rodski_cli/
│   ├── explain.py          # ⭐ 扩展 explain 命令
│   ├── report.py           # ⭐ 增强 report 命令
│   └── ...
├── core/
│   ├── case_parser.py      # ⭐ 支持业务标签解析
│   └── model_parser.py     # ⭐ 支持 description 字段
└── docs/
    └── user-guides/
        └── EXPLAIN.md      # ⭐ explain 命令使用文档
```

---

## 2. 设计方案

### 2.1 Case 业务标签扩展

**XML Schema 扩展**：

```xml
<case id="xxx" 
      title="用例标题"
      purpose="用例目的描述"
      priority="P0"
      tags="标签1,标签2"
      component_type="界面"
      expected_result="预期结果描述">
```

**解析器支持**：

```python
# core/case_parser.py
class TestCase:
    id: str
    title: str
    purpose: str           # 新增
    priority: str         # 新增
    tags: List[str]       # 新增
    component_type: str   # 新增
    expected_result: str  # 新增
```

### 2.2 Model 描述字段扩展

**XML Schema 扩展**：

```xml
<element name="vin">
    <type>input</type>
    <location type="id">vin</location>
    <description>车辆识别代号输入框，用于输入17位VIN码</description>
</element>
```

**解析器支持**：

```python
# core/model_parser.py
class ModelElement:
    name: str
    type: str
    location: dict
    description: str  # 新增
```

### 2.3 Explain 命令增强

**输出格式选项**：

| 格式 | 说明 | 示例 |
|------|------|------|
| `text` | 纯文本格式（默认） | 易读，纯文本 |
| `markdown` | Markdown 格式 | 可复制到文档 |
| `html` | HTML 格式 | 可在浏览器查看 |

**命令行接口**：

```bash
# 基本用法
rodski explain case.xml

# 指定格式
rodski explain case.xml --format markdown

# 输出到文件
rodski explain case.xml --output readme.md --format markdown

# 显示详细步骤
rodski explain case.xml --verbose
```

### 2.4 Report 命令增强

**HTML 报告生成**：

```bash
# 生成 HTML 报告
rodski report result.xml --format html --output test_report.html

# 生成带截图的报告
rodski report result.xml --format html --embed-screenshots
```

**报告样式**：

```css
/* 马里奥主题报告样式 */
.report-header {
    background: #E52521;
    color: white;
    padding: 20px;
    border-radius: 8px;
}

.step-pass {
    background: #38B044;
    color: white;
}

.step-fail {
    background: #E52521;
    color: white;
}
```

---

## 3. 数据流

```
XML Case File
     │
     ▼
┌─────────────────┐
│  Case Parser     │ ←── 解析 id, title, purpose, tags, priority
└─────────────────┘
     │
     ▼
┌─────────────────┐
│  Step Parser    │ ←── 解析 action, model, data
└─────────────────┘
     │
     ▼
┌─────────────────┐
│  Model Parser   │ ←── 解析 element, location, description
└─────────────────┘
     │
     ▼
┌─────────────────┐
│  Explain Engine │ ←── 生成可读化输出
└─────────────────┘
     │
     ▼
┌─────────────────┐
│  Formatter      │ ←── text / markdown / html
└─────────────────┘
```

---

## 4. 示例输出

### 4.1 Text 格式

```
用例：小李发布询价
ID：cassmall_inquiry_publish
目的：验证维修厂用户能够成功发布询价单
优先级：P0
标签：询价, 核心流程, 冒烟测试
组件类型：界面

前置条件：
  • 小李账号已注册并拥有维修厂权限
  • 系统可正常访问

测试步骤：
  步骤 1: 打开登录页面 (3s)
  步骤 2: 输入登录信息 (5s)
  步骤 3: 进入询价页面 (2s)
  步骤 4: 填写询价信息 (5s)
  步骤 5: 提交询价单
  步骤 6: 截图记录
  步骤 7: 验证询价单已创建 (3s)

预期结果：
  ✓ 询价单发布成功
  ✓ 询价单出现在询价列表中
```

### 4.2 Markdown 格式

```markdown
# 小李发布询价

**用例 ID**: `cassmall_inquiry_publish`  
**目的**: 验证维修厂用户能够成功发布询价单  
**优先级**: P0  
**标签**: 询价 | 核心流程 | 冒烟测试  

---

## 前置条件

- [ ] 小李账号已注册并拥有维修厂权限
- [ ] 系统可正常访问

## 测试步骤

| 步骤 | 操作 | 模型 | 数据 | 耗时 |
|------|------|------|------|------|
| 1 | 打开登录页面 | - | URL | 3s |
| 2 | 输入登录信息 | LoginPage | xiaoli_login | 5s |
| 3 | 进入询价页面 | - | URL | 2s |
| 4 | 填写询价信息 | InquiryPage | I001 | 5s |
| 5 | 提交询价单 | InquiryPage | - | - |
| 6 | 截图记录 | - | - | - |
| 7 | 验证询价单已创建 | - | URL | 3s |

## 预期结果

- [x] 询价单发布成功
- [x] 询价单出现在询价列表中
```

---

## 5. 约束与限制

1. **向后兼容**：现有 XML 格式不变，新字段可选
2. **性能影响**：explain 命令不应显著增加执行时间
3. **输出一致性**：不同格式的输出内容一致
