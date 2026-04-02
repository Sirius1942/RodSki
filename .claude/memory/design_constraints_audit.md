---
name: design_constraints_audit
description: 核心设计约束与代码实现审计结果（P0/P1/P2 问题清单）
type: reference
---

**P0 — 阻塞性 Bug**：
- `keyword_engine.py` 调用 `driver.type(locator, text)` 但 `PlaywrightDriver` 只有 `type_locator` 方法，无 `type` 方法 → 批量输入必失败
- `fix/click-locator-bug` 分支已修复 click 坐标问题并合并到 main

**P1 — 严重违规（违反设计约束 §9 自检规范）**：
- `requirements.txt` 包含 pytest/pytest-cov/pytest-mock
- `pyproject.toml` 包含 pytest 配置
- `pytest.ini` 文件存在
- 30 个测试文件使用 `import pytest`
- 框架规范明确要求自检不得使用 pytest，必须用 `selftest.py`

**P1 — 架构违规**：
- 目录结构不符合 `product/项目/模块` 三层规范

**P2 — 功能偏差**：
- `screenshot` 不在 SUPPORTED 关键字列表（但 case.xsd ActionType 枚举中有）

**Why:** 审计结果是代码与设计文档不一致的已知问题，新增开发不得加剧。
**How to apply:** 任何代码修改前先检查是否属于上述违规项。
