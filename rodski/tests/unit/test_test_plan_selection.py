from core.test_plan_selection import TestPlanSelection


def _cases():
    return [
        {
            "case_id": "c001",
            "title": "case 1",
            "scenarios": [
                {
                    "type": "scenario",
                    "id": "s1",
                    "steps": [
                        {"action": "type", "model": "Login", "data": "L001"},
                        {"action": "verify", "model": "Home", "data": "V001"},
                    ],
                },
                {
                    "type": "scenario",
                    "id": "s2",
                    "steps": [{"action": "close", "model": "", "data": ""}],
                },
            ],
        },
        {
            "case_id": "c002",
            "title": "case 2",
            "scenarios": [
                {
                    "type": "scenario",
                    "id": "s3",
                    "steps": [{"action": "wait", "model": "", "data": "1"}],
                }
            ],
        },
    ]


def _plan(default_execute="否", scenarios=None):
    return {
        "id": "p001",
        "title": "",
        "kind": "suite",
        "execute": "是",
        "default_execute": default_execute,
        "debug": {},
        "cases": [
            {
                "id": "c001",
                "execute": "是",
                "scenarios": scenarios if scenarios is not None else [],
            }
        ],
    }


class TestTestPlanSelection:
    def test_default_execute_false_only_explicit_scenario_selected(self):
        plan = _plan(
            default_execute="否",
            scenarios=[{"id": "s1", "execute": "是", "steps": []}],
        )

        result = TestPlanSelection(_cases(), plan).select()

        assert [(entry["case_id"], entry["scenario_id"]) for entry in result["selected"]] == [("c001", "s1")]
        assert result["skipped"] == []
        assert result["stale_references"] == []

    def test_default_execute_true_includes_unmentioned_scenario(self):
        plan = _plan(
            default_execute="是",
            scenarios=[{"id": "s1", "execute": "是", "steps": []}],
        )

        result = TestPlanSelection(_cases(), plan).select()

        selected = {(entry["case_id"], entry["scenario_id"]) for entry in result["selected"]}
        assert selected == {("c001", "s1"), ("c001", "s2"), ("c002", "s3")}

    def test_plan_scenario_execute_false_skipped(self):
        plan = _plan(
            default_execute="否",
            scenarios=[{"id": "s1", "execute": "否", "steps": []}],
        )

        result = TestPlanSelection(_cases(), plan).select()

        assert result["selected"] == []
        assert len(result["skipped"]) == 1
        assert result["skipped"][0]["type"] == "scenario"
        assert result["skipped"][0]["case_id"] == "c001"
        assert result["skipped"][0]["scenario_id"] == "s1"
        assert result["skipped"][0]["reason"] == "plan_scenario_execute_false"

    def test_stale_scenario_reference_recorded(self):
        plan = _plan(
            default_execute="否",
            scenarios=[{"id": "missing", "execute": "是", "steps": []}],
        )

        result = TestPlanSelection(_cases(), plan).select()

        assert result["selected"] == []
        assert result["stale_references"] == [
            {
                "type": "scenario",
                "case_id": "c001",
                "scenario_id": "missing",
                "reason": "not_found",
            }
        ]

    def test_explicit_step_selection_and_step_skip(self):
        plan = _plan(
            default_execute="否",
            scenarios=[
                {
                    "id": "s1",
                    "execute": "是",
                    "steps": [
                        {"no": 1, "execute": "是"},
                        {"no": 2, "execute": "否"},
                    ],
                }
            ],
        )

        result = TestPlanSelection(_cases(), plan).select()

        assert len(result["selected"]) == 1
        assert result["selected"][0]["type"] == "step"
        assert result["selected"][0]["step_no"] == 1
        assert len(result["skipped"]) == 1
        assert result["skipped"][0]["step_no"] == 2
        assert result["skipped"][0]["reason"] == "plan_step_execute_false"
