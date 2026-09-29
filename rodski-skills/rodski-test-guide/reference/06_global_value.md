<!-- 自动生成 from rodski/docs/TEST_CASE_WRITING_GUIDE.md  请勿手工编辑 -->

## 6. GlobalValue XML — 全局变量

### 6.0 什么时候用全局变量

**判断标准：这个值是否"换一个环境就要改"，或者"整个模块共用、与单条用例无关"。** 是，就放 `globalvalue.xml`；否，就放 `data.sqlite` 或运行时变量。

**该用全局变量**

| 场景 | 例子 | 推荐组名 |
|------|------|----------|
| 随环境变化的地址 | 站点 URL、API 基址、第三方回调地址 | `DefaultValue.URL` 或按系统分组（如 `Site.URL`、`Api.BASE_URL`） |
| 与环境绑定的账号 | 测试环境的登录名、租户号（密码见下方"不该用"） | `Account` |
| 数据库连接 | 连接类型、地址、库名（被数据库模型的 `connection` 引用） | 与模型 `connection` 同名的组，如 `order_db` |
| 移动端设备与应用 | `Platform`、`UDID`、`AppPackage`、`BundleId`、Appium 地址 | `Mobile` |
| 模块内多个用例共享、且随环境变化的常量 | 默认门店编码、默认币种 | 按业务命名的组 |
| 框架执行策略 | `WaitTime`、`AutoWait`、`DialogPolicy`、`SessionMode`、`EvidenceMode`（见 [§6.3](#63-框架内置全局变量)、[§6.4](#64-waittime-与执行策略配置v1160)） | 固定为 `DefaultValue` |

**不该用全局变量**

| 值 | 应该放在 | 原因 |
|----|----------|------|
| 某条用例的输入数据、期望值 | `data.sqlite` 的数据表 / `_verify` 表 | 用例数据要跟用例一起维护、按 DataID 引用（[§5](#5-数据表--测试数据编写)） |
| 运行时产生的值（订单号、token、接口返回字段） | `set` / `get` 命名变量、`${Return[-N]}`、模型 `auto_capture` | 每次运行都不同，写死在全局变量里会过期 |
| 生产环境或个人的真实密码、密钥 | 不要写进任何被提交的文件；使用测试环境专用账号 | 避免把敏感信息提交进仓库（CORE §16.2）。框架目前不支持从环境变量读取 globalvalue，测试账号的密码如需放在 globalvalue，应只用于测试环境 |
| 只有一两条用例用到的常量 | 这些用例自己的数据行 | 全局变量越少越好找，不要把它当"公共常量池" |

**换环境只改 globalvalue**：用例、模型、数据表里凡是涉及环境的值都用 `GlobalValue.组名.变量名` 引用，切换 beta / ci / prod 时只替换 `globalvalue.xml`，其余文件不动（`rodski-skill--switch-rodski-env` 就是按这个约定工作的）。

```xml
<!-- beta 环境 -->
<globalvalue>
  <group name="DefaultValue">
    <var name="URL" value="https://beta.example.com"/>
    <var name="WaitTime" value="0"/>          <!-- 毫秒 -->
    <var name="AutoWait" value="5000"/>       <!-- 毫秒：verify 自动等待上限 -->
  </group>
  <group name="Account">
    <var name="Admin" value="qa_admin"/>
  </group>
  <group name="order_db">
    <var name="type" value="mysql"/>
    <var name="host" value="beta-db.example.com"/>
  </group>
</globalvalue>
```

```xml
<!-- 用例与数据表中只引用，不写死地址 -->
<test_step action="navigate" model="" data="GlobalValue.DefaultValue.URL/login"/>
```

数据表字段值同样可以写 `GlobalValue.Account.Admin`；数据库模型写 `connection="order_db"`，连接信息由同名组提供。

### 6.1 文件格式

全局变量文件固定命名为 `globalvalue.xml`，存放在 `data/` 目录下。

**与 `globalvalue.xsd` 一致**：全文件内 **`<group name="...">` 不得重名**；同一 `<group>` 内 **`<var name="...">` 不得重名**；每个 `<var>` 必须同时有 `name` 与 `value` 属性。

```xml
<?xml version="1.0" encoding="UTF-8"?>
<globalvalue>
  <group name="DefaultValue">
    <var name="URL" value="http://127.0.0.1:5555"/>
    <var name="BrowserType" value="chromium"/>
    <var name="WaitTime" value="0"/>           <!-- 毫秒；0 = 不做固定等待 -->
    <var name="AutoWait" value="5000"/>        <!-- 毫秒；自动等待：UI verify 自动重试上限 -->
    <var name="DialogPolicy" value="fail"/>
    <var name="SessionMode" value="shared_browser"/>
    <var name="EvidenceMode" value="full"/>
  </group>
  <group name="sqlite_db">
    <var name="type" value="sqlite"/>
    <var name="database" value="product/DEMO/demo_site/demo.db"/>
  </group>
  <group name="Roam">
    <var name="Enabled" value="否"/>
    <var name="MaxVariantsPerCase" value="5"/>
    <var name="MaxDurationSeconds" value="120"/>
    <var name="MinConfidenceToAct" value="0.6"/>
    <var name="MaxTokenBudget" value="20000"/>
    <var name="MaxCostUsd" value="0.5"/>
  </group>
</globalvalue>
```

### 6.2 引用语法

```
GlobalValue.组名.变量名
```

示例：

```
GlobalValue.DefaultValue.URL          → "http://127.0.0.1:5555"
GlobalValue.DefaultValue.WaitTime     → "0"
```

### 6.3 框架内置全局变量

| 组名 | Key | 说明 | 示例值 |
|------|-----|------|--------|
| DefaultValue | URL | 测试环境地址 | http://127.0.0.1:5555 |
| DefaultValue | BrowserType | 浏览器类型 | chromium / firefox / webkit |
| DefaultValue | WaitTime | 每步执行后的固定等待，单位**毫秒**（v11.6.0 起；旧值 ≤30 暂按秒兼容并告警） | 0 |
| DefaultValue | AutoWait | **自动等待**：UI `verify` 自动重试的上限，单位**毫秒**；`0` 关闭（v11.6.0） | 5000 |
| DefaultValue | DialogPolicy | 未注册处理器的原生弹窗：`accept` / `dismiss` / `fail`（v11.6.0） | fail |
| DefaultValue | SessionMode | 浏览器会话：`isolated` / `shared_browser` / `shared_session`（v11.6.0） | isolated |
| DefaultValue | EvidenceMode | 截图证据：`full` / `concise`（v11.6.0） | full |
| DefaultValue | Headless | 无头模式 | True / False |
| Roam | Enabled | 漫游全局开关；只有 `是` 才允许显式漫游 | 是 / 否 |
| Roam | MaxVariantsPerCase | 单个基础用例最多执行的漫游变体数 | 5 |
| Roam | MaxDurationSeconds | 单个漫游会话时长上限（秒） | 120 |
| Roam | MinConfidenceToAct | 自动执行动作的最低置信度 | 0.6 |
| Roam | MaxTokenBudget | 自定义/后续 LLM 引擎 token 上限；核心默认引擎不使用 LLM | 20000 |
| Roam | MaxCostUsd | 自定义/后续 LLM 引擎成本上限（美元） | 0.5 |

### 6.4 WaitTime 与执行策略配置（v11.6.0）

#### 6.4.1 WaitTime — 步骤固定等待（单位：毫秒）

设置 `DefaultValue.WaitTime` 后，框架在**每个步骤执行完成后**固定等待指定**毫秒**数。`<cases step_wait="...">` 同样是**毫秒**，写了就覆盖 `WaitTime`。

| 关键字 | 是否应用 WaitTime |
|--------|-----------------|
| navigate / type / verify / send 等 | 是 |
| wait | 否（wait 自身已包含等待） |
| close | 否（浏览器已关闭） |

**推荐 `WaitTime=0`**：交互等待由智能等待（元素出现即继续）和 `verify` 自动重试（[§5.7.2](#572-ui-verify-自动重试替代-wait)）负责，固定等待只用于演示或录屏。固定等待会按步数线性累加：20 步 × 1000ms = 每个用例多 20 秒。`WaitTime > 0` 或用例里出现数字字面量 `wait` 时，`rodski case lint` 会给出 WARNING 并估算耗时。

**单位迁移（v11.6.0 之前 WaitTime 按秒解析）**：

| 写法 | v11.6.0 起的解释 |
|------|------------------|
| `0` | 不等待 |
| `1` ~ `30`（旧写法） | **过渡期按秒**解释（`1` = 1 秒），并打印一次弃用告警：提示 WaitTime 已改为毫秒，请改写（如 `1` → `1000`） |
| `> 30` | 按毫秒解释（`500` = 0.5 秒） |

请尽快把旧值改写为毫秒；过渡兼容会在后续版本移除。

#### 6.4.2 AutoWait — 自动等待（单位：毫秒）

UI 模型的 `verify` 在 `AutoWait` 毫秒内反复读取、比对，直到全部字段匹配或超时（默认 `5000`，即 5 秒）。`0` 关闭重试（单次比对）。接口 / DB 的 `verify` 不受影响。单位与 `WaitTime`、`step_wait` 一致，都是毫秒。

- 11.6.0 开发期曾叫 `VerifyTimeout`（单位秒）；配置里如果还写着 `VerifyTimeout`，执行前会报错并提示改为 `AutoWait`。
- 作用范围：只控制 `verify` 的自动重试；元素出现前的智能等待（§13）仍用原有配置。详见 [§5.7.2](#572-ui-verify-自动重试替代-wait)。

#### 6.4.3 DialogPolicy — 未预期的原生弹窗

| 取值 | 行为 |
|------|------|
| `fail`（默认） | 出现未注册处理器的弹窗时，该步骤立即失败，错误信息包含弹窗文本；不会卡住等待，也不会静默吞掉 |
| `accept` | 自动确认（prompt 按其默认值确认） |
| `dismiss` | 自动取消 |

需要对某一次弹窗做特定处理时，用 `page=dialog` 元素注册一次性处理器，见 [4.3.4](#434-页面属性定位器-pagev1160)。

#### 6.4.4 SessionMode — 浏览器会话复用

| 取值 | 行为 | 隔离性 |
|------|------|--------|
| `isolated`（默认） | 每个用例启动一次浏览器 | 完全隔离 |
| `shared_browser`（推荐） | 整个 run 只启动一次浏览器，每个用例新建独立 context；用例里的 `close` 只关闭本用例的 context | cookie / localStorage / 页面按用例隔离 |
| `shared_session` | 所有用例共用同一个页面（相当于以往不写 `close`） | 不隔离 |

CLI `--session-mode` 可临时覆盖。配合登录态复用（[§8.8](#88-登录态复用save_auth_state--use_auth_statev1160)）可以省掉每个用例的 UI 登录。

#### 6.4.5 EvidenceMode — 截图证据模式

| 取值 | 行为 |
|------|------|
| `full`（默认） | 每步截图 + 失败截图 |
| `concise` | 只在步骤失败时截图（与失败截图相同的处理方式），不产生逐步截图 |

- 两种模式下**录像不受影响**：是否录像仍由 `--record` / `recording` 配置决定。
- `result.xml` 与 HTML 报告会标注本次使用的模式，避免误以为截图丢失。
- CLI `--evidence full|concise` 可临时覆盖。步数多、只关心失败现场时用 `concise` 节省时间；排查偶发问题时保持 `full` 并开启录像。

**非法取值**（如 `DialogPolicy=yes`）会在执行开始前报错并列出合法取值。优先级：CLI 参数 > `globalvalue.xml` > 默认值。

### 6.5 数据库连接配置

DB 关键字最终仍通过 `globalvalue.xml` 中的组读取数据库连接参数，但引用路径已调整为：

1. Case 中 `model` 填数据库模型名（如 `QuerySQL`）
2. 数据库模型通过 `connection="sqlite_db"` 指向连接组
3. 框架再到 `globalvalue.xml` 中读取 `sqlite_db` 组参数

| 组名 | Key | 说明 |
|------|-----|------|
| sqlite_db | type | 数据库类型：sqlite / mysql / postgresql / sqlserver |
| sqlite_db | host | 主机地址（sqlite 不需要） |
| sqlite_db | port | 端口号（sqlite 不需要） |
| sqlite_db | database | 数据库名或文件路径 |
| sqlite_db | username | 用户名 |
| sqlite_db | password | 密码 |

因此，Case XML 中 DB 关键字的 `model` 属性**不再**填写连接组名，而是填写数据库模型名。

---
