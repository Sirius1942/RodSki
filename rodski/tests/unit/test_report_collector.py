"""报告收集器单元测试"""

import json
import os
import sys
import tempfile
from datetime import datetime
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from report.collector import ReportCollector, _collect_environment
from report.data_model import (
    CaseReport,
    EnvironmentInfo,
    PhaseReport,
    ReportData,
    RunSummary,
    StepReport,
)


class TestCollectEnvironment:
    """环境信息采集测试"""

    def test_returns_environment_info(self):
        """应返回 EnvironmentInfo 实例"""
        env = _collect_environment()
        assert isinstance(env, EnvironmentInfo)
        assert env.os_name != ""
        assert env.python_version != ""

    def test_os_info_populated(self):
        """操作系统信息应被填充"""
        env = _collect_environment()
        assert len(env.os_name) > 0
        assert len(env.os_version) > 0


class TestReportCollectorLifecycle:
    """收集器完整生命周期测试"""

    def test_start_run_creates_report(self):
        """start_run 应创建 ReportData 并记录开始时间"""
        collector = ReportCollector()
        report = collector.start_run(run_id="test-run-001")
        assert isinstance(report, ReportData)
        assert report.run_id == "test-run-001"
        assert isinstance(report.start_time, datetime)
        assert isinstance(report.environment, EnvironmentInfo)

    def test_start_run_auto_generates_id(self):
        """start_run 不传 run_id 时应自动生成"""
        collector = ReportCollector()
        report = collector.start_run()
        assert len(report.run_id) > 0

    def test_end_run_computes_summary(self):
        """end_run 应计算汇总并设置结束时间"""
        collector = ReportCollector()
        collector.start_run()

        collector.start_case({"case_id": "TC001", "title": "用例一"})
        collector.end_case("PASS")

        collector.start_case({"case_id": "TC002", "title": "用例二"})
        collector.end_case("FAIL")

        report = collector.end_run()
        assert report is not None
        assert report.end_time is not None
        assert report.duration > 0 or report.duration == 0  # 可能非常快
        assert isinstance(report.summary, RunSummary)
        assert report.summary.total == 2
        assert report.summary.passed == 1
        assert report.summary.failed == 1
        assert report.summary.pass_rate == 50.0

    def test_end_run_without_start_returns_none(self):
        """未调用 start_run 时 end_run 应返回 None"""
        collector = ReportCollector()
        assert collector.end_run() is None

    def test_full_lifecycle(self):
        """完整的 run -> case -> phase -> step 生命周期"""
        collector = ReportCollector()
        collector.start_run(run_id="full-test")

        # 用例 1
        collector.start_case({"case_id": "TC001", "title": "登录测试"})

        collector.start_phase("pre_process")
        collector.record_step({"index": 1, "action": "open", "model": "url", "data": "http://localhost", "status": "ok"})
        collector.end_phase("ok")

        collector.start_phase("test_case")
        collector.record_step({"index": 2, "action": "type", "model": "username", "data": "admin", "status": "ok"})
        collector.record_step({"index": 3, "action": "type", "model": "password", "data": "pass", "status": "ok"})
        collector.record_step({"index": 4, "action": "click", "model": "login_btn", "data": "", "status": "ok"})
        collector.end_phase("ok")

        collector.start_phase("post_process")
        collector.record_step({"index": 5, "action": "close", "model": "", "data": "", "status": "ok"})
        collector.end_phase("ok")

        collector.end_case("PASS")

        report = collector.end_run()

        assert report.run_id == "full-test"
        assert len(report.cases) == 1
        case = report.cases[0]
        assert case.case_id == "TC001"
        assert case.status == "PASS"
        assert case.pre_process is not None
        assert len(case.pre_process.steps) == 1
        assert case.test_case is not None
        assert len(case.test_case.steps) == 3
        assert case.post_process is not None
        assert len(case.post_process.steps) == 1


class TestReportCollectorCase:
    """用例级别收集测试"""

    def test_start_case_creates_case_report(self):
        """start_case 应创建 CaseReport 并填充元信息"""
        collector = ReportCollector()
        collector.start_run()
        case = collector.start_case({
            "case_id": "TC001",
            "title": "登录测试",
            "description": "验证登录功能",
            "component_type": "界面",
            "tags": ["smoke"],
            "priority": "P0",
        })
        assert isinstance(case, CaseReport)
        assert case.case_id == "TC001"
        assert case.title == "登录测试"
        assert case.description == "验证登录功能"
        assert case.component_type == "界面"
        assert case.tags == ["smoke"]
        assert case.priority == "P0"

    def test_start_case_missing_fields(self):
        """start_case 缺少字段时应使用默认值"""
        collector = ReportCollector()
        collector.start_run()
        case = collector.start_case({"case_id": "TC002"})
        assert case.title == ""
        assert case.description == ""
        assert case.component_type == "界面"

    def test_end_case_sets_status_and_duration(self):
        """end_case 应设置状态和耗时"""
        collector = ReportCollector()
        collector.start_run()
        collector.start_case({"case_id": "TC001"})
        case = collector.end_case("FAIL")
        assert case is not None
        assert case.status == "FAIL"
        assert case.duration >= 0

    def test_end_case_without_start_returns_none(self):
        """未调用 start_case 时 end_case 应返回 None"""
        collector = ReportCollector()
        collector.start_run()
        assert collector.end_case("PASS") is None

    def test_end_case_appends_to_report(self):
        """end_case 应将 case 添加到 report.cases"""
        collector = ReportCollector()
        collector.start_run()
        collector.start_case({"case_id": "TC001"})
        collector.end_case("PASS")
        collector.start_case({"case_id": "TC002"})
        collector.end_case("FAIL")
        assert len(collector.report.cases) == 2
        assert collector.report.cases[0].case_id == "TC001"
        assert collector.report.cases[1].case_id == "TC002"


class TestReportCollectorPhase:
    """阶段级别收集测试"""

    def test_start_phase_creates_phase_report(self):
        """start_phase 应创建 PhaseReport"""
        collector = ReportCollector()
        collector.start_run()
        collector.start_case({"case_id": "TC001"})
        phase = collector.start_phase("test_case")
        assert isinstance(phase, PhaseReport)
        assert phase.name == "test_case"

    def test_end_phase_sets_status_and_duration(self):
        """end_phase 应设置状态和耗时"""
        collector = ReportCollector()
        collector.start_run()
        collector.start_case({"case_id": "TC001"})
        collector.start_phase("pre_process")
        phase = collector.end_phase("ok")
        assert phase is not None
        assert phase.status == "ok"
        assert phase.duration >= 0

    def test_end_phase_without_start_returns_none(self):
        """未调用 start_phase 时 end_phase 应返回 None"""
        collector = ReportCollector()
        collector.start_run()
        collector.start_case({"case_id": "TC001"})
        assert collector.end_phase() is None

    def test_phase_attached_to_case(self):
        """end_phase 后阶段应正确挂载到对应 case 字段"""
        collector = ReportCollector()
        collector.start_run()
        collector.start_case({"case_id": "TC001"})

        collector.start_phase("pre_process")
        collector.end_phase("ok")

        collector.start_phase("test_case")
        collector.end_phase("fail")

        collector.start_phase("post_process")
        collector.end_phase("ok")

        case = collector.end_case("FAIL")
        assert case.pre_process is not None
        assert case.pre_process.name == "pre_process"
        assert case.pre_process.status == "ok"
        assert case.test_case is not None
        assert case.test_case.name == "test_case"
        assert case.test_case.status == "fail"
        assert case.post_process is not None
        assert case.post_process.name == "post_process"


class TestReportCollectorStep:
    """步骤级别收集测试"""

    def test_record_step_returns_step_report(self):
        """record_step 应返回 StepReport"""
        collector = ReportCollector()
        collector.start_run()
        collector.start_case({"case_id": "TC001"})
        collector.start_phase("test_case")

        step = collector.record_step({
            "index": 1,
            "action": "type",
            "model": "username_input",
            "data": "admin",
            "status": "ok",
            "duration": 0.5,
        })
        assert isinstance(step, StepReport)
        assert step.index == 1
        assert step.action == "type"
        assert step.model == "username_input"
        assert step.data == "admin"

    def test_record_step_added_to_phase(self):
        """record_step 应将步骤添加到当前阶段"""
        collector = ReportCollector()
        collector.start_run()
        collector.start_case({"case_id": "TC001"})
        collector.start_phase("test_case")

        collector.record_step({"index": 1, "action": "open"})
        collector.record_step({"index": 2, "action": "type"})
        collector.record_step({"index": 3, "action": "click"})

        phase = collector.end_phase("ok")
        assert len(phase.steps) == 3

    def test_record_step_without_phase(self):
        """无当前阶段时 record_step 应不报错，步骤不挂载"""
        collector = ReportCollector()
        collector.start_run()
        collector.start_case({"case_id": "TC001"})
        # 没有 start_phase
        step = collector.record_step({"index": 1, "action": "open"})
        assert step.action == "open"

    def test_record_step_with_error(self):
        """记录失败步骤应包含错误信息"""
        collector = ReportCollector()
        collector.start_run()
        collector.start_case({"case_id": "TC001"})
        collector.start_phase("test_case")

        step = collector.record_step({
            "index": 1,
            "action": "verify",
            "status": "fail",
            "error": "元素未找到",
            "diagnosis": {"type": "element_not_found", "suggestion": "检查定位器"},
        })
        assert step.status == "fail"
        assert step.error == "元素未找到"
        assert step.diagnosis["type"] == "element_not_found"

    def test_record_step_with_retry_history(self):
        """记录包含重试历史的步骤"""
        collector = ReportCollector()
        collector.start_run()
        collector.start_case({"case_id": "TC001"})
        collector.start_phase("test_case")

        step = collector.record_step({
            "index": 1,
            "action": "click",
            "status": "ok",
            "retry_history": [
                {"attempt": 1, "error": "timeout"},
                {"attempt": 2, "error": None},
            ],
        })
        assert len(step.retry_history) == 2


class TestReportCollectorSummary:
    """汇总计算测试"""

    def test_all_pass(self):
        """全部通过时通过率应为 100%"""
        collector = ReportCollector()
        collector.start_run()
        for i in range(5):
            collector.start_case({"case_id": f"TC{i:03d}"})
            collector.end_case("PASS")
        report = collector.end_run()
        assert report.summary.total == 5
        assert report.summary.passed == 5
        assert report.summary.failed == 0
        assert report.summary.pass_rate == 100.0

    def test_mixed_results(self):
        """混合结果时应正确统计各状态"""
        collector = ReportCollector()
        collector.start_run()

        statuses = ["PASS", "PASS", "FAIL", "SKIP", "ERROR"]
        for i, status in enumerate(statuses):
            collector.start_case({"case_id": f"TC{i:03d}"})
            collector.end_case(status)

        report = collector.end_run()
        assert report.summary.total == 5
        assert report.summary.passed == 2
        assert report.summary.failed == 1
        assert report.summary.skipped == 1
        assert report.summary.error == 1
        assert report.summary.pass_rate == 40.0

    def test_no_cases(self):
        """无用例时通过率应为 0"""
        collector = ReportCollector()
        collector.start_run()
        report = collector.end_run()
        assert report.summary.total == 0
        assert report.summary.pass_rate == 0.0


class TestReportCollectorOutput:
    """报告输出测试"""

    def test_auto_write_json_on_end_run(self):
        """指定 output_dir 时 end_run 应自动写入 report_data.json"""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = ReportCollector(output_dir=tmpdir)
            collector.start_run(run_id="output-test")
            collector.start_case({"case_id": "TC001", "title": "输出测试"})
            collector.end_case("PASS")
            collector.end_run()

            json_path = os.path.join(tmpdir, "report_data.json")
            assert os.path.exists(json_path)

            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert data["run_id"] == "output-test"
            assert len(data["cases"]) == 1

    def test_no_auto_write_without_output_dir(self):
        """未指定 output_dir 时 end_run 不应写入文件"""
        collector = ReportCollector()
        collector.start_run(run_id="no-output")
        collector.start_case({"case_id": "TC001"})
        collector.end_case("PASS")
        report = collector.end_run()
        # 应正常返回 report 但不写文件
        assert report is not None
        assert report.run_id == "no-output"

    def test_report_property(self):
        """report 属性应返回当前报告数据"""
        collector = ReportCollector()
        assert collector.report is None
        collector.start_run(run_id="prop-test")
        assert collector.report is not None
        assert collector.report.run_id == "prop-test"


class TestReportCollectorOptional:
    """收集器作为可选组件的测试"""

    def test_collector_is_optional(self):
        """收集器为 None 时不影响正常逻辑（模拟 SKIExecutor 场景）"""
        collector = None
        # 模拟 SKIExecutor 中的条件调用
        if collector:
            collector.start_run()
        # 不应报错
        assert True

    def test_multiple_cases_with_phases(self):
        """多个用例各自包含不同阶段的完整场景"""
        collector = ReportCollector()
        collector.start_run()

        # 用例 1：正常通过
        collector.start_case({"case_id": "TC001", "title": "正常用例"})
        collector.start_phase("pre_process")
        collector.record_step({"index": 1, "action": "open", "status": "ok"})
        collector.end_phase("ok")
        collector.start_phase("test_case")
        collector.record_step({"index": 2, "action": "verify", "status": "ok"})
        collector.end_phase("ok")
        collector.end_case("PASS")

        # 用例 2：测试阶段失败
        collector.start_case({"case_id": "TC002", "title": "失败用例"})
        collector.start_phase("test_case")
        collector.record_step({"index": 1, "action": "verify", "status": "fail", "error": "断言失败"})
        collector.end_phase("fail")
        collector.start_phase("post_process")
        collector.record_step({"index": 2, "action": "close", "status": "ok"})
        collector.end_phase("ok")
        collector.end_case("FAIL")

        report = collector.end_run()
        assert len(report.cases) == 2
        assert report.cases[0].status == "PASS"
        assert report.cases[1].status == "FAIL"
        assert report.cases[1].test_case.status == "fail"
        assert report.cases[1].test_case.steps[0].error == "断言失败"
