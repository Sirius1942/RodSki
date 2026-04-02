"""用例服务"""
from typing import List, Optional, Dict
from src.parsers.case_parser import CaseParser
import os


class CaseService:
    """用例管理服务"""
    
    def __init__(self, data_path: str = None):
        if data_path is None:
            import yaml
            with open('config.yaml') as f:
                config = yaml.safe_load(f)
                data_path = config['rodski']['data_path']
        
        self.parser = CaseParser(data_path)
        self.data_path = data_path
    
    def list_modules(self) -> List[str]:
        """获取所有模块"""
        return self.parser.list_modules()
    
    def list_cases(self, module: Optional[str] = None) -> List[Dict]:
        """获取用例列表"""
        cases = self.parser.list_cases(module)
        return [self.parser.case_to_dict(c) for c in cases]
    
    def get_case(self, case_id: str) -> Optional[Dict]:
        """获取单个用例"""
        case = self.parser.get_case_by_id(case_id)
        if case:
            return self.parser.case_to_dict(case)
        return None
    
    def search_cases(self, keyword: str) -> List[Dict]:
        """搜索用例"""
        all_cases = self.parser.list_cases()
        results = []
        
        keyword_lower = keyword.lower()
        for case in all_cases:
            if keyword_lower in case.title.lower() or keyword_lower in case.id.lower():
                results.append(self.parser.case_to_dict(case))
        
        return results
    
    def explain_case(self, case_id: str) -> Optional[str]:
        """解释用例为可读文本"""
        case = self.parser.get_case_by_id(case_id)
        if not case:
            return None
        
        lines = []
        lines.append(f"用例: {case.title}")
        lines.append(f"ID: {case.id}")
        if case.description:
            lines.append(f"描述: {case.description}")
        lines.append(f"执行: {case.execute}")
        lines.append(f"组件类型: {case.component_type}")
        lines.append("")
        
        for phase_name, phase in case.phases.items():
            lines.append(f"=== 阶段: {phase_name} ===")
            for i, step in enumerate(phase.steps, 1):
                lines.append(f"  步骤 {i}: {step.action}")
                if step.data:
                    lines.append(f"    数据: {step.data}")
                if step.model:
                    lines.append(f"    模型: {step.model}")
            lines.append("")
        
        return "\n".join(lines)
