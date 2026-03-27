"""迭代 01 - 视觉定位功能测试运行脚本

使用 ski_run.py 运行测试用例
"""
import sys
import subprocess
from pathlib import Path

def main():
    test_dir = Path(__file__).parent
    rodski_dir = test_dir.parent.parent.parent / "rodski"
    ski_run = rodski_dir / "ski_run.py"

    print("=== 迭代 01 视觉定位功能测试 ===\n")

    # 运行测试
    result = subprocess.run(
        [sys.executable, str(ski_run), str(test_dir), "--headless"],
        cwd=str(rodski_dir)
    )

    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
