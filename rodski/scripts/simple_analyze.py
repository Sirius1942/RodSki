"""简化版测试结果分析 - 使用 OpenAI API"""
import os
import base64
from pathlib import Path

# 需要设置环境变量: export OPENAI_API_KEY=your-key


def analyze_with_openai(screenshot_path: Path, desc: str):
    """使用 OpenAI API 分析截图"""
    try:
        from openai import OpenAI
        client = OpenAI()

        with open(screenshot_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": f"""分析截图（{desc}）：
1. 是否有错误提示、警告
2. 页面是否正常
3. 操作是否成功

简短回答问题所在。"""},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
                ]
            }],
            max_tokens=300
        )

        return response.choices[0].message.content
    except Exception as e:
        return f"分析失败: {e}"


if __name__ == "__main__":
    result_dir = Path("/Users/sirius05/Documents/project/RodSki/CassMall_examples/inquiry/result/run_20260403_084451")
    screenshots_dir = result_dir / "screenshots"

    key_screenshots = [
        ("cassmall_inquiry_xiaoli_13_用例_20260403_084532.png", "点击提交按钮后"),
        ("cassmall_inquiry_xiaoli_14_用例_20260403_084535.png", "提交后等待2秒"),
    ]

    print("分析测试结果...\n")
    for filename, desc in key_screenshots:
        path = screenshots_dir / filename
        if path.exists():
            print(f"检查: {desc}")
            result = analyze_with_openai(path, desc)
            print(f"结果: {result}\n")
            print("-" * 50)

