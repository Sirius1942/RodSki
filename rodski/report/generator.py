"""HTML 报告生成器 - 从 ReportData 生成零外部依赖的 HTML 报告

支持两种模式：
    - 多文件模式：index.html + 截图文件引用
    - 单文件模式：所有内容（含截图 base64）内联到一个 HTML 文件
"""

import base64
import math
import os
from datetime import datetime
from pathlib import Path
from string import Template
from typing import List, Optional, Tuple

from .data_model import CaseReport, PhaseReport, ReportData, StepReport


# ---------------------------------------------------------------------------
# 状态颜色常量
# ---------------------------------------------------------------------------
STATUS_COLORS = {
    "PASS": "#4caf50",
    "FAIL": "#f44336",
    "SKIP": "#9e9e9e",
    "ERROR": "#ff9800",
    "ok": "#4caf50",
    "fail": "#f44336",
    "skip": "#9e9e9e",
}

PHASE_COLORS = {
    "pre_process": "#2196f3",
    "test_case": "#ff9800",
    "post_process": "#9c27b0",
}


# ---------------------------------------------------------------------------
# CSS 样式
# ---------------------------------------------------------------------------
_CSS = """\
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 "Helvetica Neue", Arial, sans-serif;
    line-height: 1.6; color: #333; background: #f5f5f5; padding: 20px;
}
.container { max-width: 1200px; margin: 0 auto; }
h1 { font-size: 1.8em; margin-bottom: 4px; color: #1a1a2e; }
h2 { font-size: 1.4em; margin: 20px 0 10px; color: #1a1a2e; }
h3 { font-size: 1.15em; margin: 16px 0 8px; color: #333; }
.subtitle { color: #666; font-size: 0.9em; margin-bottom: 20px; }
.card {
    background: #fff; border-radius: 8px; padding: 20px;
    margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
.stats-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 12px; margin: 16px 0;
}
.stat-box {
    text-align: center; padding: 16px; border-radius: 8px;
    background: #fafafa; border: 1px solid #eee;
}
.stat-box .value { font-size: 2em; font-weight: 700; }
.stat-box .label { font-size: 0.85em; color: #666; margin-top: 4px; }
.charts-row { display: flex; gap: 24px; flex-wrap: wrap; align-items: flex-start; }
.chart-container { flex: 0 0 auto; text-align: center; }
.chart-container .chart-title { font-size: 0.9em; color: #666; margin-bottom: 8px; }
.legend { display: flex; gap: 16px; justify-content: center; margin-top: 10px; flex-wrap: wrap; }
.legend-item { display: flex; align-items: center; gap: 4px; font-size: 0.85em; }
.legend-dot { width: 12px; height: 12px; border-radius: 50%; display: inline-block; }
table { width: 100%; border-collapse: collapse; margin-top: 8px; }
th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #eee; }
th { background: #fafafa; font-weight: 600; font-size: 0.9em; color: #555; }
tr:hover { background: #f9f9f9; }
.status-badge {
    display: inline-block; padding: 2px 10px; border-radius: 12px;
    font-size: 0.8em; font-weight: 600; color: #fff;
}
.status-PASS, .status-ok { background: #4caf50; }
.status-FAIL, .status-fail { background: #f44336; }
.status-SKIP, .status-skip { background: #9e9e9e; }
.status-ERROR { background: #ff9800; }
a { color: #1976d2; text-decoration: none; }
a:hover { text-decoration: underline; }
.timeline {
    display: flex; align-items: center; gap: 0; margin: 12px 0;
    border-radius: 6px; overflow: hidden; height: 28px;
}
.timeline-seg {
    height: 100%; display: flex; align-items: center;
    justify-content: center; color: #fff; font-size: 0.75em;
    font-weight: 600; min-width: 40px; position: relative;
}
.timeline-seg .seg-label {
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    padding: 0 6px;
}
.collapsible { cursor: pointer; user-select: none; }
.collapsible::before { content: "\\25B6"; display: inline-block; margin-right: 6px; font-size: 0.7em; transition: transform 0.2s; }
.collapsible.open::before { transform: rotate(90deg); }
.collapse-content { display: none; }
.collapse-content.show { display: block; }
.error-row { background: #fff5f5 !important; }
.error-msg { color: #d32f2f; font-size: 0.85em; margin-top: 4px; }
.screenshot-thumb {
    max-width: 120px; max-height: 80px; border-radius: 4px;
    cursor: pointer; border: 1px solid #ddd; transition: transform 0.2s;
}
.screenshot-thumb:hover { transform: scale(1.05); }
.overlay {
    display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
    background: rgba(0,0,0,0.85); z-index: 1000; justify-content: center;
    align-items: center; cursor: pointer;
}
.overlay.active { display: flex; }
.overlay img { max-width: 95vw; max-height: 95vh; border-radius: 8px; }
.filter-bar { margin: 12px 0; display: flex; gap: 8px; flex-wrap: wrap; }
.filter-btn {
    padding: 4px 14px; border-radius: 16px; border: 1px solid #ddd;
    background: #fff; cursor: pointer; font-size: 0.85em; transition: all 0.2s;
}
.filter-btn:hover { border-color: #999; }
.filter-btn.active { background: #1976d2; color: #fff; border-color: #1976d2; }
.back-link { display: inline-block; margin-bottom: 12px; font-size: 0.9em; }
.case-anchor { scroll-margin-top: 20px; }
@media (max-width: 768px) {
    .charts-row { flex-direction: column; }
    .stats-grid { grid-template-columns: repeat(2, 1fr); }
}
"""

# ---------------------------------------------------------------------------
# JavaScript（原生）
# ---------------------------------------------------------------------------
_JS = """\
document.addEventListener("DOMContentLoaded", function() {
    // 折叠/展开
    document.querySelectorAll(".collapsible").forEach(function(el) {
        el.addEventListener("click", function() {
            this.classList.toggle("open");
            var content = this.nextElementSibling;
            if (content && content.classList.contains("collapse-content")) {
                content.classList.toggle("show");
            }
        });
    });

    // 截图全屏
    var overlay = document.getElementById("screenshotOverlay");
    var overlayImg = document.getElementById("overlayImg");
    document.querySelectorAll(".screenshot-thumb").forEach(function(img) {
        img.addEventListener("click", function() {
            overlayImg.src = this.src;
            overlay.classList.add("active");
        });
    });
    if (overlay) {
        overlay.addEventListener("click", function() {
            overlay.classList.remove("active");
        });
    }

    // 筛选按钮
    document.querySelectorAll(".filter-btn").forEach(function(btn) {
        btn.addEventListener("click", function() {
            var status = this.getAttribute("data-status");
            // 切换 active
            if (this.classList.contains("active")) {
                this.classList.remove("active");
                status = "ALL";
            } else {
                document.querySelectorAll(".filter-btn").forEach(function(b) {
                    b.classList.remove("active");
                });
                this.classList.add("active");
            }
            // 筛选行
            document.querySelectorAll(".case-row").forEach(function(row) {
                if (status === "ALL" || row.getAttribute("data-status") === status) {
                    row.style.display = "";
                } else {
                    row.style.display = "none";
                }
            });
        });
    });
});
"""


def _escape_html(text: str) -> str:
    """转义 HTML 特殊字符"""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def _format_duration(seconds: float) -> str:
    """将秒数格式化为可读字符串"""
    if seconds < 0.001:
        return "< 1ms"
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    if seconds < 60:
        return f"{seconds:.2f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.1f}s"


def _format_datetime(dt: Optional[datetime]) -> str:
    """格式化日期时间"""
    if dt is None:
        return "-"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _read_screenshot_as_base64(path: str) -> Optional[str]:
    """读取截图文件并编码为 base64 data URI"""
    if not path or not os.path.isfile(path):
        return None
    ext = Path(path).suffix.lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }
    mime = mime_map.get(ext, "image/png")
    try:
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode("ascii")
        return f"data:{mime};base64,{data}"
    except OSError:
        return None


# ===================================================================
# SVG 图表生成
# ===================================================================


def _generate_pie_chart_svg(
    values: List[int],
    colors: List[str],
    labels: Optional[List[str]] = None,
    size: int = 200,
) -> str:
    """生成纯 SVG 饼图

    Args:
        values: 各扇区数值列表
        colors: 各扇区颜色列表
        labels: 各扇区标签（可选）
        size: SVG 尺寸（正方形）

    Returns:
        SVG 字符串
    """
    total = sum(values)
    if total == 0:
        # 空状态：灰色圆圈
        cx, cy, r = size / 2, size / 2, size / 2 - 10
        return (
            f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#e0e0e0"/>'
            f'<text x="{cx}" y="{cy}" text-anchor="middle" '
            f'dominant-baseline="central" fill="#999" font-size="14">No Data</text>'
            f"</svg>"
        )

    cx, cy = size / 2, size / 2
    r = size / 2 - 10
    paths: List[str] = []
    start_angle = -math.pi / 2  # 从 12 点方向开始

    for i, (value, color) in enumerate(zip(values, colors)):
        if value == 0:
            continue
        sweep = (value / total) * 2 * math.pi

        # 如果只有一个非零值，绘制完整圆
        if sweep >= 2 * math.pi - 0.0001:
            paths.append(
                f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}"/>'
            )
            start_angle += sweep
            continue

        end_angle = start_angle + sweep
        x1 = cx + r * math.cos(start_angle)
        y1 = cy + r * math.sin(start_angle)
        x2 = cx + r * math.cos(end_angle)
        y2 = cy + r * math.sin(end_angle)
        large_arc = 1 if sweep > math.pi else 0
        path = (
            f'<path d="M{cx:.2f},{cy:.2f} L{x1:.2f},{y1:.2f} '
            f"A{r:.2f},{r:.2f} 0 {large_arc},1 {x2:.2f},{y2:.2f} Z\" "
            f'fill="{color}"/>'
        )
        paths.append(path)
        start_angle = end_angle

    # 中心显示通过率文字
    center_text = ""
    if labels and len(values) > 0 and values[0] > 0:
        pct = values[0] / total * 100
        center_text = (
            f'<text x="{cx}" y="{cy - 6}" text-anchor="middle" '
            f'font-size="20" font-weight="700" fill="#333">{pct:.0f}%</text>'
            f'<text x="{cx}" y="{cy + 14}" text-anchor="middle" '
            f'font-size="11" fill="#666">Pass Rate</text>'
        )

    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
        f'{"".join(paths)}{center_text}</svg>'
    )


def _generate_bar_chart_svg(
    data: List[Tuple[str, float]],
    width: int = 500,
    bar_height: int = 24,
    max_label_len: int = 16,
) -> str:
    """生成纯 SVG 水平柱状图（用例耗时分布）

    Args:
        data: [(label, value), ...] 列表
        width: SVG 宽度
        bar_height: 每根柱高度
        max_label_len: 标签最大字符数

    Returns:
        SVG 字符串
    """
    if not data:
        return (
            f'<svg width="{width}" height="40" viewBox="0 0 {width} 40">'
            f'<text x="{width // 2}" y="20" text-anchor="middle" '
            f'fill="#999" font-size="13">No Data</text></svg>'
        )

    label_area = 130
    chart_area = width - label_area - 70  # 右侧留出数字空间
    gap = 6
    top_padding = 4
    row_height = bar_height + gap
    height = top_padding + len(data) * row_height + 4

    max_val = max(v for _, v in data) if data else 1
    if max_val == 0:
        max_val = 1

    bars: List[str] = []
    for i, (label, value) in enumerate(data):
        y = top_padding + i * row_height
        truncated = label[:max_label_len] + ("..." if len(label) > max_label_len else "")
        bar_w = max((value / max_val) * chart_area, 2)

        # 根据耗时着色
        if value < 5:
            color = "#4caf50"
        elif value < 15:
            color = "#ff9800"
        else:
            color = "#f44336"

        bars.append(
            f'<text x="{label_area - 8}" y="{y + bar_height / 2 + 1}" '
            f'text-anchor="end" dominant-baseline="central" '
            f'font-size="12" fill="#555">{_escape_html(truncated)}</text>'
            f'<rect x="{label_area}" y="{y}" width="{bar_w:.1f}" '
            f'height="{bar_height}" rx="4" fill="{color}" opacity="0.85"/>'
            f'<text x="{label_area + bar_w + 6}" y="{y + bar_height / 2 + 1}" '
            f'dominant-baseline="central" font-size="11" fill="#666">'
            f"{_format_duration(value)}</text>"
        )

    return (
        f'<svg width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">{"".join(bars)}</svg>'
    )


# ===================================================================
# 时间线 SVG
# ===================================================================


def _generate_timeline(case: CaseReport) -> str:
    """生成三阶段时间线 HTML"""
    phases = []
    for name, phase in [
        ("pre_process", case.pre_process),
        ("test_case", case.test_case),
        ("post_process", case.post_process),
    ]:
        if phase is not None:
            phases.append((name, phase.duration))

    if not phases:
        return '<div class="timeline"><div class="timeline-seg" style="background:#ccc;flex:1;"><span class="seg-label">No phases</span></div></div>'

    total = sum(d for _, d in phases) or 1
    parts = []
    for name, dur in phases:
        color = PHASE_COLORS.get(name, "#757575")
        pct = max(dur / total * 100, 5)  # 最小 5% 可见
        label = f"{name} ({_format_duration(dur)})"
        parts.append(
            f'<div class="timeline-seg" style="background:{color};flex:{pct:.1f};">'
            f'<span class="seg-label">{_escape_html(label)}</span></div>'
        )
    return f'<div class="timeline">{"".join(parts)}</div>'


# ===================================================================
# ReportGenerator
# ===================================================================


class ReportGenerator:
    """从 ReportData 生成 HTML 报告"""

    def __init__(self, report_data: ReportData):
        self.data = report_data

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    def generate(self, output_dir: str, single_file: bool = False) -> str:
        """生成 HTML 报告

        Args:
            output_dir: 输出目录
            single_file: True 则生成单文件 HTML（截图 base64 内联）

        Returns:
            报告主页路径
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        html = self._render_full_report(single_file=single_file)
        output_path = os.path.join(output_dir, "index.html")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        return output_path

    # ------------------------------------------------------------------
    # 渲染方法
    # ------------------------------------------------------------------

    def _render_full_report(self, single_file: bool = False) -> str:
        """渲染完整的单页报告"""
        overview = self._render_overview()
        case_sections = []
        for case in self.data.cases:
            case_sections.append(
                self._render_case_detail(case, single_file=single_file)
            )
        cases_html = "\n".join(case_sections)

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RodSki Test Report - {_escape_html(self.data.run_id)}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="container">
{overview}
{cases_html}
</div>
<div id="screenshotOverlay" class="overlay">
<img id="overlayImg" src="" alt="screenshot"/>
</div>
<script>{_JS}</script>
</body>
</html>"""

    def _render_overview(self) -> str:
        """渲染总览部分：运行信息 + 饼图 + 统计 + 用例列表"""
        summary = self.data.summary
        env = self.data.environment

        # -- 运行信息 --
        env_info = ""
        if env:
            parts = [f"OS: {env.os_name} {env.os_version}"]
            parts.append(f"Python: {env.python_version}")
            if env.rodski_version:
                parts.append(f"RodSki: {env.rodski_version}")
            if env.browser:
                browser_str = env.browser
                if env.browser_version:
                    browser_str += f" {env.browser_version}"
                parts.append(f"Browser: {browser_str}")
            env_info = " | ".join(parts)

        # -- 统计数字 --
        total = summary.total if summary else 0
        passed = summary.passed if summary else 0
        failed = summary.failed if summary else 0
        skipped = summary.skipped if summary else 0
        error = summary.error if summary else 0
        pass_rate = summary.pass_rate if summary else 0.0
        duration = summary.duration if summary else self.data.duration

        # -- 饼图 SVG --
        pie_svg = self._generate_pie_chart_svg(passed, failed, skipped, error)

        # -- 柱状图 SVG --
        bar_data = [
            (c.case_id or c.title or f"Case {i + 1}", c.duration)
            for i, c in enumerate(self.data.cases)
        ]
        bar_svg = self._generate_bar_chart_svg(bar_data)

        # -- 统计卡片 --
        stats_html = f"""
<div class="stats-grid">
    <div class="stat-box"><div class="value" style="color:#333;">{total}</div><div class="label">Total</div></div>
    <div class="stat-box"><div class="value" style="color:#4caf50;">{passed}</div><div class="label">Passed</div></div>
    <div class="stat-box"><div class="value" style="color:#f44336;">{failed}</div><div class="label">Failed</div></div>
    <div class="stat-box"><div class="value" style="color:#9e9e9e;">{skipped}</div><div class="label">Skipped</div></div>
    <div class="stat-box"><div class="value" style="color:#ff9800;">{error}</div><div class="label">Error</div></div>
    <div class="stat-box"><div class="value" style="color:#1976d2;">{pass_rate:.1f}%</div><div class="label">Pass Rate</div></div>
    <div class="stat-box"><div class="value" style="color:#555;">{_format_duration(duration)}</div><div class="label">Duration</div></div>
</div>"""

        # -- 图例 --
        legend_html = """
<div class="legend">
    <span class="legend-item"><span class="legend-dot" style="background:#4caf50;"></span> PASS</span>
    <span class="legend-item"><span class="legend-dot" style="background:#f44336;"></span> FAIL</span>
    <span class="legend-item"><span class="legend-dot" style="background:#9e9e9e;"></span> SKIP</span>
    <span class="legend-item"><span class="legend-dot" style="background:#ff9800;"></span> ERROR</span>
</div>"""

        # -- 用例表格 --
        filter_bar = """
<div class="filter-bar">
    <button class="filter-btn" data-status="PASS">PASS</button>
    <button class="filter-btn" data-status="FAIL">FAIL</button>
    <button class="filter-btn" data-status="SKIP">SKIP</button>
    <button class="filter-btn" data-status="ERROR">ERROR</button>
</div>"""

        rows = []
        for i, case in enumerate(self.data.cases):
            cid = _escape_html(case.case_id or f"Case {i + 1}")
            title = _escape_html(case.title or "-")
            status = case.status
            dur = _format_duration(case.duration)
            anchor = f"case-{case.case_id or i}"
            rows.append(
                f'<tr class="case-row" data-status="{status}">'
                f"<td>{i + 1}</td>"
                f'<td><a href="#{anchor}">{cid}</a></td>'
                f"<td>{title}</td>"
                f'<td><span class="status-badge status-{status}">{status}</span></td>'
                f"<td>{dur}</td>"
                f"</tr>"
            )

        case_table = f"""
{filter_bar}
<table>
<thead><tr><th>#</th><th>Case ID</th><th>Title</th><th>Status</th><th>Duration</th></tr></thead>
<tbody>
{"".join(rows)}
</tbody>
</table>"""

        return f"""
<div class="card">
    <h1>RodSki Test Report</h1>
    <div class="subtitle">
        Run ID: {_escape_html(self.data.run_id)} |
        Start: {_format_datetime(self.data.start_time)} |
        End: {_format_datetime(self.data.end_time)}
        {(' | ' + env_info) if env_info else ''}
    </div>
    {stats_html}
    <div class="charts-row">
        <div class="chart-container">
            <div class="chart-title">Pass Rate</div>
            {pie_svg}
            {legend_html}
        </div>
        <div class="chart-container" style="flex:1;min-width:300px;">
            <div class="chart-title">Duration by Case</div>
            {bar_svg}
        </div>
    </div>
</div>
<div class="card">
    <h2>Test Cases</h2>
    {case_table}
</div>"""

    def _render_case_detail(
        self, case: CaseReport, single_file: bool = False
    ) -> str:
        """渲染单个用例详情 section"""
        anchor = f"case-{case.case_id or ''}"
        cid = _escape_html(case.case_id or "Unknown")
        title = _escape_html(case.title or "-")
        desc = _escape_html(case.description) if case.description else ""
        status = case.status
        dur = _format_duration(case.duration)

        # 时间线
        timeline_html = _generate_timeline(case)

        # 各阶段步骤表
        phase_sections = []
        for name, phase in [
            ("pre_process", case.pre_process),
            ("test_case", case.test_case),
            ("post_process", case.post_process),
        ]:
            if phase is None:
                continue
            phase_html = self._render_phase(
                name, phase, single_file=single_file
            )
            phase_sections.append(phase_html)

        phases_html = "\n".join(phase_sections)

        desc_html = f'<p style="color:#666;font-size:0.9em;margin:4px 0 12px;">{desc}</p>' if desc else ""

        return f"""
<div class="card case-anchor" id="{anchor}">
    <h2>{cid}: {title}
        <span class="status-badge status-{status}" style="vertical-align:middle;margin-left:8px;">{status}</span>
        <span style="font-size:0.7em;color:#999;margin-left:8px;font-weight:400;">{dur}</span>
    </h2>
    {desc_html}
    {timeline_html}
    {phases_html}
</div>"""

    def _render_phase(
        self,
        name: str,
        phase: PhaseReport,
        single_file: bool = False,
    ) -> str:
        """渲染单个阶段（可折叠）"""
        color = PHASE_COLORS.get(name, "#757575")
        phase_status = phase.status
        dur = _format_duration(phase.duration)

        rows = []
        for step in phase.steps:
            rows.append(self._render_step_row(step, single_file=single_file))

        is_open = phase_status == "fail" or name == "test_case"
        open_cls = " open" if is_open else ""
        show_cls = " show" if is_open else ""

        return f"""
<div style="margin-top:12px;">
    <h3 class="collapsible{open_cls}" style="color:{color};">
        {_escape_html(name)}
        <span class="status-badge status-{phase_status}" style="font-size:0.75em;vertical-align:middle;margin-left:6px;">{phase_status}</span>
        <span style="font-size:0.75em;color:#999;margin-left:6px;font-weight:400;">{dur}</span>
    </h3>
    <div class="collapse-content{show_cls}">
        <table>
        <thead><tr><th>#</th><th>Action</th><th>Model</th><th>Data</th><th>Status</th><th>Duration</th><th>Screenshot</th></tr></thead>
        <tbody>
        {"".join(rows)}
        </tbody>
        </table>
    </div>
</div>"""

    def _render_step_row(self, step: StepReport, single_file: bool = False) -> str:
        """渲染单个步骤行"""
        row_cls = ' class="error-row"' if step.status == "fail" else ""
        status_badge = f'<span class="status-badge status-{step.status}">{step.status}</span>'
        dur = _format_duration(step.duration)

        # 截图处理
        screenshot_html = ""
        if step.screenshot:
            if single_file:
                data_uri = _read_screenshot_as_base64(step.screenshot)
                if data_uri:
                    screenshot_html = f'<img class="screenshot-thumb" src="{data_uri}" alt="screenshot"/>'
                else:
                    screenshot_html = f'<span style="color:#999;font-size:0.8em;">{_escape_html(step.screenshot)}</span>'
            else:
                screenshot_html = (
                    f'<img class="screenshot-thumb" src="{_escape_html(step.screenshot)}" alt="screenshot"/>'
                )

        # 错误信息
        error_html = ""
        if step.error:
            error_html = f'<div class="error-msg">{_escape_html(step.error)}</div>'

        data_cell = _escape_html(step.data)
        if error_html:
            data_cell += error_html

        return (
            f"<tr{row_cls}>"
            f"<td>{step.index}</td>"
            f"<td>{_escape_html(step.action)}</td>"
            f"<td>{_escape_html(step.model)}</td>"
            f"<td>{data_cell}</td>"
            f"<td>{status_badge}</td>"
            f"<td>{dur}</td>"
            f"<td>{screenshot_html}</td>"
            f"</tr>"
        )

    # ------------------------------------------------------------------
    # 图表方法（委托到模块级函数，方便测试）
    # ------------------------------------------------------------------

    def _generate_pie_chart_svg(
        self, passed: int, failed: int, skipped: int, error: int
    ) -> str:
        """纯 SVG 饼图：用 Python 计算扇形坐标"""
        return _generate_pie_chart_svg(
            values=[passed, failed, skipped, error],
            colors=["#4caf50", "#f44336", "#9e9e9e", "#ff9800"],
            labels=["PASS", "FAIL", "SKIP", "ERROR"],
        )

    def _generate_bar_chart_svg(
        self, data: List[Tuple[str, float]]
    ) -> str:
        """纯 SVG 柱状图：用例耗时分布"""
        return _generate_bar_chart_svg(data)
