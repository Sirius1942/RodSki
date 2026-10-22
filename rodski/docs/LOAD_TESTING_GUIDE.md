# RodSki 性能压测指南

**版本**: v11.10.0  
**日期**: 2026-10-22  
**适用框架**: RodSki v11.10.0

---

## 目录

1. [概述](#1-概述)
2. [快速开始（5 分钟跑起来）](#2-快速开始5-分钟跑起来)
3. [核心概念](#3-核心概念)
   - 3.1 压测模式与功能测试模式的区别
   - 3.2 两个执行阶段：运行时 vs 预编译
4. [压测计划 XML（plan.xml）](#4-压测计划-xmlplanxml)
   - 4.1 最小示例
   - 4.2 load_profile 参数详解
   - 4.3 case 与 weight
   - 4.4 完整示例
5. [压测用例编写](#5-压测用例编写)
   - 5.1 用例约束
   - 5.2 接口模型（model.xml）
   - 5.3 测试数据（data.sqlite）
   - 5.4 全局变量（globalvalue.xml）
6. [目录结构](#6-目录结构)
7. [执行命令](#7-执行命令)
   - 7.1 基础执行
   - 7.2 实时监控（--load-ui）
   - 7.3 调试模式（--no-compile）
   - 7.4 dry-run 预览
8. [预编译产物（perf/）](#8-预编译产物perf)
   - 8.1 产物是什么
   - 8.2 缓存与失效
   - 8.3 手动优化（source: manual）
   - 8.4 脱离 RodSki 独立运行
9. [Locust Web UI 实时监控](#9-locust-web-ui-实时监控)
   - 9.1 启动方式
   - 9.2 可用端点
   - 9.3 指标说明
10. [压测结果（result.xml）](#10-压测结果resultxml)
11. [核心约束与注意事项](#11-核心约束与注意事项)
12. [常见问题](#12-常见问题)
13. [附录：压测相关错误码](#13-附录压测相关错误码)

---

## 1. 概述

RodSki v8.0 在接口测试能力（`send` / `verify` 关键字）之上，引入了**性能压测模式**。

核心设计原则：

> **已有的接口测试用例一行不改，直接复用于压测。** 所有压测配置（并发数、时长、爬坡策略）只在 `plan/*.xml` 中声明。

技术架构：

```
RodSki 用例 (case XML)
      │
      ├──► LoadCompiler（预编译，产物写入 perf/{plan_id}.py：标准 Locust locustfile，
      │                  可脱离 RodSki 独立运行；当前版本 rodski run 不加载它，见 3.2）
      │
      ▼ LocustLoadEngine（Locust FastHttpUser + LocalRunner；每个 VU 经 KeywordEngine 执行 case 步骤）
      │
      ▼ 并发执行（gevent greenlet）
      │
result/result_*.xml（含 <load_summary>，RPS/P95/错误率）
```

**依赖安装**：

```bash
pip install rodski[load]    # 安装 locust 可选依赖
```

---

## 2. 快速开始（5 分钟跑起来）

### 前提条件

- 已有接口测试模块（含 `case/`、`model/`、`data/` 目录）
- 用例的 `component_type="接口"`
- 目标服务正在运行

### Step 1：安装压测依赖

```bash
pip install rodski[load]
```

### Step 2：创建压测计划文件

在测试模块的 `plan/` 目录下新建 `my_load_plan.xml`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<test_plan id="my_load_plan" kind="load">
  <load_profile mode="api">
    <concurrency>10</concurrency>
    <duration_seconds>60</duration_seconds>
    <ramp_up_seconds>10</ramp_up_seconds>
    <think_time_ms min="200" max="800"/>
  </load_profile>
  <case id="your_case_id" file="your_case_file.xml" weight="1"/>
</test_plan>
```

### Step 3：执行压测

```bash
cd your/module/dir
rodski run @my_load_plan
```

### Step 4：查看结果

```
压测结果摘要
============================================================
  总请求数   : 1234
  错误率     : 0.00%
  平均 RPS   : 20.57
  P50 延迟   : 12 ms
  P95 延迟   : 45 ms
  P99 延迟   : 89 ms
  总耗时     : 60.2s
============================================================
```

结果文件保存在 `result/result_*.xml`，含完整的 `<load_summary>` 节点。

---

## 3. 核心概念

### 3.1 压测模式与功能测试模式的区别

压测模式（`kind="load"`）和功能测试模式（`kind="suite"`）是**完全独立的两条执行路径**，由 `plan.xml` 的 `kind` 属性决定，不需要额外参数。

| 维度 | 功能测试（suite） | 性能压测（load） |
|------|-----------------|----------------|
| 执行路径 | `SKIExecutor` | `LocustLoadEngine` |
| 用例执行次数 | 每条执行一次 | N 个 VU 反复执行 duration 秒 |
| 断言 | verify 失败则 case FAIL | `verify` / `check` / `assert` / `get` 步骤不执行；错误率只统计 HTTP 层失败 |
| 截图 | 失败时自动截图 | 不截图（避免影响性能指标）|
| post_process | 执行 | 不执行 |
| 结果关注点 | PASS / FAIL | RPS / P95 / 错误率 |

**互不影响**：同一套 case XML 既可 `rodski run @suite_plan` 做功能验收，也可 `rodski run @load_plan` 做性能压测。

### 3.2 两个执行阶段：预编译 vs 运行时解释

**预编译**（默认执行，`--no-compile` 时跳过）：

```
启动时 → LoadCompiler 将 case XML 翻译为 locustfile.py
        字面量字段 → Python 常量
        → 保存到 perf/{plan_id}.py（哈希未变则复用；生成失败只打印警告，继续压测）
```

**运行时**（当前版本只有这一条执行路径）：

```
每次迭代 → RodskiLoadUser → KeywordEngine → LoadDriver（Locust 客户端发请求并计时）
```

当前实现中，`rodski run @plan` **不会加载** `perf/{plan_id}.py`：无论是否加 `--no-compile`，压测都按上面的运行时路径执行，`--no-compile` 只是省掉生成产物这一步（CLI 帮助里"直接使用已有 perf/*.py"的说法与实现不符）。产物目前的用途是脱离 RodSki 独立运行（8.4）和归档追溯。该行为可能调整。

运行时路径的当前限制：
- 不解析数据字段和模型中的 `${...}` 占位符（`${GlobalValue...}`、`${Return[-1]...}`、`${random(...)}` 等）以及 `GlobalValue.组.变量` 引用，原样发送。压测用的数据行请写字面量。
- `verify` / `check` / `assert` / `get` 步骤跳过不执行。

---

## 4. 压测计划 XML（plan.xml）

### 4.1 最小示例

```xml
<?xml version="1.0" encoding="UTF-8"?>
<test_plan id="api_smoke_load" kind="load">
  <load_profile>
    <concurrency>5</concurrency>
    <duration_seconds>30</duration_seconds>
  </load_profile>
  <case id="login_api" file="api_login.xml"/>
</test_plan>
```

`<case>` 直接写在 `<test_plan>` 下，**没有** `<cases>` 包装层（`plan.xsd` 不允许，运行前的 XSD 校验会报 "Element 'cases': This element is not expected"）。完整写法参照 `rodski-demo/demosite/load/plan/api_load_basic.xml`。

### 4.2 load_profile 参数详解

| 参数 | 必填 | 类型 | 默认 | 说明 |
|------|------|------|------|------|
| `mode` 属性 | 否 | `api` \| `browser` | `api` | 压测引擎选择。当前只支持 `api`（Locust）；写 `browser` 时运行报 SKI605 并以非 0 退出（v11.8.29 起，此前被静默按 api 执行） |
| `concurrency` | ✅ | 正整数 | — | 并发虚拟用户数（VU）。建议从 10 起步，逐步调大 |
| `duration_seconds` | ✅ | 正整数 | — | 压测持续时长（秒）。建议最少 30s，稳态测试 300s+ |
| `ramp_up_seconds` | 否 | 非负整数 | `0` | 从 0 爬坡到目标 VU 的时长。0 表示立即达到目标并发 |
| `think_time_ms` | 否 | `min="..." max="..."` | 无 | VU 每次迭代之间的等待时间（毫秒范围）。模拟真实用户行为 |
| `max_rps` | 否 | 非负整数 | `0`（不限）| **当前未实现**：XSD 接受该节点，但运行时不读取，不会限速 |
| `host` | 否 | URI | GlobalValue 的 URL | 覆盖 globalvalue.xml 中的目标地址，适配多环境 |

**think_time 设置建议**：

| 场景 | 建议值 |
|------|--------|
| 极限压测（最大 RPS） | 不设，或 `min="0" max="0"` |
| 模拟真实用户 | `min="500" max="2000"` |
| API 集成测试 | `min="100" max="500"` |

### 4.3 case 与 weight

`<case>` 节点（直接写在 `<test_plan>` 下）引用 `case/` 目录下已有的用例：

```xml
<test_plan id="order_mix_load" kind="load">
  <load_profile mode="api">
    <concurrency>10</concurrency>
    <duration_seconds>60</duration_seconds>
  </load_profile>
  <!-- weight 控制各接口的调度比例，相对权重 -->
  <case id="login_api"     file="api_login.xml" execute="是" weight="1"/>
  <case id="query_orders"  file="api_order.xml" execute="是" weight="3"/>
  <case id="create_order"  file="api_order.xml" execute="是" weight="1"/>
</test_plan>
```

上例中，`query_orders` 的请求量约为总量的 3/5，`login_api` 和 `create_order` 各约 1/5。

**约束**：
- `id` 必须与 `case/*.xml` 中的 `<case id="...">` 完全一致
- `file` 写用例文件相对 `case/` 的路径。压测执行时按 `id` 在整个 `case/` 中查找；但 `--dry-run` 走计划选择逻辑，模块内有多个用例文件而没写 `file` 时报 SKI207，建议始终写上
- `execute="否"` 的 case 不参与压测
- `weight` 默认为 1，只在 `kind="load"` 的计划中有效
- 压测只读取 `<case>`：`<case_dir>` 在压测中不生效
- 不支持 `scenario` 级别选择，只能整 case 粒度

### 4.4 完整示例

```xml
<?xml version="1.0" encoding="UTF-8"?>
<test_plan id="order_service_load" kind="load" title="订单服务压测">

  <load_profile mode="api">
    <!-- 并发与时长 -->
    <concurrency>50</concurrency>
    <duration_seconds>300</duration_seconds>
    <ramp_up_seconds>60</ramp_up_seconds>

    <!-- 模拟用户思考时间 -->
    <think_time_ms min="200" max="1000"/>

    <!-- 可选：限制最大 RPS（0 = 不限）。当前版本未实现，写了也不会限速 -->
    <max_rps>200</max_rps>

    <!-- 可选：指定目标地址（不写则从 GlobalValue.DefaultValue.URL 取） -->
    <host>http://api.staging.example.com</host>
  </load_profile>

  <case id="user_login"     file="user_api.xml"  execute="是" weight="1"/>
  <case id="order_query"    file="order_api.xml" execute="是" weight="5"/>
  <case id="order_create"   file="order_api.xml" execute="是" weight="2"/>
  <case id="order_cancel"   file="order_api.xml" execute="否"/>  <!-- 暂不压测 -->

</test_plan>
```

---

## 5. 压测用例编写

### 5.1 用例约束

压测计划（`mode="api"`）**只能引用 `component_type="接口"` 的 case**。引用 `component_type` 为其他值的 case 时，压测开始前报 `LoadModeUnsupportedCaseError`（SKI602）。没写 `component_type` 的 case 不会被这一步拦下，压测中执行到 UI 步骤（如 `navigate`、`type`）时报 `LoadModeUnsupportedError`（SKI601）。

```xml
<!-- ✅ 正确：接口类用例 -->
<case execute="是" id="login_api" title="登录接口" component_type="接口">
  <test_case>
    <test_step action="send"   model="LoginAPI" data="D001"/>
    <test_step action="verify" model="LoginAPI" data="V001"/>
  </test_case>
</case>

<!-- ❌ 错误：UI 用例不能用于 mode=api 的压测计划 -->
<case execute="是" id="login_ui" title="登录页面" component_type="界面">
  <test_case>
    <test_step action="navigate" model="" data="http://..."/>
    <test_step action="type"     model="LoginPage" data="L001"/>
  </test_case>
</case>
```

压测模式下的执行行为（当前实现）：
- **执行** `pre_process` + `test_case` 步骤
- **跳过** `post_process`（避免关闭连接等操作影响指标）
- **跳过** `verify` / `check` / `assert` / `get` 步骤：不做字段比对，`verify` 不会把请求记为失败
- 失败请求只来自 HTTP 层：请求异常，或响应为 4xx / 5xx（Locust 默认规则）
- 数据字段里的 `${...}` 占位符不解析（见 3.2）

该行为可能调整。

### 5.2 接口模型（model.xml）

压测复用功能测试的 model.xml，无需修改：

```xml
<model name="LoginAPI" type="interface">
  <element name="_method" type="http_method">
    <location type="static">POST</location>
  </element>
  <element name="_url" type="http_url">
    <location type="static">http://api.example.com/api/login</location>
  </element>
  <element name="username" type="field">
    <location type="field">username</location>
  </element>
  <element name="password" type="field">
    <location type="field">password</location>
  </element>
</model>
```

**URL 建议**：压测时通常需要指向不同环境（staging vs prod）。在 `load_profile` 的 `<host>`（或 `GlobalValue.DefaultValue.URL`）中指定 base host，model 的 `_url` 只写路径 `/api/login`。

当前压测运行时不解析 `${GlobalValue.DefaultValue.URL}` 这类引用（见 3.2），不要在 model URL 里用变量拼接。

### 5.3 测试数据（data.sqlite）

压测复用功能测试的 `data.sqlite`，数据结构不变。

压测用**固定 DataID**：每次迭代都使用同一条数据行（如 `D001`）。适合大多数压测场景（用固定账号/参数反复打压）。

**注意**：当前压测运行时不解析字段值中的 `${random(...)}` 等占位符，会把 `ORD_${random(digits, 8)}` 原样发送。LoadCompiler 会把它翻译成每次迭代生成新值的代码，但只体现在 `perf/{plan_id}.py` 中，而该产物当前不被 `rodski run` 加载（见 3.2）。有幂等限制的创建类接口，目前只能用 Locust 直接运行编译产物（8.4），或在被测服务侧放开唯一性约束。

### 5.4 全局变量（globalvalue.xml）

```xml
<?xml version="1.0" encoding="UTF-8"?>
<globalvalue>
  <group name="DefaultValue">
    <!-- 压测目标地址（可被 load_profile 的 host 节点覆盖）-->
    <var name="URL"      value="http://api.staging.example.com"/>
    <var name="WaitTime" value="0"/>  <!-- 单位毫秒（v11.6.0 起） -->
  </group>
</globalvalue>
```

`GlobalValue.DefaultValue.URL` 是 `load_profile.host` 的默认回退值：若 plan 里没有写 `<host>`，则使用此值。

---

## 6. 目录结构

v8.0 在原有的 6 个固定目录之外，新增了 `perf/` 目录：

```
{测试模块}/
├── case/            ← 用例 XML（component_type="接口" 的才能压测）
├── model/
│   └── model.xml    ← 接口模型（复用，无需修改）
├── data/
│   ├── data.sqlite  ← 测试数据（复用，无需修改）
│   └── globalvalue.xml
├── plan/
│   ├── suite_full.xml         ← kind="suite"，功能测试
│   └── api_load_basic.xml     ← kind="load"，性能压测  ← 新增
├── perf/                      ← v8.0 新增：预编译产物目录
│   ├── api_load_basic.py      ← LoadCompiler 生成的 locustfile
│   └── api_load_basic.py.meta ← 哈希元数据
├── fun/
└── result/          ← 框架自动生成（含 result_*.xml，以及本次 perf/{plan_id}.py 的归档 {plan_id}_{ts}.py）
```

**`perf/` 目录规则**：
- 由 `LoadCompiler` 自动生成，首次压测时创建
- 应纳入版本管理（`git add perf/`），代表当前调优状态
- 不要手动编辑，除非有意优化（改后需将 `.meta` 中的 `source` 改为 `"manual"`）
- `.gitignore` 中默认不排除 `perf/`（区别于 `result/`）

---

## 7. 执行命令

### 7.1 基础执行

```bash
# 进入测试模块目录
cd product/MyProject/order_module

# 执行压测计划
rodski run @api_load_basic
```

执行流程：
1. 检测 `plan/api_load_basic.xml` 的 `kind="load"`
2. 构建 `SharedLoadContext`（加载 case/model/data，只读，一次性）
3. `LoadCompiler.compile_if_needed()`：哈希未变则跳过，否则重新生成 `perf/api_load_basic.py`（产物当前不参与执行，见 3.2）
4. `LocustLoadEngine.run()`：Locust LocalRunner 启动 N 个 VU，每个 VU 经 KeywordEngine 执行 case 步骤
5. 持续 duration 秒后停止，写入 `result/result_*.xml`
6. 终端打印结果摘要

### 7.2 实时监控（--load-ui）

```bash
# 启动压测 + 开启 Locust Web UI（默认 8089 端口）
rodski run @api_load_basic --load-ui

# 指定端口
rodski run @api_load_basic --load-ui --load-ui-port 9090
```

启动后终端输出：

```
  🖥  Locust 监控界面已启动: http://127.0.0.1:8089
      可用端点:
        http://127.0.0.1:8089/           实时监控仪表盘
        http://127.0.0.1:8089/stats/requests  指标 JSON
        http://127.0.0.1:8089/stats/report    实时 HTML 报告
        http://127.0.0.1:8089/stats/requests/csv  CSV 导出
      压测结束后 Web UI 将自动关闭。
```

> 详见第 9 节。

### 7.3 调试模式（--no-compile）

```bash
# 跳过预编译（不生成 / 更新 perf/ 产物）
rodski run @api_load_basic --no-compile
```

当前版本中，加不加 `--no-compile` 压测的执行路径相同（都经 KeywordEngine 执行，见 3.2），区别只是是否生成 `perf/` 产物。

### 7.4 dry-run 预览

```bash
# 不发送任何请求，仅预览计划选中的 case
rodski run @api_load_basic --dry-run
```

dry-run 不显示编译产物路径，也不生成产物。

---

## 8. 预编译产物（perf/）

### 8.1 产物是什么

`LoadCompiler` 将 RodSki XML 用例翻译为标准 Locust `locustfile.py`，存放在 `perf/` 目录。当前版本 `rodski run` 不加载该产物（见 3.2），它用于脱离 RodSki 独立运行（8.4）和追溯；每次压测结束会复制一份到 `result/{plan_id}_{ts}.py`。

产物示例（`perf/api_load_basic.py`）：

```python
# ============================================================
# RodSki LoadCompiler — plan_id: api_load_basic
# Generated: 2026-06-07 07:24:17 UTC
# 脱离 RodSki 运行: locust -f api_load_basic.py --host http://... -u 10 -t 60s
# ============================================================
from locust import FastHttpUser, task, between

# 编译期内联常量（消除热路径 DataResolver 解析开销）
_TC_LOAD_001_STEP0_METHOD = 'POST'
_TC_LOAD_001_STEP0_URL    = 'http://api.example.com/api/login'

class CompiledRodskiUser(FastHttpUser):
    host      = 'http://api.example.com'
    wait_time = between(0.1, 0.5)

    @task(2)   # weight=2，约占 2/3 请求量
    def task_TC_LOAD_001(self):
        self._returns = []
        _resp = self.client.request(
            _TC_LOAD_001_STEP0_METHOD,
            _TC_LOAD_001_STEP0_URL,
            json={'username': 'admin', 'password': '123456'},
            headers={}
        )
        self._returns.append({'status_code': _resp.status_code})
```

**字段编译策略**（只体现在产物中）：

| 数据字段类型 | 编译结果 | 运行时开销 |
|------------|---------|-----------|
| 字面量（`admin`、`123456`）| 内联为常量 | **零** |
| `${GlobalValue.DefaultValue.URL}` | 编译期展开 | **零** |
| `${random(int, 6)}` | `lambda: random.randint(...)` | 极低 |
| `${date(today)}` | `lambda: datetime.date.today().isoformat()` | 极低 |
| `${Return[-1].token}` | `self._returns[-1].get('token')` | 极低 |

### 8.2 缓存与失效

`perf/{plan_id}.py.meta` 记录联合哈希，**以下任一变化会触发重新编译**：
- `plan/*.xml` 修改
- `case/*.xml` 修改
- `model/model.xml` 修改
- `data/data.sqlite` 修改（mtime 变化）

```json
{
  "plan_hash": "<sha256 十六进制摘要>",
  "compiled_at": "2026-06-07T14:25:00",
  "source": "auto"
}
```

### 8.3 手动优化（source: manual）

如果需要在自动生成的基础上手动调优（如添加连接池复用、token 预热逻辑），可直接编辑 `perf/{plan_id}.py`，然后将 `.meta` 中的 `source` 改为 `"manual"`：

```json
{
  "plan_hash": "<sha256 十六进制摘要>",
  "compiled_at": "2026-06-07T14:25:00",
  "source": "manual"
}
```

标记后，`LoadCompiler` 不再自动覆盖，每次运行发出一条 Python `UserWarning`：

```
[LoadCompiler] api_load_basic.py source=manual，跳过自动覆盖。
```

如需重新生成，删除 `.meta` 文件（或把 `source` 改回 `"auto"`）。注意手动修改的产物同样不会被 `rodski run` 加载，只在用 Locust 直接运行时生效。

### 8.4 脱离 RodSki 独立运行

编译产物是标准 Locust locustfile，可直接用 Locust CLI 运行（适合 CI/CD 环境中不安装完整 RodSki）：

```bash
# 安装最小依赖
pip install locust

# 运行压测（不需要 rodski）
locust -f perf/api_load_basic.py \
  --host http://api.example.com \
  --headless \
  --users 50 \
  --spawn-rate 10 \
  --run-time 120s
```

---

## 9. Locust Web UI 实时监控

### 9.1 启动方式

```bash
rodski run @api_load_basic --load-ui

# 指定端口（默认 8089）
rodski run @api_load_basic --load-ui --load-ui-port 9090
```

Web UI 在压测期间持续运行，压测结束后自动关闭。

### 9.2 可用端点

| 端点 | 说明 |
|------|------|
| `http://localhost:8089/` | **实时仪表盘**（RPS 折线图、响应时间分布、并发用户曲线、失败数）|
| `http://localhost:8089/stats/requests` | **指标 JSON**，可被外部监控系统（Prometheus、Grafana）消费 |
| `http://localhost:8089/stats/report` | **实时 HTML 报告**（完整统计，含图表，可另存为文件）|
| `http://localhost:8089/stats/requests/csv` | 请求统计 CSV（各接口 P50/P95/P99/avg/min/max）|
| `http://localhost:8089/stats/failures/csv` | 失败请求明细 CSV |
| `http://localhost:8089/exceptions` | 异常信息列表 |
| `http://localhost:8089/logs` | 实时日志流 |

### 9.3 指标说明

`/stats/requests` JSON 中的关键字段：

```json
{
  "stats": [
    {
      "name": "POST /api/login",
      "num_requests": 1234,
      "num_failures": 2,
      "median_response_time": 45,
      "avg_response_time": 52.3,
      "min_response_time": 8,
      "max_response_time": 892,
      "response_time_percentile_50": 45,
      "response_time_percentile_95": 180,
      "response_time_percentile_99": 450,
      "current_rps": 20.5,
      "current_fail_per_sec": 0.0
    }
  ],
  "total_rps": 20.5,
  "num_failures": 2,
  "fail_ratio": 0.0016
}
```

| 字段 | 含义 |
|------|------|
| `num_requests` | 总请求数 |
| `num_failures` | 失败请求数（HTTP 层失败；verify 在压测中不执行，不计入）|
| `current_rps` | 当前实时 RPS |
| `response_time_percentile_95` | P95 延迟（毫秒）|
| `fail_ratio` | 失败率（0~1）|

---

## 10. 压测结果（result.xml）

压测执行完成后，在 `result/` 目录生成 `result_{timestamp}.xml`。

```xml
<?xml version='1.0' encoding='utf-8'?>
<testresult>
  <!-- 用例级汇总 -->
  <summary total="2" passed="2" failed="0" pass_rate="100.0%"
           total_time="30s" start_time="20260607_152447"/>

  <!-- 各 case 执行状态 -->
  <results>
    <result case_id="TC-LOAD-001" status="PASS"
            load_requests="299" load_failures="0" load_p95_ms="2"/>
    <result case_id="TC-LOAD-002" status="PASS"
            load_requests="146" load_failures="0" load_p95_ms="3"/>
  </results>

  <!-- 压测汇总指标（kind=load 时才有此节点）-->
  <load_summary
    total_requests="445"
    total_failures="0"
    error_rate_pct="0.0"
    rps_avg="15.03"
    rps_peak="0.0"
    duration_seconds="30"
    concurrency="5">
    <latency p50_ms="2" p75_ms="2" p95_ms="3" p99_ms="4"
             avg_ms="1.7" max_ms="4"/>
    <endpoints>
      <endpoint name="POST /api/login"  requests="299" failures="0"
                rps_avg="10.1" p95_ms="2"/>
      <endpoint name="GET /api/orders"  requests="146" failures="0"
                rps_avg="4.93" p95_ms="3"/>
    </endpoints>
  </load_summary>
</testresult>
```

**result 节点新增属性（压测模式）**：

| 属性 | 说明 |
|------|------|
| `load_requests` | 该 case 的总请求次数 |
| `load_failures` | 该 case 的失败请求数 |
| `load_p95_ms` | 该 case 的 P95 延迟 |

**退出码**：
- `0`：`error_rate_pct ≤ 5.0%`，压测通过
- `1`：`error_rate_pct > 5.0%`，压测不通过

适合 CI/CD 集成：`rodski run @api_load_basic && echo "性能达标" || echo "性能未达标"`

---

## 11. 核心约束与注意事项

### 约束

1. **压测 plan.xml 必须存在**：不支持 `rodski run --load --concurrency 50 case/` 这类临时压测，所有负载参数必须写在 plan XML 里。

2. **mode=api 只能压接口 case**：`component_type` 不是 `"接口"` 的 case 会在压测开始前报 `SKI602` 错误；未写 `component_type` 的 case 执行到 UI 步骤时报 `SKI601`。

3. **不引入新关键字**：压测模式复用 `send`，不新增 `load_send` 等关键字（`verify` 等步骤在压测中跳过，见 5.1）。

4. **perf/ 目录应纳入版本管理**：与 `result/`（`.gitignore` 排除）不同，`perf/` 的产物是可追溯的工件，建议 `git add perf/`。

5. **`@plan_id` 与 selector 互斥约束同样适用**：`rodski run @api_load_basic --tag smoke` 不允许，同功能测试。

6. **只支持 mode="api"**：写 `mode="browser"` 报 `SKI605` 并以退出码 1 结束。

7. **`max_rps` 未实现**：XSD 接受该节点，运行时不读取。

### 注意事项

- **并发数建议**：单机压测建议从 10~50 VU 起步，观察系统 CPU/内存后再调大。`gevent` 协程模型理论上支持 1000+ VU/核，但实际受目标服务响应速度影响。

- **think_time 的作用**：不设 think_time 会让每个 VU 尽可能快地发请求，得到的是极限 RPS；设置合理的 think_time（如 500ms~2s）能模拟真实用户行为，得到更接近生产的负载分布。

- **爬坡与稳态**：`ramp_up_seconds` 控制 VU 从 0 到目标数量的爬坡时间。压测结果的统计区间包含整个 duration，如需排除爬坡阶段的干扰，可适当加长 duration（如 ramp_up=60s，duration=180s）。

- **gevent 与 asyncio 不兼容**：Locust 基于 gevent，`LocustLoadEngine` 启动时会执行 `gevent.monkey.patch_all()`。若你的 RodSki 模块中有 asyncio 代码，需隔离运行（各自独立进程）。

---

## 12. 常见问题

**Q：执行压测提示需要安装 locust？**

通过 `rodski run @plan` 执行时，CLI 先检查 locust，缺失时输出下面的提示并以退出码 1 结束：

```
错误: 压测模式需要 locust，请先安装：
  pip install locust
```

运行 `pip install rodski[load]`（或 `pip install locust`）安装依赖。直接在 Python 中调用 `LocustLoadEngine` 时，缺失 locust 报 `LoadDependencyMissingError`（SKI603）。

---

**Q：计划里引用的 case 找不到？**

检查 `plan.xml` 中 `<case id="...">` 的 id 是否与 `case/*.xml` 中 `<case id="...">` 完全一致（区分大小写）。

---

**Q：压测运行但 `total_requests` 很少，RPS 极低？**

可能原因：
1. `think_time_ms` 设置过大，VU 大部分时间在等待
2. 目标服务响应太慢，VU 被阻塞
3. `concurrency` 太小，适当增大

---

**Q：`--load-ui` 启动后浏览器打不开仪表盘？**

默认监听 `127.0.0.1:8089`，只能本机访问。如果在远程服务器上运行，需要 SSH 端口转发：

```bash
ssh -L 8089:127.0.0.1:8089 user@server
```

---

**Q：如何在 CI/CD 中集成压测？**

```yaml
# .gitlab-ci.yml 示例
load_test:
  script:
    - pip install rodski[load]
    - rodski run @api_load_basic
  after_script:
    - cat result/result_*.xml | grep error_rate_pct
  allow_failure: false
```

压测失败（`error_rate > 5%`）时退出码为 1，CI job 自动标记失败。

---

**Q：预编译产物是否需要每次重新生成？**

不需要。只有 plan/case/model/data 有变化时才重新编译（哈希校验），未变化时跳过生成。当前版本运行时不加载产物（见 3.2），所以产物是否最新不影响 `rodski run` 的压测结果。

---

**Q：想在压测脚本里加自定义逻辑（如 token 预热）怎么办？**

当前 `rodski run` 压测不解析数据字段中的 `${Return[-1].token}`（见 3.2），因此"在 `pre_process` 中 `send` 取 token、后续步骤引用"的写法在压测中暂不可用。

可行做法：手动编辑 `perf/{plan_id}.py`（把 `.meta` 中 `source` 改为 `"manual"` 防止被覆盖），在 `CompiledRodskiUser.on_start()` 中加预热逻辑，然后用 Locust 直接运行该产物（8.4）。`rodski run` 不加载该产物。

```python
def on_start(self):
    self._returns = []
    # 预热：获取 token
    resp = self.client.post('/api/auth/token',
                            json={'client_id': 'test', 'secret': 'xxx'})
    self._token = resp.json().get('access_token', '')
```

---

## 13. 附录：压测相关错误码

| 错误码 | 异常类 | 触发条件 | 处理方式 |
|--------|--------|---------|---------|
| SKI601 | `LoadModeUnsupportedError` | 压测执行中，步骤调用了 UI 操作（`navigate`、`type`、`launch` 等）。常见于没写 `component_type` 的 UI case 绕过了 SKI602 的检查 | 给 case 标明 `component_type`，压测计划只引用 `component_type="接口"` 的 case |
| SKI602 | `LoadModeUnsupportedCaseError` | `mode=api` 计划引用了 `component_type` 不是"接口"的 case（压测开始前检查） | 修改 plan，只引用接口 case |
| SKI603 | `LoadDependencyMissingError` | `LocustLoadEngine` 运行时 locust 未安装。通过 `rodski run` 执行时 CLI 会先检查并输出安装提示（不带该错误码），见第 12 节 | `pip install rodski[load]` |
| SKI604 | `LoadBrowserModeUnsupportedCaseError` | 为 `mode=browser` 预留（browser 计划引用非界面 case）。当前版本不会触发：`mode="browser"` 先报 SKI605 | — |
| SKI605 | `LoadBrowserModeNotSupportedError` | 计划声明了 `mode="browser"`（当前版本未实现）。CLI 输出 `错误: 压测执行失败: [SKI605] ...`，退出码 1 | 改为 `mode="api"`，只引用接口 case |

通过 `rodski run` 执行时，SKI602 / SKI605（以及 CLI 先行检查出的 locust 缺失）使命令以退出码 1 结束。SKI601 发生在 VU 执行任务的过程中，由 Locust 记为任务异常（可在 Web UI 的 `/exceptions` 查看），该次迭代的剩余步骤不再执行，压测继续，退出码仍按错误率判定。

---

*文档版本: v11.10.0 | 最后更新: 2026-10-22*
