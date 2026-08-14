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

    def test_metadata_inserted_before_test_case(self, case_xml):
        """新建 metadata 节点应插入在 test_case 之前，而不是之后"""
        MetadataWriter.update_metadata(case_xml, "c001", {"author": "test"})

        tree = ET.parse(case_xml)
        case_node = tree.getroot().find("case[@id='c001']")
        tags = [child.tag for child in case_node]
        assert tags.index("metadata") < tags.index("test_case")

    def test_metadata_inserted_before_pre_process(self, tmp_path):
        """case 中存在 pre_process 节点时，metadata 应插入在其之前"""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="c001" title="带前置条件的用例">
    <pre_process>
      <test_step action="navigate" model="" data="http://test.com"/>
    </pre_process>
    <test_case>
      <test_step action="type" model="Login" data="L001"/>
    </test_case>
  </case>
</cases>"""
        f = tmp_path / "test_case.xml"
        f.write_text(xml_content, encoding="utf-8")

        MetadataWriter.update_metadata(f, "c001", {"author": "test"})

        tree = ET.parse(f)
        case_node = tree.getroot().find("case[@id='c001']")
        tags = [child.tag for child in case_node]
        assert tags.index("metadata") < tags.index("pre_process")
        assert tags.index("metadata") < tags.index("test_case")

    def test_metadata_not_inserted_after_post_process(self, tmp_path):
        """case 中存在 post_process 节点时，metadata 仍应插入在其之前，不能落到最后"""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="c001" title="带后置清理的用例">
    <test_case>
      <test_step action="type" model="Login" data="L001"/>
    </test_case>
    <post_process>
      <test_step action="close" model="" data=""/>
    </post_process>
  </case>
</cases>"""
        f = tmp_path / "test_case.xml"
        f.write_text(xml_content, encoding="utf-8")

        MetadataWriter.update_metadata(f, "c001", {"author": "test"})

        tree = ET.parse(f)
        case_node = tree.getroot().find("case[@id='c001']")
        tags = [child.tag for child in case_node]
        assert tags.index("metadata") < tags.index("test_case")
        assert tags.index("metadata") < tags.index("post_process")

    def test_chinese_attribute_value_preserved(self, case_xml):
        """中文属性值应在序列化/重新解析后保持不变（覆盖 ET.tostring 的 encoding 参数）"""
        MetadataWriter.update_metadata(case_xml, "c001", {"author": "张三"})

        tree = ET.parse(case_xml)
        meta = tree.getroot().find("case[@id='c001']/metadata")
        assert meta.get("author") == "张三"

    def test_output_has_no_blank_lines(self, case_xml):
        """输出文件不应包含空白行（split('\\n') 后过滤空行）"""
        MetadataWriter.update_metadata(case_xml, "c001", {"author": "test"})
        content = case_xml.read_text(encoding="utf-8")
        lines = content.split("\n")
        assert all(line.strip() for line in lines)

    def test_output_uses_two_space_indent(self, case_xml):
        """输出 XML 应使用 2 个空格缩进"""
        MetadataWriter.update_metadata(case_xml, "c001", {"author": "test"})
        content = case_xml.read_text(encoding="utf-8")
        lines = content.split("\n")
        indented = [l for l in lines if l.startswith("  ") and not l.startswith("    ")]
        assert indented, f"未找到 2 空格缩进行: {lines}"

    def test_output_file_encoding_is_utf8(self, case_xml):
        """写回文件应使用 utf-8 编码，中文内容不应变成 latin-1 等其他编码报错"""
        MetadataWriter.update_metadata(case_xml, "c001", {"author": "中文用户名"})
        # 显式用 utf-8 重新读取应能拿到原文，不抛 UnicodeDecodeError
        content = case_xml.read_text(encoding="utf-8")
        assert "中文用户名" in content

    def test_metadata_inserted_at_start_when_no_recognized_children(self, tmp_path):
        """case 下没有 pre_process/test_case/post_process 任何一个子节点时，
        insert_pos 应保持初始值 0（插到最前面），而不是 None 或其他值导致报错/位置错误
        """
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="c001" title="无标准子节点的用例">
    <custom_step action="noop"/>
  </case>
</cases>"""
        f = tmp_path / "test_case.xml"
        f.write_text(xml_content, encoding="utf-8")

        MetadataWriter.update_metadata(f, "c001", {"author": "test"})

        tree = ET.parse(f)
        case_node = tree.getroot().find("case[@id='c001']")
        tags = [child.tag for child in case_node]
        assert tags[0] == "metadata"  # 插到最前面

    def test_metadata_inserted_before_post_process_only_case(self, tmp_path):
        """case 中只有 post_process（没有 pre_process/test_case）时，
        metadata 仍应插入在 post_process 之前

        （若 'post_process' 被拼错成其他字符串，或 in 被误写成 not in，
        循环找不到/错误匹配 post_process，insert_pos 会停在初始值 0——
        这里恰好也是 0，所以还不足以区分；关键要看 tags 是否精确为
        [metadata, post_process] 而不是因为找不到匹配而在其他位置。）
        """
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="c001" title="只有后置清理的用例">
    <post_process>
      <test_step action="close" model="" data=""/>
    </post_process>
  </case>
</cases>"""
        f = tmp_path / "test_case.xml"
        f.write_text(xml_content, encoding="utf-8")

        MetadataWriter.update_metadata(f, "c001", {"author": "test"})

        tree = ET.parse(f)
        case_node = tree.getroot().find("case[@id='c001']")
        tags = [child.tag for child in case_node]
        assert tags == ["metadata", "post_process"]

    def test_metadata_inserted_immediately_before_post_process_with_preceding_unknown_tag(self, tmp_path):
        """case 中有一个不被识别的自定义节点在 post_process 之前时，
        insert_pos 必须精确停在 post_process 的下标（1），而不是 0 或其他值。

        这个用例专门杀死 `in (...)` 被误写成 `not in (...)` 的变异：
        - 正确逻辑：第 0 个 custom_tag 不匹配，继续；第 1 个 post_process 匹配，
          insert_pos=1，break。结果 tags == [custom_tag, metadata, post_process]。
        - `not in` 变异：第 0 个 custom_tag 匹配 "not in"（因为它不在元组里），
          insert_pos=0，break。结果会变成 [metadata, custom_tag, post_process]。
        """
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="c001" title="用例">
    <custom_tag/>
    <post_process>
      <test_step action="close" model="" data=""/>
    </post_process>
  </case>
</cases>"""
        f = tmp_path / "test_case.xml"
        f.write_text(xml_content, encoding="utf-8")

        MetadataWriter.update_metadata(f, "c001", {"author": "test"})

        tree = ET.parse(f)
        case_node = tree.getroot().find("case[@id='c001']")
        tags = [child.tag for child in case_node]
        assert tags == ["custom_tag", "metadata", "post_process"]

    def test_insert_pos_matches_first_recognized_child_not_last(self, tmp_path):
        """存在 test_case 和 post_process 两个节点时，insert_pos 应停在第一个
        匹配到的 test_case 上（break 生效），而不是继续遍历到 post_process 才停
        """
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="c001" title="用例">
    <test_case>
      <test_step action="type" model="Login" data="L001"/>
    </test_case>
    <post_process>
      <test_step action="close" model="" data=""/>
    </post_process>
  </case>
</cases>"""
        f = tmp_path / "test_case.xml"
        f.write_text(xml_content, encoding="utf-8")

        MetadataWriter.update_metadata(f, "c001", {"author": "test"})

        tree = ET.parse(f)
        case_node = tree.getroot().find("case[@id='c001']")
        tags = [child.tag for child in case_node]
        # metadata 必须紧邻在第一个匹配节点（test_case）之前
        assert tags == ["metadata", "test_case", "post_process"]

    def test_write_text_called_with_encoding_utf8(self, case_xml):
        """写回文件时应显式调用 write_text(..., encoding='utf-8')

        （在本机 locale 默认编码恰好也是 UTF-8 的环境下，省略/改写 encoding
        参数从行为上无法区分，因此直接 mock 断言调用参数。）
        """
        from unittest.mock import patch

        with patch.object(Path, "write_text", autospec=True) as mock_write:
            MetadataWriter.update_metadata(case_xml, "c001", {"author": "test"})
            mock_write.assert_called_once()
            _, kwargs = mock_write.call_args
            assert kwargs.get("encoding") == "utf-8"

    def test_tostring_called_with_encoding_unicode(self, case_xml):
        """MetadataWriter 应显式调用 ET.tostring(root, encoding='unicode')

        （minidom.parseString 对 str 和 bytes 输入的解析结果在本场景下恰好一致，
        无法靠输出内容区分，因此直接 mock 断言调用参数本身。）
        """
        from unittest.mock import patch
        import xml.etree.ElementTree as ET_module

        with patch("core.metadata_writer.ET.tostring", wraps=ET_module.tostring) as mock_tostring:
            MetadataWriter.update_metadata(case_xml, "c001", {"author": "test"})
            mock_tostring.assert_called_once()
            _, kwargs = mock_tostring.call_args
            assert kwargs.get("encoding") == "unicode"


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
