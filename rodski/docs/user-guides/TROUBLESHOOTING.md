# RodSki 故障排查指南

## 常见问题

### 1. 安装问题

**问题**: `playwright install` 失败
```bash
# 解决方案：指定浏览器
playwright install chromium
```

**问题**: PyQt6 安装失败
```bash
# macOS
brew install qt6
pip install PyQt6

# Linux
sudo apt-get install python3-pyqt6
```

### 2. 运行问题

**问题**: GUI 无法启动
```bash
# 检查依赖
python3 -c "import PyQt6; print('OK')"

# 使用 CLI 模式
python3 cli_main.py run examples/demo_case.xlsx
```

**问题**: 浏览器驱动失败
```bash
# 重新安装 Playwright
playwright install --force chromium
```

### 3. 测试执行问题

**问题**: 元素定位失败
- 检查 locator 语法（CSS/XPath）
- 增加等待时间
- 使用 `screenshot` 关键字调试

**问题**: 并发执行冲突
- 确保测试用例独立
- 避免共享状态
- 使用不同的测试数据

### 4. 性能问题

**问题**: 执行速度慢
```python
# 启用 headless 模式
driver = PlaywrightDriver(headless=True)

# 减少等待时间
# 优化元素定位策略
```

### 5. API 测试问题

**问题**: HTTP 请求超时
```python
# 增加超时时间
rest_helper = RestHelper(timeout=30)
```

**问题**: JSON 断言失败
- 检查 JSON 路径语法
- 使用 `print()` 调试响应内容

## 日志分析

### 查看详细日志
```bash
# 日志位置
logs/ski_YYYYMMDD_HHMMSS.log

# 实时查看
tail -f logs/ski_*.log
```

### 日志级别
- DEBUG: 详细调试信息
- INFO: 一般信息
- WARNING: 警告
- ERROR: 错误

## 获取帮助

1. 查看文档：[文档首页](../README.md)（索引）
2. 运行示例：`examples/`
3. 查看测试：`tests/`
4. 提交 Issue

## 调试技巧

### 1. 使用 screenshot
```python
# 在关键步骤截图
screenshot(path="debug_step1.png")
```

### 2. 启用详细日志
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 3. 单步调试
```python
# 在 GUI 中使用暂停功能
# 或在代码中添加断点
import pdb; pdb.set_trace()
```

### 4. 性能分析
```python
from core.performance import monitor_performance

@monitor_performance
def my_test():
    # 测试代码
    pass
```

---

**更新时间**: 2026-03-17
