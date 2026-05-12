"""Unit tests for rodski_agent.narrator.log_correlator"""
import pytest
from textwrap import dedent


LOG_SAMPLE = dedent("""\
    2026-05-07 15:37:12,488 [INFO] 执行用例 1/3: TC020 - SQLite查询订单
    2026-05-07 15:37:12,488 [INFO] 执行关键字: DB(model=QuerySQL, data=Q001)
    2026-05-07 15:37:12,488 [INFO] DB query: SELECT order_no FROM orders LIMIT '3'
    2026-05-07 15:37:12,489 [INFO] DB 操作成功 (query)
    2026-05-07 15:37:12,489 [INFO] [STEP] action=DB model=QuerySQL status=OK source=keyword_result
    2026-05-07 15:37:12,489 [DEBUG]   history[0]=[{'order_no': 'ORD001'}]
    2026-05-07 15:37:14,029 [INFO]   PASS (1.542s)
    2026-05-07 15:37:14,030 [INFO] 执行用例 2/3: TC021 - SQLite插入并验证
    2026-05-07 15:37:14,031 [INFO] 执行关键字: DB(model=QuerySQL, data=Q005)
    2026-05-07 15:37:14,031 [INFO] DB execute: DELETE FROM orders WHERE order_no = 'TEST001'
    2026-05-07 15:37:14,031 [INFO] [STEP] action=DB model=QuerySQL status=OK source=keyword_result
    2026-05-07 15:37:16,447 [INFO]   FAIL (2.417s)
""")


@pytest.fixture
def log_file(tmp_path):
    f = tmp_path / "execution.log"
    f.write_text(LOG_SAMPLE, encoding="utf-8")
    return f


def test_correlate_case_count(log_file):
    from rodski_agent.narrator.log_correlator import LogCorrelator

    result = LogCorrelator(str(log_file)).correlate()
    assert len(result) == 2
    assert "TC020" in result
    assert "TC021" in result


def test_correlate_case_title(log_file):
    from rodski_agent.narrator.log_correlator import LogCorrelator

    result = LogCorrelator(str(log_file)).correlate()
    assert result["TC020"].title == "SQLite查询订单"


def test_correlate_case_status(log_file):
    from rodski_agent.narrator.log_correlator import LogCorrelator

    result = LogCorrelator(str(log_file)).correlate()
    assert result["TC020"].status == "PASS"
    assert result["TC021"].status == "FAIL"


def test_correlate_duration(log_file):
    from rodski_agent.narrator.log_correlator import LogCorrelator

    result = LogCorrelator(str(log_file)).correlate()
    assert abs(result["TC020"].duration_s - 1.542) < 0.001


def test_correlate_sql_extraction(log_file):
    from rodski_agent.narrator.log_correlator import LogCorrelator

    result = LogCorrelator(str(log_file)).correlate()
    steps = result["TC020"].steps
    assert len(steps) >= 1
    assert "SELECT order_no" in steps[0].sql


def test_correlate_execute_sql(log_file):
    from rodski_agent.narrator.log_correlator import LogCorrelator

    result = LogCorrelator(str(log_file)).correlate()
    steps = result["TC021"].steps
    assert "DELETE FROM orders" in steps[0].sql


def test_correlate_step_status(log_file):
    from rodski_agent.narrator.log_correlator import LogCorrelator

    result = LogCorrelator(str(log_file)).correlate()
    assert result["TC020"].steps[0].status == "OK"


def test_correlate_return_value(log_file):
    from rodski_agent.narrator.log_correlator import LogCorrelator

    result = LogCorrelator(str(log_file)).correlate()
    assert "ORD001" in result["TC020"].steps[0].return_value


def test_correlate_missing_log(tmp_path):
    from rodski_agent.narrator.log_correlator import LogCorrelator

    result = LogCorrelator(str(tmp_path / "nonexistent.log")).correlate()
    assert result == {}


def test_to_dict_serializable(log_file):
    from rodski_agent.narrator.log_correlator import LogCorrelator
    import json

    result = LogCorrelator(str(log_file)).correlate()
    for info in result.values():
        d = LogCorrelator.to_dict(info)
        json.dumps(d, ensure_ascii=False)
