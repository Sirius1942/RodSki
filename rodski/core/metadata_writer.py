"""元数据写入模块 - 更新 case XML 中的 metadata 节点"""
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


class MetadataWriter:
    """更新 case XML 文件中的元数据"""

    @staticmethod
    def update_metadata(case_file: Path, case_id: str, metadata: Dict[str, str]) -> None:
        """更新指定用例的元数据

        Args:
            case_file: case XML 文件路径
            case_id: 用例 ID
            metadata: 元数据字典，支持 created_by, created_at, updated_by, updated_at, success_rate, last_run
        """
        tree = ET.parse(case_file)
        root = tree.getroot()

        for case_node in root.findall('case'):
            if case_node.get('id') == case_id:
                metadata_node = case_node.find('metadata')
                if metadata_node is None:
                    # 在 pre_process 之前插入 metadata
                    metadata_node = ET.Element('metadata')
                    insert_pos = 0
                    for i, child in enumerate(case_node):
                        if child.tag in ('pre_process', 'test_case', 'post_process'):
                            insert_pos = i
                            break
                    case_node.insert(insert_pos, metadata_node)

                for key, value in metadata.items():
                    if value:
                        metadata_node.set(key, str(value))

                break

        xml_str = minidom.parseString(ET.tostring(root, encoding='unicode')).toprettyxml(indent="  ")
        lines = [line for line in xml_str.split('\n') if line.strip()]
        case_file.write_text('\n'.join(lines), encoding='utf-8')

    @staticmethod
    def update_success_rate(case_file: Path, case_id: str, success_rate: float) -> None:
        """更新用例成功率

        Args:
            case_file: case XML 文件路径
            case_id: 用例 ID
            success_rate: 成功率（0-100）
        """
        MetadataWriter.update_metadata(
            case_file,
            case_id,
            {
                'success_rate': f"{success_rate:.1f}%",
                'last_run': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        )
