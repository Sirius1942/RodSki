#!/usr/bin/env python3
"""执行轨迹标记：把标签追加到 RODSKI_DEBUG_MARKER 指向的文件，并回显为步骤返回值。

验收脚本通过标记文件判断被测用例"真实执行了哪些步骤"，不依赖框架自报的结果；
单独运行被测用例时未设置该环境变量，只回显、不写文件。
"""
import os
import sys

label = sys.argv[1] if len(sys.argv) > 1 else ""
marker = os.environ.get("RODSKI_DEBUG_MARKER")
if marker:
    with open(marker, "a", encoding="utf-8") as fh:
        fh.write(label + "\n")
print(label)
