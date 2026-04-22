"""DataTableParser 单元测试 - XML 版本

测试 core/data_table_parser.py 中的数据表解析器。
覆盖：parse_all_tables（从 data/ 目录加载所有数据表 XML）、
      get_data（按 datatable name + row id 获取数据行）、
      verify 数据表（_verify 后缀命名约定）、字段值提取。
对应数据文件组织约定：datatable@name = model name。
"""
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


# =====================================================================
# SQLite 集成场景
# =====================================================================
import sqlite3


def _make_sqlite(data_dir: Path, tables_spec: dict) -> None:
    """在 data_dir 下创建 testdata.sqlite，tables_spec = {table_name: {data_id: {field: val}}}"""
    db = data_dir / "testdata.sqlite"
    conn = sqlite3.connect(str(db))
    conn.executescript("""
        CREATE TABLE rs_datatable (table_name TEXT PRIMARY KEY, model_name TEXT NOT NULL,
            table_kind TEXT NOT NULL, row_mode TEXT NOT NULL, remark TEXT DEFAULT '', updated_at TEXT DEFAULT '');
        CREATE TABLE rs_datatable_field (table_name TEXT NOT NULL, field_name TEXT NOT NULL,
            field_order INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (table_name, field_name));
        CREATE TABLE rs_row (table_name TEXT NOT NULL, data_id TEXT NOT NULL,
            remark TEXT DEFAULT '', PRIMARY KEY (table_name, data_id));
        CREATE TABLE rs_field (table_name TEXT NOT NULL, data_id TEXT NOT NULL,
            field_name TEXT NOT NULL, field_value TEXT NOT NULL,
            PRIMARY KEY (table_name, data_id, field_name));
    """)
    for table_name, rows in tables_spec.items():
        conn.execute(
            "INSERT INTO rs_datatable VALUES (?,?,?,?,?,?)",
            (table_name, table_name, 'data', 'standard', '', ''),
        )
        # schema = union of all field names (tests must supply consistent rows)
        all_fields = sorted({f for row in rows.values() for f in row})
        for i, field in enumerate(all_fields):
            conn.execute(
                "INSERT INTO rs_datatable_field VALUES (?,?,?)", (table_name, field, i)
            )
        for data_id, row_data in rows.items():
            conn.execute("INSERT INTO rs_row VALUES (?,?,?)", (table_name, data_id, ''))
            for field_name, field_value in row_data.items():
                conn.execute(
                    "INSERT INTO rs_field VALUES (?,?,?,?)",
                    (table_name, data_id, field_name, field_value),
                )
    conn.commit()
    conn.close()


class TestSQLiteOnly:
    def test_sqlite_tables_loaded(self, tmp_path):
        d = tmp_path / "data"
        d.mkdir()
        _make_sqlite(d, {"Order": {"O001": {"amount": "100", "status": "ok"}}})
        parser = DataTableParser(str(d))
        parser.parse_all_tables()
        assert parser.get_data("Order", "O001")["amount"] == "100"

    def test_merge_table_works(self, tmp_path):
        d = tmp_path / "data"
        d.mkdir()
        parser = DataTableParser(str(d))
        parser.parse_all_tables()
        parser.merge_table("Tmp", {"T001": {"x": "1"}})
        assert parser.get_data("Tmp", "T001")["x"] == "1"


class TestXmlSqliteCoexistence:
    def test_different_tables_ok(self, tmp_path):
        d = tmp_path / "data"
        d.mkdir()
        (d / "data.xml").write_text(
            '<?xml version="1.0"?><datatables>'
            '<datatable name="Login"><row id="L001"><field name="u">admin</field></row></datatable>'
            '</datatables>',
            encoding="utf-8",
        )
        _make_sqlite(d, {"Order": {"O001": {"amount": "50"}}})
        parser = DataTableParser(str(d))
        parser.parse_all_tables()
        assert parser.get_data("Login", "L001")["u"] == "admin"
        assert parser.get_data("Order", "O001")["amount"] == "50"

    def test_same_table_conflict_raises(self, tmp_path):
        from core.exceptions import DataParseError
        d = tmp_path / "data"
        d.mkdir()
        (d / "data.xml").write_text(
            '<?xml version="1.0"?><datatables>'
            '<datatable name="Login"><row id="L001"><field name="u">admin</field></row></datatable>'
            '</datatables>',
            encoding="utf-8",
        )
        _make_sqlite(d, {"Login": {"L001": {"u": "other"}}})
        parser = DataTableParser(str(d))
        with pytest.raises(DataParseError, match="Login"):
            parser.parse_all_tables()

