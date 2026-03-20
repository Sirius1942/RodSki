# RodSki 快速入门指南

5 分钟快速上手 RodSki 自动化测试框架。

## 1. 安装

```bash
cd rodski

# 安装依赖
pip install -r requirements.txt

# 安装浏览器驱动
playwright install chromium
```

## 2. 运行演示项目

项目自带一个完整的演示测试网站和测试用例，路径 `product/DEMO/demo_site/`。

**启动测试网站**：

```bash
python product/DEMO/demo_site/app.py
```

网站地址 http://127.0.0.1:5555，账号 admin / admin123。

**执行测试用例**：

```bash
python ski_run.py product/DEMO/demo_site/case/demo_test_case.xlsx
```

## 3. 理解用例结构

RodSki 用例由三部分组成：**关键字 + 模型 + 数据**。

```
关键字（做什么） + 模型（对哪些元素） + 数据（用什么值）
```

一个 Excel 用例文件包含：

| Sheet | 作用 |
|-------|------|
| Case | 测试步骤（动作 + 模型 + 数据） |
| GlobalValue | 全局配置（URL、等待时间、数据库连接等） |
| 数据表 | 测试数据（如 LoginData、ItemData） |
| TestResult | 执行结果（框架自动回填） |

核心规则：**模型元素名 = 数据表列名**。

## 4. 写第一个用例

### model.xml（定义页面元素）

```xml
<models>
<model name="Login">
  <element name="username" type="web">
    <location type="id">username</location>
  </element>
  <element name="password" type="web">
    <location type="id">password</location>
  </element>
</model>
</models>
```

### 数据表 LoginData（定义输入数据）

| DataID | Remark | username | password |
|--------|--------|----------|----------|
| L001 | 管理员 | admin | admin123 |

### Case Sheet（定义用例步骤）

| 执行控制 | 编号 | 标题 | 描述 | 类型 | 预处理动作 | 预处理模型 | 预处理数据 | 测试动作 | 测试模型 | 测试数据 |
|---------|------|------|------|------|-----------|-----------|-----------|---------|---------|---------|
| 是 | c001 | 登录 | 验证登录 | 界面 | navigate | | GlobalValue.DefaultValue.URL/login | type | Login | LoginData.L001 |

`type Login LoginData.L001` 的含义：遍历 Login 模型的每个元素（username、password），从 LoginData.L001 取同名列的值，逐一输入。

## 5. 控制执行节奏

在 GlobalValue Sheet 中设置 `DefaultValue.WaitTime`，每步执行后自动等待：

| GroupName | Key | Value |
|-----------|-----|-------|
| DefaultValue | WaitTime | 2 |

`wait` 和 `close` 关键字不受此影响。

## 6. 查看结果

执行完成后，结果自动回填到 Excel 的 TestResult Sheet。

生成 HTML 报告：

```bash
PYTHONPATH=. python cli_main.py report --input logs/latest_results.json
```

## 7. 进阶学习

- **用例编写规范**：`docs/TEST_CASE_WRITING_GUIDE.md`（最重要）
- **API 测试**：`docs/API_TESTING_GUIDE.md`
- **GUI 使用**：`docs/GUI_USAGE.md`
- **架构说明**：`docs/ARCHITECTURE.md`
- **故障排查**：`docs/TROUBLESHOOTING.md`

---

**下一步**：阅读 `docs/TEST_CASE_WRITING_GUIDE.md` 了解完整的用例编写规范。
