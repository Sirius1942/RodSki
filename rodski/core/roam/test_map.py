"""Versioned Test Map persistence with cross-process write serialization."""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Tuple


logger = logging.getLogger("rodski")

SUPPORTED_TEST_MAP_SCHEMA_VERSION = 1


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class InterProcessFileLock:
    """A small stdlib-only advisory lock for Unix and Windows."""

    def __init__(
        self,
        path: Path,
        timeout: float = 5.0,
        poll_interval: float = 0.05,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.path = Path(path)
        self.timeout = max(0.0, float(timeout))
        self.poll_interval = max(0.001, float(poll_interval))
        self._clock = clock
        self._handle = None

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+b")
        if os.name == "nt":
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()

        deadline = self._clock() + self.timeout
        while True:
            try:
                self._try_lock(handle)
                self._handle = handle
                return True
            except (BlockingIOError, OSError):
                if self._clock() >= deadline:
                    handle.close()
                    return False
                time.sleep(min(self.poll_interval, max(0.0, deadline - self._clock())))

    def release(self) -> None:
        handle = self._handle
        if handle is None:
            return
        try:
            self._unlock(handle)
        finally:
            handle.close()
            self._handle = None

    @staticmethod
    def _try_lock(handle: Any) -> None:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            return

        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    @staticmethod
    def _unlock(handle: Any) -> None:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            return

        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def __enter__(self) -> "InterProcessFileLock":
        if not self.acquire():
            raise TimeoutError(f"Timed out acquiring test map lock: {self.path}")
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.release()


@dataclass(frozen=True)
class TestMapMergeResult:
    written: bool
    nodes_added: int = 0
    edges_added: int = 0
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "written": self.written,
            "nodes_added": self.nodes_added,
            "edges_added": self.edges_added,
            "reason": self.reason,
        }


class TestMapStore:
    """Load and incrementally merge ``knowledge/test_map.json``.

    Reads never block on the lock because writes use atomic replacement. Writes
    acquire the lock, re-read the latest file, merge the delta, and then replace
    the file. A map from a newer implementation is returned by :meth:`load` but
    never modified.
    """

    def __init__(
        self,
        module_dir: Any,
        lock_timeout: float = 5.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.module_dir = Path(module_dir)
        self.knowledge_dir = self.module_dir / "knowledge"
        self.path = self.knowledge_dir / "test_map.json"
        self.lock_path = self.knowledge_dir / "test_map.json.lock"
        self.lock_timeout = float(lock_timeout)
        self._clock = clock

    def empty_map(self) -> Dict[str, Any]:
        return {
            "schema_version": SUPPORTED_TEST_MAP_SCHEMA_VERSION,
            "module": str(self.module_dir),
            "updated_at": _utc_now(),
            "nodes": [],
            "edges": [],
        }

    def load(self) -> Dict[str, Any]:
        """Read the last complete map without acquiring the writer lock."""
        if not self.path.exists():
            return self.empty_map()
        with self.path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError("test_map.json root must be an object")
        return data

    def merge(self, delta: Mapping[str, Any]) -> TestMapMergeResult:
        """Merge nodes/edges into the latest map, or safely skip the write."""
        nodes, edges = self._validate_delta(delta)
        lock = InterProcessFileLock(
            self.lock_path,
            timeout=self.lock_timeout,
            clock=self._clock,
        )
        if not lock.acquire():
            logger.warning(
                "测试地图文件锁等待 %.1f 秒超时，跳过本次写回: %s",
                self.lock_timeout,
                self.path,
            )
            return TestMapMergeResult(False, reason="lock_timeout")

        try:
            try:
                current = self.load()
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                logger.warning("测试地图读取失败，跳过写回以避免覆盖: %s", exc)
                return TestMapMergeResult(False, reason="invalid_map")

            version = current.get("schema_version")
            if not isinstance(version, int):
                logger.warning("测试地图缺少有效 schema_version，跳过写回: %s", self.path)
                return TestMapMergeResult(False, reason="invalid_schema_version")
            if version > SUPPORTED_TEST_MAP_SCHEMA_VERSION:
                logger.warning(
                    "测试地图 schema_version=%s 高于当前支持版本 %s，仅只读不写回",
                    version,
                    SUPPORTED_TEST_MAP_SCHEMA_VERSION,
                )
                return TestMapMergeResult(False, reason="newer_schema")
            if version != SUPPORTED_TEST_MAP_SCHEMA_VERSION or not self._is_valid_map(current):
                logger.warning("测试地图 v1 结构无效，跳过写回: %s", self.path)
                return TestMapMergeResult(False, reason="invalid_map")

            merged_nodes, nodes_added = self._merge_nodes(current["nodes"], nodes)
            merged_edges, edges_added = self._merge_edges(current["edges"], edges)
            current["nodes"] = merged_nodes
            current["edges"] = merged_edges
            current["updated_at"] = _utc_now()
            self._atomic_write(current)
            return TestMapMergeResult(True, nodes_added, edges_added)
        finally:
            lock.release()

    # Integration-friendly aliases: callers can use either verb without
    # knowing the persistence implementation details.
    load_or_empty = load
    merge_delta = merge

    @staticmethod
    def _is_valid_map(value: Mapping[str, Any]) -> bool:
        return (
            isinstance(value.get("module"), str)
            and isinstance(value.get("updated_at"), str)
            and isinstance(value.get("nodes"), list)
            and isinstance(value.get("edges"), list)
        )

    @staticmethod
    def _validate_delta(
        delta: Mapping[str, Any]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        if not isinstance(delta, Mapping):
            raise TypeError("test map delta must be a mapping")
        raw_nodes = delta.get("nodes", [])
        raw_edges = delta.get("edges", [])
        if not isinstance(raw_nodes, list) or not isinstance(raw_edges, list):
            raise ValueError("test map delta nodes/edges must be lists")

        nodes: List[Dict[str, Any]] = []
        for node in raw_nodes:
            if not isinstance(node, Mapping) or not str(node.get("id") or "").strip():
                raise ValueError("every test map node must have a non-empty id")
            nodes.append(dict(node))

        edges: List[Dict[str, Any]] = []
        for edge in raw_edges:
            if (
                not isinstance(edge, Mapping)
                or not str(edge.get("from") or "").strip()
                or not str(edge.get("to") or "").strip()
                or not isinstance(edge.get("action"), Mapping)
            ):
                raise ValueError("every test map edge requires from/to/action")
            copied = dict(edge)
            copied["action"] = dict(edge["action"])
            edges.append(copied)
        return nodes, edges

    @staticmethod
    def _merge_nodes(
        current: Iterable[Mapping[str, Any]], incoming: Iterable[Mapping[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], int]:
        current_items = list(current)
        incoming_items = list(incoming)
        order: List[str] = []
        indexed: Dict[str, Dict[str, Any]] = {}
        for raw_node in current_items + incoming_items:
            node = dict(raw_node)
            node_id = str(node.get("id") or "")
            if not node_id:
                continue
            if node_id not in indexed:
                indexed[node_id] = node
                order.append(node_id)
                continue
            indexed[node_id] = TestMapStore._merge_node(indexed[node_id], node)

        current_ids = {
            str(node.get("id"))
            for node in current_items
            if isinstance(node, Mapping) and node.get("id")
        }
        added = sum(1 for node_id in order if node_id not in current_ids)
        return [indexed[node_id] for node_id in order], added

    @staticmethod
    def _merge_node(existing: Mapping[str, Any], update: Mapping[str, Any]) -> Dict[str, Any]:
        merged = dict(existing)
        merged.update(update)
        for field_name in ("covered_by_cases", "business_tags", "findings"):
            values: List[Any] = []
            for source in (existing.get(field_name, []), update.get(field_name, [])):
                if isinstance(source, list):
                    for value in source:
                        if value not in values:
                            values.append(value)
            if values or field_name in existing or field_name in update:
                merged[field_name] = values
        return merged

    @staticmethod
    def _edge_key(edge: Mapping[str, Any]) -> Tuple[str, str, str]:
        action = edge.get("action")
        action_payload = json.dumps(
            action if isinstance(action, Mapping) else {},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return str(edge.get("from") or ""), str(edge.get("to") or ""), action_payload

    @staticmethod
    def _merge_edges(
        current: Iterable[Mapping[str, Any]], incoming: Iterable[Mapping[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], int]:
        current_items = list(current)
        incoming_items = list(incoming)
        order: List[Tuple[str, str, str]] = []
        indexed: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
        for raw_edge in current_items + incoming_items:
            edge = dict(raw_edge)
            key = TestMapStore._edge_key(edge)
            if key not in indexed:
                order.append(key)
                indexed[key] = edge
            else:
                indexed[key].update(edge)

        current_keys = {
            TestMapStore._edge_key(edge)
            for edge in current_items
            if isinstance(edge, Mapping)
        }
        added = sum(1 for key in order if key not in current_keys)
        return [indexed[key] for key in order], added

    def _atomic_write(self, data: Mapping[str, Any]) -> None:
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        descriptor, temp_name = tempfile.mkstemp(
            prefix=".test_map.",
            suffix=".tmp",
            dir=str(self.knowledge_dir),
        )
        temp_path = Path(temp_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(str(temp_path), str(self.path))
        finally:
            if temp_path.exists():
                temp_path.unlink()
