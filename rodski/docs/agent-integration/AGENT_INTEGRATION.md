# RodSki Agent 集成指南

## 概述

RodSki 为 AI Agent 提供结构化的测试自动化执行能力。Agent 可以通过两种方式与 RodSki 交互：

1. **CLI 调用** — 通过命令行执行用例，适合一次性任务和脚本集成
2. **编程接口** — 通过 Python API 直接调用，适合复杂工作流和自动化管道

```
┌─────────────────────────────────────────────────────────┐
│  AI Agent (Claude Code / OpenCode / OpenClaw)           │
│                                                         │
│   ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  │
│   │ CLI 调用    │  │ Python API  │  │ OpenClaw Skill│  │
│   └──────┬──────┘  └──────┬──────┘  └──────┬───────┘  │
└──────────┼────────────────┼────────────────┼──────────┘
           │                │                │
           ▼                ▼                ▼
      ┌────────────────────────────────────────────┐
      │              RodSki 引擎                     │
      │  SKIExecutor → KeywordEngine → Drivers       │
      └────────────────────────────────────────────┘
```

---

## 1. CLI 调用集成

### 1.1 基本执行

```bash
# 标准执行
rodski run case.xml --output-format json

# 带变量注入
rodski run case.xml -v user=admin -v env=staging

# 干跑验证
rodski run case.xml --dry-run

# 单步执行 (调试模式)
rodski run case.xml --step-by-step
```

### 1.2 JSON 输出格式

**成功响应：**
```json
{
  "status": "success",
  "exit_code": 0,
  "summary": {
    "total": 5,
    "passed": 5,
    "failed": 0,
    "skipped": 0
  },
  "steps": [
    {
      "case_id": "TC001",
      "index": 0,
      "keyword": "navigate",
      "status": "PASS",
      "duration_ms": 1200
    }
  ],
  "variables": {
    "last_result": {"status": "PASS"}
  }
}
```

**失败响应：**
```json
{
  "status": "failed",
  "exit_code": 1,
  "error": {
    "type": "ElementNotFoundError",
    "message": "无法定位元素 #submit-btn"
  },
  "failed_step": {
    "case_id": "TC001",
    "index": 3,
    "keyword": "click",
    "locator": "#submit-btn"
  },
  "context": {
    "url": "https://example.com/form",
    "screenshot": "screenshots/failed_step_3.png"
  }
}
```

### 1.3 退出码规范

| 退出码 | 含义 |
|--------|------|
| 0 | 所有测试通过 |
| 1 | 测试失败或执行错误 |
| 130 | 用户中断 (Ctrl+C) |

---

## 2. 编程接口

### 2.1 SKIExecutor

`SKIExecutor` 是核心执行器，提供细粒度的编程控制：

```python
from core.ski_executor import SKIExecutor
from core.keyword_engine import KeywordEngine
from core.driver_factory import DriverFactory

# 初始化组件
driver_factory = DriverFactory()
keyword_engine = KeywordEngine(driver_factory)
executor = SKIExecutor(keyword_engine)

# 执行单个用例
result = executor.execute_case(
    case_path="case.xml",
    variables={"env": "staging"},
    config={"execution.recovery_enabled": True}
)

print(f"Status: {result['status']}")
print(f"Passed: {result['summary']['passed']}")
```

### 2.2 关键字引擎

`KeywordEngine` 注册和管理所有关键字：

```python
from core.keyword_engine import KeywordEngine

engine = KeywordEngine(driver_factory)

# 注册自定义关键字
def my_custom_keyword(driver, params, context):
    # params: dict 参数
    # context: dict 上下文 (包含 _variables 等)
    value = params.get("value", "")
    print(f"Custom keyword executed with: {value}")
    return {"status": "PASS", "message": "执行成功"}

engine.register_keyword("custom_action", my_custom_keyword)

# 调用关键字
result = engine.execute_keyword("custom_action", {"value": "test"}, {})
```

### 2.3 DriverFactory

```python
from core.driver_factory import DriverFactory

factory = DriverFactory()

# 获取浏览器驱动
driver = factory.create_driver("playwright")
# 或
driver = factory.create_driver("selenium")

# 执行浏览器操作
driver.navigate("https://example.com")
driver.click("#button")
```

---

## 3. 异常处理与恢复

### 3.1 异常类型体系

```python
from core.exceptions import (
    SKIError,
    ElementNotFoundError,
    TimeoutError,
    AssertionFailedError,
    StepTimeoutError,
)

try:
    result = executor.execute_case("case.xml")
except ElementNotFoundError as e:
    print(f"元素未找到: {e.message}")
    print(f"定位器: {e.details.get('locator')}")
except TimeoutError as e:
    print(f"操作超时: {e.message}")
except AssertionFailedError as e:
    print(f"断言失败: {e.message}")
except SKIError as e:
    print(f"框架错误: {e.error_code} - {e.message}")
```

### 3.2 RecoveryEngine

```python
from core.recovery_engine import RecoveryEngine
from core.diagnosis_engine import DiagnosisEngine

diagnosis_engine = DiagnosisEngine(keyword_engine, ai_verifier)
recovery_engine = RecoveryEngine(keyword_engine, browser_recycler)

# 诊断异常
report = diagnosis_engine.diagnose(
    exception=ElementNotFoundError(...),
    screenshot_path="screenshots/failed.png",
    step_context={"keyword": "click", "locator": "#btn"}
)

# 执行恢复
recovery_result = recovery_engine.execute_recovery(report)

if recovery_result.success:
    print("恢复成功，步骤已插入")
else:
    print(f"恢复失败: {recovery_result.final_error}")
```

### 3.3 重试策略

在 `config/default_config.yaml` 中配置：

```yaml
execution:
  max_retries: 3
  retry_delay_seconds: 2
  recovery_enabled: true
  recovery_max_attempts: 2
```

---

## 4. 多 Agent 协作

### 4.1 协作模式

```
Agent A (规划者)
   │
   ├─→ 编写测试用例 case.xml
   │
   ├─→ 调用 RodSki 执行
   │
   └─→ 将结果传递给 Agent B

Agent B (分析师)
   │
   ├─→ 接收执行结果
   │
   ├─→ 分析失败原因
   │
   └─→ 生成诊断报告
```

### 4.2 共享状态

通过共享文件传递状态：

```python
import json
from pathlib import Path

# Agent A: 保存状态
state = {
    "last_execution": {
        "case_id": "TC001",
        "status": "failed",
        "failed_step": 3,
        "variables": {"user": "admin"}
    }
}
Path("agent_state.json").write_text(json.dumps(state))

# Agent B: 读取状态
state = json.loads(Path("agent_state.json").read_text())
last_case = state["last_execution"]["case_id"]
```

### 4.3 管道集成示例

```python
import subprocess
import json

def run_rodski_case(case_path, variables=None):
    """执行 RodSki 用例并返回结构化结果"""
    cmd = ["rodski", "run", case_path, "--output-format", "json"]
    if variables:
        for k, v in variables.items():
            cmd.extend(["-v", f"{k}={v}"])

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        return json.loads(result.stdout)
    else:
        error_result = json.loads(result.stdout) if result.stdout else {}
        error_result["exit_code"] = result.returncode
        return error_result

# Agent A 规划者
plan = {
    "test_cases": ["login.xml", "search.xml", "purchase.xml"],
    "environment": "staging"
}

# Agent B 执行者
for case in plan["test_cases"]:
    result = run_rodski_case(case, {"env": plan["environment"]})
    print(f"{case}: {result['status']}")
```

---

## 5. Claude Code 集成

### 5.1 集成架构

```bash
# 在 Claude Code 中调用 RodSki
/rodski run case.xml --output-format json
```

### 5.2 错误处理工作流

```python
# examples/agent/claude_code_integration.py

import subprocess
import json
import sys
from pathlib import Path

def run_case(case_path, verbose=False):
    """执行 RodSki 用例"""
    cmd = ["rodski", "run", case_path, "--output-format", "json"]
    if verbose:
        cmd.append("--verbose")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        return json.loads(result.stdout)
    else:
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {
                "status": "error",
                "exit_code": result.returncode,
                "error": result.stderr
            }

def main():
    if len(sys.argv) < 2:
        print("用法: python claude_code_integration.py <case.xml>")
        sys.exit(1)

    case_path = sys.argv[1]
    result = run_case(case_path, verbose=True)

    if result["status"] == "success":
        print(f"✅ 测试通过: {result['summary']['passed']}/{result['summary']['total']}")
    else:
        error = result.get("error", {})
        print(f"❌ 测试失败: {error.get('type', 'Unknown')}")
        print(f"   消息: {error.get('message', '')}")

        failed_step = result.get("failed_step", {})
        if failed_step:
            print(f"   失败步骤: {failed_step.get('case_id')} (index={failed_step.get('index')})")

        context = result.get("context", {})
        if context.get("screenshot"):
            print(f"   截图: {context['screenshot']}")

if __name__ == "__main__":
    main()
```

---

## 6. 最佳实践

### 6.1 用例设计

1. **模块化** — 每个用例尽量单一职责
2. **变量化** — 使用变量而非硬编码值
3. **可重试** — 设计具有重试机制的稳定用例
4. **可解释** — 使用 `rodski explain` 验证用例可读性

### 6.2 错误恢复

1. 启用 `recovery_enabled` 配置
2. 合理设置 `recovery_max_attempts`
3. 使用 `on_error` 动态步骤处理边界情况
4. 定期审查 AI 诊断报告优化恢复策略

### 6.3 性能优化

1. 配置 `browser_restart_interval` 防止内存泄漏
2. 使用 `parallel_executor` 并行执行独立用例
3. 合理设置 `step_wait` 减少不必要的等待

---

## 7. 配置参考

```yaml
# 完整配置示例
execution:
  allow_conditions: true        # 启用条件执行
  allow_loops: true              # 启用循环
  allow_dynamic_steps: true      # 启用动态步骤注入
  loop_max_iterations: 1000      # 循环最大次数
  max_retries: 3                 # 最大重试次数
  recovery_enabled: true         # 启用自动恢复
  recovery_max_attempts: 2       # 最大恢复尝试次数
  browser_restart_interval: 50   # 浏览器定期重启步数

result:
  record_step_timing: true       # 记录步骤耗时
  capture_failure_context: true   # 捕获失败上下文
  embed_diagnosis: true          # 嵌入 AI 诊断

statistics:
  result_dir: "output/results"    # 结果目录
  flaky_threshold: 0.3           # 不稳定用例阈值
```
