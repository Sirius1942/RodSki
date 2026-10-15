# local/session_shared — F073 SessionMode 验收

`data/globalvalue.xml` 配置 `DefaultValue.SessionMode=shared_session`。`case/shared_session.xml`：
TC001 写入 localStorage + cookie 标记后 `close`，TC002 重新打开页面读取标记。

文档依据：CORE §7.4、§23.1、§23.4；GUIDE §6.4.4。

## 运行

```bash
python3 rodski-demo/local/session_shared/run_acceptance.py           # S01~S05
```

脚本先执行 `fun/build_data.py` 生成 `data.sqlite`，在 `127.0.0.1:18131` 以 `fun/site/` 起静态站，然后：

| 编号 | 命令 | 期望 |
|------|------|------|
| S01 | `rodski run case/`（globalvalue shared_session） | TC001/TC002 PASS；summary@session_mode=shared_session；浏览器启动 1 次 |
| S02 | `--session-mode isolated` | TC002 FAIL（读不到标记）；summary=isolated；浏览器启动 2 次 |
| S03 | `--session-mode shared_browser` | TC002 FAIL（新 context）；summary=shared_browser；浏览器启动 1 次 |
| S04 | 临时副本 SessionMode=bogus | 退出码非 0，列出合法取值，不执行用例 |
| S05 | `--session-mode bogus` | 参数解析报错，列出合法取值 |

裸跑 `rodski run case/ --session-mode isolated` 时 TC002 失败是**预期**（证明 CLI 覆盖生效）。
