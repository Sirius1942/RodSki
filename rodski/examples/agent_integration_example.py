"""Agent Integration Example - How to call RodSki from an AI Agent"""
import subprocess
import json
import sys


def run_rodski_test(case_path, headless=True):
    """Execute RodSki test and return parsed JSON result

    Args:
        case_path: Path to test case XML file or case directory
        headless: Run browser in headless mode

    Returns:
        dict: Parsed JSON output from RodSki
    """
    cmd = ["rodski", "run", case_path, "--output-format", "json"]
    if headless:
        cmd.append("--headless")

    result = subprocess.run(cmd, capture_output=True, text=True)

    try:
        data = json.loads(result.stdout)
        data["exit_code"] = result.returncode
        return data
    except json.JSONDecodeError:
        return {
            "status": "error",
            "exit_code": result.returncode,
            "error": {"type": "ParseError", "message": result.stderr}
        }


def handle_result(result):
    """Handle test execution result

    Args:
        result: Parsed JSON result from RodSki
    """
    status = result.get("status")

    if status == "success":
        summary = result.get("summary", {})
        print(f"✅ Tests passed: {summary.get('passed')}/{summary.get('total')}")
        return True

    elif status == "failed":
        error = result.get("error", {})
        failed_step = result.get("failed_step", {})
        print(f"❌ Test failed: {error.get('message')}")
        print(f"   Failed at: {failed_step.get('case_id')} (step {failed_step.get('index')})")
        return False

    elif status == "interrupted":
        print("⏹️ Test interrupted by user")
        return False

    else:
        print(f"⚠️ Unknown status: {status}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python agent_integration_example.py <case_path>")
        sys.exit(1)

    case_path = sys.argv[1]
    result = run_rodski_test(case_path)
    success = handle_result(result)

    sys.exit(0 if success else 1)
