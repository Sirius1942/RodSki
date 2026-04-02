"""测试数据解析器 - 独立实现，不依赖 RodSki"""
import os
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class DataItem:
    """数据项"""
    name: str
    value: str


@dataclass
class DataSet:
    """数据集（如登录数据 xiaoli_login）"""
    name: str
    data: Dict[str, str]


class DataParser:
    """测试数据 XML 解析器"""
    
    def __init__(self, data_path: str):
        self.data_path = data_path
    
    def parse_data_file(self, xml_path: str) -> List[DataSet]:
        """解析数据文件"""
        datasets = []
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            for data_elem in root.findall('data'):
                dataset = self._parse_dataset(data_elem)
                if dataset:
                    datasets.append(dataset)
        except Exception as e:
            print(f"解析数据文件失败 {xml_path}: {e}")
        
        return datasets
    
    def _parse_dataset(self, data_elem) -> Optional[DataSet]:
        """解析单个数据集"""
        name = data_elem.get('name', '')
        if not name:
            return None
        
        items = {}
        for item_elem in data_elem.findall('item'):
            item_name = item_elem.get('name', '')
            item_value = item_elem.get('value', '')
            if item_name:
                items[item_name] = item_value
        
        return DataSet(name=name, data=items)
    
    def list_data_files(self, module: Optional[str] = None) -> List[str]:
        """列出所有数据文件"""
        data_files = []
        search_path = self.data_path
        
        if module:
            search_path = os.path.join(self.data_path, module, 'data')
        
        if not os.path.exists(search_path):
            return data_files
        
        for root, dirs, files in os.walk(search_path):
            for f in files:
                if f.endswith('.xml') or f == 'data.xml':
                    data_files.append(os.path.join(root, f))
        
        return data_files
    
    def list_data(self, module: Optional[str] = None) -> List[DataSet]:
        """列出所有数据"""
        all_data = []
        data_files = self.list_data_files(module)
        
        for df in data_files:
            datasets = self.parse_data_file(df)
            all_data.extend(datasets)
        
        return all_data
    
    def get_data_by_name(self, data_name: str, module: Optional[str] = None) -> Optional[DataSet]:
        """根据名称获取数据"""
        all_data = self.list_data(module)
        
        for ds in all_data:
            if ds.name == data_name:
                return ds
        
        return None
    
    def dataset_to_dict(self, dataset: DataSet) -> dict:
        """将数据集转换为字典"""
        return {
            'name': dataset.name,
            'data': dataset.data
        }
