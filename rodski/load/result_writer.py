"""LoadResultWriter — 压测结果 XML 写入器。
生成含 <load_summary> 节点的 result XML，兼容 result.xsd。
每次压测后同时将 perf/{plan_id}.py 归档到 result/ 目录，确保产物可追溯。
"""
from __future__ import annotations
import shutil
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
        """生成 result/result_{timestamp}.xml，返回文件路径。
        同时将本次使用的 perf/{plan_id}.py 归档到 result/{plan_id}_{timestamp}.py。
        """
        module_dir = Path(module_dir)
        result_dir = module_dir / "result"
        result_dir.mkdir(exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_path = result_dir / f"result_{ts}.xml"

        plan_id     = plan.get("id", "load")
        profile     = plan.get("load_profile", {})
        duration    = int(profile.get("duration_seconds", 0))
        concurrency = int(profile.get("concurrency", 0))

        summary_data   = stats.summary()
        endpoints_data = stats.per_endpoint()
        plan_cases     = [c for c in plan.get("cases", []) if c.get("execute") == "是"]

        root = ET.Element("testresult")

        # <summary>
        total  = len(plan_cases)
        failed = 1 if summary_data.get("error_rate_pct", 0) > 5.0 else 0
        summary_el = ET.SubElement(root, "summary")
        summary_el.set("total",       str(total))
        summary_el.set("passed",      str(total - failed))
        summary_el.set("failed",      str(failed))
        summary_el.set("pass_rate",   f"{100.0 - summary_data.get('error_rate_pct', 0):.1f}%")
        summary_el.set("total_time",  f"{duration}s")
        summary_el.set("start_time",  ts)
        summary_el.set("end_time",    datetime.now().strftime("%Y%m%d_%H%M%S"))

        # <results>（按 weight 均摊估算各 case 请求量）
        results_el   = ET.SubElement(root, "results")
        total_req    = summary_data.get("total_requests", 0)
        total_fail   = summary_data.get("total_failures", 0)
        global_p95   = summary_data.get("p95_ms", 0)
        total_weight = sum(int(c.get("weight", 1)) for c in plan_cases)
        for case_cfg in plan_cases:
            case_id = case_cfg["id"]
            weight  = int(case_cfg.get("weight", 1))
            result_el = ET.SubElement(results_el, "result")
            result_el.set("case_id",       case_id)
            result_el.set("status",        "FAIL" if failed else "PASS")
            result_el.set("load_requests", str(int(total_req  * weight / max(total_weight, 1))))
            result_el.set("load_failures", str(int(total_fail * weight / max(total_weight, 1))))
            result_el.set("load_p95_ms",   str(global_p95))

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

        # 写入 result XML
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        tree.write(str(result_path), encoding="utf-8", xml_declaration=True)

        # ── 归档 perf/{plan_id}.py 到 result/ ────────────────────────────────
        # 每次压测结束后，将本次使用的编译产物复制一份到 result/ 目录，
        # 文件名含时间戳，与 result_{ts}.xml 一一对应，确保可追溯。
        perf_src = module_dir / "perf" / f"{plan_id}.py"
        if perf_src.exists():
            perf_archive = result_dir / f"{plan_id}_{ts}.py"
            shutil.copy2(str(perf_src), str(perf_archive))
        # ─────────────────────────────────────────────────────────────────────

        return result_path

