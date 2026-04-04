# RodSki Agent 使用指南

**版本**: v1.0
**日期**: 2026-03-26
**目标读者**: OpenClaw、Claude Code 等 AI Agent

---

## 1. 概述

### 1.1 RodSki 是什么

RodSki 是关键字驱动的自动化测试框架，支持 Web/Mobile/Desktop 平台。

### 1.2 Agent 与 RodSki 的协作模式

**职责划分**：

| 角色 | 职责 |
|------|------|
| **Agent** | 探索页面/应用、生成 XML、决策执行策略、分析结果 |
| **RodSki** | 执行 XML 定义的操作、返回结构化结果 |

**协作流程**：
```
1. Agent 探索 → 发现元素和操作路径
2. Agent 生成 XML → 记录为活文档
3. Agent 调用 RodSki → 执行 XML
4. RodSki 返回结果 → Agent 分析并决策下一步
```

---

## 2. 快速开始

### 2.1 最简单的调用示例

```python
# 1. Agent 生成 XML（探索后）
model_xml = """
<models>
  <model name="LoginPage">
    <element name="username" locator="vision:用户名输入框"/>
    <element name="loginBtn" locator="vision:登录按钮"/>
  </model>
</models>
"""

# 2. 写入文件
Path("model/model.xml").write_text(model_xml)

# 3. 调用 RodSki 执行
result = subprocess.run([
    "python", "rodski/ski_run.py",
    "case/login.xml"
], capture_output=True)

# 4. 解析结果
print(result.stdout)
```

---

## 3. XML 生成指南

### 3.1 模型 XML 生成

**传统定位器**：
```xml
<element name="username" type="xpath" value="//input[@id='user']"/>
```

**vision 定位器**（Agent 探索后生成）：
```xml
<element name="loginBtn" locator="vision:登录按钮"/>
<element name="closeBtn" locator="vision_bbox:1850,50,1900,100"/>
```

### 3.2 用例 XML 生成（三阶段结构）

```xml
<cases>
  <case execute="是" id="c001" title="登录测试">
    <pre_process>
      <test_step action="navigate" model="" data="https://example.com"/>
    </pre_process>
    <test_case>
      <test_step action="type" model="LoginPage" data="L001"/>
      <test_step action="verify" model="LoginPage" data="V001"/>
    </test_case>
    <post_process>
      <test_step action="close" model="" data=""/>
    </post_process>
  </case>
</cases>
```

### 3.3 数据表 XML 生成

```xml
<datatable name="LoginPage">
  <row id="L001">
    <field name="username">admin</field>
    <field name="password">admin123</field>
    <field name="loginBtn">click</field>
  </row>
</datatable>
```

---

## 4. 视觉定位工作流

### 4.1 Agent 如何使用 vision 定位器

**步骤**：
1. Agent 使用自己的视觉能力探索页面
2. 识别元素（按钮、输入框等）
3. 生成 `locator="vision:描述"` 或 `locator="vision_bbox:坐标"`
4. RodSki 执行时调用 OmniParser + LLM 进行定位

### 4.2 vision vs vision_bbox 选择策略

| 场景 | 推荐 |
|------|------|
| 首次探索 | `vision:描述`（灵活） |
| 已知精确坐标 | `vision_bbox:x,y,w,h`（快速） |
| 动态页面 | `vision:描述`（适应变化） |
| 固定布局 | `vision_bbox`（性能优） |

---

## 5. 桌面自动化

### 5.1 桌面应用 XML 模板

```xml
<model name="NotepadPage" driver_type="windows">
  <element name="textArea" locator="vision:文本编辑区域"/>
</model>
```

### 5.2 launch 关键字

```xml
<test_step action="launch" model="" data="notepad.exe"/>
```

### 5.3 run 调用桌面脚本

```xml
<test_step action="run" model="" data="fun/desktop/key_combo.py Ctrl+V"/>
```

---

## 6. 执行与结果处理

### 6.1 运行命令

```bash
python rodski/ski_run.py case/test.xml
```

### 6.2 结果解析

结果输出在 `result/result_*.xml`：
```xml
<testresult>
  <summary total="1" passed="1" failed="0"/>
  <results>
    <result case_id="c001" status="PASS" execution_time="2.5"/>
  </results>
</testresult>
```

### 6.3 失败分析与重试

```python
if result.returncode != 0:
    # 分析失败原因
    # 1. 元素未找到 → 更新 vision 描述
    # 2. 超时 → 增加 wait 步骤
    # 3. 坐标偏移 → 重新探索生成 vision_bbox
```

---

## 7. 最佳实践

### 7.1 什么时候用 vision vs xpath

| 定位器 | 适用场景 |
|--------|---------|
| xpath/css | 稳定的 Web 元素、性能要求高 |
| vision | 动态 ID、无明显属性、跨语言 |

### 7.2 用例复用

生成的 XML 是活文档，可复用：
- 同一页面不同数据 → 复用 model，修改 data
- 相似流程 → 复用 case 结构，替换 model

### 7.3 活文档维护

- Agent 每次探索后更新 vision_bbox 坐标
- 页面变化时重新生成 vision 描述
- 保持 XML 与实际页面同步

---

**文档版本**: v1.0
**最后更新**: 2026-03-26
