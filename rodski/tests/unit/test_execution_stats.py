"""ExecutionStats 单元测试

测试 core/execution_stats.py 中的执行统计分析模块。
覆盖：calculate_case_success_rate（正常/无记录/部分失败）、
      get_all_case_stats（多用例/多运行目录）、_get_case_results（内部方法）。
"""
import xml.etree.ElementTree as ET
import pytest
from pathlib import Path
from unittest.mock import patch
from core.execution_stats import ExecutionStats


@pytest.fixture
def result_dir(tmp_path):
    """创建包含多次运行结果的临时 result 目录"""
    # 第一次运行：c001 PASS, c002 FAIL
    run1 = tmp_path / "20260401_100000"
    run1.mkdir()
    _write_result(run1, [("c001", "PASS"), ("c002", "FAIL")])

    # 第二次运行：c001 PASS, c002 PASS
    run2 = tmp_path / "20260402_100000"
    run2.mkdir()
    _write_result(run2, [("c001", "PASS"), ("c002", "PASS")])

    # 第三次运行：c001 FAIL, c002 PASS
    run3 = tmp_path / "20260403_100000"
    run3.mkdir()
    _write_result(run3, [("c001", "FAIL"), ("c002", "PASS")])

    return tmp_path


def _write_result(run_dir: Path, cases: list):
    """辅助函数：写入一个 result.xml 文件"""
    root = ET.Element("testresult")
    results = ET.SubElement(root, "results")
    for case_id, status in cases:
        ET.SubElement(results, "result", case_id=case_id, status=status)
    tree = ET.ElementTree(root)
    tree.write(str(run_dir / "result.xml"), encoding="unicode")


class TestCalculateCaseSuccessRate:
    """calculate_case_success_rate —— 单个用例成功率计算"""

    def test_success_rate_two_of_three(self, result_dir):
        """c001 有 2 次 PASS / 1 次 FAIL，成功率应为 66.67%"""
        rate = ExecutionStats.calculate_case_success_rate(result_dir, "c001")
        assert rate is not None
        assert abs(rate - 66.67) < 1  # 约 66.67%

    def test_success_rate_nonexistent_case(self, result_dir):
        """不存在的 case_id 应返回 None"""
        rate = ExecutionStats.calculate_case_success_rate(result_dir, "c999")
        assert rate is None

    def test_success_rate_empty_dir(self, tmp_path):
        """空目录应返回 None"""
        rate = ExecutionStats.calculate_case_success_rate(tmp_path, "c001")
        assert rate is None

    def test_success_rate_last_n(self, result_dir):
        """last_n=2 时只统计最近两次"""
        # 最近两次：20260403(FAIL), 20260402(PASS) → 50%
        rate = ExecutionStats.calculate_case_success_rate(result_dir, "c001", last_n=2)
        assert rate is not None
        assert abs(rate - 50.0) < 0.1

    def test_success_rate_all_pass(self, result_dir):
        """c002 有 2 次 PASS / 1 次 FAIL，但 last_n=2 时最近两次全 PASS"""
        rate = ExecutionStats.calculate_case_success_rate(result_dir, "c002", last_n=2)
        assert rate is not None
        assert abs(rate - 100.0) < 0.1

    def test_success_rate_default_last_n_is_10(self, tmp_path):
        """默认 last_n=10：11 次历史记录时应忽略最早一次（第 11 次不计入统计）"""
        # 11 次运行：最近 10 次全 PASS，最早（第 11 次）FAIL
        for i in range(11):
            run = tmp_path / f"202604{i:02d}_100000"
            run.mkdir()
            status = "FAIL" if i == 0 else "PASS"  # i=0 是 sorted(reverse=True) 后最早的一次
            _write_result(run, [("c001", status)])

        rate = ExecutionStats.calculate_case_success_rate(tmp_path, "c001")
        assert rate == 100.0  # 默认只看最近 10 次，最早的 FAIL 被排除


class TestGetAllCaseStats:
    """get_all_case_stats —— 所有用例统计信息"""

    def test_returns_all_cases(self, result_dir):
        """应返回所有用例的统计信息"""
        stats = ExecutionStats.get_all_case_stats(result_dir)
        assert "c001" in stats
        assert "c002" in stats

    def test_stats_structure(self, result_dir):
        """每个用例的统计应包含 success_rate、total_runs、last_status"""
        stats = ExecutionStats.get_all_case_stats(result_dir)
        c001 = stats["c001"]
        assert "success_rate" in c001
        assert "total_runs" in c001
        assert "last_status" in c001

    def test_total_runs_count(self, result_dir):
        """total_runs 应等于实际运行次数"""
        stats = ExecutionStats.get_all_case_stats(result_dir)
        assert stats["c001"]["total_runs"] == 3
        assert stats["c002"]["total_runs"] == 3

    def test_last_status_is_latest_run(self, result_dir):
        """last_status 应为最近一次运行的状态"""
        stats = ExecutionStats.get_all_case_stats(result_dir)
        # 最近运行 20260403：c001=FAIL, c002=PASS
        assert stats["c001"]["last_status"] == "FAIL"
        assert stats["c002"]["last_status"] == "PASS"

    def test_empty_dir(self, tmp_path):
        """空目录应返回空字典"""
        stats = ExecutionStats.get_all_case_stats(tmp_path)
        assert stats == {}

    def test_default_last_n_is_10(self, tmp_path):
        """默认 last_n=10：11 次历史记录时最早一次不应计入 total_runs"""
        for i in range(11):
            run = tmp_path / f"202604{i:02d}_100000"
            run.mkdir()
            _write_result(run, [("c001", "PASS")])

        stats = ExecutionStats.get_all_case_stats(tmp_path)
        assert stats["c001"]["total_runs"] == 10

    def test_run_dir_without_result_xml_is_skipped(self, tmp_path):
        """run 目录下没有 result.xml 时应跳过该目录，不影响其他目录统计"""
        run1 = tmp_path / "20260401_100000"
        run1.mkdir()
        _write_result(run1, [("c001", "PASS")])

        run2 = tmp_path / "20260402_100000"
        run2.mkdir()  # 故意不写 result.xml

        stats = ExecutionStats.get_all_case_stats(tmp_path)
        assert stats["c001"]["total_runs"] == 1

    def test_case_without_case_id_attribute_ignored(self, tmp_path):
        """result 节点缺少 case_id 属性时应被忽略，不产生空字符串 key 的统计项"""
        run = tmp_path / "20260401_100000"
        run.mkdir()
        root = ET.Element("testresult")
        results = ET.SubElement(root, "results")
        ET.SubElement(results, "result", status="PASS")  # 无 case_id
        ET.ElementTree(root).write(str(run / "result.xml"), encoding="unicode")

        stats = ExecutionStats.get_all_case_stats(tmp_path)
        assert stats == {}

    def test_success_rate_calculation_is_correct_ratio(self, tmp_path):
        """success_rate 应为 passed/total*100，而非其他运算（如加减乘除误用）"""
        # 4 次运行：3 PASS 1 FAIL → 75%
        for i, status in enumerate(["PASS", "PASS", "PASS", "FAIL"]):
            run = tmp_path / f"202604{i:02d}_100000"
            run.mkdir()
            _write_result(run, [("c001", status)])

        stats = ExecutionStats.get_all_case_stats(tmp_path)
        assert abs(stats["c001"]["success_rate"] - 75.0) < 0.1

    def test_status_comparison_is_case_sensitive_exact_match(self, tmp_path):
        """success_rate 只统计精确等于 'PASS' 的状态，'pass'（小写）不算通过"""
        run = tmp_path / "20260401_100000"
        run.mkdir()
        _write_result(run, [("c001", "pass")])  # 小写，不应被计为 PASS

        stats = ExecutionStats.get_all_case_stats(tmp_path)
        assert stats["c001"]["success_rate"] == 0.0

    def test_result_node_missing_status_defaults_to_empty_string(self, tmp_path):
        """result 节点缺少 status 属性时，应记为空字符串而非 None

        （空字符串和 None 都是 falsy，但作为列表元素被 append 后，
        len(statuses) 和后续 == "PASS" 比较结果一致，因此换成直接检查
        raw 状态列表内容，而不是只看聚合后的 success_rate/total_runs。）
        """
        run = tmp_path / "20260401_100000"
        run.mkdir()
        root = ET.Element("testresult")
        results = ET.SubElement(root, "results")
        ET.SubElement(results, "result", case_id="c001")  # 无 status 属性
        ET.ElementTree(root).write(str(run / "result.xml"), encoding="unicode")

        raw_results = ExecutionStats._get_case_results(tmp_path, "c001", 10)
        assert raw_results == [""]

    def test_get_case_results_missing_status_is_empty_string(self, tmp_path):
        """_get_case_results 中 result 节点缺少 status 属性时应记为空字符串"""
        run = tmp_path / "20260401_100000"
        run.mkdir()
        root = ET.Element("testresult")
        results = ET.SubElement(root, "results")
        ET.SubElement(results, "result", case_id="c001")  # 无 status 属性
        ET.ElementTree(root).write(str(run / "result.xml"), encoding="unicode")

        raw_results = ExecutionStats._get_case_results(tmp_path, "c001", 10)
        assert raw_results == [""]
        assert raw_results != [None]

    def test_get_all_case_stats_result_xml_filename_is_exact_lowercase(self, tmp_path):
        """get_all_case_stats 查询的文件名必须精确为 'result.xml'（全小写）

        通过 mock Path.exists 拦截实际被查询的文件名，避免大小写不敏感的
        文件系统（如 macOS APFS 默认配置）掩盖大小写拼写错误。
        """
        run = tmp_path / "20260401_100000"
        run.mkdir()
        _write_result(run, [("c001", "PASS")])

        queried_names = []
        original_exists = Path.exists

        def spy_exists(self):
            queried_names.append(self.name)
            return original_exists(self)

        with patch.object(Path, "exists", spy_exists):
            ExecutionStats.get_all_case_stats(tmp_path)

        assert "result.xml" in queried_names

    def test_get_case_results_result_xml_filename_is_exact_lowercase(self, tmp_path):
        """_get_case_results 查询的文件名必须精确为 'result.xml'（全小写）"""
        run = tmp_path / "20260401_100000"
        run.mkdir()
        _write_result(run, [("c001", "PASS")])

        queried_names = []
        original_exists = Path.exists

        def spy_exists(self):
            queried_names.append(self.name)
            return original_exists(self)

        with patch.object(Path, "exists", spy_exists):
            ExecutionStats._get_case_results(tmp_path, "c001", 10)

        assert "result.xml" in queried_names

    def test_success_rate_is_zero_not_one_when_no_statuses_recorded(self, tmp_path):
        """last_n=0 时，case_id 存在但 statuses 列表为空 —— success_rate 应为 0.0（而非 1.0）

        get_all_case_stats 用 defaultdict 访问 stats[case_id] 时，即使 last_n=0
        导致 append 条件从不成立，该 case_id 的 defaultdict 条目仍会被创建
        （访问即创建）。此时 statuses == [] 触发三元表达式的 else 分支。
        """
        run = tmp_path / "20260401_100000"
        run.mkdir()
        _write_result(run, [("c001", "PASS")])

        stats = ExecutionStats.get_all_case_stats(tmp_path, last_n=0)
        assert stats["c001"]["success_rate"] == 0.0

    def test_get_all_case_stats_missing_status_recorded_as_empty_string(self, tmp_path):
        """get_all_case_stats 中 result 节点缺少 status 属性时应记为空字符串而非 None

        断言 last_status（首次记录的状态）为空字符串，而不是 None：
        `if not stats[case_id]["last_status"]:` 这一判断对 "" 和 None 结果一致，
        但 last_status 字段本身的值（""）能被序列化/展示，None 则不能。
        """
        run = tmp_path / "20260401_100000"
        run.mkdir()
        root = ET.Element("testresult")
        results = ET.SubElement(root, "results")
        ET.SubElement(results, "result", case_id="c001")  # 无 status 属性
        ET.ElementTree(root).write(str(run / "result.xml"), encoding="unicode")

        stats = ExecutionStats.get_all_case_stats(tmp_path)
        assert stats["c001"]["last_status"] == ""
        assert stats["c001"]["last_status"] is not None

    def test_missing_result_file_continues_to_next_run_dir(self, tmp_path):
        """run 目录下没有 result.xml 时应 continue 跳过，而不是 break 提前终止整个循环

        构造：最新的 run 目录没有 result.xml，更早的 run 目录有。
        若误写成 break，第一次循环（最新目录）直接终止，永远读不到更早目录的数据。
        """
        run_missing = tmp_path / "20260402_100000"
        run_missing.mkdir()  # 无 result.xml，且是排序后最先遍历到的（最新）

        run_has_data = tmp_path / "20260401_100000"
        run_has_data.mkdir()
        _write_result(run_has_data, [("c001", "PASS")])

        stats = ExecutionStats.get_all_case_stats(tmp_path)
        assert "c001" in stats
        assert stats["c001"]["total_runs"] == 1

        raw_results = ExecutionStats._get_case_results(tmp_path, "c001", 10)
        assert raw_results == ["PASS"]
