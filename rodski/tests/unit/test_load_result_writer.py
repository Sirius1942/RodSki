"""单元测试：LoadResultWriter。
验证生成 XML 结构 + XSD 校验。
"""
from __future__ import annotations
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

# 确保 rodski 包可导入
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from rodski.load.stats import LoadStats, RequestRecord
from rodski.load.result_writer import LoadResultWriter


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_stats() -> LoadStats:
    """构造含若干请求记录的 LoadStats。"""
    stats = LoadStats()
    # tc001: 3 次成功，1 次失败
    stats.record(RequestRecord(name="tc001", elapsed_ms=120, success=True))
    stats.record(RequestRecord(name="tc001", elapsed_ms=150, success=True))
    stats.record(RequestRecord(name="tc001", elapsed_ms=200, success=True))
    stats.record(RequestRecord(name="tc001", elapsed_ms=500, success=False, failure_reason="timeout"))
    # tc002: 2 次成功
    stats.record(RequestRecord(name="tc002", elapsed_ms=80, success=True))
    stats.record(RequestRecord(name="tc002", elapsed_ms=90, success=True))
    return stats


def _make_plan() -> dict:
    return {
        "load_profile": {
            "duration_seconds": 60,
            "concurrency": 10,
        },
        "cases": [
            {"id": "tc001", "execute": "是"},
            {"id": "tc002", "execute": "是"},
            {"id": "tc003", "execute": "否"},   # 不执行，不进结果
        ],
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLoadResultWriter:

    def test_result_dir_auto_created(self, tmp_path):
        """result/ 目录不存在时应自动创建。"""
        module_dir = tmp_path / "mymodule"
        module_dir.mkdir()
        # 不预先创建 result/

        writer = LoadResultWriter()
        result_path = writer.write(_make_stats(), _make_plan(), module_dir)

        assert result_path.exists(), "结果文件应已生成"
        assert result_path.parent.name == "result", "文件应在 result/ 目录下"

    def test_xml_root_element(self, tmp_path):
        """根元素应为 testresult。"""
        writer = LoadResultWriter()
        result_path = writer.write(_make_stats(), _make_plan(), tmp_path)

        tree = ET.parse(str(result_path))
        root = tree.getroot()
        assert root.tag == "testresult"

    def test_summary_element(self, tmp_path):
        """<summary> 应包含 total/passed/failed 属性。"""
        writer = LoadResultWriter()
        result_path = writer.write(_make_stats(), _make_plan(), tmp_path)

        root = ET.parse(str(result_path)).getroot()
        summary = root.find("summary")
        assert summary is not None
        # 只有 execute=是 的两个用例
        assert summary.get("total") == "2"
        assert summary.get("passed") == "2"
        assert "failed" in summary.attrib

    def test_results_element_only_executed_cases(self, tmp_path):
        """<results> 只包含 execute=是 的用例。"""
        writer = LoadResultWriter()
        result_path = writer.write(_make_stats(), _make_plan(), tmp_path)

        root = ET.parse(str(result_path)).getroot()
        results = root.find("results")
        assert results is not None
        result_els = results.findall("result")
        assert len(result_els) == 2
        ids = {el.get("case_id") for el in result_els}
        assert ids == {"tc001", "tc002"}
        assert "tc003" not in ids

    def test_result_load_attributes(self, tmp_path):
        """<result> 节点应含 load_requests / load_failures / load_p95_ms。"""
        writer = LoadResultWriter()
        result_path = writer.write(_make_stats(), _make_plan(), tmp_path)

        root = ET.parse(str(result_path)).getroot()
        results = root.find("results")
        tc001 = next(el for el in results.findall("result") if el.get("case_id") == "tc001")
        assert tc001.get("load_requests") == "4"
        assert tc001.get("load_failures") == "1"
        assert tc001.get("load_p95_ms") is not None

    def test_load_summary_exists(self, tmp_path):
        """<load_summary> 节点应存在。"""
        writer = LoadResultWriter()
        result_path = writer.write(_make_stats(), _make_plan(), tmp_path)

        root = ET.parse(str(result_path)).getroot()
        ls = root.find("load_summary")
        assert ls is not None, "<load_summary> 节点应存在"

    def test_load_summary_attributes(self, tmp_path):
        """<load_summary> 属性值正确性检查。"""
        stats = _make_stats()
        plan = _make_plan()

        writer = LoadResultWriter()
        result_path = writer.write(stats, plan, tmp_path)

        root = ET.parse(str(result_path)).getroot()
        ls = root.find("load_summary")

        assert ls.get("total_requests") == "6"
        assert ls.get("total_failures") == "1"
        assert ls.get("duration_seconds") == "60"
        assert ls.get("concurrency") == "10"

    def test_load_summary_latency_child(self, tmp_path):
        """<load_summary> 应含 <latency> 子节点及百分位属性。"""
        writer = LoadResultWriter()
        result_path = writer.write(_make_stats(), _make_plan(), tmp_path)

        root = ET.parse(str(result_path)).getroot()
        ls = root.find("load_summary")
        latency = ls.find("latency")
        assert latency is not None
        for attr in ("p50_ms", "p75_ms", "p95_ms", "p99_ms", "avg_ms", "max_ms"):
            assert latency.get(attr) is not None, f"latency 缺少属性 {attr}"

    def test_load_summary_endpoints_child(self, tmp_path):
        """<load_summary> 应含 <endpoints> 及两个 <endpoint>。"""
        writer = LoadResultWriter()
        result_path = writer.write(_make_stats(), _make_plan(), tmp_path)

        root = ET.parse(str(result_path)).getroot()
        ls = root.find("load_summary")
        endpoints = ls.find("endpoints")
        assert endpoints is not None
        ep_els = endpoints.findall("endpoint")
        assert len(ep_els) == 2
        names = {el.get("name") for el in ep_els}
        assert names == {"tc001", "tc002"}

    def test_xml_has_declaration(self, tmp_path):
        """生成文件应以 XML 声明开头。"""
        writer = LoadResultWriter()
        result_path = writer.write(_make_stats(), _make_plan(), tmp_path)

        raw = result_path.read_bytes()
        assert raw.startswith(b"<?xml"), "文件应以 XML 声明开头"

    def test_xsd_validation(self, tmp_path):
        """生成的 XML 应通过 result.xsd 校验。"""
        import xmlschema

        xsd_path = Path(__file__).parent.parent.parent / "schemas" / "result.xsd"
        assert xsd_path.exists(), f"找不到 XSD 文件：{xsd_path}"

        schema = xmlschema.XMLSchema(str(xsd_path))

        writer = LoadResultWriter()
        result_path = writer.write(_make_stats(), _make_plan(), tmp_path)

        errors = list(schema.iter_errors(str(result_path)))
        assert errors == [], (
            f"XSD 校验失败，共 {len(errors)} 个错误：\n"
            + "\n".join(str(e) for e in errors)
        )

    def test_empty_stats_no_crash(self, tmp_path):
        """空 LoadStats 不应抛异常。"""
        writer = LoadResultWriter()
        result_path = writer.write(LoadStats(), _make_plan(), tmp_path)
        assert result_path.exists()
        # 空 stats 仍需通过 XSD
        import xmlschema
        xsd_path = Path(__file__).parent.parent.parent / "schemas" / "result.xsd"
        schema = xmlschema.XMLSchema(str(xsd_path))
        errors = list(schema.iter_errors(str(result_path)))
        assert errors == [], "空 stats 生成的 XML 也应通过 XSD 校验"

    def test_no_endpoints_when_empty_stats(self, tmp_path):
        """空 LoadStats 不应生成 <endpoints> 节点。"""
        writer = LoadResultWriter()
        result_path = writer.write(LoadStats(), _make_plan(), tmp_path)

        root = ET.parse(str(result_path)).getroot()
        ls = root.find("load_summary")
        assert ls is not None
        # endpoints 节点不应存在（空时不生成）
        assert ls.find("endpoints") is None
