"""HTML 报告生成器单元测试"""

import base64
import math
import os
import sys
import tempfile
from datetime import datetime

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from report.data_model import (
    CaseReport,
    EnvironmentInfo,
    PhaseReport,
    ReportData,
    RunSummary,
    StepReport,
)
from report.generator import (
    ReportGenerator,
    _escape_html,
    _format_duration,
    _format_datetime,
    _generate_pie_chart_svg,
    _generate_bar_chart_svg,
    _generate_timeline,
    _read_screenshot_as_base64,
)


# ------------------------------------------------------------------
# 辅助工厂方法
# ------------------------------------------------------------------


def _make_step(index=1, action="click", model="btn", data="", status="ok",
               duration=0.1, screenshot=None, error=None):
    """创建测试用 StepReport"""
    return StepReport(
        index=index, action=action, model=model, data=data,
        status=status, duration=duration, screenshot=screenshot, error=error,
    )


def _make_phase(name="test_case", steps=None, status="ok", duration=1.0):
    """创建测试用 PhaseReport"""
    return PhaseReport(
        name=name, steps=steps or [], status=status, duration=duration,
    )


def _make_case(case_id="TC001", title="登录测试", status="PASS", duration=3.0,
               pre=None, test=None, post=None, description=""):
    """创建测试用 CaseReport"""
    return CaseReport(
        case_id=case_id, title=title, status=status, duration=duration,
        description=description,
        pre_process=pre, test_case=test, post_process=post,
    )


def _make_report(
    run_id="test-run",
    cases=None,
    total=0, passed=0, failed=0, skipped=0, error=0, duration=10.0,
):
    """创建测试用 ReportData（含 summary 和 environment）"""
    if cases is None:
        cases = []
    t = total or len(cases)
    p = passed or sum(1 for c in cases if c.status == "PASS")
    f = failed or sum(1 for c in cases if c.status == "FAIL")
    sk = skipped or sum(1 for c in cases if c.status == "SKIP")
    er = error or sum(1 for c in cases if c.status == "ERROR")
    pr = (p / t * 100) if t > 0 else 0.0

    return ReportData(
        run_id=run_id,
        start_time=datetime(2026, 4, 16, 10, 0, 0),
        end_time=datetime(2026, 4, 16, 10, 5, 0),
        duration=duration,
        environment=EnvironmentInfo(
            os_name="Darwin", os_version="25.3.0",
            python_version="3.11.0", rodski_version="5.7.0",
        ),
        summary=RunSummary(
            total=t, passed=p, failed=f, skipped=sk, error=er,
            pass_rate=round(pr, 2), duration=duration,
        ),
        cases=cases,
    )


# ==================================================================
# 辅助函数测试
# ==================================================================


class TestEscapeHtml:
    """HTML 转义函数测试"""

    def test_plain_text_unchanged(self):
        """普通文本不应被修改"""
        assert _escape_html("hello world") == "hello world"

    def test_angle_brackets(self):
        """尖括号应被转义"""
        assert _escape_html("<script>") == "&lt;script&gt;"

    def test_ampersand(self):
        """& 应被转义"""
        assert _escape_html("a&b") == "a&amp;b"

    def test_quotes(self):
        """引号应被转义"""
        assert "&quot;" in _escape_html('"hello"')
        assert "&#x27;" in _escape_html("it's")

    def test_non_string_input(self):
        """非字符串输入应先转为字符串"""
        assert _escape_html(42) == "42"


class TestFormatDuration:
    """耗时格式化函数测试"""

    def test_sub_millisecond(self):
        """亚毫秒应显示 '< 1ms'"""
        assert _format_duration(0.0001) == "< 1ms"

    def test_milliseconds(self):
        """毫秒范围应显示 'xxxms'"""
        assert _format_duration(0.5) == "500ms"
        assert _format_duration(0.123) == "123ms"

    def test_seconds(self):
        """秒范围应显示 'x.xxs'"""
        assert _format_duration(5.12) == "5.12s"
        assert _format_duration(59.99) == "59.99s"

    def test_minutes(self):
        """超过 60 秒应显示 'xm x.xs'"""
        result = _format_duration(125.3)
        assert "2m" in result
        assert "5.3s" in result

    def test_zero(self):
        """零应显示 '< 1ms'"""
        assert _format_duration(0) == "< 1ms"


class TestFormatDatetime:
    """日期时间格式化函数测试"""

    def test_none_returns_dash(self):
        """None 应返回 '-'"""
        assert _format_datetime(None) == "-"

    def test_datetime_formatted(self):
        """datetime 应格式化为标准格式"""
        dt = datetime(2026, 4, 16, 10, 30, 45)
        assert _format_datetime(dt) == "2026-04-16 10:30:45"


class TestReadScreenshotAsBase64:
    """截图 base64 编码测试"""

    def test_none_path(self):
        """路径为 None 时返回 None"""
        assert _read_screenshot_as_base64(None) is None

    def test_empty_path(self):
        """空路径返回 None"""
        assert _read_screenshot_as_base64("") is None

    def test_nonexistent_file(self):
        """不存在的文件返回 None"""
        assert _read_screenshot_as_base64("/nonexistent/file.png") is None

    def test_valid_png(self):
        """有效的 PNG 文件应返回 data URI"""
        # 创建一个最小的 PNG（1x1 像素白色）
        png_data = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
            b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
            b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(png_data)
            f.flush()
            path = f.name
        try:
            result = _read_screenshot_as_base64(path)
            assert result is not None
            assert result.startswith("data:image/png;base64,")
            # 验证 base64 编码正确
            b64_part = result.split(",", 1)[1]
            decoded = base64.b64decode(b64_part)
            assert decoded == png_data
        finally:
            os.unlink(path)

    def test_jpg_mime_type(self):
        """JPG 文件应使用 image/jpeg MIME 类型"""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"\xff\xd8\xff")  # 简单的 JPEG 头
            f.flush()
            path = f.name
        try:
            result = _read_screenshot_as_base64(path)
            assert result is not None
            assert result.startswith("data:image/jpeg;base64,")
        finally:
            os.unlink(path)


# ==================================================================
# SVG 饼图测试
# ==================================================================


class TestPieChartSvg:
    """SVG 饼图生成测试"""

    def test_all_zeros_shows_empty(self):
        """所有值为零时应显示空状态"""
        svg = _generate_pie_chart_svg([0, 0, 0, 0], ["#a", "#b", "#c", "#d"])
        assert "<svg" in svg
        assert "No Data" in svg

    def test_single_category(self):
        """只有一个类别时应显示完整圆"""
        svg = _generate_pie_chart_svg(
            [10, 0, 0, 0],
            ["#4caf50", "#f44336", "#9e9e9e", "#ff9800"],
        )
        assert "<svg" in svg
        assert "<circle" in svg  # 完整圆用 circle 元素

    def test_two_categories(self):
        """两个类别时应显示两个扇形"""
        svg = _generate_pie_chart_svg(
            [7, 3, 0, 0],
            ["#4caf50", "#f44336", "#9e9e9e", "#ff9800"],
        )
        assert "<svg" in svg
        assert "<path" in svg
        assert "#4caf50" in svg
        assert "#f44336" in svg

    def test_all_four_categories(self):
        """四个类别都有值时应显示四个扇形"""
        svg = _generate_pie_chart_svg(
            [5, 2, 2, 1],
            ["#4caf50", "#f44336", "#9e9e9e", "#ff9800"],
            labels=["PASS", "FAIL", "SKIP", "ERROR"],
        )
        assert "<svg" in svg
        assert "#4caf50" in svg
        assert "#f44336" in svg
        assert "#9e9e9e" in svg
        assert "#ff9800" in svg

    def test_custom_size(self):
        """可自定义 SVG 尺寸"""
        svg = _generate_pie_chart_svg(
            [5, 5], ["#aaa", "#bbb"], size=300,
        )
        assert 'width="300"' in svg
        assert 'height="300"' in svg

    def test_pass_rate_label(self):
        """传入 labels 时应在中心显示通过率"""
        svg = _generate_pie_chart_svg(
            [8, 2, 0, 0],
            ["#4caf50", "#f44336", "#9e9e9e", "#ff9800"],
            labels=["PASS", "FAIL", "SKIP", "ERROR"],
        )
        assert "80%" in svg
        assert "Pass Rate" in svg


# ==================================================================
# SVG 柱状图测试
# ==================================================================


class TestBarChartSvg:
    """SVG 柱状图生成测试"""

    def test_empty_data(self):
        """空数据应显示空状态"""
        svg = _generate_bar_chart_svg([])
        assert "<svg" in svg
        assert "No Data" in svg

    def test_single_bar(self):
        """单个柱状图应正确渲染"""
        svg = _generate_bar_chart_svg([("TC001", 2.5)])
        assert "<svg" in svg
        assert "<rect" in svg
        assert "TC001" in svg

    def test_multiple_bars(self):
        """多个柱状图应全部渲染"""
        data = [("TC001", 1.0), ("TC002", 5.5), ("TC003", 20.0)]
        svg = _generate_bar_chart_svg(data)
        assert "TC001" in svg
        assert "TC002" in svg
        assert "TC003" in svg

    def test_long_labels_truncated(self):
        """超长标签应被截断"""
        svg = _generate_bar_chart_svg(
            [("very_long_case_id_that_exceeds_limit_significantly", 1.0)],
            max_label_len=10,
        )
        assert "..." in svg

    def test_color_by_duration(self):
        """柱子颜色应根据耗时区分"""
        svg = _generate_bar_chart_svg([
            ("fast", 1.0),    # 绿色 (#4caf50)
            ("medium", 10.0), # 橙色 (#ff9800)
            ("slow", 30.0),   # 红色 (#f44336)
        ])
        assert "#4caf50" in svg
        assert "#ff9800" in svg
        assert "#f44336" in svg

    def test_zero_values(self):
        """所有值为零时不应报错"""
        svg = _generate_bar_chart_svg([("TC001", 0.0), ("TC002", 0.0)])
        assert "<svg" in svg


# ==================================================================
# 时间线测试
# ==================================================================


class TestTimeline:
    """三阶段时间线 HTML 生成测试"""

    def test_no_phases(self):
        """无阶段时应显示占位"""
        case = _make_case()
        html = _generate_timeline(case)
        assert "No phases" in html

    def test_single_phase(self):
        """单阶段应正确渲染"""
        case = _make_case(
            test=_make_phase("test_case", duration=5.0),
        )
        html = _generate_timeline(case)
        assert "test_case" in html
        assert "#ff9800" in html  # test_case 颜色

    def test_three_phases(self):
        """三个阶段应全部渲染且颜色正确"""
        case = _make_case(
            pre=_make_phase("pre_process", duration=1.0),
            test=_make_phase("test_case", duration=3.0),
            post=_make_phase("post_process", duration=1.0),
        )
        html = _generate_timeline(case)
        assert "pre_process" in html
        assert "test_case" in html
        assert "post_process" in html
        assert "#2196f3" in html  # pre_process
        assert "#ff9800" in html  # test_case
        assert "#9c27b0" in html  # post_process


# ==================================================================
# ReportGenerator 核心测试
# ==================================================================


class TestReportGeneratorGenerate:
    """ReportGenerator.generate() 方法测试"""

    def test_generate_creates_index_html(self):
        """generate 应在输出目录创建 index.html"""
        report = _make_report(cases=[
            _make_case("TC001", "用例一", "PASS", 2.0),
        ])
        gen = ReportGenerator(report)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = gen.generate(tmpdir)
            assert os.path.isfile(path)
            assert path.endswith("index.html")

    def test_generate_creates_output_dir(self):
        """generate 应自动创建不存在的输出目录"""
        report = _make_report()
        gen = ReportGenerator(report)
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = os.path.join(tmpdir, "sub", "dir")
            path = gen.generate(nested)
            assert os.path.isfile(path)

    def test_generate_returns_path(self):
        """generate 应返回 index.html 的完整路径"""
        report = _make_report()
        gen = ReportGenerator(report)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = gen.generate(tmpdir)
            assert path == os.path.join(tmpdir, "index.html")

    def test_generated_html_is_valid_structure(self):
        """生成的 HTML 应包含完整的文档结构"""
        report = _make_report(cases=[
            _make_case("TC001", "用例一", "PASS", 2.0),
        ])
        gen = ReportGenerator(report)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = gen.generate(tmpdir)
            with open(path, "r", encoding="utf-8") as f:
                html = f.read()
            assert "<!DOCTYPE html>" in html
            assert "<html" in html
            assert "</html>" in html
            assert "<head>" in html
            assert "<body>" in html
            assert "<style>" in html
            assert "<script>" in html

    def test_generated_html_contains_run_info(self):
        """生成的 HTML 应包含运行信息"""
        report = _make_report(run_id="my-run-123")
        gen = ReportGenerator(report)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = gen.generate(tmpdir)
            with open(path, "r", encoding="utf-8") as f:
                html = f.read()
            assert "my-run-123" in html
            assert "2026-04-16" in html

    def test_generated_html_contains_environment(self):
        """生成的 HTML 应包含环境信息"""
        report = _make_report()
        gen = ReportGenerator(report)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = gen.generate(tmpdir)
            with open(path, "r", encoding="utf-8") as f:
                html = f.read()
            assert "Darwin" in html
            assert "3.11.0" in html  # Python version
            assert "5.7.0" in html  # RodSki version


class TestReportGeneratorOverview:
    """总览页面渲染测试"""

    def test_overview_contains_statistics(self):
        """总览应包含所有统计数字"""
        cases = [
            _make_case("TC001", "通过用例", "PASS", 1.0),
            _make_case("TC002", "失败用例", "FAIL", 2.0),
            _make_case("TC003", "跳过用例", "SKIP", 0.5),
        ]
        report = _make_report(cases=cases)
        gen = ReportGenerator(report)
        html = gen._render_overview()
        # 检查统计数字
        assert ">3<" in html  # total
        assert "Passed" in html
        assert "Failed" in html
        assert "Skipped" in html

    def test_overview_contains_pie_chart(self):
        """总览应包含饼图 SVG"""
        cases = [_make_case("TC001", status="PASS")]
        report = _make_report(cases=cases)
        gen = ReportGenerator(report)
        html = gen._render_overview()
        assert "<svg" in html
        assert "Pass Rate" in html.lower() or "pass rate" in html.lower() or "Pass Rate" in html

    def test_overview_contains_bar_chart(self):
        """总览应包含柱状图 SVG"""
        cases = [
            _make_case("TC001", duration=1.0),
            _make_case("TC002", duration=5.0),
        ]
        report = _make_report(cases=cases)
        gen = ReportGenerator(report)
        html = gen._render_overview()
        assert "Duration by Case" in html
        assert "<rect" in html

    def test_overview_contains_case_table(self):
        """总览应包含用例列表表格"""
        cases = [
            _make_case("TC001", "登录", "PASS", 1.5),
            _make_case("TC002", "注册", "FAIL", 3.2),
        ]
        report = _make_report(cases=cases)
        gen = ReportGenerator(report)
        html = gen._render_overview()
        assert "TC001" in html
        assert "TC002" in html
        assert "登录" in html
        assert "注册" in html

    def test_overview_case_links_to_detail(self):
        """用例表中的 case_id 应链接到详情 section"""
        cases = [_make_case("TC001")]
        report = _make_report(cases=cases)
        gen = ReportGenerator(report)
        html = gen._render_overview()
        assert 'href="#case-TC001"' in html

    def test_overview_status_badges(self):
        """用例表中应使用状态徽章"""
        cases = [
            _make_case("TC001", status="PASS"),
            _make_case("TC002", status="FAIL"),
        ]
        report = _make_report(cases=cases)
        gen = ReportGenerator(report)
        html = gen._render_overview()
        assert "status-PASS" in html
        assert "status-FAIL" in html

    def test_overview_filter_buttons(self):
        """总览应包含状态筛选按钮"""
        report = _make_report(cases=[_make_case()])
        gen = ReportGenerator(report)
        html = gen._render_overview()
        assert 'data-status="PASS"' in html
        assert 'data-status="FAIL"' in html
        assert 'data-status="SKIP"' in html
        assert 'data-status="ERROR"' in html

    def test_overview_no_summary(self):
        """没有 summary 时不应报错"""
        report = ReportData(run_id="no-summary")
        report.summary = None
        gen = ReportGenerator(report)
        html = gen._render_overview()
        assert "RodSki Test Report" in html

    def test_overview_no_environment(self):
        """没有 environment 时不应报错"""
        report = _make_report()
        report.environment = None
        gen = ReportGenerator(report)
        html = gen._render_overview()
        assert "RodSki Test Report" in html


class TestReportGeneratorCaseDetail:
    """用例详情渲染测试"""

    def test_case_detail_shows_case_info(self):
        """用例详情应显示基本信息"""
        case = _make_case("TC001", "登录测试", "PASS", 3.0, description="验证登录功能")
        report = _make_report(cases=[case])
        gen = ReportGenerator(report)
        html = gen._render_case_detail(case)
        assert "TC001" in html
        assert "登录测试" in html
        assert "验证登录功能" in html
        assert "status-PASS" in html

    def test_case_detail_shows_timeline(self):
        """用例详情应显示三阶段时间线"""
        case = _make_case(
            pre=_make_phase("pre_process", duration=0.5),
            test=_make_phase("test_case", duration=2.0),
            post=_make_phase("post_process", duration=0.3),
        )
        report = _make_report(cases=[case])
        gen = ReportGenerator(report)
        html = gen._render_case_detail(case)
        assert "timeline" in html
        assert "pre_process" in html
        assert "test_case" in html
        assert "post_process" in html

    def test_case_detail_shows_steps(self):
        """用例详情应显示步骤表格"""
        steps = [
            _make_step(1, "open", "url", "http://localhost"),
            _make_step(2, "type", "username", "admin"),
            _make_step(3, "click", "login_btn"),
        ]
        case = _make_case(
            test=_make_phase("test_case", steps=steps),
        )
        report = _make_report(cases=[case])
        gen = ReportGenerator(report)
        html = gen._render_case_detail(case)
        assert "open" in html
        assert "type" in html
        assert "click" in html
        assert "username" in html

    def test_case_detail_error_step_highlighted(self):
        """失败步骤应被高亮"""
        steps = [
            _make_step(1, "verify", "title", "Expected", status="fail", error="标题不匹配"),
        ]
        case = _make_case(
            status="FAIL",
            test=_make_phase("test_case", steps=steps, status="fail"),
        )
        report = _make_report(cases=[case])
        gen = ReportGenerator(report)
        html = gen._render_case_detail(case)
        assert "error-row" in html
        assert "标题不匹配" in html
        assert "error-msg" in html

    def test_case_detail_collapsible_phases(self):
        """阶段应可折叠"""
        case = _make_case(
            pre=_make_phase("pre_process"),
            test=_make_phase("test_case"),
        )
        report = _make_report(cases=[case])
        gen = ReportGenerator(report)
        html = gen._render_case_detail(case)
        assert "collapsible" in html
        assert "collapse-content" in html

    def test_case_detail_test_case_phase_open_by_default(self):
        """test_case 阶段应默认展开"""
        case = _make_case(
            pre=_make_phase("pre_process", status="ok"),
            test=_make_phase("test_case", status="ok"),
        )
        report = _make_report(cases=[case])
        gen = ReportGenerator(report)
        html = gen._render_case_detail(case)
        # test_case 的 collapsible 应有 open class
        # pre_process 不是 test_case 也不是 fail，不应默认展开
        assert "collapsible open" in html

    def test_case_detail_failed_phase_open_by_default(self):
        """失败的阶段应默认展开"""
        case = _make_case(
            pre=_make_phase("pre_process", status="fail"),
        )
        report = _make_report(cases=[case])
        gen = ReportGenerator(report)
        html = gen._render_case_detail(case)
        assert "collapsible open" in html

    def test_case_detail_anchor_id(self):
        """用例详情应有正确的锚点 ID"""
        case = _make_case("TC001")
        report = _make_report(cases=[case])
        gen = ReportGenerator(report)
        html = gen._render_case_detail(case)
        assert 'id="case-TC001"' in html

    def test_case_detail_no_phases(self):
        """无阶段的用例详情不应报错"""
        case = _make_case("TC001")
        report = _make_report(cases=[case])
        gen = ReportGenerator(report)
        html = gen._render_case_detail(case)
        assert "TC001" in html


class TestReportGeneratorScreenshots:
    """截图处理测试"""

    def test_screenshot_in_normal_mode(self):
        """普通模式下截图使用文件路径"""
        steps = [
            _make_step(1, "click", "btn", screenshot="/tmp/shot.png"),
        ]
        case = _make_case(test=_make_phase("test_case", steps=steps))
        report = _make_report(cases=[case])
        gen = ReportGenerator(report)
        html = gen._render_case_detail(case, single_file=False)
        assert "screenshot-thumb" in html
        assert "/tmp/shot.png" in html

    def test_screenshot_in_single_file_mode_nonexistent(self):
        """单文件模式下不存在的截图应显示路径文本"""
        steps = [
            _make_step(1, "click", "btn", screenshot="/nonexistent/shot.png"),
        ]
        case = _make_case(test=_make_phase("test_case", steps=steps))
        report = _make_report(cases=[case])
        gen = ReportGenerator(report)
        html = gen._render_case_detail(case, single_file=True)
        assert "/nonexistent/shot.png" in html

    def test_screenshot_in_single_file_mode_with_real_file(self):
        """单文件模式下存在的截图应 base64 内联"""
        png_data = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
            b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
            b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(png_data)
            f.flush()
            path = f.name
        try:
            steps = [_make_step(1, "click", "btn", screenshot=path)]
            case = _make_case(test=_make_phase("test_case", steps=steps))
            report = _make_report(cases=[case])
            gen = ReportGenerator(report)
            html = gen._render_case_detail(case, single_file=True)
            assert "data:image/png;base64," in html
            assert "screenshot-thumb" in html
        finally:
            os.unlink(path)

    def test_no_screenshot(self):
        """无截图时不应显示图片"""
        steps = [_make_step(1, "click", "btn")]
        case = _make_case(test=_make_phase("test_case", steps=steps))
        report = _make_report(cases=[case])
        gen = ReportGenerator(report)
        html = gen._render_case_detail(case)
        assert "screenshot-thumb" not in html


class TestReportGeneratorFullReport:
    """完整报告端到端测试"""

    def test_full_report_with_mixed_statuses(self):
        """混合状态的完整报告应正确渲染"""
        steps_pass = [
            _make_step(1, "open", "url", "http://test.com"),
            _make_step(2, "verify", "title", "Home", status="ok"),
        ]
        steps_fail = [
            _make_step(1, "open", "url", "http://test.com"),
            _make_step(2, "type", "search", "keyword"),
            _make_step(3, "verify", "results", "5 items", status="fail",
                       error="Expected 5 but got 0"),
        ]
        cases = [
            _make_case("TC001", "首页测试", "PASS", 2.0,
                       test=_make_phase("test_case", steps=steps_pass, duration=2.0)),
            _make_case("TC002", "搜索测试", "FAIL", 5.0,
                       pre=_make_phase("pre_process", steps=[_make_step(1, "open", "url")], duration=0.5),
                       test=_make_phase("test_case", steps=steps_fail, status="fail", duration=4.0),
                       post=_make_phase("post_process", steps=[_make_step(1, "close")], duration=0.5)),
            _make_case("TC003", "跳过用例", "SKIP", 0.0),
        ]
        report = _make_report(run_id="full-test", cases=cases, duration=7.0)
        gen = ReportGenerator(report)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = gen.generate(tmpdir)

            with open(path, "r", encoding="utf-8") as f:
                html = f.read()

            # 基本结构
            assert "<!DOCTYPE html>" in html
            assert "full-test" in html

            # 统计
            assert "TC001" in html
            assert "TC002" in html
            assert "TC003" in html

            # 状态
            assert "status-PASS" in html
            assert "status-FAIL" in html
            assert "status-SKIP" in html

            # 错误信息
            assert "Expected 5 but got 0" in html

            # 中文标题
            assert "首页测试" in html
            assert "搜索测试" in html

    def test_full_report_single_file_mode(self):
        """单文件模式的完整报告应可生成"""
        cases = [_make_case("TC001", "测试", "PASS")]
        report = _make_report(cases=cases)
        gen = ReportGenerator(report)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = gen.generate(tmpdir, single_file=True)
            assert os.path.isfile(path)

            with open(path, "r", encoding="utf-8") as f:
                html = f.read()
            assert "<!DOCTYPE html>" in html

    def test_empty_report(self):
        """空报告（无用例）应正常生成"""
        report = _make_report(run_id="empty")
        gen = ReportGenerator(report)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = gen.generate(tmpdir)
            assert os.path.isfile(path)

            with open(path, "r", encoding="utf-8") as f:
                html = f.read()
            assert "empty" in html
            assert "No Data" in html  # 饼图和柱状图都应显示空状态

    def test_html_encoding_utf8(self):
        """生成的 HTML 文件应使用 UTF-8 编码"""
        report = _make_report(cases=[_make_case("TC001", "中文标题")])
        gen = ReportGenerator(report)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = gen.generate(tmpdir)
            with open(path, "r", encoding="utf-8") as f:
                html = f.read()
            assert "charset=\"UTF-8\"" in html or "charset=UTF-8" in html
            assert "中文标题" in html

    def test_html_has_responsive_viewport(self):
        """生成的 HTML 应包含响应式 viewport meta"""
        report = _make_report()
        gen = ReportGenerator(report)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = gen.generate(tmpdir)
            with open(path, "r", encoding="utf-8") as f:
                html = f.read()
            assert "viewport" in html
            assert "width=device-width" in html

    def test_html_has_overlay_for_screenshots(self):
        """生成的 HTML 应包含截图全屏遮罩层"""
        report = _make_report()
        gen = ReportGenerator(report)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = gen.generate(tmpdir)
            with open(path, "r", encoding="utf-8") as f:
                html = f.read()
            assert "screenshotOverlay" in html

    def test_xss_prevention(self):
        """用例数据中的 HTML 特殊字符应被转义"""
        steps = [
            _make_step(1, "type", "input", '<script>alert("xss")</script>'),
        ]
        case = _make_case(
            "TC<XSS>", "<b>Title</b>", "PASS",
            test=_make_phase("test_case", steps=steps),
        )
        report = _make_report(cases=[case])
        gen = ReportGenerator(report)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = gen.generate(tmpdir)
            with open(path, "r", encoding="utf-8") as f:
                html = f.read()
            # 原始标签不应出现
            assert "<script>alert" not in html
            assert "<b>Title</b>" not in html
            # 转义后的版本应存在
            assert "&lt;script&gt;" in html
            assert "&lt;b&gt;" in html


class TestReportGeneratorPieChartMethod:
    """ReportGenerator._generate_pie_chart_svg 实例方法测试"""

    def test_method_delegates_correctly(self):
        """实例方法应正确委托到模块级函数"""
        report = _make_report()
        gen = ReportGenerator(report)
        svg = gen._generate_pie_chart_svg(8, 1, 1, 0)
        assert "<svg" in svg
        assert "#4caf50" in svg  # PASS 颜色

    def test_method_all_pass(self):
        """全部通过时应显示 100% 通过率"""
        report = _make_report()
        gen = ReportGenerator(report)
        svg = gen._generate_pie_chart_svg(10, 0, 0, 0)
        assert "100%" in svg


class TestReportGeneratorBarChartMethod:
    """ReportGenerator._generate_bar_chart_svg 实例方法测试"""

    def test_method_delegates_correctly(self):
        """实例方法应正确委托到模块级函数"""
        report = _make_report()
        gen = ReportGenerator(report)
        svg = gen._generate_bar_chart_svg([("TC001", 2.0)])
        assert "<svg" in svg
        assert "TC001" in svg
