# rodski-demo 项目问题清单

**创建日期**: 2026-04-09  
**项目**: rodski-demo  
**版本**: 当前状态快照

---

## 🔴 P0 - 严重问题（需立即修复）

### 1. 预期失败测试用例缺少 expect_fail 属性

**问题描述**:
- TC012A（get不存在key报错测试）和 TC014A（type Auto Capture失败测试）是故意设计失败的用例
- 但没有标记 `expect_fail="是"`，导致测试报告显示为失败而非预期失败
- 影响测试报告的准确性

**位置**:
- `rodski-demo/DEMO/demo_full/case/demo_case.xml:169`
- `rodski-demo/DEMO/demo_full/case/demo_case.xml:217`

**修复方案**:
```xml
<!-- TC012A: get不存在key报错测试 -->
<case execute="是" id="TC012A" title="get不存在key报错测试" component_type="界面" expect_fail="是">
    <test_case>
        <test_step action="get" model="" data="undefined_key"/>
    </test_case>
</case>

<!-- TC014A: AC12-002 type Auto Capture失败 -->
<case execute="是" id="TC014A" title="type Auto Capture失败测试" component_type="界面" expect_fail="是">
    <pre_process>
        <test_step action="navigate" model="" data="http://localhost:8000"/>
        <test_step action="type" model="LoginForm" data="L001"/>
        <test_step action="type" model="NavMenu" data="N001"/>
    </pre_process>
    <test_case>
        <test_step action="type" model="DemoFormBadCapture" data="F001"/>
    </test_case>
    <post_process>
        <test_step action="close" model="" data=""/>
    </post_process>
</case>
```

---

### 2. tc_expect_fail.xml 引用不存在的模型和数据

**问题描述**:
- `tc_expect_fail.xml` 中使用了 `ErrorMessage` 模型，但 `model.xml` 中没有定义
- 使用了 `LoginForm` 的 `L002` 数据，但 `data/` 目录中没有该数据文件

**位置**:
- `rodski-demo/DEMO/demo_full/case/tc_expect_fail.xml:12`

**影响**:
- 该测试用例无法正常运行
- 缺少负面测试的完整示例

**修复方案**:
1. 在 `model.xml` 中添加 `ErrorMessage` 模型定义
2. 在 `data/LoginForm.xml` 中添加 `L002` 数据行（错误密码）
3. 或者修改用例使用已有的模型和数据

---

### 3. run_demo.sh 路径错误

**问题描述**:
- 第 36 行使用了错误的路径 `product/DEMO/demo_full/result/`
- 应该是 `rodski-demo/DEMO/demo_full/result/`

**位置**:
- `rodski-demo/DEMO/demo_full/run_demo.sh:36`

**影响**:
- 用户无法找到测试报告
- 脚本提示信息误导用户

**修复方案**:
```bash
echo "📊 查看测试报告："
echo "   ls -la rodski-demo/DEMO/demo_full/result/"
```

---

## 🟡 P1 - 重要问题（后续优化）

### 4. data 目录文件冗余严重

**问题描述**:
- data 目录包含 47 个文件，存在大量冗余
- 命名不一致：`Dashboard.xml` vs `Dashboard_verify.xml`
- 命名混乱：`Login.xml` vs `LoginForm.xml`
- 很多 `_verify.xml` 文件可能是测试遗留

**位置**:
- `rodski-demo/DEMO/demo_full/data/`

**影响**:
- 维护困难
- 新用户难以理解文件组织
- 可能存在未使用的文件

**优化方案**:
1. 清理未使用的数据文件
2. 统一命名规范：模型名.xml / 模型名_verify.xml
3. 合并重复的数据文件
4. 添加 data/README.md 说明文件组织

---

### 5. README 文档过时

**问题描述**:
- 提到 "set关键字暂不支持XML直接配置"，但 TC010 已经在使用
- 路径引用混乱（`product/` vs `rodski-demo/`）
- 测试用例数量不准确（说10个，实际有15+个）
- 缺少最新功能说明（expect_fail、Auto Capture、结构化日志）

**位置**:
- `rodski-demo/DEMO/demo_full/README.md`

**影响**:
- 误导新用户
- 文档与实际不符

**优化方案**:
1. 更新功能说明，补充最新特性
2. 修正路径引用
3. 更新测试用例统计
4. 添加功能覆盖矩阵

---

### 6. 缺少统一的运行入口

**问题描述**:
- demo_full 目录下只有 shell 脚本 `run_demo.sh`
- 缺少 Python 运行脚本，不够跨平台
- 缺少参数化运行支持（如只运行部分用例）

**位置**:
- `rodski-demo/DEMO/demo_full/`

**影响**:
- Windows 用户体验差
- 无法灵活控制测试执行

**优化方案**:
1. 添加 `run_demo.py` Python 脚本
2. 支持参数：`--case`, `--tag`, `--parallel` 等
3. 提供更友好的输出和错误提示

---

## 📊 问题统计

| 优先级 | 数量 | 状态 |
|--------|------|------|
| P0 严重 | 3 | 待修复 |
| P1 重要 | 3 | 待优化 |
| **总计** | **6** | - |

---

## 🔄 修复建议顺序

1. **立即修复** (P0):
   - 给 TC012A 和 TC014A 添加 `expect_fail="是"`
   - 修复 run_demo.sh 的路径错误
   - 补充 tc_expect_fail.xml 缺失的模型和数据

2. **后续优化** (P1):
   - 清理 data 目录冗余文件
   - 更新 README 文档
   - 添加 Python 运行脚本

---

## 📝 备注

- 本清单基于 2026-04-09 的代码状态
- 修复后需要运行完整测试验证
- 建议在修复后更新本文档状态
