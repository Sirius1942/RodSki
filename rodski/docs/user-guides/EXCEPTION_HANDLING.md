# RodSki 异常处理与智能恢复最佳实践

本文档详细介绍 RodSki 框架的异常处理机制、智能恢复策略以及最佳实践。

## 1. 异常类型参考

RodSki 框架定义了以下异常类型，用于精确识别测试执行中的不同失败场景：

| 异常类型 | 触发场景 | 典型原因 |
|---------|---------|---------|
| `ElementNotFoundError` | 页面元素定位失败 | 元素未加载、定位器错误、页面结构变化 |
| `NetworkError` | 网络请求失败 | 服务器无响应、DNS解析失败、连接超时 |
| `AssertionFailedError` | 断言验证失败 | 实际结果与预期不符 |
| `StepTimeoutError` | 步骤执行超时 | 页面加载慢、元素响应慢、脚本执行时间过长 |
| `PageCrashError` | 页面崩溃或无响应 | 浏览器崩溃、JavaScript错误、内存溢出 |

## 2. 失败上下文捕获

当测试步骤失败时，RodSki 自动捕获以下上下文信息：

### 捕获内容

- **URL**：失败时的页面地址
- **步骤索引**：失败步骤在用例中的位置（从0开始）
- **模型名称**：失败步骤使用的页面模型
- **数据标识**：失败步骤使用的测试数据ID
- **截图文件**：失败时的页面截图，保存路径为 `result/{执行ID}/screenshots/{用例ID}_{时间戳}_failure.png`
- **异常堆栈**：完整的异常堆栈信息

### 上下文存储

所有失败上下文信息会记录到 `result.xml` 文件中，便于后续分析和调试。

## 3. 配置恢复策略

在 `config/default_config.yaml` 中配置异常处理和恢复策略：

```yaml
exception_handling:
  # 自动截图开关
  auto_screenshot: true

  # 最大重试次数
  max_retry_count: 3

  # 恢复策略：auto（自动）、manual（手动）、none（不恢复）
  recovery_strategy: "auto"

  # 浏览器回收间隔（步骤数）
  browser_recycle_interval: 50

  # 启用快照恢复
  enable_snapshot: true

  # 步骤超时时间（秒）
  step_timeout: 30

  # 页面加载超时时间（秒）
  page_load_timeout: 60
```

## 4. AI 视觉诊断（AIScreenshotVerifier）

RodSki 集成 AI 视觉分析能力，位于 `vision/ai_verifier.py`，用于智能分析失败截图。

### 功能特性

- **页面状态识别**：自动识别 404 页面、500 错误、空白页等异常状态
- **元素可见性检测**：判断目标元素是否在截图中可见
- **弹窗检测**：识别遮挡页面的弹窗、对话框、广告
- **加载状态分析**：检测页面是否处于加载中状态

### 使用示例

```python
from vision.ai_verifier import AIScreenshotVerifier

verifier = AIScreenshotVerifier()
result = verifier.analyze_screenshot(
    screenshot_path="result/xxx/screenshots/TC001_failure.png",
    expected_element="登录按钮"
)

print(result.diagnosis)  # AI 诊断结果
print(result.suggestions)  # 恢复建议
```

## 5. 诊断引擎（DiagnosisEngine）

DiagnosisEngine 负责生成结构化的诊断报告。

### 诊断报告内容

- **基本信息**：用例ID、失败步骤、时间戳
- **执行上下文**：URL、模型、数据、浏览器状态
- **异常详情**：异常类型、错误消息、堆栈跟踪
- **截图分析**：AI 视觉诊断结果（如果启用）
- **恢复建议**：推荐的恢复策略和操作

### 报告输出

诊断报告会附加到 `result.xml` 的 `<diagnosis>` 节点中。

## 6. 恢复引擎（RecoveryEngine）

RecoveryEngine 提供预定义的恢复动作，用于自动处理常见失败场景。

### 预定义恢复动作

| 动作 | 说明 | 适用场景 |
|-----|------|---------|
| `wait` | 等待指定时间（默认2秒） | 页面加载慢、元素延迟出现 |
| `refresh` | 刷新当前页面 | 页面状态异常、网络临时中断 |
| `screenshot` | 重新截图并验证 | 确认页面状态是否恢复 |
| `retry` | 重试失败的步骤 | 临时性错误、网络抖动 |

### 恢复策略配置

```yaml
exception_handling:
  recovery_strategy: "auto"
  recovery_actions:
    ElementNotFoundError: ["wait", "refresh", "retry"]
    NetworkError: ["wait", "retry"]
    StepTimeoutError: ["wait", "retry"]
    PageCrashError: ["refresh"]
```

## 7. 内存监控与浏览器回收

RodSki 自动监控浏览器内存使用，防止长时间运行导致的内存泄漏。

### 自动回收机制

- 默认每执行 50 个步骤后自动回收浏览器实例
- 回收时会保存当前执行状态，确保测试可以继续
- 回收后自动创建新的浏览器实例

### 配置回收间隔

```yaml
exception_handling:
  browser_recycle_interval: 50  # 调整为其他值，如 100
```

### 手动触发回收

在用例中可以使用 `recycle` 关键字手动触发浏览器回收：

```xml
<test_step action="recycle" model="" data=""/>
```

## 8. 快照恢复功能

快照恢复允许在关键步骤保存执行状态，失败时可从最近的快照恢复。

### 启用快照

```yaml
exception_handling:
  enable_snapshot: true
```

### 在用例中创建快照

```xml
<test_step action="snapshot" model="" data="checkpoint_1"/>
```

### 恢复机制

当步骤失败且启用快照时，框架会自动从最近的快照恢复，避免从头重新执行整个用例。

## 9. 编写弹性测试用例的最佳实践

### 9.1 合理设置等待时间

```xml
<!-- 页面加载后等待元素稳定 -->
<test_step action="wait" model="" data="2"/>
```

### 9.2 使用显式等待而非固定延迟

优先依赖框架的自动等待机制，避免过度使用 `wait` 步骤。

### 9.3 设计幂等性步骤

确保步骤可以安全重试，避免重复执行导致副作用。

### 9.4 添加关键检查点

在重要步骤后添加断言验证：

```xml
<test_step action="assert" model="ResultPage" data="expected_result"/>
```

### 9.5 合理使用快照

在耗时操作前创建快照：

```xml
<test_step action="snapshot" model="" data="before_submit"/>
<test_step action="click" model="SubmitButton" data="submit"/>
```

## 10. 自定义恢复策略示例

### 示例：为特定异常配置自定义恢复流程

```yaml
exception_handling:
  recovery_strategy: "auto"
  max_retry_count: 3

  recovery_actions:
    ElementNotFoundError:
      - action: "wait"
        duration: 3
      - action: "refresh"
      - action: "retry"
        max_attempts: 2

    NetworkError:
      - action: "wait"
        duration: 5
      - action: "retry"
        max_attempts: 3
```

### 示例：在用例中处理预期异常

```xml
<test_case>
    <test_step action="navigate" model="" data="http://example.com"/>
    <test_step action="click" model="SubmitButton" data="submit"
               on_error="continue" expected_errors="NetworkError"/>
    <test_step action="verify" model="ResultPage" data="success"/>
</test_case>
```

---

**相关文档**：
- [快速入门指南](QUICKSTART.md)
- [用例编写规范](TEST_CASE_WRITING_GUIDE.md)
- [故障排查指南](TROUBLESHOOTING.md)
