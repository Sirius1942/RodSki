"""模型服务"""
from typing import List, Optional, Dict
from src.parsers.model_parser import ModelParser, PageModel


class ModelService:
    """模型管理服务"""
    
    def __init__(self, data_path: str = None):
        if data_path is None:
            import yaml
            with open('config.yaml') as f:
                config = yaml.safe_load(f)
                data_path = config['rodski']['data_path']
        
        self.parser = ModelParser(data_path)
        self.data_path = data_path
    
    def list_modules(self) -> List[str]:
        """获取所有模块"""
        return self.parser.list_modules()
    
    def list_models(self, module: Optional[str] = None) -> List[Dict]:
        """获取模型列表"""
        models = self.parser.list_models(module)
        return [self.parser.model_to_dict(m) for m in models]
    
    def get_model(self, model_name: str) -> Optional[Dict]:
        """获取单个模型"""
        model = self.parser.get_model_by_name(model_name)
        if model:
            return self.parser.model_to_dict(model)
        return None
    
    def list_all_model_names(self) -> List[str]:
        """获取所有模型名称"""
        return self.parser.list_all_model_names()
    
    def search_models(self, keyword: str) -> List[Dict]:
        """搜索模型"""
        all_models = self.parser.list_models()
        results = []
        
        keyword_lower = keyword.lower()
        for model in all_models:
            if keyword_lower in model.name.lower():
                results.append(self.parser.model_to_dict(model))
        
        return results
