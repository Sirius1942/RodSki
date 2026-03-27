#!/bin/bash
# Cassmall 同行调货测试脚本

echo "🚀 Cassmall 同行调货测试启动"
echo "========================"
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../../.." && pwd )"

echo "📁 项目路径: $PROJECT_ROOT"
echo ""

echo "🧪 运行测试用例..."
cd "$PROJECT_ROOT"
python3 rodski/ski_run.py cassmall/thdh/case/login_test.xml

echo ""
echo "✅ 测试完成！"
echo ""
echo "📄 结果已保存到: cassmall/thdh/result/"
