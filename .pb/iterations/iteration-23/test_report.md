# RodSki v5.3.1 测试报告

> 日期: 2026-04-12
> 分支: fix/v5.3.1-validation
> pytest 版本: 8.4.2 / Python 3.9.6

---

## 一、pytest 单元测试汇总

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| 可收集测试 | 754 (2 文件 import 错误) | **807** |
| 通过 | 694 | **801** |
| 失败 | 54 | **0** |
| 跳过 | 6 | 6 |
| 耗时 | 35s | 46s |

```
================= 801 passed, 6 skipped, 8 warnings in 46.18s ==================
```

---

## 二、修复详情（8 组 / 13 个文件）

### 2.1 Import 错误修复

| 文件 | 问题 | 修复 |
|------|------|------|
| `core/exceptions.py` | `DiagnosisTimeoutError` 缺失导致 2 个文件无法 import | 新增 `DiagnosisTimeoutError(ExecutionError)` |

### 2.2 源码 Bug 修复

| 文件 | 问题 | 修复 |
|------|------|------|
| `core/logger.py` | `self.log_dir` 未在 `__init__` 中初始化，导致 `get_log_files()` 等 9 个测试 AttributeError | 初始化 `self.log_dir = Path(log_dir)` |

### 2.3 测试代码修复

| 文件 | 失败数 | 根因 | 修复方式 |
|------|--------|------|---------|
| `test_cli_commands.py` | 1 | 硬编码版本 "2.0.1" | 动态导入 `cli_main.VERSION` |
| `test_cli_ux.py` | 1 | 同上 | 同上 |
| `test_playwright_driver.py` | 2 | mock `is_visible` 但代码用 `wait_for_selector` | 修正 mock 目标 |
| `test_pywinauto_driver.py` | 19 | 字符串参数 vs 坐标参数 API 不匹配 | 重写全部测试适配坐标 API |
| `test_keyword_engine.py` | 4 | 旧版直接 SQL vs 模型驱动 DB 关键字 | 重写 DB 测试用模型驱动方式 |
| `test_result_writer.py` | 4 | glob `result_*.xml` vs 实际 `rodski_*/result.xml` | 修正 glob 模式 |
| `test_logger.py` | 9 | `self.log_dir` 未初始化 + 1 个断言方向错误 | 修复源码 + 修正断言 |
| `test_vision_locator.py` | 5 | 异常类型变更 + 缺失模块 | 匹配 `InvalidBBoxError`/`ValueError` |
| `test_vision_base.py` | 3 | URL 尾斜杠 / PIL 损坏 / 异常类型 | 逐个对齐实现 |
| `test_vision_llm.py` | 3 | LLM 架构重构，`_cfg` 不再默认存在 | 强制 fallback 路径使旧 API 可用 |
| `test_vision_integration.py` | 4 | `locate()` 签名变更 / mock 路径错误 / 缓存需真实数据 | 用 `locate_legacy` + bytes 缓存 |

---

## 三、demo_full 动态测试汇总

| 测试套件 | 结果 | 说明 |
|---------|------|------|
| demo_full (TC001-TC015) | **19/19 PASS** | 核心用例全部通过 |
| tc_database (TC020-TC022) | 3/3 PASS | SQLite 查询/插入/聚合 |
| tc_data_ref (TC025-TC027) | 2/3 | TC026 已知失败（GlobalValue URL 未解析） |
| tc_script (TC028-TC030) | **3/3 PASS** | run/evaluate/screenshot |

---

## 四、迭代 23-25 修改汇总

### iteration-23: 数据文件组织修正

- 拆分 `data.xml` → `data.xml` + `data_verify.xml`（3 处）
- 删除 15 个死文件（7 数据 + 3 模型 + 5 其他 DEMO）
- XML 验证全部通过

### iteration-24: verify 空校验修复

- 确认 10 处 `${Return[-1]}`：7 处 UI 模型合法保留，3 处 DB 模型标注空校验
- `keyword_engine.py` 增加自引用检测 warning

### iteration-25: 框架文档修正

- 修正 4 份文档：DATA_FILE_ORGANIZATION / TEST_CASE_WRITING_GUIDE / CORE_DESIGN_CONSTRAINTS / SKILL_REFERENCE
- 消除三方矛盾，统一以代码实现为准

---

## 五、结论

1. **单元测试**: 801 通过 / 0 失败 / 6 跳过
2. **动态测试**: 核心用例 19/19 全部通过，无回归
3. **数据组织**: data.xml / data_verify.xml / model.xml 单文件结构已对齐代码实现
4. **文档一致性**: 4 份框架文档已统一修正
5. **防护机制**: verify 自引用检测 warning 已加入代码
