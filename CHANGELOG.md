# Changelog

All notable changes to RodSki will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [10.0.0] - 2026-08-21

### 🚀 Major Changes

**探索测试架构简化（三层 → 两层）**

- 废弃 `rodski-agent/explore` 中间层
- 新架构：Claude Code + Skill → `rodski explore-step` CLI
- 决策层上移到 AI Agent（Claude Code/Codex/AutoGPT）

### ✨ Added

**核心功能**
- `rodski explore-step` - 单步探索命令 CLI
- 会话管理模块（`rodski/core/explore/session.py`）
  - `ExploreSession`: 会话状态数据结构
  - `ExploreSessionStore`: 会话持久化（原子写入）
  - `BudgetGuard`: 预算控制（步数/时长/token/成本）+ 去重
- `ExploreExecutor` 增强：浏览器错误采集、证据增强

**Skill 文档**
- `rodski-skill--explore`: 完整的探索测试 skill（515 行）
  - 5 个阶段执行纪律
  - 数据唯一性处理指南
  - 框架无关设计（支持任何 Markdown skill Agent）
- 参考文档：charter-design.md、finding-classification.md、budget-tuning.md

**核心特性**
- ✅ 基于已通过用例建立基线
- ✅ 探索合理业务边界线下的异常
- ✅ 数据唯一性处理（避免重复主键误判）
- ✅ 框架无关设计
- ✅ 预算控制和去重机制

### 🔧 Changed

- CLI 注册：新增 `explore-step` 子命令
- 版本号：9.2.3 → 10.0.0 (MAJOR)

### 🗑️ Deprecated

- `rodski-agent/explore` - 标记为废弃
  - 原因：架构简化，决策层上移到 Claude Code
  - 短期保留代码，长期（v11.x）可能移除
  - 替代方案：使用 `rodski-skill--explore` + `rodski explore-step` CLI

### 📝 Documentation

- PRD: `.pb/requirements/v10-explore-testing-prd.md`
- 迭代总结: `.pb/iterations/iteration-v10.0.0/SUMMARY.md`
- Skill 文档: `.claude/skills/rodski-skill--explore/SKILL.md`

### 🧪 Tests

- 单元测试：16/16 passed（会话管理模块完整覆盖）
- 覆盖率：> 80%

### 🐛 Fixed

- CLI 导出问题：`rodski_cli/__init__.py` 添加 `explore` 导出

### 💔 Breaking Changes

**不兼容 v9 的变化**
- 废弃 `rodski-agent/explore` Python API
- 探索测试需要使用新的 `rodski explore-step` CLI
- 需要 Python >= 3.8

### 📦 Migration Guide

**从 v9 迁移到 v10**

```python
# v9 (已废弃)
from rodski_agent.explore.executor import ExploreAgent
agent = ExploreAgent(execute_command_fn=...)
session = agent.explore_loop()

# v10 (推荐)
# 方式 1: 在 Claude Code 中使用 /explore skill
# 方式 2: 直接调用 CLI
import subprocess
result = subprocess.run([
    "rodski", "explore-step",
    "--module", "path/to/module",
    "--session", "session_id",
    "--action", "navigate",
    "--data", "http://..."
], capture_output=True)
```

---

## [9.2.3] - 2026-08-13

### Fixed
- 探索测试集成问题修复
- 证据采集增强

---

## [9.0.0] - 2026-08-10

### Added
- 探索式测试完整实现（三层架构）
- ExploreExecutor: execute_command() API

---

## [8.4.0] - 2026-08-01

### Added
- roam 漫游测试（基于已通过用例的数据漫游）

---

[10.0.0]: https://github.com/your-org/rodski/compare/v9.2.3...v10.0.0
[9.2.3]: https://github.com/your-org/rodski/compare/v9.0.0...v9.2.3
[9.0.0]: https://github.com/your-org/rodski/compare/v8.4.0...v9.0.0
[8.4.0]: https://github.com/your-org/rodski/releases/tag/v8.4.0
