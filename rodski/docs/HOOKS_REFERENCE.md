# RodSki Hooks 参考手册（v8.2.0）

本手册是 Hooks 机制的使用参考。设计背景与决策记录见 `.pb/specs/rodski-hooks-design.md`；实现任务清单见 `.pb/iterations/iteration-60/tasks.md`。

---

## 1. 事件清单

| 事件 | 触发点 | 挂载方式 | 用途 |
|---|---|---|---|
| `on_session_start` | CLI 调用开始前 | 外部命令 hook | 低频通知/前置检查（如环境探活） |
| `on_run_start` | 合规检查前置，`execute_all_cases` 之前 | 外部命令 hook（内置合规检查同时触发） | 合规静态检查 + 自定义外部规则，检查不过可 deny 整次执行 |
| `before_keyword` | 每个关键字执行前 | 进程内 Python 回调 | 高危操作拦截（`DB` 写生产库、`navigate` 指向生产域名等），只做 allow/deny，不支持交互式 ask |
| `after_keyword` | 每个关键字执行后（成功/失败/重试都会触发一次） | 进程内 Python 回调 | 结果记录、自定义指标采集 |
| `on_case_failure` | case 失败截图逻辑之后 | 进程内 Python 回调 + `DiagnosisEngine` 接入 | 失败通知、结构化诊断 |
| `on_case_pass_roam_ready` | 成功的 `test_case` 之后、`post_process` 之前 | 仅进程内 Python 回调 | 注入漫游决策引擎；无有效 Handler 时以 `stopped_reason="no_handler"` 正常结束 |
| `on_run_end` | `execute_all_cases` 结束处 | 外部命令 hook | 汇总通知、CI 结果上报 |

不在本迭代范围内：`before_keyword` 的交互式 ask 确认、敏感数据扫描、`PreCompact`/`PostCompact` 类事件（RodSki 不管理 Agent 对话上下文）。

---

## 2. 进程内 Python 回调

通过 `SKIExecutor(hooks=..., diagnosis_engine=...)` 构造参数注入，适合以 Python API 方式调用 rodski 的场景（如 rodski-agent）。

```python
from core.ski_executor import SKIExecutor
from core.keyword_engine import HookDecision, HookResult

def before_keyword_hook(keyword: str, params: dict) -> HookDecision:
    if keyword == "DB" and "prod" in (params.get("data") or ""):
        return HookDecision(allow=False, reason="禁止在生产库上执行 DB 写操作")
    return HookDecision(allow=True)

def after_keyword_hook(keyword: str, params: dict, result: HookResult) -> None:
    if result.status != "ok":
        print(f"[metrics] {keyword} 失败，耗时 {result.elapsed:.2f}s，重试 {result.attempts} 次")

def on_case_failure_hook(case: dict, error: Exception, screenshot_path) -> None:
    print(f"用例 {case['case_id']} 失败: {error}, 截图: {screenshot_path}")

executor = SKIExecutor(
    case_path="case/",
    driver=driver,
    hooks={
        "before_keyword": [before_keyword_hook],
        "after_keyword": [after_keyword_hook],
        "on_case_failure": [on_case_failure_hook],
    },
)
```

**回调签名**：

| 事件 | 签名 | 返回值 |
|---|---|---|
| `before_keyword` | `(keyword: str, params: dict) -> HookDecision \| None` | `HookDecision(allow=False, reason=...)` 时抛 `HookDeniedError`（`SKI701`）；`None` 或 `allow=True` 放行 |
| `after_keyword` | `(keyword: str, params: dict, result: HookResult) -> None` | 忽略返回值 |
| `on_case_failure` | `(case: dict, error: Exception, screenshot_path: str \| None) -> None` | 忽略返回值 |
| `on_case_pass_roam_ready` | `(context: RoamContext) -> engine \| factory \| decision \| None` | 有效返回值用作漫游引擎；无效/异常/`None` 时该 handler 被跳过；所有 handler 均无效时会话以 `no_handler` 结束 |

**异常处理**：回调自身抛异常仅记录 `logger.warning`，不会中断关键字执行或 case 流程（`before_keyword` 的 deny 判定异常除外，那是显式约定行为，不是异常路径）。

**`HookDecision`/`HookResult`**（定义在 `core/keyword_engine.py`）：

```python
class HookDecision:
    allow: bool
    reason: Optional[str] = None

class HookResult:
    status: str       # "ok" | "error"
    attempts: int
    elapsed: float
```

### DiagnosisEngine 接入

```python
from core.ski_executor import SKIExecutor
from core.diagnosis_engine import DiagnosisEngine

executor = SKIExecutor(
    case_path="case/",
    driver=driver,
    diagnosis_engine=DiagnosisEngine(),
)
```

配置后，case 失败时自动调用 `DiagnosisEngine.diagnose()`，结果通过 `report_collector.record_diagnosis()` 写入 `CaseReport.case_diagnosis`（`report/data_model.py`），可在 JSON 输出的 `case_diagnosis.recovery_action` 中读取。`diagnosis_engine=None`（默认）时不触发诊断，行为与迭代前一致。

### `on_case_pass_roam_ready` 漫游扩展（v8.4.0）

Hooks 机制本身仍是 v8.2.0 功能；v8.3.0 新增此进程内事件，v8.4.0 完成架构解耦：核心不再包含 `DataRoamDecisionEngine` 默认引擎，决策逻辑完全由 Handler 提供。

Handler 支持三种返回形态：

1. 已实例化、实现 `next_action(context)` 的 engine
2. 可调用的 factory，调用后返回上述 engine
3. 可调用对象直接返回首个 decision 字典，执行器随后继续按该 callable 获取决策

```python
class CustomRoamEngine:
    def next_action(self, context):
        return {
            "next_action": {"action": "type", "model": "Search", "data": "D002"},
            "confidence": 0.8,
            "reversible": True,
            "usage": {"tokens": 200, "cost_usd": 0.001},
            "stop": False,
        }

executor = SKIExecutor(
    case_path="case/",
    driver=driver,
    hooks={"on_case_pass_roam_ready": [lambda context: CustomRoamEngine()]},
)
```

也可通过 `--roam-engine path/to/engine_module.py` CLI 选项加载，无需修改 Python 代码（v8.4.0）：

```python
# my_engine.py — 须导出 create_engine()
def create_engine():
    return CustomRoamEngine()
```

```bash
rodski roam --case tc001 --roam-engine my_engine.py
rodski run case/ --roam --roam-engine my_engine.py
```

未注册 Handler、Handler 抛异常、返回 `None` 或返回对象不满足契约时，框架记录 warning 并跳过该 Handler。所有 Handler 均无效时，会话以 `stopped_reason="no_handler"` 正常结束；回调异常不会改变基础用例 PASS/FAIL。

漫游会话在当前 `execute_case` 内同步执行。每个动作转换为普通 test-step，通过 `_run_steps([step], "漫游")` 执行；它不通过运行时控制命令队列。临时资源由执行器快照、应用并在执行后恢复。

该事件**只能**通过 `SKIExecutor(hooks=...)` 或 `--roam-engine` 注册，不映射到项目或全局 `hooks.json`。外部命令协议适用于低频生命周期/通知类事件，不承载逐轮漫游决策。

---

## 3. 外部命令 hook 与 `hooks.json`

适合与外部系统（通知、审批、自定义合规规则）集成，不需要写 Python 代码。

### 配置文件位置与优先级

1. 项目内：`{module_dir}/hooks.json`
2. 全局：`~/.rodski/hooks.json`

**项目内配置存在时完全覆盖全局配置**（不做按事件合并）。两者都不存在时静默视为无外部 hook（多数用户不配置，属正常情况）。

### 格式

```json
{
  "on_session_start": [{"command": ["python3", "scripts/probe_env.py"], "timeout": 5}],
  "on_run_start": [{"command": ["python3", "scripts/check_env.py"], "timeout": 10}],
  "on_case_failure": [{"command": ["./notify.sh"]}],
  "on_run_end": [{"command": ["python3", "scripts/report_ci.py"]}]
}
```

- `command`：**必须**是非空字符串数组，不经过 shell 执行（避免命令注入）。字符串或缺失会在加载时抛 `InvalidConfigError`（`SKI102`）。
- `timeout`：可选，秒，默认 10。

### 协议：stdin JSON / exit code

- 上下文以 JSON 经 stdin 传给外部命令。
- **exit code 0**：继续下一个 hook（全部通过才 allow）。
- **exit code 2**：立即 deny，短路后续 hook。stdout 若是 JSON 且含 `reason`/`detail` 字段，会作为拒绝理由；否则用原始文本。
- **其他非零**：记录 warning 但不阻断，继续下一个 hook。
- **超时**：按 deny 处理（视为该 hook 返回 deny），记录 `SKI702`。

示例外部命令（Python）：

```python
import sys, json

context = json.loads(sys.stdin.read())
if context.get("module_dir", "").endswith("prod_env"):
    print(json.dumps({"reason": "禁止在 prod_env 目录下执行"}))
    sys.exit(2)
sys.exit(0)
```

---

## 4. `on_run_start` 内置合规检查

`rodski run` 在执行前自动跑四类静态检查（`core/compliance_check.py::run_compliance_checks`）：

| 检查项 | 内容 |
|---|---|
| `directory_structure` | 测试模块目录必须包含 `case/`、`model/`、`data/` |
| `plan_selector_conflict` | `@plan_id` 与 `--tag`/`--group`/`--exclude-tag`/`--priority` 不能同时使用 |
| `data_schema_consistency` | `data.sqlite` 逻辑表字段集合必须与 schema 完全一致 |
| `return_ref_self_check` | 接口/DB 模型的 `_verify` 数据表中不能出现 `${Return[-1]}` 自引用空校验 |

任一检查失败会抛 `ComplianceCheckFailedError`（`SKI703`），CLI 退出码为 1。可用 `--force-compliance` 显式跳过——**除 `directory_structure` 外**（目录结构缺失是硬性前提，无法跳过）。跳过时会记录 `logger.warning`，留痕在日志里。

```bash
rodski run case/ --force-compliance
```

---

## 5. 两级防御关系（Codex/Claude Code Hooks vs RodSki Hooks）

若上游用 Codex/Claude Code 驱动 `rodski` CLI，两层 hook 各管各的：

- **上游层**：拦不拦 `rodski run ...` 这条命令本身（通用编码 agent 风险）
- **RodSki 内部层**（本文档）：命令放行之后，具体关键字/整次运行是否合规（RodSki 特有风险）

两层互不感知，Agent 集成时需同时遵守。详见 `AGENT_INTEGRATION.md` 错误契约一节。

---

## 6. 新增错误码（`SKI7xx` 段）

| 错误码 | 异常类 | 说明 |
|---|---|---|
| `SKI701` | `HookDeniedError` | `before_keyword` deny 或外部命令 hook 返回 exit code 2 |
| `SKI702` | `HookTimeoutError` | 外部命令 hook 执行超时（`error_level=WARNING`） |
| `SKI703` | `ComplianceCheckFailedError` | `on_run_start` 合规检查未通过且未 `--force-compliance` 跳过 |
