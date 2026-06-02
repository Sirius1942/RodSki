"""Observability 接线集成测试

验证 enable_trace=True 时，SKIExecutor 真实执行后能产出：
- 非空 trace 树（run > case > keyword 三层结构）
- keyword.total / keyword.duration 指标
- CLI 风格的 JsonExporter 导出文件

不依赖任何真实浏览器/设备驱动，仅用 wait/set 关键字。
"""
import json
from pathlib import Path

import pytest

from core.ski_executor import SKIExecutor
from observability import Tracer, MetricsCollector, JsonExporter


@pytest.fixture(autouse=True)
def _reset_singletons():
    """每个测试前后重置 observability 单例，避免状态串味。"""
    Tracer._reset_instance()
    MetricsCollector._reset_instance()
    yield
    Tracer._reset_instance()
    MetricsCollector._reset_instance()


@pytest.fixture
def wait_module(tmp_path):
    """构造一个只用 wait/set 关键字的最小测试模块（无需驱动）。"""
    mod = tmp_path / "trace_module"
    for sub in ("case", "model", "data", "fun", "result"):
        (mod / sub).mkdir(parents=True)

    (mod / "model" / "model.xml").write_text(
        '<?xml version="1.0"?><models></models>', encoding="utf-8"
    )
    (mod / "data" / "globalvalue.xml").write_text(
        '<?xml version="1.0"?>\n'
        '<globalvalue>\n'
        '  <group name="DefaultValue"><var name="WaitTime" value="0"/></group>\n'
        '</globalvalue>',
        encoding="utf-8",
    )
    (mod / "case" / "trace_case.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<cases>\n'
        '  <case execute="是" id="T001" title="trace 烟囱测试" component_type="接口">\n'
        '    <pre_process>\n'
        '      <test_step action="wait" model="" data="0"/>\n'
        '    </pre_process>\n'
        '    <test_case>\n'
        '      <test_step action="wait" model="" data="0"/>\n'
        '      <test_step action="wait" model="" data="0"/>\n'
        '    </test_case>\n'
        '  </case>\n'
        '</cases>',
        encoding="utf-8",
    )
    return mod


def _build_executor(module_dir, enable_trace):
    from unittest.mock import MagicMock
    driver = MagicMock()
    return SKIExecutor(
        str(module_dir / "case" / "trace_case.xml"),
        driver,
        module_dir=str(module_dir),
        enable_trace=enable_trace,
    )


def test_trace_tree_built_when_enabled(wait_module):
    """enable_trace=True：执行后 trace 树为 run > case > keyword 三层。"""
    executor = _build_executor(wait_module, enable_trace=True)
    executor.execute_all_cases()

    root = executor._tracer.get_root_span()
    assert root is not None
    assert root.name == "run"
    assert root.status == "ok"

    # run 下有 case span
    assert len(root.children) == 1
    case_span = root.children[0]
    assert case_span.name == "case"
    assert case_span.attributes.get("case_id") == "T001"

    # case 下有 keyword span（3 步 wait：1 pre + 2 test）
    kw_names = [c.name for c in case_span.children]
    assert kw_names == ["keyword.wait", "keyword.wait", "keyword.wait"]
    assert all(c.status == "ok" for c in case_span.children)


def test_metrics_collected_when_enabled(wait_module):
    """enable_trace=True：执行后 keyword.total / keyword.duration 指标非空。"""
    executor = _build_executor(wait_module, enable_trace=True)
    executor.execute_all_cases()

    summary = executor._metrics.get_summary()
    counters = summary["counters"]
    histograms = summary["histograms"]

    assert "keyword.total" in counters
    # wait 出现 3 次
    assert counters["keyword.total"].get("keyword=wait") == 3

    assert "keyword.duration" in histograms
    assert histograms["keyword.duration"]["keyword=wait"]["count"] == 3


def test_disabled_by_default(wait_module):
    """默认 enable_trace=False：不产生 trace 树，无 observability 开销。"""
    executor = _build_executor(wait_module, enable_trace=False)
    executor.execute_all_cases()

    assert executor._tracer is None
    assert executor._metrics is None


def test_json_export_to_file(wait_module, tmp_path):
    """JsonExporter 导出文件包含 trace 与 metrics 两部分。"""
    executor = _build_executor(wait_module, enable_trace=True)
    executor.execute_all_cases()

    out = tmp_path / "trace.json"
    JsonExporter.export_to_file(
        str(out), tracer=executor._tracer, collector=executor._metrics
    )
    assert out.exists()

    data = json.loads(out.read_text(encoding="utf-8"))
    assert "trace" in data
    assert "metrics" in data
    spans = data["trace"]["resourceSpans"][0]["scopeSpans"][0]["spans"]
    span_names = {s["name"] for s in spans}
    assert "run" in span_names
    assert "keyword.wait" in span_names


def test_tracer_reinjected_after_driver_recreation(wait_module):
    """回归：用例间驱动重建后，tracer/metrics 必须重新注入。

    否则第 2+ 个用例的 keyword span / 指标会丢失（_ensure_driver_alive
    重建 KeywordEngine 时未继承 observability 注入的历史 bug）。
    """
    executor = _build_executor(wait_module, enable_trace=True)
    # 模拟驱动已关闭 → 触发 _ensure_driver_alive 重建 KeywordEngine
    executor.driver_factory = lambda: __import__("unittest.mock", fromlist=["MagicMock"]).MagicMock()
    executor._driver_closed = True
    executor._ensure_driver_alive()

    # 重建后的关键字引擎仍持有同一 tracer / metrics
    assert executor.keyword_engine._tracer is executor._tracer
    assert executor.keyword_engine._metrics is executor._metrics

