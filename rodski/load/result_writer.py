"""LoadResultWriter — 压测结果 XML 写入器。
生成含 <load_summary> 节点的 result XML，兼容 result.xsd。
"""
from __future__ import annotations
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .stats import LoadStats


class LoadResultWriter:

    def write(
        self,
        stats: "LoadStats",
        plan: dict,
        module_dir: Path,
    ) -> Path:
        """生成 result/result_{timestamp}.xml，返回文件路径。"""
        module_dir = Path(module_dir)
        result_dir = module_dir / "result"
        result_dir.mkdir(exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_path = result_dir / f"result_{ts}.xml"

        profile = plan.get("load_profile", {})
        duration = int(profile.get("duration_seconds", 0))
        concurrency = int(profile.get("concurrency", 0))

        summary_data = stats.summary()
        endpoints_data = stats.per_endpoint()
        plan_cases = [c for c in plan.get("cases", []) if c.get("execute") == "是"]

        root = ET.Element("testresult")

        # <summary>
        total = len(plan_cases)
        passed = total  # 压测模式：用例级别不记 PASS/FAIL，只记聚合
        failed = 1 if summary_data.get("error_rate_pct", 0) > 5.0 else 0
        summary_el = ET.SubElement(root, "summary")
        summary_el.set("total",       str(total))
        summary_el.set("passed",      str(passed))
        summary_el.set("failed",      str(failed))
        summary_el.set("pass_rate",   f"{100.0 - summary_data.get('error_rate_pct', 0):.1f}%")
        summary_el.set("total_time",  f"{duration}s")
        summary_el.set("start_time",  ts)
        summary_el.set("end_time",    datetime.now().strftime("%Y%m%d_%H%M%S"))

        # <results>
        results_el = ET.SubElement(root, "results")
        ep_map = {ep["name"]: ep for ep in endpoints_data}
        for case_cfg in plan_cases:
            case_id = case_cfg["id"]
            result_el = ET.SubElement(results_el, "result")
            result_el.set("case_id", case_id)
            result_el.set("status", "PASS")
            ep = ep_map.get(case_id) or {}
            if ep:
                result_el.set("load_requests", str(ep.get("requests", 0)))
                result_el.set("load_failures", str(ep.get("failures", 0)))
                result_el.set("load_p95_ms",   str(ep.get("p95_ms", 0)))

        # <load_summary>
        ls_el = ET.SubElement(root, "load_summary")
        ls_el.set("total_requests",   str(summary_data.get("total_requests", 0)))
        ls_el.set("total_failures",   str(summary_data.get("total_failures", 0)))
        ls_el.set("error_rate_pct",   str(summary_data.get("error_rate_pct", 0)))
        ls_el.set("rps_avg",          str(summary_data.get("rps_avg", 0)))
        ls_el.set("rps_peak",         str(summary_data.get("rps_peak", 0)))
        ls_el.set("duration_seconds", str(duration))
        ls_el.set("concurrency",      str(concurrency))

        lat_el = ET.SubElement(ls_el, "latency")
        lat_el.set("p50_ms", str(summary_data.get("p50_ms", 0)))
        lat_el.set("p75_ms", str(summary_data.get("p75_ms", 0)))
        lat_el.set("p95_ms", str(summary_data.get("p95_ms", 0)))
        lat_el.set("p99_ms", str(summary_data.get("p99_ms", 0)))
        lat_el.set("avg_ms", str(summary_data.get("avg_ms", 0.0)))
        lat_el.set("max_ms", str(summary_data.get("max_ms", 0)))

        if endpoints_data:
            eps_el = ET.SubElement(ls_el, "endpoints")
            for ep in endpoints_data:
                ep_el = ET.SubElement(eps_el, "endpoint")
                ep_el.set("name",      ep["name"])
                ep_el.set("requests",  str(ep["requests"]))
                ep_el.set("failures",  str(ep["failures"]))
                ep_el.set("rps_avg",   str(ep.get("rps_avg", 0)))
                ep_el.set("p95_ms",    str(ep["p95_ms"]))

        # 写入文件（UTF-8，带 XML 声明）
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        tree.write(str(result_path), encoding="utf-8", xml_declaration=True)

        return result_path
