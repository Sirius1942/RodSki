# REQ-012 调试功能验收测试模块

本模块用于验证 RodSki v11.8.0 中新增的调试功能（REQ-012）。

## 功能概述

REQ-012 调试功能包括：

1. **断点管理** - 在指定位置暂停执行
2. **部分执行** - 从指定步骤开始或在指定步骤停止
3. **执行队列** - 记录和查看执行历史
4. **交互式调试** - 暂停时的交互命令
5. **步骤快照** - 保存和查看步骤状态

## 快速开始

### 运行所有验收用例

```bash
cd rodski-demo/DEMO/debug_partial_execution

# AC-035: 断点功能
rodski run case/AC-035_data_driven_breakpoint.xml --break-at step:3 --headless

# AC-036: 部分执行
rodski run case/AC-036_data_driven_partial_execution.xml --stop-at 4 --headless

# AC-037: 驱动器日志
rodski run case/AC-037_data_driven_driver_log.xml --headless
```

### 验证数据完整性

```bash
rodski data validate rodski-demo/DEMO/debug_partial_execution
```

## 验收用例说明

### AC-035: 数据驱动场景的断点

**目的:** 验证断点在数据驱动场景中的正常工作

**测试步骤:**
1. 加载测试页面（内嵌 HTML）
2. 执行数据驱动的表单填充
3. 在步骤3处触发断点
4. 验证断点触发和执行暂停

**命令参数:**
- `--break-at step:3` - 在步骤3设置断点
- `--headless` - 无头模式运行

**预期结果:** 用例通过，断点正常触发

---

### AC-036: 多步骤部分执行

**目的:** 验证 `--start-from` 和 `--stop-at` 参数的部分执行功能

**测试步骤:**
1. 加载测试页面（内嵌 HTML）
2. 执行8个测试步骤
3. 使用 `--stop-at 4` 在步骤4后停止

**命令参数:**
- `--stop-at 4` - 执行到步骤4后停止
- `--headless` - 无头模式运行

**预期结果:** 用例通过，仅执行前4步

**其他测试场景:**
```bash
# 完整执行（所有8步）
rodski run case/AC-036_data_driven_partial_execution.xml --headless

# 从步骤5开始（会失败，因为页面未加载 - 符合预期）
rodski run case/AC-036_data_driven_partial_execution.xml --start-from 5 --headless
```

---

### AC-037: 驱动器日志测试

**目的:** 验证驱动器动作日志的记录功能

**测试步骤:**
1. 加载测试页面（内嵌 HTML）
2. 执行数据驱动的操作
3. 验证驱动器日志自动记录

**命令参数:**
- `--headless` - 无头模式运行

**预期结果:** 用例通过，驱动器日志正常记录

**注意:** 驱动器日志在调试会话启用时自动记录，无需额外参数

---

## 目录结构

```
debug_partial_execution/
├── README.md                    # 本文件
├── TEST_REPORT.md              # 详细测试报告
├── case/                        # 测试用例
│   ├── AC-035_data_driven_breakpoint.xml
│   ├── AC-036_data_driven_partial_execution.xml
│   └── AC-037_data_driven_driver_log.xml
├── model/                       # 页面对象模型
│   └── model.xml
├── data/                        # 测试数据
│   └── data.sqlite
└── globalvalue/                 # 全局变量
    └── globalvalue.xml
```

## 测试数据

### 数据表清单

| 表名 | 行数 | 用途 | 用例 |
|------|------|------|------|
| AC035_TestData | 2 | 表单输入数据 | AC-035 |
| AC035_TestData_verify | 2 | 验证数据 | AC-035 |
| AC036_TestData | 1 | 表单输入数据 | AC-036 |
| AC036_Comment | 1 | 评论输入数据 | AC-036 |
| AC036_Final_verify | 1 | 最终验证数据 | AC-036 |
| AC037_TestData | 2 | 流程参数数据 | AC-037 |
| AC037_TestData_verify | 2 | 验证数据 | AC-037 |

### 数据库查询示例

```bash
# 查看所有数据表
sqlite3 data/data.sqlite "SELECT table_name, model_name FROM rs_datatable;"

# 查看 AC035 的测试数据
sqlite3 data/data.sqlite "SELECT * FROM AC035_TestData;"

# 查看元数据完整性
sqlite3 data/data.sqlite "
SELECT t.table_name, COUNT(DISTINCT r.data_id) as row_count
FROM rs_datatable t
LEFT JOIN rs_row r ON t.table_name = r.table_name
GROUP BY t.table_name;
"
```

## 调试命令参考

### 断点相关

```bash
# 在步骤3设置断点
--break-at step:3

# 设置多个断点
--break-at step:3,step:7

# 在场景设置断点
--break-at scenario:S001

# 在节点设置断点
--break-at node:SubmitForm
```

### 部分执行

```bash
# 从步骤5开始执行
--start-from 5

# 执行到步骤10停止
--stop-at 10

# 组合使用
--start-from 3 --stop-at 8
```

### 单步执行

```bash
# 单步执行模式（每步暂停）
--step-mode

# 驱动级别单步（每个驱动动作暂停）
--step-mode --driver-level
```

### 交互式调试命令

当执行暂停时，可以使用以下命令：

- `c` / `continue` - 继续执行
- `n` / `next` - 执行下一步
- `q` / `quit` - 退出执行
- `l` / `list` - 列出执行队列
- `ctx` / `context` - 显示当前上下文
- `help` - 显示帮助信息

## 故障排查

### 问题：用例执行失败，提示找不到数据

**原因:** rs_row 表缺少数据行记录

**解决方案:**
```bash
sqlite3 data/data.sqlite "
INSERT OR REPLACE INTO rs_row (table_name, data_id) 
SELECT 'YOUR_TABLE_NAME', data_id FROM YOUR_TABLE_NAME;
"
```

### 问题：模型元素找不到

**原因:** 模型名称与数据表名称不一致

**解决方案:** 确保 model name = table name
```bash
# 检查一致性
sqlite3 data/data.sqlite "
SELECT table_name, model_name FROM rs_datatable 
WHERE table_name != model_name;
"

# 修复
sqlite3 data/data.sqlite "
UPDATE rs_datatable SET model_name = table_name 
WHERE table_name = 'YOUR_TABLE';
"
```

### 问题：页面元素定位失败

**原因:** 使用了真实外部网站（如 example.com）

**解决方案:** 使用内嵌 HTML 的 data URL
```xml
<test_step action="navigate" model="" 
  data="data:text/html,%3Chtml%3E%3Cbody%3E%3Cinput%20id%3D%22username%22%3E%3C%2Fbody%3E%3C%2Fhtml%3E"/>
```

## 相关文档

- [TEST_REPORT.md](./TEST_REPORT.md) - 详细测试报告
- [SPEC-012.md](../../docs/SPEC-012.md) - 调试功能需求规格
- [RodSki 用户手册](https://rodski.readthedocs.io/) - 完整文档

## 联系信息

如有问题或建议，请联系开发团队或提交 Issue。
