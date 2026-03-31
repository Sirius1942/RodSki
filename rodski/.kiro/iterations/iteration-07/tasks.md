# Iteration 07: 文档体系重构 — 任务清单

## 阶段一: 目录结构重构

### T7-001: 创建文档目录结构
**文件**: `docs/` 目录重组

- 创建 `docs/getting-started/` 目录
- 创建 `docs/agent-integration/` 目录
- 创建 `docs/reference/` 目录
- 创建 `docs/best-practices/` 目录
- 移动 `QUICKSTART.md` → `getting-started/`
- 移动/合并 `agent-integration.md` 和 `skill-integration.md` → `agent-integration/`
**预计**: 2h | **Owner**: 待分配

### T7-002: 重构文档首页
**文件**: `docs/README.md` (新)

- 设计文档导航首页
- 按用户任务组织链接（快速开始/编写用例/集成/参考/最佳实践）
- 每个章节配 1-2 句话说明
- 底部包含贡献指南链接
**预计**: 2h | **Owner**: 待分配

### T7-003: Getting Started 文档完善
**文件**: `docs/getting-started/`

- `INSTALL.md` - 从源码/pip/Docker 安装
- `QUICKSTART.md` - 5 分钟快速入门（已有，移入目录）
- `FIRST_TEST.md` - 编写第一个测试用例（从 `TEST_CASE_WRITING_GUIDE.md` 精简）
**预计**: 4h | **Owner**: 待分配

---

## 阶段二: Agent 集成文档

### T7-004: 重构 Agent 集成指南
**文件**: `docs/agent-integration/AGENT_INTEGRATION.md` (重构)

- 重新组织结构：工具调用 / 编程接口 / 多 Agent 协作
- 增加完整交互协议说明
- 增加错误处理和重试策略
- 增加实际集成案例（Claude Code / OpenCode）
**预计**: 6h | **Owner**: 待分配

### T7-005: OpenClaw Skill 集成文档
**文件**: `docs/agent-integration/OPENCLAW_SKILL.md` (新)

- Skill 定义文件格式说明
- 命令注册和参数映射
- 与 OpenClaw Gateway 的集成方式
- 示例 Skill 配置
**预计**: 4h | **Owner**: 待分配

### T7-006: Agent 集成示例代码
**文件**: `examples/agent/` 目录 (新)

- `claude_code_integration.py` - Claude Code 集成完整示例
- `opencode_integration.py` - OpenCode 集成完整示例
- `multi_agent_example.py` - 多 Agent 协作示例
- 每个文件附带 README 说明
**预计**: 6h | **Owner**: 待分配

---

## 阶段三: 参考文档

### T7-007: 关键字参考文档
**文件**: `docs/reference/KEYWORD_REFERENCE.md` (新)

- 17 个关键字的完整参考
- 每个关键字: 描述 / 参数表 / XML 示例 / 错误处理 / 可组合关键字
- 使用 `scripts/generate_docs.py` 从代码注释自动生成初稿
- 人工审核和补充
**预计**: 8h | **Owner**: 待分配

### T7-008: 配置项参考文档
**文件**: `docs/reference/CONFIG_REFERENCE.md` (新)

- 从 `config/default_config.yaml` 自动生成配置项表格
- 按模块分组（execution / recovery / result / vision / metadata / statistics）
- 每个配置项: 名称 / 类型 / 默认值 / 说明 / 示例
- 配置优先级说明
**预计**: 4h | **Owner**: 待分配

### T7-009: CLI 命令参考文档
**文件**: `docs/reference/CLI_REFERENCE.md` (新)

- 从 `core/cli.py` 的 Click 装饰器自动生成
- 每个子命令: 用法 / 参数 / 选项 / 示例 / 退出码
- `rodski run / explain / validate / stats / replay / compare`
**预计**: 4h | **Owner**: 待分配

---

## 阶段四: 最佳实践文档

### T7-010: 重构错误处理最佳实践
**文件**: `docs/best-practices/ERROR_HANDLING.md` (重构)

- 扩展现有 `EXCEPTION_HANDLING.md`
- 增加分层错误处理策略（步骤级 / 用例级 / 套件级）
- 增加错误场景与解决方案对照表
- 增加 RecoveryEngine 配置最佳实践
- 增加 AI 诊断集成最佳实践
**预计**: 6h | **Owner**: 待分配

### T7-011: 性能优化指南
**文件**: `docs/best-practices/PERFORMANCE.md` (新)

- 浏览器复用策略（共享 vs 独立模式）
- 元素定位优化建议
- 等待策略最佳实践
- 并行执行配置
- 内存管理（快照频率、GC 配置）
**预计**: 4h | **Owner**: 待分配

---

## 阶段五: 工具与验证

### T7-012: MkDocs 站点配置
**文件**: `mkdocs.yml` (新)

- 配置 MkDocs Material 主题
- 配置导航结构（与文档目录对应）
- 配置 Markdown 扩展（highlight / admonition / toc）
- 配置代码高亮（Python / XML / YAML / Bash）
**预计**: 2h | **Owner**: 待分配

### T7-013: 文档生成脚本
**文件**: `scripts/generate_docs.py` (新)

- `generate_keyword_reference()` - 从 keyword_engine.py 生成关键字参考初稿
- `generate_config_reference()` - 从 default_config.yaml 生成配置参考初稿
- `generate_cli_reference()` - 从 cli.py 生成 CLI 参考初稿
- 脚本可独立运行，定期更新参考文档
**预计**: 4h | **Owner**: 待分配

### T7-014: 链接验证
**文件**: `scripts/validate_docs.py` (新)

- 验证所有 Markdown 文件内的相对链接
- 检查外部 URL 可访问性
- 检查图片引用路径
- 作为 CI 检查项
**预计**: 2h | **Owner**: 待分配

### T7-015: 示例代码验证
**文件**: `examples/` 目录

- 确保所有示例代码无语法错误
- 运行 `python -m py_compile` 检查
- 关键示例（如集成）标记为 CI 集成测试
**预计**: 2h | **Owner**: 待分配

---

## 阶段六: 审查与发布

### T7-016: 文档整体审查
**文件**: 全部文档

- 通读所有新增/修改的文档
- 检查语言准确性（英文语法、中文错别字）
- 检查代码示例可运行性
- 检查交叉引用链接
- 确保文档风格一致
**预计**: 4h | **Owner**: 待分配

### T7-017: 更新根目录文档索引
**文件**: `docs/README.md` (已有)

- 确认所有新文档已在首页正确链接
- 检查导航结构完整性
- 确认贡献指南链接有效
**预计**: 1h | **Owner**: 待分配

---

## 任务汇总

| 任务 | 名称 | 预计 | 阶段 |
|------|------|------|------|
| T7-001 | 创建文档目录结构 | 2h | 1 |
| T7-002 | 重构文档首页 | 2h | 1 |
| T7-003 | Getting Started 文档完善 | 4h | 1 |
| T7-004 | 重构 Agent 集成指南 | 6h | 2 |
| T7-005 | OpenClaw Skill 集成文档 | 4h | 2 |
| T7-006 | Agent 集成示例代码 | 6h | 2 |
| T7-007 | 关键字参考文档 | 8h | 3 |
| T7-008 | 配置项参考文档 | 4h | 3 |
| T7-009 | CLI 命令参考文档 | 4h | 3 |
| T7-010 | 重构错误处理最佳实践 | 6h | 4 |
| T7-011 | 性能优化指南 | 4h | 4 |
| T7-012 | MkDocs 站点配置 | 2h | 5 |
| T7-013 | 文档生成脚本 | 4h | 5 |
| T7-014 | 链接验证脚本 | 2h | 5 |
| T7-015 | 示例代码验证 | 2h | 5 |
| T7-016 | 文档整体审查 | 4h | 6 |
| T7-017 | 更新根目录文档索引 | 1h | 6 |

**总预计**: 65h
