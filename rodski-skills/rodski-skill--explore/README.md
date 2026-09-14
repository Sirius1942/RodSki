# RodSki 探索测试 Skill

RodSki AI 驱动的探索式测试能力。

## 概述

这个 skill 提供 RodSki 探索式测试的完整指南和工具，包括：

- **SKILL.md** - 探索测试核心 skill 文档
- **scripts/** - 快速启动脚本和示例
- **references/** - 最佳实践和参考文档

## 快速开始

### 1. 安装依赖

```bash
pip install rodski>=9.2.3
pip install rodski-agent>=9.2.3
playwright install chromium
```

### 2. 使用 skill

在 Claude Code 中调用：

```
/explore
```

### 3. 运行快速探索

```bash
cd rodski-skills/rodski-skill--explore/scripts
python3 quick_explore.py --url http://localhost:8000 --goal "探索核心功能"
```

## 文件结构

```
rodski-skill--explore/
├── SKILL.md                          # 核心 skill 文档
├── README.md                         # 本文件
├── scripts/
│   ├── quick_explore.py              # 快速启动脚本
│   ├── example_charter.json          # 示例探索约章
│   └── README.md                     # 脚本使用说明
└── references/
    ├── traditional-vs-exploratory.md # 传统测试 vs 探索测试对比
    └── charter-best-practices.md     # Charter 设计最佳实践
```

## 主要功能

### 1. 探索式测试指南

- 探索式测试核心概念
- Charter Card 设计
- Finding 分类体系
- 证据采集机制

### 2. 快速启动工具

- `quick_explore.py` - 一键启动探索会话
- 支持默认约章和自定义约章
- 自动生成 HTML 报告

### 3. 最佳实践文档

- **传统 vs 探索测试对比** - 详细对比两种测试方式
- **Charter 设计最佳实践** - 如何设计高质量的探索约章

## 使用场景

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
  --charter integration_charter.json \
  --output integration_report.html
```

### 场景 3: 使用 Python API

```python
from rodski_agent.explore.charter import CharterCard
from rodski_agent.explore.executor import ExploreAgent

charter = CharterCard(
    charter_id="TEST_001",
    goal="探索目标",
    scope={"entry_point": "http://localhost:8000"},
    oracle=["页面正常"],
    allowed_actions=["navigate", "screenshot"],
    budget={"max_steps": 20}
)

agent = ExploreAgent(execute_command_fn=execute_command)
session = agent.start_session(charter)
session = agent.explore_loop()
```

## 核心概念

### Charter Card (探索约章)

定义探索会话的目标、范围、预算和预期行为。

**关键字段：**
- `goal` - 探索目标
- `scope` - 探索范围（entry_point, allowed_domains, focus_areas）
- `oracle` - 预期行为列表
- `allowed_actions` - 允许的 RodSki 关键字
- `budget` - 探索预算（max_steps, max_time_seconds）

### Finding (发现的问题)

每个发现的问题包含完整分类和证据链。

**类型：**
- `BUG` - 功能性错误
- `PERFORMANCE` - 性能问题
- `USABILITY` - 可用性问题
- `SECURITY` - 安全问题

**质量等级：**
- `HIGH` - 严重
- `MEDIUM` - 中等
- `LOW` - 轻微

### Evidence (证据采集)

自动采集的证据包括：
- 截图（Base64）
- 当前 URL
- 页面标题
- 浏览器错误（自动分类）
- DOM 快照（可选）

## 版本兼容性

- **rodski** >= 9.2.3
- **rodski-agent** >= 9.2.3
- **playwright** >= 1.40.0
- **Python** >= 3.8

## v9.2.3 核心特性

### 已修复

- ✅ ConfigManager 序列化错误
- ✅ Playwright Sync API 冲突（命令执行层）
- ✅ 增强失败证据采集
- ✅ 浏览器错误自动分类
- ✅ HTML 报告生成器

### 已知限制

- ⚠️ 证据采集阶段仍有 Sync API 冲突（v9.2.4 修复中）

## 获取帮助

- **完整文档**: `.pb/user-guides/v9.2.3-exploratory-testing-guide.md`
- **核心 skill**: `SKILL.md`
- **最佳实践**: `references/charter-best-practices.md`
- **对比分析**: `references/traditional-vs-exploratory.md`

## 相关资源

### 相关 Skills

- `rodski` - RodSki 框架核心 skill
- `rodski-case-writer` - 传统测试用例编写 skill
- `diagnose` - 疑难 Bug 诊断 skill

### 核心文档

- `rodski/docs/AGENT_INTEGRATION.md` - Agent 集成指南
- `rodski/docs/CORE_DESIGN_CONSTRAINTS.md` - 核心设计约束
- `rodski-agent/README.md` - rodski-agent 使用指南

## 贡献

欢迎提交 Issue 和 Pull Request 到 RodSki 仓库。

## License

MIT License
