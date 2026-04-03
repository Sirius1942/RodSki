---
name: if_else_implementation
description: if/else 流程控制功能实现完成记录
type: project
---

# if/else 流程控制实现完成

**完成日期**: 2026-04-03
**版本**: RodSki v3.4

## 实现内容

### 1. 核心代码修改（5 处）

| 文件 | 修改内容 |
|------|---------|
| `rodski/schemas/case.xsd` | 新增 `IfContainerType` + `ElseType`；`PhaseType`/`TestCasePhaseType` 改用 `xs:choice` 支持 `<if>` 容器 |
| `rodski/core/case_parser.py` | `_parse_if_element` 支持解析 `else` 分支；返回 `steps` + `else_steps` |
| `rodski/core/ski_executor.py` | `_run_steps` if 块传入 `driver`、添加 try/except 友好错误处理（截图+日志）、执行 else 分支 |
| `rodski/core/dynamic_executor.py` | `evaluate_condition` 支持 AND/OR/NOT、`verify_fail`、`${Return[N].field contains/==}`、`element_exists/not_exists`、`text_contains/not_contains` |
| `rodski/core/ski_executor.py` | `DynamicExecutor` 实例化时传入 `keyword_engine._return_values` 共享列表 |

### 2. 文档更新

| 文档 | 内容 |
|------|------|
| `phoenixbear/design/CORE_DESIGN_CONSTRAINTS.md` | 新增 §12 if/else 流程控制设计约束 |
| `rodski/docs/user-guides/TEST_CASE_WRITING_GUIDE.md` | 新增 §13 if/else 流程控制用户手册 |
| `rodski/docs/user-guides/TEST_CASE_WRITING_GUIDE/` | 拆分为 17 个独立章节文件 + README + docsify 文档站 |

### 3. 文档站构建

**位置**: `rodski/docs/user-guides/TEST_CASE_WRITING_GUIDE/`

**技术栈**:
- docsify（Vue 主题，纯 CDN）
- Python HTTP Server（后台运行）
- 无需 npm install

**访问**: http://localhost:5003/

**特性**:
- 左侧导航栏（章节分组，13-if/else 标 🆕）
- 全文搜索
- 代码高亮（XML/Python/YAML/JSON/SQL）
- 蓝色主题
- 上一章/下一章翻页

## 支持的条件类型

| 条件类型 | 语法示例 | 说明 |
|---------|---------|------|
| verify_fail | `condition="verify_fail"` | 上一步 verify 失败 |
| Return 字段判断 | `condition="${Return[-1].status == 200}"` | API 返回值比较 |
| Return 包含判断 | `condition="${Return[-1].msg contains '追加'}"` | 字段包含文字 |
| 元素可见 | `condition="element_exists(#dialog)"` | 页面元素出现 |
| 元素不可见 | `condition="element_not_exists(.error)"` | 页面元素不存在 |
| 页面含文字 | `condition="text_contains('成功')"` | 页面包含文字 |
| 页面不含文字 | `condition="text_not_contains('失败')"` | 页面不包含文字 |
| 变量比较 | `condition="retry_count > 0"` | 变量值比较 |
| 逻辑组合 | `condition="verify_fail AND element_exists(#dialog)"` | AND/OR/NOT |

## 约束

- 最大嵌套层数: 2
- condition 最大长度: 200 字符
- else 分支: 可选
- 支持的阶段: pre_process / test_case / post_process

## 错误处理

条件评估失败时：
1. 自动截图保存到 `results/<run>/screenshots/`
2. 记录详细错误日志（含条件内容、错误原因）
3. 跳过该 if/else 块，继续执行后续步骤

## 验证方式

1. 单元测试：构造包含 if/else 的 XML，解析并执行
2. dry-run 验证 XML 解析正确
3. 手动执行 rodski-web 的登录用例，观察截图输出

## 相关文件

- 设计文档: `phoenixbear/design/CORE_DESIGN_CONSTRAINTS.md` §12
- 用户手册: `rodski/docs/user-guides/TEST_CASE_WRITING_GUIDE.md` §13
- 文档站: `rodski/docs/user-guides/TEST_CASE_WRITING_GUIDE/index.html`
