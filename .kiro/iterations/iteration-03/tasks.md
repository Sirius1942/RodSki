# 任务列表 - Agent 集成增强

**迭代**: iteration-02
**更新时间**: 2026-03-27

## 任务概览

| 阶段 | 任务数 | 预估工时 | 状态 |
|------|--------|----------|------|
| Phase 1: 基础设施 | 5 | 3天 | 待开始 |
| Phase 2: API 入口 | 3 | 2天 | 待开始 |
| Phase 3: 关键字补全 | 2 | 1天 | 待开始 |
| Phase 4: 异常处理 | 4 | 2天 | 待开始 |
| Phase 5: 测试与文档 | 3 | 2天 | 待开始 |
| **总计** | **17** | **10天** | - |

---

## Phase 1: 基础设施

### T1.1 实现事件系统
**优先级**: P0
**预估**: 4h
**负责人**: TBD

**任务描述**:
- 创建 `rodski/core/events.py`
- 定义 `EventType` 枚举
- 实现 `ExecutionEvent` dataclass
- 实现 `EventEmitter` 类

**验收标准**:
- [ ] 支持注册多个回调
- [ ] 回调异常不中断执行
- [ ] 单元测试覆盖

---

### T1.2 实现 IncrementalResultWriter
**优先级**: P0
**预估**: 4h
**负责人**: TBD

**任务描述**:
- 创建 `rodski/core/result_writer.py`
- 实现 JSONL 增量写入
- 实现最终结果合并
- 处理异常退出恢复

**验收标准**:
- [ ] 每个 case 完成后立即写入
- [ ] 进程崩溃后可恢复已完成结果
- [ ] 单元测试覆盖
---

### T1.3 SKIExecutor 集成事件系统
**优先级**: P0
**预估**: 6h
**负责人**: TBD

**任务描述**:
- 修改 `SKIExecutor.__init__` 接受 `event_emitter` 参数
- 在 `execute_step` 前后发射 STEP_START/END 事件
- 在 `execute_case` 前后发射 CASE_START/END 事件
- 截图时发射 SCREENSHOT 事件

**验收标准**:
- [ ] 所有关键节点发射事件
- [ ] 事件包含完整上下文信息
- [ ] 现有测试不受影响

---

### T1.4 SKIExecutor 集成 RuntimeCommandQueue
**优先级**: P0
**预估**: 4h
**负责人**: TBD

**任务描述**:
- 修改 `SKIExecutor.__init__` 接受 `runtime_control` 参数
- 在每个步骤前检查 runtime_control 命令
- 实现 pause/insert/terminate 响应

**验收标准**:
- [ ] 支持外部注入 RuntimeCommandQueue
- [ ] pause 命令可暂停执行
- [ ] insert 命令可插入步骤
- [ ] terminate 命令可终止执行

---

### T1.5 集成 IncrementalResultWriter
**优先级**: P0
**预估**: 6h
**负责人**: TBD

**任务描述**:
- 修改 `execute_all_cases` 使用 IncrementalResultWriter
- 每个 case 完成后立即写入
- 全部完成后合并最终结果

**验收标准**:
- [ ] 中间结果实时写入 .jsonl 文件
- [ ] 最终生成完整 JSON 结果
- [ ] 临时文件正确清理

---

## Phase 2: API 入口

### T2.1 实现 RodSkiRunner
**优先级**: P1
**预估**: 6h
**负责人**: TBD

**任务描述**:
- 创建 `rodski/api/runner.py`
- 实现 `RodSkiRunner` 类
- 支持传入 event_callback 和 runtime_control
- 提供 `execute_case` 和 `execute_cases` 方法

**验收标准**:
- [ ] 可通过 Python 代码调用
- [ ] 支持事件回调
- [ ] 支持运行时控制
- [ ] 返回结构化结果

---

### T2.2 CLI 支持 runtime_control 注入
**优先级**: P1
**预估**: 4h
**负责人**: TBD

**任务描述**:
- 修改 `rodski_cli/run.py`
- 添加 `--runtime-control-socket` 参数
- 通过 socket/pipe 接收外部控制命令

**验收标准**:
- [ ] CLI 可接受外部 runtime_control
- [ ] 向后兼容（参数可选）
- [ ] 文档更新

---

### T2.3 集成测试
**优先级**: P1
**预估**: 6h
**负责人**: TBD

**任务描述**:
- 编写 Python API 集成测试
- 编写 CLI runtime_control 集成测试
- 验证事件回调正确触发

**验收标准**:
- [ ] API 调用测试通过
- [ ] CLI 控制测试通过
- [ ] 事件流验证通过

---

## Phase 3: 关键字补全

### T3.1 实现 click 关键字
**优先级**: P0
**预估**: 2h
**负责人**: TBD

**任务描述**:
- 在 `KeywordEngine` 添加 `_kw_click` 方法
- 更新 `SUPPORTED` 列表
- 添加单元测试

**验收标准**:
- [ ] click 关键字可执行
- [ ] 支持所有 driver 类型
- [ ] 测试覆盖

---

### T3.2 实现 screenshot 关键字
**优先级**: P0
**预估**: 2h
**负责人**: TBD

**任务描述**:
- 在 `KeywordEngine` 添加 `_kw_screenshot` 方法
- 更新 `SUPPORTED` 列表
- 支持自定义文件名
- 添加单元测试

**验收标准**:
- [ ] screenshot 关键字可执行
- [ ] 截图文件正确保存
- [ ] 测试覆盖

---

## Phase 4: 异常处理

### T4.1 修复 get_text 异常处理
**优先级**: P1
**预估**: 2h
**负责人**: TBD

**任务描述**:
- 修改 `PlaywrightDriver.get_text` 抛出异常而非返回 None
- 修改 `SeleniumDriver.get_text` 同样处理
- 更新相关测试

**验收标准**:
- [ ] 异常正确抛出
- [ ] 类型签名正确
- [ ] 测试覆盖

---

### T4.2 重构 is_critical_error
**优先级**: P1
**预估**: 3h
**负责人**: TBD

**任务描述**:
- 修改 `core/exceptions.py` 使用异常类型判断
- 定义 CRITICAL_EXCEPTIONS 元组
- 移除字符串匹配逻辑

**验收标准**:
- [ ] 使用 isinstance 判断
- [ ] 不再误判
- [ ] 测试覆盖

---

### T4.3 修复 verify 失败处理
**优先级**: P1
**预估**: 3h
**负责人**: TBD

**任务描述**:
- 修改 `_batch_verify` 失败时抛出异常
- 确保 `execute_step` 捕获并处理
- 触发正确的失败路径（截图、记录）

**验收标准**:
- [ ] verify 失败正确触发失败流程
- [ ] 截图和错误记录正确
- [ ] 测试覆盖

---

### T4.4 修复其他代码问题
**优先级**: P2
**预估**: 4h
**负责人**: TBD

**任务描述**:
- 修复 SQLite row_factory 无效代码
- 改进 Locator 转换 heuristic
- 清理其他 issue #2 中提到的小问题

**验收标准**:
- [ ] SQLite 连接正确配置
- [ ] Locator 转换更准确
- [ ] 代码质量提升

---

## Phase 5: 测试与文档

### T5.1 核心模块单元测试
**优先级**: P1
**预估**: 8h
**负责人**: TBD

**任务描述**:
- 为 `keyword_engine.py` 添加单元测试
- 为 `ski_executor.py` 添加单元测试
- 为 `case_parser.py` 添加单元测试
- 达到目标覆盖率

**验收标准**:
- [ ] keyword_engine 覆盖率 > 80%
- [ ] ski_executor 覆盖率 > 80%
- [ ] case_parser 覆盖率 > 70%

---

### T5.2 更新 API 文档
**优先级**: P1
**预估**: 4h
**负责人**: TBD

**任务描述**:
- 编写 RodSkiRunner API 文档
- 编写事件系统使用指南
- 更新 CLI 参数文档

**验收标准**:
- [ ] API 文档完整
- [ ] 包含代码示例
- [ ] 更新 README

---

### T5.3 Agent 集成示例
**优先级**: P1
**预估**: 4h
**负责人**: TBD

**任务描述**:
- 编写 OpenClaw Agent 集成示例
- 演示事件回调使用
- 演示运行时控制使用

**验收标准**:
- [ ] 示例代码可运行
- [ ] 覆盖主要使用场景
- [ ] 文档清晰

---

## 依赖关系

```
T1.1 (事件系统) → T1.3 (SKIExecutor集成事件)
T1.2 (ResultWriter) → T1.5 (集成ResultWriter)
T1.3, T1.4, T1.5 → T2.1 (RodSkiRunner)
T2.1 → T2.2 (CLI支持)
T2.1, T2.2 → T2.3 (集成测试)
所有 Phase 1-4 → T5.1 (单元测试)
所有 Phase 1-4 → T5.2 (文档)
T2.1 → T5.3 (Agent示例)
```

---

## 里程碑

- **M1 (Day 3)**: Phase 1 完成，基础设施就绪
- **M2 (Day 5)**: Phase 2 完成，API 可用
- **M3 (Day 6)**: Phase 3 完成，关键字补全
- **M4 (Day 8)**: Phase 4 完成，异常处理修复
- **M5 (Day 10)**: Phase 5 完成，测试与文档齐全
