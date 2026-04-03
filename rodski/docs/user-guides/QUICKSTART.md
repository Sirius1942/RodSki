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

### 智能等待机制

RodSki 内置**智能等待**功能，自动处理页面元素的加载延迟，无需手动添加 `wait` 步骤。

**工作原理：**
- 查找元素时，如果元素未加载完成，自动重试（默认 30 次，间隔 300ms）
- 元素出现后立即执行，无需等待完整超时时间
- 快速响应的元素无额外延迟（首次立即尝试）

**默认配置：**
- 最多等待 9 秒（30 次 × 0.3 秒）
- 自动启用，无需配置

**适用场景：**
- ✅ 动态加载的页面元素（React、Vue 等前端框架）
- ✅ 网络延迟导致的元素延迟出现
- ✅ 异步渲染的内容
- ✅ 移动应用的慢速加载

**自定义配置：**

编辑 `rodski/config/config.json`：

```json
{
  "smart_wait_enabled": true,           // 启用/禁用智能等待
  "smart_wait_max_retries": 30,         // 最大重试次数
  "smart_wait_retry_interval": 0.3,     // 重试间隔（秒）
  "smart_wait_log_retry": true          // 是否记录重试日志
}
```

**示例：增加等待时间**

对于特别慢的页面，可以增加重试次数或间隔：

```json
{
  "smart_wait_max_retries": 50,         // 增加到 50 次
  "smart_wait_retry_interval": 0.5      // 增加到 500ms
}
```

这样最多等待 25 秒（50 × 0.5s）。

**禁用智能等待：**

如果需要禁用（例如性能测试场景）：

```json
{
  "smart_wait_enabled": false
}
```

**注意事项：**
- 智能等待与 `wait` 关键字互补，不冲突
- 智能等待处理"元素未加载"问题
- `wait` 关键字处理"需要明确等待"问题（如动画完成、数据处理等）

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

## 7. 进阶学习

- **用例编写规范**：[TEST_CASE_WRITING_GUIDE.md](TEST_CASE_WRITING_GUIDE.md)（最重要）
- **API 测试**：[API_TESTING_GUIDE.md](API_TESTING_GUIDE.md)
- **架构说明**：[../design/ARCHITECTURE.md](../design/ARCHITECTURE.md)
- **故障排查**：[TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

**下一步**：阅读 [TEST_CASE_WRITING_GUIDE.md](TEST_CASE_WRITING_GUIDE.md) 了解完整的用例编写规范。
