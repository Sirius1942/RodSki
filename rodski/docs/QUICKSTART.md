# RodSki 快速入门指南 ⚡

5 分钟快速上手 SKI 自动化测试框架。

## 1️⃣ 安装（1分钟）

```bash
# 克隆项目
git clone <repo-url>
cd rodski

# 安装依赖
pip install -r requirements.txt

# 安装浏览器驱动
playwright install chromium
```

## 2️⃣ 第一个测试（2分钟）

### 方式一：使用 GUI（推荐新手）

```bash
python3 ski_gui.py
```

1. 点击"选择用例文件" → 选择 `examples/demo_case.xlsx`
2. 点击"开始执行"
3. 查看实时日志和结果

### 方式二：使用 CLI

```bash
python3 cli_main.py run examples/demo_case.xlsx
```

## 3️⃣ 创建自己的测试（2分钟）

### Excel 用例格式

| 用例ID | 用例名称 | 前置条件 | 测试步骤 | 后置条件 |
|--------|----------|----------|----------|----------|
| TC001  | 登录测试 | navigate\|https://example.com | type\|#username\|admin<br>type\|#password\|123456<br>click\|#login | screenshot\|login_result |

### 支持的关键字

**Web 操作**：
- `click|locator` - 点击元素
- `type|locator|text` - 输入文本
- `navigate|url` - 打开网页
- `screenshot|filename` - 截图

**API 测试**：
- `http_get|url` - GET 请求
- `http_post|url|body` - POST 请求
- `assert_status|200` - 断言状态码
- `assert_json|$.data.name|expected` - 断言 JSON

**完整列表**：查看 `docs/API_TESTING_GUIDE.md`

## 4️⃣ 查看结果

### HTML 报告
```bash
python3 cli_main.py report --format html
```
打开 `logs/report.html` 查看详细报告。

### JSON 报告
```bash
python3 cli_main.py report --format json
```

## 📚 进阶学习

- **API 测试**：`docs/API_TESTING_GUIDE.md`
- **移动端测试**：`docs/MOBILE_GUIDE.md`
- **GUI 使用**：`docs/GUI_USAGE.md`
- **性能优化**：`docs/PERFORMANCE.md`

## 🆘 常见问题

### Q: 浏览器启动失败？
```bash
playwright install chromium --force
```

### Q: 找不到元素？
使用浏览器开发者工具（F12）检查元素的 CSS 选择器或 XPath。

### Q: 如何调试？
```bash
python3 cli_main.py run examples/demo_case.xlsx --verbose
```

## 🎯 示例项目

- `examples/baidu_test/` - 百度搜索测试
- `examples/api_test/` - RESTful API 测试
- `examples/demo_case.xlsx` - 综合示例

---

**下一步**：尝试修改 `examples/demo_case.xlsx`，创建你的第一个自动化测试！
