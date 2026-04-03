# RodSki 测试用例可读性提升开发任务

**版本**: v1.0
**日期**: 2026-03-31

---

## 开发流程

1. **Phase 1**: CLI explain 命令增强
2. **Phase 1 完成后**: 大黄蜂审查
3. **Phase 2**: Case 解析器业务标签支持
4. **Phase 2 完成后**: 大黄蜂审查
5. **Phase 3**: Model 描述字段支持
6. **Phase 3 完成后**: 大黄蜂审查
7. **Phase 4**: HTML 报告生成

---

## Phase 1 - CLI explain 命令增强

### Task 1.1: 分析现有 explain 实现
- **文件**: `rodski_cli/explain.py`
- **内容**: 阅读现有代码，了解结构
- **工作量**: 15min

### Task 1.2: 设计输出格式
- **内容**: 设计 text/markdown/html 三种格式的输出结构
- **工作量**: 15min

### Task 1.3: 实现 text 格式输出
- **文件**: `rodski_cli/explain.py`
- **内容**: 
  - 解析用例基本信息（id, title）
  - 解析测试步骤
  - 生成格式化文本输出
- **工作量**: 30min

### Task 1.4: 实现 markdown 格式输出
- **文件**: `rodski_cli/explain.py`
- **内容**: 生成 Markdown 格式用例说明
- **工作量**: 30min

### Task 1.5: 添加 --format 参数
- **文件**: `rodski_cli/explain.py`
- **内容**: 
  - 添加 `--format` 参数（text/markdown/html）
  - 添加 `--output` 参数
- **工作量**: 15min

---

## Phase 2 - Case 解析器业务标签支持

### Task 2.1: 扩展 CaseParser
- **文件**: `core/case_parser.py`
- **内容**:
  - 添加 `purpose`, `priority`, `tags`, `component_type`, `expected_result` 属性
  - 解析 XML 中的新属性
- **工作量**: 30min

### Task 2.2: 更新 schemas/case.xsd
- **文件**: `schemas/case.xsd`
- **内容**: 添加新属性的类型定义
- **工作量**: 15min

### Task 2.3: 编写单元测试
- **文件**: `tests/unit/test_case_parser.py`
- **内容**: 测试新属性的解析
- **工作量**: 20min

---

## Phase 3 - Model 描述字段支持

### Task 3.1: 扩展 ModelParser
- **文件**: `core/model_parser.py`
- **内容**:
  - 添加 `description` 属性
  - 解析 XML 中的 description 字段
- **工作量**: 30min

### Task 3.2: 更新 schemas/model.xsd
- **文件**: `schemas/model.xsd`
- **内容**: 添加 description 字段定义
- **工作量**: 15min

### Task 3.3: 更新 explain 输出
- **文件**: `rodski_cli/explain.py`
- **内容**: 显示元素的 description
- **工作量**: 20min

---

## Phase 4 - HTML 报告生成

### Task 4.1: 创建 HTML 模板
- **文件**: `templates/report_template.html`
- **内容**:
  - 马里奥主题样式
  - 测试结果展示
  - 截图嵌入
- **工作量**: 45min

### Task 4.2: 实现报告生成器
- **文件**: `rodski_cli/report.py`
- **内容**:
  - 读取 result.xml
  - 渲染 HTML 模板
  - 支持截图嵌入
- **工作量**: 45min

### Task 4.3: 添加 CLI 命令
- **文件**: `rodski_cli/`
- **内容**:
  - `rodski report` 子命令
  - `--format html` 参数
  - `--embed-screenshots` 参数
- **工作量**: 20min

---

## 交付物检查清单

- [ ] `rodski_cli/explain.py` 增强完成
- [ ] `core/case_parser.py` 支持业务标签
- [ ] `core/model_parser.py` 支持 description
- [ ] `schemas/case.xsd` 更新
- [ ] `schemas/model.xsd` 更新
- [ ] `templates/report_template.html` 创建
- [ ] 单元测试覆盖新功能
- [ ] 文档更新（EXPLAIN.md）

---

## 后续：大黄蜂审查
每个 Phase 完成后都需要大黄蜂进行代码审查。
