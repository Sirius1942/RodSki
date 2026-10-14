# RodSki REQ-012 调试与部分执行能力验收

本模块包含 37 个验收用例，覆盖 REQ-012 的所有功能点。

## 功能概述

REQ-012 为 RodSki 框架引入了强大的调试与部分执行能力：

- **断点机制**：多层级断点（步骤、业务节点、场景、驱动动作）
- **部分执行**：从指定步骤开始、在指定步骤停止、单步执行
- **对象生命周期管理**：暂停后对象复用、跨会话对象保持
- **执行查看器**：实时查看执行队列、驱动动作、对象池
- **驱动级别控制**：驱动动作级别断点、日志记录

## 验收用例清单

### A组：基础暂停与继续（5个用例）✅

| 用例ID | 描述 | 优先级 | 状态 |
|--------|------|--------|------|
| AC-001 | 在指定步骤暂停 | P0 | ✅ |
| AC-002 | 暂停后继续执行 | P0 | ✅ |
| AC-003 | 单步执行模式 | P0 | ✅ |
| AC-004 | 暂停后修改数据继续 | P0 | ✅ |
| AC-005 | 多断点顺序触发 | P0 | ✅ |

### B组：多层级断点（6个用例）✅

| 用例ID | 描述 | 优先级 | 状态 |
|--------|------|--------|------|
| AC-006 | 业务模型节点断点 | P0 | ✅ |
| AC-007 | Flow级别断点 | P0 | ✅ |
| AC-008 | Scenario断点 | P0 | ✅ |
| AC-009 | 驱动动作断点（click） | P0 | ✅ |
| AC-010 | 批量操作行级断点 | P0 | ✅ |
| AC-011 | 嵌套断点（业务模型内的步骤） | P0 | ✅ |

### C组：部分执行（7个用例）✅

| 用例ID | 描述 | 优先级 | 状态 |
|--------|------|--------|------|
| AC-012 | 从指定步骤开始执行 | P0 | ✅ |
| AC-013 | 执行到指定步骤停止 | P0 | ✅ |
| AC-014 | 范围执行（start + stop） | P0 | ✅ |
| AC-015 | 跳过pre_process直接执行test_case | P0 | ✅ |
| AC-016 | 只执行post_process | P0 | ✅ |
| AC-017 | 业务模型部分执行（从第3个节点开始） | P0 | ✅ |
| AC-018 | Scenario部分执行 | P0 | ✅ |

### D组：错误处理（3个用例）✅

| 用例ID | 描述 | 优先级 | 状态 |
|--------|------|--------|------|
| AC-019 | 断点位置不存在的处理 | P1 | ✅ |
| AC-020 | start_from超出步骤总数 | P1 | ✅ |
| AC-021 | stop_at小于start_from | P1 | ✅ |

### E组：驱动级别控制（5个用例）✅

| 用例ID | 描述 | 优先级 | 状态 |
|--------|------|--------|------|
| AC-022 | 查看驱动动作队列 | P0 | ✅ |
| AC-023 | 驱动动作级别断点（fill） | P0 | ✅ |
| AC-024 | 驱动动作执行日志 | P0 | ✅ |
| AC-025 | 驱动动作重试记录 | P0 | ✅ |
| AC-026 | 多驱动场景的动作队列 | P0 | ✅ |

### F组：对象生命周期（3个用例）✅

| 用例ID | 描述 | 优先级 | 状态 |
|--------|------|--------|------|
| AC-027 | 暂停后对象复用 | P0 | ✅ |
| AC-028 | 对象池查看 | P0 | ✅ |
| AC-029 | 多浏览器对象管理 | P0 | ✅ |
| AC-030 | 对象生命周期追踪 | P0 | ✅ |

### G组：执行查看与日志（4个用例）✅

| 用例ID | 描述 | 优先级 | 状态 |
|--------|------|--------|------|
| AC-031 | 实时查看执行状态 | P0 | ✅ |
| AC-032 | 执行队列导出 | P0 | ✅ |
| AC-033 | 多维度日志输出 | P0 | ✅ |
| AC-034 | 历史执行对比 | P0 | ✅ |

### H组：与数据驱动联动（3个用例）✅

| 用例ID | 描述 | 优先级 | 状态 |
|--------|------|--------|------|
| AC-035 | 数据驱动场景的断点 | P1 | ✅ |
| AC-036 | 数据驱动场景的部分执行 | P1 | ✅ |
| AC-037 | 数据驱动场景的驱动动作日志 | P1 | ✅ |

## 当前进度

- **已完成**：37/37 个验收用例（100%）✅
- **P0 用例**：31/31（100%）✅
- **P1 用例**：6/6（100%）✅
- **配套数据**：待补充

## 使用方法

### 1. 基础断点

```bash
# 在第5步暂停
rodski run case/AC-001_basic_pause.xml --break-at step:5

# 在业务节点暂停
rodski run case/AC-006_node_breakpoint.xml --break-at node:fill_vin

# 在驱动动作暂停
rodski run case/AC-009_driver_action_breakpoint.xml --break-at driver:click
```

### 2. 部分执行

```bash
# 从第3步开始
rodski run case/AC-012_start_from.xml --start-from 3

# 执行到第10步停止
rodski run case/AC-013_stop_at.xml --stop-at 10

# 范围执行
rodski run case/AC-014_range_execution.xml --start-from 5 --stop-at 15
```

### 3. 单步执行

```bash
# 单步模式
rodski run case/AC-003_step_mode.xml --step-mode
```

### 4. 执行查看器

```bash
# 查看执行状态
rodski debug status

# 查看驱动动作队列
rodski debug queue

# 查看对象池
rodski debug objects

# 导出执行队列
rodski debug export --output execution_queue.json
```

### 5. 驱动动作日志

```bash
# 记录驱动动作日志
rodski run case/AC-024_driver_log.xml --driver-log

# 查看日志
cat result/latest/driver_actions.jsonl | jq .

# 过滤特定用例的日志
cat result/latest/driver_actions.jsonl | jq 'select(.case_id=="AC-024")'
```

## 目录结构

```
debug_partial_execution/
├── case/                    # 37个验收用例XML
│   ├── AC-001_basic_pause.xml
│   ├── AC-002_resume.xml
│   └── ...
├── model/                   # 测试页面模型
│   └── model.xml
├── data/                    # 测试数据
│   ├── data.sqlite
│   └── globalvalue.xml
├── business/                # 业务模型（用于B组用例）
│   └── purchase_flow.xml
├── fun/                     # 自定义脚本（如需要）
└── README.md                # 本文件
```

## 验收标准

### P0 用例（必须全部通过）

1. **基础暂停与继续**：5个用例全部通过
2. **多层级断点**：6个用例全部通过
3. **部分执行**：7个用例全部通过
4. **驱动级别控制**：5个用例全部通过
5. **对象生命周期**：4个用例全部通过
6. **执行查看与日志**：4个用例全部通过

### P1 用例（建议通过）

7. **错误处理**：3个用例通过
8. **数据驱动联动**：3个用例通过

## 注意事项

1. **对象复用**：AC-027 和 AC-036 需要分两次运行，第二次复用第一次的浏览器对象
2. **驱动动作日志**：需要在 result 目录下生成 `driver_actions.jsonl`
3. **执行队列导出**：需要支持 `rodski debug export` 命令
4. **多浏览器场景**：AC-029 需要同时管理两个浏览器实例

## 相关文档

- 需求文档：`.pb/requirements/REQ-012_v2.0_debugging_partial_execution.md`
- 设计约束变更：`.pb/specs/DESIGN_CONSTRAINT_CHANGES_v11.8.0.md`
- 用户手册：`.pb/specs/USER_MANUAL_debugging_v11.8.0.md`
