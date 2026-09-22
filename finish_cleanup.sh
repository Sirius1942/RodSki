#!/usr/bin/env bash
# 完成清理：删除归档技能

set -euo pipefail

cd /Users/sirius.chen/Projects/rodski

echo "当前分支: $(git branch --show-current)"
echo ""

echo "=== 删除归档技能目录 ==="
git rm -r .claude/skills/rodski-skill--submit-testcases-gitlab
echo "✓ 已删除 submit-testcases-gitlab"

git rm -r .claude/skills/rodski-skill--switch-rodski-env
echo "✓ 已删除 switch-rodski-env"

echo ""
echo "=== 当前状态 ==="
git status --short

echo ""
echo "=== 提交删除 ==="
git commit -m "chore: 删除已归档的业务特定技能

这两个技能已移至 rodski-skills/.archived-business-specific/：
- rodski-skill--submit-testcases-gitlab
- rodski-skill--switch-rodski-env

归档副本保留供参考，但不再在 Claude Code 会话中加载。"

echo ""
echo "=== 验证结果 ==="
echo "剩余的 rodski-skill 目录："
ls -1 .claude/skills/ | grep "^rodski-skill" || echo "(无)"

echo ""
echo "✅ 清理完成"
