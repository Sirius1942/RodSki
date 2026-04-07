# Iteration 07: 文档体系重构 — 设计文档

---

## 设计目标

1. **用户视角组织**: 按用户任务（Getting Started / Writing Tests / Integration / Reference）组织，而非按功能模块
2. **渐进式披露**: 从快速入门到深入参考，用户可以选择性深入
3. **可执行示例**: 所有示例代码附在 `examples/` 目录，可直接运行
4. **单一事实来源**: 配置项、关键字参数等信息仅在一处定义（代码或 Schema），文档自动同步

---

## 一、文档目录结构

### 1.1 顶层目录设计

```
docs/
├── README.md                     # 文档首页（总导航）
├── getting-started/              # 新手上路
│   ├── INSTALL.md
│   ├── QUICKSTART.md
│   └── FIRST_TEST.md
├── user-guides/                  # 用户指南（按任务）
│   ├── TEST_CASE_WRITING.md
│   ├── EXCEPTION_HANDLING.md
│   ├── DYNAMIC_EXECUTION.md
│   ├── RESULT_REPORT.md
│   ├── PARALLEL_EXECUTION.md
│   └── TROUBLESHOOTING.md
├── agent-integration/            # AI Agent 集成（新增）
│   ├── AGENT_INTEGRATION.md
│   └── OPENCLAW_SKILL.md
├── reference/                    # 参考资料（新增）
│   ├── KEYWORD_REFERENCE.md
│   ├── CONFIG_REFERENCE.md
│   └── CLI_REFERENCE.md
└── best-practices/               # 最佳实践（新增）
    ├── ERROR_HANDLING.md
    └── PERFORMANCE.md
```

### 1.2 迁移策略

现有文档移动/重命名映射:

| 原路径 | 新路径 |
|--------|--------|
| `docs/user-guides/QUICKSTART.md` | `docs/getting-started/QUICKSTART.md` |
| `docs/user-guides/EXCEPTION_HANDLING.md` | `docs/user-guides/EXCEPTION_HANDLING.md` (保留) |
| `docs/user-guides/TROUBLESHOOTING.md` | `docs/user-guides/TROUBLESHOOTING.md` (保留) |
| `docs/agent-integration.md` | `docs/agent-integration/AGENT_INTEGRATION.md` (重构) |
| `docs/skill-integration.md` | 删除（内容合并到 `OPENCLAW_SKILL.md`) |

---

## 二、文档编写规范

### 2.1 Frontmatter 标准

所有 Markdown 文件使用统一 frontmatter:

```markdown
---
title: 关键字参考
description: RodSki 支持的所有 17 个关键字的完整参考
slug: keyword-reference
tags: [reference, keywords]
related_doc:
  - /docs/user-guides/TEST_CASE_WRITING.md
  - /docs/reference/CLI_REFERENCE.md
---
```

### 2.2 代码示例标注

所有代码示例标注语言和来源:

````markdown
```python
# File: examples/agent/claude_code_integration.py
from rodski import SKIExecutor

executor = SKIExecutor(case_path="case.xml", driver=driver)
```
````

### 2.3 交叉引用格式

文档内使用相对链接交叉引用:

```markdown
详见[异常处理指南](../user-guides/EXCEPTION_HANDLING.md)
参见[关键字参考](../reference/KEYWORD_REFERENCE.md#click)
```

---

## 三、文档自动生成

### 3.1 从代码生成参考文档

**文件**: `scripts/generate_docs.py` (新)

从代码注释和 Schema 自动生成部分参考文档：

```python
class DocGenerator:
    def generate_keyword_reference(self) -> str:
        """从 keyword_engine.py 的文档字符串生成 KEYWORD_REFERENCE.md"""
        ...

    def generate_config_reference(self) -> str:
        """从 config/default_config.yaml 生成 CONFIG_REFERENCE.md"""
        ...

    def generate_cli_reference(self) -> str:
        """从 core/cli.py 的 click 装饰器生成 CLI_REFERENCE.md"""
        ...
```

### 3.2 Schema 驱动文档

配置项参考从 Schema 和默认值文件生成：

```python
def generate_config_from_yaml():
    """读取 config/default_config.yaml，生成 Markdown 表格"""
    config = yaml.safe_load(open("config/default_config.yaml"))
    for section, values in config.items():
        for key, value in values.items():
            # 生成 | key | type | default | description | 表格行
            ...
```

---

## 四、文档站构建

### 4.1 MkDocs 配置

**文件**: `mkdocs.yml` (新)

```yaml
site_name: RodSki Documentation
site_description: SKI 自动化测试执行引擎文档
site_author: Lightning Strike Team

theme:
  name: material
  palette:
    primary: indigo
    accent: blue

nav:
  - Home: index.md
  - Getting Started:
    - getting-started/INSTALL.md
    - getting-started/QUICKSTART.md
    - getting-started/FIRST_TEST.md
  - User Guides:
    - user-guides/TEST_CASE_WRITING.md
    - user-guides/EXCEPTION_HANDLING.md
    - user-guides/DYNAMIC_EXECUTION.md
    - user-guides/RESULT_REPORT.md
    - user-guides/PARALLEL_EXECUTION.md
    - user-guides/TROUBLESHOOTING.md
  - Agent Integration:
    - agent-integration/AGENT_INTEGRATION.md
    - agent-integration/OPENCLAW_SKILL.md
  - Reference:
    - reference/KEYWORD_REFERENCE.md
    - reference/CONFIG_REFERENCE.md
    - reference/CLI_REFERENCE.md
  - Best Practices:
    - best-practices/ERROR_HANDLING.md
    - best-practices/PERFORMANCE.md

markdown_extensions:
  - pymdownx.highlight
  - pymdownx.superfences
  - admonition
  - toc:
      permalink: true
```

### 4.2 文档构建命令

```bash
# 本地预览
mkdocs serve

# 构建静态站点
mkdocs build

# 发布到 GitHub Pages
mkdocs gh-deploy
```

---

## 五、文档审查清单

每次文档 PR 需要检查:

- [ ] 所有代码示例可运行
- [ ] 所有链接有效（无死链）
- [ ] 文档结构符合上述目录规范
- [ ] frontmatter 完整
- [ ] 交叉引用使用相对路径
- [ ] 中文文档无错别字
- [ ] 英文文档语法正确
- [ ] 示例文件放在 `examples/` 目录
