# 迭代 00 - 工程基础设施验证

**版本**: v1.0
**日期**: 2026-03-27
**类型**: 基础设施准备
**状态**: 📋 规划中

## 目标

在正式功能迭代前，验证和准备项目工程基础设施，确保后续迭代的质量保证体系完备。

## 背景

RodSki 项目需要建立完整的质量保证体系，包括：
- 静态代码检查
- 单元测试和覆盖率
- 验收测试用例
- CI/CD 自动化流水线

本迭代不涉及功能开发，仅验证和完善基础设施。

---

## 功能需求

### 1. 静态检查能力

#### 1.1 代码静态检查

**检查项**：
| 检查类型 | 工具 | 配置文件 | 说明 |
|---------|------|---------|------|
| 代码格式 | Black | `pyproject.toml` | 统一代码风格 |
| 规范检查 | Flake8 | `.flake8` | PEP8 规范 |
| 类型检查 | MyPy | `mypy.ini` | 静态类型分析 |
| 安全检查 | Bandit | `bandit.yaml` | 安全漏洞扫描 |
| 导入检查 | isort | `pyproject.toml` | 导入排序 |

**验收标准**：
```
✅ 所有 Python 文件通过 Black 格式化
✅ Flake8 检查无错误（警告 < 10个）
✅ MyPy 类型检查通过率 ≥ 90%
✅ Bandit 无高危漏洞
```

#### 1.2 文档静态检查

**检查项**：
| 检查类型 | 说明 | 工具 |
|---------|------|------|
| XML 格式 | 验证 XML 文件格式正确 | xmllint |
| Schema 验证 | 验证 XML 符合 XSD 定义 | xmlschema |
| Markdown 格式 | 验证 Markdown 语法 | markdownlint |
| 文档一致性 | 检查文档与代码约束一致 | 自定义脚本 |

**验收标准**：
```
✅ 所有 XML 文件通过 Schema 验证
✅ 核心设计约束与代码实现一致
✅ 用户指南示例可执行
```

#### 1.3 核心约束验证

**检查项**：
- 关键字列表与 `keyword_engine.py` 一致
- 定位器类型与 `model.xsd` 一致
- 文档示例与代码行为一致

---

### 2. 动态测试能力

#### 2.1 单元测试框架

**当前状态**：
- 测试框架：pytest
- 配置文件：`rodski/pytest.ini`
- 测试目录：`rodski/tests/unit/`, `rodski/tests/integration/`

**检查项**：
| 检查项 | 说明 | 目标 |
|-------|------|------|
| 测试发现 | pytest 能发现所有测试 | 100% |
| 测试执行 | 所有测试能正常运行 | 通过率 ≥ 95% |
| 覆盖率 | 代码覆盖率统计 | ≥ 80% |

**验收标准**：
```
✅ pytest 正常发现和执行测试
✅ 单元测试通过率 = 100%
✅ 代码覆盖率 ≥ 80%
✅ 覆盖率报告正常生成
```

#### 2.2 测试覆盖率配置

**配置要求**：
```ini
# pytest.ini 或 pyproject.toml
[tool.pytest.ini_options]
addopts = --cov=rodski --cov-report=html --cov-report=term

[tool.coverage.run]
source = rodski
omit = tests/*, */__pycache__/*

[tool.coverage.report]
fail_under = 80
```

#### 2.3 自检能力验证

**检查项**：
- `selftest.py` 能正常运行
- 自检覆盖核心功能
- 自检结果可读

---

### 3. 验收测试准备

#### 3.1 Demo 项目检查

**Demo 项目清单**：
| 项目 | 位置 | 用途 |
|------|------|------|
| demo_full | `rodski-demo/DEMO/demo_full/` | 完整功能演示 |
| demo_runtime_control | `rodski-demo/DEMO/demo_runtime_control/` | 运行时控制演示 |
| vision_web | `rodski-demo/DEMO/vision_web/` | 视觉定位Web演示 |
| vision_desktop | `rodski-demo/DEMO/vision_desktop/` | 视觉定位桌面演示 |

**检查项**：
- 每个 Demo 有独立的 README.md
- 每个 Demo 能独立运行
- 每个 Demo 的 XML 符合 Schema

**验收标准**：
```
✅ demo_full 完整执行通过
✅ 所有 Demo XML 通过 Schema 验证
✅ Demo 文档描述准确
```

#### 3.2 验收测试用例

**用例清单**：
| 用例ID | 场景 | 预期结果 |
|--------|------|---------|
| AT-001 | Web UI 登录流程 | 登录成功 |
| AT-002 | 接口请求响应 | 状态码 200 |
| AT-003 | 数据验证 | 验证通过 |
| AT-004 | 视觉定位 | 元素定位成功 |

---

### 4. CI/CD 环境准备

#### 4.1 GitHub Actions 配置

**工作流清单**：
| 工作流 | 文件 | 触发条件 |
|--------|------|---------|
| 测试流水线 | `.github/workflows/test.yml` | push/PR |
| 代码检查 | `.github/workflows/lint.yml` | push/PR |
| 发布流水线 | `.github/workflows/release.yml` | tag |

**检查项**：
- workflows 目录存在
- 配置文件语法正确
- 能被 GitHub 识别

#### 4.2 CI 流程验证

**验证步骤**：
1. 提交测试代码触发 CI
2. 检查 CI 执行状态
3. 验证测试结果报告
4. 验证覆盖率报告上传

**验收标准**：
```
✅ GitHub Actions 正常触发
✅ 测试流水线执行成功
✅ 代码检查流水线执行成功
✅ 结果报告可访问
```

---

### 5. 过程监控

#### 5.1 监控指标

| 指标 | 说明 | 目标 |
|------|------|------|
| 测试通过率 | 通过/总数 | 100% |
| 代码覆盖率 | 覆盖行/总行 | ≥ 80% |
| 静态检查通过率 | 通过文件/总文件 | 100% |
| 文档一致性 | 一致项/检查项 | 100% |

#### 5.2 报告输出

**报告清单**：
- 测试报告：`reports/test-report.html`
- 覆盖率报告：`reports/coverage/`
- 静态检查报告：`reports/lint-report.txt`

---

## 非功能需求

### 1. 执行效率
- 静态检查执行时间 < 30秒
- 单元测试执行时间 < 60秒
- 完整 CI 流程 < 5分钟

### 2. 可维护性
- 配置文件集中管理
- 检查脚本可独立执行
- 报告格式统一

### 3. 兼容性
- 支持 Python 3.9-3.13
- 支持 macOS / Linux / Windows

---

## 任务分解

### Wave 1: 静态检查配置（3任务, 2h）

**Task 1.1**: 配置代码静态检查工具
- Black, Flake8, MyPy, Bandit 配置
- 创建配置文件
- 验证工具可用

**Task 1.2**: 配置文档静态检查
- XML Schema 验证脚本
- Markdown 检查配置
- 约束一致性检查脚本

**Task 1.3**: 创建检查执行脚本
- 统一入口脚本 `scripts/check.sh`
- 输出检查报告

### Wave 2: 测试框架配置（3任务, 2h）

**Task 2.1**: 验证单元测试框架
- pytest 配置验证
- 测试发现验证
- 修复失败的测试

**Task 2.2**: 配置覆盖率统计
- pytest-cov 配置
- 覆盖率报告生成
- 覆盖率阈值设置

**Task 2.3**: 验证自检能力
- selftest.py 验证
- 补充自检用例

### Wave 3: Demo 和验收测试（2任务, 2h）

**Task 3.1**: 验证 Demo 项目
- 检查 Demo 完整性
- 执行 demo_full
- 修复问题

**Task 3.2**: 创建验收测试脚本
- 验收测试执行脚本
- 结果验证

### Wave 4: CI/CD 配置（3任务, 2h）

**Task 4.1**: 创建 GitHub Actions 工作流
- test.yml 创建
- lint.yml 创建

**Task 4.2**: 验证 CI 流程
- 提交测试代码
- 检查 CI 执行

**Task 4.3**: 配置监控和报告
- 报告输出配置
- 监控指标收集

---

## 验收标准

本迭代完成的标志：

```
✅ 静态检查脚本可执行，通过率 100%
✅ 单元测试通过率 100%，覆盖率 ≥ 80%
✅ demo_full 验收测试通过
✅ GitHub Actions CI 流程正常
✅ 所有报告正常生成
```

---

## 参考文档

- #[[file:../../conventions/PROJECT_CONSTRAINTS.md]]
- #[[file:../../conventions/GIT_WORKFLOW.md]]
- #[[file:../../conventions/CI_CD_GUIDE.md]]

---

**创建日期**: 2026-03-27