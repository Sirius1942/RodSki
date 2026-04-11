#!/bin/bash
# RodSki Demo 快速启动脚本

echo "🏎️  RodSki Demo 快速启动"
echo "========================"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../../.." && pwd )"

echo "📁 项目路径: $PROJECT_ROOT"
echo ""

# 初始化数据库
echo "1️⃣  初始化数据库..."
cd "$SCRIPT_DIR"
python3 init_db.py

if [ $? -eq 0 ]; then
    echo "✅ 数据库初始化成功"
else
    echo "❌ 数据库初始化失败"
    exit 1
fi

echo ""
echo "2️⃣  运行测试用例..."
cd "$PROJECT_ROOT"
python3 rodski/ski_run.py rodski-demo/DEMO/demo_full/case/demo_case.xml

echo ""
echo "3️⃣  测试完成！"
echo ""
echo "📊 查看测试报告："
echo "   ls -la rodski-demo/DEMO/demo_full/result/"
echo ""
echo "🌐 打开测试网站："
echo "   file://$SCRIPT_DIR/demo_site.html"
