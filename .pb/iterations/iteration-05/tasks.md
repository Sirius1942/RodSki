# Iteration 05: 活文档增强 — 任务清单

## 阶段一: XML 元数据支持

### T5-001: Case XSD 元数据扩展
**文件**: `schemas/case.xsd`

- 在 `<case>` 根元素上新增可选属性: `priority`, `component`, `component_type`
- 新增 `<metadata>` 子元素，包含: `tag`(可多个), `author`, `create_time`, `modify_time`, `estimated_duration`, `requirement_id`, `test_type`
- 预留 `<xs:any>` 扩展点供未来自定义字段
- 编写 XSD 变更的单元测试，验证向后兼容
**预计**: 4h | **Owner**: 待分配

### T5-002: CaseMetadata 数据类
**文件**: `core/case_metadata.py`

- 实现 `CaseMetadata` dataclass，字段与 XSD 对应
- 实现 `from_xml(root: Etree) -> CaseMetadata` 类方法
- 实现 `to_dict() -> Dict` 方法
- 解析失败时返回默认值，不抛异常
- 提取 `tags` 时按逗号分割为 List[str]
**预计**: 4h | **Owner**: 待分配

### T5-003: CaseMetadataExtractor 提取器
**文件**: `core/case_metadata.py`

- 实现 `CaseMetadataExtractor` 类
- `extract(case_path: str) -> CaseMetadata`
- `extract_batch(case_dir: str) -> Dict[str, CaseMetadata]`
- 集成 XML Schema 验证（使用 `core/xml_schema_validator.py`）
- 在 SKIExecutor 初始化时创建 extractor 实例
**预计**: 4h | **Owner**: 待分配

### T5-004: CLI 元数据展示
**文件**: `core/cli.py` / `core/test_runner.py`

- `rodski run` 执行时解析并显示元数据摘要行
- `rodski explain` 在头部显示完整元数据（优先级/标签/组件/类型/作者）
- 元数据也写入 result.xml 的 `<case>` 节点属性
**预计**: 4h | **Owner**: 待分配

---

## 阶段二: 结果反馈增强

### T5-005: Result XSD 步骤级扩展
**文件**: `schemas/result.xsd`

- 在 `<step>` 节点新增属性: `start_time`, `end_time`, `duration_ms`, `attempt`, `status`
- 新增 `<step_metadata>` 子元素: `browser`, `viewport`, `url`
- 新增 `<failure_context>` 子元素: `page_source_snapshot`, `console_logs`, `network_requests`, `variable_snapshot`
- 编写 XSD 单元测试，验证向后兼容
**预计**: 4h | **Owner**: 待分配

### T5-006: ResultWriter 步骤耗时增强
**文件**: `core/result_writer.py`

- 扩展 `write_step_result()` 方法，新增参数: `start_time`, `end_time`, `duration_ms`, `attempt`, `status`, `metadata`
- 在 `SKIExecutor._execute_step()` 的步骤开始/结束时记录时间戳
- 当 `record_step_timing: true` 时启用
**预计**: 8h | **Owner**: 待分配

### T5-007: 失败上下文捕获
**文件**: `core/ski_executor.py`

- 实现 `_capture_failure_context(step_index) -> Dict`
- 捕获 page_source → `page_sources/{prefix}.html`
- 捕获 console logs → `console/{prefix}.log`
- 捕获 network requests → `network/{prefix}.json`
- 捕获当前变量快照 → `<variable_snapshot>`
- 写入 result.xml 的 `<failure_context>` 节点
**预计**: 8h | **Owner**: 待分配

### T5-008: 诊断结果嵌入 Result XML
**文件**: `core/result_writer.py`

- 扩展 `write_diagnosis(diagnosis: DiagnosisReport)` 方法
- 将 DiagnosisReport 的所有字段写入 `<diagnosis>` 节点
- AI 诊断时间 `diagnosis_time_ms` 写入属性
- 当 `embed_diagnosis: true` 时启用
**预计**: 4h | **Owner**: 待分配

### T5-009: Case 元数据写入 Result
**文件**: `core/result_writer.py`

- 扩展 `write_case_metadata(metadata: CaseMetadata)` 方法
- 将 CaseMetadata 字段写入 result.xml 的 `<case metadata="...">` 属性
- `tags` 以逗号分隔写入属性值
**预计**: 2h | **Owner**: 待分配

---

## 阶段三: 执行统计分析

### T5-010: 统计数据结构
**文件**: `core/statistics_collector.py`

- 实现 `StepStatistics` dataclass: keyword / count / pass/fail/skip / durations_ms / avg / p50/p95/p99
- 实现 `CaseStatistics` dataclass: case_id / run_count / pass/fail/skip / pass_rate / avg_duration / step_stats
- 实现 `RunStatistics` dataclass: run_id / run_time / total/passed/failed/skipped / pass_rate / total_duration
- 实现 `AggregatedStatistics` dataclass: 聚合所有统计
**预计**: 4h | **Owner**: 待分配

### T5-011: StatisticsCollector 聚合器
**文件**: `core/statistics_collector.py`

- 实现 `StatisticsCollector` 类
- `add_result(result_xml_path: str)`: 解析单个 result.xml 并累积
- `aggregate() -> AggregatedStatistics`: 执行聚合计算
- `get_flaky_cases(threshold) -> List[str]`: 识别 flaky 用例
- `export_json(output_path)`: 导出 JSON 格式统计报告
- 支持按日期范围过滤 (`date_from`, `date_to`)
**预计**: 8h | **Owner**: 待分配

### T5-012: stats CLI 命令
**文件**: `core/cli.py`

- 实现 `rodski stats <result_dir>` 命令
- 选项: `--from`, `--to`, `--format` (terminal/json), `--output`, `--flaky-only`, `--top-slow N`
- Terminal 格式输出统计摘要（通过率 / 按优先级 / 按组件 / Flaky / 最慢用例）
- JSON 格式输出完整时间序列数据
**预计**: 8h | **Owner**: 待分配

### T5-013: 趋势分析
**文件**: `core/statistics_collector.py`

- 实现 `daily_trend` 时间序列数据生成
- 计算 `by_priority` 和 `by_component` 分组统计
- 计算环比变化 (`trend`: stable/+0.03/-0.05)
- 支持 Grafana 消费的 JSON 格式导出
**预计**: 4h | **Owner**: 待分配

---

## 阶段四: 集成与文档

### T5-014: 配置项集成
**文件**: `config/default_config.yaml`

- 新增 `result.record_step_timing: true`
- 新增 `result.capture_failure_context: true`
- 新增 `result.embed_diagnosis: true`
- 新增 `metadata.extract_from_case: true`
- 新增 `metadata.show_in_cli: true`
- 新增 `statistics.result_dir`, `statistics.flaky_threshold`, `statistics.top_slow_count`
**预计**: 2h | **Owner**: 待分配

### T5-015: 集成测试
**文件**: `tests/integration/test_live_document.py`

- 测试 CaseMetadataExtractor 正常解析和缺失字段降级
- 测试 ResultWriter 步骤耗时记录
- 测试失败上下文捕获（page_source / console / network）
- 测试 StatisticsCollector 聚合多个 result.xml
- 测试 Flaky case 识别逻辑
- 测试 stats CLI 输出格式
**预计**: 8h | **Owner**: 待分配

### T5-016: 文档更新
**文件**: `docs/user-guides/RESULT_REPORT_GUIDE.md` (新)

- 编写 Result XML Schema 说明文档
- 编写元数据提取使用指南
- 编写 StatisticsCollector 使用说明
- 编写 `rodski stats` CLI 使用示例
- 更新 QUICKSTART.md 添加统计相关章节
**预计**: 4h | **Owner**: 待分配

---

## 任务汇总

| 任务 | 名称 | 预计 | 阶段 |
|------|------|------|------|
| T5-001 | Case XSD 元数据扩展 | 4h | 1 |
| T5-002 | CaseMetadata 数据类 | 4h | 1 |
| T5-003 | CaseMetadataExtractor 提取器 | 4h | 1 |
| T5-004 | CLI 元数据展示 | 4h | 1 |
| T5-005 | Result XSD 步骤级扩展 | 4h | 2 |
| T5-006 | ResultWriter 步骤耗时增强 | 8h | 2 |
| T5-007 | 失败上下文捕获 | 8h | 2 |
| T5-008 | 诊断结果嵌入 Result XML | 4h | 2 |
| T5-009 | Case 元数据写入 Result | 2h | 2 |
| T5-010 | 统计数据结构 | 4h | 3 |
| T5-011 | StatisticsCollector 聚合器 | 8h | 3 |
| T5-012 | stats CLI 命令 | 8h | 3 |
| T5-013 | 趋势分析 | 4h | 3 |
| T5-014 | 配置项集成 | 2h | 4 |
| T5-015 | 集成测试 | 8h | 4 |
| T5-016 | 文档更新 | 4h | 4 |

**总预计**: 80h
