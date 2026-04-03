"""Case metadata extraction and management"""
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional


@dataclass
class CaseMetadata:
    """Case metadata container"""
    priority: Optional[str] = None
    component: Optional[str] = None
    component_type: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    author: Optional[str] = None
    create_time: Optional[str] = None
    modify_time: Optional[str] = None
    estimated_duration: Optional[str] = None
    requirement_id: Optional[str] = None
    test_type: Optional[str] = None

    @classmethod
    def from_xml(cls, root: ET.Element) -> 'CaseMetadata':
        """Extract metadata from case XML element"""
        priority = root.get('priority')
        component = root.get('component')
        component_type = root.get('component_type')

        tags = []
        metadata_node = root.find('metadata')
        author = None
        create_time = None
        modify_time = None
        estimated_duration = None
        requirement_id = None
        test_type = None

        if metadata_node is not None:
            tags = [tag.text for tag in metadata_node.findall('tag') if tag.text]
            author = metadata_node.get('author')
            create_time = metadata_node.get('create_time')
            modify_time = metadata_node.get('modify_time')
            estimated_duration = metadata_node.get('estimated_duration')
            requirement_id = metadata_node.get('requirement_id')
            test_type = metadata_node.get('test_type')

        return cls(
            priority=priority,
            component=component,
            component_type=component_type,
            tags=tags,
            author=author,
            create_time=create_time,
            modify_time=modify_time,
            estimated_duration=estimated_duration,
            requirement_id=requirement_id,
            test_type=test_type
        )

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'priority': self.priority,
            'component': self.component,
            'component_type': self.component_type,
            'tags': self.tags,
            'author': self.author,
            'create_time': self.create_time,
            'modify_time': self.modify_time,
            'estimated_duration': self.estimated_duration,
            'requirement_id': self.requirement_id,
            'test_type': self.test_type
        }


class CaseMetadataExtractor:
    """Extract metadata from case XML files"""

    def extract(self, case_path: str) -> CaseMetadata:
        """Extract metadata from a single case file"""
        tree = ET.parse(case_path)
        root = tree.getroot()
        case_node = root.find('case')
        if case_node is None:
            return CaseMetadata()
        return CaseMetadata.from_xml(case_node)

    def extract_batch(self, case_dir: str) -> Dict[str, CaseMetadata]:
        """Extract metadata from all case files in directory"""
        result = {}
        case_path = Path(case_dir)

        if not case_path.exists():
            return result

        for xml_file in case_path.glob('*.xml'):
            tree = ET.parse(xml_file)
            root = tree.getroot()
            for case_node in root.findall('case'):
                case_id = case_node.get('id', '')
                if case_id:
                    result[case_id] = CaseMetadata.from_xml(case_node)

        return result
