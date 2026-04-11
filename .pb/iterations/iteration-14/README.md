# Iteration 14: P0问题修复

**版本**: v4.6.0  
**分支**: release/v4.6.0  
**日期**: 2026-04-09  
**工时**: 3h  
**优先级**: P0

---

## 目标

修复 rodski-demo 项目中的 P0 严重问题：
1. 添加 expect_fail 属性支持负面测试
2. 修复 run_demo.sh 路径错误
3. 补充 tc_expect_fail.xml 缺失内容

---

## 任务清单

### T14-001: 添加 expect_fail 属性 (0.5h)

**文件**: `rodski-demo/DEMO/demo_full/case/demo_case.xml`

**任务**:
- 给 TC012A 添加 `expect_fail="是"`
- 给 TC014A 添加 `expect_fail="是"`
- 验证测试报告正确显示预期失败

**验收**:
- TC012A、TC014A 显示为"预期失败"
- 测试报告统计正确

---

### T14-002: 修复 run_demo.sh 路径 (0.5h)

**文件**: `rodski-demo/DEMO/demo_full/run_demo.sh`

**任务**:
- 修正第 36 行：`product/` → `rodski-demo/`
- 修正第 30 行：确保相对路径正确
- 测试脚本运行

**验收**:
- 脚本可以正确运行
- 路径提示准确
- 可以找到测试报告

---

### T14-003: 补充 tc_expect_fail.xml (2h)

**文件**: 
- `rodski-demo/DEMO/demo_full/model/model.xml`
- `rodski-demo/DEMO/demo_full/data/LoginForm.xml`
- `rodski-demo/DEMO/demo_full/data/ErrorMessage_verify.xml`
- `rodski-demo/DEMO/demo_full/demosite/app.py`

**任务**:
1. 在 model.xml 添加 ErrorMessage 模型
2. 在 LoginForm.xml 添加 L002 错误密码数据
3. 创建 ErrorMessage_verify.xml
4. 扩展 demosite/app.py 支持错误提示

**验收**:
- tc_expect_fail.xml 可以运行
- 错误提示正确显示
- 负面测试通过

---

## 验收标准

- [ ] TC012A、TC014A 正确标记为预期失败
- [ ] run_demo.sh 路径全部正确
- [ ] tc_expect_fail.xml 可以正常运行
- [ ] 所有测试用例通过
- [ ] 测试报告统计准确

---

## 工作流程

1. 创建分支: `git checkout -b release/v4.6.0`
2. 执行 T14-001
3. 执行 T14-002
4. 执行 T14-003
5. 运行回归测试
6. 更新 record.md
7. 合并到 main: `git merge release/v4.6.0`
8. 打标签: `git tag v4.6.0`

---

## 参考文档

- `.pb/iterations/iteration-14-19-plan.md` - 总体规划
- `rodski/docs/TEST_CASE_WRITING_GUIDE.md` - 用例编写指南
