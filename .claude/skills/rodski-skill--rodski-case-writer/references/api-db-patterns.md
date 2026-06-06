# RodSki API 与 DB 模式

RodSki 接口和数据库用例使用本文。实时契约仍以 `TEST_CASE_WRITING_GUIDE.md` 为准；本文是从 `$HOME/TestCase/improve` 提炼出的紧凑模式索引。

## API 主路径

- 新 API 用例使用 `send` 加 `verify`。
- 不要写 `http_get`、`http_post`、`assert_json` 或 `assert_status`。
- 请求字段放在接口模型中，输入行放在 `data.sqlite`。
- 通过匹配的 `_verify` 逻辑表验证响应字段。
- 不要在 `_verify` 中将 `${Return[-1]}` 与它自身比较；期望值必须独立且有意义。

## 接口模型形态

- 必要时显式保留传输字段：`_method`、`_url`、headers、body/form 字段、redirects 和期望响应字段。
- 只有环境 URL 和 token 确实是全局值时，才放进 `globalvalue.xml`。
- 对稳定环境值使用 `GlobalValue.Group.Var` 引用，不要用于临时 case 数据。
- 优先使用 model/data 驱动的请求构造，而不是一次性 Python 脚本。

## `run` 边界

- 现有 `run login_api_check.py` 风格探针是兼容性边界，不是新 API 用例模板。
- 只有当 RodSki `send` 尚无法表达复杂登录、session bootstrap 或授权业务探测时，才使用 `run`。
- `run` 步骤后仍必须接基于模型和 `_verify` 行的 `verify`。
- 脚本失败应暴露状态、body 片段、业务 ID 和最近状态。不要把异常吞成泛泛失败文本。

## DB 主路径

- DB 测试使用 `DB` 加数据库模型和 `data.sqlite` 查询参数。
- DB 连接配置放在 `data/globalvalue.xml`。
- SQL 不应直接嵌入 `case.xml`。
- 查询行应有清晰的 DataID，验证行应断言真实业务值。
- DB `_verify` 行不得将最新 Return 自引用为期望值。

## UI 流程中的 API/DB

- 在长 UI 链路中，当这不是被测用户行为时，API 或 DB 可以用于设置前置条件、轮询状态或清理数据。
- API/DB 推进状态后，回到 UI 并验证用户可见状态。
- 授权业务 API 捷径必须明确，并且限定在测试环境范围内。
- 如果 API 轮询超时，报告业务 ID、最后状态/body 片段和页面状态。

## 失败分诊

- `send` 失败：检查接口模型字段、请求数据行、URL/header/global 引用，然后检查 `_verify`。
- API 后的 `verify` 失败：修改请求设置前，先检查响应结构和期望行。
- `DB` 失败：检查数据库模型、查询 DataID、连接全局值和 SQL 结果结构。
- API 返回看起来像认证页的 HTML，通常意味着 session/cookie bootstrap 失败，而不是 JSON 断言错误。
