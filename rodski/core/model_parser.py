import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional


class ModelParser:
    def __init__(self, xml_path: str):
        self.xml_path = Path(xml_path)
        self.tree = ET.parse(self.xml_path)
        self.root = self.tree.getroot()
        self.models = self._parse_models()

    def _parse_models(self) -> Dict[str, Dict[str, Dict[str, str]]]:
        """解析所有模型，支持两种格式"""
        models = {}
        for model in self.root.findall('model'):
            model_name = model.get('name')
            if not model_name:
                continue
            elements = {}
            for element in model.findall('element'):
                element_name = element.get('name')
                if not element_name:
                    continue
                location = element.find('location')
                if location is not None:
                    elements[element_name] = {
                        'type': location.get('type', 'id'),
                        'value': location.text or ''
                    }
                elif element.get('type') and element.get('value'):
                    elements[element_name] = {
                        'type': element.get('type'),
                        'value': element.get('value')
                    }
            models[model_name] = elements
        return models

    def get_element(self, locator: str) -> Optional[Dict[str, str]]:
        """Parse ModelName.ElementName format"""
        if '.' not in locator:
            return None
        model_name, element_name = locator.split('.', 1)
        model = self.models.get(model_name)
        if not model:
            return None
        element = model.get(element_name)
        if not element:
            return None
        return {'locator_type': element['type'], 'locator_value': element['value']}

    def get_model(self, model_name: str) -> Optional[Dict[str, Dict[str, str]]]:
        """获取整个模型的所有元素"""
        return self.models.get(model_name)
