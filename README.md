# 🏎️ RodSki

**RodSki** 是一个关键字驱动的自动化测试框架，使用 Python 编写，支持 Web（Playwright）、Android（Appium）、iOS（Appium）和桌面应用（PyWinAuto）的自动化测试。

> 从 SKI Java 测试框架重写而来，使用 PyQt6 构建 GUI，Playwright 替代 Selenium，新增 RESTful API 测试支持。

## ✨ 特性

- **关键字驱动** — 通过 xml 用例驱动测试执行，无需编写代码
- **多平台支持** — Web / Android / iOS / Windows 桌面应用
- **数据驱动** — 支持 xml 数据表与全局变量
- **智能等待** — 自动处理元素加载延迟，提高测试稳定性
- **RESTful API** — 内置 API 测试能力
- **并行执行** — 支持多用例并行
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

## 🎯 智能等待机制

RodSki 内置智能等待功能，自动处理 UI 元素的加载延迟，无需手动添加等待步骤。

### 特点

- ⚡ **零配置** — 默认启用，开箱即用
- 🚀 **性能优化** — 快速响应元素无延迟（首次立即尝试）
- 🔄 **自动重试** — 元素未加载时自动重试（默认 30 次 × 300ms = 9 秒）
- ⏱️ **智能停止** — 元素出现后立即执行，不浪费时间
- 🎛️ **可配置** — 支持自定义重试次数和间隔

### 配置

编辑 `rodski/config/config.json`：

```json
{
  "smart_wait_enabled": true,           // 启用智能等待
  "smart_wait_max_retries": 30,         // 最大重试 30 次
  "smart_wait_retry_interval": 0.3,     // 每次间隔 300ms
  "smart_wait_log_retry": true          // 记录重试日志
}
```

### 适用场景

- 动态加载的页面元素（React、Vue 等）
- 网络延迟导致的元素延迟出现
- 移动应用的异步加载
- 桌面应用的窗口切换

详见：[快速入门指南](rodski/docs/user-guides/QUICKSTART.md)

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
├── docs/           # 正式文档（requirements / design / user-guides），见 rodski/docs/README.md
└── examples/       # 示例
```

## 📄 License

MIT License - 详见 [LICENSE](rodski/LICENSE)
