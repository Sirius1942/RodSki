# 迭代 00 - 任务列表

**总计**: 11任务, 8小时

---

## Wave 1: 静态检查配置 (3任务, 2h)

### Task 1.1: 配置代码静态检查工具

**工作量**: 45min

**工作内容**:
- [ ] 创建 `rodski/.flake8` 配置
- [ ] 创建 `rodski/mypy.ini` 配置
- [ ] 创建 `rodski/bandit.yaml` 配置
- [ ] 更新 `rodski/pyproject.toml` 添加 Black/isort 配置
- [ ] 验证各工具可执行

**验收标准**:
```
✅ black --check rodski/ 通过
✅ flake8 rodski/ 无错误
✅ mypy rodski/ 通过（允许部分忽略）
✅ bandit -r rodski/ 无高危
```

---

### Task 1.2: 配置文档静态检查

**工作量**: 30min

**工作内容**:
- [ ] 创建 XML Schema 验证脚本
- [ ] 验证所有 XML 文件符合 Schema
- [ ] 创建约束一致性检查脚本

**文件**:
- `rodski/scripts/validate_xml.py`

**验收标准**:
```
✅ 所有 model.xml 通过 model.xsd 验证
✅ 所有 case/*.xml 通过 case.xsd 验证
✅ 所有 data/*.xml 通过 data.xsd 验证
```

---

### Task 1.3: 创建统一检查脚本

**工作量**: 45min

**工作内容**:
- [ ] 创建 `rodski/scripts/check.sh`
- [ ] 实现 static/test/coverage/acceptance 子命令
- [ ] 创建 `rodski/scripts/` 目录（如不存在）
- [ ] 设置执行权限

**验收标准**:
```
✅ ./scripts/check.sh static 执行成功
✅ ./scripts/check.sh test 执行成功
✅ ./scripts/check.sh coverage 生成报告
```

---

## Wave 2: 测试框架配置 (3任务, 2h)

### Task 2.1: 验证单元测试框架

**工作量**: 30min

**工作内容**:
- [ ] 运行 `pytest rodski/tests/` 检查执行情况
- [ ] 修复失败的测试用例
- [ ] 更新 `rodski/pytest.ini` 配置

**验收标准**:
```
✅ pytest 正常发现所有测试
✅ pytest rodski/tests/unit/ 通过率 100%
```

---

### Task 2.2: 配置覆盖率统计

**工作量**: 45min

**工作内容**:
- [ ] 安装 pytest-cov
- [ ] 配置 `pyproject.toml` coverage 部分
- [ ] 执行覆盖率统计
- [ ] 检查当前覆盖率基线

**命令**:
```bash
pytest rodski/tests/ --cov=rodski --cov-report=html --cov-report=term
```

**验收标准**:
```
✅ 覆盖率报告生成到 htmlcov/
✅ 当前覆盖率 ≥ 60%（基线）
✅ 配置 fail_under = 80（目标）
```

---

### Task 2.3: 验证自检能力

**工作量**: 45min

**工作内容**:
- [ ] 检查 `rodski/selftest.py` 存在性
- [ ] 执行 selftest.py
- [ ] 分析自检覆盖范围
- [ ] 补充必要自检用例（如需要）

**验收标准**:
```
✅ python selftest.py 执行成功
✅ 自检覆盖核心功能
```

---

## Wave 3: Demo 和验收测试 (2任务, 2h)

### Task 3.1: 验证 Demo 项目完整性

**工作量**: 1h

**工作内容**:
- [ ] 检查 demo_full 目录结构
- [ ] 验证 XML 文件格式
- [ ] 检查 README.md 完整性
- [ ] 执行 demo_full 测试

**Demo 项目检查清单**:
| 项目 | 检查项 |
|------|--------|
| demo_full | 目录完整、XML有效、README存在 |
| demo_runtime_control | 目录完整、XML有效 |
| vision_web | 目录完整、XML有效 |
| vision_desktop | 目录完整、XML有效 |

**验收标准**:
```
✅ 所有 Demo 目录结构完整
✅ 所有 Demo XML 通过 Schema 验证
✅ demo_full 可执行（如环境允许）
```

---

### Task 3.2: 创建验收测试脚本

**工作量**: 1h

**工作内容**:
- [ ] 创建 `scripts/acceptance.sh`
- [ ] 定义验收测试用例清单
- [ ] 创建验收测试报告模板

**验收标准**:
```
✅ scripts/acceptance.sh 可执行
✅ 验收测试清单明确
```

---

## Wave 4: CI/CD 配置 (3任务, 2h)

### Task 4.1: 创建测试工作流

**工作量**: 45min

**工作内容**:
- [ ] 创建 `.github/workflows/` 目录
- [ ] 创建 `test.yml` 工作流
- [ ] 配置多 Python 版本矩阵
- [ ] 配置覆盖率上传

**文件**: `.github/workflows/test.yml`

**验收标准**:
```
✅ GitHub Actions 识别工作流
✅ 工作流语法正确
```

---

### Task 4.2: 创建检查工作流

**工作量**: 30min

**工作内容**:
- [ ] 创建 `lint.yml` 工作流
- [ ] 配置 Black/Flake8/MyPy/Bandit 检查

**文件**: `.github/workflows/lint.yml`

**验收标准**:
```
✅ GitHub Actions 识别工作流
✅ 工作流语法正确
```

---

### Task 4.3: 验证 CI 流程

**工作量**: 45min

**工作内容**:
- [ ] 提交所有配置文件
- [ ] 推送到远程仓库
- [ ] 检查 GitHub Actions 执行状态
- [ ] 修复 CI 问题（如有）

**验收标准**:
```
✅ GitHub Actions 正常触发
✅ test 工作流执行成功
✅ lint 工作流执行成功
```

---

## 验收检查表

本迭代完成前需确认：

```
□ 静态检查
  □ black --check 通过
  □ flake8 无错误
  □ mypy 通过
  □ bandit 无高危

□ 单元测试
  □ pytest 通过率 100%
  □ 覆盖率 ≥ 60%（基线）

□ Demo 验证
  □ 所有 Demo XML 有效
  □ demo_full README 完整

□ CI/CD
  □ test.yml 创建成功
  □ lint.yml 创建成功
  □ GitHub Actions 执行成功
```

---

**创建日期**: 2026-03-27