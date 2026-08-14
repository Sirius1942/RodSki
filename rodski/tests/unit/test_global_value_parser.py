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
        # 空 group_name 应被整体跳过：结果里只能有 "Valid" 这一个 key，
        # 不能因为 (get('name') or 占位符) 的兜底逻辑写错而多出别的 key。
        assert list(result.keys()) == ["Valid"]

    def test_close_is_noop(self, globalvalue_xml):
        parser = GlobalValueParser(globalvalue_xml)
        parser.close()

    def test_group_with_whitespace_only_name_skipped(self, tmp_path):
        """group name 属性为纯空白（strip 后为空）时也应被跳过，不产生占位 key

        （name 属性在 XSD 中是必填的，但允许取值为空/空白字符串，
        对应 `(group_node.get('name') or '').strip()` 这条 or-兜底逻辑。）
        """
        content = '''<?xml version="1.0" encoding="UTF-8"?>
<globalvalue>
  <group name="   ">
    <var name="x" value="y"/>
  </group>
  <group name="Valid">
    <var name="k" value="v"/>
  </group>
</globalvalue>'''
        f = tmp_path / "gv.xml"
        f.write_text(content, encoding="utf-8")
        result = GlobalValueParser(str(f)).parse()
        assert list(result.keys()) == ["Valid"]

    def test_var_with_whitespace_only_name_skipped(self, tmp_path):
        """var name 属性为纯空白时应被跳过，不产生占位 key"""
        content = '''<?xml version="1.0" encoding="UTF-8"?>
<globalvalue>
  <group name="G1">
    <var name="   " value="orphan_value"/>
    <var name="k" value="v"/>
  </group>
</globalvalue>'''
        f = tmp_path / "gv.xml"
        f.write_text(content, encoding="utf-8")
        result = GlobalValueParser(str(f)).parse()
        assert result["G1"] == {"k": "v"}

    def test_var_with_empty_string_name_skipped_not_placeholder(self, tmp_path):
        """var name 属性为空字符串（而非纯空白）时应被跳过

        与上面纯空白的用例不同：空字符串本身是 falsy，会触发
        `(var_node.get('name') or 占位符).strip()` 里的 or 分支。
        用这个用例专门区分 or 右侧是 '' 还是被误改成非空占位符
        （占位符本身非空，strip 后仍非空，if var_name 会误判为真）。
        """
        content = '''<?xml version="1.0" encoding="UTF-8"?>
<globalvalue>
  <group name="G1">
    <var name="" value="orphan_value"/>
    <var name="k" value="v"/>
  </group>
</globalvalue>'''
        f = tmp_path / "gv.xml"
        f.write_text(content, encoding="utf-8")
        result = GlobalValueParser(str(f)).parse()
        assert result["G1"] == {"k": "v"}

    def test_var_with_empty_value_attribute_is_empty_string(self, tmp_path):
        """var value 属性为空字符串时，变量值应保持为空字符串（而非占位字符串）"""
        content = '''<?xml version="1.0" encoding="UTF-8"?>
<globalvalue>
  <group name="G1">
    <var name="empty_val" value=""/>
  </group>
</globalvalue>'''
        f = tmp_path / "gv.xml"
        f.write_text(content, encoding="utf-8")
        result = GlobalValueParser(str(f)).parse()
        assert result["G1"]["empty_val"] == ""
