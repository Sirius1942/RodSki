"""ModelManager 单元测试"""
import json
import pytest
from data.model_manager import ModelManager


@pytest.fixture
def mm(tmp_path):
    return ModelManager(model_dir=str(tmp_path / "models"))


class TestModelManager:
    def test_register_and_get(self, mm):
        mm.register("login", {"name": "login", "type": "page", "elements": {"btn": "#btn"}})
        model = mm.get("login")
        assert model["name"] == "login"
        assert model["type"] == "page"

    def test_get_nonexistent(self, mm):
        assert mm.get("nonexistent") is None

    def test_get_with_default(self, mm):
        assert mm.get("nonexistent", default="fallback") == "fallback"

    def test_get_field(self, mm):
        mm.register("page", {"name": "page", "type": "web", "elements": {"btn": "#submit"}})
        assert mm.get("page", field="btn") == "#submit"
        assert mm.get("page", field="nonexistent") is None

    def test_list_models_empty(self, mm):
        assert mm.list_models() == []

    def test_list_models_memory(self, mm):
        mm.register("a", {"name": "a", "type": "t"})
        mm.register("b", {"name": "b", "type": "t"})
        assert mm.list_models() == ["a", "b"]

    def test_create_model(self, mm):
        model = mm.create_model("test", "page")
        assert model["name"] == "test"
        assert model["type"] == "page"
        assert model["elements"] == {}

    def test_create_model_persists(self, mm):
        mm.create_model("test", "page")
        path = mm.model_dir / "test.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["name"] == "test"

    def test_save_and_load(self, mm):
        mm.register("login", {"name": "login", "type": "page", "elements": {"btn": "#btn"}})
        mm.save("login")

        mm2 = ModelManager(model_dir=str(mm.model_dir))
        model = mm2.get("login")
        assert model["name"] == "login"

    def test_delete(self, mm):
        mm.create_model("test", "page")
        assert mm.delete("test") is True
        assert mm.get("test") is None
        assert not (mm.model_dir / "test.json").exists()

    def test_delete_nonexistent(self, mm):
        assert mm.delete("nonexistent") is False

    def test_validate_model_valid(self, mm):
        mm.register("p", {"name": "p", "type": "web"})
        assert mm.validate_model("p") is True

    def test_validate_model_invalid(self, mm):
        mm.register("bad", {"foo": "bar"})
        assert mm.validate_model("bad") is False

    def test_validate_model_nonexistent(self, mm):
        assert mm.validate_model("nope") is False

    def test_get_element(self, mm):
        mm.register("p", {"name": "p", "type": "web", "elements": {"btn": "#ok"}})
        assert mm.get_element("p", "btn") == "#ok"
        assert mm.get_element("p", "nope") is None

    def test_list_models_from_disk(self, mm):
        mm.create_model("disk_model", "page")
        mm2 = ModelManager(model_dir=str(mm.model_dir))
        assert "disk_model" in mm2.list_models()

    def test_save_nonexistent(self, mm):
        mm.save("nonexistent")  # should not raise
