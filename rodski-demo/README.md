# rodski-demo

RodSki 官方示例与验收用例库。本目录就是 product 层：

```
rodski-demo/<环境>/<模块>/{case,model,data,fun,plan,...}
```

- **项目层按运行环境划分**：同一环境的模块共享前置条件（服务、设备、桌面会话），回归时按环境分批起停。
- **模块层按功能域划分**：一个模块验收一组相关能力；模块级配置（AutoWait、DialogPolicy、SessionMode 等）需要不同取值时拆成兄弟模块（如 `autowait` / `autowait_zero` / `autowait_long`）。
- 用例编写规范以 `rodski/docs/TEST_CASE_WRITING_GUIDE.md` 为准。

## 全量回归

```bash
python3 rodski-demo/run_regression.py                 # 全部环境
python3 rodski-demo/run_regression.py local demosite  # 只跑指定环境
python3 rodski-demo/run_regression.py --desktop       # 额外执行会操作鼠标键盘的桌面用例
```

脚本按环境自动启动所需服务（demosite、web、mock、模块自带静态站），输出 `PASS / FAIL / KNOWN / ENV_BLOCKED`，逐用例结果写入 `rodski-demo/.regression/<时间戳>/cases.json`，结束时恢复被运行改写的 demo.db、data.sqlite、截图等产物。

## 模块索引

### `_sites/` 共享被测站点

| 目录 | 说明 |
|------|------|
| `_sites/demosite/` | FastAPI 站点，`python3 rodski-demo/_sites/demosite/app.py` → http://localhost:8000（admin / 123456）。首次启动自动生成站点自用的 `demo.db`。不是测试模块。 |

### `local/` 无外部服务

| 模块 | 验收内容 | 规定入口 |
|------|---------|---------|
| `expressions/` | 内置函数、数组、断言操作符、match_mode | `rodski run case/` |
| `control_flow/` | if/elif/else、loop、scenario tags/depends | `run_v7_demo.py` |
| `hooks/` | Hook 事件与权限 | `run_demo.py` |
| `runtime_control/` | 暂停 / 恢复 / 插入步骤 | `run_demo.py` |
| `roaming/` | 漫游执行 | `run_demo.py` |
| `nested_case/` + `_single` + `_dup_id` | 嵌套目录用例、case_file::case_id 身份（v11.5） | `nested_case/run_acceptance.py` |
| `authoring/` + `_pitfalls` + `_no_retry` | AI 编写契约、lint、断言可靠性（v11.5.2+） | `authoring/run_acceptance.py` |
| `autowait/` + `_zero` + `_long` | 自动等待（v11.7） | `autowait/run_acceptance.py` |
| `debug_partial_execution/` | 调试与局部执行验收（REQ-012，37 条） | `rodski run case/` |
| `debug_partial_execution_targets/` | 上一模块驱动的被测用例 | 由上一模块调用 |

### `demosite/` 依赖共享站点 :8000

| 模块 | 验收内容 | 规定入口 |
|------|---------|---------|
| `full/` | 主回归：UI、接口、SQLite、Return 引用、定位器、多窗口/iframe、内置函数、录制、JS 覆盖率；发布 Stage 2/4 使用其子集 | `rodski run case/ --headless` |
| `core_keywords/` | 关键字基础示例：SQLite 查询/插入、GlobalValue、Return 链、Set/Get、assert 图片、clear/check、run 脚本 | `rodski run case/ --headless` |
| `load/` | 性能压测计划 | `rodski run @api_load_basic`（在模块目录下） |
| `pause_takeover/` | CDP 共享浏览器暂停接管 | `run_demo.py` |

### `mock_api/`

| 模块 | 验收内容 | 规定入口 |
|------|---------|---------|
| `business_model/` | 业务模型 business_call（v11.4），自带 `server.py` mock | `acceptance.py`；回归时改用 18001 端口 |

### `mobile/` 需 Android 模拟器 + Appium

| 模块 | 验收内容 | 规定入口 |
|------|---------|---------|
| `app/` | 自建 Android/iOS App、移动端 AutoWait、录像 | `scripts/run_autowait_acceptance.py`、`rodski run case/login.xml --udid emulator-5554` |
| `qq_music/` | 第三方 App 示例 | 需安装 QQ 音乐 APK |

### `desktop_vision/` 需桌面会话或视觉服务

| 模块 | 验收内容 | 规定入口 |
|------|---------|---------|
| `perception/` | 感知定位（本地视觉模型） | 需 `test_app` 与 qwen3-vl 模型 |
| `desktop/` | macOS 桌面自动化与录制（TextEdit） | `rodski run case/`，执行时勿移动鼠标 |

### `plugins/`

| 模块 | 验收内容 | 规定入口 |
|------|---------|---------|
| `browser_plugin/` | 浏览器插件后端 API（web :5002） | `rodski run case/ --headless` |
| `browser_plugin_baidu/` | 插件示例：百度搜索 | `rodski run case/ --headless` |
| `vscode_plugin/` | VS Code 扩展（含打开表格视图的桌面用例） | `rodski run case/` |
| `website/` | 官网测试（需 rodski-website 仓库 :3001） | `rodski run case/` |

## 新增用例放在哪里

1. 先按**运行环境**选项目：只用 data: URL / 本地脚本 → `local/`；需要 demosite → `demosite/`；以此类推。
2. 再按**功能域**选模块；已有模块覆盖该功能域就加到该模块的 `case/` 下，需要不同模块级配置时新建兄弟模块。
3. 模块名不能用保留名（case、model、data、plan、fun、result、business、perf、knowledge）。
4. 新模块需要在 `run_regression.py` 登记规定入口，并在本表补一行。
