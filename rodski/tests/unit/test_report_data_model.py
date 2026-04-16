"""报告数据模型单元测试"""

import json
import os
import tempfile
from datetime import datetime

import pytest

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from report.data_model import (
    CaseReport,
    EnvironmentInfo,
    PhaseReport,
    ReportData,
    RunSummary,
    StepReport,
    _serialize,
)


class TestEnvironmentInfo:
    """环境信息数据模型测试"""

    def test_default_values(self):
        """默认值应为空字符串或 None"""
        env = EnvironmentInfo()
        assert env.os_name == ""
        assert env.os_version == ""
        assert env.python_version == ""
        assert env.rodski_version == ""
        assert env.browser is None
        assert env.browser_version is None

    def test_with_values(self):
        """可以正常设置所有字段"""
        env = EnvironmentInfo(
            os_name="Darwin",
            os_version="25.3.0",
            python_version="3.11.0",
            rodski_version="3.1.0",
            browser="chromium",
            browser_version="120.0",
        )
        assert env.os_name == "Darwin"
        assert env.browser == "chromium"


class TestRunSummary:
    """执行汇总数据模型测试"""

    def test_default_values(self):
        """默认值应全部为零"""
        s = RunSummary()
        assert s.total == 0
        assert s.passed == 0
        assert s.failed == 0
        assert s.skipped == 0
        assert s.error == 0
        assert s.pass_rate == 0.0
        assert s.duration == 0.0

    def test_with_values(self):
        """可以正常设置汇总字段"""
        s = RunSummary(total=10, passed=8, failed=1, skipped=1, error=0, pass_rate=80.0, duration=12.5)
        assert s.total == 10
        assert s.pass_rate == 80.0


class TestStepReport:
    """步骤报告数据模型测试"""

    def test_default_values(self):
        """默认状态为 ok，列表字段为空列表"""
        step = StepReport()
        assert step.index == 0
        assert step.action == ""
        assert step.status == "ok"
        assert step.retry_history == []
        assert step.error is None
        assert step.diagnosis is None

    def test_with_values(self):
        """可以正常设置步骤字段"""
        step = StepReport(
            index=1,
            action="type",
            model="username_input",
            data="admin",
            status="ok",
            duration=0.5,
            return_value="typed",
        )
        assert step.index == 1
        assert step.action == "type"
        assert step.return_value == "typed"

    def test_retry_history_isolation(self):
        """不同 StepReport 实例的 retry_history 不应共享"""
        s1 = StepReport()
        s2 = StepReport()
        s1.retry_history.append("retry1")
        assert s2.retry_history == []


class TestPhaseReport:
    """阶段报告数据模型测试"""

    def test_default_values(self):
        """默认状态为 ok，步骤列表为空"""
        phase = PhaseReport()
        assert phase.name == ""
        assert phase.status == "ok"
        assert phase.steps == []
        assert phase.duration == 0.0

    def test_steps_isolation(self):
        """不同 PhaseReport 实例的 steps 不应共享"""
        p1 = PhaseReport(name="pre_process")
        p2 = PhaseReport(name="test_case")
        p1.steps.append(StepReport(index=1, action="open"))
        assert len(p2.steps) == 0

    def test_with_steps(self):
        """阶段可以包含多个步骤"""
        step1 = StepReport(index=1, action="open")
        step2 = StepReport(index=2, action="type")
        phase = PhaseReport(name="test_case", steps=[step1, step2], status="ok", duration=1.5)
        assert len(phase.steps) == 2
        assert phase.steps[0].action == "open"


class TestCaseReport:
    """用例报告数据模型测试"""

    def test_default_values(self):
        """默认状态为 PASS，各阶段为 None"""
        case = CaseReport()
        assert case.case_id == ""
        assert case.status == "PASS"
        assert case.component_type == "界面"
        assert case.pre_process is None
        assert case.test_case is None
        assert case.post_process is None
        assert case.tags == []

    def test_with_phases(self):
        """用例可以包含三个阶段"""
        pre = PhaseReport(name="pre_process")
        test = PhaseReport(name="test_case")
        post = PhaseReport(name="post_process")
        case = CaseReport(
            case_id="TC001",
            title="登录测试",
            pre_process=pre,
            test_case=test,
            post_process=post,
            status="PASS",
            duration=3.2,
        )
        assert case.case_id == "TC001"
        assert case.pre_process.name == "pre_process"

    def test_tags_isolation(self):
        """不同 CaseReport 实例的 tags 不应共享"""
        c1 = CaseReport()
        c2 = CaseReport()
        c1.tags.append("smoke")
        assert c2.tags == []


class TestReportData:
    """完整报告数据模型测试"""

    def test_default_values(self):
        """默认值应正确初始化"""
        report = ReportData(run_id="test-001")
        assert report.run_id == "test-001"
        assert isinstance(report.start_time, datetime)
        assert report.end_time is None
        assert report.duration == 0.0
        assert report.environment is None
        assert report.summary is None
        assert report.cases == []

    def test_cases_isolation(self):
        """不同 ReportData 实例的 cases 不应共享"""
        r1 = ReportData(run_id="r1")
        r2 = ReportData(run_id="r2")
        r1.cases.append(CaseReport(case_id="TC001"))
        assert len(r2.cases) == 0

    def test_to_dict(self):
        """to_dict 应返回可 JSON 序列化的字典"""
        report = ReportData(
            run_id="test-002",
            start_time=datetime(2026, 1, 1, 12, 0, 0),
            end_time=datetime(2026, 1, 1, 12, 5, 0),
            duration=300.0,
            environment=EnvironmentInfo(
                os_name="Darwin",
                os_version="25.3.0",
                python_version="3.11.0",
                rodski_version="3.1.0",
            ),
            summary=RunSummary(total=2, passed=1, failed=1, pass_rate=50.0, duration=300.0),
        )
        case = CaseReport(
            case_id="TC001",
            title="测试用例一",
            status="PASS",
            duration=1.5,
            pre_process=PhaseReport(
                name="pre_process",
                steps=[StepReport(index=1, action="open", model="url", data="http://localhost")],
            ),
        )
        report.cases.append(case)

        d = report.to_dict()
        # 应该可以序列化为 JSON
        json_str = json.dumps(d, ensure_ascii=False)
        assert "test-002" in json_str
        assert "TC001" in json_str
        assert "测试用例一" in json_str
        assert "Darwin" in json_str

    def test_to_dict_datetime_format(self):
        """to_dict 中 datetime 应转为 ISO 格式字符串"""
        dt = datetime(2026, 4, 16, 10, 30, 0)
        report = ReportData(run_id="dt-test", start_time=dt)
        d = report.to_dict()
        assert d["start_time"] == "2026-04-16T10:30:00"

    def test_to_dict_none_fields(self):
        """to_dict 中 None 字段应保留为 None"""
        report = ReportData(run_id="none-test")
        d = report.to_dict()
        assert d["end_time"] is None
        assert d["environment"] is None
        assert d["summary"] is None

    def test_to_json(self):
        """to_json 应写入有效的 JSON 文件"""
        report = ReportData(
            run_id="json-test",
            start_time=datetime(2026, 1, 1, 12, 0, 0),
            duration=10.0,
            summary=RunSummary(total=1, passed=1, pass_rate=100.0, duration=10.0),
        )
        report.cases.append(CaseReport(case_id="TC001", title="测试"))

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "report_data.json")
            report.to_json(path)

            assert os.path.exists(path)
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert data["run_id"] == "json-test"
            assert len(data["cases"]) == 1
            assert data["cases"][0]["case_id"] == "TC001"
            assert data["cases"][0]["title"] == "测试"

    def test_to_json_creates_parent_dirs(self):
        """to_json 应自动创建不存在的父目录"""
        report = ReportData(run_id="dir-test")
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "subdir", "deep", "report_data.json")
            report.to_json(path)
            assert os.path.exists(path)


class TestSerialize:
    """_serialize 辅助函数测试"""

    def test_primitives(self):
        """基础类型应原样返回"""
        assert _serialize(None) is None
        assert _serialize("hello") == "hello"
        assert _serialize(42) == 42
        assert _serialize(3.14) == 3.14
        assert _serialize(True) is True

    def test_datetime(self):
        """datetime 应转为 ISO 格式字符串"""
        dt = datetime(2026, 4, 16, 10, 30, 0)
        assert _serialize(dt) == "2026-04-16T10:30:00"

    def test_dict(self):
        """字典应递归序列化"""
        d = {"key": datetime(2026, 1, 1), "nested": {"value": 42}}
        result = _serialize(d)
        assert result["key"] == "2026-01-01T00:00:00"
        assert result["nested"]["value"] == 42

    def test_list(self):
        """列表应递归序列化"""
        lst = [1, "two", datetime(2026, 1, 1)]
        result = _serialize(lst)
        assert result == [1, "two", "2026-01-01T00:00:00"]

    def test_unknown_type_to_str(self):
        """未知类型应转为字符串"""

        class Custom:
            def __str__(self):
                return "custom_obj"

        assert _serialize(Custom()) == "custom_obj"

    def test_step_report_serialization(self):
        """StepReport dataclass 应正确序列化"""
        step = StepReport(index=1, action="verify", status="ok")
        result = _serialize(step)
        assert isinstance(result, dict)
        assert result["index"] == 1
        assert result["action"] == "verify"
