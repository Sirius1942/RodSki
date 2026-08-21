# RodSki 探索测试 - 快速参考

## 安装

```bash
pip install rodski>=9.2.3
pip install rodski-agent>=9.2.3
playwright install chromium
```

## 快速启动

### 使用默认约章

```bash
python3 quick_explore.py \
  --url http://localhost:8000 \
  --goal "探索登录功能" \
  --max-steps 20 \
  --max-time 300
```

### 使用自定义约章

```bash
python3 quick_explore.py \
  --charter example_charter.json \
  --output my_report.html
```

## Charter JSON 格式

```json
{
  "charter_id": "唯一标识",
  "goal": "探索目标（单句）",
  "scope": {
    "entry_point": "起点 URL",
    "allowed_domains": ["允许的域名"],
    "focus_areas": ["重点区域"]
  },
  "oracle": ["预期行为列表"],
  "allowed_actions": ["允许的关键字"],
  "budget": {
    "max_steps": 30,
    "max_time_seconds": 600
  }
}
```

## Python API

### 基础用法

```python
from rodski_agent.explore.charter import CharterCard
from rodski_agent.explore.executor import ExploreAgent

# 创建约章
charter = CharterCard(
    charter_id="TEST_001",
    goal="探索目标",
    scope={"entry_point": "http://localhost:8000"},
    oracle=["页面正常"],
    allowed_actions=["navigate", "screenshot"],
    budget={"max_steps": 20}
)

# 创建 Agent
agent = ExploreAgent(execute_command_fn=execute_command)

# 执行探索
session = agent.start_session(charter)
session = agent.explore_loop()

# 查看结果
print(f"发现问题: {len(session.findings)}")
```

### 生成报告

```python
from rodski_agent.explore.report import ExploreReportGenerator

generator = ExploreReportGenerator()
html = generator.generate_html(session, title="报告标题")

with open("report.html", "w") as f:
    f.write(html)
```

## 常见场景

### 场景 1: 探索新功能

```bash
python3 quick_explore.py \
  --url http://localhost:8000/new-feature \
  --goal "探索新功能的边界条件" \
  --max-steps 30
```

### 场景 2: 集成测试

```bash
python3 quick_explore.py \
  --url http://localhost:8000/integration \
  --goal "验证多模块集成" \
  --max-steps 50 \
  --max-time 600
```

### 场景 3: 回归增强

```bash
# 先运行传统测试
rodski run case/

# 再运行探索测试
python3 quick_explore.py \
  --url http://localhost:8000 \
  --goal "发现传统测试遗漏的问题"
```

## 支持的关键字

- `navigate` - 导航到 URL
- `wait` - 等待元素或时间
- `screenshot` - 截图
- `click` - 点击元素
- `type` - 输入文本
- `verify` - 验证元素状态
- `get_text` - 获取文本

## Finding 类型

- `BUG` - 功能性错误
- `PERFORMANCE` - 性能问题
- `USABILITY` - 可用性问题
- `SECURITY` - 安全问题

## 质量等级

- `HIGH` - 严重（影响核心功能）
- `MEDIUM` - 中等（边界条件错误）
- `LOW` - 轻微（UI 瑕疵）

## 故障排查

### 问题: 导入错误

```bash
# 检查安装
pip list | grep rodski
pip list | grep playwright

# 重新安装
pip install --upgrade rodski rodski-agent
playwright install chromium
```

### 问题: 探索卡住

- 降低 max_steps
- 缩小 allowed_domains
- 限制 allowed_actions
- 检查 session.history

### 问题: 证据缺失

- 已知限制（v9.2.4 修复中）
- Finding 仍会创建
- 查看 session.history 获取详情

## 版本要求

- rodski >= 9.2.3
- rodski-agent >= 9.2.3
- playwright >= 1.40.0
- Python >= 3.8

## 获取帮助

- 文档: `.pb/user-guides/v9.2.3-exploratory-testing-guide.md`
- Skill: `/explore`
- Issues: GitLab RodSki 仓库
