# Iteration 26 执行记录: 契约统一 + 历史包袱清理

> 版本: v5.4.0  
> 分支: release/v5.4.0  
> 开始时间: 2026-04-13  
> 状态: ✅ 已完成

---

## 任务执行记录

### T26-001: 迁移所有 model XML 到 `<location>` 格式 ✅

20 个 XML 文件完成迁移：
- `rodski-demo/DEMO/vision_web/model/model.xml` — 3 元素
- `rodski-demo/DEMO/vision_desktop/model/model.xml` — 22 元素
- `rodski/examples/product/cassmall-beta/` 下 5 个 model 文件
- `CassMall_examples/` 下 13 个 model 文件（含 63 个 API field/static 元素）

转换模式：
- `locator="type:value"` → `<location type="...">value</location>`
- `type="id" value="xxx"` → `<location type="id">xxx</location>`
- `desc` 属性 → `<desc>` 子元素
- 保留 `type="web"` / `type="interface"` / `type="database"` 驱动类型不变

### T26-002: model_parser.py 移除旧定位器格式 ✅

- 删除 `_parse_element()` 中 `locator` 属性解析代码块
- 删除 `_parse_element()` 中 `type+value` 简化格式代码块
- 只保留 `<location>` 子元素解析
- 更新 docstring
- 新增 3 个测试：旧格式返回 None、新格式正常解析

22 个测试全部通过。

### T26-003: vision/locator.py 移除旧前缀解析 ✅

- `is_vision_locator()` 添加 DeprecationWarning
- `locate_legacy()` 添加 DeprecationWarning
- `locate_with_driver()` 标记废弃
- 更新模块 docstring

36 个测试全部通过，deprecation warnings 正常触发。

### T26-004: 移除 Excel 相关代码 ✅

9 个文件修改：
- `requirements.txt` — 删除 `openpyxl>=3.1.0`
- `tests/conftest.py` — 删除 openpyxl warning filter
- `cli_main.py` — 6 处 `case.xlsx` → `case/`
- `tests/` — 3 个测试文件 `.xlsx` → `.xml`
- `core/` — 3 个模块注释移除 Excel 历史引用

### T26-005: Agent 示例归档 ✅

- 4 个文件从 `rodski/examples/agent/` 移至 `.pb/archive/agent_examples/`
- 新增 `ARCHIVE_NOTE.md`
- `rodski/examples/agent/` 目录已删除

### T26-006: 全量回归测试 ✅

- **1126 passed, 2 skipped, 3 xfailed** — 零失败
- 格式审计：4 项全部零残留

---

## 审计结果

| 审计项 | 结果 |
|--------|------|
| `locator="..."` XML 属性 | 0 |
| `xlsx` / `openpyxl` Python 引用 | 0 |
| `type="id" value="..."` 简化格式 | 0 |
| `rodski/examples/agent/` 目录 | 已删除 |

---

## 文件变更汇总

| 类别 | 文件数 | 说明 |
|------|--------|------|
| XML 迁移 | 20 | model XML 统一为 `<location>` 格式 |
| 代码修改 | 3 | model_parser.py, vision/locator.py, cli_main.py |
| 依赖清理 | 1 | requirements.txt 移除 openpyxl |
| 测试更新 | 5 | test_model_parser, test_cli_ux, test_keyword_engine, test_cli_commands, conftest |
| 注释更新 | 3 | result_writer, ski_executor, global_value_parser |
| 文件归档 | 4 | examples/agent/ → .pb/archive/agent_examples/ |

---

## 记录人

Claude (AI Agent) | 2026-04-13
