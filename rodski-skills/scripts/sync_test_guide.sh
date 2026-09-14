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

# 注意：旧 reference/*.md 的删除**不在这里**做，而是由下面的 Python 在
# 章节齐备性校验通过之后自己删。之前把删除放在这里，一旦切片失败（章节
# 漂移），旧文件已经删光、新文件又没写全，reference/ 就残缺了。

python3 - "$SRC" "$REF_DIR" <<'PY'
import sys
import re
from pathlib import Path

src_path = Path(sys.argv[1])
out_dir = Path(sys.argv[2])

# 章节标题正则 → 输出文件名
#
# 这份映射必须与 TEST_CASE_WRITING_GUIDE.md 的章节结构保持同步。两个已知的
# 漂移来源：
#   1. 指南新增章节但这里没加 → 新章节被静默并进上一节的文件（例如 15/16 节
#      曾整段落在 14_mobile.md 里）
#   2. 指南删掉某节但这里没删 → 这里会因切不满 17 个而 FAIL，但**旧文件已
#      在切之前被删掉**，失败会留下残缺的 reference/
# 因此切片前先按下面的清单核对一次章节齐备性，缺任何一节就直接退出，不做删除。
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
    (r"^## 15\. ",               "15_ios.md"),
    (r"^## 16\. ",               "16_load_testing.md"),
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

# 先核对章节齐备性再动手删旧文件。否则「切不满」的失败会留下一个残缺的
# reference/ —— 旧文件已经删了，新文件没全写出来。
expected = len(MAPPING)
if len(section_starts) != expected:
    missing = [fname for _, fname in MAPPING
               if fname not in {f for _, f in section_starts}]
    print(f"[FAIL] 期望 {expected} 个章节，实际匹配到 {len(section_starts)} 个。\n"
          f"       未匹配: {', '.join(missing)}\n"
          f"       指南章节结构与 sync_test_guide.sh 的 MAPPING 已漂移，"
          f"请先对齐 MAPPING 再重跑。reference/ 未做任何改动。",
          file=sys.stderr)
    sys.exit(1)

banner = "<!-- 自动生成 from rodski/docs/TEST_CASE_WRITING_GUIDE.md  请勿手工编辑 -->\n\n"

# 校验已过，现在安全：先清旧文件再逐个写出。
# 判据是文件首行的自动生成 banner —— 只动本脚本自己的产物，reference/ 里
# 若有手工维护的其它文件保持不动。这样指南删掉某节时，对应的旧切片
# （如已移除的 90_faq.md）会随之消失，而不是变成孤儿。
for stale in out_dir.glob("*.md"):
    try:
        head = stale.read_text(encoding="utf-8", errors="replace").splitlines()[:1]
    except OSError:
        continue
    if head and head[0].startswith("<!-- 自动生成 from"):
        stale.unlink()

written = 0
for idx, (start, fname, heading) in enumerate(section_starts):
    end = section_starts[idx + 1][0] if idx + 1 < len(section_starts) else len(lines)
    body = "".join(lines[start:end]).rstrip() + "\n"
    out_path = out_dir / fname
    out_path.write_text(banner + body, encoding="utf-8")
    print(f"  + {fname}  ({end-start} lines)")
    written += 1

print(f"[OK] 共生成 {written} 个 reference 文件")
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
