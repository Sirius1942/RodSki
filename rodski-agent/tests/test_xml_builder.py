"""XML Builder 单元测试。

测试 src/rodski_agent/common/xml_builder.py 中各 build_* 函数的正确性和约束校验。
"""
from __future__ import annotations

import pytest

from rodski_agent.common.xml_builder import (
    build_case_xml,
    build_model_xml,
    build_data_xml,
    build_verify_xml,
    build_globalvalue_xml,
)


# ============================================================
# build_case_xml
# ============================================================


class TestBuildCaseXml:
    """测试 build_case_xml"""

    def test_valid_case(self):
        """Valid single case produces proper XML."""
        cases = [
            {
                "id": "c001",
                "title": "Login Test",
                "component_type": "界面",
                "steps": [
                    {"phase": "pre_process", "action": "navigate", "model": "", "data": "http://localhost"},
                    {"phase": "test_case", "action": "type", "model": "Login", "data": "L001"},
                    {"phase": "test_case", "action": "verify", "model": "Login", "data": "V001"},
                    {"phase": "post_process", "action": "close", "model": "", "data": ""},
                ],
            }
        ]
        xml = build_case_xml(cases)
        assert '<?xml version="1.0" encoding="UTF-8"?>' in xml
        assert "<cases>" in xml
        assert 'id="c001"' in xml
        assert 'action="type"' in xml
        assert "<pre_process>" in xml
        assert "<test_case>" in xml
        assert "<post_process>" in xml

    def test_invalid_action_raises(self):
        """Invalid action (e.g., 'click') should raise ValueError."""
        cases = [
            {
                "id": "c001",
                "title": "Bad Action",
                "steps": [
                    {"phase": "test_case", "action": "click", "model": "", "data": ""},
                ],
            }
        ]
        with pytest.raises(ValueError, match="invalid action 'click'"):
            build_case_xml(cases)

    def test_invalid_action_hover_raises(self):
        """hover is a UI atomic action, not a keyword."""
        cases = [
            {
                "id": "c001",
                "title": "Bad Action",
                "steps": [
                    {"phase": "test_case", "action": "hover", "model": "", "data": ""},
                ],
            }
        ]
        with pytest.raises(ValueError, match="invalid action 'hover'"):
            build_case_xml(cases)

    def test_empty_cases_raises(self):
        """Empty cases list should raise."""
        with pytest.raises(ValueError, match="must not be empty"):
            build_case_xml([])

    def test_missing_test_case_step_raises(self):
        """Case with only pre_process steps (no test_case) should raise."""
        cases = [
            {
                "id": "c001",
                "title": "No Test Case",
                "steps": [
                    {"phase": "pre_process", "action": "navigate", "model": "", "data": "http://x"},
                ],
            }
        ]
        with pytest.raises(ValueError, match="at least one test_case step"):
            build_case_xml(cases)

    def test_invalid_execute_raises(self):
        """Invalid execute value should raise."""
        cases = [
            {
                "id": "c001",
                "title": "Bad Execute",
                "execute": "maybe",
                "steps": [
                    {"phase": "test_case", "action": "type", "model": "M", "data": "D001"},
                ],
            }
        ]
        with pytest.raises(ValueError, match="execute='maybe' invalid"):
            build_case_xml(cases)

    def test_invalid_component_type_raises(self):
        """Invalid component_type should raise."""
        cases = [
            {
                "id": "c001",
                "title": "Bad Type",
                "component_type": "unknown",
                "steps": [
                    {"phase": "test_case", "action": "type", "model": "M", "data": "D001"},
                ],
            }
        ]
        with pytest.raises(ValueError, match="component_type='unknown' invalid"):
            build_case_xml(cases)

    def test_missing_id_raises(self):
        """Missing case id should raise."""
        cases = [{"title": "No ID", "steps": [{"phase": "test_case", "action": "type", "model": "M", "data": "D"}]}]
        with pytest.raises(ValueError, match="'id' is required"):
            build_case_xml(cases)

    def test_multiple_cases(self):
        """Multiple cases in one XML."""
        cases = [
            {
                "id": "c001",
                "title": "Case 1",
                "steps": [{"phase": "test_case", "action": "type", "model": "M1", "data": "D001"}],
            },
            {
                "id": "c002",
                "title": "Case 2",
                "steps": [{"phase": "test_case", "action": "send", "model": "M2", "data": "D002"}],
            },
        ]
        xml = build_case_xml(cases)
        assert 'id="c001"' in xml
        assert 'id="c002"' in xml

    def test_compat_keyword_check_allowed(self):
        """'check' is a compat keyword and should be allowed."""
        cases = [
            {
                "id": "c001",
                "title": "Check Test",
                "steps": [{"phase": "test_case", "action": "check", "model": "M", "data": "V001"}],
            }
        ]
        xml = build_case_xml(cases)
        assert 'action="check"' in xml

    def test_screenshot_action_allowed(self):
        """'screenshot' is an additional action type and should be allowed."""
        cases = [
            {
                "id": "c001",
                "title": "Screenshot Test",
                "steps": [
                    {"phase": "test_case", "action": "type", "model": "M", "data": "D001"},
                    {"phase": "test_case", "action": "screenshot", "model": "", "data": "/tmp/shot.png"},
                ],
            }
        ]
        xml = build_case_xml(cases)
        assert 'action="screenshot"' in xml


# ============================================================
# build_model_xml
# ============================================================


class TestBuildModelXml:
    """测试 build_model_xml"""

    def test_valid_model(self):
        """Valid model produces proper XML with location elements."""
        models = [
            {
                "name": "Login",
                "elements": [
                    {
                        "name": "username",
                        "type": "web",
                        "locators": [
                            {"type": "id", "value": "username"},
                            {"type": "css", "value": "#username"},
                        ],
                    },
                    {
                        "name": "password",
                        "type": "web",
                        "locators": [{"type": "id", "value": "password"}],
                    },
                ],
            }
        ]
        xml = build_model_xml(models)
        assert '<?xml version="1.0" encoding="UTF-8"?>' in xml
        assert "<models>" in xml
        assert 'name="Login"' in xml
        assert 'name="username"' in xml
        assert '<location type="id">' in xml
        assert "username</location>" in xml
        # Multiple locators should have priority
        assert 'priority="1"' in xml
        assert 'priority="2"' in xml

    def test_invalid_locator_type_raises(self):
        """Invalid locator type should raise ValueError."""
        models = [
            {
                "name": "Bad",
                "elements": [
                    {
                        "name": "elem",
                        "type": "web",
                        "locators": [{"type": "invalid_type", "value": "x"}],
                    }
                ],
            }
        ]
        with pytest.raises(ValueError, match="invalid locator type 'invalid_type'"):
            build_model_xml(models)

    def test_empty_models_raises(self):
        """Empty models list should raise."""
        with pytest.raises(ValueError, match="must not be empty"):
            build_model_xml([])

    def test_no_locators_raises(self):
        """Element without locators should raise."""
        models = [
            {
                "name": "Bad",
                "elements": [
                    {"name": "elem", "type": "web", "locators": []},
                ],
            }
        ]
        with pytest.raises(ValueError, match="at least one locator"):
            build_model_xml(models)

    def test_all_12_locator_types(self):
        """All 12 valid locator types should be accepted."""
        from rodski_agent.common.rodski_knowledge import LOCATOR_TYPES

        elements = [
            {
                "name": f"elem_{lt}",
                "type": "web",
                "locators": [{"type": lt, "value": f"val_{lt}"}],
            }
            for lt in LOCATOR_TYPES
        ]
        models = [{"name": "AllLocators", "elements": elements}]
        xml = build_model_xml(models)
        for lt in LOCATOR_TYPES:
            assert f'type="{lt}"' in xml

    def test_missing_model_name_raises(self):
        """Model without name should raise."""
        models = [{"elements": [{"name": "e", "type": "web", "locators": [{"type": "id", "value": "x"}]}]}]
        with pytest.raises(ValueError, match="'name' is required"):
            build_model_xml(models)

    def test_single_locator_no_priority(self):
        """Single locator should NOT have priority attribute."""
        models = [
            {
                "name": "M",
                "elements": [
                    {"name": "e", "type": "web", "locators": [{"type": "id", "value": "x"}]},
                ],
            }
        ]
        xml = build_model_xml(models)
        assert "priority" not in xml


# ============================================================
# build_data_xml
# ============================================================


class TestBuildDataXml:
    """测试 build_data_xml"""

    def test_valid_data(self):
        """Valid datatable produces proper XML."""
        datatables = [
            {
                "name": "Login",
                "rows": [
                    {
                        "id": "L001",
                        "fields": [
                            {"name": "username", "value": "admin"},
                            {"name": "password", "value": "123456"},
                        ],
                    }
                ],
            }
        ]
        xml = build_data_xml(datatables)
        assert '<?xml version="1.0" encoding="UTF-8"?>' in xml
        assert "<datatables>" in xml
        assert 'name="Login"' in xml
        assert 'id="L001"' in xml
        assert 'name="username"' in xml
        assert "admin" in xml

    def test_empty_datatables_raises(self):
        """Empty datatables list should raise."""
        with pytest.raises(ValueError, match="must not be empty"):
            build_data_xml([])

    def test_duplicate_row_id_raises(self):
        """Duplicate row IDs should raise."""
        datatables = [
            {
                "name": "T",
                "rows": [
                    {"id": "D001", "fields": [{"name": "f", "value": "v"}]},
                    {"id": "D001", "fields": [{"name": "f", "value": "v2"}]},
                ],
            }
        ]
        with pytest.raises(ValueError, match="duplicate row id 'D001'"):
            build_data_xml(datatables)

    def test_empty_rows_raises(self):
        """Datatable with no rows should raise."""
        datatables = [{"name": "T", "rows": []}]
        with pytest.raises(ValueError, match="at least one row"):
            build_data_xml(datatables)

    def test_multiple_datatables(self):
        """Multiple datatables in one XML."""
        datatables = [
            {
                "name": "Login",
                "rows": [{"id": "L001", "fields": [{"name": "f", "value": "v"}]}],
            },
            {
                "name": "Search",
                "rows": [{"id": "S001", "fields": [{"name": "q", "value": "test"}]}],
            },
        ]
        xml = build_data_xml(datatables)
        assert 'name="Login"' in xml
        assert 'name="Search"' in xml


# ============================================================
# build_verify_xml
# ============================================================


class TestBuildVerifyXml:
    """测试 build_verify_xml"""

    def test_valid_verify_table(self):
        """Valid verify table with _verify suffix should succeed."""
        datatables = [
            {
                "name": "Login_verify",
                "rows": [
                    {
                        "id": "V001",
                        "fields": [
                            {"name": "welcome_text", "value": "Welcome"},
                        ],
                    }
                ],
            }
        ]
        xml = build_verify_xml(datatables)
        assert 'name="Login_verify"' in xml

    def test_missing_verify_suffix_raises(self):
        """Table name without _verify suffix should raise."""
        datatables = [
            {
                "name": "Login",
                "rows": [
                    {"id": "V001", "fields": [{"name": "f", "value": "v"}]},
                ],
            }
        ]
        with pytest.raises(ValueError, match="must end with '_verify'"):
            build_verify_xml(datatables)

    def test_empty_verify_raises(self):
        """Empty verify datatables list should raise."""
        with pytest.raises(ValueError, match="must not be empty"):
            build_verify_xml([])


# ============================================================
# build_globalvalue_xml
# ============================================================


class TestBuildGlobalvalueXml:
    """测试 build_globalvalue_xml"""

    def test_valid_globalvalue(self):
        """Valid globalvalue produces proper XML."""
        groups = [
            {
                "name": "DefaultValue",
                "vars": [
                    {"name": "URL", "value": "http://localhost:8080"},
                    {"name": "Timeout", "value": "30"},
                ],
            }
        ]
        xml = build_globalvalue_xml(groups)
        assert '<?xml version="1.0" encoding="UTF-8"?>' in xml
        assert "<globalvalue>" in xml
        assert 'name="DefaultValue"' in xml
        assert 'name="URL"' in xml
        assert 'value="http://localhost:8080"' in xml

    def test_empty_groups_raises(self):
        """Empty groups list should raise."""
        with pytest.raises(ValueError, match="must not be empty"):
            build_globalvalue_xml([])

    def test_duplicate_group_name_raises(self):
        """Duplicate group names should raise."""
        groups = [
            {"name": "G1", "vars": [{"name": "v", "value": "1"}]},
            {"name": "G1", "vars": [{"name": "v", "value": "2"}]},
        ]
        with pytest.raises(ValueError, match="duplicate group name 'G1'"):
            build_globalvalue_xml(groups)

    def test_duplicate_var_name_in_group_raises(self):
        """Duplicate var names within a group should raise."""
        groups = [
            {
                "name": "G1",
                "vars": [
                    {"name": "v1", "value": "a"},
                    {"name": "v1", "value": "b"},
                ],
            }
        ]
        with pytest.raises(ValueError, match="duplicate var name 'v1'"):
            build_globalvalue_xml(groups)

    def test_empty_vars_raises(self):
        """Group with no vars should raise."""
        groups = [{"name": "G1", "vars": []}]
        with pytest.raises(ValueError, match="at least one var"):
            build_globalvalue_xml(groups)

    def test_multiple_groups(self):
        """Multiple groups in one XML."""
        groups = [
            {"name": "G1", "vars": [{"name": "v1", "value": "a"}]},
            {"name": "G2", "vars": [{"name": "v2", "value": "b"}]},
        ]
        xml = build_globalvalue_xml(groups)
        assert 'name="G1"' in xml
        assert 'name="G2"' in xml
