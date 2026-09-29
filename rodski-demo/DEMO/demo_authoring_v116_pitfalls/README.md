# demo_authoring_v116_pitfalls — 踩坑夹具（lint / 兼容性验收）

复现 AI 写用例对比实验里 RodSki 一侧的典型错误写法，**不是推荐写法**，供 `demo_authoring_v116/run_acceptance.py` 验收：

| 内容 | 用途 |
|------|------|
| `case/pitfalls/js_assertions.xml`（`execute="否"`） | `rodski case lint` 应报出 evaluate 断言、固定 wait、confirm 垫片（V14） |
| `data` 中 `OrderDB.Q_BAD`（`sql`、`query` 均为 BLANK） | lint 应报 ERROR（V14） |
| `globalvalue.xml` 中 `WaitTime=1` | 旧单位为秒；v11.6.0 起按毫秒，≤30 的旧值按秒兼容并打印弃用告警（V17） |
| `case/db/db_ok.xml` | 可执行；配合 `rodski data set` 修改期望值后直接重跑（V15） |

正确写法见 `../demo_authoring_v116/`。
