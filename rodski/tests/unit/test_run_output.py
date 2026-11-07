"""run 外部脚本的输出与超时（v11.12.0）

覆盖：
- 失败时报错同时带 stderr 与 stdout 末尾，长输出截断并注明
- 超时时带出脚本已输出的内容（子进程不缓冲）
- 超时可由 test_step 的 timeout 属性 / DefaultValue.RunTimeout 设置，非法值报错
- timeout 只能用于 run 外部脚本
"""
import logging
import xml.etree.ElementTree as ET
from unittest.mock import MagicMock

import pytest

from core.case_parser import CaseParser
from core.exceptions import DriverError, InvalidParameterError
from core.keyword_engine import KeywordEngine, _tail


def _engine(tmp_path, global_vars=None):
    return KeywordEngine(driver=MagicMock(), model_parser=MagicMock(), data_manager=MagicMock(),
                         global_vars=global_vars, module_dir=str(tmp_path))


def _script(tmp_path, body, name="s.py"):
    fun = tmp_path / "fun"
    fun.mkdir(exist_ok=True)
    (fun / name).write_text(body, encoding="utf-8")
    return name


def test_failure_includes_stdout_and_stderr(tmp_path, caplog):
    name = _script(tmp_path, "import sys\nprint('登录接口返回 500')\nsys.stderr.write('boom\\n')\nsys.exit(3)\n")
    with caplog.at_level(logging.ERROR, logger="rodski"):
        with pytest.raises(DriverError) as ei:
            _engine(tmp_path)._kw_run({"model": "", "data": name})
    msg = str(ei.value)
    assert "退出码 3" in msg
    assert "登录接口返回 500" in msg and "boom" in msg
    assert "登录接口返回 500" in caplog.text and "boom" in caplog.text


def test_failure_with_only_stdout_is_not_lost(tmp_path):
    name = _script(tmp_path, "print('断言失败: 期望 2 实际 1')\nraise SystemExit(1)\n")
    with pytest.raises(DriverError) as ei:
        _engine(tmp_path)._kw_run({"model": "", "data": name})
    assert "断言失败: 期望 2 实际 1" in str(ei.value)


def test_failure_without_output_says_so(tmp_path):
    name = _script(tmp_path, "raise SystemExit(1)\n")
    with pytest.raises(DriverError) as ei:
        _engine(tmp_path)._kw_run({"model": "", "data": name})
    assert "没有任何输出" in str(ei.value)


def test_long_output_keeps_tail(tmp_path):
    name = _script(tmp_path, "for i in range(200):\n    print(f'line-{i:03d}')\nraise SystemExit(1)\n")
    with pytest.raises(DriverError) as ei:
        _engine(tmp_path)._kw_run({"model": "", "data": name})
    msg = str(ei.value)
    assert "line-199" in msg and "line-000" not in msg and "前略" in msg


def test_tail_char_limit():
    out = _tail("x" * 10000)
    assert out.endswith("x" * 100) and "前略" in out and len(out) < 3100


def test_timeout_keeps_partial_output(tmp_path):
    name = _script(tmp_path, "import time\nprint('已登录，开始等待回调')\ntime.sleep(30)\n")
    with pytest.raises(DriverError) as ei:
        _engine(tmp_path)._kw_run({"model": "", "data": name, "timeout": "1"})
    msg = str(ei.value)
    assert "超时 (1s)" in msg and "已登录，开始等待回调" in msg


def test_timeout_from_globalvalue(tmp_path):
    name = _script(tmp_path, "import time\ntime.sleep(30)\n")
    engine = _engine(tmp_path, {"DefaultValue": {"RunTimeout": "0.5"}})
    with pytest.raises(DriverError) as ei:
        engine._kw_run({"model": "", "data": name})
    assert "超时 (0.5s)" in str(ei.value) and "没有任何输出" in str(ei.value)


def test_step_timeout_overrides_globalvalue(tmp_path):
    engine = _engine(tmp_path, {"DefaultValue": {"RunTimeout": "1"}})
    assert engine._resolve_run_timeout({"timeout": "600"}) == 600
    assert engine._resolve_run_timeout({}) == 1
    assert _engine(tmp_path)._resolve_run_timeout({}) == 300


@pytest.mark.parametrize("params,gv", [
    ({"timeout": "0"}, None),
    ({"timeout": "-5"}, None),
    ({"timeout": "abc"}, None),
    ({}, {"DefaultValue": {"RunTimeout": "10s"}}),
])
def test_invalid_timeout(tmp_path, params, gv):
    with pytest.raises(InvalidParameterError):
        _engine(tmp_path, gv)._resolve_run_timeout(params)


def test_success_returns_stdout(tmp_path):
    name = _script(tmp_path, "import json, sys\nsys.stderr.write('warn\\n')\nprint(json.dumps({'id': 7}))\n")
    engine = _engine(tmp_path)
    assert engine._kw_run({"model": "", "data": name, "timeout": "30"}) is True
    assert engine._context.history[-1] == {"id": 7}


def test_timeout_rejected_for_builtin(tmp_path):
    with pytest.raises(InvalidParameterError):
        _engine(tmp_path)._kw_run({"model": "", "data": "clear_routes()", "timeout": "5"})


def test_parser_timeout_only_on_run():
    step = CaseParser._parse_step_element(ET.fromstring('<test_step action="run" data="a.py" timeout="600"/>'))
    assert step["timeout"] == "600"
    assert "timeout" not in CaseParser._parse_step_element(ET.fromstring('<test_step action="run" data="a.py"/>'))
    with pytest.raises(ValueError):
        CaseParser._parse_step_element(ET.fromstring('<test_step action="wait" data="1" timeout="5"/>'))
