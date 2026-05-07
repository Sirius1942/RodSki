from pathlib import Path

import pytest

from core.plan_parser import PlanParser


VALID_SUITE_PLAN = '''\
<?xml version="1.0" encoding="UTF-8"?>
<test_plan id="suite_plan" title="Suite Plan" kind="suite" default_execute="是">
  <debug prepare="case" step_mode="from" cleanup="是"/>
  <case id="c001" execute="是">
    <scenario id="s1" execute="是">
      <step no="1" execute="是"/>
      <step no="2" execute="否"/>
    </scenario>
    <scenario id="s2" execute="否"/>
  </case>
</test_plan>'''


def _write_plan(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / f"{name}.xml"
    path.write_text(content, encoding="utf-8")
    return path


class TestPlanParser:
    def test_plan_xsd_valid_suite_plan(self, tmp_path):
        plan_path = _write_plan(tmp_path, "suite_plan", VALID_SUITE_PLAN)

        plan = PlanParser(str(plan_path)).parse_plan()

        assert plan["id"] == "suite_plan"
        assert plan["kind"] == "suite"
        assert plan["execute"] == "是"
        assert plan["default_execute"] == "是"

    def test_id_mismatch_raises(self, tmp_path):
        plan_path = _write_plan(tmp_path, "actual_file", '''\
<?xml version="1.0" encoding="UTF-8"?>
<test_plan id="different_id" kind="suite"/>
''')

        with pytest.raises(ValueError, match="文件名 stem"):
            PlanParser(str(plan_path)).parse_plan()

    def test_parse_case_scenario_step_debug(self, tmp_path):
        plan_path = _write_plan(tmp_path, "suite_plan", VALID_SUITE_PLAN)

        plan = PlanParser(str(plan_path)).parse_plan()

        assert plan == {
            "id": "suite_plan",
            "title": "Suite Plan",
            "kind": "suite",
            "execute": "是",
            "default_execute": "是",
            "debug": {"prepare": "case", "step_mode": "from", "cleanup": "是"},
            "cases": [
                {
                    "id": "c001",
                    "execute": "是",
                    "scenarios": [
                        {
                            "id": "s1",
                            "execute": "是",
                            "steps": [
                                {"no": 1, "execute": "是"},
                                {"no": 2, "execute": "否"},
                            ],
                        },
                        {"id": "s2", "execute": "否", "steps": []},
                    ],
                }
            ],
        }

    def test_debug_absent_defaults_to_empty_dict(self, tmp_path):
        plan_path = _write_plan(tmp_path, "minimal", '''\
<?xml version="1.0" encoding="UTF-8"?>
<test_plan id="minimal" kind="suite"/>
''')

        plan = PlanParser(str(plan_path)).parse_plan()

        assert plan["debug"] == {}
        assert plan["default_execute"] == "否"
        assert plan["cases"] == []
