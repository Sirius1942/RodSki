# 业务特定 Skills 归档

本目录存放包含硬编码业务路径、URL 或环境配置的 RodSki Skills。

这些 skills 不适合作为通用框架的一部分对外发布，建议迁移至内部仓库或单独的业务 skills 包。

## 归档的 Skills

### rodski-skill--submit-testcases-gitlab
- **原因**：包含硬编码的 GitLab URL (`https://gitlab.casstime.net/qa/RodSki-AutoTest`)、默认路径 (`$HOME/TestCase/00 Pass`)
- **用途**：将测试资产提交到共享 GitLab 仓库
- **建议**：迁移至内部测试工具仓库，配置化 URL 和路径

### rodski-skill--switch-rodski-env
- **原因**：包含硬编码的业务环境路径 (`$HOME/beta_old/000 case_old`, `$HOME/ci_new/000 case_new`)、业务特定的环境映射 (beta → ci)
- **用途**：在不同测试环境之间迁移 RodSki 用例
- **建议**：迁移至内部测试工具仓库，配置化环境路径

## 如何使用归档的 Skills

如果需要在内部使用这些 skills：

1. 将它们复制到 `.claude/skills/` 目录
2. 或者创建一个单独的内部 skills 仓库
3. 配置化硬编码的路径和 URL

## 版本记录

- **归档日期**: 2026-08-21
- **归档版本**: v10.0.0
- **原始位置**: `rodski-skills/`
