# Iteration 04 设计文档

## 1. CLI JSON 输出格式

```json
{
  "status": "success|failed|partial",
  "exit_code": 0,
  "summary": {
    "total_steps": 10,
    "executed": 10,
    "passed": 10,
    "failed": 0,
    "duration": "12.5s"
  },
  "steps": [...],
  "variables": {...}
}
```

## 2. 错误信息格式

```json
{
  "status": "failed",
  "failed_step": {
    "index": 5,
    "action": "type",
    "model": "Login"
  },
  "error": {
    "type": "ElementNotFound",
    "message": "无法定位元素"
  },
  "context": {
    "url": "...",
    "screenshot": "..."
  }
}
```

## 3. Test Case Explainer（已完成）

详见 `core/test_case_explainer.py`

```python
from core.test_case_explainer import TestCaseExplainer

explainer = TestCaseExplainer(model_parser=mp, data_manager=dm)
print(explainer.explain_case("path/to/case.xml"))
```

## 4. 异常处理与智能恢复架构

### 4.1 异常捕获层次

```
SKIExecutor.execute()
  └── KeywordEngine.execute_step(step)
        └── Driver method (PlaywrightDriver.click etc.)
              └── try/except
                    └── StepExecutionError
                          ├── ElementNotFoundError
                          ├── NetworkError
                          ├── AssertionFailedError
                          ├── StepTimeoutError
                          └── PageCrashError
```

### 4.2 异常处理流程

```
步骤执行失败
    ↓
捕获 StepExecutionError
    ↓
记录上下文（URL、步骤索引、模型、数据）
    ↓
触发 ScreenshotCapture（失败截图）
    ↓
触发 DiagnosisEngine
    ↓
调用 AIScreenshotVerifier 分析截图
    ↓
生成 DiagnosisReport
    ↓
判断是否可恢复
    ├─ YES → RecoveryEngine 执行动态步骤插入
    │         ↓
    │         重试当前步骤
    │         ↓
    │         成功 → 继续下一步
    │         失败 → 达到 max_retries → 标记失败，继续
    └─ NO  → 标记步骤失败，继续执行后续步骤
    ↓
最终生成完整 Result XML（含诊断信息）
```

### 4.3 DiagnosisEngine

```python
class DiagnosisEngine:
    """异常诊断引擎"""

    def __init__(self, screenshot_verifier: AIScreenshotVerifier):
        self.screenshot_verifier = screenshot_verifier

    def diagnose(
        self,
        error: StepExecutionError,
        screenshot_path: str,
        context: dict
    ) -> DiagnosisReport:
        """
        分析异常原因

        Returns:
            DiagnosisReport: 包含 failure_reason, visual_analysis, suggestion, recovery_action
        """
        # 1. 调用视觉分析
        visual_result = self.screenshot_verifier.verify(
            screenshot_path,
            f"页面状态：{context.get('url', '')}，异常：{error.message}"
        )

        # 2. 结合上下文和视觉分析生成报告
        return DiagnosisReport(
            failure_point=context.get('step_description', ''),
            failure_reason=error.type,
            visual_analysis=visual_result.reason,
            suggestion=self._generate_suggestion(error, visual_result),
            recovery_action=self._suggest_recovery_action(error, visual_result)
        )

    def _generate_suggestion(self, error, visual_result) -> str:
        """根据错误类型和视觉分析生成建议"""

    def _suggest_recovery_action(self, error, visual_result) -> str:
        """建议恢复动作"""
```

### 4.4 RecoveryEngine

```python
class RecoveryEngine:
    """动态恢复引擎"""

    RECOVERY_ACTIONS = {
        "ElementNotFound": ["wait:data=3", "screenshot", "refresh"],
        "AssertionFailed": ["screenshot", "wait:data=2"],
        "StepTimeout": ["wait:data=5", "refresh"],
        "PageCrash": ["restart_browser", "navigate:data={last_url}"],
    }

    def __init__(self, keyword_engine: KeywordEngine):
        self.keyword_engine = keyword_engine

    def try_recover(
        self,
        diagnosis: DiagnosisReport,
        context: dict,
        max_attempts: int = 2
    ) -> RecoveryResult:
        """
        尝试恢复执行

        Returns:
            RecoveryResult: (success: bool, steps_inserted: list)
        """
        actions = self.RECOVERY_ACTIONS.get(
            diagnosis.failure_reason,
            ["wait:data=3", "screenshot"]
        )

        for action in actions[:max_attempts]:
            try:
                # 解析并执行动态步骤
                step = self._parse_dynamic_action(action)
                self.keyword_engine.execute_step(step)
                # 重试原步骤
                self.keyword_engine.execute_step(context['failed_step'])
                return RecoveryResult(success=True, steps_inserted=actions)
            except Exception:
                continue

        return RecoveryResult(success=False, steps_inserted=actions)
```

### 4.5 AIScreenshotVerifier

```python
class AIScreenshotVerifier:
    """AI 截图验证器"""

    def verify(self, screenshot_path: str, question: str) -> VerificationResult:
        """
        用视觉大模型分析截图

        Args:
            screenshot_path: 截图文件路径
            question: 分析问题，如 "页面上显示什么？有没有错误提示？"

        Returns:
            VerificationResult: (is_pass, reason)
        """
```

### 4.6 配置项

```yaml
# config/default_config.yaml
execution:
  max_retries: 3
  recovery_enabled: true
  recovery_max_attempts: 2
  screenshot_on_failure: true
  video_recording: false
  max_step_timeout: 30
  browser_restart_interval: 50  # 每50步重启浏览器

screen_record:
  enabled: false
  fps: 10
  output_dir: screenshots/
  max_duration: 600
```

### 4.7 Result XML 新增字段

```xml
<testresult>
  <summary .../>
  <results>
    <case id="TC001" status="FAIL">
      <diagnosis>
        <failure_point>步骤 3/5 - click(loginBtn)</failure_point>
        <failure_reason>ElementNotFound</failure_reason>
        <visual_analysis>页面上显示'加载中'，元素尚未渲染完成</visual_analysis>
        <suggestion>在 click 前插入 wait action，等待元素可见</suggestion>
        <recovery_attempted>true</recovery_attempted>
        <recovery_result>SUCCESS</recovery_result>
        <steps_inserted>
          <step action="wait" data="3"/>
        </steps_inserted>
      </diagnosis>
      ...
    </case>
  </results>
</testresult>
```

### 4.8 动态步骤语法

在配置或外部指令中可以指定动态插入的步骤：

```yaml
recovery:
  # 预定义恢复策略
  strategies:
    slow_page:
      trigger: "ElementNotFound"
      condition: "visual:contains('加载中')"
      actions:
        - wait:data=5
        - wait_for_selector:timeout=10000
```

在执行时也可以通过 API 动态插入步骤：

```python
executor.dynamic_insert("wait", data="3")
executor.dynamic_insert("click", locator="css=.modal-close")
```
