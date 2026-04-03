"""分析测试结果"""
import os
import sys
import base64
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from llm.client import LLMClient


def analyze_screenshot(llm_client, screenshot_path: Path, desc: str):
    """分析单张截图"""
    with open(screenshot_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    prompt = f"""分析这张截图（{desc}），检测：
1. 是否有错误提示、警告信息
2. 页面是否正常显示
3. 操作是否成功

返回 JSON: {{"has_issue": true/false, "issue": "问题描述"}}"""

    result = llm_client.call_vision(img_b64, prompt)
    return result


if __name__ == "__main__":
    result_dir = Path("/Users/sirius05/Documents/project/RodSki/CassMall_examples/inquiry/result/run_20260403_084451")

    print("初始化 LLM 客户端...")
    llm_client = LLMClient()

    screenshots_dir = result_dir / "screenshots"
    key_screenshots = [
        ("cassmall_inquiry_xiaoli_13_用例_20260403_084532.png", "点击提交后"),
        ("cassmall_inquiry_xiaoli_14_用例_20260403_084535.png", "提交结果页"),
    ]

    print(f"\n分析关键截图...\n")
    for filename, desc in key_screenshots:
        path = screenshots_dir / filename
        if path.exists():
            print(f"检查 {desc}...")
            result = analyze_screenshot(llm_client, path, desc)
            print(f"结果: {result}\n")

