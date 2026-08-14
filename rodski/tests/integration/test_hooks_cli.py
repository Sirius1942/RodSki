"""CLI Hooks 机制集成测试（v8.2.0）

覆盖：
  - 无 hooks.json 时行为不变（回归）
  - on_run_start 合规检查失败（缺目录）无 --force-compliance 时 exit 1
  - 加 --force-compliance 后可跳过非目录类检查项并继续执行，日志有跳过记录
  - hooks.json 配置 on_run_start deny hook 时 exit 1 且不执行
"""
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent


def run_cli(*args, cwd=None):
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "cli_main.py")] + list(args),
        capture_output=True,
        text=True,
        cwd=str(cwd or PROJECT_ROOT),
    )
    return result


def _make_minimal_module(base: Path, with_data_dir: bool = True) -> Path:
    """构造最小可 dry-run 的测试模块目录。"""
    (base / "case").mkdir(parents=True, exist_ok=True)
    (base / "model").mkdir(parents=True, exist_ok=True)
    (base / "fun").mkdir(parents=True, exist_ok=True)
    (base / "result").mkdir(parents=True, exist_ok=True)
    if with_data_dir:
        (base / "data").mkdir(parents=True, exist_ok=True)
        (base / "data" / "globalvalue.xml").write_text(
            '<?xml version="1.0"?><globalvalue></globalvalue>', encoding="utf-8"
        )

    (base / "case" / "t.xml").write_text(
        """<?xml version="1.0"?>
<cases>
  <case id="c1" title="t" execute="是">
    <test_case>
      <test_step action="wait" model="" data="0"/>
    </test_case>
  </case>
</cases>
""",
        encoding="utf-8",
    )
    (base / "model" / "model.xml").write_text(
        '<?xml version="1.0"?><models></models>', encoding="utf-8"
    )
    return base / "case" / "t.xml"


def _make_verify_sqlite(base: Path, value: str) -> None:
    conn = sqlite3.connect(str(base / "data" / "data.sqlite"))
    conn.executescript("""
        CREATE TABLE rs_datatable (table_name TEXT PRIMARY KEY, model_name TEXT NOT NULL,
            table_kind TEXT NOT NULL, row_mode TEXT NOT NULL, remark TEXT DEFAULT '', updated_at TEXT DEFAULT '');
        CREATE TABLE rs_datatable_field (table_name TEXT NOT NULL, field_name TEXT NOT NULL,
            field_order INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (table_name, field_name));
        CREATE TABLE rs_row (table_name TEXT NOT NULL, data_id TEXT NOT NULL,
            remark TEXT DEFAULT '', PRIMARY KEY (table_name, data_id));
        CREATE TABLE rs_field (table_name TEXT NOT NULL, data_id TEXT NOT NULL,
            field_name TEXT NOT NULL, field_value TEXT NOT NULL,
            PRIMARY KEY (table_name, data_id, field_name));
    """)
    conn.execute(
        "INSERT INTO rs_datatable VALUES (?,?,?,?,?,?)",
        ("LoginAPI_verify", "LoginAPI", "verify", "standard", "", ""),
    )
    conn.execute(
        "INSERT INTO rs_datatable_field VALUES (?,?,?)",
        ("LoginAPI_verify", "token", 0),
    )
    conn.execute("INSERT INTO rs_row VALUES (?,?,?)", ("LoginAPI_verify", "V001", ""))
    conn.execute(
        "INSERT INTO rs_field VALUES (?,?,?,?)",
        ("LoginAPI_verify", "V001", "token", value),
    )
    conn.commit()
    conn.close()


def _extract_json_payload(stdout: str):
    decoder = json.JSONDecoder()
    for index, char in enumerate(stdout):
        if char != "{":
            continue
        try:
            payload, end = decoder.raw_decode(stdout[index:])
        except json.JSONDecodeError:
            continue
        if not stdout[index + end:].strip():
            return payload
    raise AssertionError(f"stdout 中未找到最终 JSON 输出: {stdout}")


class TestNoHooksConfigBehaviorUnchanged:
    """无 hooks.json 时，dry-run 行为应与迭代前完全一致（回归保护）。"""

    def test_dry_run_passes_without_hooks_json(self, tmp_path):
        case_path = _make_minimal_module(tmp_path)
        r = run_cli("run", str(case_path), "--dry-run")
        assert r.returncode == 0
        assert "验证通过" in r.stdout


class TestComplianceCheckDirectoryMissing:
    """目录结构缺失是硬性前提，--force-compliance 也不能跳过。"""

    def test_missing_data_dir_fails_without_force(self, tmp_path):
        case_path = _make_minimal_module(tmp_path, with_data_dir=False)
        r = run_cli("run", str(case_path), "--dry-run")
        assert r.returncode == 1
        assert "directory_structure" in r.stdout or "directory_structure" in r.stderr

    def test_missing_data_dir_fails_even_with_force_compliance(self, tmp_path):
        case_path = _make_minimal_module(tmp_path, with_data_dir=False)
        r = run_cli("run", str(case_path), "--dry-run", "--force-compliance")
        assert r.returncode == 1
        combined = r.stdout + r.stderr
        assert "directory_structure" in combined


class TestOnRunStartHookDeny:
    """hooks.json 配置 on_run_start deny hook 时应拒绝执行。"""

    def test_on_run_start_deny_blocks_execution(self, tmp_path):
        case_path = _make_minimal_module(tmp_path)
        hooks_config = {
            "on_run_start": [
                {
                    "command": [
                        sys.executable,
                        "-c",
                        "import sys; print('{\"reason\": \"policy: blocked\"}'); sys.exit(2)",
                    ]
                }
            ]
        }
        (tmp_path / "hooks.json").write_text(json.dumps(hooks_config), encoding="utf-8")

        r = run_cli("run", str(case_path), "--dry-run")
        assert r.returncode == 1
        combined = r.stdout + r.stderr
        assert "policy: blocked" in combined

    def test_on_run_start_allow_permits_execution(self, tmp_path):
        case_path = _make_minimal_module(tmp_path)
        hooks_config = {
            "on_run_start": [
                {"command": [sys.executable, "-c", "import sys; sys.exit(0)"]}
            ]
        }
        (tmp_path / "hooks.json").write_text(json.dumps(hooks_config), encoding="utf-8")

        r = run_cli("run", str(case_path), "--dry-run")
        assert r.returncode == 0
        assert "验证通过" in r.stdout


class TestExternalHookContext:
    def test_on_run_start_receives_event_version_and_live_capabilities(self, tmp_path):
        case_path = _make_minimal_module(tmp_path)
        captured = tmp_path / "run-start-context.json"
        script = (
            "from pathlib import Path; import sys; "
            "Path(sys.argv[1]).write_text(sys.stdin.read(), encoding='utf-8')"
        )
        (tmp_path / "hooks.json").write_text(
            json.dumps({
                "on_run_start": [{
                    "command": [sys.executable, "-c", script, str(captured)]
                }]
            }),
            encoding="utf-8",
        )

        r = run_cli("run", str(case_path), "--dry-run")

        assert r.returncode == 0, r.stderr
        context = json.loads(captured.read_text(encoding="utf-8"))
        assert context["event"] == "on_run_start"
        assert context["rodski_version"] == context["version"]
        assert "wait" in context["supported_keywords"]
        assert context["required_dirs"] == ["case", "model", "data"]
        assert context["module_dir"] == str(tmp_path)
        assert context["case_path"] == str(case_path)
        assert context["plan_id"] is None
        assert context["selector_filters"]["filter_tags"] is None

    def test_failing_case_triggers_external_on_case_failure(self, tmp_path):
        case_path = _make_minimal_module(tmp_path)
        (case_path).write_text(
            """<?xml version="1.0"?>
<cases>
  <case id="c1" title="broken" description="intentional" execute="是" component_type="接口">
    <test_case><test_step action="wait" model="" data="not-a-number"/></test_case>
  </case>
</cases>
""",
            encoding="utf-8",
        )
        captured = tmp_path / "case-failure-context.json"
        script = (
            "from pathlib import Path; import sys; "
            "Path(sys.argv[1]).write_text(sys.stdin.read(), encoding='utf-8')"
        )
        (tmp_path / "hooks.json").write_text(
            json.dumps({
                "on_case_failure": [{
                    "command": [sys.executable, "-c", script, str(captured)]
                }]
            }),
            encoding="utf-8",
        )

        r = run_cli("run", str(case_path), "--output-format", "json")

        assert r.returncode == 1
        context = json.loads(captured.read_text(encoding="utf-8"))
        assert context["event"] == "on_case_failure"
        assert context["case_id"] == "c1"
        assert context["title"] == "broken"
        assert context["description"] == "intentional"
        assert context["component_type"] == "接口"
        assert context["error_type"] == "RetryExhaustedError"
        assert "not-a-number" in context["error_message"]
        output = _extract_json_payload(r.stdout)
        assert output["steps"][0]["case_diagnosis"]["failure_reason"]

    def test_on_run_end_receives_summary_and_common_context(self, tmp_path):
        case_path = _make_minimal_module(tmp_path)
        captured = tmp_path / "run-end-context.json"
        script = (
            "from pathlib import Path; import sys; "
            "Path(sys.argv[1]).write_text(sys.stdin.read(), encoding='utf-8')"
        )
        (tmp_path / "hooks.json").write_text(
            json.dumps({
                "on_run_end": [{
                    "command": [sys.executable, "-c", script, str(captured)]
                }]
            }),
            encoding="utf-8",
        )

        r = run_cli("run", str(case_path), "--output-format", "json")

        assert r.returncode == 0, r.stderr
        context = json.loads(captured.read_text(encoding="utf-8"))
        assert context["event"] == "on_run_end"
        assert context["rodski_version"] == context["version"]
        assert context["module_dir"] == str(tmp_path)
        assert context["total"] == 1
        assert context["passed"] == 1
        assert context["failed"] == 0
        assert context["skipped"] == 0
        assert context["status"] == "passed"
        assert context["compliance"]["passed"] is True
        assert context["compliance"]["skipped"] is False


class TestForceComplianceAudit:
    def test_json_output_records_skipped_non_directory_check(self, tmp_path):
        case_path = _make_minimal_module(tmp_path)
        (tmp_path / "model" / "model.xml").write_text(
            '<?xml version="1.0"?><models><model name="LoginAPI" type="interface"/></models>',
            encoding="utf-8",
        )
        _make_verify_sqlite(tmp_path, "${Return[-1].token}")

        r = run_cli(
            "run",
            str(case_path),
            "--force-compliance",
            "--output-format",
            "json",
        )

        assert r.returncode == 0, r.stderr
        output = _extract_json_payload(r.stdout)
        assert output["compliance"]["passed"] is False
        assert output["compliance"]["skipped"] is True
        failed_names = {
            item["check_name"] for item in output["compliance"]["failed_checks"]
        }
        assert failed_names == {"return_ref_self_check"}
        assert output["compliance"]["skipped_checks"] == output["compliance"]["failed_checks"]


class TestInvalidHooksConfig:
    """hooks.json 格式错误时应清晰报错退出，不进入执行。"""

    def test_malformed_command_field_fails_clearly(self, tmp_path):
        case_path = _make_minimal_module(tmp_path)
        (tmp_path / "hooks.json").write_text(
            json.dumps({"on_run_start": [{"command": "not-an-array"}]}), encoding="utf-8"
        )
        r = run_cli("run", str(case_path), "--dry-run")
        assert r.returncode == 1
        combined = r.stdout + r.stderr
        assert "hooks.json" in combined
