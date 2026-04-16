"""HistoryManager 单元测试

覆盖历史数据的写入、查询、诊断信息保存、边界情况等。
"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

# 直接导入，避免整体包依赖
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from report.data_model import (
    ReportData, CaseReport, StepReport, PhaseReport, RunSummary,
)
from report.history import HistoryManager, _extract_diagnosis_summary


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture
def tmp_result_dir(tmp_path):
    """临时结果目录"""
    return str(tmp_path / "result")


@pytest.fixture
def manager(tmp_result_dir):
    """返回一个空的 HistoryManager"""
    return HistoryManager(tmp_result_dir)


def _make_case(case_id, status="PASS", duration=1.0, error=None, steps=None):
    """辅助：构造 CaseReport（步骤放在 test_case phase 中）"""
    phase_steps = steps or []
    if error and not steps:
        phase_steps = [StepReport(action="verify", status="FAIL", error=error)]
    phase = PhaseReport(name="test_case", steps=phase_steps, status="ok", duration=duration)
    return CaseReport(case_id=case_id, status=status, duration=duration, test_case=phase)


def _make_report(
    run_id="run_001",
    timestamp="2026-04-16T10:00:00",
    cases=None,
    total=None,
    passed=None,
    failed=None,
) -> ReportData:
    """辅助：构造 ReportData（兼容 Wave 1 数据模型）"""
    if cases is None:
        cases = [
            _make_case("TC001", status="PASS", duration=1.5),
            _make_case("TC002", status="FAIL", duration=2.3,
                       error="Element not found: #btn"),
        ]
    _total = total if total is not None else len(cases)
    _passed = passed if passed is not None else sum(1 for c in cases if c.status == "PASS")
    _failed = failed if failed is not None else sum(1 for c in cases if c.status == "FAIL")
    _duration = sum(c.duration for c in cases)

    summary = RunSummary(
        total=_total,
        passed=_passed,
        failed=_failed,
        skipped=0,
        pass_rate=round(_passed / _total * 100, 1) if _total else 0,
        duration=_duration,
    )

    return ReportData(
        run_id=run_id,
        start_time=datetime.fromisoformat(timestamp),
        duration=_duration,
        summary=summary,
        cases=cases,
    )


# ------------------------------------------------------------------
# 测试
# ------------------------------------------------------------------


class TestHistoryManagerAddRun:
    """测试 add_run 写入功能"""

    def test_add_run_creates_history_file(self, manager, tmp_result_dir):
        """添加运行后 history.json 应被创建"""
        report = _make_report()
        manager.add_run(report)
        assert Path(tmp_result_dir, "history.json").exists()

    def test_add_run_stores_summary(self, manager):
        """添加运行后应存储正确的摘要字段"""
        report = _make_report(run_id="run_100", total=2, passed=1, failed=1)
        manager.add_run(report)

        runs = manager.get_history(last_n=1)
        assert len(runs) == 1
        run = runs[0]
        assert run["run_id"] == "run_100"
        assert run["total"] == 2
        assert run["passed"] == 1
        assert run["failed"] == 1
        assert run["pass_rate"] == 50.0

    def test_add_run_stores_case_info(self, manager):
        """添加运行后应存储各用例状态和耗时"""
        report = _make_report()
        manager.add_run(report)

        runs = manager.get_history()
        cases = runs[0]["cases"]
        assert cases["TC001"]["status"] == "PASS"
        assert cases["TC001"]["duration"] == 1.5
        assert cases["TC002"]["status"] == "FAIL"
        assert "error" in cases["TC002"]

    def test_add_run_stores_error_only_for_failures(self, manager):
        """通过的用例不应包含 error 字段"""
        report = _make_report()
        manager.add_run(report)

        cases = manager.get_history()[0]["cases"]
        assert "error" not in cases["TC001"]
        assert "error" in cases["TC002"]

    def test_add_multiple_runs(self, manager):
        """多次添加运行应追加而非覆盖"""
        manager.add_run(_make_report(run_id="run_001"))
        manager.add_run(_make_report(run_id="run_002"))
        manager.add_run(_make_report(run_id="run_003"))

        runs = manager.get_history(last_n=100)
        assert len(runs) == 3
        assert [r["run_id"] for r in runs] == ["run_001", "run_002", "run_003"]


class TestHistoryManagerGetHistory:
    """测试 get_history 查询功能"""

    def test_get_history_empty(self, manager):
        """无历史记录时应返回空列表"""
        assert manager.get_history() == []

    def test_get_history_last_n(self, manager):
        """last_n 应只返回最近 N 条"""
        for i in range(5):
            manager.add_run(_make_report(run_id=f"run_{i:03d}"))

        runs = manager.get_history(last_n=3)
        assert len(runs) == 3
        assert runs[0]["run_id"] == "run_002"
        assert runs[-1]["run_id"] == "run_004"

    def test_get_history_all(self, manager):
        """last_n=0 应返回全部"""
        for i in range(3):
            manager.add_run(_make_report(run_id=f"run_{i}"))
        assert len(manager.get_history(last_n=0)) == 3


class TestHistoryManagerGetCaseHistory:
    """测试 get_case_history 查询功能"""

    def test_get_case_history(self, manager):
        """查询特定用例的历史记录"""
        manager.add_run(_make_report(run_id="run_001", timestamp="2026-04-16T10:00:00"))
        manager.add_run(_make_report(run_id="run_002", timestamp="2026-04-16T11:00:00"))

        records = manager.get_case_history("TC001")
        assert len(records) == 2
        assert records[0]["run_id"] == "run_001"
        assert records[0]["status"] == "PASS"

    def test_get_case_history_nonexistent(self, manager):
        """查询不存在的用例应返回空列表"""
        manager.add_run(_make_report())
        assert manager.get_case_history("NONEXISTENT") == []

    def test_get_case_history_last_n(self, manager):
        """last_n 应限制返回数量"""
        for i in range(5):
            manager.add_run(_make_report(run_id=f"run_{i}"))

        records = manager.get_case_history("TC001", last_n=2)
        assert len(records) == 2


class TestHistoryManagerGetRun:
    """测试 get_run 查询功能"""

    def test_get_run_found(self, manager):
        """按 run_id 查询应返回对应运行"""
        manager.add_run(_make_report(run_id="run_abc"))
        run = manager.get_run("run_abc")
        assert run is not None
        assert run["run_id"] == "run_abc"

    def test_get_run_not_found(self, manager):
        """查询不存在的 run_id 应返回 None"""
        assert manager.get_run("nonexistent") is None


class TestHistoryManagerEdgeCases:
    """边界场景测试"""

    def test_corrupted_history_file(self, manager, tmp_result_dir):
        """history.json 损坏时应优雅降级"""
        Path(tmp_result_dir).mkdir(parents=True, exist_ok=True)
        Path(tmp_result_dir, "history.json").write_text(
            "not valid json!!!", encoding="utf-8"
        )
        # 不应抛异常
        assert manager.get_history() == []

    def test_invalid_structure(self, manager, tmp_result_dir):
        """history.json 格式不对时应优雅降级"""
        Path(tmp_result_dir).mkdir(parents=True, exist_ok=True)
        Path(tmp_result_dir, "history.json").write_text(
            '["not a dict"]', encoding="utf-8"
        )
        assert manager.get_history() == []

    def test_max_history_cap(self, manager):
        """历史记录数应不超过 _MAX_HISTORY_RUNS"""
        from report.history import _MAX_HISTORY_RUNS

        for i in range(_MAX_HISTORY_RUNS + 20):
            manager.add_run(_make_report(run_id=f"run_{i:04d}"))

        runs = manager.get_history(last_n=0)
        assert len(runs) == _MAX_HISTORY_RUNS
        # 最旧的 20 条应被裁剪
        assert runs[0]["run_id"] == "run_0020"


class TestDiagnosisSummaryExtraction:
    """测试诊断信息的提取和保存（WI-44）"""

    def test_extracts_diagnosis_from_steps(self):
        """应从步骤的 diagnosis 字段提取类别和策略"""
        step = StepReport(
            action="click",
            status="FAIL",
            diagnosis={
                "failure_reason": "ElementNotFound",
                "recovery_action": {"action": "wait", "data": "3"},
            },
        )
        phase = PhaseReport(name="test_case", steps=[step])
        case = CaseReport(case_id="TC100", status="FAIL", test_case=phase)
        summaries = _extract_diagnosis_summary(case)
        assert len(summaries) == 1
        assert summaries[0]["category"] == "ElementNotFound"
        assert summaries[0]["strategy"] == "wait"

    def test_extracts_retry_history(self):
        """应从步骤的 retry_history 中提取修复策略和结果"""
        step = StepReport(
            action="click",
            status="PASS",
            retry_history=[
                {"strategy": "wait", "fixed": True},
                {"strategy": "refresh", "fixed": False},
            ],
        )
        phase = PhaseReport(name="test_case", steps=[step])
        case = CaseReport(case_id="TC101", status="PASS", test_case=phase)
        summaries = _extract_diagnosis_summary(case)
        assert len(summaries) == 2
        assert summaries[0] == {"strategy": "wait", "fixed": True}
        assert summaries[1] == {"strategy": "refresh", "fixed": False}

    def test_diagnosis_saved_in_history(self, manager):
        """诊断信息应被保存到 history.json 中"""
        step = StepReport(
            action="verify",
            status="FAIL",
            error="timeout",
            diagnosis={
                "failure_reason": "Timeout",
                "recovery_action": {"action": "refresh"},
            },
        )
        phase = PhaseReport(name="test_case", steps=[step])
        case = CaseReport(case_id="TC200", status="FAIL", duration=1.0, test_case=phase)
        report = _make_report(cases=[case], total=1, passed=0, failed=1)
        manager.add_run(report)

        runs = manager.get_history()
        diag = runs[0]["cases"]["TC200"].get("diagnosis")
        assert diag is not None
        assert len(diag) == 1
        assert diag[0]["category"] == "Timeout"

    def test_no_diagnosis_when_steps_clean(self, manager):
        """无诊断信息时不应存储 diagnosis 字段"""
        case = _make_case("TC300", status="PASS", duration=1.0)
        report = _make_report(cases=[case], total=1, passed=1, failed=0)
        manager.add_run(report)

        runs = manager.get_history()
        assert "diagnosis" not in runs[0]["cases"]["TC300"]
