#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 OmniParser 服务"""
import requests
import base64
import json
from pathlib import Path


def test_omniparser(image_path, omni_url="http://14.103.175.167:7862/parse/"):
    """测试 OmniParser 图像识别"""
    # 读取图片并转 base64
    with open(image_path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')

    # 请求参数
    payload = {
        "base64_image": image_data,
        "box_threshold": 0.18,
        "iou_threshold": 0.7
    }

    # 调用服务
    response = requests.post(omni_url, json=payload, timeout=10)
    result = response.json()

    # 输出结果
    print(f"识别耗时: {result.get('latency', 0):.2f}秒")
    print(f"识别到 {len(result.get('parsed_content_list', []))} 个元素\n")

    for idx, element in enumerate(result.get('parsed_content_list', []), 1):
        print(f"元素 {idx}:")
        print(f"  类型: {element['type']}")
        print(f"  内容: {element['content']}")
        print(f"  坐标: {element['bbox']}")
        print(f"  可交互: {element['interactivity']}")
        print()

    return result


if __name__ == "__main__":
    # 测试图片路径
    test_image = "test_screenshot.png"

    if Path(test_image).exists():
        test_omniparser(test_image)
    else:
        print(f"请提供测试图片: {test_image}")
