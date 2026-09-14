#!/usr/bin/env python3
"""
RodSki 探索测试快速启动脚本

使用方法:
    python3 quick_explore.py --url http://localhost:8000 --goal "探索登录功能"
    python3 quick_explore.py --charter charter.json --output report.html
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from rodski_agent.explore.charter import CharterCard
    from rodski_agent.explore.executor import ExploreAgent
    from rodski_agent.explore.report import ExploreReportGenerator
    from rodski.core.keyword_engine import KeywordEngine
except ImportError as e:
    print(f"❌ 依赖缺失: {e}")
    print("\n请安装依赖:")
    print("  pip install rodski>=9.2.3")
    print("  pip install rodski-agent>=9.2.3")
    print("  playwright install chromium")
    sys.exit(1)


def create_default_charter(url: str, goal: str) -> CharterCard:
    """创建默认探索约章"""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    domain = parsed.netloc or "localhost"

    return CharterCard(
        charter_id="QUICK_EXPLORE",
        goal=goal or f"探索 {url} 的核心功能",
        scope={
            "entry_point": url,
            "allowed_domains": [domain],
            "focus_areas": ["导航", "表单", "交互"]
        },
        oracle=[
            "页面正常加载",
            "无浏览器错误",
            "交互响应正常"
        ],
        allowed_actions=["navigate", "wait", "screenshot", "click"],
        budget={
            "max_steps": 20,
            "max_time_seconds": 300
        }
    )


def load_charter_from_file(filepath: str) -> CharterCard:
    """从 JSON 文件加载探索约章"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return CharterCard(**data)


def execute_command(command: dict) -> dict:
    """命令执行函数"""
    engine = KeywordEngine()
    try:
        result = engine.execute(command)
        return result
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


def main():
    parser = argparse.ArgumentParser(
        description="RodSki 探索测试快速启动脚本"
    )
    parser.add_argument(
        "--url",
        help="探索起点 URL（与 --charter 互斥）"
    )
    parser.add_argument(
        "--goal",
        help="探索目标描述"
    )
    parser.add_argument(
        "--charter",
        help="探索约章 JSON 文件路径"
    )
    parser.add_argument(
        "--output",
        default="explore_report.html",
        help="HTML 报告输出路径（默认: explore_report.html）"
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=20,
        help="最大探索步数（默认: 20）"
    )
    parser.add_argument(
        "--max-time",
        type=int,
        default=300,
        help="最大探索时间（秒，默认: 300）"
    )

    args = parser.parse_args()

    # 验证参数
    if not args.charter and not args.url:
        parser.error("必须指定 --url 或 --charter 之一")

    if args.charter and args.url:
        parser.error("--url 和 --charter 不能同时指定")

    # 创建或加载探索约章
    if args.charter:
        print(f"📋 加载探索约章: {args.charter}")
        charter = load_charter_from_file(args.charter)
    else:
        print(f"📋 创建默认探索约章")
        charter = create_default_charter(args.url, args.goal)
        charter.budget["max_steps"] = args.max_steps
        charter.budget["max_time_seconds"] = args.max_time

    print(f"🎯 探索目标: {charter.goal}")
    print(f"🌐 起点 URL: {charter.scope['entry_point']}")
    print(f"⏱️  预算: {charter.budget['max_steps']} 步 / {charter.budget['max_time_seconds']} 秒")
    print()

    # 创建探索 Agent
    print("🤖 启动探索 Agent...")
    agent = ExploreAgent(execute_command_fn=execute_command)

    # 启动探索会话
    session = agent.start_session(charter)
    print(f"✅ 会话已启动: {session.session_id}")
    print()

    # 执行探索循环
    print("🔍 开始探索...")
    try:
        session = agent.explore_loop()
    except KeyboardInterrupt:
        print("\n⚠️  用户中断探索")
    except Exception as e:
        print(f"\n❌ 探索失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # 显示结果摘要
    print()
    print("=" * 60)
    print("📊 探索结果摘要")
    print("=" * 60)
    print(f"总步数: {len(session.history)}")
    print(f"发现问题: {len(session.findings)}")
    print(f"会话状态: {session.status}")

    if session.findings:
        print("\n发现的问题:")
        for i, finding in enumerate(session.findings, 1):
            print(f"  {i}. [{finding.finding_type.value}] {finding.title}")
            print(f"     质量: {finding.quality.value}")
    else:
        print("\n✅ 未发现问题")

    # 生成 HTML 报告
    print(f"\n📄 生成 HTML 报告: {args.output}")
    generator = ExploreReportGenerator()
    html_report = generator.generate_html(
        session,
        title=f"探索测试报告 - {charter.goal}"
    )

    output_path = Path(args.output)
    output_path.write_text(html_report, encoding='utf-8')
    print(f"✅ 报告已生成: {output_path.absolute()}")

    # 返回状态码
    if session.findings:
        sys.exit(1)  # 有发现问题时返回非零
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
