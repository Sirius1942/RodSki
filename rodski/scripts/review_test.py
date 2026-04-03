"""使用现有 LLM 配置审查测试结果"""
import sys
import base64
from pathlib import Path

# 添加 rodski 到路径
rodski_path = Path(__file__).parent.parent
sys.path.insert(0, str(rodski_path))

from llm.client import LLMClient


def review_result(result_dir: str):
    """审查测试结果"""
    result_path = Path(result_dir)
    screenshots_dir = result_path / "screenshots"

    # 初始化客户端
    print("初始化 LLM 客户端...")
    client = LLMClient()

    # 关键截图
    key_shots = [
        "cassmall_inquiry_xiaoli_13_用例_20260403_084532.png",
        "cassmall_inquiry_xiaoli_14_用例_20260403_084535.png",
    ]

    print("\n分析关键截图...\n")
    for filename in key_shots:
        path = screenshots_dir / filename
        if not path.exists():
            continue

        print(f"检查: {filename}")
        with open(path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()

        prompt = """分析截图，检测问题：
1. 是否有错误提示
2. 页面是否正常
3. 操作是否成功

简短说明。"""

        result = client.call_vision(img_b64, prompt)
        print(f"结果: {result}\n")


if __name__ == "__main__":
    result_dir = "/Users/sirius05/Documents/project/RodSki/CassMall_examples/inquiry/result/run_20260403_084451"
    review_result(result_dir)


