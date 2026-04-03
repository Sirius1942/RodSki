# Error Handling Best Practices

RodSki 错误处理最佳实践指南，涵盖分层错误处理策略、错误场景解决方案、RecoveryEngine 配置和 AI 诊断集成。

---

## 1. 分层错误处理策略

RodSki 采用三层错误处理架构：

### 1.1 步骤级错误处理 (Step-Level)

每个关键字执行时的错误处理：

```python
from core.keyword_engine import KeywordEngine

engine = KeywordEngine(driver_factory)

# 注册带错误处理的关键字
def safe_click(driver, params, context):
    try:
        return driver.click(params["locator"])
    except ElementNotFoundError:
        # 尝试等待后重试
        import time
        time.sleep(2)
        return driver.click(params["locator"])
    except TimeoutError:
        # 降级处理：跳过此步骤
        return {"status": "skipped", "message": "跳过点击步骤（超时）"}
```

配置步骤级重试：

```yaml
execution:
  max_retries: 3
  retry_delay_seconds: 2
  step_timeout: 30
```

### 1.2 用例级错误处理 (Case-Level)

用例执行过程中的错误处理：

```python
from core.ski_executor import SKIExecutor
from core.exceptions import StepExecutionError

executor = SKIExecutor(keyword_engine)

try:
    result = executor.execute_case("case.xml")
except StepExecutionError as e:
    print(f"用例执行失败: {e.case_id}")
    print(f"失败步骤: {e.step_index}")
    print(f"错误类型: {e.error_code}")
    # 触发恢复流程
```

用例级恢复配置：

```yaml
recovery_enabled: true
recovery_max_attempts: 2
recovery_wait_seconds: 1
```

### 1.3 套件级错误处理 (Suite-Level)

整个测试套件的错误策略：

```python
from core.parallel_executor import ParallelExecutor

executor = ParallelExecutor(max_workers=4)

# 套件级错误策略：continue-on-failure
result = executor.execute_suite(
    "cases/*.xml",
    continue_on_failure=True,  # 单个用例失败不终止其他用例
    stop_on_critical=False,
)

print(f"通过: {result.summary.passed}")
print(f"失败: {result.summary.failed}")
```

---

## 2. 错误类型与解决方案对照表

| 错误类型 | 原因 | 解决方案 | 配置 |
|---------|------|---------|------|
| `ElementNotFoundError` | 元素未找到/加载慢 | 增加等待时间、使用备用定位器 | `step_timeout`, `wait_before_retry` |
| `TimeoutError` | 网络慢/服务器响应慢 | 增加超时、增加重试 | `execution.max_retries` |
| `StaleElementError` | DOM 元素过期 | 重新定位元素、等待刷新 | `browser_restart_interval` |
| `AssertionFailedError` | 断言不成立 | 检查测试数据、修正断言条件 | — |
| `PageCrashError` | 页面崩溃 | 重启浏览器、记录崩溃前状态 | `browser_restart_interval` |
| `NetworkError` | 网络问题 | 重试、检查网络连接 | `execution.max_retries` |
| `ConfigurationError` | 配置错误 | 检查配置文件 | — |
| `ParseError` | XML 解析失败 | 验证 XML 语法 | — |

---

## 3. RecoveryEngine 配置最佳实践

### 3.1 基础配置

```yaml
recovery_enabled: true
recovery_max_attempts: 2
recovery_wait_seconds: 1
recovery_strategy: "aggressive"  # aggressive | conservative | ai_guided
```

### 3.2 预定义恢复动作

RecoveryEngine 支持以下恢复动作：

| 动作 | 说明 | 使用场景 |
|-----|------|---------|
| `wait N` | 等待 N 秒 | 元素加载慢、网络延迟 |
| `refresh` | 刷新页面 | 内容未更新、临时错误 |
| `screenshot` | 截图 | 记录失败状态 |
| `retry` | 重试当前步骤 | 瞬时失败 |
| `restart_browser` | 重启浏览器 | 浏览器崩溃、内存泄漏 |
| `insert_step` | 插入动态步骤 | 需要额外操作后重试 |

### 3.3 错误到恢复动作映射

```yaml
recovery:
  error_action_map:
    ElementNotFoundError: ["wait 3", "screenshot", "retry"]
    TimeoutError: ["refresh", "wait 2", "retry"]
    StaleElementError: ["wait 2", "retry"]
    AssertionFailedError: ["screenshot", "stop"]
    PageCrashError: ["restart_browser", "navigate ${current_url}"]
```

### 3.4 自定义恢复策略

```python
from core.recovery_engine import RecoveryEngine

recovery = RecoveryEngine(keyword_engine, browser_recycler)

# 注册自定义恢复动作
def custom_recovery_action(driver, context):
    """自定义恢复: 清除 cookies 后重试"""
    driver.delete_all_cookies()
    return {"success": True, "action": "clear_cookies"}

recovery.register_action("clear_cookies", custom_recovery_action)
```

---

## 4. AI 诊断集成最佳实践

### 4.1 配置 AI 视觉诊断

```yaml
vision:
  ai_verifier:
    enabled: true
    model_provider: "claude"  # claude | openai | qwen
    api_key: "${CLAUDE_API_KEY}"  # 从环境变量读取
    timeout: 30

diagnosis:
  enabled: true
  embed_in_result: true
  max_diagnosis_time_ms: 5000
```

### 4.2 使用 DiagnosisEngine

```python
from core.diagnosis_engine import DiagnosisEngine
from core.vision.ai_verifier import AIScreenshotVerifier

ai_verifier = AIScreenshotVerifier(model_provider="claude")
diagnosis_engine = DiagnosisEngine(keyword_engine, ai_verifier)

# 诊断失败
report = diagnosis_engine.diagnose(
    exception=ElementNotFoundError(...),
    screenshot_path="screenshots/failed.png",
    step_context={
        "keyword": "click",
        "locator": "#submit-btn",
        "url": driver.current_url,
    }
)

print(f"失败点: {report.failure_point}")
print(f"失败原因: {report.failure_reason}")
print(f"视觉分析: {report.visual_analysis}")
print(f"建议: {report.suggestion}")
print(f"恢复动作: {report.recovery_action}")
```

### 4.3 内置错误动作映射

DiagnosisEngine 内置了 ERROR_ACTION_MAP：

```python
ERROR_ACTION_MAP = {
    ElementNotFoundError: "wait 3s",
    TimeoutError: "refresh",
    StaleElementError: "wait 2s",
    AssertionFailedError: "screenshot",
    PageCrashError: "restart_browser",
}
```

### 4.4 分析录像关键帧

```python
from vision.ai_verifier import analyze_recording

report = analyze_recording(
    recording_path="recordings/test_001.webm",
    question="登录流程是否正常完成？",
    model_provider="claude"
)

print(f"分析结果: {report.analysis}")
print(f"关键帧: {report.key_frames}")
```

---

## 5. 失败上下文捕获

启用失败上下文捕获，记录详细信息用于调试：

```yaml
result:
  capture_failure_context: true
  failure_context_types:
    - page_source
    - console_logs
    - network_requests
    - variable_snapshot
    - screenshot
```

捕获内容示例：

```xml
<failure_context>
  <page_source>output/page_sources/TC001_step_3.html</page_source>
  <console_logs>output/console/TC001_step_3.log</console_logs>
  <network_requests>output/network/TC001_step_3.json</network_requests>
  <variable_snapshot>
    <variable name="user" value="admin"/>
    <variable name="last_result" value="{"status": "PASS"}"/>
  </variable_snapshot>
  <screenshot>screenshots/TC001_step_3.png</screenshot>
</failure_context>
```

---

## 6. 最佳实践清单

### 6.1 设计阶段

- [ ] 为不稳定操作配置重试策略
- [ ] 使用多个定位器策略（primary + fallback）
- [ ] 设置合理的超时时间
- [ ] 设计原子化步骤，减少依赖

### 6.2 实现阶段

- [ ] 使用显式等待而非固定 sleep
- [ ] 捕获并记录足够的失败上下文
- [ ] 启用 AI 诊断（关键流程）
- [ ] 配置浏览器定期回收

### 6.3 执行阶段

- [ ] 监控内存使用，及时触发 GC
- [ ] 配置浏览器重启间隔
- [ ] 使用并行执行提高效率
- [ ] 定期审查 flaky cases

### 6.4 维护阶段

- [ ] 定期更新错误动作映射
- [ ] 分析失败趋势，优化恢复策略
- [ ] 清理过时快照文件
- [ ] 更新 AI 诊断提示词

---

## 7. 常见错误场景与解决方案

### 场景 1: Flaky Test (不稳定测试)

**表现**: 同样的用例，有时通过，有时失败

**解决方案**:
1. 增加等待时间
2. 使用 `wait_for_element` 代替固定等待
3. 启用 `retry_on_fail`
4. 检查是否有竞态条件

### 场景 2: 元素间歇性找不到

**表现**: 元素大部分时间能找到，偶尔找不到

**解决方案**:
1. 增加 `step_wait` 时间
2. 添加重试机制
3. 使用更稳定的定位器（ID > NAME > CSS > XPath）
4. 检查是否有动态加载内容

### 场景 3: 长时间运行内存泄漏

**表现**: 用例运行时间越长，速度越慢，最终崩溃

**解决方案**:
1. 配置 `browser_restart_interval: 50`
2. 启用内存监控 `memory_check_interval: 10`
3. 设置内存增长阈值触发 GC
4. 定期清理截图和日志文件

### 场景 4: 并行执行资源竞争

**表现**: 并行执行时失败率显著高于串行

**解决方案**:
1. 降低并行数 `max_workers`
2. 每个 worker 使用独立浏览器实例
3. 避免共享状态
4. 检查端口冲突

---

## 8. 反模式 (避免这样做)

❌ **不要**在每个步骤后使用固定 `wait(10)`
→ 使用 `wait_for_element` 或动态等待

❌ **不要**捕获所有异常并忽略
→ 至少记录错误日志

❌ **不要**设置过长的超时掩盖问题
→ 分析超时原因，修复根本问题

❌ **不要**禁用 RecoveryEngine 跳过失败
→ 失败说明有问题，应该修复

❌ **不要**在并行执行中使用共享状态
→ 使用独立浏览器配置文件
