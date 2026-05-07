"""Plan XML parser for RodSki test plans."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List

from .xml_schema_validator import RodskiXmlValidator, schemas_directory

try:
    import xmlschema
    from xmlschema.validators.exceptions import XMLSchemaValidationError as _XsdValidationError
except ImportError:  # pragma: no cover
    xmlschema = None  # type: ignore
    _XsdValidationError = Exception  # type: ignore


class PlanParser:
    """Parse and validate a single ``test_plan`` XML file."""

    KIND_PLAN = "plan"

    def __init__(self, plan_path: str):
        self.plan_path = Path(plan_path)

    def parse_plan(self) -> Dict[str, Any]:
        """Parse the plan XML into a normalized dictionary."""
        if not self.plan_path.is_file():
            raise FileNotFoundError(f"Plan XML 文件不存在: {self.plan_path}")

        self._validate_file(self.plan_path)
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

        return {
            "id": plan_id,
            "title": (root.get("title") or "").strip(),
            "kind": (root.get("kind") or "").strip(),
            "execute": (root.get("execute") or "是").strip(),
            "default_execute": (root.get("default_execute") or "否").strip(),
            "debug": debug,
            "cases": [self._parse_case(case_node) for case_node in root.findall("case")],
        }

    @classmethod
    def _validate_file(cls, xml_path: Path) -> None:
        """Validate with RodskiXmlValidator when it supports plans, otherwise local XSD."""
        plan_kind = getattr(RodskiXmlValidator, "KIND_PLAN", cls.KIND_PLAN)
        try:
            RodskiXmlValidator.validate_file(xml_path, plan_kind)
            return
        except ValueError:
            cls._validate_file_locally(xml_path)

    @staticmethod
    def _validate_file_locally(xml_path: Path) -> None:
        if xmlschema is None:  # pragma: no cover
            raise ImportError("缺少依赖 xmlschema，无法进行 plan.xsd 校验。请执行: pip install xmlschema")
        xsd_path = schemas_directory() / "plan.xsd"
        schema = xmlschema.XMLSchema(str(xsd_path))
        try:
            schema.validate(str(xml_path))
        except _XsdValidationError as exc:
            raise ValueError(f"Plan XML 不符合 Schema 约束 ({xsd_path}): {xml_path}\n{exc}") from exc

    @staticmethod
    def _parse_case(case_node: ET.Element) -> Dict[str, Any]:
        return {
            "id": (case_node.get("id") or "").strip(),
            "execute": (case_node.get("execute") or "是").strip(),
            "scenarios": [
                PlanParser._parse_scenario(scenario_node)
                for scenario_node in case_node.findall("scenario")
            ],
        }

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
