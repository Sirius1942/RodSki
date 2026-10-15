# data_rules — 数据规则验收（local）

验收数据表 / 引用 / 内置函数 / Schema 相关的文档约定。不依赖 :8000：页面与接口由
`fun/mock_server.py`（127.0.0.1:18121，仅标准库）提供，用例 pre_process 中 `run mock_server.py ensure`
自动后台启动（空闲 600 秒自动退出）；DB 用例使用模块目录下 `.runtime/biz.db`（本地 SQLite，自动建表）。

## 运行

```bash
# 规定入口（仓库根目录）：41 个检查项，输出 PASS / KNOWN / FAIL / FIXED，退出码 0 = 无 FAIL
python3 rodski-demo/local/data_rules/run_acceptance.py
python3 rodski-demo/local/data_rules/run_acceptance.py F026 F055   # 只跑指定功能
python3 rodski-demo/local/data_rules/run_acceptance.py --strict    # KNOWN 也算失败

# 只执行 case/（21 个用例；当前 16 通过、5 个 KNOWN 失败，退出码 1）
python3 rodski/cli_main.py run rodski-demo/local/data_rules/case --headless

# 重建 data.sqlite
python3 rodski-demo/local/data_rules/data/init_data.py
```

会改 data / case 的检查（F049 import 与行级编辑、F050、F056、F065/F086 负向）全部在临时副本中进行，模块本身不被修改。

## 目录

| 路径 | 说明 |
|------|------|
| `case/f026_special_values.xml` | F026 BLANK/NULL/NONE/空值：UI type、UI verify、send、接口 verify、DB verify（含 1 个 expect_fail） |
| `case/f027_password_mask.xml` | F027 `.Password` 后缀输入 |
| `case/f055_return_refs.xml` | F055 `${Return[-2]}` / `${Return[-1]}` / `${Return[0]}` / `表名.DataID.字段名`（只写在数据表字段值中）、UI verify 跨源 `${Return[-2]}` |
| `case/f059_generators.xml` | F059 生成函数（数据表字段值），`fun/check_generated.py` 断言格式 / 范围 |
| `case/f060_generator_in_case.xml` | F060 set 中纯函数与 `$${` 转义；set / navigate 中写生成函数报错（4 个 expect_fail） |
| `case/f065_metadata.xml` | F065 `<metadata>` 6 个属性 |
| `plan/data_rules_smoke.xml` | F086 plan.xsd 校验样例（F059 + F065） |
| `fun/mock_server.py` | 页面 `/pages/*`、回显 `/echo/<tag>`（请求记录到 `.runtime/requests.jsonl`）、固定响应 `/fixed/specials` |
| `fun/emit.py` | 输出 `{"tag": ...}` 作为 run 步骤返回值（构造 Return 链） |
| `fun/negative/` | 负向样例（不放在 case/，避免污染整目录执行）：`f056_verify_return_forbidden.xml`、`invalid_case.xml`、`invalid_model.xml`、`invalid_plan.xml`、`metadata_after_pre.xml` |
| `data/init_data.py` | 生成 data.sqlite；`NEGATIVE_F056` 为 F056 负向数据（只写入临时副本） |

## 检查项与文档依据

| 编号 | 断言 | 依据 |
|------|------|------|
| F086-01 | case/ 全部、fun/negative/f056、model.xml、plan/*.xml、globalvalue.xml 分别通过 case/model/plan/globalvalue.xsd | GUIDE §2.2 |
| F086-02 | 非法关键字 `click`、旧版 `type/value` 定位器、缺 `kind` 的 plan、metadata 位置错误 —— xmllint 均失败 | CORE 关键字清单、§2（`<location>` 唯一格式）；plan.xsd |
| F086-03 | 非法 case 放进 case/，`rodski run` 报 SKI204 case.xsd、退出码非 0 | GUIDE §2.2 |
| F086-04 | `rodski plan validate data_rules_smoke` 通过 | GUIDE §10.4 |
| F027-01 | `Zq7SecretPw.Password` 输入后页面得到 11 位、字符码和一致（后缀已去掉） | CORE §4.1；GUIDE §5.4 |
| F027-02 | execution.log 中 password 输入显示 `***` | GUIDE §5.4 |
| F027-03 | 明文不出现在 execution.log / result.xml / 控制台 | CORE §4.1「日志脱敏」；GUIDE §5.4 |
| F027-04 | type 的 Return（execution_summary.json return_value）不含明文 | 任务要求（文档未明确 Return 是否脱敏，见 KNOWN） |
| F026-01 | UI type：BLANK / NULL / NONE 跳过，预填值不变 | CORE §4.1；GUIDE §5.4 |
| F026-02 | UI type：空值跳过 | CORE §4.1「空值 → 跳过」；GUIDE §5.4 |
| F026-03 | UI verify：BLANK / NONE 跳过 | CORE §4.1；GUIDE §5.7.3 |
| F026-04 | send：BLANK→`""`、NULL→`null`、NONE→不发送（mock 原始请求体确认） | CORE §4.1；GUIDE §5.4 |
| F026-05 | 接口 verify：BLANK 期望空串、NULL 期望 null | CORE §4.1；GUIDE §5.7.3 |
| F026-06 | 接口 verify：NONE 跳过验证 | CORE §4.1 |
| F026-07 | 接口 verify：BLANK 遇实际 `hello` 失败（expect_fail，失败字段为 v_text） | CORE §4.1；GUIDE §5.7.3 |
| F026-08 | DB verify：BLANK 跳过、NULL 期望 null | CORE §4.1；GUIDE §5.7.3 |
| F026-09 | DB verify：NONE 跳过验证 | CORE §4.1 |
| F055-01 | `${Return[-2]}`、`${Return[-1]}`、`PwdForm.P001.username`、`pre-SpecForm.S001.f4-post` 解析正确 | GUIDE §7.1、§7.2；CORE §4.2 |
| F055-02 | UI type 引用 `${Return[-1]}`；UI _verify 引用 `${Return[-2]}` 跨源比对 | GUIDE §5.6、§7.3；CORE §4.3 |
| F055-03 | 非首个用例中 `${Return[0]}` = 本用例第一步返回值 | GUIDE §7.2（「第一步返回值」） |
| F055-04 | 用例单独执行时 `${Return[0]}` 取到第一步返回值 | GUIDE §7.2 |
| F059-01 | random int/float/str/digits/phone/email/choice/uuid、date now/today/time/timestamp/timestamp_ms/offset(天/小时/格式)、timestamp()/timestamp_ms()/timestamp36()、拼接、`$${` 转义；两次求值不同 | GUIDE §7.7；CORE §4.4.1~4.4.3、§4.4.6 规则 4/7 |
| F060-01 | set 中 `${toUpperCase(${raw})}` 得到 ABC | CORE §4.4.6 规则 5；GUIDE §7.6.2 |
| F060-02 | set 中 `$${random(int, 1, 9)}` 不报错且保持字面量 | CORE §4.4.6 规则 7 |
| F060-03 | set 中 random / date / timestamp36、navigate data 中 random —— 报「只能写在 data.sqlite 字段值中」 | CORE §4.4.6 规则 5；GUIDE §7.6.2、§7.7 |
| F065-01 | 6 个 metadata 属性通过 case.xsd，位于 pre_process 之前 | GUIDE §3.2 |
| F065-02 | 带 metadata 的用例正常通过，执行后用例文件不被改写 | GUIDE §3.2（只记录元信息） |
| F065-03 | metadata 放在 pre_process 之后：xmllint 失败，run 报 SKI204 | GUIDE §3.2 |
| F049-01 | GUIDE 列出的 9 个 data 子命令 CLI 均存在（CLI 另有文档未列的 dump / add-field） | GUIDE §5.3.1 |
| F049-02~06 | list（表与行数）/ schema / show（含不存在 DataID 报错）/ query --limit / validate | GUIDE §5.3.1 |
| F049-07 | import 首次导入、默认跳过、--overwrite 覆盖；data.xml 未删时 run 报 SKI203 | GUIDE §5.2；DATA_FILE_ORGANIZATION「数据迁移」；CORE §2.4.1 |
| F049-08 | add-row / set / delete-row；set 未知字段报错并列出合法字段 | GUIDE §5.3.1；CORE §2.4.1 |
| F050-01 | add-row 缺字段：报错、列出缺字段、提示 BLANK/NULL/NONE、不写入 | GUIDE §5.3.1；CORE §2.4.1 |
| F050-02 | data.sqlite 某行缺字段：validate 与 run 均报错并提示 BLANK/NULL/NONE | GUIDE §5.1；CORE §2.4.1 |
| F050-03 | import 字段不一致的 XML：须统一为固定字段集合 | CORE「XML-only 历史数据…迁移到 SQLite 时必须统一为固定字段集合」 |
| F056-01 | 接口 / DB _verify 中 `${Return[-1]}`：运行前 SKI703 return_ref_self_check 拦截并指出两张表 | CORE §4.3；GUIDE §7.4 |
| F056-02 | `--force-compliance` 后 verify 步骤仍硬性失败（原因为自引用） | CORE §4.3（v6.7.6 硬性约束） |

## KNOWN（框架与文档不符，保留用例、未改框架）

| 检查项 | 现象 |
|--------|------|
| F026-02 | 空值字段被当作输入值，输入框被清空（实际 `f5=`） |
| F026-06 / F026-09 | 接口 / DB verify 中 `NONE` 被当作期望字符串 `none`，未跳过 |
| F027-03 | execution.log 的 `history[N]=...` DEBUG 行打印 type 返回值，含 `.Password` 明文 |
| F027-04 | type 的 Return 含 `明文.Password`（execution_summary.json return_value 同样落盘） |
| F050-03 | `data import` 接受字段不一致的 XML，写出的 data.sqlite 随后 validate / run 均失败 |
| F055-03 | Return 历史在一次运行内跨用例累积不重置，非首个用例中 `${Return[0]}` 指向整次运行第一步 |
| F060-02 | set 的值先经 `resolve_case_data` 去转义，再在 `_kw_set` 中 `resolve_with_return` 二次解析，`${random(...)}` 被求值 |

修复后 run_acceptance.py 会把对应项报为 FIXED，届时从脚本 `KNOWN` 表与本表移除。
