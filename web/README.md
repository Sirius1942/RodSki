# RodSki Web - 测试用例管理系统

🍄 关键字驱动测试用例 Web 管理平台

## 项目简介

RodSki Web 是一个独立的测试用例管理系统，用于管理 RodSki 框架的测试用例、页面模型和测试结果。

**关键特性：**
- ✅ 独立项目，不依赖 RodSki 主项目代码
- ✅ 通过配置文件指定 RodSki 数据路径，实现解耦
- ✅ 自己实现 XML 解析器，解析逻辑与 RodSki 一致
- ✅ 调用 RodSki CLI 执行测试用例
- ✅ 马里奥主题 UI 设计

## 项目结构

```
rodski-web/
├── src/
│   ├── __init__.py
│   ├── app.py                    # Flask 应用入口
│   ├── api/                      # API 层
│   │   ├── __init__.py
│   │   ├── cases.py             # 用例管理 API
│   │   ├── models.py            # 模型管理 API
│   │   ├── results.py           # 结果管理 API
│   │   └── runner.py            # 执行器 API
│   ├── services/                # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── case_service.py      # 用例服务
│   │   ├── model_service.py     # 模型服务
│   │   ├── result_service.py    # 结果服务
│   │   └── runner_service.py    # 执行器服务
│   └── parsers/                 # XML 解析器（自己实现）
│       ├── __init__.py
│       ├── case_parser.py       # 用例解析器
│       ├── model_parser.py      # 模型解析器
│       └── data_parser.py       # 数据解析器
├── static/
│   ├── css/
│   │   └── style.css           # 马里奥主题样式
│   └── js/
│       └── app.js              # 前端脚本
├── templates/
│   ├── base.html               # 基础模板
│   ├── index.html              # 首页
│   ├── cases.html              # 用例管理页
│   ├── models.html             # 模型管理页
│   ├── results.html            # 结果管理页
│   └── runner.html             # 执行器页
├── config.yaml                 # ⭐ 配置文件
├── requirements.txt
├── run.sh                      # 启动脚本
└── README.md
```

## 核心功能

### 1. 用例管理
- 查看所有测试用例
- 按模块筛选用例
- 搜索用例（按标题、描述、ID）
- 查看用例详情和执行步骤
- 生成用例的人类可读说明

### 2. 模型管理
- 查看所有页面模型
- 查看模型元素定位符
- 搜索模型

### 3. 结果管理
- 查看历史测试结果
- 查看测试结果汇总统计
- 查看详细的执行步骤

### 4. 测试执行器
- 执行单个测试用例
- 验证用例格式（dry-run）
- 生成用例说明
- 查看执行状态

## 与 RodSki 的解耦方式

### 1. 配置文件解耦

```yaml
# config.yaml
rodski:
  project_path: /path/to/rodski           # RodSki 项目路径
  data_path: /path/to/cassmall/rod_ski_format  # 测试数据路径
  run_timeout: 300                         # 执行超时
```

### 2. 数据软链接

```bash
# 将 RodSki 测试数据软链接到本地
ln -s /path/to/cassmall/thdh/rod_ski_format data
```

### 3. 执行器调用 CLI

```python
# 通过 subprocess 调用 RodSki CLI
cmd = ['python3', 'cli_main.py', 'run', case_path]
result = subprocess.run(cmd, capture_output=True, cwd=project_path)
```

### 4. 独立 XML 解析器

`parsers/` 目录下的解析器独立实现，解析逻辑与 RodSki 一致，但不依赖 RodSki 代码。

## 安装与启动

### 1. 安装依赖

```bash
cd rodski-web
pip install -r requirements.txt
```

### 2. 配置

编辑 `config.yaml`，设置正确的 RodSki 项目路径和数据路径。

### 3. 启动

```bash
# 方式一：直接运行
python3 src/app.py

# 方式二：使用启动脚本
./run.sh

# 方式三：指定配置目录
RODSKI_CONFIG=/path/to/config.yaml python3 src/app.py
```

### 4. 访问

打开浏览器访问: http://localhost:5000

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/cases/` | GET | 获取用例列表 |
| `/api/cases/<id>` | GET | 获取用例详情 |
| `/api/cases/<id>/explain` | GET | 获取用例说明 |
| `/api/models/` | GET | 获取模型列表 |
| `/api/models/<name>` | GET | 获取模型详情 |
| `/api/results/` | GET | 获取结果列表 |
| `/api/results/summary` | GET | 获取结果汇总 |
| `/api/runner/run` | POST | 执行用例 |
| `/api/runner/dry-run` | POST | 验证用例 |
| `/api/runner/explain` | POST | 生成用例说明 |

## 技术栈

- **后端**: Flask
- **前端**: 原生 HTML/CSS/JavaScript
- **主题**: 马里奥游戏风格 🍄

## License

MIT
