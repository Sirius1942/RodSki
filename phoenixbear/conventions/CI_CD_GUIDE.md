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
   - `DOCKER_USERNAME`: Docker Hub 用户名
   - `DOCKER_PASSWORD`: Docker Hub 密码

3. **触发工作流**

   - **自动触发**: 推送代码到 main/develop 分支
   - **手动触发**: 在 Actions 页面选择 "Run workflow"
   - **定时触发**: 每天 2:00 AM UTC 自动运行

### 工作流说明

#### 1. ski-test.yml - 测试执行

**功能**:
- 多 Python 版本测试 (3.9-3.13)
- 自动安装 Playwright 浏览器
- 运行 SKI 测试用例
- 上传测试结果和截图

#### 2. ski-lint.yml - 代码质量

**检查项**:
- Black (代码格式化)
- Flake8 (代码规范)
- Pylint (代码质量)
- MyPy (类型检查)
- Bandit (安全检查)

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
  python ski_run.py product/TEST/v1R1C01/case/baidu_search_case.xml --headless

# 使用 docker-compose
docker-compose up ski-runner
```

---

## Jenkins 集成

### Pipeline 示例

创建 `Jenkinsfile`:

```groovy
pipeline {
    agent any
    stages {
        stage('Test') {
            steps {
                sh 'python selftest.py'
            }
        }
        stage('SKI Test') {
            steps {
                sh 'python ski_run.py product/TEST/v1R1C01/case/*.xml --headless'
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

test:
  stage: test
  image: python:3.9
  script:
    - pip install -r requirements.txt
    - playwright install chromium
    - python selftest.py
  artifacts:
    when: always
    paths:
      - screenshots/
      - logs/
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
│   │   └── model/
└── PROD/
```

### 2. 重试机制

```yaml
retry_config:
  max_retries: 3
  retry_delay: 2.0
```

### 3. 失败截图

- SKI 会自动在失败时截图
- 截图保存在 `screenshots/` 目录
- CI/CD 中自动上传截图

---

## 常见问题

### Q1: Playwright 浏览器安装失败

```bash
playwright install-deps
```

### Q2: Docker 容器中无法运行 GUI 测试

```bash
python ski_run.py case.xml --headless
```

### Q3: 测试超时

增加超时时间：
```yaml
execution:
  timeout: 300
  page_timeout: 60
```

---

**文档版本**: v1.0
**更新时间**: 2026-03-20
