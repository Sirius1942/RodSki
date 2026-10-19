#!/usr/bin/env python3
"""
iframe 切换脚本
切换到指定的 iframe 或返回主文档

用法:
  python switch_frame.py <frame_name_or_id>  # 切换到指定 iframe
  python switch_frame.py default             # 返回主文档
  python switch_frame.py 0                   # 切换到第一个 iframe (索引)
"""
import sys
from rodski.core.runtime_context import RuntimeContext

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python switch_frame.py <frame_name_or_id|default|index>")
        print("  frame_name_or_id: iframe 的 name 或 id 属性")
        print("  default: 返回主文档")
        print("  index: iframe 索引 (从 0 开始)")
        sys.exit(1)

    try:
        frame_ref = sys.argv[1]
        ctx = RuntimeContext.get_instance()
        driver = ctx.get_driver()

        # 返回主文档
        if frame_ref.lower() == 'default':
            driver.switch_to.default_content()
            print("已返回主文档")
        # 按索引切换
        elif frame_ref.isdigit():
            index = int(frame_ref)
            driver.switch_to.frame(index)
            print(f"已切换到 iframe 索引 {index}")
        # 按 name 或 id 切换
        else:
            driver.switch_to.frame(frame_ref)
            print(f"已切换到 iframe: {frame_ref}")

    except Exception as e:
        print(f"切换 iframe 失败: {e}")
        sys.exit(1)
