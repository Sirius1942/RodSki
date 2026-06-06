# RodSki Skills

RodSki 对外发布的独立 Skill 集合，可被 Claude Code、Claude Agent SDK 或第三方 Agent 系统加载，用于辅助开发 RodSki 框架、生成/调试 RodSki 测试用例、迁移用例环境、提交测试资产和诊断疑难问题。

## 项目定位

| 项 | 说明 |
|----|------|
| 受众 | 使用或维护 RodSki 的 AI Agent / 业务测试团队 / 框架开发者 |
| 与 `.claude/skills/` 的区别 | `.claude/skills/` 是本仓库 Claude Code 会话的本地加载目录；`rodski-skills/` 是**可分发**、可归档、可打包的对外产物源 |
| 版本对齐 | `VERSION` 文件与 `rodski/__init__.py::__version__` 保持一致，由发布流程 `bump_all_versions()` 自动同步 |
| 分发形式 | 每次正式发布生成 `dist/rodski-skills-vX.Y.Z.zip`，可挂载到 GitHub Release / 内部仓库 / SkillHub Registry |
| Registry | 当前 SkillHub Registry 为 `https://skills.casstime.com`；当前已安装 namespace 为 `rodski-skill`，后续建议统一为 `rodski-skills` |

## 目录结构

```text
rodski-skills/
├── README.md
├── VERSION
├── rodski-test-guide/                    # 用例编写指南 Skill（由 TEST_CASE_WRITING_GUIDE.md 切片生成）
├── rodski-skill--rodski/                 # 框架源码 / 协议 / CLI / schema 总控 Skill
├── rodski-skill--rodski-case-writer/     # 用例编写、修改、审查、调试 Skill
├── rodski-skill--switch-rodski-env/      # RodSki 用例换环境 Skill
├── rodski-skill--submit-testcases-gitlab/# 测试资产提交 GitLab Skill
├── rodski-skill--diagnose/               # 疑难 bug / 性能回归诊断 Skill
└── scripts/                              # 维护脚本（不进入发行包）
    ├── sync_test_guide.sh
    └── package_release.sh
```

> `rodski-skill--*` 目录名来自当前 SkillHub / clawhub namespace slug；各 skill 的 `SKILL.md` frontmatter 中仍保留较短的 `name`，例如 `rodski-case-writer`。

## Skills 清单

| Skill | 来源 / 版本 | 说明 |
|-------|-------------|------|
| `rodski-test-guide` | **v7.1.1** (sha256: `e5547626850c`)；源文档 `rodski/docs/TEST_CASE_WRITING_GUIDE.md` | RodSki 用例 / 模型 / 数据 / 关键字编写权威指南，章节切片位于 `reference/*.md` |
| `rodski-skill--rodski` | SkillHub `20260605.034754` | RodSki 框架源码、XML 活文档协议、关键字实现、XSD schema、CLI、视觉/Desktop/API/DB 能力和 demo 验收链路 |
| `rodski-skill--rodski-case-writer` | SkillHub `20260605.034337` | 在任意 RodSki 用例仓库中编写、修改、调试或审查 `case/model/data/plan` 资产 |
| `rodski-skill--switch-rodski-env` | SkillHub `20260605.035123` | beta/ci/stage/prod 等环境迁移；补齐缺失用例资产；只替换 URL 和数据库地址 |
| `rodski-skill--submit-testcases-gitlab` | SkillHub `20260605.035047` | 将提交者自己的 RodSki 测试资产提交到共享 GitLab 仓库个人分支和 owner directory |
| `rodski-skill--diagnose` | SkillHub `20260605.034904` | 疑难 bug 和性能回归诊断循环：反馈循环 → 复现 → 假设 → 插桩 → 修复 → 回归 |

> `rodski-test-guide` 的源文档版本与 sha256 由 `sync_test_guide.sh` 在每次同步时自动更新到 `rodski-test-guide/source.sha256` 和本 README 表格。

## 路由建议

| 用户意图 | 优先使用 |
|----------|----------|
| 询问 RodSki 用例规则、关键字语义、model.xml/data.sqlite 写法 | `rodski-test-guide` |
| 编写、修改、审查、修复 RodSki 用例资产 | `rodski-skill--rodski-case-writer` |
| 调试 RodSki 用例运行结果、分析 result 目录 | `rodski-skill--rodski-case-writer` |
| 修改 RodSki 框架源码、关键字实现、XSD、CLI、驱动层或 demo 验收 | `rodski-skill--rodski` |
| 排查框架 bug、疑难失败、性能回归 | `rodski-skill--diagnose`，必要时结合 `rodski-skill--rodski` |
| 将旧环境用例迁移到新环境，只切 URL/DB 地址 | `rodski-skill--switch-rodski-env` |
| 提交测试资产到共享 GitLab | `rodski-skill--submit-testcases-gitlab` |
| 发布 RodSki 正式版本 | `.claude/skills/rodski-release`（后续建议纳入本目录和 registry） |

## 与发布流程的集成

`rodski-release` 在 **Stage 2.5** 自动检查测试指南是否更新：

```text
Stage 2    主干验收测试
   ↓
Stage 2.5  Skills 同步与打包
   ↓          ├ diff TEST_CASE_WRITING_GUIDE.md
Stage 3       ├ 有变更 → 重切 reference/，git commit
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

从 SkillHub 更新本地 Claude Code skills：

```bash
export CLAWHUB_REGISTRY=https://skills.casstime.com
npx clawhub --workdir /path/to/rodski --dir .claude/skills update
```

## 设计约定

1. `rodski-test-guide/reference/*.md` 与 `source.sha256` 由 sync 脚本生成，**不要手工编辑**。
2. 修改测试指南只改源文件 `rodski/docs/TEST_CASE_WRITING_GUIDE.md`，发布流程会自动同步。
3. 新增 Skill 时遵循同一约定：`rodski-skills/<name>/SKILL.md` + 按需 `reference/` / `scripts/` / 来源元数据。
4. `scripts/` 不进入对外发行 zip。
5. Registry 安装产生的 `.clawhub/origin.json` 可作为来源记录保留在归档目录；发行 zip 默认排除隐藏文件。

## 后续改进重点

详见 `rodski/docs/RODSKI_SKILLS_REGISTRY.md`。优先级最高的改进包括：

1. 统一 namespace：当前实际为 `@rodski-skill`，建议统一到 `@rodski-skills`。
2. 修正 bundled scripts 的执行路径，避免 `python3 scripts/xxx.py` 在项目根目录下找不到文件。
3. 同步 `rodski-test-guide` 到当前 RodSki 版本。
4. 将 `.claude/skills/rodski-release` 纳入 registry 和本目录归档。
5. 将 `$HOME/TestCase`、GitLab URL、默认环境目录等业务默认值配置化。
