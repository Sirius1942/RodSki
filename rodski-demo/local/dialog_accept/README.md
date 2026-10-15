# local/dialog_accept — F072 DialogPolicy 验收

三个兄弟模块只差 `data/globalvalue.xml` 的 `DefaultValue.DialogPolicy`（README 规则：模块级配置取值不同拆兄弟模块）：

| 模块 | DialogPolicy | 用例 |
|------|--------------|------|
| `dialog_accept/` | `accept` | alert / confirm / prompt 自动确认；一次性 `dismiss`、`accept:加急` 覆盖全局且只生效一次 |
| `../dialog_dismiss/` | `dismiss` | alert 关闭、confirm=false、prompt=null；一次性 `accept` 只生效一次 |
| `../dialog_default/` | 不写（默认 `fail`） | 未注册处理器的弹窗使 type 步骤立即失败（`expect_fail="是"`），错误含弹窗文本；遗留处理器在用例结束时清除 |

文档依据：CORE §2.5.6 第 4 条、§7.4；GUIDE §4.3.4、§6.4.3。

## 运行

```bash
python3 rodski-demo/local/dialog_accept/run_acceptance.py            # D01~D05
```

脚本先执行 `fun/build_data.py` 生成三个模块的 `data.sqlite`，在 `127.0.0.1:18130` 以 `fun/site/` 为根目录
起静态站（三模块共用 `dialog.html`），再逐模块 `rodski run <模块>/case --headless` 并断言 result.xml；
另外在临时目录复制模块、把 DialogPolicy 改为 `yes` 验证非法取值在执行前报错。
手工单跑时先起站点：`cd rodski-demo/local/dialog_accept/fun/site && python3 -m http.server 18130`。

已登记缺陷：D01:TC003（accept 策略下 prompt 以空串确认，而非默认值）。
