# 设计文档：RodSki 文档与代码一致性审计

## 1. 设计目标

基于**核心设计约束.md (v3.5)** 和 **TEST_CASE_WRITING_GUIDE.md (v3.3)** 作为权威来源，系统性审计并修正 `rodski/docs/` 目录下所有文档与代码的不一致问题。

## 2. 审计范围

### 2.1 包含的文档

**用户指南类**（`rodski/docs/user-guides/`）：
- API_TESTING_GUIDE.md - 接口测试指南
- QUICKSTART.md - 快速入门
- MOBILE_GUIDE.md - 移动端测试
- PARALLEL_EXECUTION.md - 并发执行
- GUI_USAGE.md - GUI 使用（需评估是否废弃）

**设计文档类**（`rodski/docs/design/`）：
- ARCHITECTURE.md - 架构文档
- CI_CD_GUIDE.md - CI/CD 集成

**项目根文档**：
- rodski/docs/README.md - 文档索引

### 2.2 排除的内容

- 动态步骤设计（核心设计约束 §8）
- Agent 自动化设计
- 多模态问题判别器
- RPA 路线图相关文档（已在 `doc/design/` 下）

## 3. 核心设计原则

### 3.1 格式迁移原则

**从 Excel 到 XML**：
- 所有用例示例使用 XML 格式（Case_XML + Data_XML + Model_XML）
- 移除所有 Excel Sheet 描述和 `.xlsx` 文件路径
- 结果输出为 `result/*.xml`，不再回填 Excel

### 3.2 关键字设计原则

**14 个合法关键字** + 兼容关键字 `check`：
```
navigate, type, verify, send, wait,
execute, switch, alert, select, upload,
screenshot, scroll, refresh, close
```

**重要约束**：
- `click`、`swipe`、`tap` 等不是独立关键字，而是 `type` 关键字的数据表字段值
- 接口测试使用 `send` + `verify` 模式，不使用 `http_get`/`http_post` 等独立关键字
- `open` 已重命名为 `navigate`

### 3.3 接口测试模式

**send + verify 标准模式**：
1. 模型定义：`_method`、`_url`、`_header_*` 元素
2. `send` 执行：返回 `{"status": 200, "headers": {...}, "body": {...}}` 字典
3. 响应存储：`Return[-1]` 格式（不带 `${}`）
4. `verify` 验证：从 `Return[-1]` 读取实际值，与数据表 `_verify` 字段对比

### 3.4 目录结构约束

固定五目录结构（核心设计约束 §6）：
```
product/<project>/<site>/
├── case/      # 测试用例 XML
├── model/     # 页面/接口模型 XML
├── data/      # 数据表 XML
├── fun/       # 自定义函数
└── result/    # 执行结果 XML（自动生成）
```

## 4. 文档修正策略

### 4.1 API_TESTING_GUIDE.md 重写

**移除内容**：
- 独立 HTTP 关键字：`http_get`、`http_post`、`http_put`、`http_delete`
- 断言关键字：`assert_status`、`assert_json`
- JSONPath 语法说明
- Excel 格式示例

**新增内容**：
- 接口模型定义示例（`_method`、`_url`、`_header_*`）
- `send` 响应存储格式（`{"status": 200, ...}`）
- `verify` 验证机制（`Return[-1]` + `_verify` 数据表）
- XML 格式完整示例

### 4.2 QUICKSTART.md 重写

**替换内容**：
- Excel Sheet → XML 文件（Case_XML、Data_XML、Model_XML、GlobalValue_XML）
- `.xlsx` 路径 → `.xml` 路径
- 单行步骤 → 三阶段容器（`pre_process` → `test_case` → `post_process`）
- 结果回填 Excel → 结果输出 `result/*.xml`

**使用示例**：
- 路径：`product/DEMO/demo_site/`
- 命令：`python ski_run.py product/DEMO/demo_site/case/demo_case.xml`

### 4.3 README.md 更新

**修正内容**：
- 特性描述：Excel → XML
- 移除 `python3 ski_gui.py` 命令（文件不存在）
- CLI 命令：使用 `.xml` 路径
- Python 版本：与 `pyproject.toml` 一致
- 项目结构：移除不存在的目录（`ui/`、`tests/`）

### 4.4 ARCHITECTURE.md 更新

**修正内容**：
- 移除不存在的文件/目录：`ui/main_window.py`、`utils/helpers.py`、`tests/`、`setup.py`
- `setup.py` → `pyproject.toml`
- 关键字清单：`open` → `navigate`
- 数据流图：Excel → XML 解析
- BaseDriver 方法：移除 `http_get`/`http_post` 等
- 添加 `data/model_manager.py` 说明

### 4.5 MOBILE_GUIDE.md 更新

**修正内容**：
- `click`、`swipe`、`tap` 等从独立关键字 → 数据表字段值
- 使用 `type` 批量模式 + 数据表字段值描述移动端操作
- Python 直接调用示例 → XML 格式用例示例

### 4.6 CI_CD_GUIDE.md 更新

**修正内容**：
- `.xlsx` → `.xml`
- `python run_tests.py` → `python selftest.py`
- 移除 `pytest`、`coverage`、`pytest-cov` 相关内容
- Python 版本与 README.md 一致

### 4.7 PARALLEL_EXECUTION.md 更新

**修正内容**：
- 步骤格式：`{"keyword": "navigate", "params": {...}}` → `{"action": "navigate", "model": "", "data": "..."}`
- 移除 `click` 作为独立关键字的示例

### 4.8 GUI_USAGE.md 处理

**策略**：
- 如果 `ski_gui.py` 不存在 → 在文件顶部添加 "已废弃" 标记
- 从 QUICKSTART.md 和 README.md 移除引用

## 5. 代码清理策略

### 5.1 遗留 Excel 代码标记

**需要标记的文件**：
- `core/data_parser.py` - 遗留 Excel 解析代码
- `data/excel_parser.py` - 遗留 Excel 解析器
- `keyword_engine.py` 中的 `self.data_parser = DataParser(...)` 初始化

**标记格式**：
```python
# DEPRECATED: 遗留 Excel 解析代码，新代码应使用 data/data_resolver.py
# 保留此模块仅为向后兼容，XML 模式不使用此解析器
```

### 5.2 ModelManager 定位说明

在 `data/model_manager.py` 顶部添加说明注释，明确其与 `core/model_parser.py`（XML 模型解析）的关系。

### 5.3 Return 引用格式统一

**标准格式**：`${Return[-1]}`（带 `${}`）
- `data/data_resolver.py` 使用此格式
- 用例编写指南仅描述此格式
- 检查文档和示例demo代码进行修正

## 6. 实施顺序

1. **阶段 1**：重写核心用户指南
   - API_TESTING_GUIDE.md
   - QUICKSTART.md

2. **阶段 2**：更新项目文档
   - README.md
   - ARCHITECTURE.md

3. **阶段 3**：更新其他用户指南
   - MOBILE_GUIDE.md
   - CI_CD_GUIDE.md
   - PARALLEL_EXECUTION.md

4. **阶段 4**：处理 GUI_USAGE.md

5. **阶段 5**：代码清理
   - 添加废弃标记
   - 添加 ModelManager 说明
   - 统一 Return 引用格式说明

## 7. 验收标准

- 所有文档使用 XML 格式示例，无 Excel 引用
- 所有关键字描述与核心设计约束一致
- 所有文件路径和命令可执行
- 遗留代码有明确标记
- 文档间引用一致（Python 版本、目录结构等）
