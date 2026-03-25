# 并发执行指南

## 功能说明

ParallelExecutor 支持多个测试用例并行执行，提升大规模测试效率。

## 使用方法

### Python API

```python
from core.parallel_executor import ParallelExecutor
from drivers.playwright_driver import PlaywrightDriver

# 准备用例
cases = [
    {
        "name": "登录测试",
        "steps": [
            {"action": "navigate", "model": "", "data": "https://example.com"},
            {"action": "type", "model": "#username", "data": "admin"},
        ]
    },
    {
        "name": "搜索测试",
        "steps": [
            {"action": "navigate", "model": "", "data": "https://example.com"},
            {"action": "type", "model": "#search", "data": "test"},
        ]
    }
]

# 定义 driver 工厂
def driver_factory():
    return PlaywrightDriver()

# 并发执行（4 线程）
executor = ParallelExecutor(max_workers=4)
results = executor.execute_cases(cases, driver_factory)

# 查看结果
for result in results:
    print(f"{result['case']}: {'✅' if result['success'] else '❌'}")
```

## 注意事项

- 每个线程使用独立的 driver 实例
- 默认并发数为 4，可根据机器性能调整
- 适用于独立的测试用例，不适合有依赖关系的用例

## 性能对比

| 用例数 | 串行耗时 | 并发耗时 (4线程) | 提升 |
|--------|----------|------------------|------|
| 10     | 50s      | 15s              | 3.3x |
| 20     | 100s     | 30s              | 3.3x |
