# 迭代 00 - 工程基础设施设计

**版本**: v1.0
**日期**: 2026-03-27

## 架构设计

### 质量保证体系架构

```
┌─────────────────────────────────────────────────────────────┐
│                    CI/CD Pipeline                           │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐     │
│  │  Lint   │ → │  Test   │ → │ Coverage│ → │ Report  │     │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘     │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                    Local Development                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ scripts/check.sh (统一入口)                          │   │
│  │  ├── static-check  (静态检查)                        │   │
│  │  ├── unit-test     (单元测试)                        │   │
│  │  ├── coverage      (覆盖率)                          │   │
│  │  └── acceptance    (验收测试)                        │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 模块设计

### 1. 静态检查模块

#### 1.1 目录结构

```
rodski/
├── pyproject.toml      # Black, isort, coverage 配置
├── .flake8             # Flake8 配置
├── mypy.ini            # MyPy 配置
├── bandit.yaml         # Bandit 配置
└── scripts/
    └── check.sh        # 统一检查入口
```

#### 1.2 配置文件

**pyproject.toml**:
```toml
[tool.black]
line-length = 100
target-version = ['py39', 'py310', 'py311', 'py312']

[tool.isort]
profile = "black"
line_length = 100

[tool.coverage.run]
source = ["rodski"]
omit = ["tests/*", "*/__pycache__/*"]

[tool.coverage.report]
fail_under = 80
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
]
```

**.flake8**:
```ini
[flake8]
max-line-length = 100
exclude =
    .git,
    __pycache__,
    venv,
    .venv
ignore = E203, W503
```

#### 1.3 检查脚本

**scripts/check.sh**:
```bash
#!/bin/bash
# RodSki 质量检查统一入口

set -e

case "$1" in
    static|static-check)
        echo "=== 静态检查 ==="
        black --check rodski/
        flake8 rodski/
        mypy rodski/
        bandit -c bandit.yaml -r rodski/
        ;;
    test|unit-test)
        echo "=== 单元测试 ==="
        pytest rodski/tests/unit/ -v
        ;;
    coverage)
        echo "=== 覆盖率检查 ==="
        pytest rodski/tests/ --cov=rodski --cov-report=html --cov-report=term
        ;;
    acceptance)
        echo "=== 验收测试 ==="
        cd rodski-demo/DEMO/demo_full && python ski_run.py case/*.xml
        ;;
    all)
        $0 static
        $0 coverage
        $0 acceptance
        ;;
    *)
        echo "用法: $0 {static|test|coverage|acceptance|all}"
        exit 1
        ;;
esac
```

---

### 2. 测试框架模块

#### 2.1 目录结构

```
rodski/tests/
├── __init__.py
├── conftest.py          # pytest fixtures
├── unit/                # 单元测试
│   ├── test_*.py
│   └── ...
├── integration/         # 集成测试
│   ├── test_*.py
│   └── ...
└── functional/          # 功能测试
    └── ...
```

#### 2.2 pytest 配置

**pytest.ini**:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow running tests
```

---

### 3. CI/CD 模块

#### 3.1 GitHub Actions 工作流

**test.yml**:
```yaml
name: Test

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11', '3.12']

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov

    - name: Run tests
      run: |
        pytest rodski/tests/ --cov=rodski --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v4
      with:
        file: coverage.xml
```

**lint.yml**:
```yaml
name: Lint

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: Install linters
      run: pip install black flake8 mypy bandit

    - name: Run Black
      run: black --check rodski/

    - name: Run Flake8
      run: flake8 rodski/

    - name: Run MyPy
      run: mypy rodski/ --ignore-missing-imports

    - name: Run Bandit
      run: bandit -r rodski/ -ll
```

---

### 4. 验收测试模块

#### 4.1 Demo 项目结构

```
rodski-demo/DEMO/demo_full/
├── README.md            # 使用说明
├── case/                # 测试用例
│   └── *.xml
├── data/                # 测试数据
│   └── *.xml
├── model/               # 页面模型
│   └── model.xml
├── globalvalue.xml      # 全局变量
└── run_test.sh          # 执行脚本
```

#### 4.2 验收测试脚本

**scripts/acceptance.sh**:
```bash
#!/bin/bash
# 验收测试执行脚本

DEMO_DIR="rodski-demo/DEMO/demo_full"

echo "=== 执行验收测试 ==="

# 检查 Demo 目录
if [ ! -d "$DEMO_DIR" ]; then
    echo "错误: Demo 目录不存在"
    exit 1
fi

# 执行测试
cd "$DEMO_DIR"
python ski_run.py case/*.xml --headless

# 检查结果
if [ $? -eq 0 ]; then
    echo "✅ 验收测试通过"
else
    echo "❌ 验收测试失败"
    exit 1
fi
```

---

## 文件清单

### 需要创建的文件

| 文件 | 说明 |
|------|------|
| `rodski/.flake8` | Flake8 配置 |
| `rodski/mypy.ini` | MyPy 配置 |
| `rodski/bandit.yaml` | Bandit 配置 |
| `rodski/scripts/check.sh` | 统一检查脚本 |
| `.github/workflows/test.yml` | 测试工作流 |
| `.github/workflows/lint.yml` | 检查工作流 |

### 需要更新的文件

| 文件 | 更新内容 |
|------|---------|
| `rodski/pyproject.toml` | 添加 coverage 配置 |
| `rodski/pytest.ini` | 优化配置 |
| `rodski/requirements.txt` | 添加开发依赖 |

---

## 执行计划

```
Wave 1: 静态检查配置 (2h)
  └── 创建配置文件，验证工具可用

Wave 2: 测试框架配置 (2h)
  └── 验证 pytest，配置覆盖率

Wave 3: Demo 验证 (2h)
  └── 检查 Demo，执行验收测试

Wave 4: CI/CD 配置 (2h)
  └── 创建工作流，验证 CI 执行
```

**总计**: 8小时

---

**创建日期**: 2026-03-27