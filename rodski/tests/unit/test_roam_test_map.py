"""Unit tests for the versioned, locked roaming Test Map store."""

import json
from unittest.mock import patch

import pytest

from core.roam import (
    SUPPORTED_TEST_MAP_SCHEMA_VERSION,
    InterProcessFileLock,
    TestMapStore as MapStore,
)


def _node(node_id, **overrides):
    value = {
        "id": node_id,
        "label": node_id,
        "business_tags": [],
        "covered_by_cases": [],
        "roam_visit_count": 1,
        "coverage": "roam_only",
        "findings": [],
        "last_visited": "2026-08-10T00:00:00Z",
    }
    value.update(overrides)
    return value


def _edge(source="a", target="b", data="D001", **overrides):
    value = {
        "from": source,
        "to": target,
        "action": {"action": "type", "model": "Form", "data": data},
        "discovered_by": "roam:c001",
        "confidence": 1.0,
    }
    value.update(overrides)
    return value


class TestMapLoading:
    def test_missing_map_returns_v1_without_creating_knowledge_directory(self, tmp_path):
        store = MapStore(tmp_path / "module")
        data = store.load()
        assert data["schema_version"] == SUPPORTED_TEST_MAP_SCHEMA_VERSION == 1
        assert data["nodes"] == []
        assert data["edges"] == []
        assert not store.knowledge_dir.exists()

    def test_load_allows_newer_schema_for_read_only_consumers(self, tmp_path):
        store = MapStore(tmp_path / "module")
        store.knowledge_dir.mkdir(parents=True)
        expected = {
            "schema_version": 2,
            "module": "future",
            "updated_at": "future",
            "nodes": [{"id": "future"}],
            "edges": [],
            "future_field": True,
        }
        store.path.write_text(json.dumps(expected), encoding="utf-8")
        assert store.load() == expected

    def test_non_object_root_is_rejected(self, tmp_path):
        store = MapStore(tmp_path / "module")
        store.knowledge_dir.mkdir(parents=True)
        store.path.write_text("[]", encoding="utf-8")
        with pytest.raises(ValueError, match="root"):
            store.load()


class TestMapMerging:
    def test_first_merge_creates_optional_knowledge_directory_and_lock(self, tmp_path):
        store = MapStore(tmp_path / "module")

        result = store.merge(
            {"nodes": [_node("n1")], "edges": [_edge("n1", "n2")]}
        )

        assert result.written is True
        assert result.nodes_added == 1
        assert result.edges_added == 1
        assert store.path.exists()
        assert store.lock_path.exists()
        saved = store.load()
        assert saved["schema_version"] == 1
        assert saved["nodes"][0]["id"] == "n1"

    def test_lock_scoped_read_modify_write_preserves_existing_entries(self, tmp_path):
        store = MapStore(tmp_path / "module")
        store.merge({"nodes": [_node("n1")], "edges": [_edge("n1", "n2")]})

        result = store.merge(
            {"nodes": [_node("n2")], "edges": [_edge("n2", "n3", "D002")]}
        )

        assert result.nodes_added == 1
        assert result.edges_added == 1
        saved = store.load()
        assert [item["id"] for item in saved["nodes"]] == ["n1", "n2"]
        assert [(item["from"], item["to"]) for item in saved["edges"]] == [
            ("n1", "n2"),
            ("n2", "n3"),
        ]

    def test_node_merge_unions_list_fields_and_uses_updated_values(self, tmp_path):
        store = MapStore(tmp_path / "module")
        store.merge(
            {
                "nodes": [
                    _node(
                        "n1",
                        business_tags=["order"],
                        covered_by_cases=["c001"],
                        findings=["f1"],
                    )
                ]
            }
        )

        result = store.merge(
            {
                "nodes": [
                    _node(
                        "n1",
                        label="new label",
                        business_tags=["order", "stock"],
                        covered_by_cases=["c002"],
                        findings=["f2"],
                        roam_visit_count=4,
                    )
                ]
            }
        )

        assert result.nodes_added == 0
        saved = store.load()["nodes"][0]
        assert saved["label"] == "new label"
        assert saved["business_tags"] == ["order", "stock"]
        assert saved["covered_by_cases"] == ["c001", "c002"]
        assert saved["findings"] == ["f1", "f2"]
        assert saved["roam_visit_count"] == 4

    def test_edge_identity_is_from_to_and_canonical_action(self, tmp_path):
        store = MapStore(tmp_path / "module")
        first = _edge()
        store.merge({"edges": [first]})
        equivalent = _edge(
            action={"data": "D001", "model": "Form", "action": "type"},
            confidence=0.8,
        )

        result = store.merge({"edges": [equivalent]})

        assert result.edges_added == 0
        edges = store.load()["edges"]
        assert len(edges) == 1
        assert edges[0]["confidence"] == 0.8

    def test_newer_schema_is_never_overwritten(self, tmp_path):
        store = MapStore(tmp_path / "module")
        store.knowledge_dir.mkdir(parents=True)
        future = {
            "schema_version": 2,
            "module": "future",
            "updated_at": "future",
            "nodes": [],
            "edges": [],
            "future_field": {"keep": True},
        }
        original = json.dumps(future, ensure_ascii=False, sort_keys=True)
        store.path.write_text(original, encoding="utf-8")

        result = store.merge({"nodes": [_node("must_not_write")]})

        assert result.written is False
        assert result.reason == "newer_schema"
        assert json.dumps(store.load(), ensure_ascii=False, sort_keys=True) == original

    def test_invalid_existing_map_is_not_destroyed(self, tmp_path):
        store = MapStore(tmp_path / "module")
        store.knowledge_dir.mkdir(parents=True)
        store.path.write_text("{broken", encoding="utf-8")

        result = store.merge({"nodes": [_node("n1")]})

        assert result.written is False
        assert result.reason == "invalid_map"
        assert store.path.read_text(encoding="utf-8") == "{broken"

    @pytest.mark.parametrize(
        "delta,match",
        [
            ({"nodes": {}}, "lists"),
            ({"nodes": [{}]}, "non-empty id"),
            ({"edges": [{"from": "a", "to": "b"}]}, "from/to/action"),
        ],
    )
    def test_delta_application_validation(self, tmp_path, delta, match):
        with pytest.raises(ValueError, match=match):
            MapStore(tmp_path / "module").merge(delta)

    def test_lock_timeout_skips_write_without_raising(self, tmp_path):
        store = MapStore(tmp_path / "module", lock_timeout=5.0)
        with patch("core.roam.test_map.InterProcessFileLock.acquire", return_value=False):
            result = store.merge({"nodes": [_node("n1")]})
        assert result.written is False
        assert result.reason == "lock_timeout"
        assert not store.path.exists()


class TestInterProcessFileLock:
    def test_second_lock_times_out_until_first_is_released(self, tmp_path):
        lock_path = tmp_path / "test_map.json.lock"
        first = InterProcessFileLock(lock_path, timeout=0.1, poll_interval=0.005)
        second = InterProcessFileLock(lock_path, timeout=0.02, poll_interval=0.005)
        assert first.acquire() is True
        try:
            assert second.acquire() is False
        finally:
            first.release()

        third = InterProcessFileLock(lock_path, timeout=0.1, poll_interval=0.005)
        assert third.acquire() is True
        third.release()
