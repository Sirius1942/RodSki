# Skill 集成规范

## Skill 定义

RodSki 可作为 AI Agent 的 Skill 工具，执行 UI 自动化测试任务。

### Skill 名称

`rodski-test` 或 `ui-test`

### Skill 参数

```json
{
  "case_path": "string (required)",
  "browser": "chromium|firefox|webkit (optional, default: chromium)",
  "headless": "boolean (optional, default: false)"
}
```

## OpenClaw 集成示例

### 1. 定义 Skill

在 OpenClaw 配置中添加 RodSki skill：

```yaml
skills:
  - name: rodski-test
    command: rodski run {case_path} --output-format json --browser {browser} --headless
    description: 执行 UI 自动化测试
    parameters:
      - name: case_path
        type: string
        required: true
        description: 测试用例路径
      - name: browser
        type: string
        default: chromium
        description: 浏览器类型
```

### 2. 使用示例

```python
# Agent 调用
result = agent.use_skill("rodski-test", {
    "case_path": "/path/to/test/case.xml",
    "browser": "chromium"
})

# 解析结果
if result["status"] == "success":
    print(f"测试通过: {result['summary']['passed']}/{result['summary']['total_steps']}")
else:
    print(f"测试失败: {result['error']['message']}")
```

## Claude Code 集成示例

### 1. 创建 Skill 文件

创建 `.claude/skills/rodski-test.sh`:

```bash
#!/bin/bash
# Skill: rodski-test
# Description: 执行 RodSki UI 自动化测试
# Parameters: case_path, browser (optional)

CASE_PATH="$1"
BROWSER="${2:-chromium}"

rodski run "$CASE_PATH" --output-format json --browser "$BROWSER" --headless
```

### 2. 使用示例

在 Claude Code 中：

```
User: 运行登录测试用例
Claude: 我将使用 rodski-test skill 执行测试

/rodski-test /path/to/login-test.xml chromium
```

## 错误处理

Agent 应根据返回的 JSON 判断执行状态：

```python
def handle_rodski_result(result):
    if result["exit_code"] != 0:
        # 提取失败信息
        error = result.get("error", {})
        failed_step = result.get("failed_step", {})

        # 构建错误报告
        report = f"测试失败: {error.get('message')}"
        if failed_step:
            report += f"\n失败步骤: {failed_step.get('case_id')} 第 {failed_step.get('index')} 步"

        # 检查是否可恢复
        if error.get("type") == "TimeoutError":
            return {"recoverable": True, "suggestion": "增加超时时间"}

        return {"recoverable": False, "report": report}

    return {"success": True}
```
