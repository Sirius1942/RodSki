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

### 4. 运行测试

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

## 📝 测试用例（19个）

### ✅ 已实现功能覆盖

**Web UI测试（10个）**
- TC001: Web登录测试 - navigate + type
- TC002: 看板数据验证 - verify
- TC003: 功能测试页操作 - type多控件
- TC008: UI动作关键字测试 - hover, double_click, right_click, scroll, drag
- TC009: Return引用测试 - Return[-1]引用上一步返回值
- TC009A: history连续性测试 - 验证history跨步骤连续性
- TC011: get选择器模式测试 - 直接读取DOM元素
- TC012: evaluate结构化返回测试 - JavaScript执行
- TC012B: get模型模式测试 - 通过模型读取数据
- TC015: 结构化日志验证 - execution_summary

**API接口测试（2个）**
- TC004: API登录接口测试 - send + verify
- TC005: API查询订单 - send GET请求

**数据库测试（1个）**
- TC006: 数据库查询订单 - DB关键字

**代码执行（1个）**
- TC007: Python代码执行 - run关键字

**高级特性测试（5个）**
- TC010: set/get命名访问测试 - 变量存储和读取
- TC012A: get不存在key报错测试 - expect_fail负面测试
- TC013: type Auto Capture测试 - 自动提取返回值
- TC014: send Auto Capture测试 - API自动提取
- TC014A: type Auto Capture失败测试 - 错误场景验证

## ✅ RodSki能力覆盖

**Web UI测试**
- navigate - 页面导航
- type - UI批量输入（input/button/select）
- verify - 批量验证
- get - 读取元素值（支持选择器模式和模型模式）
- evaluate - 执行JavaScript代码
- UI动作：hover, double_click, right_click, scroll, drag
- 定位器：id, css

**API接口测试**
- send - POST/GET请求
- verify - JSON响应验证
- RESTful API
- Auto Capture - 自动提取响应字段

**数据库测试**
- DB - SQLite/MySQL查询和更新

**代码执行**
- run - Python脚本执行

**高级功能**
- Return引用 - Return[-1]引用上一步返回值
- set/get - 命名变量存储和访问
- GlobalValue - 全局变量配置
- expect_fail - 负面测试用例支持
- Auto Capture - type/send自动返回值提取
- 结构化日志 - execution_summary JSON输出

**数据驱动测试**
- 模型驱动（model.xml）
- 数据表驱动（data/data.xml）
- GlobalValue全局变量（data/globalvalue.xml）

## 📂 目录结构

```
demo_full/
├── case/           # 测试用例
│   ├── demo_case.xml       # 主测试用例集（17个用例）
│   ├── tc015_only.xml      # 单独测试TC015
│   └── tc_expect_fail.xml  # expect_fail功能演示
├── model/          # 模型定义
│   └── model.xml           # 所有模型定义
├── data/           # 测试数据
│   ├── data.xml            # 所有测试数据表（44个）
│   ├── globalvalue.xml     # 全局变量配置
│   ├── DB_USAGE.md         # 数据库使用说明
│   └── README.md           # 数据目录说明
├── demosite/       # 示例网站
│   └── app.py              # FastAPI应用
├── fun/            # Python代码
│   └── gen_data.py         # 数据生成脚本
├── result/         # 测试结果
├── init_db.py      # 数据库初始化
├── run_demo.sh     # Shell运行脚本
├── run_demo.py     # Python运行脚本（跨平台）
└── README.md       # 本文件
```

## 📋 注意事项

1. Web UI测试需要页面完全加载（约18秒超时）
2. 数据库路径配置在 `data/globalvalue.xml` 中
3. 测试结果保存在 `result/` 目录，包含详细的执行日志和截图
