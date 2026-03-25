"""模型管理 - 页面对象模型的加载、保存、查询、验证

本模块提供基于 JSON 的页面对象模型（POM）管理功能，用于简单场景下的元素定位信息存储。

**与 XML 模型体系的关系**：
- 本模块是轻量级的 JSON 模型管理器，适用于简单的元素定位场景
- core/model_parser.py 提供完整的 XML 模型解析能力，支持复杂的模型定义、继承、变量替换等高级特性
- 两者互不依赖，可根据项目需求选择使用

**适用场景**：
- 简单的页面元素定位信息存储（JSON 格式）
- 快速原型开发或小型项目
- 不需要模型继承、变量替换等高级特性的场景

**不适用场景**：
- 需要使用 XML 模型的复杂项目（请使用 core/model_parser.py）
- 需要模型继承、变量替换、条件判断等高级特性
- 需要与现有 XML 模型体系集成的项目

**使用示例**：
    manager = ModelManager("models")
    manager.register("login_page", {"elements": {"username": "//input[@id='user']"}})
    locator = manager.get("login_page", "username")
"""
import json
from typing import Dict, Any, Optional, List
from pathlib import Path


class ModelManager:
    def __init__(self, model_dir: str = "models"):
        self.model_dir = Path(model_dir)
        self.models: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, model: Dict[str, Any]) -> None:
        self.models[name] = model

    def get(self, name: str, field: str = None, default: Any = None) -> Any:
        model = self.models.get(name)
        if model is None:
            path = self.model_dir / f"{name}.json"
            if path.exists():
                model = json.loads(path.read_text(encoding="utf-8"))
                self.models[name] = model
        if model is None:
            return default
        if field:
            elements = model.get("elements", model) if isinstance(model, dict) else {}
            return elements.get(field, default)
        return model

    def list_models(self) -> List[str]:
        names = set(self.models.keys())
        if self.model_dir.exists():
            for f in self.model_dir.glob("*.json"):
                names.add(f.stem)
        return sorted(names)

    def create_model(self, name: str, model_type: str) -> Dict[str, Any]:
        model = {"name": name, "type": model_type, "elements": {}}
        self.models[name] = model
        self.save(name)
        return model

    def save(self, name: str) -> None:
        model = self.models.get(name)
        if not model:
            return
        self.model_dir.mkdir(parents=True, exist_ok=True)
        path = self.model_dir / f"{name}.json"
        path.write_text(json.dumps(model, indent=2, ensure_ascii=False))

    def delete(self, name: str) -> bool:
        self.models.pop(name, None)
        path = self.model_dir / f"{name}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    def validate_model(self, name: str) -> bool:
        model = self.get(name)
        if not model:
            return False
        if isinstance(model, dict):
            return "name" in model and "type" in model
        return False

    def get_element(self, model_name: str, element_name: str) -> Optional[str]:
        return self.get(model_name, field=element_name)
