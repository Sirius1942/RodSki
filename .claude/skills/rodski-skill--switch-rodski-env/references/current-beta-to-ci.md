# 当前 beta_old 到 ci_new 的换环境参考

本参考来自 2026-05-28 对比：

- 旧目录：`$HOME/beta_old/000 case_old`
- 新目录：`$HOME/ci_new/000 case_new`

只把这里当作经验映射，不要替代实时审计。

## URL 规律

已观察到的 EC 域名切换：

- `ec-hwbeta.casstime.com` -> `ec-hwci.casstime.com`
- `http://ec-hwbeta.casstime.com/seller` -> `https://ec-hwci.casstime.com/seller`
- `https://ec-hwbeta.casstime.com/admin` -> `https://ec-hwci.casstime.com/admin#/`
- `https://ec-hwbeta.casstime.com/passport/login` -> `https://ec-hwci.casstime.com/passport/login`
- `https://ec-hwbeta.casstime.com/agentBuy/` -> `https://ec-hwci.casstime.com/agentBuy/`

仍需人工确认的项：

- `https://f2b-beta.casstime.com/admin`
- `https://f2b-beta.casstime.com/buyer`
- `https://f2b-beta.casstime.com/seller`
- `https://f2b-beta.casstime.com/admin#/source-manage/config`

这些项在当前 ci_new 目录仍未切走。不要自动猜成 `f2b-ci`，除非用户提供目标值或已有目标目录能推断。

## DB host 映射

本次已观察到的 `globalvalue.xml` host 切换。真实 host 已脱敏；使用时通过
`audit`/`compare`/`extract-map` 从当前旧新目录重新生成映射。

- `ec_central_promotion_mysql.host`
  - old: `<old_db_host>`
  - new: `<new_db_host>`
- `ec_commerce_mysql.host`
  - old: `<old_db_host>`
  - new: `<new_db_host>`
- `ec_central_beta_mysql.host`
  - old: `<old_db_host>`
  - new: `<new_db_host>`
- `ec_distribute_mysql57.host`
  - old: `<old_db_host>`
  - new: `<new_db_host>`
- `infrastructure_mysql.host`
  - old: `<old_db_host>`
  - new: `<new_db_host>`
- `master_data_mysql.host`
  - old: `<old_db_host>`
  - new: `<new_db_host>`
- `new_billing_bosch_mysql.host`
  - old: `<old_db_host>`
  - new: `<new_db_host>`
- `one_account_mysql.host`
  - old: `<old_db_host>`
  - new: `<new_db_host>`
- `peer_resupply_mysql.host`
  - old: `<old_db_host>`
  - new: `<new_db_host>`

## 注意

- `分流/data/globalvalue.xml` 当前是本地 SQLite：`type=sqlite`、`database=data/data.sqlite`。这不是外部 DB host；是否需要切换取决于目标环境策略。
- 密码、用户名、token、cookie 不属于本技能默认改动范围。除非用户明确要求，不要改。
