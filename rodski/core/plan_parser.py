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

        cases = []
        case_dirs = []
        suites = []
        for child in root:
            if child.tag == "case":
                cases.append(self._parse_case(child))
            elif child.tag == "case_dir":
                case_dirs.append(self._parse_case_dir(child))
            elif child.tag == "suite":
                # v11.11.0 测试套（CORE §7.9）：套内条目同时平铺进 cases / case_dirs（带 suite 键），
                # 选择、数据驱动等既有逻辑照常读取平铺列表
                suite = self._parse_suite(child)
                suites.append(suite)
                cases.extend(suite["cases"])
                case_dirs.extend(suite["case_dirs"])

        result: Dict[str, Any] = {
            "id": plan_id,
            "title": (root.get("title") or "").strip(),
            "kind": (root.get("kind") or "").strip(),
            "execute": (root.get("execute") or "是").strip(),
            "default_execute": (root.get("default_execute") or "否").strip(),
            "debug": debug,
            "cases": cases,
            "case_dirs": case_dirs,
        }
        # load_profile 只在非空时加入，避免影响 kind=suite 的测试期望
        if load_profile:
            result["load_profile"] = load_profile
        # suites / max_parallel 只在显式声明时加入，未写 <suite> 的计划保持 v11.10 的字典结构
        if suites:
            result["suites"] = suites
        if root.get("max_parallel") is not None:
            result["max_parallel"] = int(root.get("max_parallel").strip())
        return result

    @staticmethod
    def _parse_suite(suite_node: ET.Element) -> Dict[str, Any]:
        """解析 suite 元素（v11.11.0）。"""
        suite_id = (suite_node.get("id") or "").strip()
        cases = []
        case_dirs = []
        for child in suite_node:
            if child.tag == "case":
                entry = PlanParser._parse_case(child)
                entry["suite"] = suite_id
                cases.append(entry)
            elif child.tag == "case_dir":
                entry = PlanParser._parse_case_dir(child)
                entry["suite"] = suite_id
                case_dirs.append(entry)
        tags = [t.strip() for t in (suite_node.get("tags") or "").split(",") if t.strip()]
        return {
            "id": suite_id,
            "title": (suite_node.get("title") or "").strip(),
            "execute": (suite_node.get("execute") or "是").strip(),
            "tags": tags,
            "cases": cases,
            "case_dirs": case_dirs,
        }

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
        # file 属性：v11.5.0 新增，用于多级嵌套目录下定位用例
        file_attr = case_node.get("file")
        if file_attr is not None:
            result["file"] = file_attr.strip()
        # data_driven：v11.9.0 计划级数据驱动表名（CORE §7.8），只在显式声明时加入
        data_driven = (case_node.get("data_driven") or "").strip()
        if data_driven:
            result["data_driven"] = data_driven
        # weight 只在 load 计划中使用，仅当 XML 中显式声明时才加入，避免影响 suite 测试期望
        if case_node.get("weight") is not None:
            result["weight"] = int(case_node.get("weight") or 1)
        return result

    @staticmethod
    def _parse_case_dir(case_dir_node: ET.Element) -> Dict[str, Any]:
        """解析 case_dir 元素（v11.5.0 新增）。"""
        return {
            "path": (case_dir_node.get("path") or "").strip(),
            "execute": (case_dir_node.get("execute") or "是").strip(),
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
