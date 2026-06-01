# RodSki Skills

RodSki 对外发布的独立 Skill 集合，可被 Claude Code、Claude Agent SDK 或第三方 Agent 系统加载，用于辅助生成 RodSki 测试用例、模型与数据。

## 项目定位

| 项 | 说明 |
|----|------|
| 受众 | 使用 RodSki 编写测试用例的 AI Agent / 业务团队 |
| 与 `.claude/skills/` 的区别 | `.claude/skills/` 仅供本仓库 Claude Code 使用（如 `rodski-release`）；`rodski-skills/` 是**可分发**的对外产物 |
| 版本对齐 | `VERSION` 文件与 `rodski/__init__.py::__version__` 保持一致，由发布流程 `bump_all_versions()` 自动同步 |
| 分发形式 | 每次正式发布生成 `dist/rodski-skills-vX.Y.Z.zip`，可挂载到 GitHub Release / 内部仓库 |

## 目录结构

```
skills/
├── README.md                       # 本文件
├── VERSION                         # 与 RodSki 主版本同步
├── rodski-test-guide/              # 用例编写指南 Skill
│   ├── SKILL.md                    # Skill 入口（触发条件 + 章节索引）
│   ├── reference/                  # 按章节拆分的参考材料（由 sync 脚本生成）
│   └── source.sha256               # 源文档指纹，用于变更检测
└── scripts/                        # 维护脚本（不进入发行包）
    ├── sync_test_guide.sh          # 从源 md 切片生成 reference/
    └── package_release.sh          # 打 dist/rodski-skills-vX.Y.Z.zip
```

## Skills 清单

| Skill | 源文档版本 | 源文档路径 | 说明 |
|-------|-----------|-----------|------|
| `rodski-test-guide` | **v7.1.1** (sha256: `e5547626850c`) | `rodski/docs/TEST_CASE_WRITING_GUIDE.md` | 用例 / 模型 / 数据 / 关键字编写规范 |

> 源文档版本与 sha256 由 `sync_test_guide.sh` 在每次同步时自动更新到 `rodski-test-guide/source.sha256`。
> 上表中的版本号取自源文档 `**版本**: vX.Y.Z` 行，sha256 取前 12 位。

## 与发布流程的集成

`rodski-release` 在 **Stage 2.5** 自动检查测试指南是否更新：

```
Stage 2  主干验收测试
   ↓
Stage 2.5  Skills 同步与打包    ← 本项目的接入点
   ↓                                ├ diff TEST_CASE_WRITING_GUIDE.md
Stage 3  打包 + 打 tag             ├ 有变更 → 重切 reference/，git commit
                                    └ 打 dist/rodski-skills-vX.Y.Z.zip
```

详见 `.claude/skills/rodski-release/SKILL.md`。

## 手动维护命令

```bash
# 检查并同步测试指南（幂等）
bash rodski-skills/scripts/sync_test_guide.sh

# 退出码: 0=无变更 / 10=有更新 / 1=出错

# 打当前版本的发行包
bash rodski-skills/scripts/package_release.sh $(cat rodski-skills/VERSION)
```

## 设计约定

1. `reference/*.md` 与 `source.sha256` 由 sync 脚本生成，**不要手工编辑**
2. 修改测试指南只改源文件 `rodski/docs/TEST_CASE_WRITING_GUIDE.md`，发布流程会自动同步
3. 新增 Skill 时遵循同一约定：`rodski-skills/<name>/SKILL.md` + `reference/` + `source.sha256`
4. `scripts/` 不进入对外发行 zip
