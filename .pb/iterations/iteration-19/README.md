# Iteration 19: 复杂引用 + 负面测试 + 文档

**版本**: v4.11.0  
**分支**: release/v4.11.0  
**日期**: 2026-04-09  
**工时**: 5.5h  
**优先级**: P1  
**前置依赖**: iteration-18

---

## 目标

完成最后的功能补充和文档更新：
1. 创建 TC021 复杂数据引用测试
2. 创建 TC022-024 负面测试集合
3. 更新文档
4. 完整回归测试

---

## 任务清单

### T19-001: TC021 复杂数据引用测试 (1.5h)

**文件**: 
- `rodski-demo/DEMO/demo_full/case/tc021_data_ref.xml`
- `rodski-demo/DEMO/demo_full/model/model.xml`
- `rodski-demo/DEMO/demo_full/data/DataRefTest.xml`
- `rodski-demo/DEMO/demo_full/data/DataRefTest_verify.xml`

**任务**:
创建测试用例 TC021，覆盖：
- GlobalValue 引用
- Return 嵌套引用
- 命名变量访问
- 复杂数据路径

**验收**:
- GlobalValue 引用正确
- Return 嵌套引用正确
- 命名变量读写正确
- 验证通过

---

### T19-002: TC022-024 负面测试集合 (1.5h)

**文件**: 
- `rodski-demo/DEMO/demo_full/case/tc022_negative.xml`
- `rodski-demo/DEMO/demo_full/model/model.xml`
- `rodski-demo/DEMO/demo_full/data/ErrorTest.xml`

**任务**:
1. TC022: 元素不存在测试 (expect_fail="是")
2. TC023: 接口错误响应测试 (expect_fail="是")
3. TC024: SQL 语法错误测试 (expect_fail="是")

**验收**:
- 所有负面用例正确标记 expect_fail
- 测试报告显示为预期失败
- 不影响整体测试结果

---

### T19-003: 更新文档 (1.5h)

**文件**: 
- `rodski-demo/DEMO/demo_full/README.md`
- `rodski-demo/DEMO/demo_full/COVERAGE.md` (新建)

**任务**:
1. 更新 README.md
   - 补充新增测试用例说明
   - 更新功能覆盖矩阵
   - 更新运行说明

2. 创建 COVERAGE.md
   - 功能覆盖详细说明
   - 关键字覆盖矩阵
   - 定位器覆盖矩阵
   - 高级特性覆盖矩阵

**验收**:
- README 内容完整
- COVERAGE.md 详细准确
- 功能覆盖率达到 90%+

---

### T19-004: 完整回归测试 (1h)

**文件**: 所有测试用例

**任务**:
1. 运行所有现有测试用例（TC001-TC015）
2. 运行所有新增测试用例（TC016-TC024）
3. 验证功能覆盖率
4. 检查测试报告

**验收**:
- 所有正向用例通过
- 所有负向用例正确标记
- 功能覆盖率达到 90%+
- 无回归问题

---

## 验收标准

- [ ] TC021 数据引用正确
- [ ] TC022-024 负面测试通过
- [ ] 功能覆盖率达到 90%+
- [ ] 文档完整
- [ ] 所有测试用例通过
- [ ] 无回归问题

---

## 工作流程

1. 确认 iteration-18 已完成
2. 创建分支: `git checkout -b release/v4.11.0`
3. 执行 T19-001
4. 执行 T19-002
5. 执行 T19-003
6. 执行 T19-004
7. 更新 record.md
8. 合并到 main: `git merge release/v4.11.0`
9. 打标签: `git tag v4.11.0`

---

## 参考文档

- `.pb/iterations/iteration-14-19-plan.md` - 总体规划
- `rodski/docs/TEST_CASE_WRITING_GUIDE.md` - 用例编写指南
- `rodski/docs/SKILL_REFERENCE.md` - 关键字参考
