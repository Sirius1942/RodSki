# demo_business_model 数据说明

本目录使用 RodSki 当前普通 SQLite Data/Verify 数据结构，不增加业务模型专用元表，也不在业务 XML 中重复定义业务字段。业务模型 `id="login_flow"` 通过约定直接对应两张普通逻辑表：

- `login_flow`：`table_kind='data'`，业务输入数据表；
- `login_flow_verify`：`table_kind='verify'`，业务期望数据表。

两张表均通过 RodSki 公共的 `rs_datatable`、`rs_datatable_field`、`rs_row`、`rs_field` 元表保存，字段 schema 由 SQLite 中的 `rs_datatable_field` 维护。业务模型不定义 `username`、`password` 等字段；这些字段只存在于 Data 表的 schema 和数据行中。

## 表与字段

| 逻辑表 | `table_kind` | 字段 | 用途 |
|---|---|---|---|
| `login_flow` | `data` | `username`、`password` | 提供 `LoginAPI` 请求输入 |
| `login_flow_verify` | `verify` | `login_status`、`message`、`expected_path` | 校验接口返回值和实际业务路径 |

当前 Data 表只有 `username`、`password`，不包含 `url` 或其他浏览器字段。接口地址属于 `model/model.xml` 中 `LoginAPI` 的静态模型配置，不属于业务模型输入数据。

## DataID 与 VerifyID

`business_call` 的 `input` 和 `expect` 使用数据行 ID，并通过同一个 ID 将输入行与期望行配对：

```xml
<business_call id="login_success"
               ref="login_flow"
               flow="F_LOGIN_SUCCESS"
               input="LOGIN_OK_01"
               expect="LOGIN_OK_01" />
```

对应关系如下：

| DataID / VerifyID | `login_flow` 输入 | 期望 `login_status` | 期望 `message` | 期望 `expected_path` |
|---|---|---|---|---|
| `LOGIN_OK_01` | `admin` / `123456` | `success` | 登录成功 | `open_login>submit_login>validate_login>home` |
| `LOGIN_INVALID_01` | `admin` / `wrong-password` | `invalid_credentials` | 用户名或密码错误 | `open_login>submit_login>validate_login>error` |
| `LOGIN_LOCKED_01` | `locked` / `any-password` | `locked` | 账号已锁定 | `open_login>submit_login>validate_login>locked` |

`expected_path` 是 Verify 表中的普通字段，不是业务模型执行控制参数。业务条件仍然读取 Mock API 的真实 `login_status`：

- `success` 进入 `home`；
- `invalid_credentials` 进入 `error`；
- `locked` 进入 `locked`。

Case 中的 `flow` 用于选择/声明要验证的合法业务路径；如果输入数据产生的实际路径与 `flow` 或 `expected_path` 不一致，业务调用失败，不会被 `flow` 强制改道。

## 运行时数据来源

三条输入行由 `server.py` 提供的 Mock API 验证：

```bash
# 终端一：从仓库根目录启动 Mock API
python3 rodski-demo/DEMO/demo_business_model/server.py

# 终端二：执行三条正式业务模型 Case
PYTHONDONTWRITEBYTECODE=1 python3 rodski/ski_run.py \
  rodski-demo/DEMO/demo_business_model/case/login_flows.xml \
  --headless
```

三条正式 Case 预期全部通过：

- `TC-BM-LOGIN-OK`：`LOGIN_OK_01` → `F_LOGIN_SUCCESS`；
- `TC-BM-LOGIN-INVALID`：`LOGIN_INVALID_01` → `F_LOGIN_INVALID`；
- `TC-BM-LOGIN-LOCKED`：`LOGIN_LOCKED_01` → `F_LOGIN_LOCKED`。

## 负向路径断言

负向样例使用无效密码输入，却声明成功路径：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 rodski/ski_run.py \
  rodski-demo/DEMO/demo_business_model/case/expected_path_mismatch.xml \
  --headless
```

该命令预期失败。实际路径应为：

```text
open_login>submit_login>validate_login>error
```

而样例声明的目标路径为：

```text
open_login>submit_login>validate_login>home
```

这个失败用于证明业务流程中的条件判断由实际业务数据决定，Case 只能选择并断言目标路径。

## 创建 / 重建 SQLite 文件

仓库中已提供 `data/data.sqlite`。如需按照 RodSki 公共 DDL 重新生成，从仓库根目录执行：

```bash
python3 rodski-demo/DEMO/demo_business_model/data/init_data.py
```

**注意：脚本会删除并重建 `data/data.sqlite`。** 它从 `rodski/core/sqlite_schema.py` 读取公共 DDL，然后写入上述两张逻辑表、字段 schema 和三组配对 DataID。若要保留现有数据库内容，请先备份，不要直接运行重建脚本。
