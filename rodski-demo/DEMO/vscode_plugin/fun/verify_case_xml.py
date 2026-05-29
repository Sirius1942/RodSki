#!/usr/bin/env python3
import os, sys
from xml.etree import ElementTree as ET

fun_dir = os.path.dirname(os.path.abspath(__file__))
case_file = os.path.normpath(os.path.join(fun_dir, '../../demo_full/case/demo_case.xml'))

if not os.path.exists(case_file):
    print(f"case 文件不存在: {case_file}", file=sys.stderr)
    sys.exit(1)

tree = ET.parse(case_file)
root = tree.getroot()
cases = root.findall('case')

if not cases:
    print("未找到任何 <case> 元素", file=sys.stderr)
    sys.exit(1)

for c in cases:
    assert c.get('id'), f"case 缺少 id 属性: {ET.tostring(c, encoding='unicode')[:80]}"
    assert c.get('execute') in ('是', '否'), f"case execute 属性非法: {c.get('execute')}"

print(f"XML 结构合法，共 {len(cases)} 个用例")
