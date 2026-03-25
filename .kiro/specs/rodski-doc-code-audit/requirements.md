# 需求文档：RodSki 文档与代码一致性审计

## 简介

本文档定义 RodSki 测试框架的文档与代码一致性审计需求。审计以**核心设计约束.md (v3.5)** 和 **TEST_CASE_WRITING_GUIDE.md (v3.3)** 为权威来源，检查其余文档和遗留代码中与之不一致的问题，并提出修正需求。

动态步骤设计（核心设计约束 §8）、Agent 自动化设计、多模态问题判别器等规划阶段内容不在本次审计范围内。

## 术语表

- **Framework**: RodSki 关键字驱动自动化测试框架
- **核心设计约束**: `rodski/docs/design/核心设计约束.md`，框架的权威设计规范文档 (v3.5)
- **用例编写指南**: `rodski/docs/user-guides/TEST_CASE_WRITING_GUIDE.md`，面向用户的权威使用指南 (v3.3)
- **SUPPORTED**: `core/keyword_engine.py` 中定义的合法关键字列表（14 个 + 兼容关键字 `check`）
- **Case_XML**: 符合 `schemas/case.xsd` 的测试用例 XML 文件
- **Data_XML**: 符合 `schemas/data.xsd` 的数据表 XML 文件
- **Model_XML**: 符合 `schemas/model.xsd` 的模型 XML 文件
- **GlobalValue_XML**: 符合 `schemas/globalvalue.xsd` 的全局变量 XML 文件
- **send_verify_模式**: 接口测试通过 `send`（发送请求）+ `verify`（验证响应）完成的标准模式
- **type_批量模式**: UI 操作通过 `type` 关键字遍历模型元素、从数据表取值逐一执行的标准模式
- **遗留_Excel_代码**: 框架迁移到 XML 格式前遗留的 Excel 解析相关代码

## 需求

### 需求 1：重写 API_TESTING_GUIDE.md

**用户故事：** 作为测试工程师，我希望 API 测试指南与框架实际的 send + verify 接口测试模式一致，以便正确编写接口测试用例。

#### 验收标准

1. WHEN 用户阅读 API_TESTING_GUIDE.md 时，THE Framework 文档 SHALL 仅描述 `send` + `verify` 接口测试模式，不包含 `http_get`、`http_post`、`http_put`、`http_delete`、`assert_status`、`assert_json` 等已废弃的独立 HTTP 关键字
2. THE API_TESTING_GUIDE.md SHALL 包含接口模型定义示例（`_method`、`_url`、`_header_*` 元素命名约定），与核心设计约束 §3.1 一致
3. THE API_TESTING_GUIDE.md SHALL 包含 `send` 响应存储格式说明（`{"status": 200, ...}` 字典），与核心设计约束 §3.2 一致
4. THE API_TESTING_GUIDE.md SHALL 包含 `verify` 接口验证说明（从 `Return[-1]` 读取实际值、`_verify` 数据表中 `status` 列验证状态码），与核心设计约束 §3.3 一致
5. THE API_TESTING_GUIDE.md SHALL 使用 XML 格式的用例示例（Case_XML + Data_XML + Model_XML），替代所有 Excel 格式示例
6. THE API_TESTING_GUIDE.md SHALL 移除所有 JSONPath 语法说明（框架不使用 JSONPath）

### 需求 2：重写 QUICKSTART.md

**用户故事：** 作为新用户，我希望快速入门指南基于当前 XML 格式，以便正确理解框架的用例结构和运行方式。

#### 验收标准

1. THE QUICKSTART.md SHALL 使用 XML 格式描述用例结构（Case_XML、Data_XML、GlobalValue_XML、Model_XML），替代所有 Excel Sheet 描述（Case Sheet、GlobalValue Sheet、数据表 Sheet）
2. THE QUICKSTART.md SHALL 使用 `product/DEMO/demo_site/` 下的实际 XML 文件作为示例路径
3. WHEN 描述运行命令时，THE QUICKSTART.md SHALL 使用 XML 文件路径（如 `python ski_run.py product/DEMO/demo_site/case/demo_case.xml`），替代 `.xlsx` 文件路径
4. THE QUICKSTART.md SHALL 描述三阶段容器结构（`pre_process` → `test_case` → `post_process`），替代 Excel 的单行步骤描述
5. THE QUICKSTART.md SHALL 描述结果输出为 `result/*.xml`（框架自动生成），替代 "结果回填到 Excel TestResult Sheet" 的描述
6. THE QUICKSTART.md SHALL 描述目录结构约束（`case/`、`model/`、`data/`、`fun/`、`result/` 五个固定目录），与核心设计约束 §6 一致

### 需求 3：更新 README.md

**用户故事：** 作为潜在用户，我希望 README 准确反映框架当前状态，以便正确评估和使用框架。

#### 验收标准

1. THE README.md SHALL 将特性描述从 "📊 Excel 用例 - 零编程门槛" 更新为 XML 用例格式描述
2. THE README.md SHALL 移除 `python3 ski_gui.py` 的 GUI 运行命令（该文件不存在于代码库中）
3. WHEN 描述 CLI 运行命令时，THE README.md SHALL 使用 XML 文件路径（如 `python3 cli_main.py run product/DEMO/demo_site/case/demo_case.xml`），替代 `.xlsx` 文件路径
4. THE README.md SHALL 将 Python 版本要求与 `pyproject.toml` 和实际支持范围保持一致
5. THE README.md SHALL 移除项目结构中不存在的目录引用（如 `ui/`、`tests/`）

### 需求 4：更新 ARCHITECTURE.md

**用户故事：** 作为开发者，我希望架构文档准确反映当前代码结构，以便正确理解框架内部设计。

#### 验收标准

1. THE ARCHITECTURE.md SHALL 移除目录结构中不存在的文件和目录（`ui/main_window.py`、`utils/helpers.py`、`tests/` 目录、`setup.py`）
2. THE ARCHITECTURE.md SHALL 将 `setup.py` 引用更新为 `pyproject.toml`
3. THE ARCHITECTURE.md SHALL 在关键字清单中将 `open` 替换为 `navigate`，与核心设计约束 §1.3 一致
4. THE ARCHITECTURE.md SHALL 将数据流图从 Excel 格式更新为 XML 格式（CaseParser 解析 `case/*.xml`，DataTableParser 解析 `data/*.xml`）
5. THE ARCHITECTURE.md SHALL 将 BaseDriver 抽象方法列表中移除 `http_get`、`http_post`、`http_put`、`http_delete`（这些不是驱动层方法，接口测试通过 `send` 关键字 + `rest_helper` 完成）
6. THE ARCHITECTURE.md SHALL 将执行流程图中的 `ExcelParser.parse()` 更新为 XML 解析流程
7. THE ARCHITECTURE.md SHALL 在 `data/` 模块描述中添加 `model_manager.py`

### 需求 5：更新 MOBILE_GUIDE.md

**用户故事：** 作为移动端测试工程师，我希望移动端指南与框架的关键字设计一致，以便正确编写移动端测试用例。

#### 验收标准

1. THE MOBILE_GUIDE.md SHALL 将 "支持的关键字" 章节中的 `click`、`swipe`、`tap`、`long_press`、`scroll` 等从独立关键字描述改为数据表字段值描述，与核心设计约束 §1.2 一致
2. THE MOBILE_GUIDE.md SHALL 使用 `type` 批量模式 + 数据表字段值的方式描述移动端操作（如 `<field name="loginBtn">click</field>`），替代 `driver.click("id=button")` 的直接调用示例
3. THE MOBILE_GUIDE.md SHALL 使用 XML 格式的用例示例（Case_XML + Data_XML + Model_XML），替代 Python 代码直接调用驱动的示例

### 需求 6：更新 CI_CD_GUIDE.md

**用户故事：** 作为 DevOps 工程师，我希望 CI/CD 指南与框架当前的文件格式和测试方式一致，以便正确配置持续集成流水线。

#### 验收标准

1. THE CI_CD_GUIDE.md SHALL 将所有 `.xlsx` 文件引用更新为 `.xml` 文件引用
2. THE CI_CD_GUIDE.md SHALL 将 `python run_tests.py` 命令更新为 `python selftest.py`，与核心设计约束 §9.3 一致
3. THE CI_CD_GUIDE.md SHALL 移除所有 `pytest`、`coverage`、`pytest-cov` 相关引用和配置，与核心设计约束 §9 "不依赖外部测试框架" 约束一致
4. THE CI_CD_GUIDE.md SHALL 将 Python 版本范围描述与 README.md 保持一致

### 需求 7：更新 PARALLEL_EXECUTION.md

**用户故事：** 作为测试工程师，我希望并发执行指南使用框架标准的步骤格式，以便正确理解并发执行的用例结构。

#### 验收标准

1. THE PARALLEL_EXECUTION.md SHALL 将步骤格式从 `{"keyword": "navigate", "params": {"url": "..."}}` 更新为与 Case_XML test_step 同构的格式 `{"action": "navigate", "model": "", "data": "..."}`
2. THE PARALLEL_EXECUTION.md SHALL 移除 `click` 作为独立关键字的示例（`{"keyword": "click", "params": {"locator": "#login"}}`），与核心设计约束 §1.2 一致

### 需求 8：清理遗留 Excel 代码依赖

**用户故事：** 作为框架维护者，我希望代码中的遗留 Excel 依赖被明确标记或清理，以避免新开发者混淆 XML 和 Excel 两套数据解析路径。

#### 验收标准

1. THE Framework SHALL 在 `core/data_parser.py` 文件顶部添加废弃标记（deprecation notice），说明该模块为遗留 Excel 解析代码，新代码应使用 `data/data_resolver.py`
2. THE Framework SHALL 在 `data/excel_parser.py` 文件顶部添加废弃标记，说明该模块为遗留 Excel 解析器
3. THE Framework SHALL 在 `keyword_engine.py` 的 `__init__` 方法中，为 `self.data_parser = DataParser(data_dir, self)` 行添加注释，说明该初始化为遗留兼容代码，XML 模式使用 `data_resolver`

### 需求 9：处理 ModelManager JSON 格式不一致

**用户故事：** 作为框架维护者，我希望 `data/model_manager.py` 的定位被明确，以避免与 XML 模型体系（`core/model_parser.py` + `model.xsd`）产生混淆。

#### 验收标准

1. THE Framework SHALL 在 `data/model_manager.py` 文件顶部添加说明注释，明确该模块的用途与 `core/model_parser.py`（XML 模型解析）的关系
2. IF `data/model_manager.py` 仅用于遗留兼容或独立功能，THEN THE Framework SHALL 在注释中标注其适用场景，避免与 XML 模型体系混淆

### 需求 10：移除或标记 GUI_USAGE.md

**用户故事：** 作为用户，我希望文档中不包含引用不存在文件的指南，以避免困惑。

#### 验收标准

1. IF `ski_gui.py` 不存在于代码库中，THEN THE Framework SHALL 移除 `docs/GUI_USAGE.md` 文件，或在文件顶部添加明确的 "已废弃" 标记
2. THE QUICKSTART.md SHALL 移除 "进阶学习" 章节中对 `docs/GUI_USAGE.md` 的引用
3. THE README.md SHALL 移除对 `ski_gui.py` 的所有引用

### 需求 11：统一 Return 引用格式

**用户故事：** 作为框架维护者，我希望 Return 引用格式在代码中统一，以避免解析歧义。

#### 验收标准

1. THE `core/data_parser.py`（遗留代码）SHALL 在废弃标记中说明其使用 `${Return[-1]}` 格式（带 `${}`），而当前标准格式为 `Return[-1]`（不带 `${}`，由 `data/data_resolver.py` 解析）
2. THE 用例编写指南 SHALL 仅描述 `Return[-1]` 格式（不带 `${}`），与 `data/data_resolver.py` 的实现一致

