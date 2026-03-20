"""模型管理 - 页面对象模型的加载、保存、查询、验证"""
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
