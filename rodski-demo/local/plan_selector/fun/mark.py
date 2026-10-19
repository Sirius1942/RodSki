#!/usr/bin/env python3
"""执行轨迹标记：python3 mark.py LABEL

把 LABEL 追加到环境变量 RODSKI_PS_MARKER 指向的文件，并回显为步骤返回值。
run_acceptance.py 以该文件判定"实际执行集合"（精确到 scenario 内第几步），不依赖框架自报结果；
单独 `rodski run` 时未设置该变量，只回显、不写文件。
"""
import os
import sys

label = " ".join(sys.argv[1:])
marker = os.environ.get("RODSKI_PS_MARKER")
if marker:
    with open(marker, "a", encoding="utf-8") as fh:
        fh.write(label + "\n")
print(label)
