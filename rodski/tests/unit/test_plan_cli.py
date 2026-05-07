"""plan CLI 单元测试 — v6.3.0"""
import xml.etree.ElementTree as ET
import pytest
from pathlib import Path
from argparse import Namespace
from unittest.mock import patch

from rodski_cli.plan import (
    handle,
    _plan_dir,
    _plan_path,
    _write_plan_xml,
    _build_plan_root,
)


@pytest.fixture
def project(tmp_path, monkeypatch):
    """Set up a fake project directory with plan/ and case/ dirs."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "plan").mkdir()
    (tmp_path / "case").mkdir()
    return tmp_path


def _make_case_xml(project_path: Path, case_id: str, scenarios: list):
    """Create a minimal case XML with given scenarios."""
    case_dir = project_path / "case"
    case_dir.mkdir(exist_ok=True)
    root = ET.Element("cases")
    case_node = ET.SubElement(root, "case", {"id": case_id, "execute": "是", "title": case_id})
    tc = ET.SubElement(case_node, "test_case")
    for sid in scenarios:
        ET.SubElement(tc, "scenario", {"id": sid, "group": "default"})
    tree = ET.ElementTree(root)
    path = case_dir / f"{case_id}.xml"
    tree.write(str(path), encoding="UTF-8", xml_declaration=True)
    return path


class TestPlanInit:
    def test_init_creates_project_full(self, project):
        args = Namespace(plan_action="init", kind="suite", default_execute="是", force=False)
        rc = handle(args)
        assert rc == 0
        path = project / "plan" / "project_full.xml"
        assert path.is_file()
        tree = ET.parse(path)
        root = tree.getroot()
        assert root.tag == "test_plan"
        assert root.get("id") == "project_full"
        assert root.get("kind") == "suite"
        assert root.get("default_execute") == "是"

    def test_init_no_overwrite_without_force(self, project):
        args = Namespace(plan_action="init", kind="suite", default_execute="是", force=False)
        handle(args)
        path = project / "plan" / "project_full.xml"
        mtime = path.stat().st_mtime
        handle(args)
        assert path.stat().st_mtime == mtime

    def test_init_force_overwrites(self, project):
        args = Namespace(plan_action="init", kind="suite", default_execute="是", force=False)
        handle(args)
        args2 = Namespace(plan_action="init", kind="suite", default_execute="否", force=True)
        handle(args2)
        tree = ET.parse(project / "plan" / "project_full.xml")
        assert tree.getroot().get("default_execute") == "否"


class TestPlanList:
    def test_list_empty(self, project, capsys):
        args = Namespace(plan_action="list")
        rc = handle(args)
        assert rc == 0
        out = capsys.readouterr().out
        assert "无 plan 文件" in out

    def test_list_shows_plans(self, project, capsys):
        # Create two plans
        handle(Namespace(plan_action="init", kind="suite", default_execute="是", force=False))
        handle(Namespace(
            plan_action="create", plan_id="smoke", kind="suite",
            default_execute="否", title="Smoke", from_tag=None, from_group=None, force=False
        ))
        args = Namespace(plan_action="list")
        handle(args)
        out = capsys.readouterr().out
        assert "project_full" in out
        assert "smoke" in out


class TestPlanCreate:
    def test_create_suite_plan(self, project):
        args = Namespace(
            plan_action="create", plan_id="my_plan", kind="suite",
            default_execute="否", title="My Plan", from_tag=None, from_group=None, force=False
        )
        rc = handle(args)
        assert rc == 0
        path = project / "plan" / "my_plan.xml"
        assert path.is_file()
        tree = ET.parse(path)
        root = tree.getroot()
        assert root.get("id") == "my_plan"
        assert root.get("title") == "My Plan"
        assert root.get("kind") == "suite"

    def test_create_from_tag(self, project):
        # Create case with tagged scenarios
        case_dir = project / "case"
        case_xml = '''\
<?xml version="1.0" encoding="UTF-8"?>
<cases tags="smoke,regression">
  <case id="tc001" execute="是" title="Test 1">
    <test_case>
      <scenario id="sc01" group="positive">
        <test_step action="navigate" model="url" data="http://example.com"/>
      </scenario>
    </test_case>
  </case>
</cases>'''
        (case_dir / "tc001.xml").write_text(case_xml, encoding="utf-8")

        args = Namespace(
            plan_action="create", plan_id="smoke_plan", kind="suite",
            default_execute="否", title="", from_tag="smoke", from_group=None, force=False
        )
        rc = handle(args)
        assert rc == 0
        tree = ET.parse(project / "plan" / "smoke_plan.xml")
        root = tree.getroot()
        cases = root.findall("case")
        assert len(cases) == 1
        assert cases[0].get("id") == "tc001"
        scenarios = cases[0].findall("scenario")
        assert len(scenarios) == 1
        assert scenarios[0].get("id") == "sc01"


class TestPlanAddCase:
    def test_add_case(self, project):
        handle(Namespace(plan_action="init", kind="suite", default_execute="是", force=False))
        args = Namespace(plan_action="add-case", plan_id="project_full", case_id="tc001")
        rc = handle(args)
        assert rc == 0
        tree = ET.parse(project / "plan" / "project_full.xml")
        cases = tree.getroot().findall("case")
        assert any(c.get("id") == "tc001" for c in cases)

    def test_add_case_no_duplicate(self, project, capsys):
        handle(Namespace(plan_action="init", kind="suite", default_execute="是", force=False))
        handle(Namespace(plan_action="add-case", plan_id="project_full", case_id="tc001"))
        handle(Namespace(plan_action="add-case", plan_id="project_full", case_id="tc001"))
        tree = ET.parse(project / "plan" / "project_full.xml")
        cases = [c for c in tree.getroot().findall("case") if c.get("id") == "tc001"]
        assert len(cases) == 1


class TestPlanAddScenario:
    def test_add_scenario(self, project):
        handle(Namespace(plan_action="init", kind="suite", default_execute="是", force=False))
        handle(Namespace(plan_action="add-case", plan_id="project_full", case_id="tc001"))
        args = Namespace(plan_action="add-scenario", plan_id="project_full", case_id="tc001", scenario_id="sc01")
        rc = handle(args)
        assert rc == 0
        tree = ET.parse(project / "plan" / "project_full.xml")
        case_node = tree.getroot().find("case[@id='tc001']")
        assert case_node is not None
        scenarios = case_node.findall("scenario")
        assert any(s.get("id") == "sc01" for s in scenarios)

    def test_add_scenario_creates_case_if_missing(self, project):
        handle(Namespace(plan_action="init", kind="suite", default_execute="是", force=False))
        args = Namespace(plan_action="add-scenario", plan_id="project_full", case_id="tc002", scenario_id="sc01")
        rc = handle(args)
        assert rc == 0
        tree = ET.parse(project / "plan" / "project_full.xml")
        case_node = tree.getroot().find("case[@id='tc002']")
        assert case_node is not None

    def test_add_scenario_no_duplicate(self, project):
        handle(Namespace(plan_action="init", kind="suite", default_execute="是", force=False))
        handle(Namespace(plan_action="add-scenario", plan_id="project_full", case_id="tc001", scenario_id="sc01"))
        handle(Namespace(plan_action="add-scenario", plan_id="project_full", case_id="tc001", scenario_id="sc01"))
        tree = ET.parse(project / "plan" / "project_full.xml")
        case_node = tree.getroot().find("case[@id='tc001']")
        scenarios = [s for s in case_node.findall("scenario") if s.get("id") == "sc01"]
        assert len(scenarios) == 1


class TestPlanEnableDisable:
    def test_disable_case(self, project):
        handle(Namespace(plan_action="init", kind="suite", default_execute="是", force=False))
        handle(Namespace(plan_action="add-case", plan_id="project_full", case_id="tc001"))
        rc = handle(Namespace(plan_action="disable-case", plan_id="project_full", case_id="tc001"))
        assert rc == 0
        tree = ET.parse(project / "plan" / "project_full.xml")
        case_node = tree.getroot().find("case[@id='tc001']")
        assert case_node.get("execute") == "否"

    def test_enable_case(self, project):
        handle(Namespace(plan_action="init", kind="suite", default_execute="是", force=False))
        handle(Namespace(plan_action="add-case", plan_id="project_full", case_id="tc001"))
        handle(Namespace(plan_action="disable-case", plan_id="project_full", case_id="tc001"))
        rc = handle(Namespace(plan_action="enable-case", plan_id="project_full", case_id="tc001"))
        assert rc == 0
        tree = ET.parse(project / "plan" / "project_full.xml")
        case_node = tree.getroot().find("case[@id='tc001']")
        assert case_node.get("execute") == "是"

    def test_disable_scenario(self, project):
        handle(Namespace(plan_action="init", kind="suite", default_execute="是", force=False))
        handle(Namespace(plan_action="add-scenario", plan_id="project_full", case_id="tc001", scenario_id="sc01"))
        rc = handle(Namespace(plan_action="disable-scenario", plan_id="project_full", case_id="tc001", scenario_id="sc01"))
        assert rc == 0
        tree = ET.parse(project / "plan" / "project_full.xml")
        case_node = tree.getroot().find("case[@id='tc001']")
        sc_node = case_node.find("scenario[@id='sc01']")
        assert sc_node.get("execute") == "否"

    def test_enable_scenario(self, project):
        handle(Namespace(plan_action="init", kind="suite", default_execute="是", force=False))
        handle(Namespace(plan_action="add-scenario", plan_id="project_full", case_id="tc001", scenario_id="sc01"))
        handle(Namespace(plan_action="disable-scenario", plan_id="project_full", case_id="tc001", scenario_id="sc01"))
        rc = handle(Namespace(plan_action="enable-scenario", plan_id="project_full", case_id="tc001", scenario_id="sc01"))
        assert rc == 0
        tree = ET.parse(project / "plan" / "project_full.xml")
        case_node = tree.getroot().find("case[@id='tc001']")
        sc_node = case_node.find("scenario[@id='sc01']")
        assert sc_node.get("execute") == "是"


class TestPlanValidate:
    def test_validate_passes_valid_plan(self, project, capsys):
        _make_case_xml(project, "tc001", ["sc01", "sc02"])
        handle(Namespace(plan_action="init", kind="suite", default_execute="是", force=False))
        handle(Namespace(plan_action="add-scenario", plan_id="project_full", case_id="tc001", scenario_id="sc01"))
        rc = handle(Namespace(plan_action="validate", plan_id="project_full"))
        assert rc == 0
        out = capsys.readouterr().out
        assert "校验通过" in out

    def test_validate_detects_stale_case(self, project, capsys):
        handle(Namespace(plan_action="init", kind="suite", default_execute="是", force=False))
        handle(Namespace(plan_action="add-case", plan_id="project_full", case_id="nonexistent"))
        rc = handle(Namespace(plan_action="validate", plan_id="project_full"))
        assert rc == 1
        out = capsys.readouterr().out
        assert "nonexistent" in out
        assert "不存在" in out

    def test_validate_detects_stale_scenario(self, project, capsys):
        _make_case_xml(project, "tc001", ["sc01"])
        handle(Namespace(plan_action="init", kind="suite", default_execute="是", force=False))
        handle(Namespace(plan_action="add-scenario", plan_id="project_full", case_id="tc001", scenario_id="sc_bad"))
        rc = handle(Namespace(plan_action="validate", plan_id="project_full"))
        assert rc == 1
        out = capsys.readouterr().out
        assert "sc_bad" in out


class TestPlanDebugScenario:
    def test_debug_scenario_creates_plan(self, project):
        args = Namespace(
            plan_action="debug-scenario", plan_id="dbg_sc",
            case_id="tc001", scenario_id="sc01",
            prepare="case", cleanup="是"
        )
        rc = handle(args)
        assert rc == 0
        path = project / "plan" / "dbg_sc.xml"
        assert path.is_file()
        tree = ET.parse(path)
        root = tree.getroot()
        assert root.get("kind") == "scenario_debug"
        debug = root.find("debug")
        assert debug is not None
        assert debug.get("prepare") == "case"
        assert debug.get("cleanup") == "是"
        case_node = root.find("case")
        assert case_node.get("id") == "tc001"
        sc_node = case_node.find("scenario")
        assert sc_node.get("id") == "sc01"


class TestPlanDebugStep:
    def test_debug_step_creates_plan(self, project):
        args = Namespace(
            plan_action="debug-step", plan_id="dbg_step",
            case_id="tc001", scenario_id="sc01", step_no=3,
            step_mode="from", prepare="none", cleanup="否"
        )
        rc = handle(args)
        assert rc == 0
        path = project / "plan" / "dbg_step.xml"
        assert path.is_file()
        tree = ET.parse(path)
        root = tree.getroot()
        assert root.get("kind") == "step_debug"
        debug = root.find("debug")
        assert debug.get("step_mode") == "from"
        assert debug.get("prepare") == "none"
        case_node = root.find("case")
        sc_node = case_node.find("scenario")
        step_node = sc_node.find("step")
        assert step_node.get("no") == "3"
