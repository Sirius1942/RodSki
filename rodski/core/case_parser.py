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

        # 读取 <cases> 套件级 tags（逗号分隔 → list），所有 case 共享
        raw_suite_tags = (root.get('tags') or '').strip()
        suite_tags = [t.strip() for t in raw_suite_tags.split(',') if t.strip()] if raw_suite_tags else []

        for case_node in root.findall('case'):
            execute = case_node.get('execute', '否').strip()
            if execute != '是':
                continue

            case = {
                'case_id': case_node.get('id', ''),
                'title': case_node.get('title', ''),
                'description': case_node.get('description', ''),
                'component_type': case_node.get('component_type', ''),
                'expect_fail': case_node.get('expect_fail', '否').strip(),
                'tags': suite_tags,
                'priority': (case_node.get('priority') or '').strip(),
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
        """解析一个阶段容器内的全部 test_step，支持 if/elif/else 和 loop"""
        if phase_node is None:
            return []
        steps = []
        children = list(phase_node)
        i = 0
        while i < len(children):
            el = children[i]
            if el.tag == 'test_step':
                step = CaseParser._parse_step_element(el)
                if step.get('action'):
                    steps.append(step)
                i += 1
            elif el.tag == 'if':
                if_block = CaseParser._parse_if_element(el, depth=1)
                # 收集紧跟的 elif / else 元素
                elif_chain: List[Dict[str, Any]] = []
                else_steps: List[Dict[str, str]] = []
                j = i + 1
                while j < len(children):
                    nxt = children[j]
                    if nxt.tag == 'elif':
                        elif_chain.append({
                            'condition': str(nxt.get('condition', '') or '').strip(),
                            'steps': [
                                CaseParser._parse_step_element(s)
                                for s in nxt.findall('test_step')
                                if s.get('action')
                            ],
                        })
                        j += 1
                    elif nxt.tag == 'else':
                        else_steps = [
                            CaseParser._parse_step_element(s)
                            for s in nxt.findall('test_step')
                            if s.get('action')
                        ]
                        j += 1
                        break  # else 终止链
                    else:
                        break
                if elif_chain:
                    if_block['elif_chain'] = elif_chain
                if else_steps:
                    if_block['else_steps'] = else_steps
                steps.append(if_block)
                i = j
            elif el.tag == 'loop':
                steps.append(CaseParser._parse_loop_element(el))
                i += 1
            else:
                # 跳过未识别的元素（如独立的 elif/else 不紧跟 if）
                i += 1
        return steps

    @staticmethod
    def _parse_step_element(el: ET.Element) -> Dict[str, str]:
        return {
            'action': str(el.get('action', '') or '').strip(),
            'model': str(el.get('model', '') or '').strip(),
            'data': str(el.get('data', '') or '').strip(),
        }

    @staticmethod
    def _parse_if_element(el: ET.Element, depth: int = 1) -> Dict[str, Any]:
        """解析 if 条件元素（支持 else 分支和嵌套 if，最多 2 层）

        Args:
            el: if XML 元素
            depth: 当前嵌套深度（1 = 顶层，2 = 第二层）
        """
        condition = str(el.get('condition', '') or '').strip()

        # 解析 then 分支（直属子元素，支持 test_step 和嵌套 if）
        then_steps: List[Dict[str, Any]] = []
        for child in el:
            if child.tag == 'test_step' and child.get('action'):
                then_steps.append(CaseParser._parse_step_element(child))
            elif child.tag == 'if':
                if depth >= 2:
                    raise ValueError(
                        f"if 嵌套深度超过 2 层限制 (condition={condition})"
                    )
                then_steps.append(CaseParser._parse_if_element(child, depth=depth + 1))
            # else 元素在下面单独处理

        # 解析 else 分支（仅内联 else，非 phase 级别）
        else_steps: List[Dict[str, str]] = []
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
