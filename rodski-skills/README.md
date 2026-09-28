# RodSki Skills

RodSki 对外发布的独立 Skill 集合，可被 Claude Code、Claude Agent SDK 或第三方 Agent 系统加载，用于辅助开发 RodSki 框架、生成/调试 RodSki 测试用例、迁移用例环境、提交测试资产和诊断疑难问题。

## 项目定位

| 项 | 说明 |
|----|------|
| 受众 | 使用或维护 RodSki 的 AI Agent / 业务测试团队 / 框架开发者 |
| 与 `.claude/skills/` 的区别 | `.claude/skills/` 是本仓库 Claude Code 会话的本地加载目录；`rodski-skills/` 是**可分发**、可归档、可打包的对外产物源 |
| 版本对齐 | `VERSION` 文件与 `rodski/__init__.py::__version__` 保持一致，由发布流程 `bump_all_versions()` 自动同步 |
| 分发形式 | 每次正式发布生成 `dist/rodski-skills-vX.Y.Z.zip`，可挂载到 GitHub Release / 内部仓库 |

## 目录结构

```text
rodski-skills/
├── README.md
├── VERSION
├── rodski-test-guide/                    # 用例编写指南 Skill（由 TEST_CASE_WRITING_GUIDE.md 切片生成）
├── rodski-skill--rodski/                 # 框架源码 / 协议 / CLI / schema 总控 Skill
├── rodski-skill--rodski-case-writer/     # 用例编写、修改、审查、调试 Skill
├── rodski-skill--diagnose/               # 疑难 bug / 性能回归诊断 Skill
├── rodski-skill--explore/                # 探索式测试 Skill
├── rodski-skill--pause-takeover/         # 「暂停 → Agent 接管页面 → 继续」交接 Skill (RodSki v11.1.0+)
└── scripts/                              # 维护脚本（不进入发行包）
    ├── sync_test_guide.sh
    └── package_release.sh
```

> `rodski-skill--*` 为目录名；各 skill 的 `SKILL.md` frontmatter 中使用较短的 `name`，例如 `rodski-case-writer`。

## Skills 清单

| Skill | 来源 / 版本 | 说明 |
|-------|-------------|------|
| `rodski-test-guide` | **v11.4.0** (sha256: `a9eedd1b1f48`)；源文档 `rodski/docs/TEST_CASE_WRITING_GUIDE.md` | RodSki 用例 / 模型 / 数据 / 关键字编写权威指南，章节切片位于 `reference/*.md` |
| `rodski-skill--rodski` | 随主仓库版本 | RodSki 框架源码、XML 活文档协议、关键字实现、XSD schema、CLI、视觉/Desktop/API/DB 能力和 demo 验收链路 |
| `rodski-skill--rodski-case-writer` | 随主仓库版本 | 在任意 RodSki 用例仓库中编写、修改、调试或审查 `case/model/business/data/plan` 资产（含业务模型 `business_call`） |
| `rodski-skill--explore` | 随主仓库版本 | 基于已通过用例基线的 AI 探索式测试 |
| `rodski-skill--diagnose` | 随主仓库版本 | 疑难 bug 和性能回归诊断循环：反馈循环 → 复现 → 假设 → 插桩 → 修复 → 回归 |
| `rodski-skill--pause-takeover` | **RodSki ≥ v11.1.0**（需 CLI `--cdp` + driver CDP attach） | 用例「暂停 → Agent 接管页面 → 继续」工作流：固定用例跑到目标页后由外部 Agent 用 playwright 判断页面并操作 1-2 个按钮，RodSki 再在同一 CDP 共享浏览器会话继续 verify；框架无关，任何能加载 Markdown skill 的 Agent 可自行编导 |

> `rodski-test-guide` 的源文档版本与 sha256 由 `sync_test_guide.sh` 在每次同步时自动更新到 `rodski-test-guide/source.sha256` 和本 README 表格。

## 路由建议

| 用户意图 | 优先使用 |
|----------|----------|
| 询问 RodSki 用例规则、关键字语义、model.xml/data.sqlite 写法 | `rodski-test-guide` |
| 编写、修改、审查、修复 RodSki 用例资产 | `rodski-skill--rodski-case-writer` |
| 用场景法建业务模型（`business/*.xml`、`business_call`、基本流/备选流/异常流） | `rodski-skill--rodski-case-writer`（`references/business-model.md`）；语法细节查 `rodski-test-guide` 第 17 章 |
| 调试 RodSki 用例运行结果、分析 result 目录 | `rodski-skill--rodski-case-writer` |
| 修改 RodSki 框架源码、关键字实现、XSD、CLI、驱动层或 demo 验收 | `rodski-skill--rodski` |
| 排查框架 bug、疑难失败、性能回归 | `rodski-skill--diagnose`，必要时结合 `rodski-skill--rodski` |
| 让固定用例跑到目标页后暂停、由外部 AI Agent 接管页面操作、再继续验证 | `rodski-skill--pause-takeover`（CDP 共享浏览器、双 run 交接；Agent 自编导） |
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

## 设计约定

1. `rodski-test-guide/reference/*.md` 与 `source.sha256` 由 sync 脚本生成，**不要手工编辑**。
2. 修改测试指南只改源文件 `rodski/docs/TEST_CASE_WRITING_GUIDE.md`，发布流程会自动同步。
3. 新增 Skill 时遵循同一约定：`rodski-skills/<name>/SKILL.md` + 按需 `reference/` / `scripts/`。
4. `scripts/` 不进入对外发行 zip。
5. 不提交任何第三方安装工具生成的元数据目录（如 `.clawhub/`）或自引用 symlink；发行 zip 默认排除隐藏文件。

## 后续改进重点

详见 `rodski/docs/RODSKI_SKILLS_REGISTRY.md`。优先级最高的改进包括：

1. 修正 bundled scripts 的执行路径，避免 `python3 scripts/xxx.py` 在项目根目录下找不到文件。
2. 同步 `rodski-test-guide` 到当前 RodSki 版本。
3. 将 `.claude/skills/rodski-release` 纳入本目录归档。
4. 业务相关 skill（换环境、提交 GitLab）已归档到 `.archived-business-specific/`；保留在本目录的 skill 不得写死业务系统、仓库路径、账号或内部 URL。
