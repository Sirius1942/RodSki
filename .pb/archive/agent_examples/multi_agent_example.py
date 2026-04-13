#!/usr/bin/env python3
"""
多 Agent 协作示例 - Multi-Agent Collaboration Example

本示例展示多个 Agent 如何通过 RodSki 协作完成复杂的测试任务。

协作模式:
    Agent A (规划者) → Agent B (执行者) → Agent C (分析师)
         │                   │                  │
         ├─ 生成测试计划      ├─ 执行测试用例      ├─ 分析结果
         ├─ 分解任务         ├─ 处理失败         ├─ 生成报告
         └─ 分配给执行者      └─ 重试恢复         └─ 提出建议

共享状态通过文件系统传递 (agent_state.json)

使用方式:
    python examples/agent/multi_agent_example.py <test_suite_dir>
"""

import subprocess
import json
import sys
import shutil
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum


class AgentRole(Enum):
    PLANNER = "planner"       # 规划者: 制定测试计划
    EXECUTOR = "executor"     # 执行者: 运行测试用例
    ANALYZER = "analyzer"     # 分析师: 分析测试结果


class AgentState:
    """Agent 共享状态"""

    STATE_FILE = "agent_state.json"

    def __init__(self, state_dir: str = "."):
        self.state_dir = Path(state_dir)
        self.state_file = self.state_dir / self.STATE_FILE
        self._state: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text())
            except json.JSONDecodeError:
                pass
        return {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "plan": None,
            "executions": [],
            "analysis": None,
        }

    def save(self):
        self._state["updated_at"] = datetime.now().isoformat()
        self.state_file.write_text(
            json.dumps(self._state, indent=2, ensure_ascii=False)
        )

    def set_plan(self, plan: Dict[str, Any]):
        self._state["plan"] = plan
        self.save()

    def add_execution(self, execution: Dict[str, Any]):
        self._state["executions"].append(execution)
        self.save()

    def set_analysis(self, analysis: Dict[str, Any]):
        self._state["analysis"] = analysis
        self.save()

    @property
    def plan(self) -> Optional[Dict[str, Any]]:
        return self._state.get("plan")

    @property
    def executions(self) -> List[Dict[str, Any]]:
        return self._state.get("executions", [])

    @property
    def analysis(self) -> Optional[Dict[str, Any]]:
        return self._state.get("analysis")


class PlannerAgent:
    """规划者 Agent — 分析需求，制定测试计划"""

    def __init__(self, state: AgentState):
        self.state = state

    def analyze_requirements(self, test_suite_dir: str) -> Dict[str, Any]:
        """
        分析测试套件目录，生成测试计划

        Returns:
            dict: 测试计划
        """
        suite_path = Path(test_suite_dir)
        case_files = list(suite_path.rglob("*.xml"))

        # 分析每个用例
        case_analysis = []
        for case_file in case_files:
            try:
                import xml.etree.ElementTree as ET
                tree = ET.parse(case_file)
                root = tree.getroot()

                cases = root.findall(".//case")
                for case in cases:
                    case_analysis.append({
                        "id": case.get("id", "unknown"),
                        "title": case.get("title", ""),
                        "priority": case.get("priority", "medium"),
                        "component": case.get("component", "unknown"),
                        "file": str(case_file.relative_to(suite_path.parent)),
                        "step_count": len(case.findall(".//test_step")),
                    })
            except Exception as e:
                print(f"警告: 解析 {case_file} 失败: {e}")

        plan = {
            "suite_dir": test_suite_dir,
            "total_cases": len(case_analysis),
            "cases": case_analysis,
            "execution_order": "sequential",  # 后续可扩展为智能排序
            "estimated_duration_minutes": len(case_analysis) * 2,  # 粗略估计
        }

        self.state.set_plan(plan)
        return plan

    def generate_report(self) -> str:
        """生成规划报告"""
        plan = self.state.plan
        if not plan:
            return "错误: 未找到测试计划"

        lines = []
        lines.append("📋 测试规划报告")
        lines.append(f"总用例数: {plan['total_cases']}")
        lines.append(f"预计耗时: {plan['estimated_duration_minutes']} 分钟")
        lines.append("")
        lines.append("用例列表:")
        for case in plan["cases"]:
            lines.append(
                f"  [{case['priority']}] {case['id']}: {case['title']} "
                f"({case['step_count']} 步, {case['component']})"
            )
        return "\n".join(lines)


class ExecutorAgent:
    """执行者 Agent — 运行测试，处理失败和恢复"""

    def __init__(self, state: AgentState):
        self.state = state

    def execute_case(self, case_path: str, variables: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        执行单个测试用例

        Returns:
            dict: 执行结果
        """
        cmd = ["rodski", "run", case_path, "--output-format", "json"]

        if variables:
            for k, v in variables.items():
                cmd.extend(["-v", f"{k}={v}"])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
            data = json.loads(result.stdout) if result.stdout else {}
            return {
                "case_path": case_path,
                "status": data.get("status", "error"),
                "exit_code": result.returncode,
                "summary": data.get("summary", {}),
                "error": data.get("error"),
                "failed_step": data.get("failed_step"),
                "timestamp": datetime.now().isoformat(),
            }
        except subprocess.TimeoutExpired:
            return {
                "case_path": case_path,
                "status": "timeout",
                "exit_code": 124,
                "summary": {},
                "error": {"type": "TimeoutError", "message": "执行超时"},
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "case_path": case_path,
                "status": "exception",
                "exit_code": 1,
                "summary": {},
                "error": {"type": type(e).__name__, "message": str(e)},
                "timestamp": datetime.now().isoformat(),
            }

    def execute_plan(self, plan: Dict[str, Any], variables: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """
        按计划执行所有用例

        Returns:
            List[dict]: 所有执行结果
        """
        results = []

        for case in plan["cases"]:
            case_path = str(Path(plan["suite_dir"]).parent / case["file"])
            print(f"执行: {case['id']}...")

            result = self.execute_case(case_path, variables)
            results.append(result)
            self.state.add_execution(result)

            status_symbol = "✅" if result["status"] == "success" else "❌"
            print(f"  {status_symbol} {case['id']}: {result['status']}")

            if result["status"] != "success" and result.get("error"):
                print(f"     错误: {result['error'].get('message', '')}")

        return results


class AnalyzerAgent:
    """分析师 Agent — 分析执行结果，生成诊断报告"""

    def __init__(self, state: AgentState):
        self.state = state

    def analyze(self) -> Dict[str, Any]:
        """
        分析执行结果，生成诊断报告

        Returns:
            dict: 分析报告
        """
        executions = self.state.executions
        if not executions:
            return {"error": "无执行结果可分析"}

        total = len(executions)
        passed = sum(1 for e in executions if e["status"] == "success")
        failed = sum(1 for e in executions if e["status"] != "success")

        # 按错误类型分组
        error_groups: Dict[str, List[Dict]] = {}
        for exec_result in executions:
            if exec_result["status"] != "success":
                error_type = exec_result.get("error", {}).get("type", "Unknown")
                if error_type not in error_groups:
                    error_groups[error_type] = []
                error_groups[error_type].append(exec_result)

        # 识别 flaky cases
        flaky = []
        case_ids = {}
        for exec_result in executions:
            case_id = exec_result["case_path"]
            if case_id not in case_ids:
                case_ids[case_id] = []
            case_ids[case_id].append(exec_result["status"])

        for case_id, statuses in case_ids.items():
            pass_count = statuses.count("success")
            if 0 < pass_count < len(statuses):  # 有通过也有失败
                flaky.append({
                    "case_id": case_id,
                    "pass_rate": pass_count / len(statuses),
                    "runs": len(statuses),
                })

        analysis = {
            "total_cases": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": (passed / total * 100) if total > 0 else 0,
            "error_groups": {
                error_type: len(cases) for error_type, cases in error_groups.items()
            },
            "flaky_cases": flaky,
            "recommendations": self._generate_recommendations(error_groups, flaky),
            "timestamp": datetime.now().isoformat(),
        }

        self.state.set_analysis(analysis)
        return analysis

    def _generate_recommendations(
        self,
        error_groups: Dict[str, List[Dict]],
        flaky: List[Dict]
    ) -> List[str]:
        """根据分析结果生成建议"""
        recommendations = []

        if "ElementNotFoundError" in error_groups:
            recommendations.append(
                "⚠️  元素未找到错误较多，建议检查页面定位器是否稳定"
            )
        if "TimeoutError" in error_groups:
            recommendations.append(
                "⏱️  超时错误较多，建议增加等待时间或检查网络条件"
            )
        if flaky:
            recommendations.append(
                f"🔄 发现 {len(flaky)} 个不稳定用例 (flaky cases)，建议优先排查"
            )

        if not recommendations:
            recommendations.append("✅ 未发现明显问题，测试结果正常")

        return recommendations

    def generate_report(self) -> str:
        """生成分析报告"""
        analysis = self.state.analysis
        if not analysis:
            return "错误: 未找到分析结果"

        lines = []
        lines.append("")
        lines.append("=" * 60)
        lines.append("  🔍 RodSki 多 Agent 测试分析报告")
        lines.append("=" * 60)
        lines.append(f"  总用例数:   {analysis['total_cases']}")
        lines.append(f"  ✅ 通过:     {analysis['passed']}")
        lines.append(f"  ❌ 失败:     {analysis['failed']}")
        lines.append(f"  📈 通过率:   {analysis['pass_rate']:.1f}%")
        lines.append("")

        if analysis.get("error_groups"):
            lines.append("  错误类型分布:")
            for error_type, count in analysis["error_groups"].items():
                lines.append(f"    {error_type}: {count} 次")
            lines.append("")

        if analysis.get("flaky_cases"):
            lines.append("  🔄 不稳定用例 (Flaky Cases):")
            for fc in analysis["flaky_cases"]:
                lines.append(
                    f"    - {fc['case_id']}: "
                    f"pass_rate={fc['pass_rate']:.0%}, runs={fc['runs']}"
                )
            lines.append("")

        lines.append("  💡 建议:")
        for rec in in analysis.get("recommendations", []):
            lines.append(f"    {rec}")

        lines.append("=" * 60)
        lines.append("")

        return "\n".join(lines)


def run_multi_agent_workflow(test_suite_dir: str, variables: Optional[Dict[str, str]] = None) -> str:
    """
    运行完整的多 Agent 工作流

    1. PlannerAgent 分析需求，制定测试计划
    2. ExecutorAgent 按计划执行所有用例
    3. AnalyzerAgent 分析结果，生成诊断报告
    """
    print("🚀 启动 RodSki 多 Agent 工作流")
    print(f"测试套件: {test_suite_dir}")
    print("")

    # 初始化共享状态
    state = AgentState()

    # Phase 1: 规划
    print("📋 Phase 1: 规划者 Agent — 制定测试计划")
    planner = PlannerAgent(state)
    plan = planner.analyze_requirements(test_suite_dir)
    print(planner.generate_report())
    print("")

    # Phase 2: 执行
    print("📋 Phase 2: 执行者 Agent — 运行测试")
    executor = ExecutorAgent(state)
    executions = executor.execute_plan(plan, variables)
    print(f"\n执行完成: {sum(1 for e in executions if e['status']=='success')}/{len(executions)} 通过")
    print("")

    # Phase 3: 分析
    print("📋 Phase 3: 分析师 Agent — 分析结果")
    analyzer = AnalyzerAgent(state)
    analysis = analyzer.analyze()
    report = analyzer.generate_report()
    print(report)

    # 保存最终报告
    report_path = Path("output/multi_agent_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps({
            "plan": state.plan,
            "executions": state.executions,
            "analysis": state.analysis,
        }, indent=2, ensure_ascii=False)
    )
    print(f"📄 完整报告已保存: {report_path}")

    return report


def main():
    parser = argparse.ArgumentParser(
        description="RodSki 多 Agent 协作示例"
    )
    parser.add_argument(
        "test_suite_dir",
        help="测试套件目录"
    )
    parser.add_argument(
        "-v", "--variable",
        action="append",
        dest="variables",
        help="全局变量 (格式: KEY=VALUE)"
    )
    parser.add_argument(
        "--skip-planner",
        action="store_true",
        help="跳过规划阶段"
    )
    parser.add_argument(
        "--skip-analyzer",
        action="store_true",
        help="跳过分析阶段"
    )

    args = parser.parse_args()

    variables = {}
    if args.variables:
        for v in args.variables:
            if "=" in v:
                k, val = v.split("=", 1)
                variables[k] = val

    report = run_multi_agent_workflow(args.test_suite_dir, variables)
    return 0


if __name__ == "__main__":
    sys.exit(main())
