from pathlib import Path
from unittest.mock import Mock
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from rodski.core.config_manager import ConfigManager
from rodski.core.ski_executor import SKIExecutor


def _build_module(tmp_path: Path) -> Path:
    module_dir = tmp_path / "test_module"
    (module_dir / "case").mkdir(parents=True)
    (module_dir / "model").mkdir()
    (module_dir / "data").mkdir()
    (module_dir / "result").mkdir()

    (module_dir / "model" / "model.xml").write_text('''\
<?xml version="1.0" encoding="UTF-8"?>
<models>
  <model name="test">
    <element name="input">
      <location type="id">username</location>
    </element>
  </model>
</models>''', encoding="utf-8")

    (module_dir / "data" / "globalvalue.xml").write_text('''\
<?xml version="1.0" encoding="UTF-8"?>
<globalvalue>
  <group name="DefaultValue">
    <var name="WaitTime" value="0"/>
  </group>
</globalvalue>''', encoding="utf-8")

    (module_dir / "case" / "test.xml").write_text('''\
<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="TC001" title="录制测试">
    <test_case>
      <test_step action="wait" model="" data="0"/>
    </test_case>
  </case>
</cases>''', encoding="utf-8")

    return module_dir


def _make_driver() -> Mock:
    driver = Mock()
    driver.headless = True
    driver.wait = Mock(return_value=True)
    driver.screenshot = Mock(return_value=True)
    driver.close = Mock(return_value=True)
    driver.start_case_recording = Mock(side_effect=lambda output_dir, case_id, target_path: target_path)
    driver.stop_case_recording = Mock(side_effect=lambda case_id, target_path: target_path)
    return driver


def _make_config(tmp_path: Path, enabled: bool) -> ConfigManager:
    config = ConfigManager(str(tmp_path / f"config_{enabled}.json"))
    config.config["recording"] = {
        "enabled": enabled,
        "mode": "auto",
        "scope": "target",
        "output_dir": "recordings",
        "fps": 10,
        "max_duration": 600,
        "retain_on_pass": True,
        "retain_on_fail": True,
        "prefer_playwright_native_in_headless": True,
        "capture_input": False,
        "event_timeline": False,
        "monitor_id": None,
    }
    return config


class TestRecordingIntegration:
    def test_recording_disabled_by_default(self, tmp_path):
        module_dir = _build_module(tmp_path)
        driver = _make_driver()
        config = _make_config(tmp_path, False)
        executor = SKIExecutor(str(module_dir / "case" / "test.xml"), driver, config, module_dir=str(module_dir))

        result = executor.execute_case({
            "case_id": "TC_OFF",
            "title": "关闭录制",
            "pre_process": [],
            "test_case": [{"action": "wait", "model": "", "data": "0"}],
            "post_process": [],
        })

        assert result["status"] == "PASS"
        assert result["recording_path"] == ""
        driver.start_case_recording.assert_not_called()

    def test_playwright_recording_starts_and_stops(self, tmp_path):
        module_dir = _build_module(tmp_path)
        driver = _make_driver()
        config = _make_config(tmp_path, True)
        executor = SKIExecutor(str(module_dir / "case" / "test.xml"), driver, config, module_dir=str(module_dir))
        executor.result_writer._init_run_dir()

        result = executor.execute_case({
            "case_id": "TC_REC",
            "title": "开启录制",
            "pre_process": [],
            "test_case": [{"action": "wait", "model": "", "data": "0"}],
            "post_process": [],
        })

        assert result["status"] == "PASS"
        assert result["recording_path"].startswith("recordings/TC_REC_")
        assert result["recording_path"].endswith(".webm")
        driver.start_case_recording.assert_called_once()
        driver.stop_case_recording.assert_called_once()

    def test_recording_start_failure_does_not_fail_case(self, tmp_path):
        module_dir = _build_module(tmp_path)
        driver = _make_driver()
        driver.start_case_recording.side_effect = RuntimeError("recording unavailable")
        config = _make_config(tmp_path, True)
        executor = SKIExecutor(str(module_dir / "case" / "test.xml"), driver, config, module_dir=str(module_dir))
        executor.result_writer._init_run_dir()

        result = executor.execute_case({
            "case_id": "TC_REC_FAIL",
            "title": "录制失败不影响用例",
            "pre_process": [],
            "test_case": [{"action": "wait", "model": "", "data": "0"}],
            "post_process": [],
        })

        assert result["status"] == "PASS"
        assert result["recording_path"] == ""

    def test_result_xml_contains_recording_path(self, tmp_path):
        module_dir = _build_module(tmp_path)
        driver = _make_driver()
        config = _make_config(tmp_path, True)
        executor = SKIExecutor(str(module_dir / "case" / "test.xml"), driver, config, module_dir=str(module_dir))

        results = executor.execute_all_cases()

        assert results[0]["recording_path"].endswith(".webm")
        result_file = executor.result_writer.current_run_dir / "result.xml"
        root = ET.parse(result_file).getroot()
        result_elem = root.find("./results/result")
        assert result_elem is not None
        assert result_elem.get("recording_path", "").endswith(".webm")
