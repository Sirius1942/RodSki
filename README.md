# 🏎️ RodSki

**RodSki** 是一个关键字驱动的自动化测试框架，使用 Python 编写，支持 Web（Playwright）、Android（Appium）、iOS（Appium）和桌面应用（PyWinAuto）的自动化测试。

> 从 SKI Java 测试框架重写而来，使用 PyQt6 构建 GUI，Playwright 替代 Selenium，新增 RESTful API 测试支持。

## ✨ 特性

- **关键字驱动** — 通过 Excel 用例驱动测试执行，无需编写代码
- **多平台支持** — Web / Android / iOS / Windows 桌面应用
- **数据驱动** — 支持 Excel 数据表与全局变量
- **RESTful API** — 内置 API 测试能力
- **并行执行** — 支持多用例并行
- **GUI 界面** — PyQt6 图形化管理界面
- **CLI 工具** — 命令行接口，支持 CI/CD 集成
- **测试报告** — 自动生成 HTML 测试报告

## 🚀 快速开始

### 安装

```bash
pip install -r requirements.txt
```

### CLI 使用

```bash
# 执行测试用例
rodski run case.xlsx

# 详细输出
rodski run case.xlsx --verbose

# 单步执行
rodski run case.xlsx --step-by-step

# 查看配置
rodski config list
```

### GUI 启动

```bash
python rodski/ski_gui.py
```

## 📁 项目结构

```
rodski/
├── api/            # RESTful API 测试
├── cli_main.py     # CLI 入口
├── config/         # 配置文件
├── core/           # 核心引擎（关键字解析、执行器等）
├── drivers/        # 浏览器/设备驱动
├── rodski_cli/     # CLI 子命令
├── ui/             # GUI 界面
├── utils/          # 工具函数
├── tests/          # 测试用例
├── docs/           # 文档
└── examples/       # 示例
```

## 📄 License

MIT License - 详见 [LICENSE](rodski/LICENSE)
