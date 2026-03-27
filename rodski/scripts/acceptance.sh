#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

echo "🔍 RodSki 验收测试"
echo "===================="

PASS=0
FAIL=0

check_demo() {
    local demo_path="$PROJECT_ROOT/$1"
    local demo_name=$(basename "$demo_path")

    if [ ! -d "$demo_path" ]; then
        echo "❌ $demo_name: 目录不存在"
        ((FAIL++))
        return
    fi

    if [ ! -f "$demo_path/model/model.xml" ]; then
        echo "❌ $demo_name: model.xml 缺失"
        ((FAIL++))
        return
    fi

    echo "✅ $demo_name: 结构完整"
    ((PASS++))
}

echo -e "\n📦 检查 Demo 项目..."
check_demo "examples/product/DEMO/demo_site"

echo -e "\n📊 验收结果"
echo "通过: $PASS"
echo "失败: $FAIL"

[ $FAIL -eq 0 ] && exit 0 || exit 1
