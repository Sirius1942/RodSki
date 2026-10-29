"""测试套解析、归属裁决、能力聚合与编译清单（v11.11.0，CORE §7.9）。"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from rodski.core.capability import (
    ANDROID,
    DESKTOP,
    IOS,
    WEB,
    CapabilityError,
    CapabilityResolver,
    navigate_target_capability,
    resolve_mobile_platform,
)
from rodski.core.plan_parser import PlanParser
from rodski.core.plan_suites import (
    IMPLICIT_SUITE_ID,
    MANIFEST_SCHEMA,
    assign_suites,
    check_plan_structure,
    compile_plan,
    format_summary,
)

MODELS = (
    '<?xml version="1.0" encoding="UTF-8"?>\n<models>\n'
    '  <model name="WebPage" type="ui"/>\n'
    '  <model name="Api" type="interface"/>\n'
    '  <model name="Db" type="database"/>\n'
    '  <model name="AndroidScreen" type="ui" driver_type="android"/>\n'
    '  <model name="IosScreen" type="ui" driver_type="ios"/>\n'
    '  <model name="MobileScreen" type="ui" driver_type="mobile"/>\n'
    '  <model name="WinApp" type="ui" driver_type="windows"/>\n'
    '</models>\n'
)


def _case(case_id, models, execute="是"):
    steps = "".join(f'      <test_step action="verify" model="{m}" data="D1"/>\n' for m in models)
    return (f'  <case execute="{execute}" id="{case_id}" title="{case_id}" component_type="界面" priority="P0">\n'
            f'    <test_case>\n{steps}    </test_case>\n  </case>\n')


def _cases_file(path: Path, *cases: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('<?xml version="1.0" encoding="UTF-8"?>\n<cases>\n' + "".join(cases) + '</cases>\n',
                    encoding="utf-8")


@pytest.fixture
def module(tmp_path):
    for name in ("plan", "case", "model", "data"):
        (tmp_path / name).mkdir()
    (tmp_path / "model" / "model.xml").write_text(MODELS, encoding="utf-8")
    _cases_file(tmp_path / "case" / "order" / "create.xml", _case("O1", ["WebPage"]), _case("O2", ["Api", "Db"]))
    _cases_file(tmp_path / "case" / "order" / "deep" / "special.xml", _case("S1", ["WebPage"]))
    _cases_file(tmp_path / "case" / "admin" / "manage.xml", _case("M1", ["WebPage"]))
    _cases_file(tmp_path / "case" / "app.xml", _case("A1", ["AndroidScreen", "WebPage", "Db"]),
                _case("I1", ["IosScreen"]))
    return tmp_path


def _plan(module, plan_id, body, attrs=""):
    path = module / "plan" / f"{plan_id}.xml"
    path.write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<test_plan id="{plan_id}" title="t" kind="suite"{attrs}>\n{body}</test_plan>\n', encoding="utf-8")
    return path


class TestPlanParserSuites:
    def test_suites_parsed_and_flattened(self, module):
        path = _plan(module, "p", '  <suite id="order" title="下单" tags="冒烟, 核心">\n'
                                  '    <case_dir path="order"/>\n'
                                  '    <case file="admin/manage.xml" id="M1"/>\n'
                                  '  </suite>\n'
                                  '  <suite id="off" execute="否"><case file="app.xml" id="I1"/></suite>\n',
                     ' max_parallel="2"')
        plan = PlanParser(str(path)).parse_plan()

        assert [s["id"] for s in plan["suites"]] == ["order", "off"]
        order = plan["suites"][0]
        assert order["title"] == "下单" and order["tags"] == ["冒烟", "核心"] and order["execute"] == "是"
        assert plan["suites"][1]["execute"] == "否"
        assert plan["max_parallel"] == 2
        # 套内条目平铺进 cases / case_dirs，带 suite 键
        assert {(c["id"], c["suite"]) for c in plan["cases"]} == {("M1", "order"), ("I1", "off")}
        assert [(d["path"], d["suite"]) for d in plan["case_dirs"]] == [("order", "order")]

    def test_plan_without_suites_keeps_v1110_shape(self, module):
        plan = PlanParser(str(_plan(module, "p", '  <case_dir path="order"/>\n'))).parse_plan()
        assert "suites" not in plan and "max_parallel" not in plan

    def test_mixing_suite_and_top_level_case_rejected(self, module):
        path = _plan(module, "p", '  <suite id="a"><case_dir path="order"/></suite>\n'
                                  '  <case file="admin/manage.xml" id="M1"/>\n')
        with pytest.raises(Exception):
            PlanParser(str(path)).parse_plan()


class TestPlanStructure:
    def test_suite_only_for_kind_suite(self):
        errors = check_plan_structure({"id": "p", "kind": "load", "suites": [{"id": "a"}], "max_parallel": 2})
        assert len(errors) == 2 and all("kind=\"suite\"" in e for e in errors)

    def test_default_execute_cannot_combine_with_suites(self):
        errors = check_plan_structure({"id": "p", "kind": "suite", "default_execute": "是", "suites": [{"id": "a"}]})
        assert errors and "default_execute" in errors[0]

    def test_duplicate_suite_id(self):
        errors = check_plan_structure({"id": "p", "kind": "suite", "suites": [{"id": "a"}, {"id": "a"}]})
        assert errors == ["计划 p: 测试套 id 重复: a"]


def _c(case_file, case_id):
    return {"case_file": case_file, "case_id": case_id}


class TestAssignSuites:
    CASES = [_c("order/create.xml", "O1"), _c("order/deep/special.xml", "S1"), _c("admin/manage.xml", "M1")]

    def test_explicit_case_beats_case_dir(self):
        plan = {"suites": [
            {"id": "order", "case_dirs": [{"path": "order"}], "cases": []},
            {"id": "special", "cases": [{"file": "order/deep/special.xml", "id": "S1"}], "case_dirs": []},
        ]}
        assignment, errors = assign_suites(plan, self.CASES)
        assert errors == []
        assert assignment == {"order/create.xml::O1": "order", "order/deep/special.xml::S1": "special"}

    def test_longer_case_dir_beats_shorter(self):
        plan = {"suites": [
            {"id": "all", "case_dirs": [{"path": ""}], "cases": []},
            {"id": "order", "case_dirs": [{"path": "order"}], "cases": []},
            {"id": "deep", "case_dirs": [{"path": "order/deep/"}], "cases": []},
        ]}
        assignment, errors = assign_suites(plan, self.CASES)
        assert errors == []
        assert assignment == {"order/create.xml::O1": "order", "order/deep/special.xml::S1": "deep",
                              "admin/manage.xml::M1": "all"}

    def test_same_rank_in_two_suites_is_error(self):
        plan = {"suites": [
            {"id": "a", "cases": [{"file": "admin/manage.xml", "id": "M1"}], "case_dirs": []},
            {"id": "b", "cases": [{"id": "M1"}], "case_dirs": []},
        ]}
        assignment, errors = assign_suites(plan, self.CASES)
        assert "admin/manage.xml::M1" not in assignment
        assert len(errors) == 1 and "a, b" in errors[0] and "显式 <case>" in errors[0]

    def test_disabled_case_dir_does_not_claim(self):
        plan = {"suites": [
            {"id": "a", "case_dirs": [{"path": "admin", "execute": "否"}], "cases": []},
            {"id": "b", "case_dirs": [{"path": "admin"}], "cases": []},
        ]}
        assignment, errors = assign_suites(plan, self.CASES)
        assert errors == [] and assignment == {"admin/manage.xml::M1": "b"}


def _step(**attrs):
    return ET.Element("test_step", attrs)


class TestCapability:
    def test_driver_type_mapping(self, module):
        r = CapabilityResolver(module)
        assert r.step_capability(_step(action="verify", model="WebPage")) == WEB
        assert r.step_capability(_step(action="send", model="Api")) == WEB
        assert r.step_capability(_step(action="DB", model="Db")) == WEB
        assert r.step_capability(_step(action="type", model="AndroidScreen")) == ANDROID
        assert r.step_capability(_step(action="type", model="IosScreen")) == IOS
        assert r.step_capability(_step(action="type", model="WinApp")) == DESKTOP
        assert r.step_capability(_step(action="wait", model="", data="1")) is None

    def test_navigate_target(self):
        assert navigate_target_capability("app://android/com.x/.Main") == ANDROID
        assert navigate_target_capability("app://ios/com.x") == IOS
        assert navigate_target_capability("http://x") == WEB
        assert navigate_target_capability("") is None

    def test_navigate_globalvalue_reference_resolved(self, module):
        (module / "data" / "globalvalue.xml").write_text(
            '<globalvalue><group name="Mobile"><var name="AppTarget" value="app://android/com.x"/></group>'
            '</globalvalue>', encoding="utf-8")
        step = _step(action="navigate", model="", data="GlobalValue.Mobile.AppTarget")
        assert CapabilityResolver(module).step_capability(step) == ANDROID

    def test_mobile_driver_type_needs_platform(self, module):
        step = _step(action="type", model="MobileScreen")
        with pytest.raises(CapabilityError, match="Mobile.Platform"):
            CapabilityResolver(module).step_capability(step)
        assert CapabilityResolver(module, platform="ios").step_capability(step) == IOS
        (module / "data" / "globalvalue.xml").write_text(
            '<globalvalue><group name="Mobile"><var name="Platform" value="Android"/></group></globalvalue>',
            encoding="utf-8")
        assert resolve_mobile_platform(module) == ANDROID
        assert CapabilityResolver(module).step_capability(step) == ANDROID

    def test_case_requires_aggregates_whole_case(self, module):
        case = ET.fromstring(
            '<case id="X"><pre_process><test_step action="navigate" model="" data="http://x"/></pre_process>'
            '<test_case><if condition="1"><test_step action="type" model="AndroidScreen" data="D"/></if>'
            '<test_step action="type" model="WinApp" data="D"/></test_case></case>')
        info = CapabilityResolver(module).case_requires(case, "x.xml")
        assert info["requires"] == [ANDROID, DESKTOP, WEB]
        assert info["os_tags"] == {"os:windows"}
        assert info["steps"] == 3

    def test_business_call_steps_counted(self, module):
        (module / "business").mkdir()
        (module / "business" / "login.xml").write_text(
            '<business_models><business_model id="AppLogin">'
            '<node id="n1"><test_step action="type" model="AndroidScreen" data="D"/></node>'
            '<flow id="ok" path="n1"/></business_model></business_models>', encoding="utf-8")
        refs = set()
        case = ET.fromstring('<case id="X"><test_case><business_call ref="AppLogin" flow="ok"/>'
                             '<test_step action="verify" model="WebPage" data="D"/></test_case></case>')
        info = CapabilityResolver(module).case_requires(case, "x.xml", refs)
        assert info["requires"] == [ANDROID, WEB] and refs == {"AppLogin"}

        missing = ET.fromstring('<case id="Y"><test_case><business_call ref="Nope"/></test_case></case>')
        with pytest.raises(CapabilityError, match="Nope"):
            CapabilityResolver(module).case_requires(missing)


class TestCompilePlan:
    SUITES = ('  <suite id="order" title="下单"><case_dir path="order"/></suite>\n'
              '  <suite id="admin" tags="后台"><case_dir path="admin"/>'
              '<case file="app.xml" id="A1"/></suite>\n'
              '  <suite id="ios" execute="否"><case file="app.xml" id="I1"/></suite>\n')

    def test_manifest_for_suites(self, module):
        _plan(module, "p", self.SUITES, ' max_parallel="2"')
        compiled = compile_plan(module, "@p")

        assert compiled.ok, compiled.errors
        m = compiled.manifest
        assert m["schema"] == MANIFEST_SCHEMA and m["plan_id"] == "p"
        assert m["max_parallel"] == 2 and m["implicit_suite"] is False
        suites = {s["id"]: s for s in m["suites"]}
        assert list(suites) == ["order", "admin", "ios"]
        assert [c["case_id"] for c in suites["order"]["cases"]] == ["O1", "O2", "S1"]
        assert suites["order"]["requires"] == [WEB]
        # 混合用例 A1（android + web + db）整条归 admin 套 → 套需要 android 与 web
        assert suites["admin"]["requires"] == [ANDROID, WEB] and suites["admin"]["tags"] == ["后台"]
        assert suites["ios"]["execute"] is False and suites["ios"]["cases"] == []
        assert m["skipped"] == [{"case_file": "app.xml", "case_id": "I1", "reason": "suite_execute_false",
                                 "suite_id": "ios"}]
        # app.xml 两条用例分属 admin / ios → WARN
        assert any("app.xml" in w for w in m["warnings"])
        assert compiled.suite("admin")["weight"] == 4

    def test_implicit_suite(self, module):
        _plan(module, "p", '  <case_dir path="order"/>\n')
        m = compile_plan(module, "p").manifest
        assert m["implicit_suite"] is True
        assert [s["id"] for s in m["suites"]] == [IMPLICIT_SUITE_ID]
        assert m["max_parallel"] is None

    def test_digest_tracks_plan_cases_and_model_only(self, module):
        _plan(module, "p", self.SUITES)
        first = compile_plan(module, "p").digest
        assert first.startswith("sha256:") and compile_plan(module, "p").digest == first

        (module / "data" / "globalvalue.xml").write_text("<globalvalue/>", encoding="utf-8")
        (module / "data" / "data.sqlite").write_bytes(b"x")
        assert compile_plan(module, "p").digest == first

        # 不在计划中的用例文件改动不影响 digest
        _cases_file(module / "case" / "unused" / "x.xml", _case("U1", ["WebPage"]))
        assert compile_plan(module, "p").digest == first

        _cases_file(module / "case" / "admin" / "manage.xml", _case("M1", ["WebPage", "WebPage"]))
        assert compile_plan(module, "p").digest != first

    def test_cross_platform_suite_needs_flag(self, module):
        _plan(module, "p", '  <suite id="both"><case file="app.xml" id="A1"/>'
                           '<case file="app.xml" id="I1"/></suite>\n')
        compiled = compile_plan(module, "p")
        assert not compiled.ok and "测试套 both" in compiled.errors[0]
        assert compiled.error_payload()["errors"] == compiled.errors
        assert compile_plan(module, "p", allow_cross_platform=True).ok

    def test_structure_errors_collected_not_raised(self, module):
        _plan(module, "p", '  <suite id="a"><case_dir path="admin"/></suite>\n'
                           '  <suite id="b"><case_dir path="admin"/></suite>\n')
        compiled = compile_plan(module, "p")
        assert not compiled.ok and "被多个测试套" in compiled.errors[0]
        assert format_summary(compiled).startswith("[ERROR]")

    def test_missing_plan_reported(self, module):
        compiled = compile_plan(module, "nope")
        assert not compiled.ok and "解析失败" in compiled.errors[0]

    def test_text_summary(self, module):
        _plan(module, "p", self.SUITES, ' max_parallel="2"')
        text = format_summary(compile_plan(module, "p"))
        assert "max_parallel: 2" in text
        assert "- admin: 用例 2" in text and "requires [android, web]" in text
        assert "[停用]" in text and "[WARN]" in text


class _Args:
    def __init__(self, **kw):
        self.suite = None
        self.expect_digest = None
        self.platform = None
        self.allow_cross_platform_plan = False
        self.__dict__.update(kw)


class TestRunSuitePrecheck:
    WEB_SUITES = ('  <suite id="order"><case_dir path="order"/></suite>\n'
                  '  <suite id="admin"><case_dir path="admin"/></suite>\n'
                  '  <suite id="off" execute="否"><case file="app.xml" id="I1"/></suite>\n')

    def _precheck(self, module, plan_id, **kw):
        from rodski.rodski_cli.run import _precheck_plan_suites
        args = _Args(**kw)
        path = module / "plan" / f"{plan_id}.xml" if plan_id else None
        return _precheck_plan_suites(path, module, args), args

    def test_suite_filter_and_meta(self, module):
        _plan(module, "p", self.WEB_SUITES, ' max_parallel="2"')
        errors, args = self._precheck(module, "p", suite="admin,admin")
        assert errors == []
        assert args._suite_filter == ["admin"]
        assert args._plan_meta == {"plan_id": "p", "suites": "admin",
                                   "digest": args._compiled_plan.digest}

    def test_no_filter_lists_all_suites(self, module):
        _plan(module, "p", self.WEB_SUITES)
        errors, args = self._precheck(module, "p")
        assert errors == [] and args._suite_filter is None
        assert args._plan_meta["suites"] == "order,admin,off"

    def test_suite_errors(self, module):
        _plan(module, "p", self.WEB_SUITES)
        errors, _ = self._precheck(module, "p", suite="nope,off")
        assert any("测试套不存在: nope" in e for e in errors)
        assert any("测试套 off 已停用" in e for e in errors)
        assert self._precheck(module, "p", suite=" , ")[0] == ["--suite 需要至少一个测试套 id"]
        assert "只能与测试计划" in self._precheck(module, None, suite="a")[0][0]

    def test_expect_digest(self, module):
        _plan(module, "p", self.WEB_SUITES)
        digest = compile_plan(module, "p").digest
        assert self._precheck(module, "p", expect_digest=digest)[0] == []
        errors, _ = self._precheck(module, "p", expect_digest="sha256:0")
        assert errors and "digest 不一致" in errors[0]

    def test_implicit_plan_untouched(self, module):
        _plan(module, "p", '  <case_dir path="order"/>\n')
        errors, args = self._precheck(module, "p")
        assert errors == [] and args._compiled_plan is None and args._plan_meta == {"plan_id": "p"}


class TestMergeSuiteResults:
    def test_order_disabled_skip_and_worker_error(self, module):
        from rodski.core.parallel_runner import SuiteTask, merge_suite_results
        suites = [
            SuiteTask(suite_id="order", execute=True, weight=2,
                      cases=[{"case_file": "order/create.xml", "case_id": "O1"},
                             {"case_file": "order/create.xml", "case_id": "O2"}]),
            SuiteTask(suite_id="off", execute=False, weight=0, cases=[],
                      skipped=[{"case_file": "app.xml", "case_id": "I1", "reason": "suite_execute_false"}]),
            SuiteTask(suite_id="admin", execute=True, weight=1,
                      cases=[{"case_file": "admin/manage.xml", "case_id": "M1"}]),
        ]
        outputs = [
            # admin 的 worker 先结束；合并结果仍按计划中的套顺序
            {"suite_filter": ["admin"], "results": [{"case_id": "M1", "case_file": "admin/manage.xml",
                                                     "status": "PASS", "suite_id": "admin"}]},
            {"suite_filter": ["order"], "worker_id": 2, "error": "boom",
             "results": [{"case_id": "O1", "case_file": "order/create.xml", "status": "PASS",
                          "suite_id": "order"}]},
        ]
        merged = merge_suite_results(suites, outputs, module)

        assert [(r["case_id"], r["status"], r["suite_id"]) for r in merged] == [
            ("O1", "PASS", "order"), ("O2", "FAIL", "order"),
            ("I1", "SKIP", "off"), ("M1", "PASS", "admin"),
        ]
        assert merged[1]["error_type"] == "WorkerError" and "boom" in merged[1]["error"]
        assert merged[2]["title"] == "I1" and merged[2]["error"] == "suite_execute_false"


class TestRunActionCapability:
    def test_run_model_is_fun_project_not_web(self, module):
        r = CapabilityResolver(module)
        assert r.step_capability(_step(action="run", model="calc", data="add.py")) is None
        assert r.step_capability(_step(action="run", model="", data="mock_route(x)")) is None


MIXED_SUITES = ('  <suite id="order"><case_dir path="order"/></suite>\n'
                '  <suite id="admin"><case_dir path="admin"/></suite>\n'
                '  <suite id="app"><case file="app.xml" id="A1"/></suite>\n'
                '  <suite id="off" execute="否"><case file="app.xml" id="I1"/></suite>\n')


class TestDryRunSuites:
    def _dry_run(self, module, capsys, suite_filter=None, body=MIXED_SUITES):
        from rodski.rodski_cli.run import _handle_dry_run
        path = _plan(module, "p", body)
        code = _handle_dry_run(module / "case", module / "model" / "model.xml", False, plan_path=path,
                               module_dir=module, suite_filter=suite_filter)
        return code, capsys.readouterr().out

    def test_selection_follows_suite_assignment(self, module, capsys):
        # special 套的 case_dir 与显式 <case> 都选中 S1：S1 只出现一次且归 special（不再按 order 重复）
        body = ('  <suite id="order"><case_dir path="order"/></suite>\n'
                '  <suite id="special"><case_dir path="order/deep"/><case file="order/deep/special.xml" id="S1"/>'
                '</suite>\n'
                '  <suite id="off" execute="否"><case file="app.xml" id="I1"/></suite>\n')
        code, out = self._dry_run(module, capsys, body=body)
        assert code == 0, out
        assert out.count("order/deep/special.xml::S1") == 1
        assert "[special] order/deep/special.xml::S1" in out
        selected = out.split("Selected:")[1].split("Skipped:")[0]
        assert "app.xml::I1" not in selected
        assert "[off] app.xml::I1 (suite_execute_false)" in out

    def test_suite_filter(self, module, capsys):
        code, out = self._dry_run(module, capsys, suite_filter=["admin"])
        assert code == 0, out
        selected = out.split("Selected:")[1].split("Skipped:")[0]
        assert "[admin] admin/manage.xml::M1" in selected
        assert "order/" not in selected and "app.xml" not in selected


class TestWorkersWithSuites:
    def _args(self, module, **kw):
        from rodski.rodski_cli.run import _precheck_plan_suites
        args = _Args(model=None, cdp_endpoint=None, insert_steps=None, debug=False, roam=False,
                     trace=False, coverage=False, _executor_hooks={}, **kw)
        assert _precheck_plan_suites(module / "plan" / "p.xml", module, args) == []
        return args

    def test_capabilities_only_from_selected_suites(self, module):
        from rodski.rodski_cli.run import _plan_parallel
        _plan(module, "p", MIXED_SUITES)
        path = module / "plan" / "p.xml"

        tasks, reason = _plan_parallel(module / "case", module, self._args(module), path)
        assert tasks == [] and "android" in reason

        tasks, reason = _plan_parallel(module / "case", module, self._args(module, suite="order,admin"), path)
        assert reason is None and [t["suite_id"] for t in tasks] == ["order", "admin"]

    def test_model_override_does_not_bypass_suites(self, module):
        from rodski.rodski_cli.run import _plan_parallel
        _plan(module, "p", MIXED_SUITES)
        args = self._args(module, suite="order,admin")
        args.model = str(module / "model" / "model.xml")
        tasks, reason = _plan_parallel(module / "case", module, args, module / "plan" / "p.xml")
        assert tasks == [] and "--model" in reason

    def test_auto_queue_only_when_selected_suites_need_device(self, module):
        from rodski.rodski_cli.run import _selected_suites_need_device
        _plan(module, "p", MIXED_SUITES)
        assert _selected_suites_need_device(self._args(module)) is True
        assert _selected_suites_need_device(self._args(module, suite="order,admin")) is False
        assert _selected_suites_need_device(_Args()) is True   # 没有编译清单：保持 v11.10 行为
