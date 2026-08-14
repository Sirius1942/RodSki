"""漫游 MVP 的 Schema、解析、错误码和 JSON 输出契约。"""

from core.exceptions import (
    ERROR_CODE_MAP,
    RoamCaseNotFoundError,
    RoamNotEligibleError,
    RoamUnsupportedCaseError,
)
from core.json_formatter import JSONFormatter


def test_roam_error_codes_are_registered():
    assert ERROR_CODE_MAP["SKI801"] is RoamCaseNotFoundError
    assert ERROR_CODE_MAP["SKI802"] is RoamNotEligibleError
    assert ERROR_CODE_MAP["SKI803"] is RoamUnsupportedCaseError


def test_roam_not_eligible_error_lists_failed_switches():
    error = RoamNotEligibleError(
        case_id="c001",
        reasons=["Roam.Enabled != 是", "case.roam != 是"],
    )
    payload = error.to_dict()
    assert payload["error_code"] == "SKI802"
    assert payload["details"]["case_id"] == "c001"
    assert payload["details"]["reasons"] == [
        "Roam.Enabled != 是",
        "case.roam != 是",
    ]


def test_json_formatter_passes_through_roam_summary():
    summary = {
        "base_case_id": "c001",
        "triggered_by": "batch_just_passed",
        "variants_tried": 1,
        "duration_seconds": 0.1,
        "stopped_reason": "no_candidates",
        "findings": [],
    }
    output = JSONFormatter.format_success(
        [{
            "case_id": "c001",
            "title": "漫游用例",
            "status": "PASS",
            "execution_time": 0.2,
            "roam_summary": summary,
        }],
        duration=0.2,
    )
    assert output["steps"][0]["roam_summary"] == summary


def test_json_formatter_omits_roam_summary_for_normal_run():
    output = JSONFormatter.format_success(
        [{"case_id": "c001", "status": "PASS", "execution_time": 0.1}],
        duration=0.1,
    )
    assert "roam_summary" not in output["steps"][0]
