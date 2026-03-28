#!/usr/bin/env python3
"""Agent 集成示例 - 演示如何在 Agent 中调用 RodSki"""
import subprocess
import json
import sys


def run_rodski_test(case_path: str, browser: str = "chromium", headless: bool = True) -> dict:
    """执行 RodSki 测试并返回 JSON 结果"""
    cmd = [
        "python3", "cli_main.py", "run", case_path,
        "--output-format", "json",
        "--browser", browser
    ]
    if headless:
        cmd.append("--headless")

    result = subprocess.run(cmd, capture_output=True, text=True)

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {
            "status": "failed",
            "exit_code": result.returncode,
            "error": {"type": "ParseError", "message": result.stderr}
        }


def main():
    if len(sys.argv) < 2:
        print("用法: python agent_integration_example.py <case_path>")
        sys.exit(1)

    case_path = sys.argv[1]
    result = run_rodski_test(case_path)

    print(f"状态: {result['status']}")

    if result['status'] == 'success':
        summary = result['summary']
        print(f"通过: {summary['passed']}/{summary['total_steps']}")
        print(f"耗时: {summary['duration']}")
    else:
        error = result.get('error', {})
        print(f"错误: {error.get('message')}")


if __name__ == "__main__":
    main()
