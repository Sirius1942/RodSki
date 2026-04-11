"""用例 XML 解析器 - 独立实现，不依赖 RodSki"""
import os
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class TestStep:
    """测试步骤"""
    action: str
    data: str
    model: Optional[str] = None


@dataclass
class TestPhase:
    """测试阶段（pre_process, test_case, post_process）"""
    name: str
    steps: List[TestStep]


@dataclass
class TestCase:
    """测试用例"""
    id: str
    title: str
    description: str
    execute: str
    component_type: str
    phases: Dict[str, TestPhase]
    xml_path: str = ""


class CaseParser:
    """用例 XML 解析器"""
    
    def __init__(self, data_path: str):
        self.data_path = data_path
    
    def _get_step_info(self, step_elem) -> TestStep:
        """解析单个测试步骤"""
        action = step_elem.get('action', '')
        data = step_elem.get('data', '')
        model = step_elem.get('model')
        return TestStep(action=action, data=data, model=model)
    
    def _parse_phase(self, phase_elem) -> TestPhase:
        """解析测试阶段"""
        name = phase_elem.tag
        steps = [self._get_step_info(s) for s in phase_elem.findall('test_step')]
        return TestPhase(name=name, steps=steps)
    
    def parse_case(self, case_elem, xml_path: str = "") -> TestCase:
        """解析单个用例"""
        case_id = case_elem.get('id', '')
        title = case_elem.get('title', '')
        description = case_elem.get('description', '')
        execute = case_elem.get('execute', '是')
        component_type = case_elem.get('component_type', '界面')
        
        phases = {}
        for phase_name in ['pre_process', 'test_case', 'post_process']:
            phase_elem = case_elem.find(phase_name)
            if phase_elem is not None:
                phases[phase_name] = self._parse_phase(phase_elem)
        
        return TestCase(
            id=case_id,
            title=title,
            description=description,
            execute=execute,
            component_type=component_type,
            phases=phases,
            xml_path=xml_path
        )
    
    def parse_file(self, xml_path: str) -> List[TestCase]:
        """解析用例文件"""
        cases = []
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            for case_elem in root.findall('case'):
                case = self.parse_case(case_elem, xml_path)
                cases.append(case)
        except Exception as e:
            print(f"解析用例文件失败 {xml_path}: {e}")
        
        return cases
    
    def list_case_files(self, module: Optional[str] = None) -> List[str]:
        """列出所有用例文件"""
        case_files = []
        search_path = self.data_path
        
        if module:
            search_path = os.path.join(self.data_path, module, 'case')
        
        if not os.path.exists(search_path):
            return case_files
        
        for root, dirs, files in os.walk(search_path):
            for f in files:
                if f.endswith('.xml'):
                    case_files.append(os.path.join(root, f))
        
        return case_files
    
    def list_modules(self) -> List[str]:
        """列出所有模块"""
        modules = []
        if not os.path.exists(self.data_path):
            return modules
        
        for item in os.listdir(self.data_path):
            item_path = os.path.join(self.data_path, item)
            case_dir = os.path.join(item_path, 'case')
            if os.path.isdir(item_path) and os.path.exists(case_dir):
                modules.append(item)
        
        return sorted(modules)
    
    def list_cases(self, module: Optional[str] = None) -> List[TestCase]:
        """列出所有用例"""
        all_cases = []
        case_files = self.list_case_files(module)
        
        for cf in case_files:
            cases = self.parse_file(cf)
            all_cases.extend(cases)
        
        return all_cases
    
    def get_case_by_id(self, case_id: str) -> Optional[TestCase]:
        """根据 ID 获取用例"""
        all_cases = self.list_cases()
        
        for case in all_cases:
            if case.id == case_id:
                return case
        
        return None
    
    def case_to_dict(self, case: TestCase) -> dict:
        """将用例转换为字典"""
        return {
            'id': case.id,
            'title': case.title,
            'description': case.description,
            'execute': case.execute,
            'component_type': case.component_type,
            'phases': {
                name: {
                    'steps': [
                        {
                            'action': s.action,
                            'data': s.data,
                            'model': s.model
                        } for s in phase.steps
                    ]
                } for name, phase in case.phases.items()
            },
            'xml_path': case.xml_path
        }
    
    def explain_case(self, case: TestCase) -> str:
        """生成用例的人类可读说明"""
        lines = [f"# {case.title}"]
        lines.append(f"**用例ID**: {case.id}")
        lines.append(f"**描述**: {case.description}")
        lines.append(f"**组件类型**: {case.component_type}")
        lines.append("")
        
        phase_names = {
            'pre_process': '🔧 前置准备',
            'test_case': '🧪 测试步骤',
            'post_process': '🧹 清理工作'
        }
        
        for phase_name, phase in case.phases.items():
            if phase.steps:
                lines.append(f"## {phase_names.get(phase_name, phase_name)}")
                for i, step in enumerate(phase.steps, 1):
                    model_info = f" [使用 {step.model}]" if step.model else ""
                    lines.append(f"{i}. **{step.action}**{model_info}: `{step.data}`")
                lines.append("")
        
        return "\n".join(lines)
