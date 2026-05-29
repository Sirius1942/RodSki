#!/usr/bin/env python3
"""验证插件的 execute 开关写回 XML 逻辑（模拟插件行为，不依赖 UI）"""
import os, sys, shutil
from xml.etree import ElementTree as ET

fun_dir = os.path.dirname(os.path.abspath(__file__))
case_file = os.path.normpath(os.path.join(fun_dir, '../../demo_full/case/demo_case.xml'))
backup = case_file + '.bak'

shutil.copy2(case_file, backup)
try:
    tree = ET.parse(case_file)
    root = tree.getroot()
    case = root.find('case')
    original = case.get('execute')
    toggled = '否' if original == '是' else '是'

    # 模拟插件写回
    case.set('execute', toggled)
    tree.write(case_file, encoding='UTF-8', xml_declaration=True)

    # 验证写入成功
    tree2 = ET.parse(case_file)
    actual = tree2.getroot().find('case').get('execute')
    assert actual == toggled, f"写回失败: 期望 {toggled}，实际 {actual}"

    print(f"execute 开关写回验证通过: {original} → {toggled}")
finally:
    shutil.copy2(backup, case_file)
    os.remove(backup)
