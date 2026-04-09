# Iteration 14: 验收测试

## 设计合规性检查

| 检查项 | 结论 |
|--------|------|
| 不改变 rodski 框架代码 | ✅ |
| 所有修改向后兼容 | ✅ |
| 修复后所有测试用例通过 | ✅ |
| 文档与代码同步 | ✅ |

---

## AC14-001: expect_fail 属性修复验证

**测试用例名称**: TC012A 和 TC014A 正确标记为预期失败

**验收条件**:
- TC012A 在测试报告中显示为"预期失败"（Expected Fail），而非"失败"（Failed）
- TC014A 在测试报告中显示为"预期失败"（Expected Fail），而非"失败"（Failed）
- 测试报告统计中，预期失败数量正确
- 总体测试结果判定不受预期失败影响

**运行方式**: 
```bash
python3 rodski/ski_run.py rodski-demo/DEMO/demo_full/case/demo_case.xml
```

**验证方法**:
1. 检查控制台输出，TC012A 和 TC014A 显示为 EXPECTED_FAIL
2. 检查 result.xml，对应用例的 status 为 "expected_fail"
3. 检查测试统计，预期失败计数正确

---

## AC14-002: run_demo.sh 路径修复验证

**测试用例名称**: run_demo.sh 路径全部正确

**验收条件**:
- 脚本可以从项目根目录运行
- 脚本可以从 demo_full 目录运行
- 路径提示信息准确，用户可以找到测试报告
- 测试用例可以正常执行

**运行方式**: 
```bash
cd rodski-demo/DEMO/demo_full
./run_demo.sh
```

**验证方法**:
1. 脚本运行无错误
2. 测试用例执行成功
3. 提示的报告路径存在且正确

---

## AC14-003: tc_expect_fail.xml 完整性验证

**测试用例名称**: tc_expect_fail.xml 可以正常运行

**验收条件**:
- ErrorMessage 模型定义存在且正确
- LoginForm.xml 包含 L002 数据行
- ErrorMessage_verify.xml 存在且包含验证数据
- demosite 支持错误提示显示
- TC_EF001 正确标记为预期失败并通过
- TC_EF002 正常通过

**运行方式**: 
```bash
python3 rodski/ski_run.py rodski-demo/DEMO/demo_full/case/tc_expect_fail.xml
```

**验证方法**:
1. 两个用例都能运行
2. TC_EF001 显示为预期失败
3. TC_EF002 显示为通过
4. 错误提示信息正确显示

---

## AC14-004: data 目录清理验证

**测试用例名称**: data 目录文件组织规范

**验收条件**:
- data 目录文件数量减少到 30 个以内
- 所有文件命名遵循规范（模型名.xml / 模型名_verify.xml）
- data/README.md 存在且说明清晰
- 所有现有测试用例不受影响

**验证方法**:
1. 统计 data 目录文件数量：`ls -1 data/*.xml | wc -l`
2. 检查命名规范：所有文件符合命名约定
3. 阅读 data/README.md，内容清晰
4. 运行所有测试用例，全部通过

---

## AC14-005: README 文档更新验证

**测试用例名称**: README 文档内容准确完整

**验收条件**:
- 功能说明包含最新特性（expect_fail、Auto Capture、结构化日志）
- 路径引用全部正确（使用 rodski-demo/ 前缀）
- 测试用例统计准确
- 无过时说明

**验证方法**:
1. 阅读 README.md，检查功能说明完整性
2. 验证所有路径引用可用
3. 统计实际测试用例数量，与文档一致
4. 确认无"暂不支持"等过时描述

---

## AC14-006: Python 运行脚本验证

**测试用例名称**: run_demo.py 跨平台运行

**验收条件**:
- 脚本可以在 Windows/macOS/Linux 运行
- 支持 --case, --log-level, --init-db 参数
- 错误提示清晰友好
- 功能与 run_demo.sh 一致

**运行方式**: 
```bash
python3 rodski-demo/DEMO/demo_full/run_demo.py --init-db
python3 rodski-demo/DEMO/demo_full/run_demo.py --case case/demo_case.xml --log-level debug
```

**验证方法**:
1. 在不同平台运行脚本
2. 测试所有参数组合
3. 验证错误提示清晰
4. 对比 shell 脚本功能一致

---

## AC14-007: 完整回归测试验证

**测试用例名称**: 所有测试用例通过

**验收条件**:
- 所有正向用例通过
- 所有负向用例正确标记为预期失败
- 测试报告统计准确
- 日志输出正常
- 无回归问题

**运行方式**: 
```bash
python3 rodski/ski_run.py rodski-demo/DEMO/demo_full/case/demo_case.xml
python3 rodski/ski_run.py rodski-demo/DEMO/demo_full/case/tc_expect_fail.xml
```

**验证方法**:
1. 运行所有测试用例
2. 检查测试报告，统计准确
3. 检查日志输出，格式正确
4. 对比修复前后，无新增失败

---

## rodski-demo 开发需求

**需要开发**: T14-001 ~ T14-008  
**rodski 开发**: 无（仅修改 demo 项目）

---

## 验收总结

| 验收项 | 状态 | 备注 |
|--------|------|------|
| AC14-001 | ⏳ | expect_fail 属性 |
| AC14-002 | ⏳ | run_demo.sh 路径 |
| AC14-003 | ⏳ | tc_expect_fail.xml |
| AC14-004 | ⏳ | data 目录清理 |
| AC14-005 | ⏳ | README 更新 |
| AC14-006 | ⏳ | Python 运行脚本 |
| AC14-007 | ⏳ | 完整回归测试 |

**图例**: ✅ 通过 | ❌ 失败 | ⏳ 待验证
