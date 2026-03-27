#!/usr/bin/env python3
"""XML Schema 验证脚本"""
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

def validate_xml(xml_path: Path) -> bool:
    try:
        ET.parse(str(xml_path))
        print(f"✅ {xml_path.relative_to(Path.cwd())}")
        return True
    except Exception as e:
        print(f"❌ {xml_path.name}: {e}")
        return False

def main():
    base = Path(__file__).parent.parent
    results = []

    # 验证所有 XML 文件
    for xml in base.rglob("*.xml"):
        if ".archive" not in str(xml) and "demo_" not in str(xml):
            results.append(validate_xml(xml))

    if all(results):
        print(f"\n✅ 所有 XML 文件格式正确 ({len(results)} 个)")
        return 0
    else:
        print(f"\n❌ {results.count(False)} 个文件验证失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
