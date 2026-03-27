# 迭代2 - 单元测试增强设计

## 1. 测试架构设计

### 1.1 目录结构

```
rodski/tests/
├── unit/              # 单元测试
├── integration/       # 集成测试
├── functional/        # 功能测试
├── fixtures/          # 测试夹具
├── mocks/            # Mock 对象
└── data/             # 测试数据
```

### 1.2 测试分层

- **L1 单元测试**: 测试单个函数/类，完全隔离
- **L2 集成测试**: 测试模块间交互，部分隔离
- **L3 功能测试**: 测试完整流程，最小隔离

## 2. 测试工具链

### 2.1 核心工具

- **pytest**: 测试框架
- **pytest-cov**: 覆盖率统计
- **pytest-mock**: Mock 支持
- **pytest-xdist**: 并行执行

### 2.2 辅助工具

- **faker**: 测试数据生成
- **responses**: HTTP Mock
- **freezegun**: 时间 Mock


## 3. 测试用例设计模式

### 3.1 AAA 模式

```python
def test_example():
    # Arrange - 准备测试数据
    executor = SKIExecutor()
    case_data = {'case_id': 'TC001', 'step_wait': '500'}
    
    # Act - 执行被测试代码
    result = executor.execute_case(case_data)
    
    # Assert - 验证结果
    assert result['status'] == 'PASS'
```

### 3.2 参数化测试

```python
@pytest.mark.parametrize("input,expected", [
    ("${Return[-1]}", "last_value"),
    ("${Return[0]}", "first_value"),
    ("${Return[-2]}", "second_last_value"),
])
def test_return_reference(input, expected):
    result = resolve_return_reference(input)
    assert result == expected
```

### 3.3 Fixture 复用

```python
@pytest.fixture
def mock_browser():
    browser = Mock()
    yield browser
    browser.close()
```


## 4. 覆盖率目标

### 4.1 模块覆盖率要求

| 模块 | 语句覆盖 | 分支覆盖 | 函数覆盖 |
|------|---------|---------|---------|
| core/ | ≥95% | ≥90% | 100% |
| drivers/ | ≥90% | ≥85% | 100% |
| data/ | ≥95% | ≥90% | 100% |
| keywords/ | ≥90% | ≥85% | 100% |

### 4.2 关键路径

- 用例解析 → 执行 → 结果输出
- 数据加载 → 变量替换 → 关键字执行
- 驱动初始化 → 元素操作 → 资源清理

## 5. Mock 策略

### 5.1 外部依赖 Mock

- 浏览器驱动 → Mock Playwright/Selenium
- 数据库连接 → Mock SQLite/MySQL
- HTTP 请求 → Mock requests
- 文件系统 → Mock 临时目录

### 5.2 Mock 实现示例

```python
@pytest.fixture
def mock_playwright():
    with patch('playwright.sync_api.sync_playwright') as mock:
        yield mock
```


## 6. CI/CD 集成

### 6.1 GitHub Actions 配置

```yaml
name: Unit Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: pytest --cov=rodski --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

### 6.2 测试报告

- HTML 覆盖率报告
- JUnit XML 格式
- 失败用例截图
- 性能基准对比

## 7. 测试数据管理

### 7.1 测试数据原则

- 使用最小化数据集
- 数据可重复生成
- 避免硬编码
- 敏感数据脱敏

### 7.2 数据生成工具

```python
from faker import Faker
fake = Faker('zh_CN')

def generate_test_user():
    return {
        'username': fake.user_name(),
        'phone': fake.phone_number(),
        'email': fake.email()
    }
```

## 8. 实施里程碑

- Week 1-2: 基础设施 + 核心模块
- Week 3-4: 驱动层测试
- Week 5: 集成测试
- Week 6: CI/CD + 文档
