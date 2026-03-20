import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional


# 驱动类型常量，对应老 SKI 中 element 的 type 属性
DRIVER_TYPE_WEB = "web"
DRIVER_TYPE_INTERFACE = "interface"
DRIVER_TYPE_OTHER = "other"


class ModelParser:
    def __init__(self, xml_path: str):
        self.xml_path = Path(xml_path)
        self.tree = ET.parse(self.xml_path)
        self.root = self.tree.getroot()
        self.models = self._parse_models()

    def _parse_models(self) -> Dict[str, Dict[str, Dict[str, str]]]:
        """解析所有模型，兼容老 SKI 格式和简化格式
        
        老 SKI 格式 (带完整元数据):
            <element name="username" interfacename="" group="" type="web">
                <type>input</type>
                <location type="id" item="">usernameInput</location>
            </element>
        
        简化格式:
            <element name="UsernameInput" type="id" value="username"/>
        
        解析后每个 element 包含:
            - type: 定位器类型 (id/xpath/css/...)
            - value: 定位器值
            - driver_type: 驱动类型 (web/interface/other)，用于关键字路由
            - element_type: 元素 UI 类型 (input/button/select/...)
            - interfacename: 接口名称（interface 类型时使用）
        """
        models = {}
        for model_node in self.root.findall('model'):
            model_name = model_node.get('name')
            if not model_name:
                continue
            elements = {}
            for elem_node in model_node.findall('element'):
                element_name = elem_node.get('name')
                if not element_name:
                    continue
                
                element_info = self._parse_element(elem_node)
                if element_info:
                    elements[element_name] = element_info
            
            models[model_name] = elements
        return models

    def _parse_element(self, elem_node) -> Optional[Dict[str, str]]:
        """解析单个 element 节点"""
        location = elem_node.find('location')
        
        if location is not None:
            # 老 SKI 完整格式
            type_node = elem_node.find('type')
            return {
                'type': location.get('type', 'id'),
                'value': (location.text or '').strip(),
                'driver_type': elem_node.get('type', DRIVER_TYPE_WEB),
                'element_type': (type_node.text or '').strip() if type_node is not None else '',
                'interfacename': elem_node.get('interfacename', ''),
            }
        elif elem_node.get('type') and elem_node.get('value'):
            # 简化格式：type 是定位器类型，默认 web 驱动
            return {
                'type': elem_node.get('type'),
                'value': elem_node.get('value'),
                'driver_type': DRIVER_TYPE_WEB,
                'element_type': '',
                'interfacename': '',
            }
        return None

    def get_element(self, locator: str) -> Optional[Dict[str, str]]:
        """通过 ModelName.ElementName 格式获取元素定位信息"""
        if '.' not in locator:
            return None
        model_name, element_name = locator.split('.', 1)
        model = self.models.get(model_name)
        if not model:
            return None
        element = model.get(element_name)
        if not element:
            return None
        return {
            'locator_type': element['type'],
            'locator_value': element['value'],
            'driver_type': element.get('driver_type', DRIVER_TYPE_WEB),
            'element_type': element.get('element_type', ''),
        }

    def get_model(self, model_name: str) -> Optional[Dict[str, Dict[str, str]]]:
        """获取整个模型的所有元素"""
        return self.models.get(model_name)

    def get_model_driver_type(self, model_name: str) -> str:
        """获取模型的主要驱动类型（取第一个元素的 driver_type）"""
        model = self.models.get(model_name)
        if not model:
            return DRIVER_TYPE_WEB
        for element in model.values():
            return element.get('driver_type', DRIVER_TYPE_WEB)
        return DRIVER_TYPE_WEB
