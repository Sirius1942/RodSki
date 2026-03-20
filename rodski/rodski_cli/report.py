"""report 子命令 - 报告生成"""
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional


def setup_parser(subparsers):
    parser = subparsers.add_parser("report", help="生成报告")
    parser.add_argument("--format", choices=["html", "json", "pdf"], default="html", help="报告格式")
    parser.add_argument("--input", help="结果文件路径")
    parser.add_argument("--output", help="输出路径")
    parser.add_argument("--trend", action="store_true", help="包含历史趋势图表")
    parser.add_argument("--history-dir", default="logs/history", help="历史报告目录")


def handle(args):
    results_file = Path(args.input) if args.input else Path("logs/latest_results.json")
    if not results_file.exists():
        print("没有可用的执行结果", file=sys.stderr)
        return 1

    try:
        results = json.loads(results_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, Exception):
        print("结果文件格式错误", file=sys.stderr)
        return 1

    output = args.output or f"report.{args.format}"

    if args.format == "json":
        Path(output).write_text(json.dumps(results, indent=2, ensure_ascii=False))
    elif args.format == "pdf":
        html = _generate_html(results, include_trend=args.trend, history_dir=args.history_dir)
        success = _export_pdf(html, output)
        if not success:
            print("PDF 导出失败，请确保已安装 pdfkit 或 weasyprint", file=sys.stderr)
            # Fallback to HTML
            Path(output.replace('.pdf', '.html')).write_text(html, encoding="utf-8")
            print(f"已生成 HTML 报告: {output.replace('.pdf', '.html')}")
            return 1
    else:
        html = _generate_html(results, include_trend=args.trend, history_dir=args.history_dir)
        Path(output).write_text(html, encoding="utf-8")

    print(f"报告已生成: {output}")
    
    # Save to history
    if args.trend:
        _save_to_history(results, args.history_dir)
    
    return 0


def _generate_html(results: dict, include_trend: bool = False, history_dir: str = "logs/history") -> str:
    summary = results.get("summary", {})
    steps = results.get("results", [])
    timestamp = results.get("timestamp", datetime.now().isoformat())
    
    total = summary.get('total', 0)
    passed = summary.get('passed', 0)
    failed = summary.get('failed', 0)
    pass_rate = summary.get('pass_rate', 0)
    duration = summary.get('duration', 0)

    rows = ""
    timeline_segments = ""
    for i, r in enumerate(steps, 1):
        status = "PASS" if r.get("success") else "FAIL"
        status_class = "pass" if r.get("success") else "fail"
        keyword = r.get("keyword", "")
        step_name = r.get("step", f"步骤 {i}")
        step_duration = r.get("duration", 0)
        message = r.get("message", "")
        
        # Table rows
        rows += f'''<tr class="{status_class}">
            <td>{i}</td>
            <td>{step_name}</td>
            <td><code>{keyword}</code></td>
            <td><span class="status-badge {status_class}">{status}</span></td>
            <td class="message">{message[:50] + '...' if len(message) > 50 else message}</td>
        </tr>\n'''
        
        # Timeline segments (proportional width based on duration)
        if duration > 0:
            width_pct = (step_duration / duration) * 100
        else:
            width_pct = 100 / len(steps) if steps else 0
        timeline_segments += f'<div class="timeline-seg {status_class}" style="width: {width_pct:.2f}%" title="{step_name}: {step_duration:.2f}s"></div>\n'
    
    # Trend chart section
    trend_section = ""
    if include_trend:
        history_data = _load_history_data(history_dir)
        if history_data:
            labels = [d["timestamp"][:10] for d in history_data[-10:]]  # Last 10 runs
            pass_rates = [d["summary"].get("pass_rate", 0) for d in history_data[-10:]]
            durations = [d["summary"].get("duration", 0) for d in history_data[-10:]]
            
            trend_section = f'''
        <div class="chart-container">
            <h3 class="chart-title">📈 趋势分析</h3>
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
            // Pass Rate Trend
            const ctx1 = document.getElementById('passRateChart').getContext('2d');
            new Chart(ctx1, {{
                type: 'line',
                data: {{
                    labels: {json.dumps(labels)},
                    datasets: [{{
                        label: '通过率 (%)',
                        data: {json.dumps(pass_rates)},
                        borderColor: 'rgb(16, 185, 129)',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        tension: 0.3,
                        fill: true
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {{
                        title: {{ display: true, text: '通过率趋势' }}
                    }},
                    scales: {{
                        y: {{ beginAtZero: true, max: 100 }}
                    }}
                }}
            }});
            
            // Duration Trend
            const ctx2 = document.getElementById('durationChart').getContext('2d');
            new Chart(ctx2, {{
                type: 'bar',
                data: {{
                    labels: {json.dumps(labels)},
                    datasets: [{{
                        label: '执行时间 (秒)',
                        data: {json.dumps(durations)},
                        backgroundColor: 'rgba(79, 70, 229, 0.6)',
                        borderColor: 'rgb(79, 70, 229)',
                        borderWidth: 1
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {{
                        title: {{ display: true, text: '执行时间趋势' }}
                    }}
                }}
            }});
        </script>
'''

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SKI 测试报告</title>
    <style>
        :root {{
            --primary: #4F46E5;
            --primary-light: #818CF8;
            --success: #10B981;
            --success-light: #D1FAE5;
            --error: #EF4444;
            --error-light: #FEE2E2;
            --warning: #F59E0B;
            --bg: #F9FAFB;
            --card: #FFFFFF;
            --text: #111827;
            --text-muted: #6B7280;
            --border: #E5E7EB;
        }}
        
        @media (prefers-color-scheme: dark) {{
            :root {{
                --bg: #111827;
                --card: #1F2937;
                --text: #F9FAFB;
                --text-muted: #9CA3AF;
                --border: #374151;
            }}
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            padding: 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        header {{
            text-align: center;
            margin-bottom: 30px;
            padding: 30px;
            background: linear-gradient(135deg, var(--primary), var(--primary-light));
            border-radius: 16px;
            color: white;
        }}
        
        header h1 {{
            font-size: 2rem;
            margin-bottom: 8px;
        }}
        
        header p {{
            opacity: 0.9;
        }}
        
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 30px;
        }}
        
        .card {{
            background: var(--card);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border: 1px solid var(--border);
        }}
        
        .card-label {{
            color: var(--text-muted);
            font-size: 0.875rem;
            margin-bottom: 4px;
        }}
        
        .card-value {{
            font-size: 2rem;
            font-weight: 700;
        }}
        
        .card.success .card-value {{ color: var(--success); }}
        .card.error .card-value {{ color: var(--error); }}
        .card.primary .card-value {{ color: var(--primary); }}
        
        .progress-container {{
            background: var(--card);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 30px;
            border: 1px solid var(--border);
        }}
        
        .progress-bar {{
            height: 24px;
            background: var(--border);
            border-radius: 12px;
            overflow: hidden;
            display: flex;
        }}
        
        .progress-pass {{
            background: linear-gradient(90deg, var(--success), #34D399);
            height: 100%;
            transition: width 0.5s ease;
        }}
        
        .progress-fail {{
            background: linear-gradient(90deg, var(--error), #F87171);
            height: 100%;
            transition: width 0.5s ease;
        }}
        
        .progress-label {{
            text-align: center;
            margin-top: 10px;
            color: var(--text-muted);
        }}
        
        .timeline-container {{
            background: var(--card);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 30px;
            border: 1px solid var(--border);
        }}
        
        .timeline-title {{
            font-size: 1rem;
            color: var(--text-muted);
            margin-bottom: 12px;
            font-weight: 500;
        }}
        
        .timeline-bar {{
            display: flex;
            height: 32px;
            border-radius: 8px;
            overflow: hidden;
            background: var(--border);
            gap: 2px;
        }}
        
        .timeline-seg {{
            height: 100%;
            min-width: 3px;
            transition: all 0.2s ease;
            cursor: pointer;
            position: relative;
        }}
        
        .timeline-seg.pass {{
            background: var(--success);
        }}
        
        .timeline-seg.fail {{
            background: var(--error);
        }}
        
        .timeline-seg:hover {{
            opacity: 0.8;
            transform: scaleY(1.1);
            filter: brightness(1.15);
        }}
        
        .timeline-legend {{
            display: flex;
            gap: 20px;
            margin-top: 12px;
            justify-content: center;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 0.875rem;
            color: var(--text-muted);
        }}
        
        .legend-dot {{
            width: 12px;
            height: 12px;
            border-radius: 3px;
        }}
        
        .legend-dot.pass {{
            background: var(--success);
        }}
        
        .legend-dot.fail {{
            background: var(--error);
        }}
        
        .chart-container {{
            background: var(--card);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 30px;
            border: 1px solid var(--border);
        }}
        
        .chart-title {{
            font-size: 1.25rem;
            color: var(--text);
            margin-bottom: 16px;
            font-weight: 600;
        }}
        
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }}
        
        .chart-box {{
            position: relative;
            height: 300px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            background: var(--card);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border: 1px solid var(--border);
        }}
        
        th {{
            background: var(--primary);
            color: white;
            padding: 14px 16px;
            text-align: left;
            font-weight: 600;
        }}
        
        td {{
            padding: 12px 16px;
            border-bottom: 1px solid var(--border);
        }}
        
        tr:last-child td {{ border-bottom: none; }}
        
        tr:hover {{ background: rgba(79, 70, 229, 0.05); }}
        
        tr.pass {{ background: var(--success-light); }}
        tr.fail {{ background: var(--error-light); }}
        
        @media (prefers-color-scheme: dark) {{
            tr.pass {{ background: rgba(16, 185, 129, 0.1); }}
            tr.fail {{ background: rgba(239, 68, 68, 0.1); }}
        }}
        
        .status-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }}
        
        .status-badge.pass {{
            background: var(--success-light);
            color: var(--success);
        }}
        
        .status-badge.fail {{
            background: var(--error-light);
            color: var(--error);
        }}
        
        @media (prefers-color-scheme: dark) {{
            .status-badge.pass {{
                background: rgba(16, 185, 129, 0.2);
            }}
            .status-badge.fail {{
                background: rgba(239, 68, 68, 0.2);
            }}
        }}
        
        code {{
            background: rgba(79, 70, 229, 0.1);
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.875rem;
            color: var(--primary);
        }}
        
        .message {{
            color: var(--text-muted);
            font-size: 0.875rem;
            max-width: 300px;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        
        footer {{
            text-align: center;
            margin-top: 30px;
            padding: 20px;
            color: var(--text-muted);
            font-size: 0.875rem;
        }}
        
        @media (max-width: 768px) {{
            .summary-cards {{ grid-template-columns: repeat(2, 1fr); }}
            .charts-grid {{ grid-template-columns: 1fr; }}
            th, td {{ padding: 10px 12px; font-size: 0.875rem; }}
            .message {{ display: none; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🏎️ SKI 测试报告</h1>
            <p>生成时间: {timestamp}</p>
        </header>
        
        <div class="summary-cards">
            <div class="card primary">
                <div class="card-label">总用例数</div>
                <div class="card-value">{total}</div>
            </div>
            <div class="card success">
                <div class="card-label">通过</div>
                <div class="card-value">{passed}</div>
            </div>
            <div class="card error">
                <div class="card-label">失败</div>
                <div class="card-value">{failed}</div>
            </div>
            <div class="card">
                <div class="card-label">执行耗时</div>
                <div class="card-value">{duration}s</div>
            </div>
        </div>
        
        <div class="progress-container">
            <div class="progress-bar">
                <div class="progress-pass" style="width: {pass_rate}%"></div>
                <div class="progress-fail" style="width: {100 - pass_rate}%"></div>
            </div>
            <div class="progress-label">通过率: {pass_rate}%</div>
        </div>
        
        {trend_section}
        
        <div class="timeline-container">
            <h3 class="timeline-title">执行时间线</h3>
            <div class="timeline-bar">
                {timeline_segments}
            </div>
            <div class="timeline-legend">
                <span class="legend-item"><span class="legend-dot pass"></span> 通过</span>
                <span class="legend-item"><span class="legend-dot fail"></span> 失败</span>
            </div>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>步骤</th>
                    <th>关键字</th>
                    <th>结果</th>
                    <th>详情</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        
        <footer>
            <p>RodSki Framework v1.2.3 | 热破 (Hot Rod) 🏎️</p>
        </footer>
    </div>
</body>
</html>'''


def _load_history_data(history_dir: str) -> List[Dict[str, Any]]:
    """Load historical test results for trend analysis"""
    history_path = Path(history_dir)
    if not history_path.exists():
        return []
    
    history_files = sorted(history_path.glob("result_*.json"), key=lambda p: p.stat().st_mtime)
    history_data = []
    
    for file_path in history_files[-20:]:  # Load last 20 results
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            history_data.append(data)
        except Exception:
            continue
    
    return history_data


def _save_to_history(results: Dict[str, Any], history_dir: str) -> None:
    """Save current results to history for trend analysis"""
    history_path = Path(history_dir)
    history_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    history_file = history_path / f"result_{timestamp}.json"
    
    try:
        history_file.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"警告: 无法保存历史记录: {e}", file=sys.stderr)


def _export_pdf(html: str, output_path: str) -> bool:
    """Export HTML report to PDF"""
    try:
        # Try pdfkit first (requires wkhtmltopdf)
        import pdfkit
        pdfkit.from_string(html, output_path)
        return True
    except ImportError:
        pass
    except Exception as e:
        print(f"pdfkit 导出失败: {e}", file=sys.stderr)
    
    try:
        # Try weasyprint as fallback
        from weasyprint import HTML
        HTML(string=html).write_pdf(output_path)
        return True
    except ImportError:
        pass
    except Exception as e:
        print(f"weasyprint 导出失败: {e}", file=sys.stderr)
    
    return False
