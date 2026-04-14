"""Design Agent 图和节点单元测试。

测试 design/nodes.py 中的节点函数和 design/graph.py 中的图构建。
所有 LLM 调用均 Mock，确保测试无外部依赖。
"""
from __future__ import annotations

import json
import os
from unittest.mock import patch, MagicMock

import pytest

from rodski_agent.design.nodes import (
    analyze_req,
    plan_cases,
    design_data,
    generate_xml,
    validate_xml,
    _fallback_scenarios,
    _fallback_case_plan,
    _fallback_test_data,
    _validate_case_plan_actions,
    _parse_json_response,
)
from rodski_agent.design.graph import build_design_graph, _validate_router


# ============================================================
# Node: analyze_req
# ============================================================


class TestAnalyzeReq:
    """测试 analyze_req 节点"""

    def test_empty_requirement_returns_error(self):
        """No requirement should return error status."""
        result = analyze_req({"requirement": ""})
        assert result["status"] == "error"
        assert result["test_scenarios"] == []

    def test_fallback_ui_scenario(self):
        """Fallback generates UI scenario for general requirement."""
        result = analyze_req({"requirement": "测试登录功能"})
        assert result["status"] == "running"
        scenarios = result["test_scenarios"]
        assert len(scenarios) >= 1
        assert scenarios[0]["type"] == "ui"

    def test_fallback_api_scenario(self):
        """Fallback detects API type from keywords."""
        result = analyze_req({"requirement": "测试登录接口 API"})
        scenarios = result["test_scenarios"]
        assert scenarios[0]["type"] == "api"

    def test_fallback_db_scenario(self):
        """Fallback detects DB type from keywords."""
        result = analyze_req({"requirement": "测试数据库查询"})
        scenarios = result["test_scenarios"]
        assert scenarios[0]["type"] == "db"

    def test_with_mock_llm(self):
        """With mock LLM unavailable, should fall back to stub."""
        with patch("rodski_agent.common.llm_bridge.call_llm_text", side_effect=Exception("no llm")):
            # LLM exception triggers fallback
            result = analyze_req({"requirement": "test login"})
            assert result["status"] == "running"
            assert len(result["test_scenarios"]) >= 1


class TestFallbackScenarios:
    """测试 _fallback_scenarios"""

    def test_basic_scenario(self):
        """Basic scenario generation."""
        scenarios = _fallback_scenarios("test search feature")
        assert len(scenarios) == 1
        assert scenarios[0]["scenario_name"] == "test_scenario_001"
        assert scenarios[0]["type"] == "ui"

    def test_api_detection(self):
        """API keywords detected."""
        scenarios = _fallback_scenarios("test HTTP request")
        assert scenarios[0]["type"] == "api"


# ============================================================
# Node: plan_cases
# ============================================================


class TestPlanCases:
    """测试 plan_cases 节点"""

    def test_empty_scenarios_returns_error(self):
        """No scenarios should return error."""
        result = plan_cases({"test_scenarios": []})
        assert result["status"] == "error"

    def test_fallback_ui_plan(self):
        """Fallback generates UI case plan."""
        scenarios = [
            {
                "scenario_name": "login_success",
                "description": "Login test",
                "type": "ui",
                "steps_outline": ["open", "fill", "verify"],
            }
        ]
        result = plan_cases({"test_scenarios": scenarios})
        assert result["status"] == "running"
        case_plan = result["case_plan"]
        assert len(case_plan) >= 1
        # Check all actions are valid
        for case in case_plan:
            for step in case["steps"]:
                from rodski_agent.common.rodski_knowledge import validate_action
                assert validate_action(step["action"]), f"Invalid action: {step['action']}"

    def test_fallback_api_plan(self):
        """Fallback generates API case plan."""
        scenarios = [
            {
                "scenario_name": "api_test",
                "description": "API test",
                "type": "api",
                "steps_outline": ["send request", "verify response"],
            }
        ]
        result = plan_cases({"test_scenarios": scenarios})
        case_plan = result["case_plan"]
        actions = [s["action"] for s in case_plan[0]["steps"]]
        assert "send" in actions

    def test_fallback_db_plan(self):
        """Fallback generates DB case plan."""
        scenarios = [
            {
                "scenario_name": "db_test",
                "description": "DB test",
                "type": "db",
                "steps_outline": ["execute query"],
            }
        ]
        result = plan_cases({"test_scenarios": scenarios})
        case_plan = result["case_plan"]
        actions = [s["action"] for s in case_plan[0]["steps"]]
        assert "DB" in actions


class TestValidateCasePlanActions:
    """测试 _validate_case_plan_actions"""

    def test_removes_invalid_actions(self):
        """Invalid actions should be removed from plan."""
        plan = [
            {
                "id": "c001",
                "title": "Test",
                "steps": [
                    {"action": "type", "model": "M", "data": "D"},
                    {"action": "click", "model": "", "data": ""},  # invalid
                    {"action": "verify", "model": "M", "data": "V"},
                ],
            }
        ]
        result = _validate_case_plan_actions(plan)
        assert len(result) == 1
        actions = [s["action"] for s in result[0]["steps"]]
        assert "click" not in actions
        assert "type" in actions
        assert "verify" in actions

    def test_case_removed_if_all_invalid(self):
        """Case with all invalid actions should be removed."""
        plan = [
            {
                "id": "c001",
                "title": "Test",
                "steps": [
                    {"action": "click", "model": "", "data": ""},
                    {"action": "hover", "model": "", "data": ""},
                ],
            }
        ]
        result = _validate_case_plan_actions(plan)
        assert len(result) == 0


# ============================================================
# Node: design_data
# ============================================================


class TestDesignData:
    """测试 design_data 节点"""

    def test_empty_case_plan_returns_error(self):
        """No case plan should return error."""
        result = design_data({"case_plan": []})
        assert result["status"] == "error"

    def test_fallback_data_generation(self):
        """Fallback generates minimal test data."""
        case_plan = [
            {
                "id": "c001",
                "title": "Test",
                "steps": [
                    {"action": "type", "model": "Login", "data": "L001"},
                    {"action": "verify", "model": "Login", "data": "V001"},
                ],
            }
        ]
        result = design_data({"case_plan": case_plan})
        assert result["status"] == "running"
        test_data = result["test_data"]
        assert "datatables" in test_data
        assert "verify_tables" in test_data


class TestFallbackTestData:
    """测试 _fallback_test_data"""

    def test_generates_data_and_verify(self):
        """Should generate both data and verify tables."""
        case_plan = [
            {
                "id": "c001",
                "steps": [
                    {"action": "type", "model": "Login", "data": "L001"},
                    {"action": "verify", "model": "Login", "data": "V001"},
                ],
            }
        ]
        data = _fallback_test_data(case_plan)
        assert len(data["datatables"]) >= 1
        assert data["datatables"][0]["name"] == "Login"
        # verify table for Login (verify step uses Login model)
        # Note: Login model is already seen by type step,
        # so verify step's model won't be added to datatables again,
        # but it will be added to verify_tables
        assert len(data["verify_tables"]) >= 1
        assert data["verify_tables"][0]["name"] == "Login_verify"


# ============================================================
# Node: generate_xml
# ============================================================


class TestGenerateXml:
    """测试 generate_xml 节点"""

    def test_no_output_dir_returns_error(self):
        """Missing output_dir should return error."""
        result = generate_xml({"output_dir": ""})
        assert result["status"] == "error"

    def test_creates_directory_structure(self, tmp_path):
        """Should create case/model/data directories."""
        output_dir = str(tmp_path / "output")
        case_plan = [
            {
                "id": "c001",
                "title": "Test",
                "steps": [
                    {"phase": "test_case", "action": "type", "model": "Login", "data": "L001"},
                ],
            }
        ]
        test_data = {
            "datatables": [
                {
                    "name": "Login",
                    "rows": [
                        {
                            "id": "L001",
                            "fields": [{"name": "field1", "value": "value1"}],
                        }
                    ],
                }
            ],
            "verify_tables": [],
        }
        result = generate_xml({
            "output_dir": output_dir,
            "case_plan": case_plan,
            "test_data": test_data,
        })
        assert result["status"] == "running"
        assert os.path.isdir(os.path.join(output_dir, "case"))
        assert os.path.isdir(os.path.join(output_dir, "model"))
        assert os.path.isdir(os.path.join(output_dir, "data"))
        assert len(result["generated_files"]) >= 1

    def test_generates_all_files(self, tmp_path):
        """Should generate case, model, and data files."""
        output_dir = str(tmp_path / "output")
        case_plan = [
            {
                "id": "c001",
                "title": "Test",
                "steps": [
                    {"phase": "test_case", "action": "type", "model": "Login", "data": "L001"},
                    {"phase": "test_case", "action": "verify", "model": "Login", "data": "V001"},
                ],
            }
        ]
        test_data = {
            "datatables": [
                {
                    "name": "Login",
                    "rows": [
                        {"id": "L001", "fields": [{"name": "username", "value": "admin"}]},
                    ],
                }
            ],
            "verify_tables": [
                {
                    "name": "Login_verify",
                    "rows": [
                        {"id": "V001", "fields": [{"name": "username", "value": "admin"}]},
                    ],
                }
            ],
        }
        result = generate_xml({
            "output_dir": output_dir,
            "case_plan": case_plan,
            "test_data": test_data,
        })
        files = result["generated_files"]
        # Should have case, model, data, and verify files
        assert any("case" in f for f in files)
        assert any("model" in f for f in files)
        assert any("data.xml" in f for f in files)
        assert any("data_verify.xml" in f for f in files)

    def test_xml_content_valid(self, tmp_path):
        """Generated XML files should contain valid XML."""
        output_dir = str(tmp_path / "output")
        case_plan = [
            {
                "id": "c001",
                "title": "Test",
                "steps": [
                    {"phase": "test_case", "action": "type", "model": "Login", "data": "L001"},
                ],
            }
        ]
        test_data = {
            "datatables": [
                {
                    "name": "Login",
                    "rows": [{"id": "L001", "fields": [{"name": "f1", "value": "v1"}]}],
                }
            ],
            "verify_tables": [],
        }
        generate_xml({
            "output_dir": output_dir,
            "case_plan": case_plan,
            "test_data": test_data,
        })
        # Check case file
        case_file = os.path.join(output_dir, "case", "test_case.xml")
        assert os.path.isfile(case_file)
        with open(case_file, encoding="utf-8") as f:
            content = f.read()
        assert '<?xml version="1.0" encoding="UTF-8"?>' in content
        assert "<cases>" in content


# ============================================================
# Node: validate_xml
# ============================================================


class TestValidateXml:
    """测试 validate_xml 节点"""

    def test_no_output_dir_returns_error(self):
        """Missing output_dir should return error."""
        result = validate_xml({"output_dir": ""})
        assert result["status"] == "error"

    def test_no_files_returns_error(self):
        """No generated files should return error."""
        result = validate_xml({"output_dir": "/tmp", "generated_files": []})
        assert result["status"] == "error"

    def test_graceful_degradation(self, tmp_path):
        """When rodski validator is not available, should succeed gracefully."""
        # Mock rodski_validate at the source module to raise ImportError
        with patch(
            "rodski_agent.common.rodski_tools.rodski_validate",
            side_effect=ImportError("no rodski"),
        ):
            result = validate_xml({
                "output_dir": str(tmp_path),
                "generated_files": [str(tmp_path / "test.xml")],
            })
        # Should gracefully degrade to success
        assert result["status"] == "success"


# ============================================================
# Graph: build_design_graph
# ============================================================


class TestDesignGraph:
    """测试 design graph 端到端"""

    def test_validate_router_success(self):
        """Router returns 'end' on success."""
        assert _validate_router({"status": "success"}) == "end"

    def test_validate_router_retry(self):
        """Router returns 'generate_xml' when fix_attempt < 3."""
        assert _validate_router({"status": "running", "fix_attempt": 1}) == "generate_xml"

    def test_validate_router_give_up(self):
        """Router returns 'end' when fix_attempt >= 3."""
        assert _validate_router({"status": "running", "fix_attempt": 3}) == "end"

    def test_end_to_end_with_mocks(self, tmp_path):
        """Full design graph with mock nodes."""
        output_dir = str(tmp_path / "output")

        def mock_analyze_req(s):
            return {
                "test_scenarios": [
                    {"scenario_name": "test_1", "description": "Test", "type": "ui", "steps_outline": ["a", "b"]}
                ],
                "status": "running",
            }

        def mock_plan_cases(s):
            return {
                "case_plan": [
                    {
                        "id": "c001",
                        "title": "Test",
                        "steps": [
                            {"phase": "test_case", "action": "type", "model": "Login", "data": "D001"},
                        ],
                    }
                ],
                "status": "running",
            }

        def mock_design_data(s):
            return {
                "test_data": {
                    "datatables": [
                        {"name": "Login", "rows": [{"id": "D001", "fields": [{"name": "f1", "value": "v1"}]}]},
                    ],
                    "verify_tables": [],
                },
                "status": "running",
            }

        def mock_generate_xml(s):
            # Create dirs and files
            od = s.get("output_dir", output_dir)
            os.makedirs(os.path.join(od, "case"), exist_ok=True)
            return {"generated_files": [os.path.join(od, "case", "test.xml")], "status": "running"}

        def mock_validate_xml(s):
            return {"validation_errors": [], "status": "success"}

        graph = build_design_graph(
            mock_analyze_req,
            mock_plan_cases,
            mock_design_data,
            mock_generate_xml,
            mock_validate_xml,
        )

        result = graph.invoke({
            "requirement": "test login",
            "output_dir": output_dir,
        })
        assert result["status"] == "success"

    def test_end_to_end_with_real_nodes(self, tmp_path):
        """Full graph with real nodes (LLM unavailable, uses fallback)."""
        output_dir = str(tmp_path / "output")
        result = build_design_graph().invoke({
            "requirement": "测试登录功能",
            "output_dir": output_dir,
        })
        # Should complete (with fallback) and create files
        generated = result.get("generated_files", [])
        assert len(generated) >= 1
        assert os.path.isdir(os.path.join(output_dir, "case"))

    def test_retry_on_validation_failure(self):
        """Graph should retry generate_xml when validation fails."""
        call_log = []

        def mock_analyze(s):
            call_log.append("analyze")
            return {"test_scenarios": [{"scenario_name": "t", "type": "ui", "description": "x", "steps_outline": ["a"]}], "status": "running"}

        def mock_plan(s):
            call_log.append("plan")
            return {"case_plan": [{"id": "c001", "title": "T", "steps": [{"phase": "test_case", "action": "type", "model": "M", "data": "D"}]}], "status": "running"}

        def mock_data(s):
            call_log.append("data")
            return {"test_data": {"datatables": [], "verify_tables": []}, "status": "running"}

        gen_count = {"n": 0}

        def mock_gen(s):
            gen_count["n"] += 1
            call_log.append(f"gen_{gen_count['n']}")
            return {"generated_files": ["/tmp/f.xml"], "status": "running"}

        val_count = {"n": 0}

        def mock_val(s):
            val_count["n"] += 1
            call_log.append(f"val_{val_count['n']}")
            if val_count["n"] < 2:
                return {"validation_errors": ["error"], "fix_attempt": val_count["n"], "status": "running"}
            return {"validation_errors": [], "status": "success"}

        graph = build_design_graph(mock_analyze, mock_plan, mock_data, mock_gen, mock_val)
        result = graph.invoke({"requirement": "test", "output_dir": "/tmp"})
        assert result["status"] == "success"
        # gen and val should each be called at least 2 times
        assert gen_count["n"] >= 2
        assert val_count["n"] >= 2


# ============================================================
# JSON parsing
# ============================================================


class TestParseJsonResponse:
    """测试 _parse_json_response"""

    def test_plain_json(self):
        """Plain JSON string should parse."""
        result = _parse_json_response('[{"a": 1}]')
        assert result == [{"a": 1}]

    def test_markdown_json_block(self):
        """JSON inside markdown code block should parse."""
        text = '```json\n[{"a": 1}]\n```'
        result = _parse_json_response(text)
        assert result == [{"a": 1}]

    def test_generic_code_block(self):
        """JSON inside generic code block should parse."""
        text = '```\n{"key": "value"}\n```'
        result = _parse_json_response(text)
        assert result == {"key": "value"}

    def test_invalid_json_raises(self):
        """Invalid JSON should raise JSONDecodeError."""
        with pytest.raises(json.JSONDecodeError):
            _parse_json_response("not json at all")


# ============================================================
# CLI design command
# ============================================================


class TestCliDesignCommand:
    """测试 CLI design 命令"""

    def test_design_help(self, cli_runner):
        """design --help should show help text."""
        from rodski_agent.cli import main
        result = cli_runner.invoke(main, ["design", "--help"])
        assert result.exit_code == 0
        assert "--requirement" in result.output

    def test_design_json_output(self, cli_runner, tmp_path):
        """design with --format json should produce valid JSON."""
        from rodski_agent.cli import main
        output_dir = str(tmp_path / "output")
        result = cli_runner.invoke(main, [
            "--format", "json",
            "design",
            "--requirement", "测试登录功能",
            "--output", output_dir,
        ])
        parsed = json.loads(result.output.strip())
        assert isinstance(parsed, dict)
        assert "status" in parsed
        assert "command" in parsed
        assert parsed["command"] == "design"

    def test_design_human_output(self, cli_runner, tmp_path):
        """design with human format should produce readable text."""
        from rodski_agent.cli import main
        output_dir = str(tmp_path / "output")
        result = cli_runner.invoke(main, [
            "--format", "human",
            "design",
            "--requirement", "测试登录功能",
            "--output", output_dir,
        ])
        assert result.output.strip() != ""

    def test_design_creates_files(self, cli_runner, tmp_path):
        """design command should create output files."""
        from rodski_agent.cli import main
        output_dir = str(tmp_path / "output")
        cli_runner.invoke(main, [
            "design",
            "--requirement", "测试搜索功能",
            "--output", output_dir,
        ])
        # Should create directory structure
        assert os.path.isdir(os.path.join(output_dir, "case"))
        assert os.path.isdir(os.path.join(output_dir, "model"))
        assert os.path.isdir(os.path.join(output_dir, "data"))

    def test_design_missing_requirement(self, cli_runner, tmp_path):
        """Missing --requirement should fail."""
        from rodski_agent.cli import main
        result = cli_runner.invoke(main, [
            "design",
            "--output", str(tmp_path / "out"),
        ])
        assert result.exit_code != 0
