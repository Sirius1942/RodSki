# Iteration 04 快速开始

## 使用 JSON 输出

```bash
# 基本用法
rodski run case.xml --output-format json

# 无头模式
rodski run case.xml --output-format json --headless

# 指定浏览器
rodski run case.xml --output-format json --browser firefox
```

## 集成到 Agent

```python
import subprocess
import json

result = subprocess.run(
    ["rodski", "run", "case.xml", "--output-format", "json"],
    capture_output=True, text=True
)

data = json.loads(result.stdout)
if data["status"] == "success":
    print(f"通过: {data['summary']['passed']}")
else:
    print(f"失败: {data['error']['message']}")
```

## 文档

- `docs/agent-integration.md` - 完整集成指南
- `docs/skill-integration.md` - Skill 定义规范
- `examples/agent_integration_example.py` - 示例代码
