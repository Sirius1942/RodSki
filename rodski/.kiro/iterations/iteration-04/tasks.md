# Iteration 04 任务清单

## Phase 1: 已有功能完善（已完成）

- T4-001: 实现 CLI JSON 输出 ✅
- T4-002: 设计错误信息格式 ✅
- T4-003: 编写 Skill 集成文档 ✅

## Phase 2: 测试用例可解释性（进行中）

- T4-004: TestCaseExplainer 核心类实现 ✅
- T4-005: 支持 17 个关键字的解释（navigate/launch/type/click/verify 等）✅
- T4-006: CLI explain 子命令实现 ✅
- T4-007: 敏感字段脱敏（password/pwd/secret/token → ***）✅
- T4-008: 批量 type 字段展开（model.xml + data.xml 联动）✅

## Phase 3: 异常处理与智能恢复（待完成）

### T4-009: 异常捕获框架
- 在 SKIExecutor 层面统一捕获 StepExecutionError
- 定义异常类型体系：ElementNotFoundError / NetworkError / AssertionFailedError / StepTimeoutError / PageCrashError
- 记录失败上下文（URL、步骤索引、模型、数据）
- 失败时自动截图
**预计**: 8h

### T4-010: AIScreenshotVerifier 视觉诊断器
- 实现 `vision/ai_verifier.py`
- 接收截图路径 + 问题描述，返回分析结果
- 支持多种视觉模型（Claude / OpenAI / Qwen）
- 实现 `analyze_recording()` 函数（从录像提取关键帧分析）
**预计**: 12h

### T4-011: DiagnosisEngine 诊断引擎
- 实现 `core/diagnosis_engine.py`
- 接收异常上下文 + 截图，生成诊断报告
- 分析失败原因、视觉判断、建议动作
- 支持扩展自定义诊断规则
**预计**: 8h

### T4-012: RecoveryEngine 恢复引擎
- 实现 `core/recovery_engine.py`
- 预定义恢复动作（wait/refresh/screenshot 等）
- 支持动态步骤插入
- 支持自定义恢复策略配置
**预计**: 8h

### T4-013: 配置项更新
- 更新 `config/default_config.yaml`
- 添加 execution.recovery_* 配置项
- 添加 screen_record 配置项
**预计**: 4h

### T4-014: Result XML 增强
- 在 result.xsd 中新增 diagnosis 节点
- 在 SKIExecutor 中写入诊断信息
- 生成结构化诊断报告
**预计**: 4h

### T4-015: 长时间执行稳定性保障
- 实现浏览器定期回收机制（每 N 步重启）
  - 在 `SKIExecutor` 中维护步数计数器 `self._step_count`
  - 配置项 `browser_restart_interval`（默认 50 步）触发 `driver.restart()`
  - 重启前自动保存当前 URL，重启后通过 `navigate` 恢复页面
  - 重启后重新绑定元素引用，避免 StaleElementError
- 实现执行快照保存（每 N 步）
  - 快照内容：当前步骤索引、变量上下文、页面 URL、DOM 状态摘要（可选）
  - 快照格式：`{case_id}_snapshot_{step_index}.json`，存入 `output/snapshots/`
  - 异常时自动加载最近快照，支持从快照点恢复执行（可选 feature）
- 添加内存泄漏监控和 GC 触发
  - 每 10 步记录 `tracemalloc.get_traced_memory()`
  - 内存增长超过阈值（默认 100MB）时主动触发 `gc.collect()`
  - 日志记录内存状态：`[MemoryMonitor] step=50, current=85MB, delta=+12MB`
**预计**: 8h

### T4-016: 集成测试
- 编写异常处理集成测试用例
- 测试动态步骤插入
- 测试视觉诊断流程
**预计**: 8h

## Phase 4: 文档与示例

- T4-017: 更新 QUICKSTART.md（新增 explain 和异常恢复说明）
- T4-018: 编写 Exception Handling 最佳实践文档
- T4-019: 提供完整的使用示例
