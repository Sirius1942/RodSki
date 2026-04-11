#!/bin/bash
# RodSki Demo 快速启动脚本
# 用法: ./run_demo.sh

echo "RodSki Demo 快速启动"
echo "========================"
echo ""

# 获取脚本所在目录（rodski-demo）
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# 项目根目录: rodski-demo -> RodSki
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "项目路径: $PROJECT_ROOT"
echo "Demo 路径: $SCRIPT_DIR"
echo ""

# 1. 初始化数据库
echo "1. 初始化数据库..."
cd "$SCRIPT_DIR"
python3 init_db.py

if [ $? -eq 0 ]; then
    echo "数据库初始化成功"
else
    echo "数据库初始化失败"
    exit 1
fi

echo ""

# 2. 运行测试用例
echo "2. 运行测试用例..."
cd "$PROJECT_ROOT"
python3 rodski/ski_run.py rodski-demo/case/demo_case.xml

echo ""
echo "3. 测试完成！"
echo ""
echo "查看测试报告："
echo "   ls -la rodski-demo/result/"
