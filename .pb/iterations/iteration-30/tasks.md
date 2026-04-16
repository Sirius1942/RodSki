# Iteration 30 — 任务清单

## Wave 1（并行）

### T30-001: WI-63 Case Tag 选择性执行 (预计 45min)

**文件**: `rodski/schemas/case.xsd`, `rodski/core/case_parser.py`, `rodski/core/ski_executor.py`, `rodski/rodski_cli/run.py`

**任务**:
1. case.xsd: case 元素新增 `tags`（可选，逗号分隔）和 `priority`（可选，P0-P3）属性
2. case_parser.py: 解析 tags 和 priority 属性，加入 case dict
3. ski_executor.py: 执行前按 tags/priority 过滤 case 列表
4. run.py: CLI 新增 `--tags` 和 `--priority` 和 `--exclude-tags` 参数
5. 编写单元测试

**验收**:
- [ ] `rodski run case/ --tags smoke` 只执行带 smoke tag 的用例
- [ ] `rodski run case/ --priority P0` 只执行 P0 用例
- [ ] 无 tag/priority 属性时行为不变（向后兼容）

---

### T30-002: WI-64 两层 if/else + elif (预计 45min)

**文件**: `rodski/schemas/case.xsd`, `rodski/core/dynamic_executor.py`

**任务**:
1. case.xsd: 新增 `elif` 元素，if 内部允许嵌套一层 if
2. dynamic_executor.py: 支持 elif 评估，支持最多 2 层嵌套 if
3. 编写单元测试

**验收**:
- [ ] elif 条件正确评估
- [ ] 两层嵌套 if 正确执行
- [ ] 3 层嵌套被拒绝（schema 或运行时报错）

---

### T30-003: WI-40 报告数据模型与收集器 (预计 60min)

**文件**: NEW `rodski/report/__init__.py`, `rodski/report/data_model.py`, `rodski/report/collector.py`

**任务**:
1. 创建 `rodski/report/` 目录和 `__init__.py`
2. data_model.py: 定义 ReportData/CaseReport/PhaseReport/StepReport dataclass
3. collector.py: Hook 到 SKIExecutor，收集每步的时间/状态/截图/Return
4. 输出 report_data.json
5. 编写单元测试

**验收**:
- [ ] 执行 rodski-demo 后生成 report_data.json
- [ ] JSON 结构完整：总览 + 每 case + 每 phase + 每 step

---

### T30-004: WI-50 Execution Trace 层 (预计 60min)

**文件**: NEW `rodski/observability/__init__.py`, `rodski/observability/tracer.py`, `rodski/observability/span.py`, `rodski/observability/metrics.py`, `rodski/observability/exporter.py`

**任务**:
1. 创建 `rodski/observability/` 目录
2. span.py: Span dataclass（name, start, end, attributes, children）
3. tracer.py: `@trace_span` 装饰器 + global tracer
4. metrics.py: 指标收集（counter/histogram）
5. exporter.py: 导出 JSON（兼容 OpenTelemetry 格式）
6. 编写单元测试

**验收**:
- [ ] `@trace_span` 装饰器可用
- [ ] 执行后生成 trace JSON
- [ ] Span 层级关系正确

---

### T30-005: WI-62 Network Interception (预计 45min)

**文件**: NEW `rodski/builtins/__init__.py`, `rodski/builtins/network_ops.py`

**任务**:
1. 创建 `rodski/builtins/` 目录和 `__init__.py`（注册表）
2. network_ops.py: mock_route / wait_for_response / clear_routes
3. keyword_engine._kw_run() 增加 builtins 注册表查询逻辑
4. 编写单元测试

**验收**:
- [ ] `run mock_route(...)` 可 mock API 响应
- [ ] `run clear_routes()` 清除所有 mock
- [ ] 非 Playwright driver 调用时优雅报错

---

### T30-006: WI-60 Agent 记忆层 (预计 45min)

**文件**: NEW `rodski-agent/src/rodski_agent/common/memory_store.py`

**任务**:
1. 创建 memory_store.py（SQLite 实现）
2. fix_patterns 表：失败模式 + 修复策略 + 置信度
3. app_models 表：应用模型缓存
4. 淘汰策略：confidence < 0.3 且 30d 未使用自动清理
5. 编写单元测试

**验收**:
- [ ] 写入和查询 fix_patterns 正确
- [ ] 置信度计算 success/(success+fail) 正确
- [ ] 淘汰策略工作

---

### T30-007: WI-61 set/get 一等公民化 (预计 20min)

**文件**: `rodski/docs/TEST_CASE_WRITING_GUIDE.md`, `rodski/docs/AGENT_INTEGRATION.md`

**任务**:
1. TEST_CASE_WRITING_GUIDE.md: 新增 set/get 推荐用法章节，标注 Return 索引为"进阶用法"
2. AGENT_INTEGRATION.md: 推荐 Agent 生成 XML 时优先使用 set/get

**验收**:
- [ ] 文档中 set/get 作为首选变量传递方式
- [ ] Return 索引仍然支持但标注为进阶

---

## Wave 2（依赖 Wave 1）

### T30-008: WI-41 HTML 报告生成器 (预计 90min)

**依赖**: T30-003 (WI-40)

### T30-009: WI-42 历史趋势与缺陷聚合 (预计 45min)

**依赖**: T30-003 (WI-40)

### T30-010: WI-44 Agent 诊断修复可视化 (预计 30min)

**依赖**: T30-008 (WI-41)

### T30-011: WI-43 CLI 集成 (预计 30min)

**依赖**: T30-008 (WI-41)

### T30-012: WI-51 LLM Token 计量 (预计 30min)

**依赖**: 无（但逻辑上 Wave 2）

## Wave 3（依赖 Wave 2）

### T30-013: WI-52 Agent KPI 评估框架 (预计 60min)

**依赖**: T30-004 (WI-50), T30-012 (WI-51)

### T30-014: WI-53 Agent vs 通用 Agent 对比 (预计 30min)

**依赖**: T30-013 (WI-52)
