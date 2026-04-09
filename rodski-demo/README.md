# RodSki Demo - 快速开始

RodSki 关键字驱动测试框架的完整演示项目，包含 Web 应用和测试用例。

## 前置条件

- Python 3.8+
- pip 安装依赖:
  ```bash
  pip install fastapi uvicorn python-multipart
  pip install playwright
  playwright install chromium
  ```

## 启动 demosite

```bash
# 进入 demo 目录
cd rodski-demo

# 初始化数据库
python3 init_db.py

# 启动 Web 服务（默认端口 8000）
python3 -m uvicorn demosite.app:app --host 0.0.0.0 --port 8000

# 或使用 run_demo.py
python3 run_demo.py --start-server
```

浏览器打开 http://localhost:8000 即可访问。

登录账号: admin / 123456

## 运行测试

```bash
# 方式一: 使用 run_demo.sh（Linux/Mac）
./run_demo.sh

# 方式二: 使用 run_demo.py（跨平台）
python3 run_demo.py

# 方式三: 直接调用 ski_run
cd <项目根目录>
python3 rodski/ski_run.py rodski-demo/case/demo_case.xml
```

## 目录结构

```
rodski-demo/
├── demosite/               # Web 应用
│   ├── app.py              # FastAPI 后端
│   ├── index.html          # 主页 SPA（登录、仪表盘、功能测试）
│   ├── upload.html          # 文件上传测试页
│   ├── locator_test.html    # 定位器测试页
│   ├── multi_window.html    # 多窗口测试页
│   ├── popup.html           # 弹出窗口
│   ├── iframe_test.html     # iframe 测试页
│   └── iframe_content.html  # iframe 内嵌内容页
├── case/                   # 测试用例（XML）
├── data/                   # 测试数据
│   └── globalvalue.xml     # 全局变量配置
├── model/                  # 页面模型
├── result/                 # 测试结果输出
├── fun/                    # 自定义函数
├── init_db.py              # 数据库初始化脚本
├── init_db.sql             # 数据库 DDL + 初始数据
├── run_demo.sh             # Linux/Mac 启动脚本
├── run_demo.py             # 跨平台启动脚本
└── README.md               # 本文件
```

## 测试页面

| 页面 | URL | 用途 |
|------|-----|------|
| 主页 SPA | / | 登录、仪表盘、表单、文本操作、UI 动作 |
| 文件上传 | /upload | 文件上传测试 |
| 定位器测试 | /locator-test | ID/Class/CSS/XPath/Name/Tag/Text 定位 |
| 多窗口 | /multi-window | 多窗口切换测试 |
| iframe | /iframe-test | iframe 内外元素操作 |

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| /api/login | POST | 登录验证（admin/123456） |
| /api/orders | GET | 获取订单列表 |
| /api/upload | POST | 文件上传 |
