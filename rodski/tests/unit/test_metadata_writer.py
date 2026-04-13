"""MetadataWriter 单元测试

测试 core/metadata_writer.py 中的元数据写入模块。
覆盖：update_metadata（新建 metadata 节点/更新已有节点/指定 case_id）、
      update_success_rate（成功率写入 + last_run 时间戳）。
"""
import xml.etree.ElementTree as ET
import pytest
from pathlib import Path
from core.metadata_writer import MetadataWriter


@pytest.fixture
def case_xml(tmp_path):
    """创建包含两个用例的临时 case XML 文件"""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="c001" title="登录测试">
    <test_case>
      <test_step action="type" model="Login" data="L001"/>
    </test_case>
  </case>
  <case execute="是" id="c002" title="查询测试">
    <test_case>
      <test_step action="navigate" model="" data="http://test.com"/>
    </test_case>
  </case>
</cases>"""
    f = tmp_path / "test_case.xml"
    f.write_text(xml_content, encoding="utf-8")
    return f


class TestUpdateMetadata:
    """update_metadata —— 更新用例元数据"""

    def test_add_new_metadata_node(self, case_xml):
        """用例没有 metadata 节点时应自动创建"""
        MetadataWriter.update_metadata(case_xml, "c001", {"author": "test_user"})

        tree = ET.parse(case_xml)
        case_node = tree.getroot().find("case[@id='c001']")
        meta = case_node.find("metadata")
        # 检查 metadata 节点被创建
        assert meta is not None
        assert meta.get("author") == "test_user"

    def test_update_existing_metadata(self, case_xml):
        """已有 metadata 节点时应更新属性"""
        # 先创建 metadata
        MetadataWriter.update_metadata(case_xml, "c001", {"author": "user_a"})
        # 再更新
        MetadataWriter.update_metadata(case_xml, "c001", {"author": "user_b", "version": "1.0"})

        tree = ET.parse(case_xml)
        meta = tree.getroot().find("case[@id='c001']/metadata")
        assert meta.get("author") == "user_b"
        assert meta.get("version") == "1.0"

    def test_target_specific_case_id(self, case_xml):
        """应仅更新目标 case_id 的元数据，不影响其他用例"""
        MetadataWriter.update_metadata(case_xml, "c002", {"tag": "regression"})

        tree = ET.parse(case_xml)
        # c002 应有 metadata
        meta_c002 = tree.getroot().find("case[@id='c002']/metadata")
        assert meta_c002 is not None
        assert meta_c002.get("tag") == "regression"
        # c001 不应有 metadata
        meta_c001 = tree.getroot().find("case[@id='c001']/metadata")
        assert meta_c001 is None

    def test_skip_empty_value(self, case_xml):
        """空值字段不应写入 metadata"""
        MetadataWriter.update_metadata(case_xml, "c001", {"author": "user", "tag": ""})

        tree = ET.parse(case_xml)
        meta = tree.getroot().find("case[@id='c001']/metadata")
        assert meta.get("author") == "user"
        # 空值不应出现
        assert meta.get("tag") is None

    def test_nonexistent_case_id_no_error(self, case_xml):
        """指定不存在的 case_id 时不应报错"""
        # 不应抛异常
        MetadataWriter.update_metadata(case_xml, "c999", {"author": "ghost"})

    def test_xml_well_formed_after_update(self, case_xml):
        """更新后 XML 文件应保持格式良好"""
        MetadataWriter.update_metadata(case_xml, "c001", {"author": "test"})
        # 再次解析不应报错
        tree = ET.parse(case_xml)
        assert tree.getroot().tag == "cases"


class TestUpdateSuccessRate:
    """update_success_rate —— 更新用例成功率"""

    def test_success_rate_written(self, case_xml):
        """成功率应写入 metadata 的 success_rate 属性"""
        MetadataWriter.update_success_rate(case_xml, "c001", 85.5)

        tree = ET.parse(case_xml)
        meta = tree.getroot().find("case[@id='c001']/metadata")
        assert meta is not None
        assert meta.get("success_rate") == "85.5%"

    def test_last_run_timestamp(self, case_xml):
        """应同时写入 last_run 时间戳"""
        MetadataWriter.update_success_rate(case_xml, "c001", 100.0)

        tree = ET.parse(case_xml)
        meta = tree.getroot().find("case[@id='c001']/metadata")
        last_run = meta.get("last_run")
        assert last_run is not None
        # 时间戳格式：YYYY-MM-DD HH:MM:SS
        assert len(last_run) == 19
