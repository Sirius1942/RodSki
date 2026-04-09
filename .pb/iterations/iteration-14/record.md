# Iteration 14 实施记录

**版本**: v4.6.0  
**分支**: release/v4.6.0  
**开始日期**: 2026-04-09  
**完成日期**: 2026-04-09  
**实际工时**: 3h

---

## 实施过程

### 准备阶段

**日期**: 2026-04-09

- [x] 创建分支 `release/v4.6.0`
- [x] 确认前置依赖（无）
- [x] 恢复被删除的 rodski-demo 文件

---

### T14-001: 添加 expect_fail 属性

**开始时间**: 2026-04-09 23:10  
**完成时间**: 2026-04-09 23:11  
**实际工时**: 0.1h

#### 实施步骤
1. 为 TC012A 添加 `expect_fail="是"` 属性
2. 为 TC014A 添加 `expect_fail="是"` 属性（后续移除）
3. 验证测试报告正确显示预期失败

#### 遇到的问题
- TC014A 在框架 v4.4.0+ 中不再失败（auto_capture 改为返回 None 而非抛异常）

#### 解决方案
- 移除 TC014A 的 expect_fail 属性，因为它现在测试优雅降级行为

---

### T14-002: 修复 run_demo.sh 路径

**开始时间**: 2026-04-09 23:11  
**完成时间**: 2026-04-09 23:11  
**实际工时**: 0.1h

#### 实施步骤
1. 修改第 36 行：`product/` → `rodski-demo/`
2. 验证脚本可以正确运行

#### 遇到的问题
- 无

#### 解决方案
- 直接修改路径即可

---

### T14-003: 补充 tc_expect_fail.xml

**开始时间**: 2026-04-09 23:11  
**完成时间**: 2026-04-09 23:28  
**实际工时**: 0.3h

#### 实施步骤
1. 在 model.xml 添加 ErrorMessage 模型（使用 loginError 元素 ID）
2. 在 data.xml 添加 LoginForm.L002 错误密码数据
3. 在 data.xml 添加 ErrorMessage_verify 验证表
4. 添加 step_wait="500" 到 tc_expect_fail.xml
5. 移除 TC_EF001 的 expect_fail 属性（该用例测试错误处理，应该通过）

#### 遇到的问题
- 最初在 LoginForm.xml 添加 L002，但框架从 data.xml 加载数据
- HTML 已有错误处理逻辑，无需修改 app.py
- TC_EF001 设计为测试错误处理功能，不应标记为 expect_fail

#### 解决方案
- 在 data.xml 中添加 L002 和 ErrorMessage_verify
- 使用现有的 loginError 元素 ID
- 移除 TC_EF001 的 expect_fail 属性

---

## 验收测试

**测试日期**: 2026-04-09

### 功能验收
- [x] AC-001: expect_fail 属性 - TC012A 正确显示为"预期失败"
- [x] AC-002: run_demo.sh 路径 - 路径已修正
- [x] AC-003: tc_expect_fail.xml - 所有测试通过

### 回归测试
- [x] RT-001: demo_case.xml 所有 19 个用例通过（100%）
- [x] RT-002: tc_expect_fail.xml 所有 2 个用例通过（100%）

---

## 交付物

- [x] 修复后的 demo_case.xml（TC012A 有 expect_fail）
- [x] 修复后的 run_demo.sh
- [x] ErrorMessage 模型定义（model.xml）
- [x] L002 测试数据（data.xml）
- [x] ErrorMessage_verify 验证表（data.xml）
- [x] tc_expect_fail.xml（添加 step_wait，移除 TC_EF001 的 expect_fail）
- [x] Git 标签 v4.6.0

---

## 总结

### 完成情况
- 所有任务按计划完成
- TC012A 正确标记为预期失败
- TC014A 移除 expect_fail（框架行为变更）
- tc_expect_fail.xml 可以正常运行
- 所有测试用例通过

### 经验教训
1. 数据文件组织：框架从 data.xml 加载数据，不是从单独的 XML 文件
2. expect_fail 语义：用于预期会失败的测试，不是用于测试错误处理功能
3. 框架演进：v4.4.0+ auto_capture 改为优雅降级，需要调整测试用例

### 后续建议
1. 文档化数据文件加载机制
2. 明确 expect_fail 的使用场景
3. 考虑为 tc_expect_fail.xml 添加真正的负面测试用例
