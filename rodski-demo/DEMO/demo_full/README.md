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

## 📝 测试用例（7个）

### ✅ 通过的测试用例 (5/7)

- **TC001: Web登录测试** - navigate + type
- **TC002: 看板数据验证** - verify
- **TC003: 功能测试页操作** - type多控件
- **TC004: API登录接口测试** - send + verify
- **TC005: API查询订单** - send GET请求

### ❌ 框架问题 (2/7)

- **TC006: 数据库查询订单** - DB关键字连接问题
- **TC007: Python代码执行** - run关键字路径问题

## ✅ RodSki能力覆盖

**Web UI测试**
- navigate - 页面导航
- type - UI批量输入（input/button/select）
- verify - 批量验证
- 定位器：id

**API接口测试**
- send - POST/GET请求
- verify - JSON响应验证
- RESTful API

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
