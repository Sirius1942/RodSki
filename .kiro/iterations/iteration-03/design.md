# 技术设计 - Agent 集成增强

**版本**: 1.0
**日期**: 2026-03-27

## 架构概览

```
┌─────────────────────────────────────────────────────────┐
│                    Agent (OpenClaw)                      │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ├─ Python API (RodSkiRunner)
                    ├─ Event Stream (callbacks)
                    └─ RuntimeCommandQueue (control)
                    │
┌───────────────────▼─────────────────────────────────────┐
│                   SKIExecutor (enhanced)                 │
│  ┌──────────────────────────────────────────────────┐  │
│  │ EventEmitter → step_start/end, case_start/end    │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │ IncrementalResultWriter → 实时写入               │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## 核心组件设计

### 1. 事件系统

#### 事件类型定义

```python
from enum import Enum
from dataclasses import dataclass
from typing import Any, Optional

class EventType(Enum):
    STEP_START = "step_start"
    STEP_END = "step_end"
    CASE_START = "case_start"
    CASE_END = "case_end"
    SCREENSHOT = "screenshot"
    ERROR = "error"

@dataclass
class ExecutionEvent:
    type: EventType
    timestamp: float
    case_id: Optional[str]
    step_index: Optional[int]
    data: dict[str, Any]
```

#### EventEmitter 实现

```python
class EventEmitter:
    def __init__(self):
        self._callbacks: list[Callable[[ExecutionEvent], None]] = []

    def on(self, callback: Callable[[ExecutionEvent], None]):
        self._callbacks.append(callback)

    def emit(self, event: ExecutionEvent):
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:
                # 回调失败不应中断执行
                logger.error(f"Event callback failed: {e}")
```

### 2. 实时结果写入

#### IncrementalResultWriter

```python
class IncrementalResultWriter:
    def __init__(self, output_path: Path):
        self.output_path = output_path
        self.temp_path = output_path.with_suffix('.jsonl')

    def write_case_result(self, case_result: dict):
        """每个 case 完成后立即追加写入"""
        with open(self.temp_path, 'a') as f:
            f.write(json.dumps(case_result) + '\n')

    def finalize(self, summary: dict):
        """全部完成后合并为最终结果"""
        results = []
        with open(self.temp_path) as f:
            for line in f:
                results.append(json.loads(line))

        final = {"summary": summary, "cases": results}
        with open(self.output_path, 'w') as f:
            json.dump(final, f, indent=2)

        self.temp_path.unlink()  # 删除临时文件
```

### 3. Python API 入口

#### RodSkiRunner

```python
class RodSkiRunner:
    def __init__(
        self,
        driver_type: str = "playwright",
        runtime_control: Optional[RuntimeCommandQueue] = None,
        event_callback: Optional[Callable[[ExecutionEvent], None]] = None
    ):
        self.driver_type = driver_type
        self.runtime_control = runtime_control
        self.emitter = EventEmitter()
        if event_callback:
            self.emitter.on(event_callback)

    def execute_case(self, case_path: str, **kwargs) -> dict:
        """执行单个测试用例"""
        executor = SKIExecutor(
            case_path,
            driver=self._create_driver(),
            runtime_control=self.runtime_control,
            event_emitter=self.emitter
        )
        return executor.execute()
```

### 4. SKIExecutor 改造

#### 关键修改点

1. 接受 `event_emitter` 参数
2. 接受 `runtime_control` 参数
3. 在关键节点发射事件
4. 使用 IncrementalResultWriter

```python
class SKIExecutor:
    def __init__(
        self,
        case_path: str,
        driver: WebDriver,
        runtime_control: Optional[RuntimeCommandQueue] = None,
        event_emitter: Optional[EventEmitter] = None,
        **kwargs
    ):
        # ... 现有初始化
        self.runtime_control = runtime_control
        self.emitter = event_emitter or EventEmitter()
```

### 5. 补全缺失关键字

#### click 实现

```python
def _kw_click(self, locator: str, **kwargs):
    """点击元素"""
    self.driver.click(locator)
```

#### screenshot 实现

```python
def _kw_screenshot(self, filename: str = None, **kwargs):
    """截图"""
    if not filename:
        filename = f"screenshot_{int(time.time())}.png"
    self.driver.screenshot(filename)
```

### 6. 异常处理改进

#### get_text 修复

```python
def get_text(self, locator: str) -> str:
    try:
        element = self.page.locator(locator)
        return element.inner_text()
    except Exception as e:
        self._handle_error("get_text", locator, e)
        raise  # 抛出而非返回 None
```

#### is_critical_error 重构

```python
CRITICAL_EXCEPTIONS = (
    PlaywrightError,
    TargetClosedError,
    BrowserClosedError
)

def is_critical_error(error: Exception) -> bool:
    return isinstance(error, CRITICAL_EXCEPTIONS)
```

## 实施计划

### Phase 1: 基础设施（3天）
- 实现 EventEmitter 和事件类型
- 实现 IncrementalResultWriter
- SKIExecutor 接受新参数

### Phase 2: API 入口（2天）
- 实现 RodSkiRunner
- CLI 支持 runtime_control 注入
- 集成测试

### Phase 3: 关键字补全（1天）
- 实现 click/screenshot
- 更新 KeywordEngine.SUPPORTED

### Phase 4: 异常处理（2天）
- 修复 get_text/verify/is_critical_error
- 添加单元测试

### Phase 5: 测试与文档（2天）
- 核心模块单元测试
- 更新 API 文档
- Agent 集成示例

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 事件回调影响性能 | 中 | 异步处理、可选禁用 |
| 向后兼容性破坏 | 高 | 所有新参数设为可选 |
| 测试覆盖不足 | 中 | 优先核心路径测试 |
