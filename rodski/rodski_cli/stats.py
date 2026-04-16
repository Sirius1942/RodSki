"""stats 子命令 - 统计数据分析"""
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from ..core.statistics_collector import StatisticsCollector


def setup_parser(subparsers):
    parser = subparsers.add_parser(
        "stats",
        help="统计分析测试结果",
        description="解析 result.xml 文件，输出执行统计摘要"
    )
    parser.add_argument(
        "result_dir",
        help="结果目录路径，包含 result.xml 文件"
    )
    parser.add_argument(
        "--from",
        dest="date_from",
        help="开始日期 (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--to",
        dest="date_to",
        help="结束日期 (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--format",
        choices=["terminal", "json"],
        default="terminal",
        help="输出格式 (默认: terminal)"
    )
    parser.add_argument(
        "--output",
        help="输出文件路径 (默认: stdout)"
    )
    parser.add_argument(
        "--flaky-only",
        action="store_true",
        help="仅显示不稳定用例 (pass rate < 30%)"
    )
    parser.add_argument(
        "--top-slow",
        type=int,
        default=5,
        dest="top_slow",
        help="显示最慢用例数量 (默认: 5)"
    )


def _find_result_files(result_dir: Path) -> List[Path]:
    """递归查找所有 result XML 文件"""
    result_files = []
    for xml_file in result_dir.rglob("result.xml"):
        result_files.append(xml_file)
    # 也支持以 result_ 开头的 xml 文件
    for xml_file in result_dir.rglob("result_*.xml"):
        if xml_file not in result_files:
            result_files.append(xml_file)
    return result_files


def _filter_by_date(files: List[Path], date_from: Optional[str], date_to: Optional[str]) -> List[Path]:
    """按日期范围过滤文件"""
    if not date_from and not date_to:
        return files

    from_xml_dates = {}
    try:
        import xml.etree.ElementTree as ET
        for f in files:
            try:
                tree = ET.parse(f)
                root = tree.getroot()
                summary = root.find("summary")
                if summary is not None:
                    start_time = summary.get("start_time", "")
                    if start_time:
                        date_str = start_time.split("T")[0] if "T" in start_time else start_time[:10]
                        from_xml_dates[f] = date_str
            except Exception:
                from_xml_dates[f] = ""
    except Exception:
        return files

    filtered = []
    for f in files:
        file_date = from_xml_dates.get(f, "")
        if not file_date:
            filtered.append(f)
            continue
        if date_from and file_date < date_from:
            continue
        if date_to and file_date > date_to:
            continue
        filtered.append(f)
    return filtered


def _format_terminal(stats: StatisticsCollector, flaky_only: bool, top_slow: int) -> str:
    """格式化终端输出"""
    lines = []
    agg = stats.aggregate()

    # 摘要头部
    total_runs = len(stats.run_stats)
    total_cases = len(stats.case_stats)
    total_passed = sum(r.passed for r in stats.run_stats)
    total_failed = sum(r.failed for r in stats.run_stats)
    total_skipped = sum(r.skipped for r in stats.run_stats)
    total_tests = total_passed + total_failed + total_skipped
    pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0

    lines.append("")
    lines.append("=" * 60)
    lines.append("  📊 RodSki 测试统计报告")
    lines.append("=" * 60)
    lines.append(f"  统计时间范围: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("-" * 60)
    lines.append(f"  总运行次数:   {total_runs}")
    lines.append(f"  总用例数:     {total_cases}")
    lines.append(f"  总测试数:     {total_tests}")
    lines.append(f"  ✅ 通过:      {total_passed}")
    lines.append(f"  ❌ 失败:      {total_failed}")
    lines.append(f"  ⏭️  跳过:      {total_skipped}")
    lines.append(f"  📈 通过率:     {pass_rate:.1f}%")
    lines.append("-" * 60)

    # Flaky Cases
    flaky = stats.get_flaky_cases(threshold=0.3)
    if flaky:
        lines.append(f"  ⚠️  不稳定用例 ({len(flaky)} 个):")
        for case_id in flaky[:10]:
            cs = stats.case_stats.get(case_id)
            if cs:
                lines.append(f"    - {case_id}: pass_rate={cs.pass_rate:.1f}%, runs={cs.run_count}")
        if len(flaky) > 10:
            lines.append(f"    ... 还有 {len(flaky) - 10} 个")
        lines.append("-" * 60)

    # 按优先级统计
    priority_stats = stats.by_priority()
    if priority_stats:
        lines.append("  📋 按优先级统计:")
        for priority, count in priority_stats.items():
            lines.append(f"    {priority}: {count}")
        lines.append("-" * 60)

    # 按组件统计
    component_stats = stats.by_component()
    if component_stats:
        lines.append("  🧩 按组件统计:")
        for component, count in component_stats.items():
            lines.append(f"    {component}: {count}")
        lines.append("-" * 60)

    # Top N 最慢用例
    if not flaky_only and top_slow > 0:
        sorted_cases = sorted(
            stats.case_stats.items(),
            key=lambda x: x[1].avg_duration,
            reverse=True
        )
        top_slow_cases = [c for c in sorted_cases if c[1].avg_duration > 0][:top_slow]
        if top_slow_cases:
            lines.append(f"  🐌 Top {len(top_slow_cases)} 最慢用例:")
            for case_id, cs in top_slow_cases:
                duration_ms = cs.avg_duration
                if duration_ms >= 1000:
                    duration_str = f"{duration_ms/1000:.1f}s"
                else:
                    duration_str = f"{duration_ms:.0f}ms"
                lines.append(f"    - {case_id}: avg={duration_str}, runs={cs.run_count}, pass_rate={cs.pass_rate:.1f}%")
            lines.append("-" * 60)

    # 每日趋势
    daily = stats.daily_trend()
    if daily and not flaky_only:
        lines.append("  📅 每日趋势 (最近 7 天):")
        sorted_days = sorted(daily.items(), reverse=True)[:7]
        for day, data in sorted_days:
            day_total = data["total"]
            day_passed = data["passed"]
            day_rate = (day_passed / day_total * 100) if day_total > 0 else 0
            lines.append(f"    {day}: {day_passed}/{day_total} ({day_rate:.1f}%)")
        lines.append("-" * 60)

    if flaky_only:
        if not flaky:
            lines.append("  ✅ 未发现不稳定用例")
            lines.append("-" * 60)

    lines.append("=" * 60)
    lines.append("")
    return "\n".join(lines)


def _format_json(stats: StatisticsCollector) -> Dict[str, Any]:
    """格式化 JSON 输出"""
    agg = stats.aggregate()
    result = {
        "generated_at": datetime.now().isoformat(),
        "total_runs": len(stats.run_stats),
        "total_cases": len(stats.case_stats),
        "summary": {
            "total_passed": sum(r.passed for r in stats.run_stats),
            "total_failed": sum(r.failed for r in stats.run_stats),
            "total_skipped": sum(r.skipped for r in stats.run_stats),
        },
        "cases": {},
        "runs": [],
        "daily_trend": stats.daily_trend(),
        "flaky_cases": stats.get_flaky_cases(threshold=0.3),
        "by_priority": stats.by_priority(),
        "by_component": stats.by_component(),
    }

    for case_id, cs in stats.case_stats.items():
        result["cases"][case_id] = {
            "run_count": cs.run_count,
            "passed": cs.passed,
            "failed": cs.failed,
            "skipped": cs.skipped,
            "pass_rate": round(cs.pass_rate, 2),
            "avg_duration_ms": round(cs.avg_duration, 2),
            "step_stats": {
                kw: {
                    "count": s.count,
                    "passed": s.passed,
                    "failed": s.failed,
                    "avg_ms": round(s.avg, 2),
                    "p50_ms": round(s.p50, 2),
                    "p95_ms": round(s.p95, 2),
                }
                for kw, s in cs.step_stats.items()
            }
        }

    for rs in stats.run_stats:
        result["runs"].append({
            "run_id": rs.run_id,
            "run_time": rs.run_time,
            "total": rs.total,
            "passed": rs.passed,
            "failed": rs.failed,
            "skipped": rs.skipped,
            "pass_rate": round(rs.pass_rate, 2),
            "total_duration_ms": rs.total_duration,
        })

    return result


def handle(args):
    """处理 stats 命令"""
    result_dir = Path(args.result_dir)
    if not result_dir.exists():
        print(f"错误: 目录不存在: {result_dir}", file=sys.stderr)
        return 1

    # 查找 result XML 文件
    result_files = _find_result_files(result_dir)
    if not result_files:
        print(f"错误: 在 {result_dir} 中未找到 result.xml 文件", file=sys.stderr)
        return 1

    # 日期过滤
    result_files = _filter_by_date(
        result_files,
        getattr(args, "date_from", None),
        getattr(args, "date_to", None)
    )

    if not result_files:
        print("错误: 日期范围内未找到 result.xml 文件", file=sys.stderr)
        return 1

    # 收集统计
    stats = StatisticsCollector()
    for rf in result_files:
        try:
            stats.add_result(str(rf))
        except Exception as e:
            print(f"警告: 解析 {rf} 失败: {e}", file=sys.stderr)

    # 生成输出
    if args.format == "json":
        import json
        output_data = _format_json(stats)
        output_text = json.dumps(output_data, indent=2, ensure_ascii=False)
    else:
        output_text = _format_terminal(stats, args.flaky_only, args.top_slow)

    # 输出
    if args.output:
        Path(args.output).write_text(output_text, encoding="utf-8")
        print(f"统计报告已保存: {args.output}")
    else:
        print(output_text)

    return 0
