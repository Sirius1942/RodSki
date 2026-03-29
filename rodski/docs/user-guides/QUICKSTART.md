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

项目自带一个完整的演示测试网站和测试用例，路径 `rodski-demo/DEMO/demo_full/`。

**启动测试网站**：

```bash
python rodski-demo/DEMO/demo_full/demosite/app.py
```

网站地址 http://127.0.0.1:8000，账号 admin / 123456。

**执行测试用例**：

```bash
python ski_run.py rodski-demo/DEMO/demo_full/case/demo_case.xml
```

## 3. 理解用例结构

RodSki 用例由三部分组成：**关键字 + 模型 + 数据**。

```
关键字（做什么） + 模型（对哪些元素） + 数据（用什么值）
```

### 目录结构约束

测试项目必须遵循以下目录结构：

```
project/
├── case/       # 测试用例 XML 文件
├── model/      # 页面元素模型 XML 文件
├── data/       # 测试数据 XML 文件
├── fun/        # 自定义函数脚本
└── result/     # 测试结果输出（自动生成）
```

### 三阶段容器结构

每个测试用例支持三个执行阶段：

```xml
<case execute="是" id="TC001" title="测试标题" component_type="界面">
    <pre_process>
        <!-- 前置步骤：环境准备、登录等 -->
    </pre_process>
    <test_case>
        <!-- 核心测试步骤 -->
    </test_case>
    <post_process>
        <!-- 后置步骤：清理、恢复等 -->
    </post_process>
</case>
```

核心规则：**模型元素名 = 数据字段名**。

## 4. 写第一个用例

### model/model.xml（定义页面元素）

```xml
<?xml version="1.0" encoding="UTF-8"?>
<models>
<model name="LoginForm">
  <element name="username" type="web">
    <type>input</type>
    <location type="id">loginUsername</location>
  </element>
  <element name="password" type="web">
    <type>input</type>
    <location type="id">loginPassword</location>
  </element>
  <element name="loginBtn" type="web">
    <type>button</type>
    <location type="id">loginBtn</location>
  </element>
</model>
</models>
```

### data/Login.xml（定义输入数据）

```xml
<?xml version="1.0" encoding="UTF-8"?>
<datatable name="Login">
    <row id="L001">
        <field name="username">admin</field>
        <field name="password">123456</field>
        <field name="loginBtn">click</field>
    </row>
</datatable>
```

### case/demo_case.xml（定义用例步骤）

```xml
<?xml version="1.0" encoding="UTF-8"?>
<cases>
    <case execute="是" id="TC001" title="登录测试" component_type="界面">
        <test_case>
            <test_step action="navigate" model="" data="http://127.0.0.1:8000"/>
            <test_step action="type" model="LoginForm" data="L001"/>
        </test_case>
    </case>
</cases>
```

`type LoginForm L001` 的含义：遍历 LoginForm 模型的每个元素（username、password、loginBtn），从 Login.xml 的 L001 行取同名字段的值，逐一执行。

## 5. 控制执行节奏

在用例 XML 中可以使用 `wait` 步骤控制等待时间：

```xml
<test_step action="wait" model="" data="2"/>
```

`close` 关键字用于关闭浏览器或清理资源。

## 6. 查看测试结果

执行完成后，结果自动输出到 `result/` 目录。每次测试执行会创建一个独立的目录。

### 结果目录结构

```
result/
└── 20260325_082802_a1b2c3d4/          # 执行日期_时间_唯一ID
    ├── result.xml                      # 测试结果XML文件
    └── screenshots/                    # 截图目录
        ├── TC001_20260325_082645_failure.png    # 失败截图：用例ID_时间戳_failure.png
        ├── TC002_20260325_082703_failure.png
        └── TC003_01_click_20260325_082710.png   # 步骤截图：用例ID_步骤序号_动作_时间戳.png
```

### 结果文件说明

**result.xml** 包含：
- `<summary>`: 执行统计（总数、通过、失败、通过率、执行时间等）
- `<results>`: 每个用例的详细结果
  - `case_id`: 用例ID
  - `status`: PASS/FAIL/SKIP/ERROR
  - `execution_time`: 执行时长（秒）
  - `screenshot_path`: 截图相对路径
  - `error_message`: 失败原因

### 截图文件命名规则

- **失败截图**: `{用例ID}_{时间戳}_failure.png`
- **步骤截图**: `{用例ID}_{步骤序号}_{动作类型}_{时间戳}.png`

生成 HTML 报告：

```bash
PYTHONPATH=. python cli_main.py report --input logs/latest_results.json
```

## 7. Explain 子命令（用例可解释性）

RodSki 提供 `explain` 子命令，用于解析测试用例并生成人类可读的执行说明。

### 使用方法

```bash
python ski_run.py explain case/demo_case.xml
```

### 功能特性

- **自动解析测试步骤**：读取用例 XML 中的 `test_step` 节点，提取 action、model、data 信息
- **生成可读描述**：将技术步骤转换为自然语言描述，例如：
  - `action="navigate" data="http://example.com"` → "导航到 http://example.com"
  - `action="type" model="LoginForm" data="L001"` → "在 LoginForm 模型中输入 L001 数据"
- **敏感字段脱敏**：自动识别并隐藏敏感信息，包含以下关键字的字段值会被替换为 `***`：
  - `password`
  - `pwd`
  - `secret`
  - `token`

### 示例输出

```
用例 TC001: 登录测试
步骤 1: 导航到 http://127.0.0.1:8000
步骤 2: 在 LoginForm 模型中输入数据
  - username: admin
  - password: ***
  - loginBtn: click
```

## 8. 异常处理与智能恢复

RodSki 内置完善的异常处理和智能恢复机制，确保测试执行的稳定性和可靠性。

### 异常类型

框架支持以下异常类型的自动捕获和处理：

- **ElementNotFoundError**：页面元素未找到
- **NetworkError**：网络请求失败
- **AssertionFailedError**：断言验证失败
- **StepTimeoutError**：步骤执行超时
- **PageCrashError**：页面崩溃或无响应

### 自动截图

所有异常发生时，框架会自动捕获当前页面截图，保存到 `result/{执行ID}/screenshots/` 目录，文件命名格式：`{用例ID}_{时间戳}_failure.png`。

### AI 视觉诊断

框架集成 AI 视觉分析能力（`vision/ai_verifier.py`），可以：
- 分析失败截图，识别页面状态
- 检测常见错误模式（404页面、弹窗、加载失败等）
- 提供智能诊断建议

### 诊断引擎

**DiagnosisEngine** 负责生成详细的诊断报告，包含：
- 失败步骤的上下文信息（URL、步骤索引、模型、数据）
- 异常类型和错误消息
- 截图路径
- 建议的恢复策略

### 恢复引擎

**RecoveryEngine** 提供多种预定义恢复动作：
- `wait`：等待页面稳定
- `refresh`：刷新页面
- `screenshot`：重新截图验证
- `retry`：重试失败步骤

### 内存监控与浏览器回收

- 框架自动监控浏览器内存使用
- 每执行 50 个步骤后自动回收浏览器实例，防止内存泄漏
- 可在配置文件中调整回收频率

### 快照恢复

框架支持在关键步骤保存执行快照，失败时可从最近的快照恢复，避免从头重新执行。

### 配置选项

所有异常处理和恢复策略可在 `config/default_config.yaml` 中配置：

```yaml
exception_handling:
  auto_screenshot: true
  max_retry_count: 3
  recovery_strategy: "auto"
  browser_recycle_interval: 50
  enable_snapshot: true
```

详细配置说明请参考 [EXCEPTION_HANDLING.md](EXCEPTION_HANDLING.md)。

## 9. 进阶学习

- **用例编写规范**：[TEST_CASE_WRITING_GUIDE.md](TEST_CASE_WRITING_GUIDE.md)（最重要）
- **API 测试**：[API_TESTING_GUIDE.md](API_TESTING_GUIDE.md)
- **架构说明**：[../design/ARCHITECTURE.md](../design/ARCHITECTURE.md)
- **故障排查**：[TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

**下一步**：阅读 [TEST_CASE_WRITING_GUIDE.md](TEST_CASE_WRITING_GUIDE.md) 了解完整的用例编写规范。
