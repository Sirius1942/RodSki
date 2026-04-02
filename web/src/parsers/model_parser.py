"""模型 XML 解析器 - 独立实现，不依赖 RodSki"""
import os
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class Element:
    """页面元素"""
    name: str
    type: str
    value: str
    desc: str


@dataclass
class PageModel:
    """页面模型"""
    name: str
    elements: List[Element]
    xml_path: str = ""


class ModelParser:
    """模型 XML 解析器"""
    
    def __init__(self, data_path: str):
        self.data_path = data_path
    
    def _parse_element(self, elem) -> Element:
        """解析单个元素"""
        name = elem.get('name', '')
        elem_type = elem.get('type', '')
        value = elem.get('value', '')
        desc = elem.get('desc', '')
        return Element(name=name, type=elem_type, value=value, desc=desc)
    
    def parse_model(self, model_elem, xml_path: str = "") -> PageModel:
        """解析单个模型"""
        name = model_elem.get('name', '')
        elements = [self._parse_element(e) for e in model_elem.findall('element')]
        return PageModel(name=name, elements=elements, xml_path=xml_path)
    
    def parse_file(self, xml_path: str) -> List[PageModel]:
        """解析模型文件"""
        models = []
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            for model_elem in root.findall('model'):
                model = self.parse_model(model_elem, xml_path)
                models.append(model)
        except Exception as e:
            print(f"解析模型文件失败 {xml_path}: {e}")
        
        return models
    
    def list_model_files(self, module: Optional[str] = None) -> List[str]:
        """列出所有模型文件"""
        model_files = []
        search_path = self.data_path
        
        if module:
            search_path = os.path.join(self.data_path, module, 'model')
        
        if not os.path.exists(search_path):
            return model_files
        
        for root, dirs, files in os.walk(search_path):
            for f in files:
                if f.endswith('.xml') or f == 'model.xml':
                    model_files.append(os.path.join(root, f))
        
        return model_files
    
    def list_modules(self) -> List[str]:
        """列出所有模块"""
        modules = []
        if not os.path.exists(self.data_path):
            return modules
        
        for item in os.listdir(self.data_path):
            item_path = os.path.join(self.data_path, item)
            model_dir = os.path.join(item_path, 'model')
            if os.path.isdir(item_path) and os.path.exists(model_dir):
                modules.append(item)
        
        return sorted(modules)
    
    def list_models(self, module: Optional[str] = None) -> List[PageModel]:
        """列出所有模型"""
        all_models = []
        model_files = self.list_model_files(module)
        
        for mf in model_files:
            models = self.parse_file(mf)
            all_models.extend(models)
        
        return all_models
    
    def get_model_by_name(self, model_name: str) -> Optional[PageModel]:
        """根据名称获取模型"""
        all_models = self.list_models()
        
        for model in all_models:
            if model.name == model_name:
                return model
        
        return None
    
    def model_to_dict(self, model: PageModel) -> dict:
        """将模型转换为字典"""
        return {
            'name': model.name,
            'elements': [
                {
                    'name': e.name,
                    'type': e.type,
                    'value': e.value,
                    'desc': e.desc
                } for e in model.elements
            ],
            'xml_path': model.xml_path
        }
    
    def list_all_model_names(self) -> List[str]:
        """列出所有模型名称"""
        models = self.list_models()
        return [m.name for m in models]
