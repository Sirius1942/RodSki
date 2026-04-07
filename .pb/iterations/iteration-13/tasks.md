# Iteration 13: 结构化日志 + 文档同步 — 任务清单

## 阶段一: Info 模式日志

### T13-001: 实现 Info 模式步骤日志
**文件**: `rodski/core/keyword_engine.py` 或 `rodski/core/logger.py`

- 每步执行后输出摘要行，格式：`[STEP N] action=xxx model=xxx status=OK capture={...}`
- auto_capture 结果在摘要中体现（字段名+值）
- named 写入（set）在摘要中体现
- 不输出内部解析细节

**预计**: 1.5h | **Owner**: 待分配

---

## 阶段二: Debug 模式日志

### T13-002: 实现 Debug 模式步骤日志
**文件**: `rodski/core/keyword_engine.py` 或 `rodski/core/logger.py`

- 参数解析链输出（模板替换前后）
- auto_capture 过程输出（字段名、locator/path、读取值）
- history/named 增量输出（每步执行后的变化）
- 失败类型区分：动作失败 / AutoCaptureError / 命名读取失败

**预计**: 2h | **Owner**: 待分配

---

## 阶段三: 结构化执行结果

### T13-003: 生成 execution_summary.json
**文件**: `rodski/core/result_writer.py`

- case 执行完成后写入结果目录 `execution_summary.json`
- 每步包含：`index`、`action`、`model`、`status`、`return_source`（keyword_result / auto_capture / get_named / evaluate）、`return_value`、`named_writes`
- 末尾包含 `context_snapshot.named`（最终命名变量快照）

**预计**: 1.5h | **Owner**: 待分配

---

## 阶段四: 文档同步更新

### T13-004: 更新 CORE_DESIGN_CONSTRAINTS.md
**文件**: `rodski/docs/CORE_DESIGN_CONSTRAINTS.md`

- 补充统一运行时上下文约束（对应规范 §10）
- 补充 Return / set / get / auto_capture / evaluate 的关系说明

**预计**: 1h | **Owner**: 待分配

### T13-005: 更新 TEST_CASE_WRITING_GUIDE.md
**文件**: `rodski/docs/TEST_CASE_WRITING_GUIDE.md`

- 补充 auto_capture 用法示例
- 补充 set/get 命名访问最佳实践
- 补充 evaluate 使用约束说明

**预计**: 1h | **Owner**: 待分配

### T13-006: 更新 AGENT_INTEGRATION.md
**文件**: `rodski/docs/AGENT_INTEGRATION.md`

- 补充 `execution_summary.json` 消费说明
- 补充 `return_source` 字段含义说明
- 补充 AI Agent 判断用例质量的参考指标

**预计**: 0.5h | **Owner**: 待分配

---

## 阶段五: 验证

### T13-007: 验证日志与结构化结果
**文件**: `rodski-demo` 示例用例

- 场景 E：Info 模式每步输出摘要，包含 auto_capture 和 named 写入信息
- 场景 F：Debug 模式可看到参数解析链、auto_capture 过程、history/named 增量
- 场景 G：`execution_summary.json` 存在，`return_source` 字段正确
- 回归：现有用例全部通过

**预计**: 1h | **Owner**: 待分配

---

## 任务汇总

| 任务 | 名称 | 预计 | 阶段 |
|------|------|------|------|
| T13-001 | Info 模式步骤日志 | 1.5h | 1 |
| T13-002 | Debug 模式步骤日志 | 2h | 2 |
| T13-003 | 生成 execution_summary.json | 1.5h | 3 |
| T13-004 | 更新 CORE_DESIGN_CONSTRAINTS.md | 1h | 4 |
| T13-005 | 更新 TEST_CASE_WRITING_GUIDE.md | 1h | 4 |
| T13-006 | 更新 AGENT_INTEGRATION.md | 0.5h | 4 |
| T13-007 | 验证日志与结构化结果 | 1h | 5 |

**总预计**: 8.5h
