"""CaseMetadata / CaseMetadataExtractor 单元测试

测试 core/case_metadata.py 中的用例元数据提取模块。
覆盖：CaseMetadata.from_xml（完整/部分/无 metadata）、to_dict、
      CaseMetadataExtractor.extract / extract_batch。
"""
import xml.etree.ElementTree as ET
import pytest
from pathlib import Path
from core.case_metadata import CaseMetadata, CaseMetadataExtractor


# =====================================================================
# CaseMetadata.from_xml
# =====================================================================
class TestCaseMetadataFromXml:
    """from_xml —— 从 XML 元素提取元数据"""

    def test_full_metadata(self):
        """包含所有字段的完整 metadata 提取"""
        xml_str = """
        <case id="c001" priority="P1" component="登录" component_type="界面">
          <metadata author="test_user" create_time="2026-01-01"
                   modify_time="2026-04-01" estimated_duration="5s"
                   requirement_id="REQ-001" test_type="回归">
            <tag>smoke</tag>
            <tag>login</tag>
          </metadata>
          <test_case>
            <test_step action="type" model="Login" data="L001"/>
          </test_case>
        </case>
        """
        root = ET.fromstring(xml_str)
        meta = CaseMetadata.from_xml(root)

        assert meta.priority == "P1"
        assert meta.component == "登录"
        assert meta.component_type == "界面"
        assert meta.author == "test_user"
        assert meta.create_time == "2026-01-01"
        assert meta.modify_time == "2026-04-01"
        assert meta.estimated_duration == "5s"
        assert meta.requirement_id == "REQ-001"
        assert meta.test_type == "回归"
        assert meta.tags == ["smoke", "login"]

    def test_no_metadata_node(self):
        """没有 metadata 节点时，所有字段应为 None/空"""
        xml_str = """
        <case id="c001" component_type="接口">
          <test_case>
            <test_step action="send" model="API" data="D001"/>
          </test_case>
        </case>
        """
        root = ET.fromstring(xml_str)
        meta = CaseMetadata.from_xml(root)

        assert meta.priority is None
        assert meta.component is None
        assert meta.component_type == "接口"   # 来自 case 属性，非 metadata
        assert meta.tags == []
        assert meta.author is None

    def test_partial_metadata(self):
        """部分字段的 metadata"""
        xml_str = """
        <case id="c001" priority="P2">
          <metadata author="张三"/>
          <test_case>
            <test_step action="wait" model="" data="2"/>
          </test_case>
        </case>
        """
        root = ET.fromstring(xml_str)
        meta = CaseMetadata.from_xml(root)

        assert meta.priority == "P2"
        assert meta.author == "张三"
        assert meta.create_time is None
        assert meta.tags == []

    def test_empty_tags(self):
        """metadata 节点下无 tag 子元素时 tags 应为空列表"""
        xml_str = """
        <case id="c001">
          <metadata author="user"/>
          <test_case><test_step action="wait" data="1"/></test_case>
        </case>
        """
        root = ET.fromstring(xml_str)
        meta = CaseMetadata.from_xml(root)
        assert meta.tags == []


# =====================================================================
# CaseMetadata.to_dict
# =====================================================================
class TestCaseMetadataToDict:
    """to_dict —— 元数据转字典"""

    def test_to_dict_completeness(self):
        """to_dict 应包含所有字段"""
        meta = CaseMetadata(
            priority="P1", component="登录", component_type="界面",
            tags=["smoke"], author="user", create_time="2026-01-01"
        )
        d = meta.to_dict()
        assert d["priority"] == "P1"
        assert d["component"] == "登录"
        assert d["tags"] == ["smoke"]
        assert d["author"] == "user"
        # 所有 10 个键都应存在
        expected_keys = {"priority", "component", "component_type", "tags", "author",
                        "create_time", "modify_time", "estimated_duration",
                        "requirement_id", "test_type"}
        assert set(d.keys()) == expected_keys

    def test_to_dict_default_values(self):
        """默认值的 to_dict"""
        meta = CaseMetadata()
        d = meta.to_dict()
        assert d["priority"] is None
        assert d["tags"] == []


# =====================================================================
# CaseMetadataExtractor
# =====================================================================
class TestCaseMetadataExtractor:
    """CaseMetadataExtractor —— 从文件/目录提取元数据"""

    def test_extract_single_file(self, tmp_path):
        """从单个 case 文件提取元数据"""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case id="c001" priority="P1" component_type="界面">
    <metadata author="tester"/>
    <test_case><test_step action="wait" data="1"/></test_case>
  </case>
</cases>"""
        f = tmp_path / "test.xml"
        f.write_text(xml_content, encoding="utf-8")

        extractor = CaseMetadataExtractor()
        meta = extractor.extract(str(f))
        assert meta.priority == "P1"
        assert meta.author == "tester"

    def test_extract_no_case_node(self, tmp_path):
        """XML 中没有 case 节点时应返回空 CaseMetadata"""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<cases></cases>"""
        f = tmp_path / "empty.xml"
        f.write_text(xml_content, encoding="utf-8")

        extractor = CaseMetadataExtractor()
        meta = extractor.extract(str(f))
        assert meta.priority is None

    def test_extract_batch(self, tmp_path):
        """批量提取目录下所有 case 文件的元数据"""
        xml1 = """<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case id="c001" priority="P1"><test_case><test_step action="wait" data="1"/></test_case></case>
  <case id="c002" priority="P2"><test_case><test_step action="wait" data="1"/></test_case></case>
</cases>"""
        (tmp_path / "case1.xml").write_text(xml1, encoding="utf-8")

        extractor = CaseMetadataExtractor()
        result = extractor.extract_batch(str(tmp_path))
        assert "c001" in result
        assert "c002" in result
        assert result["c001"].priority == "P1"
        assert result["c002"].priority == "P2"

    def test_extract_batch_empty_dir(self, tmp_path):
        """空目录应返回空字典"""
        extractor = CaseMetadataExtractor()
        result = extractor.extract_batch(str(tmp_path))
        assert result == {}

    def test_extract_batch_nonexistent_dir(self):
        """不存在的目录应返回空字典"""
        extractor = CaseMetadataExtractor()
        result = extractor.extract_batch("/nonexistent/path")
        assert result == {}
