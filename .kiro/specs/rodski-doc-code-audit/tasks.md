# 任务清单：RodSki 文档与代码一致性审计

## 任务状态说明

- ⏳ 待开始
- 🔄 进行中
- ✅ 已完成
- ⏸️ 已暂停

---

## 阶段 1：核心用户指南重写

### 任务 1.1：重写 API_TESTING_GUIDE.md ⏳

**负责人**：待分配
**优先级**：高
**预计工时**：2-3 小时

**子任务**：
1. 移除所有独立 HTTP 关键字描述（`http_get`、`http_post`、`http_put`、`http_delete`、`assert_status`、`assert_json`）
2. 移除所有 JSONPath 语法说明
3. 移除所有 Excel 格式示例
4. 添加接口模型定义示例（`_method`、`_url`、`_header_*` 元素命名约定）
5. 添加 `send` 响应存储格式说明（`{"status": 200, ...}` 字典）
6. 添加 `verify` 接口验证说明（`Return[-1]` + `_verify` 数据表）
7. 添加完整的 XML 格式接口测试示例（Case_XML + Data_XML + Model_XML）

**验收标准**：
- 文档仅描述 `send` + `verify` 模式
- 所有示例使用 XML 格式
- 与核心设计约束 §3.1-3.3 一致

---

### 任务 1.2：重写 QUICKSTART.md ⏳

**负责人**：待分配
**优先级**：高
**预计工时**：2-3 小时

**子任务**：
1. 替换所有 Excel Sheet 描述为 XML 文件描述
2. 更新示例路径为 `product/DEMO/demo_site/` 下的实际 XML 文件
3. 更新运行命令为 XML 文件路径（`python ski_run.py product/DEMO/demo_site/case/demo_case.xml`）
4. 添加三阶段容器结构描述（`pre_process` → `test_case` → `post_process`）
5. 更新结果输出描述为 `result/*.xml`
6. 添加目录结构约束说明（`case/`、`model/`、`data/`、`fun/`、`result/`）
7. 移除 "进阶学习" 章节中对 `docs/GUI_USAGE.md` 的引用

**验收标准**：
- 所有描述基于 XML 格式
- 示例路径可执行
- 与核心设计约束 §6 一致

---

## 阶段 2：项目文档更新

### 任务 2.1：更新 rodski/docs/README.md ⏳

**负责人**：待分配
**优先级**：中
**预计工时**：1 小时

**子任务**：
1. 更新特性描述：Excel → XML
2. 移除 `python3 ski_gui.py` 的 GUI 运行命令
3. 更新 CLI 命令示例为 XML 文件路径
4. 确认 Python 版本要求与 `pyproject.toml` 一致
5. 移除项目结构中不存在的目录引用（`ui/`、`tests/`）

**验收标准**：
- 所有命令和路径可执行
- 版本信息一致

---

### 任务 2.2：更新 ARCHITECTURE.md ⏳

**负责人**：待分配
**优先级**：中
**预计工时**：2 小时

**子任务**：
1. 移除不存在的文件和目录引用（`ui/main_window.py`、`utils/helpers.py`、`tests/`、`setup.py`）
2. 将 `setup.py` 引用更新为 `pyproject.toml`
3. 关键字清单中将 `open` 替换为 `navigate`
4. 更新数据流图：Excel 解析 → XML 解析（CaseParser、DataTableParser）
5. 移除 BaseDriver 抽象方法中的 `http_get`、`http_post`、`http_put`、`http_delete`
6. 更新执行流程图：`ExcelParser.parse()` → XML 解析流程
7. 在 `data/` 模块描述中添加 `model_manager.py`

**验收标准**：
- 所有文件和目录引用真实存在
- 关键字与核心设计约束一致
- 数据流图反映当前 XML 架构

---

## 阶段 3：其他用户指南更新

### 任务 3.1：更新 MOBILE_GUIDE.md ⏳

**负责人**：待分配
**优先级**：中
**预计工时**：1.5 小时

**子任务**：
1. 将 "支持的关键字" 章节中的 `click`、`swipe`、`tap`、`long_press`、`scroll` 改为数据表字段值描述
2. 使用 `type` 批量模式 + 数据表字段值描述移动端操作（如 `<field name="loginBtn">click</field>`）
3. 替换 Python 代码直接调用驱动的示例为 XML 格式用例示例

**验收标准**：
- 移动端操作描述与核心设计约束 §1.2 一致
- 所有示例使用 XML 格式

---

### 任务 3.2：更新 CI_CD_GUIDE.md ⏳

**负责人**：待分配
**优先级**：中
**预计工时**：1 小时

**子任务**：
1. 将所有 `.xlsx` 文件引用更新为 `.xml` 文件引用
2. 将 `python run_tests.py` 命令更新为 `python selftest.py`
3. 移除所有 `pytest`、`coverage`、`pytest-cov` 相关引用和配置
4. 将 Python 版本范围描述与 README.md 保持一致

**验收标准**：
- 所有命令可执行
- 与核心设计约束 §9 "不依赖外部测试框架" 一致

---

### 任务 3.3：更新 PARALLEL_EXECUTION.md ⏳

**负责人**：待分配
**优先级**：低
**预计工时**：0.5 小时

**子任务**：
1. 将步骤格式从 `{"keyword": "navigate", "params": {"url": "..."}}` 更新为 `{"action": "navigate", "model": "", "data": "..."}`
2. 移除 `click` 作为独立关键字的示例

**验收标准**：
- 步骤格式与 Case_XML test_step 同构
- 与核心设计约束 §1.2 一致

---

## 阶段 4：GUI 文档处理

### 任务 4.1：处理 GUI_USAGE.md ⏳

**负责人**：待分配
**优先级**：低
**预计工时**：0.5 小时

**子任务**：
1. 检查 `ski_gui.py` 是否存在于代码库
2. 如果不存在，在 `GUI_USAGE.md` 文件顶部添加 "已废弃" 标记
3. 从 QUICKSTART.md 移除对 `docs/GUI_USAGE.md` 的引用（已在任务 1.2 中）
4. 从 README.md 移除对 `ski_gui.py` 的引用（已在任务 2.1 中）

**验收标准**：
- 文档状态明确（废弃或可用）
- 无引用不存在的文件

---

## 阶段 5：代码清理

### 任务 5.1：标记遗留 Excel 代码 ⏳

**负责人**：待分配
**优先级**：中
**预计工时**：0.5 小时

**子任务**：
1. 在 `core/data_parser.py` 文件顶部添加废弃标记
2. 在 `data/excel_parser.py` 文件顶部添加废弃标记
3. 在 `keyword_engine.py` 的 `self.data_parser = DataParser(data_dir, self)` 行添加注释

**废弃标记模板**：
```python
# DEPRECATED: 遗留 Excel 解析代码，新代码应使用 data/data_resolver.py
# 保留此模块仅为向后兼容，XML 模式不使用此解析器
# 注意：此模块使用 ${Return[-1]} 格式，而当前标准格式为 Return[-1]（不带 ${}）
```

**验收标准**：
- 所有遗留代码有明确标记
- 新开发者不会混淆 XML 和 Excel 解析路径

---

### 任务 5.2：添加 ModelManager 说明 ⏳

**负责人**：待分配
**优先级**：低
**预计工时**：0.5 小时

**子任务**：
1. 在 `data/model_manager.py` 文件顶部添加说明注释
2. 明确该模块与 `core/model_parser.py`（XML 模型解析）的关系
3. 标注适用场景，避免与 XML 模型体系混淆

**验收标准**：
- 模块定位明确
- 与 XML 模型体系的关系清晰

---

### 任务 5.3：统一 Return 引用格式说明 ⏳

**负责人**：待分配
**优先级**：低
**预计工时**：0.5 小时

**子任务**：
1. 在 `core/data_parser.py` 检查说明其使用 `${Return[-1]}` 格式
2. 确认 TEST_CASE_WRITING_GUIDE.md 仅描述 `Return[-1]` 格式（需要带 `${}`）修改标准说明
3. 确认 `data/data_resolver.py` 实现与标准格式一致

**验收标准**：
- 标准格式明确：`${Return[-1]}`（带 `${}`）

---

## 任务统计

- **总任务数**：11
- **高优先级**：2（任务 1.1、1.2）
- **中优先级**：5（任务 2.1、2.2、3.1、3.2、5.1）
- **低优先级**：4（任务 3.3、4.1、5.2、5.3）
- **预计总工时**：13-15 小时

---

## 依赖关系

- 任务 1.2 依赖任务 4.1（移除 GUI_USAGE.md 引用）
- 任务 2.1 依赖任务 4.1（移除 ski_gui.py 引用）
- 任务 5.1 应在所有文档更新完成后执行

---

## 进度跟踪

| 阶段 | 任务数 | 已完成 | 进行中 | 待开始 | 完成率 |
|------|--------|--------|--------|--------|--------|
| 阶段 1 | 2 | 0 | 0 | 2 | 0% |
| 阶段 2 | 2 | 0 | 0 | 2 | 0% |
| 阶段 3 | 3 | 0 | 0 | 3 | 0% |
| 阶段 4 | 1 | 0 | 0 | 1 | 0% |
| 阶段 5 | 3 | 0 | 0 | 3 | 0% |
| **总计** | **11** | **0** | **0** | **11** | **0%** |
