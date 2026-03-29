# Agent 集成指南

**版本**: v1.0
**日期**: 2026-03-29
**目标读者**: AI Agent 开发者

---

## 1. 概述

### 1.1 集成模式

RodSki 作为执行引擎，Agent 作为智能层：

```
Agent (探索/决策) → XML (活文档) → RodSki (执行) → 结果 → Agent (分析)
```

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

## 3. XML 生成策略

### 3.1 模型 XML

```python
def generate_model_xml(page_name, elements):
    """
    elements: [{"name": "loginBtn", "locator": "vision:登录按钮"}]
    """
    xml = f'<models>\n  <model name="{page_name}">\n'
    for elem in elements:
        xml += f'    <element name="{elem["name"]}" locator="{elem["locator"]}"/>\n'
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

## 4. 视觉定位集成

### 4.1 探索与定位

```python
# Agent 探索页面（使用自己的视觉能力）
screenshot = capture_screen()
elements = agent.analyze_screenshot(screenshot)

# 生成 vision 定位器
for elem in elements:
    if elem["has_bbox"]:
        locator = f"vision_bbox:{elem['x']},{elem['y']},{elem['w']},{elem['h']}"
    else:
        locator = f"vision:{elem['description']}"

    # 写入模型 XML
    generate_model_xml(page_name, [{"name": elem["name"], "locator": locator}])
```

### 4.2 定位器选择

```python
def choose_locator(element_info):
    """根据元素特征选择定位器类型"""
    if element_info.get("has_stable_id"):
        return f"xpath://[@id='{element_info['id']}']"
    elif element_info.get("has_bbox"):
        return f"vision_bbox:{element_info['bbox']}"
    else:
        return f"vision:{element_info['description']}"
```

---

## 5. 错误处理

### 5.1 常见错误

| 错误类型 | 原因 | Agent 处理策略 |
|---------|------|---------------|
| 元素未找到 | vision 描述不准确 | 重新探索，更新描述 |
| 超时 | 页面加载慢 | 添加 wait 步骤 |
| 坐标偏移 | 窗口大小变化 | 使用 vision 替代 vision_bbox |
| XML 格式错误 | 生成逻辑错误 | 验证 XML 格式 |

### 5.2 重试机制

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

## 6. 最佳实践

### 6.1 活文档维护

- 每次探索后更新 XML
- 保持 XML 与实际页面同步
- 使用版本控制跟踪变化

### 6.2 性能优化

- 优先使用传统定位器（xpath/css）
- vision_bbox 比 vision 快
- 批量执行减少启动开销

### 6.3 调试技巧

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

## 7. 示例：完整工作流

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

**文档版本**: v1.0
**最后更新**: 2026-03-29
