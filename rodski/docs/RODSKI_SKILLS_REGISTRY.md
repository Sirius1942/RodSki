# RodSki Skills Registry 说明与改进清单

> 生成日期：2026-06-05  
> 目的：记录从 SkillHub Registry 下载并归档到本项目的 RodSki skills，说明各 skill 的职责边界、当前挑战点和后续改进方向。

## 1. 背景

RodSki 项目同时维护两类 skill 目录：

| 目录 | 用途 | 是否作为发行资产 |
|------|------|------------------|
| `.claude/skills/` | 本仓库 Claude Code 会话本地加载的 skills，包括发布流程、本地调试和从 registry 安装的 skills | 否，偏本地运行环境 |
| `rodski-skills/` | RodSki 对外分发的 skill 集合，随 RodSki 版本同步、打包、发布 | 是 |

本次从 SkillHub Registry 下载的 RodSki namespace skills 已归档到 `rodski-skills/`，用于后续纳入 RodSki skills 发行包和版本管理。

SkillHub Registry：

```bash
CLAWHUB_REGISTRY=https://skills.casstime.com
```

本次实际可安装的 namespace 为 `rodski-skill`，对应 clawhub slug 形如：

```text
rodski-skill--rodski
rodski-skill--rodski-case-writer
```

注意：用户语义上常称为 `@rodski-skills`，但当前 registry 中 `rodski-skills--...` 返回 namespace not found。后续应统一 namespace 命名，见“改进清单”。

## 2. 已归档 Skills 清单

归档位置：`rodski-skills/`

| Registry slug / 本地目录 | SKILL.md name | 类型 | 核心用途 |
|--------------------------|---------------|------|----------|
| `rodski-skill--rodski` | `rodski` | 框架开发总控 | RodSki 框架源码、XML 协议、关键字实现、XSD、CLI、视觉/Desktop/API/DB 能力、demo 验收链路 |
| `rodski-skill--rodski-case-writer` | `rodski-case-writer` | 用例生产与调试 | 编写、修改、审查 RodSki `case/model/data/plan`，执行 guide 合规检查、dry-run、结果目录诊断 |
| `rodski-skill--switch-rodski-env` | `switch-rodski-env` | 换环境专项 | beta/ci/stage/prod 等环境迁移；补齐缺失用例资产；只替换 URL 和 DB 地址 |
| `rodski-skill--submit-testcases-gitlab` | `submit-testcases-gitlab` | 提交专项 | 将提交者自己的 RodSki 用例资产同步到共享 GitLab 仓库个人分支和 owner directory |
| `rodski-skill--diagnose` | `diagnose` | 诊断方法论 | 疑难 bug / 性能回归的纪律化诊断循环：反馈循环 → 复现 → 假设 → 插桩 → 修复 → 回归 |
| `rodski-test-guide` | `rodski-test-guide` | 参考指南 | 从 `rodski/docs/TEST_CASE_WRITING_GUIDE.md` 切片生成的用例编写权威指南 |

另外 `.claude/skills/rodski-release/` 当前仍为本地手工安装 skill，尚未纳入 registry 管理。它负责 RodSki 正式版本发布流程。

## 3. Skills 路由建议

当多个 skill 可能同时命中时，建议按下表选择：

| 用户意图 | 优先使用 |
|----------|----------|
| 询问 RodSki 用例规则、关键字语义、model.xml/data.sqlite 写法 | `rodski-test-guide` |
| 编写、修改、审查、修复 RodSki 用例资产 | `rodski-skill--rodski-case-writer` |
| 调试某个 RodSki 用例运行结果、分析 result 目录 | `rodski-skill--rodski-case-writer` |
| 修改 RodSki 框架源码、关键字实现、XSD、CLI、驱动层或 demo 验收 | `rodski-skill--rodski` |
| 排查框架 bug、疑难失败、性能回归 | `rodski-skill--diagnose`，必要时结合 `rodski-skill--rodski` |
| 将旧环境用例迁移到新环境，只切 URL/DB 地址 | `rodski-skill--switch-rodski-env` |
| 提交测试资产到共享 GitLab | `rodski-skill--submit-testcases-gitlab` |
| 发布 RodSki 正式版本 | `.claude/skills/rodski-release` |

## 4. 单个 Skill 解读

### 4.1 `rodski-skill--rodski`

定位：RodSki 框架级工作入口。

关键约束：

- RodSki 是确定性执行引擎，Agent 负责探索、规划和生成 XML。
- 框架契约以 `CORE_DESIGN_CONSTRAINTS.md`、`TEST_CASE_WRITING_GUIDE.md`、XSD 和当前 CLI help 为准。
- 每次执行或修改 RodSki 行为前先确认当前 CLI：`--version`、`--help`、相关子命令 `--help`。
- 只有当前 CLI help 暴露 `capabilities` 时才运行 `rodski capabilities`。
- 用例级工作应转给 `rodski-case-writer`。

适合场景：

- 新增或修改关键字行为。
- 修改 `rodski/schemas/*.xsd`。
- 修改 CLI 参数、输出格式、数据命令、plan 命令。
- 维护视觉定位、Desktop/Mobile/API/DB 驱动能力。
- 做 RodSki demo 验收链路。

### 4.2 `rodski-skill--rodski-case-writer`

定位：RodSki 用例资产生产、审查、调试的核心 skill。

强项：

- 明确三元结构：Case 编排动作，Model 定义元素/API/DB 字段，Data 放 `data.sqlite`，GlobalValue 独立。
- 内置常见幻觉防护：不写 `open`、不把 `click` 当独立 action、不创造 `http_get/http_post/assert_json` 等伪关键字。
- 建议使用 bundled guard/preflight 脚本完成静态检查、数据校验、dry-run。
- 对失败结果目录给出固定排查顺序：先查用例合规，再查 summary/result/log/screenshots/recordings/case/data/model/globalvalue。

附带工具：

```text
scripts/rodski_case_guard.py
scripts/rodski_preflight.py
scripts/rodski_module_inventory.py
scripts/rodski_result_diagnose.py
scripts/rodski_slow_steps.py
scripts/rodski_scenario_slice.py
scripts/rodski_checkpoint_plan.py
scripts/rodski_guide_slice.py
```

### 4.3 `rodski-test-guide`

定位：从 `TEST_CASE_WRITING_GUIDE.md` 生成的章节化参考 skill。

适合用于解释和查询规则，不直接承担编辑/校验工作。

结构：

```text
rodski-test-guide/
├── SKILL.md
├── reference/01_concepts.md
├── reference/02_directory.md
├── ...
└── reference/92_result_xml.md
```

维护原则：

- 不手工编辑 `reference/*.md`。
- 修改源文档 `rodski/docs/TEST_CASE_WRITING_GUIDE.md` 后，通过 `rodski-skills/scripts/sync_test_guide.sh` 同步。
- 发布流程 Stage 2.5 应检查并打包该 skill。

### 4.4 `rodski-skill--switch-rodski-env`

定位：RodSki 用例环境迁移专项。

硬规则：

- 旧环境目录永远只读。
- 新旧目录分离，只写 `--target-root` / `--new-root`。
- 默认先 dry-run 或 audit，再写入。
- 默认只同步 `case/`、`data/`、`model/`、`fun/`。
- 不复制 `plan/`、`result/`、报告、前端源码、依赖目录等。
- 只允许替换 URL 和数据库地址，不改业务数据、判定表、用例结构或定位策略。

核心脚本：

```text
scripts/switch_rodski_env.py
```

主要命令：

```bash
python3 scripts/switch_rodski_env.py convert ...       # 一站式 dry-run/write
python3 scripts/switch_rodski_env.py audit ...         # 审计 URL/DB 地址
python3 scripts/switch_rodski_env.py compare ...       # 对比旧/新环境
python3 scripts/switch_rodski_env.py sync-missing ...  # 补齐缺失 case/data/model/fun
python3 scripts/switch_rodski_env.py extract-map ...   # 生成 old→new 映射
python3 scripts/switch_rodski_env.py apply ...         # 应用映射
```

### 4.5 `rodski-skill--submit-testcases-gitlab`

定位：将 RodSki 测试资产提交到共享 GitLab 仓库。

安全设计：

- 禁止提交到 `main`、`master`、`head`。
- 只重建当前 submitter 的 owner directory。
- 检查 staged paths，防止提交范围越界。
- 不清理其他提交者目录。
- 不把密码或 token 写入 skill、脚本、仓库文件或最终答复。

核心脚本：

```text
scripts/submit_testcases_gitlab.py
scripts/store_gitlab_credential.py
```

典型流程：

```bash
python3 scripts/submit_testcases_gitlab.py --dry-run
python3 scripts/submit_testcases_gitlab.py --push
```

### 4.6 `rodski-skill--diagnose`

定位：通用疑难 bug / 性能回归诊断方法论。

阶段：

1. 建立快速、确定、可由 Agent 自行运行的反馈循环。
2. 复现用户描述的真实失败模式。
3. 提出 3–5 个可证伪假设。
4. 按假设做定向插桩，一次只改一个变量。
5. 修复并补回归测试。
6. 清理插桩和临时 harness，复盘预防方案。

适合用在 RodSki 框架 bug、关键字实现异常、性能回归、偶发失败等场景。若只是普通用例失败，优先使用 `rodski-case-writer` 的结果目录诊断流程。

## 5. 当前挑战点

### 5.1 Namespace 命名不一致

用户语义为 `@rodski-skills`，当前 registry 实际为 `@rodski-skill`。

影响：

- 安装命令容易写错。
- 本地目录名为 `rodski-skill--xxx`，与 frontmatter `name: xxx` 不一致。
- 未来 release/package 文档难以统一。

建议：统一到复数 namespace：

```text
@rodski-skills/rodski
@rodski-skills/rodski-case-writer
@rodski-skills/switch-rodski-env
@rodski-skills/submit-testcases-gitlab
@rodski-skills/diagnose
@rodski-skills/rodski-test-guide
@rodski-skills/rodski-release
```

若短期无法迁移，应在 README 和 registry 说明中明确 `@rodski-skill` 是当前实际 namespace。

### 5.2 脚本路径可能不可执行

多个 skill 文档中使用：

```bash
python3 scripts/<script>.py
```

但归档后脚本实际在：

```text
rodski-skills/<skill>/scripts/<script>.py
```

被安装到 Claude Code 后则位于：

```text
.claude/skills/<skill>/scripts/<script>.py
```

如果 Agent 在项目根目录直接运行 `python3 scripts/...`，会找不到脚本。

建议统一成以下模式之一：

```bash
SKILL_ROOT=".claude/skills/rodski-skill--rodski-case-writer"
python3 "$SKILL_ROOT/scripts/rodski_preflight.py" ...
```

或在 skill runtime 支持时使用环境变量：

```bash
python3 "$CLAUDE_SKILL_ROOT/scripts/rodski_preflight.py" ...
```

这是当前最高优先级的可执行性风险。

### 5.3 版本漂移

当前项目版本为 `7.2.0`，但 `rodski-test-guide` registry 包显示 `7.1.3`。`rodski-skills/README.md` 历史内容中也曾记录旧版本行。

风险：

- Agent 虽被要求以当前 CLI / 当前文档为准，但版本漂移仍会增加误判概率。
- 发布后的 skill 可能无法反映最新 mobile、recording、report、observability 等能力。

建议：RodSki 正式发布时同步执行：

```bash
bash rodski-skills/scripts/sync_test_guide.sh
bash rodski-skills/scripts/package_release.sh $(cat rodski-skills/VERSION)
```

并检查 registry latest 与项目版本是否一致。

### 5.4 Skill 路由重叠

`rodski`、`rodski-case-writer`、`rodski-test-guide`、`diagnose` 都可能被“RodSki 问题”触发。

建议在各自 frontmatter description 和 SKILL.md 顶部加入路由规则：

- 解释规则：`rodski-test-guide`
- 写/改/调试用例：`rodski-case-writer`
- 改框架源码/协议：`rodski`
- 疑难 bug / 性能回归：`diagnose`

### 5.5 业务路径和内部服务硬编码

当前 skills 中存在一些本地或内部约定：

- `$HOME/TestCase`
- `$HOME/beta_old/000 case_old`
- `$HOME/ci_new/000 case_new`
- `/opt/homebrew/bin/rodski`
- `https://gitlab.casstime.net/qa/RodSki-AutoTest`

这些对当前用户环境有效，但作为通用发布产物时应标记为“Casstime 内部默认值”，并允许通过参数或环境变量覆盖。

### 5.6 `rodski-release` 未纳入 registry

当前 `rodski-release` 是 `.claude/skills/` 下的手工安装 skill，不在 `clawhub list` 的受管理列表中。

建议后续发布到同一 namespace，并纳入 `rodski-skills/` 归档与打包。

## 6. 改进优先级

| 优先级 | 项目 | 说明 |
|--------|------|------|
| P0 | 统一 namespace | 解决 `@rodski-skills` vs `@rodski-skill` 混乱 |
| P0 | 修正脚本路径 | 所有 bundled scripts 必须能从 Claude Code 当前 cwd 稳定执行 |
| P1 | 同步 guide 到当前版本 | 确保 `rodski-test-guide` 与 RodSki `VERSION` / docs 一致 |
| P1 | 更新 `rodski-skills/README.md` 和打包脚本说明 | 当前 README 历史上只描述 `rodski-test-guide`，需覆盖全部 skills |
| P1 | 归档并发布 `rodski-release` | release skill 也进入 registry 管理 |
| P2 | 增加 skills 路由总览 | 可新增 meta/router 说明，降低多 skill 触发冲突 |
| P2 | 业务默认值配置化 | 将内部路径、GitLab URL、默认环境目录显式配置化 |

## 7. 维护建议

### 7.1 从 registry 更新本地 Claude Code skills

```bash
export CLAWHUB_REGISTRY=https://skills.casstime.com

npx clawhub --workdir /path/to/rodski --dir .claude/skills update
```

或逐个安装：

```bash
npx clawhub --workdir /path/to/rodski --dir .claude/skills install rodski-skill--rodski
npx clawhub --workdir /path/to/rodski --dir .claude/skills install rodski-skill--rodski-case-writer
npx clawhub --workdir /path/to/rodski --dir .claude/skills install rodski-skill--switch-rodski-env
npx clawhub --workdir /path/to/rodski --dir .claude/skills install rodski-skill--submit-testcases-gitlab
npx clawhub --workdir /path/to/rodski --dir .claude/skills install rodski-skill--diagnose
npx clawhub --workdir /path/to/rodski --dir .claude/skills install rodski-test-guide
```

### 7.2 归档到 `rodski-skills/`

原则：

- `rodski-skills/` 是发行源，不应只依赖 `.claude/skills/` 本地缓存。
- registry 安装目录中的 `.clawhub/origin.json` 可作为来源记录保留在归档中；打包脚本可按需要排除 hidden metadata。
- 不归档本地凭据、token、缓存或临时运行产物。

### 7.3 发布前检查

发布前建议检查：

```bash
# 查看归档 skill
find rodski-skills -maxdepth 2 -name SKILL.md -print

# 检查版本
cat rodski-skills/VERSION
python3 - <<'PY'
import rodski
print(rodski.__version__)
PY

# 同步测试指南
bash rodski-skills/scripts/sync_test_guide.sh

# 打包
bash rodski-skills/scripts/package_release.sh $(cat rodski-skills/VERSION)
```

## 8. 结论

当前 RodSki skills 已形成较完整的分层体系：

- `rodski` 管框架源码和协议。
- `rodski-case-writer` 管用例生产与失败诊断。
- `rodski-test-guide` 管规则查询。
- `switch-rodski-env` 管环境迁移。
- `submit-testcases-gitlab` 管测试资产提交。
- `diagnose` 管疑难 bug 和性能回归。
- `rodski-release` 管正式发布，但仍需纳入 registry。

下一步最值得优先解决的是 namespace 统一、脚本路径可执行性、版本同步和 release skill registry 化。
