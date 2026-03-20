"""性能分析器 - 统计和报告"""
import time
import json
import psutil
from typing import Dict, List
from dataclasses import dataclass, asdict


@dataclass
class PerfRecord:
    keyword: str
    duration: float
    success: bool
    timestamp: float


class Profiler:
    def __init__(self):
        self.records: List[PerfRecord] = []
        self.start_time = time.time()
        self.start_memory = psutil.Process().memory_info().rss / 1024 / 1024

    def record(self, keyword: str, duration: float, success: bool):
        self.records.append(PerfRecord(keyword, duration, success, time.time()))

    def get_stats(self) -> Dict:
        if not self.records:
            return {}
        
        total = len(self.records)
        success = sum(1 for r in self.records if r.success)
        total_time = sum(r.duration for r in self.records)
        
        by_keyword = {}
        for r in self.records:
            if r.keyword not in by_keyword:
                by_keyword[r.keyword] = {"count": 0, "total_time": 0, "failures": 0}
            by_keyword[r.keyword]["count"] += 1
            by_keyword[r.keyword]["total_time"] += r.duration
            if not r.success:
                by_keyword[r.keyword]["failures"] += 1
        
        current_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        return {
            "total_keywords": total,
            "success_rate": f"{success/total*100:.1f}%",
            "total_time": f"{total_time:.2f}s",
            "avg_time": f"{total_time/total:.3f}s",
            "memory_used": f"{current_memory - self.start_memory:.1f}MB",
            "by_keyword": {k: {
                "count": v["count"],
                "avg_time": f"{v['total_time']/v['count']:.3f}s",
                "failures": v["failures"]
            } for k, v in by_keyword.items()}
        }

    def save_json(self, path: str):
        """保存 JSON 格式报告"""
        stats = self.get_stats()
        stats["total_operations"] = len(self.records)
        stats["slow_operations"] = sum(1 for r in self.records if r.duration > 1.0)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)

    def save_html(self, path: str):
        """保存 HTML 格式报告"""
        stats = self.get_stats()
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>性能报告</title>
<style>body{{font-family:sans-serif;margin:20px}}table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #ddd;padding:8px;text-align:left}}th{{background:#4CAF50;color:white}}</style>
</head><body><h1>SKI 性能报告</h1>
<h2>总览</h2><ul>
<li>总操作数: {len(self.records)}</li>
<li>成功率: {stats.get('success_rate', 'N/A')}</li>
<li>总耗时: {stats.get('total_time', 'N/A')}</li>
<li>平均耗时: {stats.get('avg_time', 'N/A')}</li>
<li>内存使用: {stats.get('memory_used', 'N/A')}</li>
</ul><h2>关键字统计</h2><table><tr><th>关键字</th><th>次数</th><th>平均耗时</th><th>失败数</th></tr>"""
        for kw, data in stats.get('by_keyword', {}).items():
            html += f"<tr><td>{kw}</td><td>{data['count']}</td><td>{data['avg_time']}</td><td>{data['failures']}</td></tr>"
        html += "</table></body></html>"
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
