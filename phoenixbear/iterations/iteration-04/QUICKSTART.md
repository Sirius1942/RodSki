# Iteration 04 快速开始

## 使用 JSON 输出

```bash
# 基本用法
python3 -c "from rodski_cli import main; import sys; sys.argv = ['rodski', 'run', 'case.xml', '--output-format', 'json']; main()"

# 无头模式
python3 -c "from rodski_cli import main; import sys; sys.argv = ['rodski', 'run', 'case.xml', '--output-format', 'json', '--headless']; main()"

# 指定浏览器
python3 -c "from rodski_cli import main; import sys; sys.argv = ['rodski', 'run', 'case.xml', '--output-format', 'json', '--browser', 'firefox']; main()"
```

## 集成到 Agent

```python
import subprocess
import json

result = subprocess.run(
    ["python3", "-c",
     "from rodski_cli import main; import sys; sys.argv = ['rodski', 'run', 'case.xml', '--output-format', 'json']; main()"],
    capture_output=True, text=True
)

data = json.loads(result.stdout)
if data["status"] == "success":
    print(f"通过: {data['summary']['passed']}")
else:
    print(f"失败: {data['error']['message']}")
```

## 文档

- [../../agent/AGENT_INTEGRATION.md](../../agent/AGENT_INTEGRATION.md) - 完整 Agent 集成指南
- [../../agent/AGENT_SKILL_GUIDE.md](../../agent/AGENT_SKILL_GUIDE.md) - Skill 定义规范
- `rodski/examples/agent_integration_example.py` - 示例代码
