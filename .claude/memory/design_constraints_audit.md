---
name: design_constraints_audit
description: 核心设计约束与代码实现审计结果（2026-04-02）
type: reference
---

2026-04-02 对 RodSki main 分支代码与核心设计约束文档的一致性审计结果：

**P0 — 阻塞性 Bug（执行必失败）**：
- `keyword_engine.py` 调用 `driver.type(locator, text)` 但 `PlaywrightDriver` 只有 `type_locator` 方法，无 `type` 方法

**P1 — 严重违规（违反设计约束 §9 自检规范）**：
- `requirements.txt` 包含 pytest/pytest-cov/pytest-mock
- `pyproject.toml` 包含 pytest 配置
- `pytest.ini` 文件存在
- 30 个测试文件使用 `import pytest`
- 框架规范明确要求自检不得使用 pytest，必须用 `selftest.py`

**P1 — 架构违规**：
- 目录结构不符合 `product/项目/模块` 三层规范（顶层 `rodski/` 直接是框架代码，无 product 包装）

**P2 — 功能偏差**：
- `screenshot` 不在 SUPPORTED 关键字列表（但 case.xsd ActionType 枚举中有）
- click/double_click/right_click/hover 动作传入坐标参数方式有问题

**Why:** 这些审计结果是代码实现与设计文档不一致的已知问题，所有新增开发都不得进一步加剧这些问题。
**How to apply:** 任何代码修改前，先检查是否属于上述违规项。
