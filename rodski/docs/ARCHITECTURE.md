# RodSki 项目架构文档

## 1. 项目目录结构

```
rodski/
├── cli_main.py              # CLI 入口点
├── ski_run.py               # 简化运行入口
├── setup.py                 # 安装配置
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
│   ├── keyword_engine.py    # ⭐ 关键字引擎 - 28+关键字实现
│   ├── task_executor.py     # 任务执行器 - 步骤执行与重试
│   ├── parallel_executor.py # 并发执行器 - 多线程执行
│   ├── case_parser.py       # 用例解析器 - Case Sheet解析
│   ├── data_table_parser.py # 数据表解析器 - 数据驱动
│   ├── model_parser.py      # 模型解析器 - XML元素定位
│   ├── global_value_parser.py # 全局变量解析器
│   ├── data_parser.py       # 数据引用解析器
│   ├── result_writer.py     # 结果回写器 - Excel结果回填
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
│   ├── excel_parser.py      # Excel 解析器
│   └── data_resolver.py     # 数据解析器 - 引用解析
│
├── api/                     # API 测试支持
│   ├── __init__.py
│   └── rest_helper.py       # RESTful API 辅助工具
│
├── ui/                      # GUI 界面 (可选)
│   ├── __init__.py
│   └── main_window.py
│
├── utils/                   # 工具函数
│   ├── __init__.py
│   └── helpers.py
│
├── tests/                   # 测试套件
│   ├── unit/                # 单元测试
│   ├── integration/         # 集成测试
│   └── functional/          # 功能测试
│
├── examples/                # 示例用例
│   ├── baidu_test/
│   ├── android_example.py
│   └── ios_example.py
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
│   cli_main.py ──► rodski_cli/run.py ──► rodski run case.xlsx [options]           │
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
│  │  TaskExecutor    │  │ 28+关键字   │  │ HTTP/API   │  │ Playwright     │ │
│  │  (步骤执行/重试)   │  │ click/type │  │ http_get   │  │ Appium         │ │
│  └──────────────────┘  │ wait/...   │  │ http_post  │  │ Pywinauto      │ │
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
    │   ├── ExcelParser.parse()             │
    │   ├── PlaywrightDriver()              │
    │   ├── KeywordEngine(driver)           │
    │   └── TaskExecutor(engine)            │
    └───────────────────┬───────────────────┘
                        │
          ┌─────────────┴─────────────┐
          │                           │
          ▼                           ▼
┌─────────────────────┐    ┌─────────────────────┐
│    ExcelParser      │    │   TaskExecutor      │
│ ┌─────────────────┐ │    │ ┌─────────────────┐ │
│ │ parse()         │ │    │ │ execute_steps() │ │
│ │ validate()      │ │    │ │ _execute_retry()│ │
│ └─────────────────┘ │    │ └────────┬────────┘ │
└─────────────────────┘    └──────────┼──────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │     KeywordEngine       │
                         │ ┌─────────────────────┐ │
                         │ │ execute(kw, params) │ │
                         │ │ _kw_click()         │ │
                         │ │ _kw_type()          │ │
                         │ │ _kw_http_get()      │ │
                         │ │ ... (28+ 关键字)     │ │
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
│                           Excel 用例文件结构                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                          Case Sheet                                  │   │
│  ├─────┬───────┬───────┬────────────────────────────────────────────────┤   │
│  │执行 │CaseID │ 标题  │ 预处理 │ 测试步骤 │ 预期结果 │ 后处理           │   │
│  │控制 │       │       │action │ action  │ action  │ action           │   │
│  ├─────┼───────┼───────┼────────────────────────────────────────────────┤   │
│  │ 是  │TC001  │登录   │open   │ type    │ assert  │ close            │   │
│  │     │       │       │       │ click   │         │                  │   │
│  └─────┴───────┴───────┴────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      数据表 Sheet (LoginData)                        │   │
│  ├─────────┬─────────┬──────────┬─────────────┐                         │   │
│  │ DataID  │ Remark  │ username │  password   │                         │   │
│  ├─────────┼─────────┼──────────┼─────────────┤                         │   │
│  │ data001 │ 正常登录 │ admin    │ 123456      │                         │   │
│  │ data002 │ 错误密码 │ admin    │ wrong       │                         │   │
│  └─────────┴─────────┴──────────┴─────────────┘                         │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        model.xml (元素定位)                          │   │
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
│  │   └─► open → navigate                    ││ │
│  ├─────────────────────────────────────────┤│ │
│  │ 测试步骤 (test_step)                     ││ │
│  │   └─► type → click                       ││ │
│  ├─────────────────────────────────────────┤│ │
│  │ 预期结果 (expected_result)               ││ │
│  │   └─► assert → check                     ││ │
│  ├─────────────────────────────────────────┤│ │
│  │ 后处理 (post_process)                    ││ │
│  │   └─► close                              ││ │
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
                    │  更新 Excel     │
                    └────────┬────────┘
                             │
                             ▼
                          结束
```

---

## 5. 关键字清单 (28+)

### UI 操作关键字
| 关键字 | 功能 | 参数 |
|--------|------|------|
| `open` | 打开URL | url/data |
| `close` | 关闭浏览器 | - |
| `click` | 点击元素 | locator |
| `type` | 输入文本 | locator, text |
| `check` | 检查元素可见 | locator |
| `wait` | 等待 | seconds/data |
| `navigate` | 导航 | url |
| `screenshot` | 截图 | path |
| `select` | 下拉选择 | locator, value |
| `hover` | 悬停 | locator |
| `drag` | 拖拽 | from, to |
| `scroll` | 滚动 | x, y |
| `assert` | 断言元素 | locator, expected |
| `upload_file` | 上传文件 | locator, file_path |
| `clear` | 清空输入 | locator |
| `double_click` | 双击 | locator |
| `right_click` | 右键点击 | locator |
| `key_press` | 按键 | key |
| `get_text` | 获取文本 | locator, var_name |

### HTTP/API 关键字
| 关键字 | 功能 | 参数 |
|--------|------|------|
| `http_get` | GET请求 | url, headers, expected_status |
| `http_post` | POST请求 | url, body, headers, expected_status |
| `http_put` | PUT请求 | url, body, headers, expected_status |
| `http_delete` | DELETE请求 | url, headers, expected_status |
| `assert_json` | JSON断言 | path, expected |
| `assert_status` | 状态码断言 | expected |
| `send` | 通用HTTP请求 | url, method, body, headers |

### 高级关键字
| 关键字 | 功能 | 参数 |
|--------|------|------|
| `set` | 设置变量 | var_name, value |
| `run` | 执行Logic用例 | case_name, case_file |
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
│   执行单个用例（预处理→测试步骤→预期结果→后处理）
│
└── _take_failure_screenshot(case_id)
    失败时自动截图
```

### 6.2 KeywordEngine (关键字引擎)
```python
职责: 解析并执行测试关键字
位置: core/keyword_engine.py

特性:
├── 28+ 关键字支持
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
├── http_get(url, headers) → Response
├── http_post(url, body, headers) → Response
├── http_put(url, body, headers) → Response
└── http_delete(url, headers) → Response

实现类:
├── PlaywrightDriver  (Web自动化)
├── AppiumDriver      (移动端)
├── AndroidDriver     (Android专用)
├── iOSDriver         (iOS专用)
└── PywinautoDriver   (Windows桌面)
```

### 6.4 CaseParser (用例解析器)
```python
职责: 解析 Excel 中的 Case Sheet
位置: core/case_parser.py

三段式用例结构:
├── pre_process (预处理)
├── test_step (测试步骤)
├── expected_result (预期结果)
└── post_process (后处理)

输出格式:
{
    'case_id': 'TC001',
    'title': '登录测试',
    'pre_process': {'action': 'open', 'model': '', 'data': 'url'},
    'test_step': {'action': 'type', 'model': 'LoginPage', 'data': 'LoginData.data001'},
    'expected_result': {...},
    'post_process': {...}
}
```

### 6.5 DataTableParser (数据表解析器)
```python
职责: 解析 Excel 数据表，支持数据驱动测试
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

Excel 用例文件
      │
      │ parse
      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  CaseParser ─────────► [{case_id, pre_process, test_step, ...}]            │
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
│      ├── 更新 Excel TestResult Sheet                                        │
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

---

## 9. CLI 命令速查

```bash
# 执行测试用例
rodski run case.xlsx

# 详细输出模式
rodski run case.xlsx --verbose

# 无头模式
rodski run case.xlsx --headless

# 失败重试
rodski run case.xlsx --retry 3

# 仅验证不执行
rodski run case.xlsx --dry-run

# 显示性能统计
rodski run case.xlsx --performance

# 查看配置
rodski config list

# 查看日志
rodski log tail
```

---

*文档生成时间: 2026-03-19*