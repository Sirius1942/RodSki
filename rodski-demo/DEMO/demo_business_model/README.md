# demo_business_model：登录业务流与本地 Mock API

本目录演示 RodSki 的业务模型（Business Model）如何通过 `business_call` 嵌套到测试用例中执行。示例使用一个登录业务流：同一张业务流程图根据 Mock API 的真实返回值进入成功、凭据错误或账号锁定路径；Case 通过选择 `flow` 和数据行来测试指定路径。

## 当前实现与执行边界

- `business/business.xml` 定义业务模型 `login_flow`、节点、条件边和三个合法流程：
  - `F_LOGIN_SUCCESS`：登录成功；
  - `F_LOGIN_INVALID`：凭据错误；
  - `F_LOGIN_LOCKED`：账号锁定。
- `business_call` 必须嵌套在 Case 中执行，不能把业务模型自动当成独立正式测试计划。Case 通过 `ref` 引用业务模型，通过 `flow` 声明要验证的目标路径，并通过 `input`、`expect` 指定 SQLite Data/Verify 行。
- `flow` 是测试目标和路径断言，不会强制条件边改道。实际路径由业务输入和 `LoginAPI` 返回的 `login_status` 决定；如果实际路径与目标路径不一致，业务调用失败。
- 业务模型的输入、期望输出使用普通 RodSki SQLite Data/Verify 表，不在业务 XML 中重复定义 `username`、`password` 等字段。对应关系见 [`data/README.md`](data/README.md)。
- 当前正式 Case 使用接口模型 `LoginAPI`，不需要浏览器页面交互；命令仍使用 `--headless`，便于以 CLI 方式运行。

## 目录与文件

- `server.py`：本地 HTTP Mock API；提供 `/api/login` 和 `/health`。
- `business/business.xml`：`login_flow` 业务流程图、条件边和合法 flow。
- `case/login_flows.xml`：三条正式业务模型 Case。
- `case/expected_path_mismatch.xml`：刻意失败的路径断言样例。
- `model/model.xml`：`LoginAPI` 请求定义，POST 到 `http://localhost:8000/api/login`，并自动捕获 `data.login_status`、`message`。
- `data/data.sqlite`：普通 RodSki SQLite 数据库，包含 `login_flow` Data 表和 `login_flow_verify` Verify 表。
- `data/init_data.py`：按 RodSki 公共 SQLite schema 重建示例数据库。
- `data/README.md`：数据表、字段、DataID 和 Case 映射说明。

## 三条正式 Case

`case/login_flows.xml` 中的三个 Case 都设置为 `execute="是"`：

| Case | `business_call` | flow | 输入 DataID | 期望 Verify DataID | 预期结果 |
|---|---|---|---|---|---|
| `TC-BM-LOGIN-OK` | `login_success` | `F_LOGIN_SUCCESS` | `LOGIN_OK_01` | `LOGIN_OK_01` | PASS |
| `TC-BM-LOGIN-INVALID` | `login_invalid` | `F_LOGIN_INVALID` | `LOGIN_INVALID_01` | `LOGIN_INVALID_01` | PASS |
| `TC-BM-LOGIN-LOCKED` | `login_locked` | `F_LOGIN_LOCKED` | `LOGIN_LOCKED_01` | `LOGIN_LOCKED_01` | PASS |

例如，Case 中的引用关系如下：

```xml
<business_call id="login_success"
               ref="login_flow"
               flow="F_LOGIN_SUCCESS"
               input="LOGIN_OK_01"
               expect="LOGIN_OK_01" />
```

这里的 `input` 和 `expect` 是数据行 ID，不是业务字段名；字段值由 SQLite Data/Verify 表提供。

## 静态校验、流程图与覆盖率

这些命令只读取业务定义或已有结果，不执行被测系统；正式执行仍必须通过 Case 的 `business_call`。

```bash
# 列出模型和业务流
./.venv/bin/python -m rodski.rodski_cli business list rodski-demo/DEMO/demo_business_model
./.venv/bin/python -m rodski.rodski_cli business flow-list rodski-demo/DEMO/demo_business_model --id login_flow

# 校验 Schema、入口、DAG、不可达节点、终点、flow 类型和路径
./.venv/bin/python -m rodski.rodski_cli business validate rodski-demo/DEMO/demo_business_model

# 输出完整图或单条业务流投影
./.venv/bin/python -m rodski.rodski_cli business graph rodski-demo/DEMO/demo_business_model --id login_flow --format mermaid
./.venv/bin/python -m rodski.rodski_cli business graph rodski-demo/DEMO/demo_business_model --id login_flow --format json

# 从最近一次 result.xml 汇总节点、边和业务流覆盖
./.venv/bin/python -m rodski.rodski_cli business coverage rodski-demo/DEMO/demo_business_model --id login_flow
```

## 真实运行正式 Case

以下命令均从仓库根目录执行。先在终端一启动 Mock API：

```bash
python3 rodski-demo/DEMO/demo_business_model/server.py
```

服务默认监听 `http://127.0.0.1:8000`。保持该终端运行，再在终端二执行三条正式 Case：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 rodski/ski_run.py \
  rodski-demo/DEMO/demo_business_model/case/login_flows.xml \
  --headless
```

预期结果为：

```text
TC-BM-LOGIN-OK       PASS
TC-BM-LOGIN-INVALID  PASS
TC-BM-LOGIN-LOCKED   PASS
```

运行结果会写入本次执行的 `result/result.xml`（具体运行目录以 RodSki 输出为准）。业务调用结果中应包含实际路径、期望路径、实际/期望字段值以及节点执行信息。

也可以使用统一验收脚本。脚本会先执行静态校验和图输出，再执行三条正式 Case，核对节点/边/flow 均达到 100% 覆盖，最后单独执行预期失败的路径错配样例；如果 8000 端口的 Mock API 尚未启动，脚本只会启动并回收自己创建的进程：

```bash
./.venv/bin/python rodski-demo/DEMO/demo_business_model/acceptance.py
```

## 负向路径断言样例

`case/expected_path_mismatch.xml` 使用无效密码输入 `LOGIN_INVALID_01`，但声明 `F_LOGIN_SUCCESS` 并期望 `LOGIN_OK_01`。它用于验证“测试用例选择路径，业务条件决定实际路径”的约束，预期必须失败：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 rodski/ski_run.py \
  rodski-demo/DEMO/demo_business_model/case/expected_path_mismatch.xml \
  --headless
```

失败原因应能看出实际路径是：

```text
open_login>submit_login>validate_login>error
```

而不是成功路径：

```text
open_login>submit_login>validate_login>home
```

不要把该负向样例的失败当成框架故障；它是用于验证路径断言的预期失败。

## Mock API 返回状态

Mock API 根据请求体中的 `username`、`password` 返回三种业务状态：

| 输入 | HTTP 状态 | JSON `data.login_status` | `message` |
|---|---:|---|---|
| `admin / 123456` | 200 | `success` | 登录成功 |
| `admin / wrong-password` | 401 | `invalid_credentials` | 用户名或密码错误 |
| `locked / 任意密码` | 423 | `locked` | 账号已锁定 |

可用健康检查确认服务已启动：

```bash
curl -i http://127.0.0.1:8000/health
```

也可以直接调用接口验证三种返回状态：

```bash
curl -i -X POST http://127.0.0.1:8000/api/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"123456"}'

curl -i -X POST http://127.0.0.1:8000/api/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"wrong-password"}'

curl -i -X POST http://127.0.0.1:8000/api/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"locked","password":"any-password"}'
```

## 重建 SQLite 数据

仓库已提供可直接运行的 `data/data.sqlite`。只有需要重建数据时，才从仓库根目录执行：

```bash
python3 rodski-demo/DEMO/demo_business_model/data/init_data.py
```

该脚本会删除并重建本目录的 `data/data.sqlite`，写入普通 `login_flow` Data 表、`login_flow_verify` Verify 表，以及三组同名 DataID。重建前如需保留现有数据库内容，请先备份。
