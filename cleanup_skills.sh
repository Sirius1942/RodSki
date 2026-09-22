#!/usr/bin/env bash
set -euo pipefail

cd /Users/sirius.chen/Projects/rodski

echo "=== 删除归档技能 ==="
git rm -rf .claude/skills/rodski-skill--submit-testcases-gitlab
git rm -rf .claude/skills/rodski-skill--switch-rodski-env

echo ""
echo "=== 检查状态 ==="
git status --short

echo ""
echo "=== 提交删除 ==="
git commit -m "chore: 删除已归档的业务特定技能"

echo ""
echo "=== 验证结果 ==="
ls -1 .claude/skills/ | grep "^rodski-skill" || echo "✓ 无归档技能残留"

echo ""
echo "✓ 完成"
