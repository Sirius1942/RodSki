# Iteration 15: 清理与文档

**版本**: v4.7.0  
**分支**: release/v4.7.0  
**日期**: 2026-04-09  
**工时**: 4h  
**优先级**: P1  
**前置依赖**: iteration-14

---

## 目标

清理 rodski-demo 项目，提升质量和可维护性：
1. 清理 data 目录冗余文件
2. 更新 README 文档
3. 添加 Python 运行脚本

---

## 任务清单

### T15-001: 清理 data 目录 (2h)

**文件**: `rodski-demo/DEMO/demo_full/data/`

**任务**:
1. 分析文件引用关系
2. 识别未使用文件
3. 统一命名规范（模型名.xml / 模型名_verify.xml）
4. 合并重复文件
5. 创建 data/README.md

**验收**:
- data 目录文件数量减少到30个以内
- 命名规范统一
- 有清晰的文件组织说明
- 现有测试用例不受影响

---

### T15-002: 更新 README 文档 (1h)

**文件**: `rodski-demo/DEMO/demo_full/README.md`

**任务**:
1. 更新功能说明（expect_fail、Auto Capture、结构化日志）
2. 修正路径引用（统一使用 rodski-demo/ 前缀）
3. 更新测试用例统计
4. 删除过时说明

**验收**:
- 文档内容与实际代码一致
- 路径引用全部正确
- 功能说明完整准确

---

### T15-003: 添加 Python 运行脚本 (1h)

**文件**: `rodski-demo/DEMO/demo_full/run_demo.py`

**任务**:
创建跨平台 Python 运行脚本，支持：
- 初始化数据库
- 运行测试用例
- 显示测试结果
- 参数：--case, --log-level, --init-db

**验收**:
- 脚本可以在 Windows/macOS/Linux 运行
- 支持所有必要参数
- 错误提示清晰
- 与 run_demo.sh 功能一致

---

## 验收标准

- [ ] data 目录文件数量减少，命名规范统一
- [ ] README 文档内容准确完整
- [ ] run_demo.py 可以跨平台运行
- [ ] 所有测试用例通过
- [ ] 无回归问题

---

## 工作流程

1. 确认 iteration-14 已完成
2. 创建分支: `git checkout -b release/v4.7.0`
3. 执行 T15-001
4. 执行 T15-002
5. 执行 T15-003
6. 运行回归测试
7. 更新 record.md
8. 合并到 main: `git merge release/v4.7.0`
9. 打标签: `git tag v4.7.0`

---

## 参考文档

- `.pb/iterations/iteration-14-19-plan.md` - 总体规划
- `rodski/docs/DATA_FILE_ORGANIZATION.md` - 数据文件组织
