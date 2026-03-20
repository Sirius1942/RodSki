# RodSki - 自动化测试框架

基于关键字驱动的现代化自动化测试框架，Python 重写版本。

## 特性

- 🎯 关键字驱动 - 简单易用的测试语法
- 🔧 模型驱动 - 模型与数据分离
- 🌐 多驱动支持 - Playwright (Web) + PyWinAuto (Desktop) + Appium (Mobile)
- 📊 Excel 用例 - 零编程门槛
- 🎨 PyQt6 界面 - 现代化 UI
- 🔌 RESTful API - 接口测试支持

## 快速开始

📖 **[5分钟快速入门指南](docs/QUICKSTART.md)** - 新手必读！

### 安装

```bash
pip install -r requirements.txt
playwright install chromium
```

### GUI 运行

```bash
python3 ski_gui.py
```

### CLI 运行

```bash
python3 cli_main.py run examples/demo_case.xlsx
```

## 项目结构

```
rodski/
├── core/          # 核心引擎
├── ui/            # PyQt6 界面
├── drivers/       # 驱动层
├── api/           # API 测试
├── tests/         # 测试用例
├── config/        # 配置
├── logs/          # 日志
└── data/          # 测试数据
```

## 开发

### 环境要求

- Python 3.11+
- Playwright
- PyQt6

### 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License
