"""DataTableParser 单元测试 - XML 版本"""
import pytest
from pathlib import Path
from core.data_table_parser import DataTableParser


@pytest.fixture
def data_dir(tmp_path):
    d = tmp_path / "data"
    d.mkdir()

    data_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<datatables>
  <datatable name="Login">
    <row id="L001" remark="管理员">
      <field name="username">admin</field>
      <field name="password">admin123</field>
      <field name="loginBtn">click</field>
    </row>
    <row id="L002" remark="普通用户">
      <field name="username">testuser</field>
      <field name="password">test123</field>
    </row>
  </datatable>
</datatables>'''

    verify_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<datatables>
  <datatable name="Login_verify">
    <row id="V001" remark="验证管理员">
      <field name="welcome_text">欢迎, admin</field>
    </row>
  </datatable>
</datatables>'''

    globalvalue_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<globalvalue>
  <group name="DefaultValue">
    <var name="URL" value="http://localhost"/>
  </group>
</globalvalue>'''

    (d / "data.xml").write_text(data_xml, encoding="utf-8")
    (d / "data_verify.xml").write_text(verify_xml, encoding="utf-8")
    (d / "globalvalue.xml").write_text(globalvalue_xml, encoding="utf-8")
    return str(d)


class TestParseAllTables:
    def test_loads_data_tables(self, data_dir):
        parser = DataTableParser(data_dir)
        tables = parser.parse_all_tables()
        assert "Login" in tables
        assert "Login_verify" in tables

    def test_skips_globalvalue(self, data_dir):
        parser = DataTableParser(data_dir)
        tables = parser.parse_all_tables()
        assert "globalvalue" not in tables

    def test_data_content(self, data_dir):
        parser = DataTableParser(data_dir)
        parser.parse_all_tables()
        assert parser.get_data("Login", "L001")["username"] == "admin"
        assert parser.get_data("Login", "L001")["password"] == "admin123"
        assert parser.get_data("Login", "L002")["username"] == "testuser"

    def test_verify_table(self, data_dir):
        parser = DataTableParser(data_dir)
        parser.parse_all_tables()
        assert parser.get_data("Login_verify", "V001")["welcome_text"] == "欢迎, admin"


class TestGetData:
    def test_get_existing(self, data_dir):
        parser = DataTableParser(data_dir)
        parser.parse_all_tables()
        data = parser.get_data("Login", "L001")
        assert data["username"] == "admin"
        assert data["loginBtn"] == "click"

    def test_get_nonexistent_table(self, data_dir):
        parser = DataTableParser(data_dir)
        parser.parse_all_tables()
        assert parser.get_data("NonExistent", "X001") == {}

    def test_get_nonexistent_id(self, data_dir):
        parser = DataTableParser(data_dir)
        parser.parse_all_tables()
        assert parser.get_data("Login", "L999") == {}


class TestLazyLoad:
    def test_load_on_demand(self, data_dir):
        parser = DataTableParser(data_dir)
        parser.parse_all_tables()
        data = parser.get_data("Login", "L001")
        assert data["username"] == "admin"


class TestEmptyDirectory:
    def test_nonexistent_dir(self, tmp_path):
        parser = DataTableParser(str(tmp_path / "nonexistent"))
        tables = parser.parse_all_tables()
        assert tables == {}

    def test_empty_dir(self, tmp_path):
        d = tmp_path / "empty"
        d.mkdir()
        parser = DataTableParser(str(d))
        tables = parser.parse_all_tables()
        assert tables == {}


class TestIgnoreLegacySplitFiles:
    def test_ignores_legacy_split_data_files(self, tmp_path):
        d = tmp_path / "data"
        d.mkdir()

        data_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<datatables>
  <datatable name="Login">
    <row id="L001">
      <field name="username">admin</field>
    </row>
  </datatable>
</datatables>'''

        legacy_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<datatable name="LegacyOnly">
  <row id="X001">
    <field name="value">should_not_load</field>
  </row>
</datatable>'''

        (d / "data.xml").write_text(data_xml, encoding="utf-8")
        (d / "LegacyOnly.xml").write_text(legacy_xml, encoding="utf-8")

        parser = DataTableParser(str(d))
        parser.parse_all_tables()

        assert "Login" in parser.tables
        assert "LegacyOnly" not in parser.tables


class TestOptionalVerifyFile:
    def test_allows_missing_data_verify_xml(self, tmp_path):
        d = tmp_path / "data"
        d.mkdir()

        data_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<datatables>
  <datatable name="OnlyPrimary">
    <row id="P001">
      <field name="value">ok</field>
    </row>
  </datatable>
</datatables>'''

        (d / "data.xml").write_text(data_xml, encoding="utf-8")

        parser = DataTableParser(str(d))
        tables = parser.parse_all_tables()

        assert "OnlyPrimary" in tables
        assert parser.get_data("OnlyPrimary", "P001")["value"] == "ok"
