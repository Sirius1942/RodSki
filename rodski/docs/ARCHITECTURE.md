# RodSki 执行引擎架构文档

> RodSki 是面向 AI Agent 的跨平台确定性测试执行引擎。

## 1. 项目目录结构

```
rodski/
├── cli_main.py              # CLI 入口点
├── ski_run.py               # 简化运行入口
├── pyproject.toml           # 安装配置
│
├── rodski_cli/                 # CLI 子命令模块
│   ├── __init__.py
│   ├── run.py               # run 子命令 - 执行测试用例
│   ├── model.py             # model 子命令 - 模型管理
│   ├── config.py            # config 子命令 - 配置管理
│   ├── log.py               # log 子命令 - 日志查看
│   ├── report.py            # report 子命令 - 报告生成
│   └── profile.py           # profile 子命令 - 性能分析
│
├── core/                    # 核心引擎层
│   ├── __init__.py
│   ├── ski_executor.py      # ⭐ SKI执行引擎 - 主执行器
│   ├── keyword_engine.py    # ⭐ 关键字引擎 - 14+关键字实现
│   ├── task_executor.py     # 任务执行器 - 步骤执行与重试
│   ├── parallel_executor.py # 并发执行器 - 多线程执行
│   ├── case_parser.py       # 用例解析器 - Case Sheet解析
│   ├── data_table_parser.py # 数据表解析器 - 数据驱动
│   ├── model_parser.py      # 模型解析器 - XML元素定位
│   ├── global_value_parser.py # 全局变量解析器
│   ├── data_parser.py       # 数据引用解析器
│   ├── result_writer.py     # 结果回写器 - 测试结果回填
│   ├── config_manager.py    # 配置管理器
│   ├── logger.py            # 日志管理
│   ├── exceptions.py        # 自定义异常
│   ├── performance.py       # 性能监控装饰器
│   └── profiler.py          # 性能分析器
│
├── drivers/                 # 驱动适配层
│   ├── __init__.py
│   ├── base_driver.py       # ⭐ 抽象基类 - 统一接口定义
│   ├── playwright_driver.py # Playwright 驱动 - Web自动化
│   ├── appium_driver.py     # Appium 驱动 - 移动端
│   ├── android_driver.py    # Android 专用驱动
│   ├── ios_driver.py        # iOS 专用驱动
│   └── pywinauto_driver.py  # Pywinauto 驱动 - Windows桌面
│
├── data/                    # 数据处理层
│   ├── __init__.py
│   ├── data_resolver.py     # 数据解析器 - 引用解析
│   └── model_manager.py     # 模型管理器
│
├── api/                     # API 测试支持
│   ├── __init__.py
│   └── rest_helper.py       # RESTful API 辅助工具
│
├── config/                  # 配置文件
├── logs/                    # 日志输出
├── screenshots/             # 截图存储
└── product/                 # 产品用例目录
```

---

## 2. 核心架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLI Layer (入口层)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   cli_main.py ──► rodski_cli/run.py ──► rodski run case/ [options]               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Core Engine Layer (核心引擎层)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐      │
│  │   SKIExecutor    │───►│  KeywordEngine   │───►│   BaseDriver     │      │
│  │   (主执行器)      │    │   (关键字引擎)    │    │   (驱动接口)      │      │
│  └────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘      │
│           │                       │                        │                │
│           │              ┌────────┴────────┐               │                │
│           │              │                 │               │                │
│           ▼              ▼                 ▼               ▼                │
│  ┌──────────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────────┐ │
│  │  TaskExecutor    │  │ 14+关键字   │  │ API/send   │  │ Playwright     │ │
│  │  (步骤执行/重试)   │  │ type/send  │  │ RestHelper │  │ Appium         │ │
│  └──────────────────┘  │ verify/... │  │            │  │ Pywinauto      │ │
│                        └────────────┘  └────────────┘  └────────────────┘ │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      ParallelExecutor (并发执行器)                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Parser Layer (解析层)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐               │
│  │  CaseParser    │  │ ModelParser    │  │DataTableParser │               │
│  │  (用例解析)     │  │  (模型解析)     │  │  (数据表解析)   │               │
│  └────────────────┘  └────────────────┘  └────────────────┘               │
│          │                   │                     │                       │
│          ▼                   ▼                     ▼                       │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐               │
│  │   Case Sheet   │  │  XML 元素定义   │  │  数据表 Sheet   │               │
│  │  三段式结构     │  │  定位器映射     │  │  DataID/字段    │               │
│  └────────────────┘  └────────────────┘  └────────────────┘               │
│                                                                             │
│  ┌────────────────┐  ┌────────────────┐                                    │
│  │GlobalValueParser│ │  DataResolver  │                                    │
│  │  (全局变量)      │ │  (数据引用解析) │                                    │
│  └────────────────┘  └────────────────┘                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Output Layer (输出层)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐               │
│  │  ResultWriter  │  │     Logger     │  │   Profiler     │               │
│  │  (结果回填)     │  │   (日志记录)    │  │  (性能分析)     │               │
│  └────────────────┘  └────────────────┘  └────────────────┘               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 关键类调用关系图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                 执行流程                                     │
└─────────────────────────────────────────────────────────────────────────────┘

                    用户命令
                        │
                        ▼
    ┌───────────────────────────────────────┐
    │           cli_main.py                 │
    │   main() → handlers["run"](args)      │
    └───────────────────┬───────────────────┘
                        │
                        ▼
    ┌───────────────────────────────────────┐
    │         rodski_cli/run.py                │
    │   handle(args)                        │
    │   ├── CaseParser.parse()              │
    │   ├── ModelParser.parse()             │
    │   ├── DataTableParser.parse()         │
    │   ├── PlaywrightDriver()              │
    │   ├── KeywordEngine(driver)           │
    │   └── TaskExecutor(engine)            │
    └───────────────────┬───────────────────┘
                        │
          ┌─────────────┴─────────────┐
          │                           │
          ▼                           ▼
┌─────────────────────┐    ┌─────────────────────┐
│   XML 解析器组       │    │   TaskExecutor      │
│ ┌─────────────────┐ │    │ ┌─────────────────┐ │
│ │ CaseParser      │ │    │ │ execute_steps() │ │
│ │ ModelParser     │ │    │ │ _execute_retry()│ │
│ │ DataTableParser │ │    │ └────────┬────────┘ │
│ └─────────────────┘ │    └──────────┼──────────┘
└─────────────────────┘              │
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │     KeywordEngine       │
                         │ ┌─────────────────────┐ │
                         │ │ execute(kw, params) │ │
                         │ │ _kw_type()          │ │
                         │ │ _kw_send()          │ │
                         │ │ _kw_verify()        │ │
                         │ │ ... (14+ 关键字)     │ │
                         │ └──────────┬──────────┘ │
                         └────────────┼────────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │      BaseDriver         │
                         │   (抽象接口)             │
                         │ ┌─────────────────────┐ │
                         │ │ click(locator)      │ │
                         │ │ type(locator, text) │ │
                         │ │ navigate(url)       │ │
                         │ │ http_get(url)       │ │
                         │ └──────────┬──────────┘ │
                         └────────────┼────────────┘
                                      │
          ┌───────────────────────────┼───────────────────────────┐
          │                           │                           │
          ▼                           ▼                           ▼
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│  PlaywrightDriver   │    │   AppiumDriver      │    │  PywinautoDriver    │
│ ┌─────────────────┐ │    │ ┌─────────────────┐ │    │ ┌─────────────────┐ │
│ │ click()         │ │    │ │ click()         │ │    │ │ click()         │ │
│ │ type()          │ │    │ │ type()          │ │    │ │ type()          │ │
│ │ navigate()      │ │    │ │ tap()           │ │    │ │ send_keys()     │ │
│ │ screenshot()    │ │    │ │ swipe()         │ │    │ │ click_element() │ │
│ └─────────────────┘ │    │ └─────────────────┘ │    │ └─────────────────┘ │
│   Web 自动化         │    │   移动端自动化       │    │   Windows 桌面      │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
```

---

## 4. SKI 用例执行流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           XML 用例文件结构                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    case/*.xml (用例定义)                              │   │
│  │  <cases>                                                            │   │
│  │    <case execute="是" id="TC001" title="登录">                      │   │
│  │      <pre_process>                                                  │   │
│  │        <test_step action="navigate" model="" data="..."/>           │   │
│  │      </pre_process>                                                 │   │
│  │      <test_case>                                                    │   │
│  │        <test_step action="type" model="Login" data="L001"/>         │   │
│  │        <test_step action="verify" model="Login" data="V001"/>       │   │
│  │      </test_case>                                                   │   │
│  │      <post_process>                                                 │   │
│  │        <test_step action="close" model="" data=""/>                 │   │
│  │      </post_process>                                                │   │
│  │    </case>                                                          │   │
│  │  </cases>                                                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    data/data.xml (数据表)                             │   │
│  │  <datatable name="Login">                                           │   │
│  │    <row id="L001" remark="正常登录">                                 │   │
│  │      <field name="username">admin</field>                           │   │
│  │      <field name="password">123456</field>                          │   │
│  │    </row>                                                           │   │
│  │    <row id="L002" remark="错误密码">                                 │   │
│  │      <field name="username">admin</field>                           │   │
│  │      <field name="password">wrong</field>                           │   │
│  │    </row>                                                           │   │
│  │  </datatable>                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        model/model.xml (元素定位)                     │   │
│  │  <model name="LoginPage">                                           │   │
│  │    <element name="username">                                        │   │
│  │      <location type="id">username_input</location>                  │   │
│  │    </element>                                                       │   │
│  │    <element name="password">                                        │   │
│  │      <location type="css">.password-field</location>                │   │
│  │    </element>                                                       │   │
│  │  </model>                                                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              执行流程图                                      │
└─────────────────────────────────────────────────────────────────────────────┘

    开始
      │
      ▼
┌─────────────────┐
│  1. 加载配置     │
│  ConfigManager  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  2. 初始化解析器  │────►│  CaseParser     │────►│  解析用例列表    │
│                 │     │  ModelParser    │     │  解析元素定位    │
│                 │     │  DataTableParser│     │  解析测试数据    │
└────────┬────────┘     └─────────────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐
│  3. 初始化驱动    │
│  PlaywrightDriver│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  4. 遍历用例     │◄─────────────────────────────┐
└────────┬────────┘                              │
         │                                       │
         ▼                                       │
┌─────────────────────────────────────────────┐ │
│  5. 执行用例步骤                              │ │
│  ┌─────────────────────────────────────────┐│ │
│  │ 预处理 (pre_process)                     ││ │
│  │   └─► 0..n 个 test_step（navigate 等）    ││ │
│  ├─────────────────────────────────────────┤│ │
│  │ 用例阶段 (test_case)                     ││ │
│  │   └─► 1..n 个 test_step（type/verify…）  ││ │
│  ├─────────────────────────────────────────┤│ │
│  │ 后处理 (post_process)                    ││ │
│  │   └─► 0..n 个 test_step（close 等）       ││ │
│  └─────────────────────────────────────────┘│ │
└────────────────────┬────────────────────────┘ │
                     │                          │
         ┌───────────┴───────────┐              │
         ▼                       ▼              │
   ┌───────────┐           ┌───────────┐        │
   │   PASS    │           │   FAIL    │        │
   │  记录结果  │           │ 自动截图   │        │
   └───────────┘           │ 记录错误   │        │
                           └───────────┘        │
                     │                          │
                     └──────────┬───────────────┘
                                │
                                ▼
                    ┌─────────────────┐
                    │  6. 结果回填     │
                    │  ResultWriter   │
                    │  更新结果 XML   │
                    └────────┬────────┘
                             │
                             ▼
                          结束
```

---

## 5. 关键字清单 (14+)

### UI 操作关键字
| 关键字 | 功能 | 参数 |
|--------|------|------|
| `navigate` | 导航到URL（无浏览器时自动创建） | url/data |
| `close` | 关闭浏览器 | - |
| `type` | UI 批量输入（PC/移动端统一） | model, data 或 locator, text |
| `verify` | 批量验证（UI + 接口通用） | model, data |
| `check` | verify 的兼容别名 | model, data |
| `wait` | 等待 | seconds/data |
| `screenshot` | 截图 | path |
| `assert` | 断言元素 | locator, expected |
| `upload_file` | 上传文件 | locator, file_path |
| `clear` | 清空输入 | locator |
| `get_text` | 获取文本 | locator, var_name |

> click / select / hover / drag / scroll / double_click / right_click / key_press 作为数据表字段值在 `type` 批量模式中使用。

### 接口测试关键字
| 关键字 | 功能 | 参数 |
|--------|------|------|
| `send` | 发送接口请求（模型定义请求方式+URL） | model=接口模型名, data=DataID |

> 接口测试通过 `send`（发送请求）+ `verify`（验证响应）完成。接口模型定义 _method/_url/_header_* 等属性，verify 数据表（ModelName_verify）包含 status 列。

### 高级关键字
| 关键字 | 功能 | 参数 |
|--------|------|------|
| `set` | 设置变量 | var_name, value |
| `run` | 沙箱执行 Python 代码 | model=工程名, data=代码路径 |
| `DB` | 数据库操作 | operation, query, var_name |

---

## 6. 核心类职责

### 6.1 SKIExecutor (核心执行引擎)
```python
职责: 协调整个测试执行流程
位置: core/ski_executor.py

主要方法:
├── __init__(case_file, model_file, driver, config)
│   初始化解析器、关键字引擎、结果回写器
│
├── execute_all_cases()
│   批量执行所有用例
│
├── execute_case(case)
│   执行单个用例（预处理→用例阶段多步→后处理；用例失败仍执行后处理）
│
└── _take_failure_screenshot(case_id)
    失败时自动截图
```

### 6.2 KeywordEngine (关键字引擎)
```python
职责: 解析并执行测试关键字
位置: core/keyword_engine.py

特性:
├── 14+ 关键字支持
├── 自动重试机制 (max_retries, retry_delay)
├── 数据引用解析
├── 返回值存储 (store_return/get_return)
└── 性能监控装饰器

主要方法:
├── execute(keyword, params) → bool
│   执行关键字（支持重试）
│
├── _kw_xxx(params)
│   各关键字的实现方法
│
└── set_retry_config(config)
    动态配置重试策略
```

### 6.3 BaseDriver (驱动抽象基类)
```python
职责: 定义统一的驱动接口
位置: drivers/base_driver.py

抽象方法 (子类必须实现):
├── click(locator) → bool
├── type(locator, text) → bool
├── check(locator) → bool
├── wait(seconds) → None
├── navigate(url) → bool
├── screenshot(path) → bool
├── select(locator, value) → bool
├── hover(locator) → bool
├── drag(from_loc, to_loc) → bool
├── scroll(x, y) → bool
├── assert_element(locator, expected) → bool
├── close() → None

实现类:
├── PlaywrightDriver  (Web自动化)
├── AppiumDriver      (移动端)
├── AndroidDriver     (Android专用)
├── iOSDriver         (iOS专用)
└── PywinautoDriver   (Windows桌面)
```

### 6.4 CaseParser (用例解析器)
```python
职责: 解析 case/*.xml（XSD: case.xsd）
位置: core/case_parser.py

三阶段容器结构（每阶段内为 test_step 列表）:
├── pre_process: List[step]   # 预处理，0..n 步
├── test_case: List[step]     # 用例阶段，至少 1 步
└── post_process: List[step]  # 后处理，0..n 步

输出格式（每步为 dict: action, model, data）:
{
    'case_id': 'c001',
    'title': '登录测试',
    'pre_process': [{'action': 'navigate', 'model': '', 'data': '...'}],
    'test_case': [
        {'action': 'type', 'model': 'Login', 'data': 'L001'},
        {'action': 'verify', 'model': 'Login', 'data': 'V001'},
    ],
    'post_process': [{'action': 'close', 'model': '', 'data': ''}],
}
```

### 6.5 DataTableParser (数据表解析器)
```python
职责: 解析 XML 数据表，支持数据驱动测试
位置: core/data_table_parser.py

功能:
├── 自动识别数据表 (非 Main/Case/GlobalValue/TestResult/Logic)
├── 按 DataID 索引数据行
└── 支持动态字段

输出格式:
{
    'LoginData': {
        'data001': {'username': 'admin', 'password': '123456'},
        'data002': {'username': 'admin', 'password': 'wrong'}
    }
}
```

---

## 7. 数据流图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              数据流向                                        │
└─────────────────────────────────────────────────────────────────────────────┘

XML 用例文件
      │
      │ parse
      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  CaseParser ─────────► [{case_id, pre_process, test_case, ...}]            │
│  DataTableParser ────► {TableName: {DataID: {field: value}}}               │
│  ModelParser ────────► {ModelName: {ElementName: {type, value}}}           │
│  GlobalValueParser ──► {VarName: Value}                                     │
└─────────────────────────────────────────────────────────────────────────────┘
      │
      │ resolve
      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  DataResolver.resolve("LoginData.data001")                                  │
│      │                                                                      │
│      ├── 查找 DataTableParser.tables["LoginData"]["data001"]               │
│      ├── 替换全局变量引用 {{baseUrl}}                                        │
│      └── 返回解析后的数据 {"username": "admin", "password": "123456"}        │
└─────────────────────────────────────────────────────────────────────────────┘
      │
      │ execute
      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  KeywordEngine.execute("type", {model: "LoginPage", data: "..."})          │
│      │                                                                      │
│      ├── 获取模型元素定位 ModelParser.get_model("LoginPage")                │
│      │   └── {"username": {"type": "id", "value": "username_input"}}       │
│      │                                                                      │
│      └── 调用驱动 Driver.type("id=username_input", "admin")                 │
└─────────────────────────────────────────────────────────────────────────────┘
      │
      │ output
      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ResultWriter.write_results(results)                                        │
│      │                                                                      │
│      ├── 更新 result/*.xml 测试结果                                          │
│      └── 写入执行状态、耗时、错误信息、截图路径                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. 扩展机制

### 8.1 添加新驱动
```python
# 1. 创建新驱动文件 drivers/new_driver.py
from drivers.base_driver import BaseDriver

class NewDriver(BaseDriver):
    def click(self, locator: str, **kwargs) -> bool:
        # 实现点击逻辑
        pass
    
    # 实现其他抽象方法...

# 2. 在 rodski_cli/run.py 中注册
from drivers.new_driver import NewDriver
driver = NewDriver()
```

### 8.2 添加新关键字
```python
# 在 core/keyword_engine.py 中添加

# 1. 更新 SUPPORTED 列表
SUPPORTED = [..., "new_keyword"]

# 2. 实现关键字方法
def _kw_new_keyword(self, params: Dict) -> bool:
    # 获取参数
    param1 = params.get("param1", "")
    # 实现逻辑
    return True
```

### 8.3 添加 Hook（v8.2.0）

RodSki 提供两种 Hook 挂载方式，覆盖不同的使用场景。设计详见 `.pb/specs/rodski-hooks-design.md`，事件清单与用法示例见 `rodski/docs/HOOKS_REFERENCE.md`。

**进程内 Python 回调**（`before_keyword`/`after_keyword`/`on_case_failure`）：直接通过 `SKIExecutor(hooks=...)` 构造参数注入，适合 rodski-agent 等以 Python API 方式调用 rodski 的场景。

```python
from core.ski_executor import SKIExecutor
from core.keyword_engine import HookDecision

def deny_prod_db_write(keyword, params):
    if keyword == "DB" and "prod" in (params.get("data") or ""):
        return HookDecision(allow=False, reason="禁止在生产库上执行 DB 写操作")
    return HookDecision(allow=True)

executor = SKIExecutor(
    case_path="case/",
    driver=driver,
    hooks={"before_keyword": [deny_prod_db_write]},
)
```

**外部命令 Hook**（`on_session_start`/`on_run_start`/`on_case_failure`/`on_run_end`）：通过项目内 `hooks.json`（或全局 `~/.rodski/hooks.json`）配置，上下文以 JSON 经 stdin 传入，退出码 0/2/其他分别对应 allow/deny/warning。适合与外部系统（通知、审批、自定义合规规则）集成，不需要写 Python 代码。

```json
{
  "on_run_start": [{"command": ["python3", "scripts/check_env.py"], "timeout": 10}]
}
```

`on_run_start` 还内置了目录结构、`@plan_id`/selector 互斥、`data.sqlite` schema 一致性、接口/DB `_verify` 表 `${Return[-1]}` 自引用四类合规检查（`core/compliance_check.py`），检查失败默认阻止执行，可用 `--force-compliance` 显式跳过（目录结构缺失除外），跳过会记录到日志留痕。

`on_case_failure` 挂载点同时用于接入 `DiagnosisEngine`：配置 `SKIExecutor(diagnosis_engine=...)` 后，case 失败时自动生成诊断报告并写入 `report_collector`。

### 8.4 漫游测试架构（v8.3.0）

漫游建立在 v8.2.0 的进程内 Hook 机制上，但不要求 Agent 或自定义 Handler 才能运行。核心 `DataRoamDecisionEngine` 提供纯规则、零 LLM 的默认数据探索；`on_case_pass_roam_ready` 只作为可选覆盖点，可返回实现 `next_action(context)` 的引擎、引擎 factory，或首个 decision。Hook 缺失、回调异常或返回值不可用时回退核心默认引擎。

```text
pre_process
    → test_case（成功）
    → 三层资格检查
    → on_case_pass_roam_ready（可选覆盖）
    → _run_roam_session()（同步）
    → post_process（恰好一次）
```

三层资格检查是 `Roam.Enabled=是`、`case.roam="是"` 和 CLI 显式使用 `roam --case`/`run --roam`。漫游只支持 `component_type` 为空或 `界面` 的用例。基础用例 PASS/FAIL 由原有 case 流程决定，漫游 finding、动作失败和预算停止都不改写状态。

`_run_roam_session()` 将每个决策动作适配成普通 test-step 字典，直接同步调用 `_run_steps([step], "漫游")`。如果动作需要临时 model/data，执行器先保存资源快照，经 `apply_insert_resources` 应用，执行后在 `finally` 恢复。漫游不是外部控制命令，不通过运行时命令队列的 insert 通道。

`RoamSessionGuard` 统一处理变体数、时长、token、成本、最低置信度、可逆性和 `(action, model, data)` 去重。核心默认引擎不调用 LLM；自定义引擎可以在 decision 中回报 usage。预算耗尽写为正常 `stopped_reason`，不抛异常。

`TestMapStore` 把探索增量写入可选的 `knowledge/test_map.json`：schema 1、5 秒标准库跨平台锁、锁内 read-modify-write、按节点 ID 与 `(from,to,action)` 边去重，并用原子替换落盘；更高 schema 版本只读。目录只在首次写入时自动创建。

v8.3.0 MVP 的 `roam_summary` 仅附加到结果字典并由 JSON formatter 透传。`result.xsd`、报告 dataclass 和 HTML 可视化保持原状，作为 v2 范围。

---

## 9. CLI 命令速查

```bash
# 执行测试用例
rodski run case/

# 详细输出模式
rodski run case/ --verbose

# 无头模式
rodski run case/ --headless

# 失败重试
rodski run case/ --retry 3

# 仅验证不执行
rodski run case/ --dry-run

# 显示性能统计
rodski run case/ --performance

# 查看配置
rodski config list

# 查看日志
rodski log tail
```

---

*文档生成时间: 2026-03-19*
