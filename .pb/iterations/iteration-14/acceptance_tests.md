# Iteration 14 验收测试

## 测试环境

- Python 版本: 3.8+
- RodSki 版本: v4.6.0
- 测试目录: rodski-demo/DEMO/demo_full/

---

## 功能验收

### AC-001: expect_fail 属性

**测试步骤**:
1. 运行 demo_case.xml
2. 查看测试报告

**预期结果**:
- TC012A 显示为"预期失败"（不是"失败"）
- TC014A 显示为"预期失败"（不是"失败"）
- 测试报告统计正确（预期失败不计入失败数）

**实际结果**: 待测试

---

### AC-002: run_demo.sh 路径

**测试步骤**:
1. 在项目根目录运行: `./rodski-demo/DEMO/demo_full/run_demo.sh`
2. 查看输出信息
3. 检查是否找到测试报告

**预期结果**:
- 脚本正常运行
- 路径提示正确
- 可以找到测试报告文件

**实际结果**: 待测试

---

### AC-003: tc_expect_fail.xml

**测试步骤**:
1. 启动 demosite: `cd rodski-demo/DEMO/demo_full/demosite && python app.py`
2. 运行测试: `python rodski/ski_run.py rodski-demo/DEMO/demo_full/case/tc_expect_fail.xml`
3. 查看测试结果

**预期结果**:
- 测试可以运行
- 登录失败时显示错误提示
- 错误消息验证通过
- 测试标记为"预期失败"

**实际结果**: 待测试

---

## 回归测试

### RT-001: 所有现有测试用例

**测试步骤**:
1. 运行 demo_case.xml
2. 运行 tc015_only.xml
3. 运行 tc_expect_fail.xml

**预期结果**:
- 所有正向用例通过
- 所有负向用例标记为预期失败
- 无回归问题

**实际结果**: 待测试

---

## 验收检查清单

- [ ] AC-001: expect_fail 属性测试通过
- [ ] AC-002: run_demo.sh 路径测试通过
- [ ] AC-003: tc_expect_fail.xml 测试通过
- [ ] RT-001: 回归测试通过
- [ ] 文档已更新
- [ ] record.md 已记录

---

## 测试报告

**测试日期**: 待填写  
**测试人员**: 待填写  
**测试结果**: 待填写

### 问题记录

| 问题ID | 描述 | 严重程度 | 状态 |
|--------|------|----------|------|
| - | - | - | - |

### 总结

待填写
