#!/usr/bin/env bash
# sync_test_guide.sh — 从 rodski/docs/TEST_CASE_WRITING_GUIDE.md 切片生成
# rodski-skills/rodski-test-guide/reference/*.md
#
# 退出码:
#   0  无变更（指纹一致，跳过切片）
#   10 有更新（已重新切片并刷新指纹）
#   1  错误
#
# 幂等：未变更时不修改任何文件。

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC="$PROJECT_ROOT/rodski/docs/TEST_CASE_WRITING_GUIDE.md"
SKILL_DIR="$PROJECT_ROOT/rodski-skills/rodski-test-guide"
REF_DIR="$SKILL_DIR/reference"
SHA_FILE="$SKILL_DIR/source.sha256"

[[ -f "$SRC" ]] || { echo "[FAIL] 源文档不存在: $SRC" >&2; exit 1; }

CURRENT_SHA=$(shasum -a 256 "$SRC" | awk '{print $1}')

if [[ -f "$SHA_FILE" ]]; then
    STORED_SHA=$(awk '{print $1}' "$SHA_FILE")
    if [[ "$CURRENT_SHA" == "$STORED_SHA" ]]; then
        echo "[OK] 测试指南无变更 (sha256=${CURRENT_SHA:0:12}...)"
        exit 0
    fi
fi

echo "[INFO] 测试指南有变更，重新切片..."

mkdir -p "$REF_DIR"
# 清空旧 reference（只删 *.md，保留可能存在的其他文件）
find "$REF_DIR" -maxdepth 1 -name '*.md' -delete

python3 - "$SRC" "$REF_DIR" <<'PY'
import sys
import re
from pathlib import Path

src_path = Path(sys.argv[1])
out_dir = Path(sys.argv[2])

# 章节标题正则 → 输出文件名
MAPPING = [
    (r"^## 1\. ",                "01_concepts.md"),
    (r"^## 2\. ",                "02_directory.md"),
    (r"^## 3\. ",                "03_case_xml.md"),
    (r"^## 4\. ",                "04_model_xml.md"),
    (r"^## 5\. ",                "05_data_tables.md"),
    (r"^## 6\. ",                "06_global_value.md"),
    (r"^## 7\. ",                "07_variable_refs.md"),
    (r"^## 8\. ",                "08_keywords.md"),
    (r"^## 9\. ",                "09_examples.md"),
    (r"^## 10\. ",               "10_test_plan.md"),
    (r"^## 11\. ",               "11_dynamic_steps.md"),
    (r"^## 12\. ",               "12_vision_locator.md"),
    (r"^## 13\. ",               "13_desktop.md"),
    (r"^## 14\. ",               "14_mobile.md"),
    (r"^## 附录：常见问题",      "90_faq.md"),
    (r"^## 附录：关键字速查",    "91_keyword_cheatsheet.md"),
    (r"^## 附录：测试结果 XML",  "92_result_xml.md"),
]

text = src_path.read_text(encoding="utf-8")
lines = text.splitlines(keepends=True)

section_starts = []
for i, line in enumerate(lines):
    for pattern, fname in MAPPING:
        if re.match(pattern, line):
            section_starts.append((i, fname, line.rstrip()))
            break

if not section_starts:
    print("[FAIL] 未找到任何匹配章节", file=sys.stderr)
    sys.exit(1)

banner = "<!-- 自动生成 from rodski/docs/TEST_CASE_WRITING_GUIDE.md  请勿手工编辑 -->\n\n"

written = 0
for idx, (start, fname, heading) in enumerate(section_starts):
    end = section_starts[idx + 1][0] if idx + 1 < len(section_starts) else len(lines)
    body = "".join(lines[start:end]).rstrip() + "\n"
    out_path = out_dir / fname
    out_path.write_text(banner + body, encoding="utf-8")
    print(f"  + {fname}  ({end-start} lines)")
    written += 1

print(f"[OK] 共生成 {written} 个 reference 文件")

# 校验：必须 17 个
expected = len(MAPPING)
if written != expected:
    print(f"[FAIL] 期望 {expected} 个章节，实际只切出 {written} 个", file=sys.stderr)
    sys.exit(1)
PY

echo "$CURRENT_SHA  $(basename "$SRC")" > "$SHA_FILE"
echo "[OK] 指纹已更新: ${CURRENT_SHA:0:12}..."

# 同步 README.md 中的源文档版本号与 sha256
GUIDE_VERSION=$(grep -m1 '^\*\*版本\*\*:' "$SRC" | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+' || echo "unknown")
README="$PROJECT_ROOT/rodski-skills/README.md"
if [[ -f "$README" ]]; then
    sed -i '' \
        "s/| \`rodski-test-guide\` | \*\*v[0-9.]*\*\* (sha256: \`[a-f0-9]*\`)/| \`rodski-test-guide\` | **${GUIDE_VERSION}** (sha256: \`${CURRENT_SHA:0:12}\`)/" \
        "$README"
    echo "[OK] README.md 版本行已更新: ${GUIDE_VERSION} / ${CURRENT_SHA:0:12}..."
fi

exit 10
