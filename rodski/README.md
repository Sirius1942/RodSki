# RodSki - 自动化测试框架

基于关键字驱动的现代化自动化测试框架，Python 重写版本。

## 特性

- 🎯 关键字驱动 - 简单易用的测试语法
- 🔧 模型驱动 - 模型与数据分离
- 🌐 多驱动支持 - Playwright (Web) + PyWinAuto (Desktop) + Appium (Mobile)
- 📊 XML 用例 - 结构化测试定义
- 🔌 RESTful API - 接口测试支持

## 快速开始

📖 **[5分钟快速入门指南](docs/user-guides/QUICKSTART.md)** - 新手必读！

### 安装

```bash
pip install -r requirements.txt
playwright install chromium
```

### CLI 运行

```bash
python3 cli_main.py run examples/product/DEMO/demo_site/case/demo_case.xml
```

## 项目结构

```
rodski/
├── core/          # 核心引擎
├── drivers/       # 驱动层
├── api/           # API 测试
├── config/        # 配置
├── data/          # 测试数据
├── examples/      # 示例用例
└── docs/          # 文档
```

## 开发

### 环境要求

- Python 3.8+
- Playwright

### 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License
