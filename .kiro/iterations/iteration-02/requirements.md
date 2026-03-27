# 需求说明 - Agent 集成增强

**版本**: 1.0
**日期**: 2026-03-27
**关联 Issue**: #2

## 背景

当前 RodSki 框架设计理念适合 Agent 自动化，但实现上存在多个阻塞问题：
- Agent 无法感知执行过程
- Agent 无法干预运行中用例
- Agent 无法获取中间结果
- 部分关键字文档与实现不一致

## 目标用户

- OpenClaw Agent（主要）
- 其他需要程序化控制测试执行的自动化系统

## 功能需求

### FR1: 运行时控制注入
**优先级**: P0

Agent 需要能够传入 `RuntimeCommandQueue` 来控制执行流程。

**验收标准**:
- CLI 支持 `--runtime-control` 参数或环境变量
- 提供 Python API 入口接受 runtime_control 参数
- Agent 可以在运行时 pause/insert/terminate

### FR2: 实时结果输出
**优先级**: P0

每个 case 完成后立即写入结果，避免进程崩溃导致数据丢失。

**验收标准**:
- 每个 case 完成后立即写入临时结果文件
- 支持增量结果输出（JSON Lines 格式）
- 进程异常退出时已完成的 case 结果可恢复

### FR3: 执行过程事件回调
**优先级**: P0

Agent 需要实时感知执行状态。

**验收标准**:
- 提供事件回调接口（StepEvent, CaseEvent）
- 支持以下事件类型：
  - step_start, step_end
  - case_start, case_end
  - screenshot_captured
  - error_occurred
- 事件包含时间戳、上下文信息

### FR4: 补全缺失关键字
**优先级**: P0

XSD 中定义的 `click` 和 `screenshot` 必须实现。

**验收标准**:
- `click` 关键字可执行
- `screenshot` 关键字可执行
- 通过 XSD 验证的 case 不会因关键字缺失而失败

### FR5: 异常处理改进
**优先级**: P1

修复异常处理中的静默失败和误判问题。

**验收标准**:
- `get_text` 异常时抛出而非返回 None
- `is_critical_error` 使用异常类型判断
- `verify` 失败时正确触发失败路径

### FR6: Python API 入口
**优先级**: P1

提供程序化调用接口，而非仅 CLI。

**验收标准**:
- 提供 `RodSkiRunner` 类
- 支持传入事件回调函数
- 支持传入 runtime_control
- 返回结构化执行结果

## 非功能需求

### NFR1: 测试覆盖
核心模块必须有单元测试覆盖。

**目标**:
- `keyword_engine.py` 覆盖率 > 80%
- `ski_executor.py` 覆盖率 > 80%
- `case_parser.py` 覆盖率 > 70%

### NFR2: 向后兼容
所有改动必须保持向后兼容，现有 CLI 用法不受影响。

### NFR3: 性能
事件回调和实时写入不应显著影响执行性能（< 5% 开销）。

## 约束条件

1. 不改变现有关键字语义
2. 不破坏现有 XSD Schema
3. 保持 CLI 接口稳定
4. 安全问题（`run` 关键字沙箱）留待后续迭代

## 成功标准

- [ ] 所有 P0 需求完成
- [ ] 核心模块测试覆盖达标
- [ ] OpenClaw Agent 可成功集成
- [ ] 现有测试用例全部通过
