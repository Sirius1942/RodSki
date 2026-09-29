"""v11.6.0 集成项（WI-64-07）：C4 非法 action 提示、demo WaitTime 毫秒迁移、init 模板。"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

RODSKI_DIR = Path(__file__).resolve().parents[2]
REPO = RODSKI_DIR.parent
if str(RODSKI_DIR) not in sys.path:
    sys.path.insert(0, str(RODSKI_DIR))

from core.exceptions import UnknownKeywordError, XmlSchemaValidationError  # noqa: E402
from core.xml_schema_validator import RodskiXmlValidator, action_hint_for  # noqa: E402


def _write_case(tmp_path: Path, action: str) -> Path:
    p = tmp_path / "c.xml"
    p.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<cases>\n'
        '  <case execute="是" id="TC001" title="t">\n    <test_case>\n'
        f'      <test_step action="{action}" model="Login" data="L001"/>\n'
        '    </test_case>\n  </case>\n</cases>\n',
        encoding="utf-8",
    )
    return p


def test_xsd_error_for_click_action_has_type_hint(tmp_path):
    with pytest.raises(XmlSchemaValidationError) as ei:
        RodskiXmlValidator.validate_file(_write_case(tmp_path, "click"), "case")
    msg = str(ei.value)
    assert "不是关键字" in msg and "type" in msg and "CORE §1.2" in msg
    assert ei.value.details.get("hint")


def test_xsd_error_for_other_unknown_action_mentions_17_keywords(tmp_path):
    with pytest.raises(XmlSchemaValidationError) as ei:
        RodskiXmlValidator.validate_file(_write_case(tmp_path, "http_get"), "case")
    assert "17 个关键字" in str(ei.value)


def test_action_hint_irrelevant_errors_return_none():
    assert action_hint_for(["missing required attribute 'id'"]) is None


def test_valid_action_passes(tmp_path):
    RodskiXmlValidator.validate_file(_write_case(tmp_path, "type"), "case")


def test_unknown_keyword_error_hint_for_ui_atomic():
    e = UnknownKeywordError("hover", ["type", "verify"])
    assert "不是关键字" in str(e)
    assert e.details["hint"]
    plain = UnknownKeywordError("foo", ["type"])
    assert "hint" not in plain.details


def _default_wait(gv: Path):
    root = ET.parse(gv).getroot()
    for group in root.findall("group"):
        if group.get("name") != "DefaultValue":
            continue
        for var in group.findall("var"):
            if var.get("name") == "WaitTime":
                return var.get("value")
    return None


def test_demo_waittime_migrated_to_milliseconds():
    """除兼容性夹具外，rodski-demo 不应再有 0 < WaitTime ≤ 30 的旧「秒」写法。"""
    demo = REPO / "rodski-demo"
    if not demo.is_dir():
        pytest.skip("rodski-demo 不存在")
    legacy = []
    for gv in demo.rglob("data/globalvalue.xml"):
        if "_archive" in gv.parts or "demo_authoring_v116_pitfalls" in gv.parts:
            continue
        raw = _default_wait(gv)
        if raw is None:
            continue
        v = float(raw)
        if 0 < v <= 30:
            legacy.append(f"{gv.relative_to(REPO)}={raw}")
    assert not legacy, f"WaitTime 仍为旧秒值: {legacy}"


def test_pitfalls_fixture_keeps_legacy_waittime():
    gv = REPO / "rodski-demo/DEMO/demo_authoring_v116_pitfalls/data/globalvalue.xml"
    if not gv.is_file():
        pytest.skip("夹具不存在")
    assert _default_wait(gv) == "1"


def test_init_template_waittime_zero_ms():
    from rodski_cli.init import _GLOBALVALUE_XML
    root = ET.fromstring(_GLOBALVALUE_XML.encode("utf-8"))
    var = root.find("./group[@name='DefaultValue']/var[@name='WaitTime']")
    assert var is not None and var.get("value") == "0"
    assert "毫秒" in _GLOBALVALUE_XML


def test_html_report_marks_evidence_and_session_mode(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from rodski_cli.report import generate_html_from_run_results
    path = generate_html_from_run_results(
        results=[{"case_id": "TC001", "title": "t", "status": "PASS", "execution_time": 0.1}],
        total=1, passed=1, failed=0, duration=0.1, output_dir=str(tmp_path),
        run_meta={"evidence_mode": "concise", "session_mode": "shared_browser"},
    )
    html = Path(path).read_text(encoding="utf-8")
    assert "EvidenceMode: concise" in html
    assert "SessionMode: shared_browser" in html


def test_html_report_without_meta_has_no_mode_line(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from rodski_cli.report import generate_html_from_run_results
    path = generate_html_from_run_results(
        results=[], total=0, passed=0, failed=0, duration=0.0, output_dir=str(tmp_path),
    )
    assert "EvidenceMode:" not in Path(path).read_text(encoding="utf-8")


@pytest.mark.parametrize("key,value", [
    ("DialogPolicy", "yes"), ("AutoWait", "-1"), ("AutoWait", "abc"),
    ("WaitTime", "abc"), ("WaitTime", "-5"),
])
def test_validate_default_values_rejects_illegal(key, value):
    from core.session_mode import validate_default_values
    with pytest.raises(ValueError) as ei:
        validate_default_values({"DefaultValue": {key: value}})
    assert key in str(ei.value) and "修复" in str(ei.value)


def test_validate_default_values_accepts_legal_and_missing():
    from core.session_mode import validate_default_values
    validate_default_values(None)
    validate_default_values({"DefaultValue": {}})
    validate_default_values({"DefaultValue": {
        "WaitTime": "1", "AutoWait": "0", "DialogPolicy": "Accept"}})
    validate_default_values({"DefaultValue": {"WaitTime": "", "AutoWait": " "}})


def test_validate_default_values_rejects_legacy_verify_timeout_key():
    """旧键 VerifyTimeout 在启动驱动前报错并提示改名为 AutoWait（毫秒）。"""
    from core.session_mode import validate_default_values
    with pytest.raises(ValueError) as ei:
        validate_default_values({"DefaultValue": {"VerifyTimeout": "5"}})
    assert "已更名为 DefaultValue.AutoWait" in str(ei.value) and "5000" in str(ei.value)


def test_run_dirs_in_same_second_do_not_collide(tmp_path, monkeypatch):
    """两次 run 同一秒启动时各自拥有独立运行目录（不覆盖前一次的 result.xml）。"""
    import core.result_writer as rw

    class _FixedDT:
        @staticmethod
        def now():
            import datetime as _d
            return _d.datetime(2026, 9, 29, 12, 0, 0)

    monkeypatch.setattr(rw, "datetime", _FixedDT)
    monkeypatch.delenv("RODSKI_RUN_DIR_SUFFIX", raising=False)
    a = rw.ResultWriter(str(tmp_path / "result"))
    a._init_run_dir()
    b = rw.ResultWriter(str(tmp_path / "result"))
    b._init_run_dir()
    assert a.current_run_dir.name == "rodski_20260929_120000"
    assert b.current_run_dir.name == "rodski_20260929_120000_2"
    a._init_run_dir()  # 同一 writer 重复调用保持原目录
    assert a.current_run_dir.name == "rodski_20260929_120000"
