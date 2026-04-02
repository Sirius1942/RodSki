#!/bin/bash

# RodSki Web 启动脚本

cd "$(dirname "$0")"

echo "🍄 RodSki Web 启动中..."

# 检查配置文件
if [ ! -f "config.yaml" ]; then
    echo "❌ 配置文件 config.yaml 不存在"
    exit 1
fi

# 检查依赖
if ! pip show flask > /dev/null 2>&1; then
    echo "📦 安装依赖..."
    pip install -r requirements.txt
fi

# 设置 PYTHONPATH 以便模块导入
export PYTHONPATH="$(pwd):$PYTHONPATH"

# 启动应用
echo "🚀 启动 Flask 服务..."
python3 src/app.py
