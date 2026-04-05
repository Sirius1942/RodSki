# CI/CD 集成指南

本文档介绍如何将 RodSki 测试框架集成到 CI/CD 流程中。

## 目录

1. [GitHub Actions 集成](#github-actions-集成)
2. [Jenkins 集成](#jenkins-集成)
3. [GitLab CI 集成](#gitlab-ci-集成)
4. [最佳实践](#最佳实践)

---

## GitHub Actions 集成

### 快速开始

1. **复制工作流模板**

   ```bash
   mkdir -p .github/workflows
   cp .github/workflows/ski-test.yml .github/workflows/
   ```

2. **触发工作流**

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

### Q2: CI 环境中无法运行 GUI 测试

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
