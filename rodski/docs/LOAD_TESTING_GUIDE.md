# RodSki 性能压测指南

**版本**: v8.0  
**日期**: 2026-06-07  
**适用框架**: RodSki v8.0+

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
   - 4.3 cases 与 weight
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
      ▼ LoadCompiler（首次编译，结果持久化到 perf/）
      │
perf/{plan_id}.py  ←  标准 Locust locustfile，可独立运行
      │
      ▼ LocustLoadEngine（Locust FastHttpUser + LocalRunner）
      │
      ▼ 并发执行（gevent greenlet，支持 1000+ VU/核）
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
  <cases>
    <case id="your_case_id" execute="是" weight="1"/>
  </cases>
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
| 断言失败行为 | case FAIL，停止 | 记为错误请求，继续执行 |
| 截图 | 失败时自动截图 | 不截图（避免影响性能指标）|
| post_process | 执行 | 不执行 |
| 结果关注点 | PASS / FAIL | RPS / P95 / 错误率 |

**互不影响**：同一套 case XML 既可 `rodski run @suite_plan` 做功能验收，也可 `rodski run @load_plan` 做性能压测。

### 3.2 两个执行阶段：预编译 vs 运行时解释

**预编译模式**（默认）：

```
启动时 → LoadCompiler 将 case XML 翻译为 locustfile.py
        字面量字段 → Python 常量（消除热路径 DataResolver 解析）
        → 保存到 perf/{plan_id}.py（持久化，纳入版本管理）
运行时 → Locust 直接 import locustfile.py，零解析开销
```

**解释模式**（`--no-compile`，调试用）：

```
运行时 → 每次迭代经过 KeywordEngine → DataResolver → LoadDriver
        → 有解析开销，适合调试
```

在高并发场景，预编译模式可显著降低 CPU 占用，让更多资源用于网络 I/O。

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
  <cases>
    <case id="login_api" execute="是"/>
  </cases>
</test_plan>
```

### 4.2 load_profile 参数详解

| 参数 | 必填 | 类型 | 默认 | 说明 |
|------|------|------|------|------|
| `mode` 属性 | 否 | `api` \| `browser` | `api` | 压测引擎选择。v8.0 只支持 `api`（Locust） |
| `concurrency` | ✅ | 正整数 | — | 并发虚拟用户数（VU）。建议从 10 起步，逐步调大 |
| `duration_seconds` | ✅ | 正整数 | — | 压测持续时长（秒）。建议最少 30s，稳态测试 300s+ |
| `ramp_up_seconds` | 否 | 非负整数 | `0` | 从 0 爬坡到目标 VU 的时长。0 表示立即达到目标并发 |
| `think_time_ms` | 否 | `min="..." max="..."` | 无 | VU 每次迭代之间的等待时间（毫秒范围）。模拟真实用户行为 |
| `max_rps` | 否 | 非负整数 | `0`（不限）| 限制最大 RPS，用于稳定性测试或接口限流验证 |
| `host` | 否 | URI | GlobalValue 的 URL | 覆盖 globalvalue.xml 中的目标地址，适配多环境 |

**think_time 设置建议**：

| 场景 | 建议值 |
|------|--------|
| 极限压测（最大 RPS） | 不设，或 `min="0" max="0"` |
| 模拟真实用户 | `min="500" max="2000"` |
| API 集成测试 | `min="100" max="500"` |

### 4.3 cases 与 weight

`<case>` 节点引用 `case/` 目录下已有的用例：

```xml
<cases>
  <!-- weight 控制各接口的调度比例，相对权重 -->
  <case id="login_api"     execute="是" weight="1"/>
  <case id="query_orders"  execute="是" weight="3"/>
  <case id="create_order"  execute="是" weight="1"/>
</cases>
```

上例中，`query_orders` 的请求量约为总量的 3/5，`login_api` 和 `create_order` 各约 1/5。

**约束**：
- `id` 必须与 `case/*.xml` 中的 `<case id="...">` 完全一致
- `execute="否"` 的 case 不参与压测
- `weight` 默认为 1，只在 `kind="load"` 的计划中有效
- v8.0 不支持 `scenario` 级别选择，只能整 case 粒度

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

    <!-- 可选：限制最大 RPS（0 = 不限） -->
    <max_rps>200</max_rps>

    <!-- 可选：指定目标地址（不写则从 GlobalValue.DefaultValue.URL 取） -->
    <host>http://api.staging.example.com</host>
  </load_profile>

  <cases>
    <case id="user_login"     execute="是" weight="1"/>
    <case id="order_query"    execute="是" weight="5"/>
    <case id="order_create"   execute="是" weight="2"/>
    <case id="order_cancel"   execute="否"/>  <!-- 暂不压测 -->
  </cases>

</test_plan>
```

---

## 5. 压测用例编写

### 5.1 用例约束

压测计划（`mode="api"`）**只能引用 `component_type="接口"` 的 case**。引用 UI case 时，运行时报 `LoadModeUnsupportedCaseError`（SKI602）。

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

压测模式下的执行行为：
- **执行** `pre_process` + `test_case` 步骤
- **跳过** `post_process`（避免关闭连接等操作影响指标）
- **跳过** `verify` 的截图行为（只做字段比对，不截图）
- `verify` 失败不中断用例，但 Locust 会将该次请求标记为失败请求

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

**URL 建议**：压测时通常需要指向不同环境（staging vs prod），有两种方式：
1. 在 `load_profile` 的 `<host>` 中指定 base host，model 里只写路径 `/api/login`
2. model URL 中使用 GlobalValue 变量：`${GlobalValue.DefaultValue.URL}/api/login`

### 5.3 测试数据（data.sqlite）

压测复用功能测试的 `data.sqlite`，数据结构不变。

v8.0 压测用**固定 DataID**：每次迭代都使用同一条数据行（如 `D001`）。适合大多数压测场景（用固定账号/参数反复打压）。

**注意**：如果接口有幂等限制（如创建类接口每次需要不同参数），可以用内置 `${random(...)}` 函数生成动态值：

```
# data.sqlite 中的字段值
order_no = ORD_${random(digits, 8)}
```

这在编译期会被翻译为 `lambda: 'ORD_' + ''.join(random.choices('0123456789', k=8))`，每次迭代生成不同订单号。

### 5.4 全局变量（globalvalue.xml）

```xml
<?xml version="1.0" encoding="UTF-8"?>
<globalvalue>
  <group name="DefaultValue">
    <!-- 压测目标地址（可被 load_profile 的 host 节点覆盖）-->
    <var name="URL"      value="http://api.staging.example.com"/>
    <var name="WaitTime" value="1"/>
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
└── result/          ← 框架自动生成（含 result_*.xml）
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
3. `LoadCompiler.compile_if_needed()`：哈希未变则复用 `perf/api_load_basic.py`
4. `LocustLoadEngine.run()`：Locust LocalRunner 启动 N 个 VU
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
# 跳过预编译，用解释模式执行（适合调试 case 逻辑）
rodski run @api_load_basic --no-compile
```

此模式每次迭代都走完整的 `KeywordEngine → DataResolver` 路径，有额外 CPU 开销，**仅用于调试**，不推荐生产压测使用。

### 7.4 dry-run 预览

```bash
# 不发送任何请求，仅预览选中的 case 和编译产物路径
rodski run @api_load_basic --dry-run
```

---

## 8. 预编译产物（perf/）

### 8.1 产物是什么

`LoadCompiler` 将 RodSki XML 用例翻译为标准 Locust `locustfile.py`，存放在 `perf/` 目录。

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

**字段编译策略**：

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
  "plan_hash": "sha256:abc123...",
  "compiled_at": "2026-06-07T14:25:00",
  "source": "auto"
}
```

### 8.3 手动优化（source: manual）

如果需要在自动生成的基础上手动调优（如添加连接池复用、token 预热逻辑），可直接编辑 `perf/{plan_id}.py`，然后将 `.meta` 中的 `source` 改为 `"manual"`：

```json
{
  "plan_hash": "sha256:abc123...",
  "compiled_at": "2026-06-07T14:25:00",
  "source": "manual"
}
```

标记后，`LoadCompiler` 不再自动覆盖，每次运行会打印：

```
[LoadCompiler] perf/api_load_basic.py 已被手动修改（source=manual），
跳过自动重编译。如需重编译，请删除 .meta 文件。
```

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
| `num_failures` | 失败请求数（含 verify 断言失败）|
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

2. **mode=api 只能压接口 case**：`component_type` 不是 `"接口"` 的 case 会在运行时报 `SKI602` 错误。

3. **不引入新关键字**：压测模式完全复用 `send`/`verify`，语义不变，不新增 `load_send` 等关键字。

4. **perf/ 目录应纳入版本管理**：与 `result/`（`.gitignore` 排除）不同，`perf/` 的产物是可追溯的工件，建议 `git add perf/`。

5. **`@plan_id` 与 selector 互斥约束同样适用**：`rodski run @api_load_basic --tag smoke` 不允许，同功能测试。

### 注意事项

- **并发数建议**：单机压测建议从 10~50 VU 起步，观察系统 CPU/内存后再调大。`gevent` 协程模型理论上支持 1000+ VU/核，但实际受目标服务响应速度影响。

- **think_time 的作用**：不设 think_time 会让每个 VU 尽可能快地发请求，得到的是极限 RPS；设置合理的 think_time（如 500ms~2s）能模拟真实用户行为，得到更接近生产的负载分布。

- **爬坡与稳态**：`ramp_up_seconds` 控制 VU 从 0 到目标数量的爬坡时间。压测结果的统计区间包含整个 duration，如需排除爬坡阶段的干扰，可适当加长 duration（如 ramp_up=60s，duration=180s）。

- **gevent 与 asyncio 不兼容**：Locust 基于 gevent，`LocustLoadEngine` 启动时会执行 `gevent.monkey.patch_all()`。若你的 RodSki 模块中有 asyncio 代码，需隔离运行（各自独立进程）。

---

## 12. 常见问题

**Q：执行压测报错 `LoadDependencyMissingError`？**

```
错误: 压测功能需要安装 locust：
  pip install rodski[load]
```

运行 `pip install rodski[load]` 安装 Locust 依赖。

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

不需要。只有 plan/case/model/data 有变化时才重新编译（哈希校验）。未变化时直接 import 已有产物，压测启动耗时 < 1s。

---

**Q：想在压测脚本里加自定义逻辑（如 token 预热）怎么办？**

方式一（推荐）：在 `case/` 中的 `pre_process` 阶段加 `send` 步骤获取 token，通过 `${Return[-1].token}` 传递。

方式二：手动编辑 `perf/{plan_id}.py`（把 `.meta` 中 `source` 改为 `"manual"` 防止被覆盖），在 `CompiledRodskiUser.on_start()` 中加预热逻辑：

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
| SKI601 | `LoadModeUnsupportedError` | 在压测驱动上调用了 UI 操作 | 检查 case 是否为 `component_type="接口"` |
| SKI602 | `LoadModeUnsupportedCaseError` | `mode=api` 计划引用了 UI case | 修改 plan，只引用接口 case |
| SKI603 | `LoadDependencyMissingError` | locust 未安装 | `pip install rodski[load]` |
| SKI604 | `LoadBrowserModeUnsupportedCaseError` | `mode=browser` 计划引用了接口 case | 修改 plan 或换 `mode=api` |

---

*文档版本: v8.0 | 最后更新: 2026-06-07*
