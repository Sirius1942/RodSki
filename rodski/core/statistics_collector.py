"""Statistics collection and aggregation for test results"""
import xml.etree.ElementTree as ET
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional


@dataclass
class StepStatistics:
    """Statistics for a specific keyword/action"""
    keyword: str
    count: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    durations_ms: List[float] = field(default_factory=list)

    @property
    def avg(self) -> float:
        return sum(self.durations_ms) / len(self.durations_ms) if self.durations_ms else 0.0

    @property
    def p50(self) -> float:
        if not self.durations_ms:
            return 0.0
        sorted_durations = sorted(self.durations_ms)
        return sorted_durations[len(sorted_durations) // 2]

    @property
    def p95(self) -> float:
        if not self.durations_ms:
            return 0.0
        sorted_durations = sorted(self.durations_ms)
        idx = int(len(sorted_durations) * 0.95)
        return sorted_durations[min(idx, len(sorted_durations) - 1)]

    @property
    def p99(self) -> float:
        if not self.durations_ms:
            return 0.0
        sorted_durations = sorted(self.durations_ms)
        idx = int(len(sorted_durations) * 0.99)
        return sorted_durations[min(idx, len(sorted_durations) - 1)]


@dataclass
class CaseStatistics:
    """Statistics for a specific test case"""
    case_id: str
    run_count: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    step_stats: Dict[str, StepStatistics] = field(default_factory=dict)

    @property
    def pass_rate(self) -> float:
        total = self.passed + self.failed
        return (self.passed / total * 100) if total > 0 else 0.0

    @property
    def avg_duration(self) -> float:
        all_durations = []
        for stats in self.step_stats.values():
            all_durations.extend(stats.durations_ms)
        return sum(all_durations) / len(all_durations) if all_durations else 0.0


@dataclass
class RunStatistics:
    """Statistics for a single test run"""
    run_id: str
    run_time: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    total_duration: float = 0.0

    @property
    def pass_rate(self) -> float:
        total = self.passed + self.failed
        return (self.passed / total * 100) if total > 0 else 0.0


@dataclass
class AggregatedStatistics:
    """Aggregated statistics across all runs"""
    total_runs: int = 0
    case_stats: Dict[str, CaseStatistics] = field(default_factory=dict)
    run_stats: List[RunStatistics] = field(default_factory=list)
    global_step_stats: Dict[str, StepStatistics] = field(default_factory=dict)


class StatisticsCollector:
    """Collect and aggregate test statistics"""

    def __init__(self):
        self.case_stats: Dict[str, CaseStatistics] = {}
        self.run_stats: List[RunStatistics] = []
        self.global_step_stats: Dict[str, StepStatistics] = {}

    def add_result(self, result_xml_path: str):
        """Parse and accumulate result from XML file"""
        tree = ET.parse(result_xml_path)
        root = tree.getroot()

        summary = root.find('summary')
        if summary is not None:
            run_stat = RunStatistics(
                run_id=Path(result_xml_path).stem,
                run_time=summary.get('start_time', ''),
                total=int(summary.get('total', 0)),
                passed=int(summary.get('passed', 0)),
                failed=int(summary.get('failed', 0)),
                skipped=int(summary.get('skipped', 0)),
                total_duration=float(summary.get('total_time', 0) or 0)
            )
            self.run_stats.append(run_stat)

        results = root.find('results')
        if results is not None:
            for result in results.findall('result'):
                self._process_result(result)

    def _process_result(self, result: ET.Element):
        """Process individual result element"""
        case_id = result.get('case_id', '')
        status = result.get('status', '')

        if case_id not in self.case_stats:
            self.case_stats[case_id] = CaseStatistics(case_id=case_id)

        case_stat = self.case_stats[case_id]
        case_stat.run_count += 1

        if status == 'PASS':
            case_stat.passed += 1
        elif status == 'FAIL':
            case_stat.failed += 1
        elif status == 'SKIP':
            case_stat.skipped += 1

        for step in result.findall('step'):
            self._process_step(step, case_stat)

    def _process_step(self, step: ET.Element, case_stat: CaseStatistics):
        """Process step statistics"""
        action = step.get('action', '')
        duration = float(step.get('duration_ms', 0) or 0)
        status = step.get('status', 'PASS')

        if action not in case_stat.step_stats:
            case_stat.step_stats[action] = StepStatistics(keyword=action)
        if action not in self.global_step_stats:
            self.global_step_stats[action] = StepStatistics(keyword=action)

        step_stat = case_stat.step_stats[action]
        global_stat = self.global_step_stats[action]

        for stat in [step_stat, global_stat]:
            stat.count += 1
            if duration > 0:
                stat.durations_ms.append(duration)
            if status == 'PASS':
                stat.passed += 1
            elif status == 'FAIL':
                stat.failed += 1
            elif status == 'SKIP':
                stat.skipped += 1

    def aggregate(self) -> AggregatedStatistics:
        """Aggregate all collected statistics"""
        return AggregatedStatistics(
            total_runs=len(self.run_stats),
            case_stats=self.case_stats,
            run_stats=self.run_stats,
            global_step_stats=self.global_step_stats
        )

    def get_flaky_cases(self, threshold: float = 0.3) -> List[str]:
        """Get cases with pass rate below threshold"""
        flaky = []
        for case_id, stats in self.case_stats.items():
            if stats.run_count > 1 and 0 < stats.pass_rate < (threshold * 100):
                flaky.append(case_id)
        return flaky

    def export_json(self, output_path: str):
        """Export statistics to JSON file"""
        agg = self.aggregate()
        data = {
            'total_runs': agg.total_runs,
            'cases': {
                cid: {
                    'run_count': cs.run_count,
                    'passed': cs.passed,
                    'failed': cs.failed,
                    'skipped': cs.skipped,
                    'pass_rate': cs.pass_rate,
                    'avg_duration': cs.avg_duration
                }
                for cid, cs in agg.case_stats.items()
            },
            'runs': [
                {
                    'run_id': rs.run_id,
                    'run_time': rs.run_time,
                    'total': rs.total,
                    'passed': rs.passed,
                    'failed': rs.failed,
                    'pass_rate': rs.pass_rate
                }
                for rs in agg.run_stats
            ]
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def daily_trend(self) -> Dict[str, Dict]:
        """Get daily trend statistics"""
        daily = {}
        for run in self.run_stats:
            date = run.run_time.split('T')[0] if 'T' in run.run_time else run.run_time[:10]
            if date not in daily:
                daily[date] = {'total': 0, 'passed': 0, 'failed': 0}
            daily[date]['total'] += run.total
            daily[date]['passed'] += run.passed
            daily[date]['failed'] += run.failed
        return daily

    def by_priority(self) -> Dict[str, int]:
        """Get statistics by priority (placeholder)"""
        return {}

    def by_component(self) -> Dict[str, int]:
        """Get statistics by component (placeholder)"""
        return {}

