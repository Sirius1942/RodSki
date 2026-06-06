# RodSki 契约摘要

本文档将 RodSki 文档压缩成 Codex 可执行检查清单。完整规范仍以 `rodski/docs/CORE_DESIGN_CONSTRAINTS.md` 和 `rodski/docs/TEST_CASE_WRITING_GUIDE.md` 为准。

## 架构边界

- RodSki 是确定性执行引擎与 XML 协议层。
- Agent 负责页面或应用探索、模型和用例生成、结果分析、重试策略和 XML 修复。
- RodSki 负责 XML 解析、Schema 校验、关键字执行、结果写入、截图和日志、确定性 Return/history 输出。
- 不要把 Agent 规划、多轮对话或策略编排移入 RodSki core。

## 安装与运行

在仓库根目录优先使用可编辑安装：

```bash
python3 -m venv .venv
source .venv/bin/activate

# 执行引擎基础安装
pip install -e .

# Web 测试能力
pip install -e ".[web]"
playwright install chromium

# 移动端能力
pip install -e ".[mobile]"

# 全部能力
pip install -e ".[all]"
```

本机未检测到 `rodski-agent`。除非用户重新安装并确认可执行文件存在，不要依赖 Agent 层 CLI。

常用 RodSki CLI：

```bash
RODSKI="/opt/homebrew/bin/rodski"
"$RODSKI" --version
"$RODSKI" run case/ --output-format json
"$RODSKI" run case/ --dry-run
"$RODSKI" run case/ --headless
"$RODSKI" run case/ --report html
"$RODSKI" init /path/to/MyTestModule
```

仅当 `/opt/homebrew/bin/rodski` 不可用，或直接调用 CLI 出现 `ModuleNotFoundError: No module named 'core'` 这类安装形态/PYTHONPATH 问题时，才临时使用历史 wrapper：

```bash
RODSKI="scripts/rodski.sh"
"$RODSKI" --version
```

常用数据命令：

```bash
"$RODSKI" data list rodski-demo/DEMO/demo_full/
"$RODSKI" data schema rodski-demo/DEMO/demo_full/ RegisterAPI
"$RODSKI" data show rodski-demo/DEMO/demo_full/ RegisterAPI L001
"$RODSKI" data query rodski-demo/DEMO/demo_full/ RegisterAPI --limit 20
"$RODSKI" data validate rodski-demo/DEMO/demo_full/
"$RODSKI" data import <module>
"$RODSKI" data import <module> --overwrite
```

本机入口以 skill wrapper 或用户明确指定的 CLI 为准。不要把旧参考里的版本号当作当前事实；每次执行前先运行 `--version`。

如果看到旧文档中的 `pip install -r rodski/requirements.txt`、`python3 rodski/cli_main.py ...`、`python rodski/ski_run.py ...`、`rodski explain ...`、`rodski init --with-verify --with-sqlite`、`rodski data validate --strict` 或 `rodski-agent ...`，只在重新确认本机工具支持后使用。

## 项目结构

使用以下模块结构：

```text
product/
└── {project}/
    └── {module}/
        ├── case/
        ├── model/
        │   └── model.xml
        ├── fun/
        ├── data/
        │   ├── data.sqlite
        │   └── globalvalue.xml
        └── result/
```

硬性规则：

- `product` 必须保持为最顶层产品根目录。
- 每个测试模块包含 `case/`、`model/`、`fun/`、`data/`、`result/`。
- `model.xml` 是唯一模型文件名。
- `data/data.sqlite` 是唯一固定测试数据文件。
- `data/globalvalue.xml` 保持为独立 XML 文件。
- `data.xml` 和 `data_verify.xml` 在 v6 已废弃；发现后使用 `"$RODSKI" data import <module>` 迁移，不要加载。

## 核心模型

RodSki 用例始终是：

```text
用例 = 关键字 + 模型 + 数据
```

匹配契约是强约束：

- Case 的 `test_step@action` 选择关键字。
- Case 的 `test_step@model` 指定模型。
- Case 的 `test_step@data` 只包含 DataID。
- 模型名等于逻辑数据表名。
- 模型 `element name` 等于数据表字段名，且区分大小写。
- `type Model L001` 读取逻辑表 `Model`。
- `send Model D001` 读取逻辑表 `Model`。
- `verify Model V001` 读取逻辑表 `Model_verify`。

批量关键字的 Case XML `data` 中不要写 `Model.DataID`。

## 关键字

主要关键字语义：

| 关键字 | 用途 | 说明 |
| --- | --- | --- |
| `navigate` | Web 或移动端 URL 导航 | 替代已废弃的 `open` |
| `launch` | 桌面应用启动或切换 | 与 `navigate` 同语义但仅用于 Desktop |
| `type` | UI 批量输入和动作 | Web、移动端、Desktop 统一 UI 写入关键字 |
| `send` | 接口请求 | 仅用于接口测试 |
| `verify` | 批量验证 | UI、API、DB 严格全字段匹配 |
| `check` | 兼容别名 | 等价于 `verify` |
| `DB` | 数据库查询或动作 | 使用数据库模型和 `globalvalue.xml` 连接 |
| `run` | Python 脚本执行 | 执行 `fun/` 下代码，stdout 成为 Return |
| `get` | 取值 | 优先使用 model+DataID 模式 |
| `set` | 保存命名变量 | 优先于脆弱的 Return 索引 |
| `wait` | 显式等待 | 不要用智能等待替代所有显式等待 |

不要把这些值加入 `action`：

```text
click / double_click / right_click / hover / select【值】
key_press【按键】 / drag【目标】 / scroll / scroll【x,y】
```

这些值属于数据字段值，由 `type` 批量模式解释执行。

不要新增 `http_get`、`http_post`、`http_put`、`http_delete`、`assert_json`、`assert_status` 等独立 HTTP 关键字。API 测试使用 `send` + `verify`。

## Case XML

使用三阶段容器格式：

```xml
<cases>
  <case execute="是" id="c001" title="登录测试" description="验证登录" component_type="界面">
    <pre_process>
      <test_step action="navigate" model="" data="GlobalValue.DefaultValue.URL/login"/>
    </pre_process>
    <test_case>
      <test_step action="type" model="Login" data="L001"/>
      <test_step action="verify" model="Login" data="V001"/>
    </test_case>
    <post_process>
      <test_step action="close" model="" data=""/>
    </post_process>
  </case>
</cases>
```

规则：

- 每个 `<case>` 必须且仅能包含一个 `<test_case>`。
- `<test_case>` 至少包含一个 `<test_step>`。
- `<pre_process>` 与 `<post_process>` 可选且最多各出现一次。
- `execute` 只能是 `是` 或 `否`。
- `component_type` 可选，可为 `界面`、`接口`、`数据库`。
- `test_step@action` 必须匹配 `rodski/schemas/case.xsd`。
- `verify` 必须同时有 model 和 DataID；它不是只传 locator 的断言捷径。

## Model XML

始终使用完整定位器格式：

```xml
<models>
  <model name="Login" driver_type="web">
    <element name="username" type="web">
      <type>input</type>
      <location type="id" priority="1">username</location>
      <location type="css" priority="2">input[name="username"]</location>
    </element>
  </model>
</models>
```

定位器规则：

- 只能使用 `<location type="类型">值</location>`。
- 不要使用旧简化格式 `<element type="id" value="username"/>`。
- 不要使用旧 `locator="..."` 格式。
- `priority` 支持多定位器回退，数字越小越优先。
- 传统定位器包括 `id`、`class`、`css`、`xpath`、`text`、`tag`、`name`。
- 视觉定位器包括 `vision`、`ocr`、`vision_bbox`。

接口模型：

- `_method`、`_url`、`_header_*` 保留给请求元数据。
- 普通元素名映射请求或响应字段。
- 静态 method/URL 可用 `<location type="static">`。
- 数据字段使用 `<location type="field">field_name</location>`。

数据库模型：

- Case XML 中 `DB` 步骤的 `model` 指向 `type="database"` 的模型。
- 数据库模型声明 `connection`，映射到 `globalvalue.xml` 中的组。
- Case XML 的 `model` 属性不要填写全局连接组名。

## SQLite 数据

所有测试数据都在 `data/data.sqlite` 中。底层逻辑使用 RodSki 的 EAV 元数据表，但行为基于逻辑表。

- 输入逻辑表名等于模型名。
- 验证逻辑表名是 `{ModelName}_verify`。
- 输入表使用 `table_kind='data'`。
- 验证表使用 `table_kind='verify'`。
- 同一逻辑表每行必须使用完全相同的字段集合。
- `DataID` 标识 Case XML `data` 选择的行。

逻辑映射示例：

```text
model Login
element username
element password
element loginBtn

data table Login, row L001:
username=admin
password=<example_password>
loginBtn=click

verify table Login_verify, row V001:
welcomeMsg=欢迎, admin
```

## GlobalValue XML

使用固定文件 `data/globalvalue.xml`：

```xml
<globalvalue>
  <group name="DefaultValue">
    <var name="URL" value="http://localhost:8000"/>
    <var name="WaitTime" value="500"/>
  </group>
  <group name="sqlite_db">
    <var name="type" value="sqlite"/>
    <var name="database" value="demo.db"/>
  </group>
</globalvalue>
```

规则：

- 每个 `group@name` 全局唯一。
- 每个 group 至少包含一个 `var`。
- 每个 `var` 必须同时有 `name` 和 `value`。
- 同一 group 内 `var@name` 唯一。
- 引用格式为 `GlobalValue.GroupName.VarName`。

## Return 与变量

会产生 Return 的关键字包括 `get`、`verify`、`type`、`send`、`DB`、`run`。

规则：

- 多步骤复用时，优先通过 `set`/`get` 使用命名变量。
- 不要在 Case XML `data` 中写 `${Return[-1]}`；它会在关键字分发前被解析，可能破坏批量模式。
- 接口/DB 的 `Model_verify` 表禁止用 `${Return[-1]}` 做期望值，因为 `verify` 会自动从最新 Return 读取实际值。
- UI `_verify` 表可以使用较早 Return，例如 `${Return[-2].token}`，用于跨源比对，因为 UI 实际值来自页面。
- 动态运行时步骤不得引入第二套语法；除非明确修改契约，否则应保持固定步骤 Return 语义。

## 接口测试

使用：

```xml
<test_step action="send" model="LoginAPI" data="D001"/>
<test_step action="verify" model="LoginAPI" data="V001"/>
```

规则：

- `send` 从接口模型和 `LoginAPI` 逻辑表读取请求元数据与字段。
- `send` 响应成为 Return，包含 `status` 与响应体字段。
- `verify` 从 `LoginAPI_verify` 读取期望值，并与 Return 响应字段比对。
- `_verify` 中的 `status` 是 HTTP 状态码期望值。
- 任意字段不匹配都会使步骤和用例失败。

## 数据库测试

使用：

```xml
<test_step action="DB" model="QuerySQL" data="Q001"/>
<test_step action="verify" model="QuerySQL" data="V001"/>
```

规则：

- `QuerySQL` 是数据库模型。
- 数据库模型的 `connection` 映射到 `globalvalue.xml` 组。
- SQL 行位于 `data.sqlite` 中的 `QuerySQL` 逻辑表。
- 同一逻辑表不要混用字段集合不兼容的行。

## 视觉定位

视觉能力是定位器级别，不是关键字级别。

```xml
<element name="loginBtn" type="web">
  <type>button</type>
  <location type="vision">登录按钮</location>
</element>

<element name="submitBtn" type="web">
  <type>button</type>
  <location type="vision_bbox">100,200,150,250</location>
</element>
```

规则：

- 不要新增 `vision_click`、`vision_input` 等视觉关键字。
- `vision` 是语义匹配，通常由 Agent 基于截图与 OmniParser 输出生成。
- `ocr` 是文字识别匹配。
- `vision_bbox` 格式是 `x1,y1,x2,y2`。
- Web 坐标是页面像素。
- Desktop 坐标是屏幕绝对坐标。

## 桌面端

Desktop 使用操作系统 driver type，例如 `windows` 或 `macos`。

规则：

- 使用 `launch`、`type`、`verify` 和已有关键字。
- Desktop 不支持 API `send`。
- 原生选择器不可用时，使用 `vision` 或 `vision_bbox`。
- Desktop 专属剪贴板、快捷键、窗口和应用控制操作用 `run` 调用 Python 脚本实现。
- 不要为剪贴板、组合键或窗口切换新增 Desktop 专用关键字。

## `run` 脚本

内置关键字无法覆盖场景时使用 `run`。

```xml
<test_step action="run" model="data_gen" data="gen_phone.py"/>
```

规则：

- 脚本位于 `fun/` 下。
- 脚本在独立 Python 子进程中执行。
- stdout 会被捕获为步骤 Return。
- 支持时，JSON stdout 应解析为结构化 Return 数据。

## 测试与验收

使用两层测试：

- 单元测试覆盖解析器、解析器辅助、关键字引擎、驱动和孤立行为。
- 验收测试通过 `rodski-demo` 的真实 case/model/data 组织方式完成。

对功能变更：

- 当行为影响 XML、数据或用户流程时，在 `rodski-demo` 下新增或更新至少一个真实 demo case。
- 新增用户可见能力时，同步补充匹配的 `model/` 和 `data/`。
- 运行定向单元测试和相关 demo 验收。
- 新增或修改关键字时，同步更新 `case.xsd`、文档、解析器/执行器行为和测试。
- 修改 XML 或 Schema 约束时，更新 `TEST_CASE_WRITING_GUIDE.md`。
- 修改核心关键字行为或设计约束时，更新 `CORE_DESIGN_CONSTRAINTS.md`。
