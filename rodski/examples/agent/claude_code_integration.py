#!/usr/bin/env python3
"""
Claude Code 集成示例 - Complete Claude Code Integration Example

本示例展示如何在 Claude Code 中集成 RodSki 测试执行能力。
通过 subprocess 调用 RodSki CLI，获取结构化 JSON 结果，
并将结果反馈给 Claude Code 进行分析和决策。

使用方式:
    # Claude Code 中执行
    /rodski run case.xml

    # 或通过脚本调用
    python examples/agent/claude_code_integration.py <case.xml> [-v KEY=VALUE...]
"""

import subprocess
import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class RodsKiResult:
    """RodSki 执行结果封装"""
    status: str  # "success" | "failed" | "error"
    exit_code: int
    summary: Dict[str, int]
    steps: List[Dict[str, Any]]
    error: Optional[Dict[str, str]] = None
    failed_step: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None
    variables: Optional[Dict[str, Any]] = None


class RodsKiExecutor:
    """RodSki 执行器封装"""

    def __init__(self, rodski_bin: str = "rodski"):
        self.rodski_bin = rodski_bin

    def run_case(
        self,
        case_path: str,
        variables: Optional[Dict[str, str]] = None,
        output_format: str = "json",
        dry_run: bool = False,
        step_by_step: bool = False,
        verbose: bool = False,
    ) -> RodsKiResult:
        """
        执行单个测试用例

        Args:
            case_path: 用例文件路径
            variables: 变量字典
            output_format: 输出格式 (json/text)
            dry_run: 干跑模式 (仅验证不执行)
            step_by_step: 单步执行模式
            verbose: 详细输出

        Returns:
            RodsKiResult: 结构化执行结果
        """
        cmd = [self.rodski_bin, "run", case_path, "--output-format", output_format]

        if dry_run:
            cmd.append("--dry-run")
        if step_by_step:
            cmd.append("--step-by-step")
        if verbose:
            cmd.append("--verbose")

        if variables:
            for k, v in variables.items():
                cmd.extend(["-v", f"{k}={v}"])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )

        return self._parse_result(result, case_path)

    def explain_case(self, case_path: str, sensitive: bool = False) -> str:
        """
        解释测试用例为自然语言

        Args:
            case_path: 用例文件路径
            sensitive: 是否脱敏敏感字段

        Returns:
            str: 自然语言解释
        """
        cmd = [self.rodski_bin, "explain", case_path]
        if sensitive:
            cmd.append("--sensitive")

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.stdout if result.returncode == 0 else result.stderr

    def validate_case(self, case_path: str) -> Dict[str, Any]:
        """
        验证用例 XML 格式

        Args:
            case_path: 用例文件路径

        Returns:
            dict: 验证结果
        """
        cmd = [self.rodski_bin, "validate", case_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"valid": result.returncode == 0, "message": result.stdout}

    def _parse_result(self, subprocess_result: subprocess.CompletedProcess, case_path: str) -> RodsKiResult:
        """解析 subprocess 结果为 RodsKiResult"""
        try:
            data = json.loads(subprocess_result.stdout)
        except json.JSONDecodeError:
            return RodsKiResult(
                status="error",
                exit_code=subprocess_result.returncode,
                summary={"total": 0, "passed": 0, "failed": 0, "skipped": 0},
                steps=[],
                error={"type": "ParseError", "message": subprocess_result.stderr or "无法解析输出"},
            )

        return RodsKiResult(
            status=data.get("status", "error"),
            exit_code=subprocess_result.returncode,
            summary=data.get("summary", {}),
            steps=data.get("steps", []),
            error=data.get("error"),
            failed_step=data.get("failed_step"),
            context=data.get("context"),
            variables=data.get("variables"),
        )


class ClaudeCodeAgent:
    """Claude Code Agent 集成类"""

    def __init__(self, executor: Optional[RodsKiExecutor] = None):
        self.executor = executor or RodsKiExecutor()

    def execute_and_report(self, case_path: str, variables: Optional[Dict[str, str]] = None) -> str:
        """
        执行用例并生成报告

        Returns:
            str: Claude Code 友好的报告文本
        """
        result = self.executor.run_case(case_path, variables=variables, verbose=True)

        lines = []
        lines.append(f"📊 RodSki 执行报告 — {Path(case_path).name}")
        lines.append(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        if result.status == "success":
            summary = result.summary
            total = summary.get("total", 0)
            passed = summary.get("passed", 0)
            failed = summary.get("failed", 0)
            skipped = summary.get("skipped", 0)
            pass_rate = (passed / total * 100) if total > 0 else 0

            lines.append(f"✅ 全部通过 ({passed}/{total}, {pass_rate:.0f}%)")
            lines.append(f"   通过: {passed} | 失败: {failed} | 跳过: {skipped}")

        elif result.status == "failed":
            lines.append(f"❌ 测试失败")

            if result.error:
                error = result.error
                lines.append(f"   错误类型: {error.get('type', 'Unknown')}")
                lines.append(f"   错误消息: {error.get('message', '')}")

            if result.failed_step:
                fs = result.failed_step
                lines.append(f"   失败用例: {fs.get('case_id', 'N/A')}")
                lines.append(f"   失败步骤: #{fs.get('index', '?')}")
                lines.append(f"   关键字: {fs.get('keyword', 'N/A')}")

            if result.context:
                ctx = result.context
                if ctx.get("screenshot"):
                    lines.append(f"   截图: {ctx['screenshot']}")
                if ctx.get("url"):
                    lines.append(f"   当前URL: {ctx['url']}")

        else:
            lines.append(f"⚠️  执行异常 (exit_code={result.exit_code})")
            if result.error:
                lines.append(f"   {result.error.get('message', '')}")

        lines.append("")
        lines.append("RodSki 执行完成。")

        return "\n".join(lines)

    def diagnose_failure(self, case_path: str) -> str:
        """
        分析测试失败原因（需要 AI 诊断能力）

        需要配置 AI 视觉诊断:
            config:
              vision.ai_verifier.enabled: true
              vision.ai_verifier.model_provider: claude
        """
        result = self.executor.run_case(case_path, verbose=True)

        if result.status == "success":
            return "✅ 测试通过，无需诊断"

        diagnosis_lines = ["🔍 失败诊断报告", ""]

        if result.error:
            diagnosis_lines.append(f"**错误类型**: {result.error.get('type')}")
            diagnosis_lines.append(f"**错误消息**: {result.error.get('message')}")

        if result.failed_step:
            fs = result.failed_step
            diagnosis_lines.append(f"**失败位置**: {fs.get('case_id')} 步骤 #{fs.get('index')}")

        if result.context:
            ctx = result.context
            if ctx.get("screenshot"):
                diagnosis_lines.append(f"**截图文件**: {ctx['screenshot']}")

        diagnosis_lines.append("")
        diagnosis_lines.append("建议: 检查元素定位器、等待时间或网络条件。")
        diagnosis_lines.append("可使用 `rodski run --step-by-step` 逐步调试。")

        return "\n".join(diagnosis_lines)


def main():
    parser = argparse.ArgumentParser(
        description="Claude Code RodSki 集成示例"
    )
    parser.add_argument(
        "case_path",
        help="测试用例文件路径 (XML)"
    )
    parser.add_argument(
        "-v", "--variable",
        action="append",
        dest="variables",
        help="变量注入 (格式: KEY=VALUE)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="干跑模式 (仅验证)"
    )
    parser.add_argument(
        "--step-by-step",
        action="store_true",
        help="单步执行模式"
    )
    parser.add_argument(
        "--explain",
        action="store_true",
        help="解释用例为自然语言"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="验证用例格式"
    )
    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="诊断失败原因"
    )

    args = parser.parse_args()

    # 解析变量
    variables = {}
    if args.variables:
        for v in args.variables:
            if "=" in v:
                k, val = v.split("=", 1)
                variables[k] = val

    executor = RodsKiExecutor()

    if args.explain:
        output = executor.explain_case(args.case_path)
        print(output)
        return 0

    if args.validate:
        result = executor.validate_case(args.case_path)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    if args.diagnose:
        agent = ClaudeCodeAgent(executor)
        print(agent.diagnose_failure(args.case_path))
        return 0

    # 默认：执行并报告
    agent = ClaudeCodeAgent(executor)
    print(agent.execute_and_report(args.case_path, variables))

    return 0


if __name__ == "__main__":
    sys.exit(main())
