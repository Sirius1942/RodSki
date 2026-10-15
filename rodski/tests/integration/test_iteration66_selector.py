"""iteration-66 回归：selector（--tag/--tags/--priority/--exclude-tag）选择语义

缺陷只在完整 CLI 链路上暴露（run.py → SKIExecutor 用例级过滤 → selector 编译 → 选择应用），
因此以子进程执行真实的 rodski run，按 result.xml 中各用例状态判定。
"""
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent

CASES = '''<?xml version="1.0" encoding="UTF-8"?>
<cases tags="suite">
  <case execute="是" id="PLAIN_P0" title="无 scenario P0" priority="P0" tags="smoke">
    <test_case><test_step action="set" model="" data="a=1"/></test_case>
  </case>
  <case execute="是" id="PLAIN_P1" title="无 scenario P1" priority="P1">
    <test_case><test_step action="set" model="" data="b=1"/></test_case>
  </case>
  <case execute="是" id="SCN" title="含 scenario" priority="P2">
    <test_case>
      <scenario id="S1" tag="p0"><test_step action="set" model="" data="s1=1"/></scenario>
      <scenario id="S2" tag="slow"><test_step action="set" model="" data="s2=1"/></scenario>
    </test_case>
  </case>
</cases>'''


def _module(tmp_path: Path) -> Path:
    module = tmp_path / "product" / "proj" / "mod"
    for name in ("case", "model", "data", "fun", "result"):
        (module / name).mkdir(parents=True)
    (module / "model" / "model.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?><models/>', encoding="utf-8")
    (module / "data" / "globalvalue.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?><globalvalue>'
        '<group name="DefaultValue"><var name="WaitTime" value="0"/></group></globalvalue>',
        encoding="utf-8")
    (module / "case" / "c.xml").write_text(CASES, encoding="utf-8")
    return module


def _executed(module: Path, *args: str):
    """返回 (退出码, 状态为 PASS 的用例 ID 集合)。"""
    proc = subprocess.run(
        [sys.executable, "-c",
         "import sys; from rodski.rodski_cli import main; sys.argv=['rodski']+sys.argv[1:]; sys.exit(main())",
         "run", str(module / "case"), *args],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT.parent), timeout=120,
    )
    results = sorted((module / "result").rglob("result.xml"))
    assert results, proc.stdout + proc.stderr
    root = ET.parse(results[-1]).getroot()
    passed = {r.get("case_id") for r in root.iter("result") if r.get("status") == "PASS"}
    return proc.returncode, passed


def test_tags_select_scenarioless_cases(tmp_path):
    """BUG-A06：--tags 命中文件级 tags 时，不含 scenario 的用例也要执行"""
    code, passed = _executed(_module(tmp_path), "--tags", "suite")
    assert code == 0
    assert passed == {"PLAIN_P0", "PLAIN_P1", "SCN"}


def test_tag_only_on_scenario(tmp_path):
    """BUG-A09：只写在 scenario@tag 上的标签也能选中（不能先按文件级 tags 过滤掉）"""
    code, passed = _executed(_module(tmp_path), "--tag", "p0")
    assert code == 0
    assert passed == {"SCN"}


def test_case_level_tags(tmp_path):
    """BUG-A07：<case tags> 参与 --tags 选择与 --exclude-tags 排除"""
    module = _module(tmp_path)
    code, passed = _executed(module, "--tags", "smoke")
    assert passed == {"PLAIN_P0"}
    code, passed = _executed(_module(tmp_path / "x"), "--tags", "suite", "--exclude-tags", "smoke")
    assert passed == {"PLAIN_P1", "SCN"}


def test_priority_multi_value(tmp_path):
    """BUG-A08：--priority P0,P2 两个优先级的用例都执行"""
    code, passed = _executed(_module(tmp_path), "--priority", "P0,P2")
    assert passed == {"PLAIN_P0", "SCN"}


def test_selector_without_case_path(tmp_path):
    """BUG-A10：模块目录下不带路径 `rodski run --tag p0` 在全部用例上选择，不去解析默认计划"""
    module = _module(tmp_path)
    proc = subprocess.run(
        [sys.executable, "-c",
         "import sys; from rodski.rodski_cli import main; sys.argv=['rodski']+sys.argv[1:]; sys.exit(main())",
         "run", "--tag", "p0"],
        capture_output=True, text=True, cwd=str(module), timeout=120,
        env={**__import__("os").environ, "PYTHONPATH": str(PROJECT_ROOT.parent)},
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "未找到默认测试计划" not in proc.stdout + proc.stderr
    root = ET.parse(sorted((module / "result").rglob("result.xml"))[-1]).getroot()
    assert {r.get("case_id") for r in root.iter("result") if r.get("status") == "PASS"} == {"SCN"}
