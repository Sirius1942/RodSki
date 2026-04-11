#!/usr/bin/env python3
"""
窗口切换脚本
切换到指定索引的浏览器窗口

用法: python switch_window.py <窗口索引>
索引从 0 开始，0 表示第一个窗口
"""
import sys
from rodski.core.runtime_context import RuntimeContext

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python switch_window.py <窗口索引>")
        print("索引从 0 开始")
        sys.exit(1)

    try:
        index = int(sys.argv[1])
        ctx = RuntimeContext.get_instance()
        driver = ctx.get_driver()

        # 获取所有窗口句柄
        handles = driver.window_handles
        print(f"当前共有 {len(handles)} 个窗口")

        if index < 0 or index >= len(handles):
            print(f"错误: 窗口索引 {index} 超出范围 (0-{len(handles)-1})")
            sys.exit(1)

        # 切换到指定窗口
        driver.switch_to.window(handles[index])
        print(f"已切换到窗口 {index}")

    except ValueError:
        print("错误: 窗口索引必须是整数")
        sys.exit(1)
    except Exception as e:
        print(f"切换窗口失败: {e}")
        sys.exit(1)
