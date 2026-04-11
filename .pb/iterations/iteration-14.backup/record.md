# Iteration 14: rodski-demo 问题修复与质量提升

**版本**: v4.6.0  
**日期**: 2026-04-09  
**分支**: main  
**需求来源**: `.pb/specs/rodski-demo-issues.md`  
**优先级**: P0（严重问题修复）  
**前置依赖**: iteration-13 完成

---

## 迭代目标

1. 修复 rodski-demo 项目中的 P0 严重问题（3个）
2. 优化 P1 重要问题（3个）
3. 提升 demo 项目的质量和可维护性
4. 为 iteration-15 的功能扩展打好基础

---

## 核心约束（不可违反）

> - 不改变 rodski 框架代码，只修改 rodski-demo 项目
> - 所有修改必须向后兼容，不破坏现有测试用例
> - 修复后所有测试用例必须通过
> - 文档更新必须与代码同步

---

## 设计决策

### D14-01: P0 问题优先修复

**决策**: 按以下顺序修复 P0 问题
1. 添加 expect_fail 属性（最简单，影响最大）
2. 修复 run_demo.sh 路径（快速修复）
3. 补充 tc_expect_fail.xml 缺失内容（需要扩展模型和数据）

**Why**: 先解决简单问题，快速提升测试报告准确性。

### D14-02: data 目录重组策略

**决策**: 采用渐进式清理
1. 识别未使用的文件（通过 grep 检查引用）
2. 统一命名规范（data.xml / data_verify.xml）
3. 合并重复文件
4. 添加 data/README.md 说明文件组织

**Why**: 避免一次性大规模删除导致遗漏，渐进式更安全。

### D14-03: 文档更新策略

**决策**: 同步更新三份文档
1. README.md - 用户快速入门
2. SUMMARY.md - 功能覆盖总结
3. TEST_SUMMARY.md - 测试用例清单

**Why**: 保持文档一致性，避免信息不同步。

---

## 实施任务

### 阶段一: P0 严重问题修复

#### T14-001: 添加 expect_fail 属性
**文件**: `rodski-demo/DEMO/demo_full/case/demo_case.xml`

**任务**:
- 给 TC012A 添加 `expect_fail="是"`
- 给 TC014A 添加 `expect_fail="是"`
- 验证测试报告正确显示预期失败

**验收标准**:
- 测试运行后，TC012A 和 TC014A 显示为"预期失败"而非"失败"
- 测试报告统计正确

**预计**: 0.5h | **Owner**: 待分配

---

#### T14-002: 修复 run_demo.sh 路径错误
**文件**: `rodski-demo/DEMO/demo_full/run_demo.sh`

**任务**:
- 修正第 36 行路径：`product/` → `rodski-demo/`
- 修正第 30 行路径：确保相对路径正确
- 测试脚本在不同目录下运行

**验收标准**:
- 脚本可以正确运行
- 路径提示信息准确
- 可以找到测试报告

**预计**: 0.5h | **Owner**: 待分配

---

#### T14-003: 补充 tc_expect_fail.xml 缺失内容
**文件**: 
- `rodski-demo/DEMO/demo_full/model/model.xml`
- `rodski-demo/DEMO/demo_full/data/LoginForm.xml`
- `rodski-demo/DEMO/demo_full/data/ErrorMessage_verify.xml`

**任务**:
1. 在 model.xml 中添加 ErrorMessage 模型定义
   ```xml
   <model name="ErrorMessage" type="ui" servicename="">
       <element name="errorMsg" type="text">
           <location type="id">errorMessage</location>
       </element>
   </model>
   ```

2. 在 LoginForm.xml 中添加 L002 数据行（错误密码）
   ```xml
   <row id="L002">
       <field name="username">admin</field>
       <field name="password">wrongpassword</field>
       <field name="loginBtn">click</field>
   </row>
   ```

3. 创建 ErrorMessage_verify.xml
   ```xml
   <datatable name="ErrorMessage_verify">
       <row id="V001">
           <field name="errorMsg">用户名或密码错误</field>
       </row>
   </datatable>
   ```

4. 扩展 demosite/app.py，支持错误提示显示

**验收标准**:
- tc_expect_fail.xml 可以正常运行
- 错误提示正确显示
- 负面测试用例通过

**预计**: 2h | **Owner**: 待分配

---

### 阶段二: P1 重要问题优化

#### T14-004: 清理 data 目录冗余文件
**文件**: `rodski-demo/DEMO/demo_full/data/`

**任务**:
1. 分析文件引用关系
   ```bash
   # 检查每个数据文件是否被引用
   for file in data/*.xml; do
       name=$(basename $file .xml)
       grep -r "$name" case/ model/ || echo "未使用: $file"
   done
   ```

2. 识别冗余文件
   - 重复命名的文件（Dashboard.xml vs Dashboard_verify.xml）
   - 未被引用的文件
   - 测试遗留文件

3. 统一命名规范
   - 数据文件：模型名.xml
   - 验证文件：模型名_verify.xml

4. 创建 data/README.md 说明文件组织

**验收标准**:
- data 目录文件数量减少到 30 个以内
- 所有文件命名规范统一
- 有清晰的文件组织说明
- 现有测试用例不受影响

**预计**: 2h | **Owner**: 待分配

---

#### T14-005: 更新 README 文档
**文件**: `rodski-demo/DEMO/demo_full/README.md`

**任务**:
1. 更新功能说明
   - 补充 expect_fail 功能
   - 补充 Auto Capture 功能
   - 补充结构化日志功能

2. 修正路径引用
   - 统一使用 `rodski-demo/` 前缀
   - 更新运行命令示例

3. 更新测试用例统计
   - 当前实际用例数量：15+
   - 按类型分类统计

4. 删除过时说明
   - 删除"set关键字暂不支持"等过时信息

**验收标准**:
- 文档内容与实际代码一致
- 路径引用全部正确
- 功能说明完整准确

**预计**: 1h | **Owner**: 待分配

---

#### T14-006: 添加 Python 运行脚本
**文件**: `rodski-demo/DEMO/demo_full/run_demo.py`

**任务**:
创建跨平台的 Python 运行脚本，支持：
1. 初始化数据库
2. 运行测试用例
3. 显示测试结果
4. 支持参数：
   - `--case`: 指定用例文件
   - `--log-level`: 日志级别
   - `--parallel`: 并发执行

**示例代码**:
```python
#!/usr/bin/env python3
"""RodSki Demo 运行脚本"""
import argparse
import subprocess
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description='RodSki Demo 运行脚本')
    parser.add_argument('--case', default='case/demo_case.xml', help='测试用例文件')
    parser.add_argument('--log-level', default='info', choices=['debug', 'info'], help='日志级别')
    parser.add_argument('--init-db', action='store_true', help='初始化数据库')
    args = parser.parse_args()
    
    demo_dir = Path(__file__).parent
    project_root = demo_dir.parent.parent.parent
    
    # 初始化数据库
    if args.init_db:
        print("🔧 初始化数据库...")
        subprocess.run([sys.executable, demo_dir / 'init_db.py'], check=True)
    
    # 运行测试
    print(f"🚀 运行测试用例: {args.case}")
    case_file = demo_dir / args.case
    cmd = [
        sys.executable,
        project_root / 'rodski' / 'ski_run.py',
        str(case_file),
        '--log-level', args.log_level
    ]
    subprocess.run(cmd, check=True)
    
    print("✅ 测试完成")

if __name__ == '__main__':
    main()
```

**验收标准**:
- 脚本可以在 Windows/macOS/Linux 运行
- 支持所有必要参数
- 错误提示清晰
- 与 run_demo.sh 功能一致

**预计**: 1.5h | **Owner**: 待分配

---

### 阶段三: 验证与文档

#### T14-007: 完整回归测试
**文件**: 所有测试用例

**任务**:
1. 运行所有测试用例
2. 验证修复效果
3. 检查测试报告
4. 确认无回归问题

**验收标准**:
- 所有正向用例通过
- 所有负向用例正确标记为预期失败
- 测试报告统计准确
- 日志输出正常

**预计**: 1h | **Owner**: 待分配

---

#### T14-008: 更新迭代文档
**文件**: `.pb/iterations/iteration-14/record.md`

**任务**:
1. 记录所有修改内容
2. 记录遇到的问题和解决方案
3. 记录验收测试结果
4. 总结经验教训

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

---

## 验收标准

### 功能验收
- [ ] TC012A 和 TC014A 正确标记为预期失败
- [ ] run_demo.sh 路径全部正确
- [ ] tc_expect_fail.xml 可以正常运行
- [ ] data 目录文件数量减少，命名规范统一
- [ ] README 文档内容准确完整
- [ ] run_demo.py 可以跨平台运行

### 质量验收
- [ ] 所有测试用例通过
- [ ] 测试报告统计准确
- [ ] 文档与代码同步
- [ ] 无回归问题

### 文档验收
- [ ] README.md 更新完成
- [ ] data/README.md 创建完成
- [ ] iteration-14/record.md 记录完整

---

## 遗留与后续

- 功能扩展（新增测试用例）推迟到 iteration-15
- 视觉定位功能需要 OmniParser 服务支持，暂不实施
- 桌面自动化功能需要额外依赖，暂不实施

---

## 风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|---------|
| data 目录清理误删文件 | 高 | 先备份，逐步验证 |
| demosite 扩展影响现有功能 | 中 | 充分测试，保持向后兼容 |
| 文档更新遗漏 | 低 | 使用检查清单 |

---

## 参考文档

- `.pb/specs/rodski-demo-issues.md` - 问题清单
- `rodski/docs/TEST_CASE_WRITING_GUIDE.md` - 用例编写指南
- `rodski/docs/CORE_DESIGN_CONSTRAINTS.md` - 核心设计约束
