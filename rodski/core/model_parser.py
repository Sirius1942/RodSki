import xml.etree.ElementTree as ET
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

from core.xml_schema_validator import RodskiXmlValidator

logger = logging.getLogger("rodski")


# 驱动类型常量，对应老 SKI 中 element 的 type 属性
DRIVER_TYPE_WEB = "web"
DRIVER_TYPE_INTERFACE = "interface"
DRIVER_TYPE_OTHER = "other"

# 有效的定位器类型
VALID_LOCATOR_TYPES = [
    # 传统定位器
    "id", "class", "css", "xpath", "text", "tag", "name", "static", "field",
    # 视觉定位器
    "vision", "ocr", "vision_bbox",
]

# 视觉定位器类型集合
VISION_LOCATOR_TYPES = {"vision", "ocr", "vision_bbox"}


class ModelParser:
    def __init__(self, xml_path: str):
        self.xml_path = Path(xml_path)
        logger.info(f"加载模型文件: {self.xml_path}")
        RodskiXmlValidator.validate_file(self.xml_path, RodskiXmlValidator.KIND_MODEL)
        self.tree = ET.parse(self.xml_path)
        self.root = self.tree.getroot()
        self.models = self._parse_models()
        logger.info(f"模型解析完成: 共 {len(self.models)} 个模型")

    def _parse_models(self) -> Dict[str, Dict[str, Dict]]:
        """解析所有模型，兼容老 SKI 格式和简化格式

        老 SKI 格式 (带完整元数据):
            <element name="username" interfacename="" group="" type="web">
                <type>input</type>
                <location type="id" item="">usernameInput</location>
            </element>

        简化格式:
            <element name="UsernameInput" type="id" value="username"/>

        简化格式（locator 属性）:
            <element name="searchBtn" locator="vision:搜索按钮"/>

        多定位器格式:
            <element name="loginBtn" type="web">
                <type>button</type>
                <location type="id" priority="1">loginBtn</location>
                <location type="ocr" priority="2">登录</location>
            </element>

        解析后每个 element 包含:
            - type: 主定位器类型 (id/xpath/css/vision/ocr/...)
            - value: 主定位器值
            - driver_type: 驱动类型 (web/interface/other)，用于关键字路由
            - element_type: 元素 UI 类型 (input/button/select/...)
            - interfacename: 接口名称（interface 类型时使用）
            - locations: 多定位器列表，按 priority 排序
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

    def _parse_element(self, elem_node) -> Optional[Dict]:
        """解析单个 element 节点

        支持三种格式：
        1. 老 SKI 完整格式（带 location 子节点）：
           <element name="username" type="web">
               <type>input</type>
               <location type="id" priority="1">username</location>
               <location type="ocr" priority="2">用户名</location>
           </element>

        2. 简化格式（type+value 属性）：
           <element name="username" type="id" value="username"/>

        3. 简化格式（locator 属性，冒号分隔）：
           <element name="searchBtn" locator="vision:搜索按钮"/>

        返回结构：
            {
                'type': 主定位器类型（向后兼容）,
                'value': 主定位器值（向后兼容）,
                'driver_type': 驱动类型,
                'element_type': 元素 UI 类型,
                'interfacename': 接口名称,
                'locations': [
                    {'type': 'id', 'value': 'username', 'priority': 1},
                    {'type': 'ocr', 'value': '用户名', 'priority': 2}
                ]
            }
        """
        # 检查 locator 属性格式（简化格式3：locator="vision:搜索按钮"）
        locator_attr = elem_node.get('locator')
        if locator_attr and ':' in locator_attr:
            locator_type, locator_value = locator_attr.split(':', 1)
            locator_type = locator_type.strip()
            locator_value = locator_value.strip()
            if locator_type in VALID_LOCATOR_TYPES:
                return {
                    'type': locator_type,
                    'value': locator_value,
                    'driver_type': elem_node.get('type', DRIVER_TYPE_WEB),
                    'element_type': '',
                    'interfacename': elem_node.get('interfacename', ''),
                    'locations': [{'type': locator_type, 'value': locator_value, 'priority': 1}],
                }

        # 检查多个 location 子节点
        location_nodes = elem_node.findall('location')

        if location_nodes:
            # 老 SKI 完整格式 - 支持多定位器
            type_node = elem_node.find('type')
            locations = []

            for loc in location_nodes:
                loc_type = loc.get('type', 'id')
                loc_value = (loc.text or '').strip()
                loc_priority = int(loc.get('priority', '1'))
                if loc_type in VALID_LOCATOR_TYPES and loc_value:
                    locations.append({
                        'type': loc_type,
                        'value': loc_value,
                        'priority': loc_priority,
                    })

            # 按 priority 从小到大排序
            locations.sort(key=lambda x: x['priority'])

            if locations:
                return {
                    'type': locations[0]['type'],  # 主定位器（向后兼容）
                    'value': locations[0]['value'],  # 主定位器值（向后兼容）
                    'driver_type': elem_node.get('type', DRIVER_TYPE_WEB),
                    'element_type': (type_node.text or '').strip() if type_node is not None else '',
                    'interfacename': elem_node.get('interfacename', ''),
                    'locations': locations,
                }

        elif elem_node.get('type') and elem_node.get('value'):
            # 简化格式：type 是定位器类型，value 是定位器值
            loc_type = elem_node.get('type')
            loc_value = elem_node.get('value')
            if loc_type in VALID_LOCATOR_TYPES:
                # field/static 类型属于接口驱动
                elem_driver_type = DRIVER_TYPE_INTERFACE if loc_type in ('field', 'static') else DRIVER_TYPE_WEB
                return {
                    'type': loc_type,
                    'value': loc_value,
                    'driver_type': elem_driver_type,
                    'element_type': '',
                    'interfacename': '',
                    'locations': [{'type': loc_type, 'value': loc_value, 'priority': 1}],
                }
        return None

    def get_element(self, locator: str) -> Optional[Dict]:
        """通过 ModelName.ElementName 格式获取元素定位信息

        返回：
            {
                'locator_type': 主定位器类型,
                'locator_value': 主定位器值,
                'driver_type': 驱动类型,
                'element_type': 元素 UI 类型,
                'locations': [  # 多定位器列表（按 priority 排序）
                    {'type': 'id', 'value': 'username', 'priority': 1},
                    {'type': 'ocr', 'value': '用户名', 'priority': 2}
                ]
            }
        """
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
            'locations': element.get('locations', []),
        }

    def get_model(self, model_name: str) -> Optional[Dict[str, Dict[str, str]]]:
        """获取整个模型的所有元素"""
        return self.models.get(model_name)

    def merge_models(self, models: Dict[str, Dict[str, Dict[str, str]]]) -> None:
        """合并运行时注入的模型（如 insert 附带的临时 model 片段）。"""
        for model_name, elements in models.items():
            if model_name not in self.models:
                self.models[model_name] = {}
            self.models[model_name].update(elements)

    def get_model_driver_type(self, model_name: str) -> str:
        """获取模型的主要驱动类型（取第一个元素的 driver_type）"""
        model = self.models.get(model_name)
        if not model:
            return DRIVER_TYPE_WEB
        for element in model.values():
            return element.get('driver_type', DRIVER_TYPE_WEB)
        return DRIVER_TYPE_WEB

    @staticmethod
    def is_vision_locator(locator_type: str) -> bool:
        """判断是否是视觉定位器类型

        Args:
            locator_type: 定位器类型字符串

        Returns:
            True 如果是 vision/ocr/vision_bbox 类型
        """
        return locator_type in VISION_LOCATOR_TYPES

    def get_locations(self, locator: str) -> List[Dict[str, Union[str, int]]]:
        """获取元素的所有定位器（按 priority 排序）

        Args:
            locator: ModelName.ElementName 格式的定位器

        Returns:
            按 priority 排序的定位器列表，每个元素包含 type/value/priority
            如果元素不存在返回空列表
        """
        element = self.get_element(locator)
        if not element:
            return []
        return element.get('locations', [])
