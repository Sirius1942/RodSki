"""Case XML 解析器 - 三阶段多步骤用例结构

从 case/*.xml 解析测试用例。每个 <case> 含：
  pre_process（可选）→ test_case（必选，且恰有一个容器）→ post_process（可选）
各阶段内为多个 <test_step>。

XML 格式参见 schemas/case.xsd。
"""
import xml.etree.ElementTree as ET
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

from core.xml_schema_validator import RodskiXmlValidator

logger = logging.getLogger("rodski")


class CaseParser:
    def __init__(self, case_path: str):
        """初始化 Case 解析器

        Args:
            case_path: case XML 文件路径，或 case/ 目录路径（加载目录下所有 XML）
        """
        self.case_path = Path(case_path)
        self._cases: List[Dict[str, Any]] = []
        logger.debug(f"初始化 CaseParser: path={case_path}")

    def parse_cases(self) -> List[Dict[str, Any]]:
        """解析所有用例，返回用例列表"""
        self._cases = []

        if self.case_path.is_dir():
            for xml_file in sorted(self.case_path.glob("*.xml")):
                self._cases.extend(self._parse_file(xml_file))
        elif self.case_path.is_file():
            self._cases = self._parse_file(self.case_path)
        else:
            logger.error(f"用例路径不存在: {self.case_path}")
            raise FileNotFoundError(f"用例路径不存在: {self.case_path}")

        logger.info(f"解析完成: 共 {len(self._cases)} 个用例")
        return self._cases

    def _parse_file(self, xml_path: Path) -> List[Dict[str, Any]]:
        """解析单个 case XML 文件"""
        logger.debug(f"解析用例文件: {xml_path}")
        RodskiXmlValidator.validate_file(xml_path, RodskiXmlValidator.KIND_CASE)
        tree = ET.parse(xml_path)
        root = tree.getroot()
        cases = []

        # 读取根节点的 step_wait 属性（毫秒）
        step_wait_ms = root.get('step_wait', None)

        for case_node in root.findall('case'):
            execute = case_node.get('execute', '否').strip()
            if execute != '是':
                continue

            case = {
                'case_id': case_node.get('id', ''),
                'title': case_node.get('title', ''),
                'description': case_node.get('description', ''),
                'component_type': case_node.get('component_type', ''),
                'step_wait': step_wait_ms,
                'metadata': self._parse_metadata(case_node.find('metadata')),
                'pre_process': self._parse_phase_steps(case_node.find('pre_process')),
                'test_case': self._parse_phase_steps(case_node.find('test_case')),
                'post_process': self._parse_phase_steps(case_node.find('post_process')),
            }
            cases.append(case)

        return cases

    @staticmethod
    def _parse_metadata(metadata_node: Optional[ET.Element]) -> Dict[str, str]:
        """解析元数据节点"""
        if metadata_node is None:
            return {}
        return {
            'created_by': metadata_node.get('created_by', ''),
            'created_at': metadata_node.get('created_at', ''),
            'updated_by': metadata_node.get('updated_by', ''),
            'updated_at': metadata_node.get('updated_at', ''),
            'success_rate': metadata_node.get('success_rate', ''),
            'last_run': metadata_node.get('last_run', ''),
        }

    @staticmethod
    def _parse_phase_steps(phase_node: Optional[ET.Element]) -> List[Dict[str, str]]:
        """解析一个阶段容器内的全部 test_step，支持 if 和 loop"""
        if phase_node is None:
            return []
        steps = []
        for el in phase_node:
            if el.tag == 'test_step':
                step = CaseParser._parse_step_element(el)
                if step.get('action'):
                    steps.append(step)
            elif el.tag == 'if':
                steps.append(CaseParser._parse_if_element(el))
            elif el.tag == 'loop':
                steps.append(CaseParser._parse_loop_element(el))
        return steps

    @staticmethod
    def _parse_step_element(el: ET.Element) -> Dict[str, str]:
        return {
            'action': str(el.get('action', '') or '').strip(),
            'model': str(el.get('model', '') or '').strip(),
            'data': str(el.get('data', '') or '').strip(),
        }

    @staticmethod
    def _parse_if_element(el: ET.Element) -> Dict[str, Any]:
        """解析 if 条件元素（支持 else 分支）"""
        condition = str(el.get('condition', '') or '').strip()

        # 解析 then 分支
        then_steps = [
            CaseParser._parse_step_element(step)
            for step in el.findall('test_step')
            if step.get('action')
        ]

        # 解析 else 分支
        else_steps = []
        else_el = el.find('else')
        if else_el is not None:
            else_steps = [
                CaseParser._parse_step_element(step)
                for step in else_el.findall('test_step')
                if step.get('action')
            ]

        return {
            'type': 'if',
            'condition': condition,
            'steps': then_steps,
            'else_steps': else_steps,
        }

    @staticmethod
    def _parse_loop_element(el: ET.Element) -> Dict[str, Any]:
        """解析 loop 循环元素"""
        return {
            'type': 'loop',
            'range': str(el.get('range', '') or '').strip(),
            'var': str(el.get('var', 'item') or '').strip(),
            'steps': [CaseParser._parse_step_element(step)
                     for step in el.findall('test_step')
                     if step.get('action')],
        }

    def close(self):
        pass
