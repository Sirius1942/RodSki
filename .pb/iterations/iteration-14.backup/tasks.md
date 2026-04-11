# Iteration 14: rodski-demo 问题修复 — 任务清单

## 阶段一: P0 严重问题修复

### T14-001: 添加 expect_fail 属性
**文件**: `rodski-demo/DEMO/demo_full/case/demo_case.xml`

- 给 TC012A（get不存在key报错测试）添加 `expect_fail="是"`
- 给 TC014A（type Auto Capture失败测试）添加 `expect_fail="是"`
- 验证测试报告正确显示预期失败

**预计**: 0.5h | **Owner**: 待分配

---

### T14-002: 修复 run_demo.sh 路径错误
**文件**: `rodski-demo/DEMO/demo_full/run_demo.sh`

- 修正第 36 行路径：`product/DEMO/demo_full/result/` → `rodski-demo/DEMO/demo_full/result/`
- 修正第 30 行路径：确保相对路径正确
- 测试脚本在不同目录下运行

**预计**: 0.5h | **Owner**: 待分配

---

### T14-003: 补充 tc_expect_fail.xml 缺失内容
**文件**: 
- `rodski-demo/DEMO/demo_full/model/model.xml`
- `rodski-demo/DEMO/demo_full/data/LoginForm.xml`
- `rodski-demo/DEMO/demo_full/data/ErrorMessage_verify.xml`
- `rodski-demo/DEMO/demo_full/demosite/app.py`

- 在 model.xml 中添加 ErrorMessage 模型定义
- 在 LoginForm.xml 中添加 L002 数据行（错误密码）
- 创建 ErrorMessage_verify.xml 验证数据
- 扩展 demosite/app.py，支持错误提示显示

**预计**: 2h | **Owner**: 待分配

---

## 阶段二: P1 重要问题优化

### T14-004: 清理 data 目录冗余文件
**文件**: `rodski-demo/DEMO/demo_full/data/`

- 分析文件引用关系，识别未使用文件
- 统一命名规范（模型名.xml / 模型名_verify.xml）
- 合并重复文件
- 创建 data/README.md 说明文件组织

**预计**: 2h | **Owner**: 待分配

---

### T14-005: 更新 README 文档
**文件**: `rodski-demo/DEMO/demo_full/README.md`

- 更新功能说明（补充 expect_fail、Auto Capture、结构化日志）
- 修正路径引用（统一使用 rodski-demo/ 前缀）
- 更新测试用例统计
- 删除过时说明

**预计**: 1h | **Owner**: 待分配

---

### T14-006: 添加 Python 运行脚本
**文件**: `rodski-demo/DEMO/demo_full/run_demo.py`

- 创建跨平台 Python 运行脚本
- 支持参数：--case, --log-level, --init-db
- 提供友好的输出和错误提示
- 与 run_demo.sh 功能一致

**预计**: 1.5h | **Owner**: 待分配

---

## 阶段三: 验证与文档

### T14-007: 完整回归测试
**文件**: 所有测试用例

- 运行所有测试用例
- 验证修复效果
- 检查测试报告
- 确认无回归问题

**预计**: 1h | **Owner**: 待分配

---

### T14-008: 更新迭代文档
**文件**: `.pb/iterations/iteration-14/record.md`

- 记录所有修改内容
- 记录遇到的问题和解决方案
- 记录验收测试结果
- 总结经验教训

**预计**: 0.5h | **Owner**: 待分配

---

## 任务汇总

| 任务 | 名称 | 预计 | 阶段 | 优先级 |
|------|------|------|------|--------|
| T14-001 | 添加 expect_fail 属性 | 0.5h | 1 | P0 |
| T14-002 | 修复 run_demo.sh 路径 | 0.5h | 1 | P0 |
| T14-003 | 补充 tc_expect_fail.xml | 2h | 1 | P0 |
| T14-004 | 清理 data 目录 | 2h | 2 | P1 |
| T14-005 | 更新 README 文档 | 1h | 2 | P1 |
| T14-006 | 添加 Python 运行脚本 | 1.5h | 2 | P1 |
| T14-007 | 完整回归测试 | 1h | 3 | P0 |
| T14-008 | 更新迭代文档 | 0.5h | 3 | P1 |

**总预计**: 9h
