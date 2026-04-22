# RodSki测试样例Demo

## 🚀 快速开始

### 1. 安装依赖
```bash
cd rodski-demo/DEMO/demo_full
pip3 install fastapi uvicorn jsonschema requests
```

### 2. 初始化数据库
```bash
python3 init_db.py
```

### 3. 启动服务
```bash
python3 demosite/app.py
```

访问：http://localhost:8000
登录：admin / 123456

### 4. 准备 SQLite 示例数据（TC030）

`data/data.sqlite` 是 demo 中唯一的 SQLite 测试数据文件，默认承载 `RegisterAPI` 示例数据。
如本地是历史拷贝，请确保 SQLite 测试数据文件已经统一迁移为固定文件名 `data/data.sqlite`。

### 5. 运行测试

**使用 Shell 脚本（推荐）**:
```bash
./run_demo.sh
```

**使用 Python 脚本（跨平台）**:
```bash
python3 run_demo.py
```

**手动运行**:
```bash
cd ../../../rodski
python3 ski_run.py ../rodski-demo/DEMO/demo_full/case/demo_case.xml
```

## 📝 测试用例（当前默认回归 4 个）

默认 `run_demo.py` / `run_demo.sh` 运行 `case/demo_case.xml`，当前聚焦一组稳定可回归的浏览器/API/SQLite 示例：

- TC015: Auto Capture + set/get 命名变量
- TC016: Playwright 定位器覆盖（ID / Name / CSS / XPath / 滚动点击）
- TC030-001: SQLite 数据源 + `/api/register`（L001）
- TC030-002: SQLite 数据源 + `/api/register`（L002）

其余用例仍保留在 `case/` 目录中，便于按需单独执行或继续修正。

## ✅ RodSki能力覆盖

当前默认回归直接覆盖：

- Web UI：navigate / type / verify / get / set / close
- Playwright 定位器：id / name / css / xpath / 滚动后点击
- Auto Capture：type 自动提取返回值
- API：send + verify
- SQLite 测试数据：`data/data.sqlite` 固定文件名、模型名强一致、XML/SQLite 共存

按需单独运行的附加示例仍保留在 `case/` 目录：

- `tc017_keywords.xml`：wait / clear / screenshot / get
- `tc018_vision.xml`：视觉定位（需额外环境）
- `tc019_desktop.xml`：桌面自动化（需手动启用）
- `tc020_windows.xml`：多窗口/iframe 草案
- `tc021_data_ref.xml`：复杂数据引用旧示例
- `tc022_negative.xml`：expect_fail 负面示例

## 📂 目录结构

```
demo_full/
├── case/           # 测试用例
│   ├── demo_case.xml       # 默认稳定回归集合（TC015 / TC016 / TC030）
│   ├── tc015_only.xml      # 单独测试TC015
│   ├── tc016_locators.xml  # TC016 定位器测试
│   ├── tc017_keywords.xml  # TC017 关键字测试
│   ├── tc018_vision.xml    # TC018 视觉定位测试（需手动启用）
│   ├── tc019_desktop.xml   # TC019 桌面自动化测试（需手动启用）
│   ├── tc020_windows.xml   # TC020 多窗口/iframe 草案
│   ├── tc021_data_ref.xml  # TC021 旧数据引用示例
│   ├── tc022_negative.xml  # TC022-024 负面测试集合
│   ├── tc030_sqlite_data.xml # SQLite 数据源验收
│   └── tc_expect_fail.xml  # expect_fail功能演示
├── model/          # 模型定义
│   └── model.xml           # 所有模型定义
├── data/           # 测试数据
│   ├── data.xml            # XML 输入数据
│   ├── data_verify.xml     # XML 验证数据
│   ├── data.sqlite         # SQLite 测试数据（固定文件名）
│   ├── globalvalue.xml     # 全局变量配置
│   ├── DB_USAGE.md         # 数据库/SQLite 使用说明
│   └── README.md           # 数据目录说明
├── demosite/       # 示例网站
│   └── app.py              # FastAPI应用
├── fun/            # Python代码
│   └── gen_data.py         # 数据生成脚本
├── result/         # 测试结果（运行后生成）
├── init_db.py      # 数据库初始化
├── run_demo.sh     # Shell运行脚本
├── run_demo.py     # Python运行脚本（跨平台）
└── README.md       # 本文件
```

## 📋 注意事项

1. 运行 `run_demo.py` 前需先启动 `python3 demosite/app.py`
2. 运行前建议先执行 `python3 init_db.py`，并确保 `data/data.sqlite` 存在
3. `demo_case.xml` 当前只保留稳定回归集合；其余示例请按单文件执行
4. 测试结果保存在 `result/` 目录，包含执行日志和截图
