#!/usr/bin/env python3
"""
OpenCode / Gemini CLI 集成示例 - OpenCode / Gemini CLI Integration Example

本示例展示如何将 RodSki 集成到 OpenCode、Gemini CLI 或其他支持
外部命令调用的 AI Agent 框架中。

核心设计:
- 同步调用模式: 等待 RodSki 执行完成后获取结果
- 异步调用模式: 启动后台执行，定期轮询状态
- 批处理模式: 批量执行多个用例，汇总结果

使用方式:
    python examples/agent/opencode_integration.py run <case.xml>
    python examples/agent/opencode_integration.py batch <case_dir>
    python examples/agent/opencode_integration.py parallel <case_dir> --workers 4
"""

import subprocess
import json
import sys
import time
import argparse
import os
import glob
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime


@dataclass
class ExecutionRequest:
    """执行请求"""
    case_path: str
    variables: Dict[str, str]
    timeout: int = 300
    retry_count: int = 0
    retry_delay: int = 5


@dataclass
class ExecutionResponse:
    """执行响应"""
    success: bool
    case_path: str
    status: str
    exit_code: int
    duration_seconds: float
    summary: Dict[str, int]
    error: Optional[Dict[str, Any]] = None
    output_path: Optional[str] = None


class OpenCodeRodsKiClient:
    """OpenCode / Gemini CLI RodSki 客户端"""

    def __init__(self, rodski_cmd: str = "rodski", work_dir: str = "."):
        self.rodski_cmd = rodski_cmd
        self.work_dir = Path(work_dir)
        self.last_result: Optional[Dict[str, Any]] = None

    def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        """
        同步执行单个用例

        Args:
            request: 执行请求

        Returns:
            ExecutionResponse: 执行结果
        """
        start_time = time.time()

        cmd = [
            self.rodski_cmd, "run",
            request.case_path,
            "--output-format", "json"
        ]

        for k, v in request.variables.items():
            cmd.extend(["-v", f"{k}={v}"])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=request.timeout,
                cwd=self.work_dir,
            )
        except subprocess.TimeoutExpired:
            return ExecutionResponse(
                success=False,
                case_path=request.case_path,
                status="timeout",
                exit_code=124,
                duration_seconds=request.timeout,
                summary={},
                error={"type": "TimeoutError", "message": f"执行超时 ({request.timeout}s)"},
            )

        duration = time.time() - start_time

        try:
            data = json.loads(result.stdout) if result.stdout else {}
            self.last_result = data

            return ExecutionResponse(
                success=(result.returncode == 0),
                case_path=request.case_path,
                status=data.get("status", "error"),
                exit_code=result.returncode,
                duration_seconds=duration,
                summary=data.get("summary", {}),
                error=data.get("error"),
            )
        except json.JSONDecodeError:
            return ExecutionResponse(
                success=False,
                case_path=request.case_path,
                status="parse_error",
                exit_code=result.returncode,
                duration_seconds=duration,
                summary={},
                error={"type": "ParseError", "message": result.stderr or "无法解析输出"},
            )

    def execute_with_retry(self, request: ExecutionRequest) -> ExecutionResponse:
        """
        带重试的执行

        Args:
            request: 执行请求 (包含 retry_count)

        Returns:
            ExecutionResponse: 最终执行结果
        """
        last_response: Optional[ExecutionResponse] = None

        for attempt in range(request.retry_count + 1):
            response = self.execute(request)

            if response.success:
                return response

            if attempt < request.retry_count:
                print(f"[Retry {attempt + 1}/{request.retry_count}] {request.case_path} failed, retrying in {request.retry_delay}s...")
                time.sleep(request.retry_delay)
                # 更新变量中的重试计数
                request.variables["_retry_count"] = str(attempt + 1)

            last_response = response

        return last_response or response

    def batch_execute(
        self,
        case_patterns: List[str],
        variables: Optional[Dict[str, str]] = None,
        stop_on_first_failure: bool = False,
    ) -> List[ExecutionResponse]:
        """
        批量执行多个用例 (串行)

        Args:
            case_patterns: 用例路径模式列表 (支持 glob)
            variables: 全局变量
            stop_on_first_failure: 首次失败是否停止

        Returns:
            List[ExecutionResponse]: 所有执行结果
        """
        case_files = []
        for pattern in case_patterns:
            case_files.extend(glob.glob(pattern))

        case_files = list(set(case_files))  # 去重

        if not case_files:
            print(f"警告: 未找到匹配的用例文件: {case_patterns}")
            return []

        results = []
        for case_path in case_files:
            request = ExecutionRequest(
                case_path=case_path,
                variables=variables or {},
                retry_count=0,
            )

            response = self.execute(request)
            results.append(response)

            if stop_on_first_failure and not response.success:
                print(f"首次失败，停止执行: {case_path}")
                break

        return results

    def parallel_execute(
        self,
        case_patterns: List[str],
        variables: Optional[Dict[str, str]] = None,
        workers: int = 4,
        max_retries: int = 1,
    ) -> List[ExecutionResponse]:
        """
        并行执行多个用例

        Args:
            case_patterns: 用例路径模式列表
            variables: 全局变量
            workers: 并行工作线程数
            max_retries: 每个用例最大重试次数

        Returns:
            List[ExecutionResponse]: 所有执行结果
        """
        case_files = []
        for pattern in case_patterns:
            case_files.extend(glob.glob(pattern))

        case_files = list(set(case_files))

        results = []

        def run_case(case_path: str) -> ExecutionResponse:
            request = ExecutionRequest(
                case_path=case_path,
                variables=variables or {},
                retry_count=max_retries,
                retry_delay=5,
            )
            return self.execute_with_retry(request)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(run_case, f): f for f in case_files}

            for future in as_completed(futures):
                case_path = futures[future]
                try:
                    response = future.result()
                    results.append(response)
                except Exception as e:
                    results.append(ExecutionResponse(
                        success=False,
                        case_path=case_path,
                        status="exception",
                        exit_code=1,
                        duration_seconds=0,
                        summary={},
                        error={"type": type(e).__name__, "message": str(e)},
                    ))

        return results

    def generate_report(self, results: List[ExecutionResponse]) -> str:
        """生成汇总报告"""
        total = len(results)
        passed = sum(1 for r in results if r.success)
        failed = total - passed
        total_duration = sum(r.duration_seconds for r in results)
        avg_duration = total_duration / total if total > 0 else 0

        lines = []
        lines.append("=" * 60)
        lines.append(f"  📊 RodSki 批量执行报告")
        lines.append(f"  执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 60)
        lines.append(f"  总用例数:  {total}")
        lines.append(f"  ✅ 通过:    {passed}")
        lines.append(f"  ❌ 失败:    {failed}")
        lines.append(f"  📈 通过率:  {(passed/total*100) if total > 0 else 0:.1f}%")
        lines.append(f"  ⏱️  总耗时:   {total_duration:.1f}s")
        lines.append(f"  ⏱️  平均耗时: {avg_duration:.1f}s")
        lines.append("=" * 60)

        # 列出失败的用例
        failed_results = [r for r in results if not r.success]
        if failed_results:
            lines.append("  ❌ 失败用例:")
            for r in failed_results:
                error_msg = r.error.get("message", "") if r.error else ""
                lines.append(f"    - {r.case_path}: {r.status} — {error_msg}")

        lines.append("=" * 60)
        return "\n".join(lines)


def cmd_run(args):
    """run 子命令"""
    client = OpenCodeRodsKiClient()

    variables = {}
    if args.variables:
        for v in args.variables:
            if "=" in v:
                k, val = v.split("=", 1)
                variables[k] = val

    request = ExecutionRequest(
        case_path=args.case_path,
        variables=variables,
        timeout=args.timeout,
        retry_count=args.retry,
    )

    if args.retry > 0:
        response = client.execute_with_retry(request)
    else:
        response = client.execute(request)

    print(json.dumps(asdict(response), indent=2, ensure_ascii=False))
    return 0 if response.success else 1


def cmd_batch(args):
    """batch 子命令"""
    client = OpenCodeRodsKiClient()

    variables = {}
    if args.variables:
        for v in args.variables:
            if "=" in v:
                k, val = v.split("=", 1)
                variables[k] = val

    patterns = args.case_patterns or [args.case_dir + "/*.xml"] if args.case_dir else []

    results = client.batch_execute(
        case_patterns=patterns,
        variables=variables,
        stop_on_first_failure=args.stop_on_failure,
    )

    print(client.generate_report(results))

    return 0 if all(r.success for r in results) else 1


def cmd_parallel(args):
    """parallel 子命令"""
    client = OpenCodeRodsKiClient()

    variables = {}
    if args.variables:
        for v in args.variables:
            if "=" in v:
                k, val = v.split("=", 1)
                variables[k] = val

    patterns = args.case_patterns or [args.case_dir + "/*.xml"] if args.case_dir else []

    results = client.parallel_execute(
        case_patterns=patterns,
        variables=variables,
        workers=args.workers,
        max_retries=args.retry,
    )

    print(client.generate_report(results))

    return 0 if all(r.success for r in results) else 1


def main():
    parser = argparse.ArgumentParser(
        description="OpenCode/Gemini CLI RodSki 集成示例"
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # run 子命令
    run_parser = subparsers.add_parser("run", help="执行单个用例")
    run_parser.add_argument("case_path", help="用例文件路径")
    run_parser.add_argument("-v", "--variable", action="append", dest="variables", help="变量注入")
    run_parser.add_argument("--timeout", type=int, default=300, help="超时时间(秒)")
    run_parser.add_argument("--retry", type=int, default=0, help="重试次数")

    # batch 子命令
    batch_parser = subparsers.add_parser("batch", help="批量执行用例 (串行)")
    batch_parser.add_argument("case_patterns", nargs="*", help="用例路径模式")
    batch_parser.add_argument("--case-dir", dest="case_dir", help="用例目录")
    batch_parser.add_argument("-v", "--variable", action="append", dest="variables", help="变量注入")
    batch_parser.add_argument("--stop-on-failure", action="store_true", dest="stop_on_failure")

    # parallel 子命令
    parallel_parser = subparsers.add_parser("parallel", help="并行执行用例")
    parallel_parser.add_argument("case_patterns", nargs="*", help="用例路径模式")
    parallel_parser.add_argument("--case-dir", dest="case_dir", help="用例目录")
    parallel_parser.add_argument("-v", "--variable", action="append", dest="variables", help="变量注入")
    parallel_parser.add_argument("--workers", type=int, default=4, help="并行工作数")
    parallel_parser.add_argument("--retry", type=int, default=1, help="每个用例重试次数")

    args = parser.parse_args()

    if args.command == "run":
        return cmd_run(args)
    elif args.command == "batch":
        return cmd_batch(args)
    elif args.command == "parallel":
        return cmd_parallel(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
