"""Plan XML parser for RodSki test plans."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict

from .xml_schema_validator import RodskiXmlValidator


class PlanParser:
    """Parse and validate a single ``test_plan`` XML file."""

    def __init__(self, plan_path: str):
        self.plan_path = Path(plan_path)

    def parse_plan(self) -> Dict[str, Any]:
        """Parse the plan XML into a normalized dictionary."""
        if not self.plan_path.is_file():
            raise FileNotFoundError(f"Plan XML 文件不存在: {self.plan_path}")

        RodskiXmlValidator.validate_file(self.plan_path, RodskiXmlValidator.KIND_PLAN)
        tree = ET.parse(self.plan_path)
        root = tree.getroot()

        plan_id = (root.get("id") or "").strip()
        if plan_id != self.plan_path.stem:
            raise ValueError(
                f"test_plan id 必须等于文件名 stem: id={plan_id!r}, stem={self.plan_path.stem!r}"
            )

        debug_node = root.find("debug")
        debug: Dict[str, str] = {}
        if debug_node is not None:
            debug = {
                "prepare": (debug_node.get("prepare") or "auto").strip(),
                "step_mode": (debug_node.get("step_mode") or "all").strip(),
                "cleanup": (debug_node.get("cleanup") or "否").strip(),
            }

        load_profile: Dict[str, Any] = {}
        load_profile_node = root.find("load_profile")
        if load_profile_node is not None:
            mode = (load_profile_node.get("mode") or "api").strip()
            load_profile = {"mode": mode}

            def _int_text(tag: str, default: int = 0) -> int:
                node = load_profile_node.find(tag)
                try:
                    return int((node.text or "").strip()) if node is not None else default
                except (ValueError, TypeError):
                    return default

            load_profile["concurrency"] = _int_text("concurrency", 1)
            load_profile["duration_seconds"] = _int_text("duration_seconds", 30)
            load_profile["ramp_up_seconds"] = _int_text("ramp_up_seconds", 0)

            host_node = load_profile_node.find("host")
            if host_node is not None:
                load_profile["host"] = (host_node.text or "").strip()

            think_node = load_profile_node.find("think_time_ms")
            if think_node is not None:
                load_profile["think_time_ms"] = {
                    "min": int(think_node.get("min") or 0),
                    "max": int(think_node.get("max") or 0),
                }

        result: Dict[str, Any] = {
            "id": plan_id,
            "title": (root.get("title") or "").strip(),
            "kind": (root.get("kind") or "").strip(),
            "execute": (root.get("execute") or "是").strip(),
            "default_execute": (root.get("default_execute") or "否").strip(),
            "debug": debug,
            "cases": [self._parse_case(case_node) for case_node in root.findall("case")],
        }
        # load_profile 只在非空时加入，避免影响 kind=suite 的测试期望
        if load_profile:
            result["load_profile"] = load_profile
        return result

    @staticmethod
    def _parse_case(case_node: ET.Element) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "id": (case_node.get("id") or "").strip(),
            "execute": (case_node.get("execute") or "是").strip(),
            "scenarios": [
                PlanParser._parse_scenario(scenario_node)
                for scenario_node in case_node.findall("scenario")
            ],
        }
        # weight 只在 load 计划中使用，仅当 XML 中显式声明时才加入，避免影响 suite 测试期望
        if case_node.get("weight") is not None:
            result["weight"] = int(case_node.get("weight") or 1)
        return result

    @staticmethod
    def _parse_scenario(scenario_node: ET.Element) -> Dict[str, Any]:
        return {
            "id": (scenario_node.get("id") or "").strip(),
            "execute": (scenario_node.get("execute") or "是").strip(),
            "steps": [PlanParser._parse_step(step_node) for step_node in scenario_node.findall("step")],
        }

    @staticmethod
    def _parse_step(step_node: ET.Element) -> Dict[str, Any]:
        return {
            "no": int((step_node.get("no") or "0").strip()),
            "execute": (step_node.get("execute") or "是").strip(),
        }
