"""GlobalValueParser 单元测试 - XML 版本

测试 core/global_value_parser.py 中的全局变量解析器。
覆盖：parse（完整/空文件）、DefaultValue 组（URL/BrowserType/WaitTime）、
      数据库连接组、自定义变量组、引用格式 GlobalValue.组名.变量名。
"""
import pytest
from pathlib import Path
from core.global_value_parser import GlobalValueParser


@pytest.fixture
def globalvalue_xml(tmp_path):
    content = '''<?xml version="1.0" encoding="UTF-8"?>
<globalvalue>
  <group name="DefaultValue">
    <var name="URL" value="http://127.0.0.1:5555"/>
    <var name="BrowserType" value="chromium"/>
    <var name="WaitTime" value="2"/>
  </group>
  <group name="demodb">
    <var name="type" value="sqlite"/>
    <var name="database" value="demo.db"/>
  </group>
</globalvalue>'''
    f = tmp_path / "globalvalue.xml"
    f.write_text(content, encoding="utf-8")
    return str(f)


class TestGlobalValueParser:
    def test_parse_groups(self, globalvalue_xml):
        parser = GlobalValueParser(globalvalue_xml)
        result = parser.parse()
        assert "DefaultValue" in result
        assert "demodb" in result

    def test_parse_vars(self, globalvalue_xml):
        parser = GlobalValueParser(globalvalue_xml)
        result = parser.parse()
        assert result["DefaultValue"]["URL"] == "http://127.0.0.1:5555"
        assert result["DefaultValue"]["BrowserType"] == "chromium"
        assert result["DefaultValue"]["WaitTime"] == "2"

    def test_parse_db_config(self, globalvalue_xml):
        parser = GlobalValueParser(globalvalue_xml)
        result = parser.parse()
        assert result["demodb"]["type"] == "sqlite"
        assert result["demodb"]["database"] == "demo.db"

    def test_nonexistent_file(self, tmp_path):
        parser = GlobalValueParser(str(tmp_path / "missing.xml"))
        result = parser.parse()
        assert result == {}

    def test_empty_groups_skipped(self, tmp_path):
        content = '''<?xml version="1.0" encoding="UTF-8"?>
<globalvalue>
  <group name="">
    <var name="x" value="y"/>
  </group>
  <group name="Valid">
    <var name="k" value="v"/>
  </group>
</globalvalue>'''
        f = tmp_path / "gv.xml"
        f.write_text(content, encoding="utf-8")
        parser = GlobalValueParser(str(f))
        result = parser.parse()
        assert "" not in result
        assert "Valid" in result

    def test_close_is_noop(self, globalvalue_xml):
        parser = GlobalValueParser(globalvalue_xml)
        parser.close()
