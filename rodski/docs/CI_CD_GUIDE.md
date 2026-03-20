# CI/CD 集成指南

本文档介绍如何将 RodSki 测试框架集成到 CI/CD 流程中。

## 目录

1. [GitHub Actions 集成](#github-actions-集成)
2. [Docker 使用](#docker-使用)
3. [Jenkins 集成](#jenkins-集成)
4. [GitLab CI 集成](#gitlab-ci-集成)
5. [最佳实践](#最佳实践)

---

## GitHub Actions 集成

### 快速开始

1. **复制工作流模板**

   ```bash
   mkdir -p .github/workflows
   cp .github/workflows/ski-test.yml .github/workflows/
   ```

2. **配置仓库密钥（可选）**

   在 GitHub 仓库设置中添加以下密钥：
   - `CODECOV_TOKEN`: Codecov 集成令牌
   - `DOCKER_USERNAME`: Docker Hub 用户名
   - `DOCKER_PASSWORD`: Docker Hub 密码

3. **触发工作流**

   - **自动触发**: 推送代码到 main/develop 分支
   - **手动触发**: 在 Actions 页面选择 "Run workflow"
   - **定时触发**: 每天 2:00 AM UTC 自动运行

### 工作流说明

#### 1. ski-test.yml - 测试执行

**功能**:
- 多 Python 版本测试 (3.8-3.12)
- 自动安装 Playwright 浏览器
- 运行单元测试和 SKI 测试用例
- 生成覆盖率报告
- 上传测试结果和截图

**配置**:
```yaml
# 修改测试文件路径
workflow_dispatch:
  inputs:
    test_file:
      default: 'product/TEST/v1R1C01/case/baidu_search_case.xlsx'
```

#### 2. ski-lint.yml - 代码质量

**检查项**:
- Black (代码格式化)
- Flake8 (代码规范)
- Pylint (代码质量)
- MyPy (类型检查)
- Bandit (安全检查)
- Safety (依赖安全)

#### 3. ski-release.yml - 自动发布

**触发条件**: 推送 tag (v*.*.*)

**功能**:
- 自动运行测试
- 构建 Python 包
- 创建 GitHub Release
- 构建 Docker 镜像

---

## Docker 使用

### 构建镜像

```bash
# 构建镜像
docker build -t rodski:latest .

# 使用特定版本
docker build -t rodski:v1.2.3 .
```

### 运行测试

```bash
# 运行单个测试用例
docker run --rm \
  -v $(pwd)/product:/app/product \
  -v $(pwd)/reports:/app/reports \
  rodski:latest \
  python ski_run.py product/TEST/v1R1C01/case/baidu_search_case.xlsx --headless

# 使用 docker-compose
docker-compose up ski-runner
```

### Docker Compose 服务

```bash
# 启动所有服务
docker-compose up -d

# 启动特定服务
docker-compose up -d ski-runner selenium-hub

# 查看日志
docker-compose logs -f ski-runner

# 停止服务
docker-compose down
```

**可用服务**:
- `ski-runner`: SKI 测试执行器
- `selenium-hub`: Selenium Grid Hub
- `chrome`: Chrome 浏览器节点
- `firefox`: Firefox 浏览器节点
- `allure`: Allure 报告服务

---

## Jenkins 集成

### Pipeline 示例

创建 `Jenkinsfile`:

```groovy
pipeline {
    agent any
    
    environment {
        PYTHON_VERSION = '3.12'
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Setup') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install -r requirements.txt
                    playwright install chromium
                '''
            }
        }
        
        stage('Lint') {
            steps {
                sh '''
                    . venv/bin/activate
                    pip install flake8 pylint black
                    black --check .
                    flake8 . --max-line-length=127
                '''
            }
        }
        
        stage('Test') {
            steps {
                sh '''
                    . venv/bin/activate
                    python run_tests.py
                '''
            }
            post {
                always {
                    junit 'test-results/*.xml'
                    archiveArtifacts artifacts: 'screenshots/*.png', allowEmptyArchive: true
                }
            }
        }
        
        stage('Run SKI Tests') {
            steps {
                sh '''
                    . venv/bin/activate
                    python ski_run.py product/TEST/v1R1C01/case/*.xlsx --headless
                '''
            }
        }
        
        stage('Report') {
            steps {
                publishHTML([
                    allowMissing: false,
                    alwaysLinkToLastBuild: true,
                    keepAll: true,
                    reportDir: 'htmlcov',
                    reportFiles: 'index.html',
                    reportName: 'Coverage Report'
                ])
            }
        }
    }
    
    post {
        always {
            cleanWs()
        }
    }
}
```

### Jenkins Docker Agent

```groovy
pipeline {
    agent {
        docker {
            image 'rodski:latest'
            args '-v /tmp:/tmp'
        }
    }
    
    stages {
        stage('Test') {
            steps {
                sh 'python run_tests.py'
            }
        }
    }
}
```

---

## GitLab CI 集成

创建 `.gitlab-ci.yml`:

```yaml
stages:
  - lint
  - test
  - report

variables:
  PYTHON_VERSION: "3.12"

lint:
  stage: lint
  image: python:${PYTHON_VERSION}
  script:
    - pip install flake8 black
    - black --check .
    - flake8 . --max-line-length=127
  allow_failure: true

test:
  stage: test
  image: python:${PYTHON_VERSION}
  script:
    - pip install -r requirements.txt
    - playwright install chromium
    - playwright install-deps chromium
    - python run_tests.py
  artifacts:
    when: always
    paths:
      - htmlcov/
      - screenshots/
      - logs/
    expire_in: 30 days

ski-test:
  stage: test
  image: rodski:latest
  script:
    - python ski_run.py product/TEST/v1R1C01/case/*.xlsx --headless
  artifacts:
    when: always
    paths:
      - reports/
      - screenshots/
    expire_in: 30 days

coverage:
  stage: report
  image: python:${PYTHON_VERSION}
  script:
    - pip install coverage
    - coverage report
    - coverage html
  coverage: '/TOTAL.+ ([0-9]{1,3}%)/'
  artifacts:
    paths:
      - htmlcov/
    expire_in: 30 days
```

---

## 最佳实践

### 1. 测试用例组织

```
product/
├── TEST/
│   ├── v1R1C01/
│   │   ├── case/
│   │   │   ├── smoke_test.xlsx        # 冒烟测试
│   │   │   ├── regression_test.xlsx   # 回归测试
│   │   │   └── integration_test.xlsx  # 集成测试
│   │   └── model/
│   │       └── model.xml
│   └── v1R1C02/
│       └── ...
└── PROD/
    └── ...
```

### 2. CI/CD 流程建议

**提交阶段 (Commit Stage)**:
- 运行快速冒烟测试
- 代码质量检查
- 单元测试

**测试阶段 (Test Stage)**:
- 运行完整回归测试
- 生成覆盖率报告
- 上传测试结果

**部署阶段 (Deploy Stage)**:
- 仅在测试通过后部署
- 生产环境运行冒烟测试

### 3. 性能优化

**并行执行**:
```bash
# 多个测试文件并行
python ski_run.py case1.xlsx case2.xlsx case3.xlsx --parallel 3
```

**缓存依赖**:
```yaml
# GitHub Actions 缓存
- uses: actions/cache@v3
  with:
    path: |
      ~/.cache/pip
      ~/.cache/ms-playwright
    key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
```

### 4. 失败处理

**重试机制**:
```yaml
# 在 SKI 配置中启用重试
retry_config:
  max_retries: 3
  retry_delay: 2.0
  retry_on_errors:
    - ElementNotFound
    - Timeout
```

**失败截图**:
- SKI 会自动在失败时截图
- 截图保存在 `screenshots/` 目录
- CI/CD 中自动上传截图

### 5. 报告和通知

**Allure 报告**:
```bash
# 生成 Allure 报告
allure generate reports/allure-results -o reports/allure-report

# 启动报告服务器
allure open reports/allure-report
```

**通知配置**:
```yaml
# GitHub Actions 通知
- name: Send notification
  if: failure()
  uses: 8398a7/action-slack@v3
  with:
    status: failure
    fields: repo,message,commit,author,action
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

### 6. 安全建议

**密钥管理**:
- 使用 CI/CD 平台的密钥管理功能
- 不要在代码中硬编码敏感信息
- 定期轮换访问令牌

**权限控制**:
- 限制 CI/CD 流程的访问权限
- 使用最小权限原则
- 审计 CI/CD 操作日志

### 7. 监控和日志

**日志级别配置**:
```yaml
# config.yaml
logging:
  level: INFO
  format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  file: logs/ski.log
```

**监控指标**:
- 测试通过率
- 平均执行时间
- 失败用例数量
- 覆盖率趋势

---

## 常见问题

### Q1: Playwright 浏览器安装失败

**解决方案**:
```bash
# 手动安装浏览器依赖
apt-get update && apt-get install -y libnss3 libnspr4 libatk1.0-0

# 使用系统浏览器
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
playwright install-deps
```

### Q2: Docker 容器中无法运行 GUI 测试

**解决方案**:
```bash
# 使用 headless 模式
python ski_run.py case.xlsx --headless

# 或使用 Xvfb
xvfb-run python ski_run.py case.xlsx
```

### Q3: 测试超时

**解决方案**:
```yaml
# 增加超时时间
execution:
  timeout: 300  # 5分钟
  page_timeout: 60  # 1分钟
```

---

## 总结

RodSki 框架提供了完整的 CI/CD 集成支持：

✅ **GitHub Actions**: 开箱即用的工作流模板
✅ **Docker**: 容器化测试环境
✅ **Jenkins**: 企业级 CI/CD 集成
✅ **GitLab CI**: GitLab 原生支持
✅ **最佳实践**: 完整的实施指南

**推荐配置**:
- 小型项目: GitHub Actions + Docker
- 中型项目: Jenkins + Selenium Grid
- 大型项目: GitLab CI + Kubernetes

**下一步**:
1. 选择适合的 CI/CD 平台
2. 复制对应的配置文件
3. 根据项目需求调整配置
4. 运行首次测试验证

---

**文档版本**: v1.0  
**更新时间**: 2026-03-20  
**维护者**: 热破 (Hot Rod) 🏎️
