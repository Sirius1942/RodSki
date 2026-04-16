"""report 子命令 — 报告生成与管理

支持的操作:
  rodski report generate <result_dir>          从已有结果目录生成报告
  rodski report generate <result_dir> --single-file --output report.html
  rodski report trend --last N [result_dir]    查看历史趋势

run 子命令集成:
  rodski run case/ --report html               执行完毕后自动生成 HTML 报告
"""
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional


# ---------------------------------------------------------------------------
# CLI 子命令注册
# ---------------------------------------------------------------------------

def setup_parser(subparsers):
    """注册 report 子命令（含 generate / trend 二级子命令）"""
    report_parser = subparsers.add_parser("report", help="测试报告管理")
    report_sub = report_parser.add_subparsers(dest="report_action")

    # rodski report generate <result_dir>
    gen_parser = report_sub.add_parser("generate", help="从已有结果生成报告")
    gen_parser.add_argument("result_dir", help="结果目录路径")
    gen_parser.add_argument("--single-file", action="store_true",
                            dest="single_file", help="生成单文件 HTML（内联所有资源）")
    gen_parser.add_argument("--output", "-o", help="输出路径")

    # rodski report trend --last N
    trend_parser = report_sub.add_parser("trend", help="查看历史趋势")
    trend_parser.add_argument("--last", type=int, default=10, help="最近 N 次运行")
    trend_parser.add_argument("result_dir", nargs="?", default=".",
                              help="结果目录（默认当前目录）")


def handle(args):
    """处理 report 子命令"""
    action = getattr(args, "report_action", None)

    if action == "generate":
        return _handle_generate(args)
    elif action == "trend":
        return _handle_trend(args)
    else:
        # 未指定二级子命令时打印帮助
        print("用法: rodski report {generate,trend} ...", file=sys.stderr)
        print("  generate  从已有结果生成报告", file=sys.stderr)
        print("  trend     查看历史趋势", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# generate 子命令
# ---------------------------------------------------------------------------

def _handle_generate(args) -> int:
    """从已有结果目录生成 HTML 报告"""
    result_dir = Path(args.result_dir)
    if not result_dir.exists():
        print(f"错误: 目录不存在: {result_dir}", file=sys.stderr)
        return 1

    # 尝试找到 result JSON 或 XML
    results_data = _load_results_from_dir(result_dir)
    if results_data is None:
        print(f"错误: 在 {result_dir} 中未找到可用的结果文件", file=sys.stderr)
        return 1

    single_file = getattr(args, "single_file", False)
    output_path = args.output if args.output else str(result_dir / "report.html")

    try:
        html = _generate_html(results_data, single_file=single_file)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(html, encoding="utf-8")
        print(f"报告已生成: {output_path}")
        return 0
    except Exception as e:
        print(f"错误: 报告生成失败: {e}", file=sys.stderr)
        return 1


def _load_results_from_dir(result_dir: Path) -> Optional[dict]:
    """从结果目录加载数据，支持 JSON 和 XML 格式"""
    # 1. 尝试 latest_results.json
    for json_name in ("latest_results.json", "results.json"):
        json_path = result_dir / json_name
        if json_path.exists():
            try:
                return json.loads(json_path.read_text(encoding="utf-8"))
            except Exception:
                continue

    # 2. 尝试子目录中的 result.xml
    xml_files = list(result_dir.rglob("result.xml"))
    if xml_files:
        return _parse_result_xml(xml_files[0])

    # 3. 尝试目录中的任意 .json
    for json_file in sorted(result_dir.glob("*.json")):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            if "summary" in data or "results" in data:
                return data
        except Exception:
            continue

    return None


def _parse_result_xml(xml_path: Path) -> Optional[dict]:
    """将 result.xml 解析为与 JSON 兼容的 dict"""
    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(xml_path)
        root = tree.getroot()
        summary_elem = root.find("summary")
        results_elem = root.find("results")

        summary = {}
        if summary_elem is not None:
            summary = {
                "total": int(summary_elem.get("total", 0)),
                "passed": int(summary_elem.get("passed", 0)),
                "failed": int(summary_elem.get("failed", 0)),
                "pass_rate": float(summary_elem.get("pass_rate", "0").rstrip("%")),
                "duration": float(summary_elem.get("total_time", "0").rstrip("s")),
            }

        results = []
        if results_elem is not None:
            for r_elem in results_elem.findall("result"):
                results.append({
                    "step": r_elem.get("case_id", ""),
                    "keyword": r_elem.get("title", ""),
                    "success": r_elem.get("status", "").upper() == "PASS",
                    "message": r_elem.get("error_message", ""),
                    "duration": float(r_elem.get("execution_time", 0) or 0),
                })

        return {
            "summary": summary,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception:
        return None


# ---------------------------------------------------------------------------
# trend 子命令
# ---------------------------------------------------------------------------

def _handle_trend(args) -> int:
    """查看历史趋势"""
    result_dir = Path(args.result_dir)
    last_n = args.last

    history = _load_history_data(str(result_dir))
    if not history:
        # 也尝试 logs/history 子目录
        history = _load_history_data(str(result_dir / "logs" / "history"))

    if not history:
        print("未找到历史运行数据", file=sys.stderr)
        return 1

    history = history[-last_n:]
    print(f"最近 {len(history)} 次运行趋势:")
    print("-" * 60)
    print(f"  {'日期':<14} {'通过率':>8} {'总用例':>8} {'耗时':>10}")
    print("-" * 60)
    for entry in history:
        s = entry.get("summary", {})
        ts = entry.get("timestamp", "")[:10]
        rate = s.get("pass_rate", 0)
        total = s.get("total", 0)
        dur = s.get("duration", 0)
        print(f"  {ts:<14} {rate:>7.1f}% {total:>8} {dur:>9.1f}s")
    print("-" * 60)
    return 0


# ---------------------------------------------------------------------------
# run --report html 集成入口
# ---------------------------------------------------------------------------

def generate_html_from_run_results(
    results: list,
    total: int,
    passed: int,
    failed: int,
    duration: float,
) -> str:
    """供 run.py 的 --report html 调用，返回生成的报告路径"""
    pass_rate = (passed / total * 100) if total > 0 else 0

    report_data = {
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": pass_rate,
            "duration": round(duration, 2),
        },
        "results": _normalize_run_results(results),
        "timestamp": datetime.now().isoformat(),
    }

    html = _generate_html(report_data, single_file=True)
    output_path = Path(f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
    output_path.write_text(html, encoding="utf-8")

    # 同时保存历史记录
    _save_to_history(report_data, "logs/history")

    return str(output_path)


def _normalize_run_results(results: list) -> list:
    """将 SKIExecutor 的 results 转为报告可用格式"""
    normalized = []
    for i, r in enumerate(results, 1):
        status = r.get("status", "FAIL").upper()
        normalized.append({
            "step": r.get("case_id", f"Case {i}"),
            "keyword": r.get("title", ""),
            "success": status == "PASS",
            "message": r.get("error", ""),
            "duration": r.get("execution_time", 0) or 0,
        })
    return normalized


# ---------------------------------------------------------------------------
# HTML 生成
# ---------------------------------------------------------------------------

def _generate_html(
    results: dict,
    include_trend: bool = False,
    history_dir: str = "logs/history",
    single_file: bool = False,
) -> str:
    """生成 HTML 报告"""
    summary = results.get("summary", {})
    steps = results.get("results", [])
    timestamp = results.get("timestamp", datetime.now().isoformat())

    total = summary.get("total", 0)
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    pass_rate = summary.get("pass_rate", 0)
    duration = summary.get("duration", 0)

    rows = ""
    timeline_segments = ""
    total_step_duration = sum(s.get("duration", 0) for s in steps) or 1
    for i, r in enumerate(steps, 1):
        status = "PASS" if r.get("success") else "FAIL"
        status_class = "pass" if r.get("success") else "fail"
        keyword = r.get("keyword", "")
        step_name = r.get("step", f"Step {i}")
        step_duration = r.get("duration", 0)
        message = r.get("message", "")

        msg_display = (message[:50] + "...") if len(message) > 50 else message
        rows += f'''<tr class="{status_class}">
            <td>{i}</td>
            <td>{step_name}</td>
            <td><code>{keyword}</code></td>
            <td><span class="status-badge {status_class}">{status}</span></td>
            <td class="message">{msg_display}</td>
        </tr>\n'''

        width_pct = (step_duration / total_step_duration) * 100 if total_step_duration else (100 / len(steps) if steps else 0)
        timeline_segments += f'<div class="timeline-seg {status_class}" style="width: {width_pct:.2f}%" title="{step_name}: {step_duration:.2f}s"></div>\n'

    # Trend section (optional)
    trend_section = ""
    if include_trend:
        history_data = _load_history_data(history_dir)
        if history_data:
            labels = [d["timestamp"][:10] for d in history_data[-10:]]
            pass_rates = [d["summary"].get("pass_rate", 0) for d in history_data[-10:]]
            durations = [d["summary"].get("duration", 0) for d in history_data[-10:]]

            trend_section = f'''
        <div class="chart-container">
            <h3 class="chart-title">Trend</h3>
            <div class="charts-grid">
                <div class="chart-box">
                    <canvas id="passRateChart"></canvas>
                </div>
                <div class="chart-box">
                    <canvas id="durationChart"></canvas>
                </div>
            </div>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script>
            const ctx1 = document.getElementById('passRateChart').getContext('2d');
            new Chart(ctx1, {{
                type: 'line',
                data: {{
                    labels: {json.dumps(labels)},
                    datasets: [{{
                        label: 'Pass Rate (%)',
                        data: {json.dumps(pass_rates)},
                        borderColor: 'rgb(16, 185, 129)',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        tension: 0.3,
                        fill: true
                    }}]
                }},
                options: {{
                    responsive: true,
                    scales: {{ y: {{ beginAtZero: true, max: 100 }} }}
                }}
            }});
            const ctx2 = document.getElementById('durationChart').getContext('2d');
            new Chart(ctx2, {{
                type: 'bar',
                data: {{
                    labels: {json.dumps(labels)},
                    datasets: [{{
                        label: 'Duration (s)',
                        data: {json.dumps(durations)},
                        backgroundColor: 'rgba(79, 70, 229, 0.6)',
                        borderColor: 'rgb(79, 70, 229)',
                        borderWidth: 1
                    }}]
                }},
                options: {{ responsive: true }}
            }});
        </script>
'''

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RodSki Test Report</title>
    <style>
        :root {{
            --primary: #4F46E5;
            --primary-light: #818CF8;
            --success: #10B981;
            --success-light: #D1FAE5;
            --error: #EF4444;
            --error-light: #FEE2E2;
            --bg: #F9FAFB;
            --card: #FFFFFF;
            --text: #111827;
            --text-muted: #6B7280;
            --border: #E5E7EB;
        }}
        @media (prefers-color-scheme: dark) {{
            :root {{
                --bg: #111827; --card: #1F2937; --text: #F9FAFB;
                --text-muted: #9CA3AF; --border: #374151;
            }}
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg); color: var(--text);
            line-height: 1.6; padding: 20px; min-height: 100vh;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        header {{
            text-align: center; margin-bottom: 30px; padding: 30px;
            background: linear-gradient(135deg, var(--primary), var(--primary-light));
            border-radius: 16px; color: white;
        }}
        header h1 {{ font-size: 2rem; margin-bottom: 8px; }}
        header p {{ opacity: 0.9; }}
        .summary-cards {{
            display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px; margin-bottom: 30px;
        }}
        .card {{
            background: var(--card); border-radius: 12px; padding: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1); border: 1px solid var(--border);
        }}
        .card-label {{ color: var(--text-muted); font-size: 0.875rem; margin-bottom: 4px; }}
        .card-value {{ font-size: 2rem; font-weight: 700; }}
        .card.success .card-value {{ color: var(--success); }}
        .card.error .card-value {{ color: var(--error); }}
        .card.primary .card-value {{ color: var(--primary); }}
        .progress-container {{
            background: var(--card); border-radius: 12px; padding: 20px;
            margin-bottom: 30px; border: 1px solid var(--border);
        }}
        .progress-bar {{
            height: 24px; background: var(--border); border-radius: 12px;
            overflow: hidden; display: flex;
        }}
        .progress-pass {{ background: linear-gradient(90deg, var(--success), #34D399); height: 100%; }}
        .progress-fail {{ background: linear-gradient(90deg, var(--error), #F87171); height: 100%; }}
        .progress-label {{ text-align: center; margin-top: 10px; color: var(--text-muted); }}
        .timeline-container {{
            background: var(--card); border-radius: 12px; padding: 20px;
            margin-bottom: 30px; border: 1px solid var(--border);
        }}
        .timeline-title {{ font-size: 1rem; color: var(--text-muted); margin-bottom: 12px; }}
        .timeline-bar {{
            display: flex; height: 32px; border-radius: 8px;
            overflow: hidden; background: var(--border); gap: 2px;
        }}
        .timeline-seg {{
            height: 100%; min-width: 3px; cursor: pointer; position: relative;
        }}
        .timeline-seg.pass {{ background: var(--success); }}
        .timeline-seg.fail {{ background: var(--error); }}
        .timeline-seg:hover {{ opacity: 0.8; transform: scaleY(1.1); }}
        .timeline-legend {{
            display: flex; gap: 20px; margin-top: 12px; justify-content: center;
        }}
        .legend-item {{ display: flex; align-items: center; gap: 6px; font-size: 0.875rem; color: var(--text-muted); }}
        .legend-dot {{ width: 12px; height: 12px; border-radius: 3px; }}
        .legend-dot.pass {{ background: var(--success); }}
        .legend-dot.fail {{ background: var(--error); }}
        .chart-container {{
            background: var(--card); border-radius: 12px; padding: 20px;
            margin-bottom: 30px; border: 1px solid var(--border);
        }}
        .chart-title {{ font-size: 1.25rem; margin-bottom: 16px; font-weight: 600; }}
        .charts-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
        .chart-box {{ position: relative; height: 300px; }}
        table {{
            width: 100%; border-collapse: collapse; background: var(--card);
            border-radius: 12px; overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1); border: 1px solid var(--border);
        }}
        th {{
            background: var(--primary); color: white; padding: 14px 16px;
            text-align: left; font-weight: 600;
        }}
        td {{ padding: 12px 16px; border-bottom: 1px solid var(--border); }}
        tr:last-child td {{ border-bottom: none; }}
        tr:hover {{ background: rgba(79, 70, 229, 0.05); }}
        tr.pass {{ background: var(--success-light); }}
        tr.fail {{ background: var(--error-light); }}
        @media (prefers-color-scheme: dark) {{
            tr.pass {{ background: rgba(16, 185, 129, 0.1); }}
            tr.fail {{ background: rgba(239, 68, 68, 0.1); }}
        }}
        .status-badge {{
            display: inline-block; padding: 4px 12px; border-radius: 20px;
            font-size: 0.75rem; font-weight: 600; text-transform: uppercase;
        }}
        .status-badge.pass {{ background: var(--success-light); color: var(--success); }}
        .status-badge.fail {{ background: var(--error-light); color: var(--error); }}
        @media (prefers-color-scheme: dark) {{
            .status-badge.pass {{ background: rgba(16, 185, 129, 0.2); }}
            .status-badge.fail {{ background: rgba(239, 68, 68, 0.2); }}
        }}
        code {{
            background: rgba(79, 70, 229, 0.1); padding: 2px 6px; border-radius: 4px;
            font-family: 'Monaco', 'Consolas', monospace; font-size: 0.875rem; color: var(--primary);
        }}
        .message {{ color: var(--text-muted); font-size: 0.875rem; max-width: 300px; overflow: hidden; text-overflow: ellipsis; }}
        footer {{ text-align: center; margin-top: 30px; padding: 20px; color: var(--text-muted); font-size: 0.875rem; }}
        @media (max-width: 768px) {{
            .summary-cards {{ grid-template-columns: repeat(2, 1fr); }}
            .charts-grid {{ grid-template-columns: 1fr; }}
            .message {{ display: none; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>RodSki Test Report</h1>
            <p>{timestamp}</p>
        </header>
        <div class="summary-cards">
            <div class="card primary">
                <div class="card-label">Total</div>
                <div class="card-value">{total}</div>
            </div>
            <div class="card success">
                <div class="card-label">Passed</div>
                <div class="card-value">{passed}</div>
            </div>
            <div class="card error">
                <div class="card-label">Failed</div>
                <div class="card-value">{failed}</div>
            </div>
            <div class="card">
                <div class="card-label">Duration</div>
                <div class="card-value">{duration}s</div>
            </div>
        </div>
        <div class="progress-container">
            <div class="progress-bar">
                <div class="progress-pass" style="width: {pass_rate}%"></div>
                <div class="progress-fail" style="width: {100 - pass_rate}%"></div>
            </div>
            <div class="progress-label">Pass Rate: {pass_rate:.1f}%</div>
        </div>
        {trend_section}
        <div class="timeline-container">
            <h3 class="timeline-title">Execution Timeline</h3>
            <div class="timeline-bar">
                {timeline_segments}
            </div>
            <div class="timeline-legend">
                <span class="legend-item"><span class="legend-dot pass"></span> Pass</span>
                <span class="legend-item"><span class="legend-dot fail"></span> Fail</span>
            </div>
        </div>
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Step</th>
                    <th>Keyword</th>
                    <th>Status</th>
                    <th>Details</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        <footer>
            <p>RodSki Framework</p>
        </footer>
    </div>
</body>
</html>'''


# ---------------------------------------------------------------------------
# 历史数据加载 / 保存
# ---------------------------------------------------------------------------

def _load_history_data(history_dir: str) -> List[Dict[str, Any]]:
    """加载历史测试结果"""
    history_path = Path(history_dir)
    if not history_path.exists():
        return []

    history_files = sorted(
        history_path.glob("result_*.json"),
        key=lambda p: p.stat().st_mtime,
    )
    history_data = []
    for file_path in history_files[-20:]:
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            history_data.append(data)
        except Exception:
            continue
    return history_data


def _save_to_history(results: Dict[str, Any], history_dir: str) -> None:
    """保存当前结果到历史"""
    history_path = Path(history_dir)
    history_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    history_file = history_path / f"result_{timestamp}.json"

    try:
        history_file.write_text(
            json.dumps(results, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as e:
        print(f"警告: 无法保存历史记录: {e}", file=sys.stderr)
