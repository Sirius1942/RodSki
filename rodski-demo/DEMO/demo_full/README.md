# RodSki测试样例Demo

## 🚀 快速开始

### 1. 安装依赖
```bash
cd product/DEMO/demo_full
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
```bash
cd ../../../rodski
python3 ski_run.py ../product/DEMO/demo_full/case/demo_case.xml
```

## 📝 测试用例（10个）

### ✅ 已实现功能覆盖

**Web UI测试**
- TC001: Web登录测试 - navigate + type
- TC002: 看板数据验证 - verify
- TC003: 功能测试页操作 - type多控件
- TC008: UI动作关键字测试 - hover, double_click, right_click, scroll, drag

**API接口测试**
- TC004: API登录接口测试 - send + verify
- TC005: API查询订单 - send GET请求

**数据库测试**
- TC006: 数据库查询订单 - DB关键字

**代码执行**
- TC007: Python代码执行 - run关键字

**高级功能**
- TC009: Return引用测试 - Return[-1]引用上一步返回值
- TC010: set变量测试 - 设置和使用变量（已禁用）

## ✅ RodSki能力覆盖

**Web UI测试**
- navigate - 页面导航
- type - UI批量输入（input/button/select）
- verify - 批量验证
- UI动作：hover, double_click, right_click, scroll, drag
- 定位器：id, css

**API接口测试**
- send - POST/GET请求
- verify - JSON响应验证
- RESTful API

**数据库测试**
- DB - SQLite查询

**代码执行**
- run - Python脚本执行

**高级功能**
- Return引用 - Return[-1]引用上一步返回值
- GlobalValue - 全局变量配置

**数据驱动测试**
- 模型驱动（model.xml）
- 数据表驱动（data/*.xml）
- GlobalValue全局变量

## 📂 目录结构

```
demo_full/
├── case/           # 测试用例
├── model/          # 模型定义
├── data/           # 测试数据
├── demosite/       # 示例网站
├── fun/            # Python代码
└── result/         # 测试结果
```

## 📋 已知问题

1. Web UI测试需要页面完全加载（约18秒超时）
2. 数据库路径需要相对于项目根目录配置
3. set关键字需要通过代码调用，暂不支持XML直接配置
