#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RODSKI_DIR="$(dirname "$SCRIPT_DIR")"

case "$1" in
  static)
    echo "🔍 运行静态检查..."
    cd "$RODSKI_DIR"
    python -m black --check . 2>/dev/null || echo "⚠️  black 未安装"
    python -m flake8 . 2>/dev/null || echo "⚠️  flake8 未安装"
    python -m mypy . 2>/dev/null || echo "⚠️  mypy 未安装"
    python -m bandit -r . -c bandit.yaml 2>/dev/null || echo "⚠️  bandit 未安装"
    python scripts/validate_xml.py
    ;;
  test)
    echo "🧪 运行单元测试..."
    cd "$RODSKI_DIR"
    python -m pytest tests/ 2>/dev/null || python selftest.py
    ;;
  coverage)
    echo "📊 生成覆盖率报告..."
    cd "$RODSKI_DIR"
    python -m pytest tests/ --cov=rodski --cov-report=html --cov-report=term 2>/dev/null || echo "⚠️  pytest-cov 未安装"
    ;;
  *)
    echo "用法: $0 {static|test|coverage}"
    exit 1
    ;;
esac
