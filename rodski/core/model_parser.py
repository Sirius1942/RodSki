import xml.etree.ElementTree as ET
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

from core.xml_schema_validator import RodskiXmlValidator

logger = logging.getLogger("rodski")

MODEL_TYPE_UI = "ui"
MODEL_TYPE_INTERFACE = "interface"
MODEL_TYPE_DATABASE = "database"
MODEL_TYPE_OTHER = "other"

LEGACY_DRIVER_TYPE_WEB = "web"
LEGACY_DRIVER_TYPE_INTERFACE = "interface"
LEGACY_DRIVER_TYPE_OTHER = "other"
LEGACY_DRIVER_TYPES = {
    LEGACY_DRIVER_TYPE_WEB,
    LEGACY_DRIVER_TYPE_INTERFACE,
    LEGACY_DRIVER_TYPE_OTHER,
    "windows",
    "macos",
}

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
        """解析所有模型

        唯一支持的元素定位格式：
            <model name="Login" type="ui">
                <element name="username" type="web">
                    <type>input</type>
                    <location type="id" priority="1">usernameInput</location>
                    <location type="xpath" priority="2">//input[@id='user']</location>
                </element>
            </model>

        Database 格式：
            <model name="OrderQuery" type="database" connection="sqlite_db">
                <query name="list">
                    <sql>SELECT * FROM orders WHERE status = :status LIMIT :limit</sql>
                </query>
            </model>

        解析后每个 model 包含:
            - __model_type__: 模型类型 (ui/interface/database)
            - __auto_capture_type__: type 的 auto_capture 规则
            - __auto_capture_send__: send 的 auto_capture 规则
            - __connection__: database 类型的连接配置名 (仅 database 类型)
            - __queries__: database 类型的查询定义 (仅 database 类型)
            - 其余 key 为元素定义
        """
        models = {}
        for model_node in self.root.findall('model'):
            model_name = model_node.get('name')
            if not model_name:
                continue

            model_type = model_node.get('type', '').strip() or None
            elements = {}
            inferred_model_type = None

            # 如果是 database 类型，解析查询定义
            if model_type == MODEL_TYPE_DATABASE:
                connection = model_node.get('connection', '').strip()
                queries = self._parse_queries(model_node)
                models[model_name] = elements
                models[model_name]['__model_type__'] = MODEL_TYPE_DATABASE
                models[model_name]['__connection__'] = connection
                models[model_name]['__queries__'] = queries
                models[model_name]['__auto_capture_type__'] = None
                models[model_name]['__auto_capture_send__'] = None
                continue

            for elem_node in model_node.findall('element'):
                element_name = elem_node.get('name')
                if not element_name:
                    continue

                element_info = self._parse_element(elem_node, model_type)
                if element_info:
                    inferred_model_type = inferred_model_type or element_info.get('model_type')
                    elements[element_name] = element_info

            # Parse auto_capture nodes
            auto_capture_type = None
            auto_capture_send = None
            for ac_node in model_node.findall('auto_capture'):
                trigger = ac_node.get('trigger', '')
                fields = []
                for field_node in ac_node.findall('field'):
                    name = field_node.get('name', '')
                    path = field_node.get('path', '')
                    loc_node = field_node.find('location')
                    if path:
                        fields.append({'name': name, 'path': path})
                    elif loc_node is not None:
                        fields.append({'name': name, 'type': loc_node.get('type', 'id'), 'value': loc_node.text or ''})
                if trigger == 'type':
                    auto_capture_type = fields
                elif trigger == 'send':
                    auto_capture_send = fields

            models[model_name] = elements
            models[model_name]['__model_type__'] = model_type or inferred_model_type or MODEL_TYPE_UI
            models[model_name]['__auto_capture_type__'] = auto_capture_type
            models[model_name]['__auto_capture_send__'] = auto_capture_send
        return models

    def _parse_element(self, elem_node, declared_model_type: Optional[str] = None) -> Optional[Dict]:
        """解析单个 element 节点。

        唯一支持的格式：<location type="...">value</location> 子元素。
        """
        raw_type = (elem_node.get('type') or '').strip()
        legacy_driver_type = raw_type if raw_type in LEGACY_DRIVER_TYPES else ''
        type_node = elem_node.find('type')
        child_type = (type_node.text or '').strip() if type_node is not None and type_node.text else ''

        location_nodes = elem_node.findall('location')
        if location_nodes:
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

            locations.sort(key=lambda x: x['priority'])
            if locations:
                primary = locations[0]
                model_type = declared_model_type or self._infer_model_type(legacy_driver_type, primary['type'])
                return {
                    'type': primary['type'],
                    'value': primary['value'],
                    'locator_type': primary['type'],
                    'locator_value': primary['value'],
                    'model_type': model_type,
                    'element_type': child_type or self._infer_element_type(raw_type, primary['type'], model_type),
                    'interfacename': elem_node.get('interfacename', ''),
                    'locations': locations,
                }

        return None

    def _infer_model_type(self, legacy_driver_type: str, locator_type: str) -> str:
        if legacy_driver_type == LEGACY_DRIVER_TYPE_INTERFACE:
            return MODEL_TYPE_INTERFACE
        if locator_type in ('field', 'static'):
            return MODEL_TYPE_INTERFACE
        return MODEL_TYPE_UI

    def _infer_element_type(self, raw_type: str, locator_type: str, model_type: str) -> str:
        if raw_type and raw_type not in LEGACY_DRIVER_TYPES and raw_type not in VALID_LOCATOR_TYPES:
            return raw_type
        if model_type == MODEL_TYPE_INTERFACE:
            if locator_type == 'static':
                return 'static'
            if locator_type == 'field':
                return 'field'
        return ''

    def _parse_queries(self, model_node) -> Dict[str, Dict[str, str]]:
        """解析 database 模型中的 query 定义

        返回格式:
        {
            "list": {
                "sql": "SELECT * FROM orders WHERE status = :status LIMIT :limit",
                "remark": "查询订单列表"
            }
        }
        """
        queries = {}
        for query_node in model_node.findall('query'):
            query_name = query_node.get('name', '').strip()
            if not query_name:
                continue

            sql_node = query_node.find('sql')
            sql = (sql_node.text or '').strip() if sql_node is not None else ''
            remark = query_node.get('remark', '').strip()

            if sql:
                queries[query_name] = {
                    'sql': sql,
                    'remark': remark
                }

        return queries

    def get_element(self, locator: str) -> Optional[Dict]:
        """通过 ModelName.ElementName 格式获取元素定位信息。"""
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
            'locator_type': element['locator_type'],
            'locator_value': element['locator_value'],
            'model_type': element.get('model_type', self.get_model_type(model_name)),
            'element_type': element.get('element_type', ''),
            'locations': element.get('locations', []),
        }

    def get_auto_capture(self, model_name: str, trigger: str) -> list:
        """返回模型的 auto_capture 规则列表，无则返回空列表"""
        model = self.models.get(model_name, {})
        return model.get(f'__auto_capture_{trigger}__') or []

    def get_model(self, model_name: str) -> Optional[Dict[str, Dict[str, str]]]:
        """获取整个模型的所有元素。"""
        return self.models.get(model_name)

    def get_model_type(self, model_name: str) -> str:
        model = self.models.get(model_name)
        if not model:
            return MODEL_TYPE_UI
        return model.get('__model_type__', MODEL_TYPE_UI)

    def merge_models(self, models: Dict[str, Dict[str, Dict[str, str]]]) -> None:
        """合并运行时注入的模型（如 insert 附带的临时 model 片段）。"""
        for model_name, elements in models.items():
            if model_name not in self.models:
                self.models[model_name] = {'__model_type__': MODEL_TYPE_UI}
            self.models[model_name].update(elements)

    def get_model_driver_type(self, model_name: str) -> str:
        """兼容旧接口：根据模型类型返回主要执行类型。"""
        model_type = self.get_model_type(model_name)
        if model_type == MODEL_TYPE_INTERFACE:
            return LEGACY_DRIVER_TYPE_INTERFACE
        return LEGACY_DRIVER_TYPE_WEB

    @staticmethod
    def is_vision_locator(locator_type: str) -> bool:
        """判断是否是视觉定位器类型。"""
        return locator_type in VISION_LOCATOR_TYPES

    def get_locations(self, locator: str) -> List[Dict[str, Union[str, int]]]:
        """获取元素的所有定位器（按 priority 排序）。"""
        element = self.get_element(locator)
        if not element:
            return []
        return element.get('locations', [])

    def get_database_model(self, model_name: str) -> Optional[Dict[str, Any]]:
        """获取 database 类型模型的完整信息

        返回格式:
        {
            "type": "database",
            "connection": "sqlite_db",
            "queries": {
                "list": {
                    "sql": "SELECT ...",
                    "remark": "查询列表"
                }
            }
        }
        """
        model = self.models.get(model_name)
        if not model:
            return None

        model_type = model.get('__model_type__')
        if model_type != MODEL_TYPE_DATABASE:
            return None

        return {
            'type': MODEL_TYPE_DATABASE,
            'connection': model.get('__connection__', ''),
            'queries': model.get('__queries__', {})
        }
