# Iteration 05: 活文档增强 — 设计文档

---

## 设计目标

1. **零破坏性扩展**: 所有新字段均为 optional，不影响现有 XML Schema 和解析逻辑
2. **统一数据流**: 元数据从 case XML → 执行上下文 → result XML → 统计报告，全链路打通
3. **按需启用**: AI 诊断结果嵌入、步骤级耗时记录等均为可选功能，通过配置控制

---

## 一、Case XML 元数据扩展

### 1.1 Schema 变更

**文件**: `schemas/case.xsd`

在 `<case>` 根元素中新增属性和子元素：

```xml
<xs:element name="case">
  <xs:complexType>
    <xs:sequence>
      <xs:element ref="description" minOccurs="0"/>
      <xs:element ref="pre_process" minOccurs="0"/>
      <xs:element ref="test_case"/>
      <xs:element ref="post_process" minOccurs="0"/>
      <!-- 新增: 元数据子元素 -->
      <xs:element ref="metadata" minOccurs="0"/>
    </xs:sequence>
    <!-- 新增: 根元素属性 -->
    <xs:attribute name="priority" type="xs:string" use="optional"/>
    <xs:attribute name="component" type="xs:string" use="optional"/>
    <xs:attribute name="component_type" type="xs:string" use="optional"/>
  </xs:complexType>
</xs:element>

<!-- 新增: metadata 子元素 -->
<xs:element name="metadata">
  <xs:complexType>
    <xs:sequence>
      <xs:element name="tag" type="xs:string" minOccurs="0" maxOccurs="unbounded"/>
      <xs:element name="author" type="xs:string" minOccurs="0"/>
      <xs:element name="create_time" type="xs:dateTime" minOccurs="0"/>
      <xs:element name="modify_time" type="xs:dateTime" minOccurs="0"/>
      <xs:element name="estimated_duration" type="xs:integer" minOccurs="0"/>
      <xs:element name="requirement_id" type="xs:string" minOccurs="0"/>
      <xs:element name="test_type" type="xs:string" minOccurs="0"/>
      <!-- 预留: 自定义扩展字段 -->
      <xs:any namespace="##other" minOccurs="0" maxOccurs="unbounded" processContents="skip"/>
    </xs:sequence>
  </xs:complexType>
</xs:element>
```

### 1.2 CaseMetadata 提取器

**文件**: `core/case_metadata.py`

设计思路:
- `CaseMetadata` 作为纯数据类（dataclass），无状态
- `from_xml()` 静态方法解析 XML Element → CaseMetadata 实例
- 解析失败时返回默认值（不抛异常），保证向后兼容

```python
class CaseMetadataExtractor:
    def __init__(self, schema_path: Optional[str] = None):
        self._validator = XmlSchemaValidator(schema_path) if schema_path else None

    def extract(self, case_path: str) -> CaseMetadata:
        tree = Etree.parse(case_path)
        root = tree.getroot()
        return CaseMetadata.from_xml(root)

    def extract_batch(self, case_dir: str) -> Dict[str, CaseMetadata]:
        """批量提取目录下所有 case XML 的元数据"""
        ...
```

### 1.3 与 SKIExecutor 的集成

在 `SKIExecutor.__init__()` 中:
```python
self._metadata_extractor = CaseMetadataExtractor()
self._case_metadata = self._metadata_extractor.extract(case_path)
```

在 `SKIExecutor._execute_step()` 中记录步骤耗时:
```python
step_start = datetime.now()
# ... 执行步骤 ...
step_end = datetime.now()
step_result.duration_ms = (step_end - step_start).total_seconds() * 1000
step_result.start_time = step_start.isoformat()
step_result.end_time = step_end.isoformat()
```

---

## 二、Result XML 增强

### 2.1 Schema 变更

**文件**: `schemas/result.xsd`

扩展 `<step>` 复杂类型：

```xml
<xs:complexType name="StepType">
  <xs:sequence>
    <xs:element ref="input" minOccurs="0"/>
    <xs:element ref="output" minOccurs="0"/>
    <xs:element ref="metadata" minOccurs="0"/>   <!-- 新增 -->
    <xs:element ref="failure_context" minOccurs="0"/>  <!-- 新增 -->
  </xs:sequence>
  <!-- 新增属性 -->
  <xs:attribute name="start_time" type="xs:dateTime" use="optional"/>
  <xs:attribute name="end_time" type="xs:dateTime" use="optional"/>
  <xs:attribute name="duration_ms" type="xs:long" use="optional"/>
  <xs:attribute name="attempt" type="xs:integer" use="optional" default="0"/>
  <xs:attribute name="status" type="xs:string" use="optional"/>
</xs:complexType>

<!-- 新增: metadata 子元素 -->
<xs:element name="step_metadata">
  <xs:complexType>
    <xs:all>
      <xs:element name="browser" type="xs:string" minOccurs="0"/>
      <xs:element name="viewport" type="xs:string" minOccurs="0"/>
      <xs:element name="url" type="xs:string" minOccurs="0"/>
    </xs:all>
  </xs:complexType>
</xs:element>

<!-- 新增: failure_context 子元素 -->
<xs:element name="failure_context">
  <xs:complexType>
    <xs:all>
      <xs:element name="page_source_snapshot" type="xs:string" minOccurs="0"/>
      <xs:element name="console_logs" type="xs:string" minOccurs="0"/>
      <xs:element name="network_requests" type="xs:string" minOccurs="0"/>
      <xs:element name="variable_snapshot" minOccurs="0"/>
    </xs:all>
  </xs:complexType>
</xs:element>
```

### 2.2 ResultWriter 增强

**文件**: `core/result_writer.py`

扩展 `ResultWriter` 类:

```python
class ResultWriter:
    def write_step_result(
        self,
        step_index: int,
        keyword: str,
        status: str,           # pass/fail/skip/retry
        start_time: str,       # ISO 8601
        end_time: str,
        duration_ms: int,
        attempt: int = 0,
        metadata: Optional[Dict] = None,
        failure_context: Optional[Dict] = None,
    ) -> None: ...

    def write_diagnosis(self, diagnosis: DiagnosisReport) -> None: ...

    def write_case_metadata(self, metadata: CaseMetadata) -> None: ...
```

步骤状态枚举:
```python
class StepStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    RETRY = "retry"
```

### 2.3 失败上下文捕获

在 `SKIExecutor._handle_step_failure()` 中:

```python
def _capture_failure_context(self, step_index: int) -> Dict[str, Any]:
    context = {
        "page_source_snapshot": self._save_page_source(f"step_{step_index}"),
        "console_logs": self._save_console_logs(f"step_{step_index}"),
        "network_requests": self._save_network_requests(f"step_{step_index}"),
        "variable_snapshot": dict(self._variables),  # 当前变量上下文
    }
    return context

def _save_page_source(self, prefix: str) -> Optional[str]:
    try:
        path = Path(self._result_dir) / "page_sources" / f"{prefix}.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._driver.page_source)
        return str(path)
    except Exception:
        return None
```

---

## 三、统计分析

### 3.1 StatisticsCollector 设计

**文件**: `core/statistics_collector.py`

数据结构设计：

```python
@dataclass
class RunStatistics:
    """单次运行的统计"""
    run_id: str
    run_time: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    skipped_cases: int
    pass_rate: float
    total_duration_ms: int

@dataclass
class StepStatistics:
    """按关键字聚合的步骤统计"""
    keyword: str
    total_count: int
    pass_count: int
    fail_count: int
    skip_count: int
    durations_ms: List[int]  # 用于计算百分位数

    @property
    def avg_duration_ms(self) -> float: ...
    @property
    def p50_duration_ms(self) -> int: ...
    @property
    def p95_duration_ms(self) -> int: ...
    @property
    def p99_duration_ms(self) -> int: ...

@dataclass
class AggregatedStatistics:
    """聚合后的完整统计"""
    runs: List[RunStatistics]
    case_stats: Dict[str, CaseStatistics]  # case_id → stats
    priority_stats: Dict[str, float]        # priority → pass_rate
    component_stats: Dict[str, float]      # component → pass_rate
    keyword_stats: Dict[str, StepStatistics]
    flaky_cases: List[str]  # pass_rate < threshold 的 case_id
```

### 3.2 百分位数计算

使用 `statistics` 模块计算耗时百分位数：

```python
import statistics

def percentile(data: List[int], p: float) -> int:
    sorted_data = sorted(data)
    index = int(len(sorted_data) * p / 100)
    return sorted_data[min(index, len(sorted_data) - 1)]
```

### 3.3 Flaky Case 识别

```python
def identify_flaky_cases(
    case_stats: Dict[str, CaseStatistics],
    threshold: float = 0.3,  # 通过率 < 30% 判定为 flaky
) -> List[str]:
    flaky = []
    for case_id, stats in case_stats.items():
        if stats.run_count >= 3 and stats.pass_rate < threshold:
            flaky.append(case_id)
    return flaky
```

### 3.4 stats CLI 命令

```python
# rodski stats results/2026-04/
#   --from 2026-04-01 --to 2026-04-30
#   --format terminal  (默认)
#   --format json --output stats.json
#   --flaky-only
#   --top-slow 10

@click.command()
@click.argument("result_dir", type=click.Path(exists=True))
@click.option("--from", "date_from", help="起始日期 (YYYY-MM-DD)")
@click.option("--to", "date_to", help="结束日期 (YYYY-MM-DD)")
@click.option("--format", "output_format", default="terminal", type=click.Choice(["terminal", "json"]))
@click.option("--output", "-o", "output_file", help="输出文件路径")
@click.option("--flaky-only", is_flag=True, help="仅显示 flaky 用例")
@click.option("--top-slow", type=int, help="显示最慢的 N 个用例")
def stats(result_dir, date_from, date_to, output_format, output_file, flaky_only, top_slow): ...
```

### 3.5 时间序列导出

```json
{
  "generated_at": "2026-04-30T12:00:00Z",
  "period": {"start": "2026-04-01", "end": "2026-04-30"},
  "summary": {
    "total_runs": 120,
    "total_cases": 45,
    "overall_pass_rate": 0.873
  },
  "daily_trend": [...],
  "by_priority": {...},
  "by_component": {...},
  "flaky_cases": [...]
}
```

---

## 四、数据流总览

```
case.xml
  │
  ├── [CaseParser] 解析 XML
  ├── [CaseMetadataExtractor] 提取元数据 → CaseMetadata
  │
  ▼
SKIExecutor 执行
  │
  ├── 记录每步骤 start_time / end_time / duration_ms
  ├── 捕获失败上下文 (page_source / console / network)
  ├── [DiagnosisEngine] AI 诊断 (可选)
  │
  ▼
result.xml
  │
  ├── <case> 节点: metadata (用例元数据)
  ├── <step> 节点: start_time / end_time / duration_ms / status / metadata
  ├── <diagnosis> 节点: AI 诊断报告
  │
  ▼
StatisticsCollector 聚合 (多次运行)
  │
  ├── 按优先级 / 组件 / 关键字聚合
  ├── Flaky case 识别
  ├── 趋势分析
  │
  ▼
stats CLI / JSON 报告
```

---

## 五、配置项

**文件**: `config/default_config.yaml`

```yaml
# Iteration-05 新增配置
result:
  # 是否记录步骤级耗时
  record_step_timing: true
  # 是否捕获失败上下文（page_source/console/network）
  capture_failure_context: true
  # 是否嵌入 AI 诊断结果
  embed_diagnosis: true

metadata:
  # 从 case.xml 提取元数据
  extract_from_case: true
  # 在 CLI 输出中显示元数据摘要
  show_in_cli: true

statistics:
  # 统计聚合结果目录
  result_dir: "results"
  # Flaky case 判定阈值（通过率低于此值视为 flaky）
  flaky_threshold: 0.3
  # 最慢用例显示数量
  top_slow_count: 10
```
