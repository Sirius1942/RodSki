# RodSki Skills v10.0.0 更新摘要

**更新日期**: 2026-08-21  
**更新版本**: v9.2.3 → v10.0.0  
**更新人**: Claude Code

---

## 更新内容

### 1. 版本号更新 ✅

- `VERSION`: `9.2.3` → `10.0.0`
- 与主仓库版本保持同步

### 2. 核心 Skills 更新 ✅

#### rodski-skill--explore (v10.0.0)
- **架构简化**: 废弃 `rodski-agent/explore` 中间层
- **新架构**: Claude Code + Skill → `rodski explore-step` CLI
- **决策层上移**: 由 AI Agent 直接调用 CLI，无需独立的 LLM 决策循环
- **框架无关设计**: 支持任何能加载 Markdown skill 的 Agent（Claude Code、Codex、AutoGPT 等）
- **核心能力**:
  - 基于已通过用例建立基线
  - 探索合理业务边界线下的异常问题
  - 数据唯一性处理（避免重复主键误判）
  - 预算控制和去重机制
  - 5 个阶段执行纪律

### 3. 业务特定 Skills 归档 ✅

以下 skills 已移至 `.archived-business-specific/` 目录，**不再纳入通用发布包**：

#### rodski-skill--submit-testcases-gitlab
- **归档原因**: 包含硬编码的 GitLab URL (`https://gitlab.casstime.net/qa/RodSki-AutoTest`)
- **建议**: 迁移至内部测试工具仓库

#### rodski-skill--switch-rodski-env
- **归档原因**: 包含硬编码的业务环境路径 (`$HOME/beta_old/`, `$HOME/ci_new/`)
- **建议**: 迁移至内部测试工具仓库

### 4. 文档更新 ✅

#### README.md 更新
- 更新版本号为 v10.0.0
- 更新目录结构说明（移除归档的 skills）
- 更新 Skills 清单（`rodski-skill--explore` 版本标注为 v10.0.0）
- 更新路由建议（移除业务特定 skills 的路由）
- 更新改进重点（强调业务特定 skills 独立维护）

#### 新增文档
- `.archived-business-specific/README.md`: 归档说明文档

---

## 当前 Skills 清单（v10.0.0）

| Skill | 版本 | 类型 | 状态 |
|-------|------|------|------|
| `rodski-test-guide` | v7.1.1 | 通用 | ✅ 活跃 |
| `rodski-skill--rodski` | SkillHub 20260605 | 通用 | ✅ 活跃 |
| `rodski-skill--rodski-case-writer` | SkillHub 20260605 | 通用 | ✅ 活跃 |
| `rodski-skill--explore` | v10.0.0 | 通用 | ✅ 活跃（已更新）|
| `rodski-skill--diagnose` | SkillHub 20260605 | 通用 | ✅ 活跃 |
| `rodski-skill--submit-testcases-gitlab` | SkillHub 20260605 | 业务特定 | 📦 已归档 |
| `rodski-skill--switch-rodski-env` | SkillHub 20260605 | 业务特定 | 📦 已归档 |

---

## 目录结构变化

### 变化前
```
rodski-skills/
├── rodski-skill--explore/                # v9.2.3
├── rodski-skill--submit-testcases-gitlab/
├── rodski-skill--switch-rodski-env/
└── ...
```

### 变化后
```
rodski-skills/
├── rodski-skill--explore/                # v10.0.0 ✨
├── .archived-business-specific/          # 新增 📦
│   ├── README.md
│   ├── rodski-skill--submit-testcases-gitlab/
│   └── rodski-skill--switch-rodski-env/
└── ...
```

---

## v10.0.0 核心变化（探索测试架构）

### Before (v9.x)
```
Claude Code → rodski-agent/explore → rodski 核心 (ExploreExecutor)
              ↑ 独立的 LLM 决策循环
```

**问题**:
- `llm_strategy.py` 的 LLM 客户端恒为 None，实际走硬编码规则
- asyncio 冲突（需要 ThreadPoolExecutor workaround）
- 调用链过长
- 维护负担重

### After (v10.0.0)
```
Claude Code + Skill → rodski explore-step CLI → rodski 核心 (ExploreExecutor)
↑ AI Agent 直接决策
```

**改进**:
- ✅ 架构简化：去除中间层
- ✅ 决策层上移：AI Agent 直接调用 CLI
- ✅ 框架无关：支持任何 Markdown skill Agent
- ✅ 无 asyncio 冲突：CLI 是同步调用
- ✅ 维护成本降低：只维护 skill 文档 + CLI

---

## 验证清单

- [x] `VERSION` 文件更新为 `10.0.0`
- [x] `README.md` 版本信息更新
- [x] `rodski-skill--explore` 已是 v10.0.0 版本（无需更新内容）
- [x] 业务特定 skills 移至 `.archived-business-specific/`
- [x] `.archived-business-specific/README.md` 创建完成
- [x] `README.md` 目录结构、Skills 清单、路由建议已更新
- [x] 目录结构验证通过

---

## 后续建议

### 立即行动
1. ✅ **已完成**: 版本号同步、业务 skills 归档、文档更新

### 中期改进（v10.x）
1. **同步 `rodski-test-guide`**: 从 v7.1.1 更新至 v10.0.0（运行 `scripts/sync_test_guide.sh`）
2. **统一 namespace**: `@rodski-skill` → `@rodski-skills`
3. **纳入 `rodski-release` skill**: 将 `.claude/skills/rodski-release` 加入 `rodski-skills/` 和 registry

### 长期优化（v11.x）
1. **移除 `rodski-agent/explore` 代码**: v10 已标记为废弃，v11 可完全移除
2. **业务 skills 独立仓库**: 为内部团队创建 `rodski-skills-internal` 仓库

---

## 发布清单

### 打包前检查
- [x] `VERSION` 文件正确
- [x] `README.md` 版本信息正确
- [x] 业务特定内容已移除或归档
- [x] 目录结构符合预期

### 发布命令（待执行）
```bash
# 1. 确认当前版本
cat rodski-skills/VERSION  # 应显示 10.0.0

# 2. 打包发布（如果有打包脚本）
cd rodski-skills/scripts
bash package_release.sh

# 3. 验证发布包（不应包含 .archived-business-specific/）
unzip -l dist/rodski-skills-v10.0.0.zip | grep -E "(submit|switch)"
# 应该没有输出

# 4. 上传到 GitHub Release / SkillHub Registry
```

---

## 相关文档

- 主仓库 CHANGELOG: `/Users/sirius.chen/Projects/rodski/CHANGELOG.md`
- v10 PRD: `.pb/requirements/v10-explore-testing-prd.md`
- Skill 主文档: `rodski-skill--explore/SKILL.md`
- 参考文档: `rodski-skill--explore/references/*.md`

---

**更新完成** ✅

所有 v10.0.0 相关的 skills 更新已完成，业务特定内容已归档，文档已同步。
