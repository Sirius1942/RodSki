# Iteration 05: 活文档增强 — 需求文档

**周期**: 2026-04-20 ~ 2026-05-03 (2 周)  
**目标**: 让测试结果成为可追溯、可分析、可视化的活文档

---

## 背景

RodSki 当前的 Result XML 侧重于**通过/失败**状态记录，缺乏细粒度的执行信息和元数据支撑。在实际测试工程中，团队需要：

1. 从用例 XML 中提取标签、优先级、组件类型等元数据，用于测试报告分层
2. 在结果中记录每一步的详细耗时和执行状态，用于性能分析和慢用例定位
3. 跨多次运行聚合统计通过率、 flaky 用例识别、耗时趋势，用于质量评估

Iteration 05 聚焦上述三个方向，实现测试结果从**静态日志**到**活文档**的升级。

---

## 功能需求

### F5-1: XML 元数据支持

#### F5-1.1: 用例 XML 元数据Schema扩展
在 `schemas/case.xsd` 中扩展 `<case>` 根元素，支持以下可选属性/子元素：

| 元数据字段 | 类型 | 说明 |
|-----------|------|------|
| `priority` | enum (P0/P1/P2/P3) | 用例优先级 |
| `tags` | string (逗号分隔) | 用例标签，如 `login,smoke,ui` |
| `component` | string | 所属组件/模块 |
| `component_type` | enum (UI/API/DB/Integration) | 组件类型 |
| `author` | string | 用例作者 |
| `create_time` | xs:dateTime | 创建时间 |
| `modify_time` | xs:dateTime | 修改时间 |
| `estimated_duration` | xs:integer (秒) | 预估执行时长 |
| `requirement_id` | string | 关联需求 ID |
| `test_type` | enum (Functional/Regression/Smoke/Performance) | 测试类型 |

**约束**:
- 所有新字段均为 `optional`，向后兼容现有用例 XML
- `tags` 允许空值或逗号分隔的多个标签

#### F5-1.2: 元数据提取器
**实现文件**: `core/case_metadata.py`

实现 `CaseMetadata` 类，从 case XML 中解析上述元数据：

```python
@dataclass
class CaseMetadata:
    case_id: str
    priority: Optional[str] = None        # P0/P1/P2/P3
    tags: List[str] = field(default_factory=list)
    component: Optional[str] = None
    component_type: Optional[str] = None   # UI/API/DB/Integration
    author: Optional[str] = None
    create_time: Optional[str] = None
    modify_time: Optional[str] = None
    estimated_duration: Optional[int] = None
    requirement_id: Optional[str] = None
    test_type: Optional[str] = None

    @classmethod
    def from_xml(cls, case_root: Etree) -> "CaseMetadata": ...
    def to_dict(self) -> Dict[str, Any]: ...
```

#### F5-1.3: CLI 元数据展示
`rodski run` 执行时自动解析并输出用例元数据摘要：

```
$ rodski run case/login.xml
[INFO] Case: login_test (P1) [smoke,ui] component=auth.UI estimated=30s
```

`rodski explain` 时在头部显示元数据：

```
用例: login_test
优先级: P1
标签: smoke, ui
组件: auth.UI
类型: Functional
作者: zhangsan
```

### F5-2: 结果反馈增强

#### F5-2.1: 增强型 Result XML Schema
**更新文件**: `schemas/result.xsd`

在 `<step>` 节点中新增以下属性：

| 字段 | 类型 | 说明 |
|------|------|------|
| `@start_time` | xs:dateTime | 步骤开始时间（ISO 8601） |
| `@end_time` | xs:dateTime | 步骤结束时间（ISO 8601） |
| `@duration_ms` | xs:long | 步骤耗时（毫秒） |
| `@attempt` | xs:integer | 本步骤重试次数 |
| `@status` | enum (pass/fail/skip/retry) | 步骤状态 |

`<step>` 节点新增子元素:

```xml
<step index="1" keyword="click" start_time="2026-04-20T10:00:00Z" end_time="2026-04-20T10:00:01.234Z" duration_ms="1234" attempt="0" status="pass">
  <input>
    <param name="locator">#submit-btn</param>
  </input>
  <output>
    <result>Element clicked successfully</result>
    <screenshot>results/screenshots/step_001.png</screenshot>
  </output>
  <!-- 新增: 步骤级元数据 -->
  <metadata>
    <browser>Chrome 120</browser>
    <viewport>1920x1080</viewport>
    <url>https://example.com/login</url>
  </metadata>
</step>
```

#### F5-2.2: 失败步骤详细上下文
失败步骤增加以下信息：

```xml
<failure_context>
  <page_source_snapshot>results/page_sources/step_005.html</page_source_snapshot>
  <console_logs>results/console/step_005.log</console_logs>
  <network_requests>results/network/step_005.json</network_requests>
  <variable_snapshot>
    <var name="username">admin</var>
    <var name="page_title">Login Page</var>
  </variable_snapshot>
</failure_context>
```

#### F5-2.3: AI 诊断结果嵌入
当启用 AI 诊断时，在 Result XML 中嵌入诊断报告：

```xml
<diagnosis ai_model="claude" diagnosis_time_ms="1523.4">
  <failure_point>Step 5: click #submit-btn</failure_point>
  <failure_reason>元素在点击时变为不可点击状态（StaleElementError）</failure_reason>
  <visual_analysis>页面显示登录表单，但提交按钮因网络请求 pending 状态而暂时禁用</visual_analysis>
  <suggestion>建议在点击前添加 wait_for_element_clickable 等待条件</suggestion>
  <recovery_action action="wait" data="2" />
</diagnosis>
```

### F5-3: 执行统计分析

#### F5-3.1: 统计聚合器
**实现文件**: `core/statistics_collector.py`

实现 `StatisticsCollector` 类，从多次运行的 Result XML 中聚合统计数据：

```python
@dataclass
class StepStatistics:
    keyword: str
    count: int
    pass_count: int
    fail_count: int
    avg_duration_ms: float
    min_duration_ms: float
    max_duration_ms: float
    p50_duration_ms: float
    p95_duration_ms: float
    p99_duration_ms: float

@dataclass
class CaseStatistics:
    case_id: str
    run_count: int
    pass_count: int
    fail_count: int
    skip_count: int
    pass_rate: float
    avg_duration_ms: float
    step_stats: List[StepStatistics]

class StatisticsCollector:
    def __init__(self, result_dir: str): ...
    def add_result(self, result_xml_path: str) -> None: ...
    def aggregate(self) -> Dict[str, Any]: ...
    def get_flaky_cases(self, threshold: float = 0.3) -> List[str]: ...
    def export_json(self, output_path: str) -> None: ...
```

#### F5-3.2: 统计报告生成
**CLI 命令**: `rodski stats <result_dir>`

输出格式:

```
===== RodSki Execution Statistics =====
Period: 2026-04-01 ~ 2026-04-30
Total Runs: 120
Total Cases: 45
========================================

Overall Pass Rate: 87.3% (104/120)

By Priority:
  P0: 95.2% (20/21)
  P1: 88.1% (56/63)
  P2: 78.3% (18/23)
  P3: 100%  (10/10)

By Component:
  auth.UI:       92.1% (32/34)
  payment.API:   84.6% (44/52)
  order.DB:      75.0%  (6/8)

Flaky Cases (pass rate < 70%):
  - TC_ORDER_003: 50.0% (3/6)
  - TC_PAY_007:   66.7% (2/3)

Slowest Cases (avg > 60s):
  - TC_AUTH_012:  78.3s (smoke test)
  - TC_ORDER_009:  65.1s (integration)
```

#### F5-3.3: 历史趋势 API
支持导出 JSON 格式的时间序列数据，供 Grafana 等工具消费：

```json
{
  "generated_at": "2026-04-30T12:00:00Z",
  "period": {"start": "2026-04-01", "end": "2026-04-30"},
  "daily_trend": [
    {"date": "2026-04-01", "pass_rate": 0.85, "total": 5, "passed": 4},
    {"date": "2026-04-02", "pass_rate": 0.90, "total": 6, "passed": 5}
  ],
  "by_priority": {
    "P0": {"pass_rate": 0.95, "trend": "stable"},
    "P1": {"pass_rate": 0.88, "trend": "+0.03"}
  }
}
```

---

## 非功能需求

### 性能
- 元数据提取应在用例解析阶段完成，不增加执行阶段开销
- 统计聚合器处理 1000 个 Result 文件应在 10 秒内完成

### 兼容性
- 所有 Schema 扩展均为可选字段，不破坏现有用例 XML
- 向后兼容现有的 Result XML 格式

### 可扩展性
- 元数据字段支持未来扩展（预留 `custom_fields` 节点）
- 统计聚合器支持插件式接入新的度量指标

---

## 里程碑

| 阶段 | 交付物 | 目标日期 |
|------|--------|---------|
| M5-1 | case.xsd 扩展 + CaseMetadata 提取器 | 2026-04-24 |
| M5-2 | Result XML 步骤级增强 + 失败上下文 | 2026-04-28 |
| M5-3 | StatisticsCollector + stats CLI | 2026-05-01 |
| M5-4 | 集成测试 + 文档 | 2026-05-03 |
