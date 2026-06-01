---
name: rodski-release
description: >
  RodSki 正式版本发布 skill。
  当用户说"发布 vX.Y.Z"、"release X.Y.Z"、"打包发布"时触发。
  按 5 个阶段编排发布流程，每个阶段对应一个独立脚本，
  失败时提供明确的回滚指引，不会留下"假成功"的 git tag。
type: release
---

# RodSki 发布 Skill

## 触发时机

用户说以下任意一种时触发本 skill：

- "发布 v7.x.x"
- "release 7.x.x"
- "打包发布新版本"
- "跑发布流程"

## 前置条件

| 条件 | 说明 |
|------|------|
| 当前在 `main` 分支 | 发布只从主干进行 |
| `~/.pypirc` 已配置 | twine 上传 PyPI 需要 |
| `rodski` CLI 可用 | 验收测试需要 |
| `python3 -m build` 可用 | 需要 `pip install build` |

## 5 阶段流程

```
Stage 1  合并功能分支到 main
   ↓
Stage 2  主干验收测试（unit tests + demo_full UI 用例）
   ↓
Stage 2.5  Skills 同步与打包（diff 测试指南 → 切片 → dist/rodski-skills-vX.Y.Z.zip）
   ↓
Stage 3  同步版本号 + 打包 + 打 tag（tag 暂不 push）
   ↓
Stage 4  干净 venv 验收 wheel（模拟用户安装体验）
   ↓
Stage 5  上传 PyPI + push git + 核验（确认真实成功）
```

**关键设计原则**：
- tag 在 PyPI 上传**成功之后**才 push 远端，避免"假成功"
- 每个阶段写入 `.release_state` 状态文件，防止跳步
- 失败时有明确的回滚指引

---

## Agent 调用方式

### 完整发布（推荐）

```bash
VERSION=7.2.0

# Stage 1: 合并功能分支
.claude/skills/rodski-release/scripts/stage1_merge_to_main.sh $VERSION

# Stage 2: 主干验收
.claude/skills/rodski-release/scripts/stage2_acceptance.sh $VERSION

# Stage 2.5: Skills 同步与打包
.claude/skills/rodski-release/scripts/stage2_5_sync_skills.sh $VERSION

# Stage 3: 打包 + 打 tag
.claude/skills/rodski-release/scripts/stage3_build_and_tag.sh $VERSION

# Stage 4: 干净环境验收
.claude/skills/rodski-release/scripts/stage4_clean_verify.sh $VERSION

# Stage 5: 上传 + 核验
.claude/skills/rodski-release/scripts/stage5_publish_and_verify.sh $VERSION
```

### 单独跑某个阶段

每个脚本都可以单独调用，但会检查前置阶段是否完成（通过 `.release_state` 文件）。

### 紧急回滚

```bash
# 撤销 tag 和版本号 commit（stage3 之后、stage5 之前失败时用）
.claude/skills/rodski-release/scripts/rollback_tag.sh $VERSION
```

---

## 各阶段详细说明

### Stage 1 — 合并功能分支到 main

**脚本**: `stage1_merge_to_main.sh <VERSION>`

执行内容：
1. 确认当前在 `main` 分支
2. `git fetch` + `fast-forward` 同步远端
3. 检查 PyPI 上该版本是否已存在（防止重复发布）
4. 自动合并所有 `feature/v<VERSION>*` 分支
5. 检查工作区干净

失败处理：
- 合并冲突 → 手动解决后重跑 stage1
- PyPI 已有该版本 → 换版本号

---

### Stage 2 — 主干验收测试

**脚本**: `stage2_acceptance.sh <VERSION>`

执行内容：
1. `pytest tests/unit/` 全量单元测试
2. `rodski run` 跑 demo_full 所有 UI 用例（10 个文件）

失败处理：
- 修复代码后重跑 stage2（不需要重跑 stage1）

---

### Stage 2.5 — Skills 同步与打包

**脚本**: `stage2_5_sync_skills.sh <VERSION>`

执行内容：
1. 计算 `rodski/docs/TEST_CASE_WRITING_GUIDE.md` 的 sha256，与 `rodski-skills/rodski-test-guide/source.sha256` 对比
2. 有变更 → 重新切片生成 `rodski-skills/rodski-test-guide/reference/*.md`，git commit
3. 无变更 → 跳过 commit
4. 打 `dist/rodski-skills-v<VERSION>.zip`（无论是否变更都打，确保版本对齐）

失败处理：
- sync 脚本异常 → 检查 `rodski-skills/scripts/sync_test_guide.sh` 是否存在且可执行
- zip 失败 → 检查 `dist/` 目录权限

---

### Stage 3 — 同步版本号 + 打包 + 打 tag

**脚本**: `stage3_build_and_tag.sh <VERSION>`

执行内容：
1. 同步所有版本号文件：
   - `pyproject.toml`（根）
   - `rodski/pyproject.toml`
   - `rodski/__init__.py`
   - `CLAUDE.md`
   - `rodski/docs/*.md`（版本行）
2. `git commit` 版本号变更
3. `python3 -m build .` 从根目录构建（输出到 `dist/`）
4. `scripts/release_check.sh` 验证 wheel 完整性
5. `git tag -a v<VERSION>` 打 annotated tag（**不 push**）

失败处理：
- wheel 验证失败 → 修复打包配置后重跑 stage3
- 如需重来 → 运行 `rollback_tag.sh <VERSION>`

---

### Stage 4 — 干净环境验收 wheel

**脚本**: `stage4_clean_verify.sh <VERSION>`

执行内容：
1. 创建全新 venv（`.release_venv_<VERSION>/`）
2. 安装刚打出的 wheel
3. 验证 `rodski --version` 输出正确版本号
4. 用安装包跑 `demo_full/case/demo_case.xml --headless`
5. 自动清理 venv

失败处理：
- CLI 版本不对 → 检查 `rodski/__init__.py` 是否正确 bump
- 验收失败 → 修复后运行 `rollback_tag.sh` 重来

---

### Stage 5 — 上传 PyPI + push git + 核验

**脚本**: `stage5_publish_and_verify.sh <VERSION>`

执行内容：
1. `twine upload` 上传 wheel + sdist（使用 `~/.pypirc`）
2. 轮询 PyPI API 最多 120s，确认包真实可访问
3. `git push origin main --tags`
4. `git push gitlab main --tags`（如果 remote 存在）
5. 最终核验：PyPI 版本 + GitHub tag 双重确认

失败处理：
- PyPI 上传失败 → tag 未 push，运行 `rollback_tag.sh` 重来
- git push 失败 → PyPI 已上传，手动 push：`git push origin main --tags`

---

## 版本号文件清单

发布时 `bump_all_versions()` 会自动更新以下文件：

| 文件 | 更新方式 |
|------|---------|
| `pyproject.toml`（根） | `version = "X.Y.Z"` |
| `rodski/pyproject.toml` | `version = "X.Y.Z"` |
| `rodski/__init__.py` | `__version__ = "X.Y.Z"` |
| `CLAUDE.md` | `当前版本：vX.Y.Z` |
| `rodski/docs/*.md` | `版本: vX.Y.Z` |

---

## 常见问题

**Q: 发布到一半失败了怎么办？**

查看 `.release_state` 文件确认当前阶段，然后：
- stage1/2 失败 → 修复后重跑对应 stage
- stage3 之后失败 → 先运行 `rollback_tag.sh <VERSION>`，再从 stage3 重来
- stage5 PyPI 上传成功但 git push 失败 → 直接手动 push，不需要回滚

**Q: 如何跳过某个阶段？**

不建议跳过。如果确实需要（如 stage1 已手动完成），可以手动写入状态：
```bash
echo "stage=stage1 version=7.2.0 ts=$(date +%Y%m%d_%H%M%S)" > .release_state
```

**Q: 为什么 tag 要在 PyPI 上传成功后才 push？**

历史上 v7.0.0 / v7.1.0 都因为 PyPI 上传失败留下了"假成功"的 tag，
导致开发者误以为已发布。新流程确保 tag 出现在远端 = PyPI 真实可用。
