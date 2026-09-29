# demo_authoring_v116 — AI 编写契约与断言可靠性验收

设计：`.pb/specs/v11.6.0-ai-authoring-and-performance-design.md`
来源：AI 写用例对比实验（Playwright+pytest+PO vs RodSki）暴露的框架契约问题。

## 当前覆盖（v11.5.2 P0）

| 用例 | 场景 | 修复前（v11.5.1）表现 |
|------|------|----------------------|
| `case/db/db_contract.xml` TC001 | query 模板里有时间字面量 `'2026-01-01 00:00:00'` + 命名参数 `:status`；该行 `sql=BLANK` 应回落到 `query` | `near "BLANK": syntax error` |
| `case/db/db_contract.xml` TC002 | 直接写 SQL，引号内含时间字面量 | `SQL 中引用了参数 ':00'，但数据表中未提供该参数` |

数据全部在模块内：`data/data.sqlite` 同时保存 RodSki 逻辑表（`OrderDB` / `OrderDB_verify`）和业务表 `orders`，连接组 `order_db` 指向它，不依赖外部数据库。

## 运行

```bash
cd rodski-demo/DEMO/demo_authoring_v116
rodski run case/db/
```

期望：`执行完成: 2/2 通过`。

## 规划中（v11.6.0）

原生数量/存在/可见/URL 断言、`verify` 自动重试、dialog、iframe、`evaluate file:`、登录态复用、会话复用、`--workers` 并行、JUnit 报告、简洁记录模式等验收用例将陆续加入本模块（见设计文档 §9.1）。
