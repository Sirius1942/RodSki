"""v11.6.0 WI-64-05：--workers 并行调度 / 结果合并，--report junit。"""
from __future__ import annotations

import argparse
import logging
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from rodski.core import parallel_runner as pr
from rodski.core.result_writer import ResultWriter
from rodski.report.junit import build_junit_tree, write_junit_report
from rodski.rodski_cli import run as run_cli


# ------------------------------------------------------------------ fixtures
def _case_xml(case_ids, steps_per_case=1):
    body = []
    for cid in case_ids:
        steps = "".join(f'<test_step action="wait" model="" data="1"/>' for _ in range(steps_per_case))
        body.append(f'<case execute="是" title="t-{cid}" id="{cid}"><test_case>{steps}</test_case></case>')
    return f'<?xml version="1.0" encoding="UTF-8"?><cases>{"".join(body)}</cases>'


@pytest.fixture
def module(tmp_path):
    mod = tmp_path / "product" / "P" / "M"
    for d in ("case/a", "case/b", "model", "data", "fun", "result"):
        (mod / d).mkdir(parents=True, exist_ok=True)
    (mod / "model" / "model.xml").write_text('<models></models>', encoding="utf-8")
    (mod / "case" / "a" / "one.xml").write_text(_case_xml(["TC001", "TC002"], 5), encoding="utf-8")
    (mod / "case" / "a" / "two.xml").write_text(_case_xml(["TC001"], 1), encoding="utf-8")
    (mod / "case" / "b" / "three.xml").write_text(_case_xml(["TC009"], 3), encoding="utf-8")
    (mod / "case" / "top.xml").write_text(_case_xml(["TC100", "TC101", "TC102"], 2), encoding="utf-8")
    return mod


def _task(cf, weight, cases=()):
    return pr.CaseFileTask(case_file=cf, path=cf, weight=weight,
                           cases=[{"case_id": c, "title": ""} for c in cases])


# ------------------------------------------------------------------ discovery / partition
def test_discover_tasks_uses_relative_case_file_order_and_weights(module):
    tasks = pr.discover_case_file_tasks(module / "case", module)
    assert [t.case_file for t in tasks] == ["a/one.xml", "a/two.xml", "b/three.xml", "top.xml"]
    assert [t.weight for t in tasks] == [10, 1, 3, 6]
    assert [c["case_id"] for c in tasks[0]["cases"]] == ["TC001", "TC002"]
    assert tasks[0]["cases"][0]["title"] == "t-TC001"  # title 写在 id 之前也能解析


def test_discover_tasks_single_file(module):
    tasks = pr.discover_case_file_tasks(module / "case" / "b" / "three.xml", module)
    assert [t.case_file for t in tasks] == ["b/three.xml"]


def test_partition_never_splits_a_file_and_caps_bucket_count():
    tasks = [_task("a.xml", 10), _task("b.xml", 1), _task("c.xml", 3), _task("d.xml", 6)]
    buckets = pr.partition_tasks(tasks, 8)
    assert len(buckets) == 4  # 桶数 = min(workers, 文件数)
    flat = [t.case_file for b in buckets for t in b]
    assert sorted(flat) == ["a.xml", "b.xml", "c.xml", "d.xml"]
    assert len(flat) == len(set(flat))


def test_partition_balances_by_weight_and_keeps_discovery_order():
    tasks = [_task("a.xml", 10), _task("b.xml", 1), _task("c.xml", 3), _task("d.xml", 6)]
    buckets = pr.partition_tasks(tasks, 2)
    loads = sorted(sum(t.weight for t in b) for b in buckets)
    assert loads == [10, 10]
    for b in buckets:
        order = [t.case_file for t in b]
        assert order == sorted(order)  # 桶内保持发现顺序


def test_partition_single_worker_keeps_everything_in_order():
    tasks = [_task("a.xml", 1), _task("b.xml", 5)]
    assert [[t.case_file for t in b] for b in pr.partition_tasks(tasks, 1)] == [["a.xml", "b.xml"]]


# ------------------------------------------------------------------ merge
def test_merge_orders_by_file_discovery_order_and_keeps_in_file_order():
    tasks = [_task("a.xml", 1, ["TC1", "TC2"]), _task("b.xml", 1, ["TC1"])]
    outputs = [
        {"worker_id": 2, "case_files": ["b.xml"], "results": [{"case_file": "b.xml", "case_id": "TC1", "status": "PASS"}]},
        {"worker_id": 1, "case_files": ["a.xml"], "results": [
            {"case_file": "a.xml", "case_id": "TC2", "status": "FAIL"},
            {"case_file": "a.xml", "case_id": "TC1", "status": "PASS"},
        ]},
    ]
    merged = pr.merge_worker_results(tasks, outputs)
    assert [(r["case_file"], r["case_id"]) for r in merged] == [("a.xml", "TC2"), ("a.xml", "TC1"), ("b.xml", "TC1")]


def test_merge_worker_error_fills_fail_rows_instead_of_dropping_cases():
    tasks = [_task("a.xml", 1, ["TC1", "TC2"]), _task("b.xml", 1, ["TC9"])]
    outputs = [
        {"worker_id": 1, "case_files": ["a.xml"], "results": [], "error": "RuntimeError: boom"},
        {"worker_id": 2, "case_files": ["b.xml"], "results": [{"case_file": "b.xml", "case_id": "TC9", "status": "PASS"}]},
    ]
    merged = pr.merge_worker_results(tasks, outputs)
    assert [(r["case_id"], r["status"]) for r in merged] == [("TC1", "FAIL"), ("TC2", "FAIL"), ("TC9", "PASS")]
    assert "boom" in merged[0]["error"] and "worker 1" in merged[0]["error"]


# ------------------------------------------------------------------ run_parallel (注入线程池与假 worker)
def test_run_parallel_dispatches_every_file_once_with_shared_run_dir(module, tmp_path):
    seen = []

    def fake_worker(spec):
        seen.append(spec)
        return {"worker_id": spec["worker_id"], "case_files": spec["case_files"], "results": [
            {"case_file": cf, "case_id": "X", "status": "PASS"} for cf in spec["case_files"]]}

    run_dir = tmp_path / "run"
    done = []
    merged, outputs = pr.run_parallel(
        module / "case", module, 3, run_dir, {"headless": True, "selector_filters": {"filter_tags": None}},
        worker_fn=fake_worker, pool_factory=lambda n: ThreadPoolExecutor(max_workers=n),
        on_worker_done=done.append,
    )
    assert len(seen) == 3 and len(done) == 3
    dispatched = [cf for s in seen for cf in s["case_files"]]
    assert sorted(dispatched) == ["a/one.xml", "a/two.xml", "b/three.xml", "top.xml"]
    assert all(s["run_dir"] == str(run_dir) and s["headless"] is True for s in seen)
    assert all(s["case_path"] == str((module / "case").resolve()) for s in seen)  # 与顺序执行同一 case_path
    assert [r["case_file"] for r in merged] == ["a/one.xml", "a/two.xml", "b/three.xml", "top.xml"]
    assert [o["worker_id"] for o in outputs] == [1, 2, 3]


def test_run_parallel_worker_crash_becomes_fail_rows(module, tmp_path):
    def crashing_worker(spec):
        if "top.xml" in spec["case_files"]:
            raise RuntimeError("process died")
        return {"worker_id": spec["worker_id"], "case_files": spec["case_files"], "results": [
            {"case_file": cf, "case_id": "X", "status": "PASS"} for cf in spec["case_files"]]}

    merged, _ = pr.run_parallel(module / "case", module, 4, tmp_path / "run", {},
                                worker_fn=crashing_worker,
                                pool_factory=lambda n: ThreadPoolExecutor(max_workers=n))
    top = [r for r in merged if r["case_file"] == "top.xml"]
    assert [r["case_id"] for r in top] == ["TC100", "TC101", "TC102"]
    assert all(r["status"] == "FAIL" and "process died" in r["error"] for r in top)


def test_to_plain_makes_results_json_safe():
    class Obj:
        def __str__(self):
            return "obj!"

    out = pr._to_plain([{"variables": {"x": Obj()}, "steps": [{"business_result": {"passed": True}}]}])
    assert out == [{"variables": {"x": "obj!"}, "steps": [{"business_result": {"passed": True}}]}]


# ------------------------------------------------------------------ ResultWriter: attach / collect_only
def test_result_writer_attach_run_dir_appends_tagged_log_and_collects_only(tmp_path):
    run_dir = tmp_path / "result" / "rodski_x"
    run_dir.mkdir(parents=True)
    (run_dir / "execution.log").write_text("parent line\n", encoding="utf-8")
    w = ResultWriter(str(tmp_path / "result"))
    w.attach_run_dir(str(run_dir), worker_tag="w2")
    w.collect_only = True
    w._init_run_dir()  # 已挂接：不得另建时间戳目录
    assert w.current_run_dir == run_dir
    logging.getLogger("rodski").info("hello from worker")
    w.write_results([{"case_id": "TC1", "status": "PASS"}])
    assert not (run_dir / "result.xml").exists()
    assert w.collected == [{"case_id": "TC1", "status": "PASS"}]
    assert [p.name for p in (tmp_path / "result").iterdir()] == ["rodski_x"]
    for h in list(logging.getLogger("rodski").handlers):
        if isinstance(h, logging.FileHandler):
            h.flush()
            logging.getLogger("rodski").removeHandler(h)
            h.close()
    log = (run_dir / "execution.log").read_text(encoding="utf-8")
    assert log.startswith("parent line")
    assert "[w2] hello from worker" in log


def test_merged_results_write_one_result_xml(tmp_path):
    w = ResultWriter(str(tmp_path / "result"))
    w.run_meta = {"evidence_mode": "full", "session_mode": "isolated"}
    w.write_results([
        {"case_id": "TC1", "case_file": "a/one.xml", "status": "PASS"},
        {"case_id": "TC1", "case_file": "b/two.xml", "status": "FAIL", "error": "x"},
    ])
    root = ET.parse(w.current_run_dir / "result.xml").getroot()
    assert [(r.get("case_file"), r.get("status")) for r in root.iter("result")] == [
        ("a/one.xml", "PASS"), ("b/two.xml", "FAIL")]
    assert root.find("summary").get("total") == "2"


# ------------------------------------------------------------------ JUnit
# Jenkins xunit-plugin junit-10.xsd（GitLab / GitHub Actions 的 JUnit 解析器均兼容此结构）
JUNIT_XSD = """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" elementFormDefault="qualified" attributeFormDefault="unqualified">
  <xs:element name="failure"><xs:complexType mixed="true">
    <xs:attribute name="type" type="xs:string" use="optional"/>
    <xs:attribute name="message" type="xs:string" use="optional"/>
  </xs:complexType></xs:element>
  <xs:element name="error"><xs:complexType mixed="true">
    <xs:attribute name="type" type="xs:string" use="optional"/>
    <xs:attribute name="message" type="xs:string" use="optional"/>
  </xs:complexType></xs:element>
  <xs:element name="properties"><xs:complexType><xs:sequence>
    <xs:element ref="property" maxOccurs="unbounded"/>
  </xs:sequence></xs:complexType></xs:element>
  <xs:element name="property"><xs:complexType>
    <xs:attribute name="name" type="xs:string" use="required"/>
    <xs:attribute name="value" type="xs:string" use="required"/>
  </xs:complexType></xs:element>
  <xs:element name="skipped"><xs:complexType mixed="true">
    <xs:attribute name="message" type="xs:string" use="optional"/>
  </xs:complexType></xs:element>
  <xs:element name="system-err" type="xs:string"/>
  <xs:element name="system-out" type="xs:string"/>
  <xs:element name="testcase"><xs:complexType><xs:sequence>
    <xs:element ref="skipped" minOccurs="0" maxOccurs="1"/>
    <xs:element ref="error" minOccurs="0" maxOccurs="unbounded"/>
    <xs:element ref="failure" minOccurs="0" maxOccurs="unbounded"/>
    <xs:element ref="system-out" minOccurs="0" maxOccurs="unbounded"/>
    <xs:element ref="system-err" minOccurs="0" maxOccurs="unbounded"/>
  </xs:sequence>
    <xs:attribute name="name" type="xs:string" use="required"/>
    <xs:attribute name="assertions" type="xs:string" use="optional"/>
    <xs:attribute name="time" type="xs:string" use="optional"/>
    <xs:attribute name="classname" type="xs:string" use="optional"/>
    <xs:attribute name="status" type="xs:string" use="optional"/>
  </xs:complexType></xs:element>
  <xs:element name="testsuite"><xs:complexType><xs:sequence>
    <xs:element ref="properties" minOccurs="0" maxOccurs="1"/>
    <xs:element ref="testcase" minOccurs="0" maxOccurs="unbounded"/>
    <xs:element ref="system-out" minOccurs="0" maxOccurs="1"/>
    <xs:element ref="system-err" minOccurs="0" maxOccurs="1"/>
  </xs:sequence>
    <xs:attribute name="name" type="xs:string" use="required"/>
    <xs:attribute name="tests" type="xs:string" use="required"/>
    <xs:attribute name="failures" type="xs:string" use="optional"/>
    <xs:attribute name="errors" type="xs:string" use="optional"/>
    <xs:attribute name="time" type="xs:string" use="optional"/>
    <xs:attribute name="disabled" type="xs:string" use="optional"/>
    <xs:attribute name="skipped" type="xs:string" use="optional"/>
    <xs:attribute name="timestamp" type="xs:string" use="optional"/>
    <xs:attribute name="hostname" type="xs:string" use="optional"/>
    <xs:attribute name="id" type="xs:string" use="optional"/>
    <xs:attribute name="package" type="xs:string" use="optional"/>
  </xs:complexType></xs:element>
  <xs:element name="testsuites"><xs:complexType><xs:sequence>
    <xs:element ref="testsuite" minOccurs="0" maxOccurs="unbounded"/>
  </xs:sequence>
    <xs:attribute name="name" type="xs:string" use="optional"/>
    <xs:attribute name="time" type="xs:string" use="optional"/>
    <xs:attribute name="tests" type="xs:string" use="optional"/>
    <xs:attribute name="failures" type="xs:string" use="optional"/>
    <xs:attribute name="disabled" type="xs:string" use="optional"/>
    <xs:attribute name="errors" type="xs:string" use="optional"/>
    <xs:attribute name="skipped" type="xs:string" use="optional"/>
  </xs:complexType></xs:element>
</xs:schema>
"""


@pytest.fixture
def run_dir_with_results(tmp_path):
    w = ResultWriter(str(tmp_path / "result"))
    w.write_results([
        {"case_id": "TC001", "case_file": "ui/dialog/dialog.xml", "title": "ok", "status": "PASS", "execution_time": 1.5},
        {"case_id": "TC002", "case_file": "ui/dialog/dialog.xml", "title": "bad <&> \"q\"", "status": "FAIL",
         "execution_time": 2.25, "error_type": "AssertionError", "error": "期望 10，实际 0",
         "screenshot_path": "case/ui/dialog/dialog/screenshots/TC002_failure.png",
         "steps": [{"phase": "test_case", "index": 2, "action": "verify", "model": "Grid", "data": "V1",
                    "status": "FAIL", "error": "$count 断言失败",
                    "screenshot": "case/ui/dialog/dialog/screenshots/TC002_step2.png"}]},
        {"case_id": "TC003", "case_file": "ui/dialog/dialog.xml", "status": "SKIP", "error": "plan 未选中"},
        {"case_id": "TC001", "case_file": "db/db.xml", "status": "ERROR", "error": "连接失败"},
    ])
    return w.current_run_dir


def test_junit_structure_counts_and_classname(run_dir_with_results):
    path = write_junit_report(run_dir_with_results)
    assert path == run_dir_with_results / "junit.xml"
    root = ET.parse(path).getroot()
    assert root.tag == "testsuites"
    assert (root.get("tests"), root.get("failures"), root.get("errors"), root.get("skipped")) == ("4", "1", "1", "1")
    suites = root.findall("testsuite")
    assert [s.get("name") for s in suites] == ["ui/dialog/dialog.xml", "db/db.xml"]
    cases = suites[0].findall("testcase")
    assert [c.get("name") for c in cases] == ["TC001", "TC002", "TC003"]
    assert all(c.get("classname") == "ui/dialog/dialog.xml" for c in cases)
    assert cases[0].get("time") == "1.500" and not list(cases[0])
    failure = cases[1].find("failure")
    assert failure.get("message") == "期望 10，实际 0" and failure.get("type") == "AssertionError"
    assert "case/ui/dialog/dialog/screenshots/TC002_failure.png" in failure.text
    assert "TC002_step2.png" in failure.text and "$count 断言失败" in failure.text
    assert "[[ATTACHMENT|case/ui/dialog/dialog/screenshots/TC002_failure.png]]" in cases[1].find("system-out").text
    assert cases[2].find("skipped") is not None
    assert suites[1].find("testcase").find("error") is not None


def test_junit_validates_against_junit_schema(run_dir_with_results):
    lxml_etree = pytest.importorskip("lxml.etree")
    schema = lxml_etree.XMLSchema(lxml_etree.fromstring(JUNIT_XSD.encode("utf-8")))
    doc = lxml_etree.parse(str(write_junit_report(run_dir_with_results)))
    assert schema.validate(doc), schema.error_log


def test_junit_missing_result_xml_has_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="result.xml"):
        write_junit_report(tmp_path)


def test_junit_result_without_case_file_falls_back_to_default_classname(tmp_path):
    w = ResultWriter(str(tmp_path / "result"))
    w.write_results([{"case_id": "TC1", "status": "PASS"}])
    root = build_junit_tree(w.current_run_dir / "result.xml")
    assert root.find("testsuite/testcase").get("classname") == "rodski"


# ------------------------------------------------------------------ CLI 参数
def _parser():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers()
    run_cli.setup_parser(sub)
    return p


def test_cli_report_accepts_html_junit_combinations():
    p = _parser()
    assert p.parse_args(["run", "case/", "--report", "junit"]).report == "junit"
    assert p.parse_args(["run", "case/", "--report", "html"]).report == "html"
    args = p.parse_args(["run", "case/", "--report", "HTML, junit"])
    assert args.report == "html,junit"
    assert run_cli._report_formats(args) == {"html", "junit"}


def test_cli_report_rejects_unknown_format(capsys):
    with pytest.raises(SystemExit):
        _parser().parse_args(["run", "case/", "--report", "pdf"])
    assert "junit" in capsys.readouterr().err


def test_report_formats_compat_with_plain_attribute():
    assert run_cli._report_formats(argparse.Namespace(report="html")) == {"html"}
    assert run_cli._report_formats(argparse.Namespace(report=None)) == set()
    assert run_cli._report_formats(argparse.Namespace()) == set()


def test_cli_workers_parsing():
    p = _parser()
    assert p.parse_args(["run", "case/", "--workers", "4"]).workers == 4
    assert p.parse_args(["run", "case/"]).workers is None
    for bad in ("0", "-2", "x"):
        with pytest.raises(SystemExit):
            p.parse_args(["run", "case/", "--workers", bad])


def test_cli_workers_combines_with_plan_ref():
    args = _parser().parse_args(["run", "@smoke", "--workers", "2", "--report", "junit"])
    assert args.case == "@smoke" and args.workers == 2
    assert not run_cli._has_active_selector(run_cli._build_selector_filters(args))


def _ns(**kw):
    base = dict(model=None, cdp_endpoint=None, insert_steps=None, debug=False, roam=False, trace=False, coverage=False)
    base.update(kw)
    return argparse.Namespace(**base)


def test_plan_parallel_ok_for_multi_file_web_module(module):
    tasks, reason = run_cli._plan_parallel(module / "case", module, _ns())
    assert reason is None and len(tasks) == 4


def test_plan_parallel_falls_back_for_single_file(module):
    tasks, reason = run_cli._plan_parallel(module / "case" / "top.xml", module, _ns())
    assert reason and "1 个用例文件" in reason


@pytest.mark.parametrize("attr,flag", [("cdp_endpoint", "--cdp"), ("trace", "--trace"), ("debug", "--debug")])
def test_plan_parallel_falls_back_for_single_process_flags(module, attr, flag):
    _, reason = run_cli._plan_parallel(module / "case", module, _ns(**{attr: ":9222" if attr == "cdp_endpoint" else True}))
    assert reason and flag in reason


def test_plan_parallel_falls_back_for_mobile_models(module):
    (module / "model" / "model.xml").write_text(
        '<models><model name="App" driver_type="android"></model></models>', encoding="utf-8")
    _, reason = run_cli._plan_parallel(module / "case", module, _ns())
    assert reason and "android" in reason


def test_plan_parallel_falls_back_for_app_navigate(module):
    (module / "case" / "b" / "three.xml").write_text(
        '<cases><case execute="是" id="TC1" title="x"><test_case>'
        '<test_step action="navigate" model="" data="app://android/com.demo"/></test_case></case></cases>',
        encoding="utf-8")
    _, reason = run_cli._plan_parallel(module / "case", module, _ns())
    assert reason and "b/three.xml" in reason
