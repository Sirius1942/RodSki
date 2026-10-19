#!/usr/bin/env python3
"""data_rules 模块验收脚本：数据规则（F026 F027 F049 F050 F055 F056 F059 F060 F065 F086）。

用法（仓库根目录）:
    python3 rodski-demo/local/data_rules/run_acceptance.py             # 全部检查项
    python3 rodski-demo/local/data_rules/run_acceptance.py F027 F050   # 只跑指定功能（前缀匹配检查项编号）
    python3 rodski-demo/local/data_rules/run_acceptance.py --strict    # KNOWN 也算失败

判定输出每行一项：PASS / KNOWN（已登记的框架与文档不符，见 README.md「KNOWN」）/ FAIL / FIXED（登记为 KNOWN
但本次通过，请从 KNOWN 表移除）。退出码：存在 FAIL（--strict 时含 KNOWN）为 1，否则 0。

执行方式：真实调用 `python3 rodski/cli_main.py`（headless Chromium）；页面与接口由 fun/mock_server.py
（127.0.0.1:18121）提供，不依赖 :8000。会改 data/case 的检查一律在临时副本中进行，模块本身不被修改。
"""
from __future__ import annotations

import functools
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CLI = REPO / "rodski" / "cli_main.py"
SCHEMAS = REPO / "rodski" / "schemas"
PY = os.environ.get("RODSKI_PY") or sys.executable
PASSWORD = "Zq7SecretPw"
RUNTIME = HERE / ".runtime"

sys.path.insert(0, str(HERE / "data"))
import init_data  # noqa: E402  (NEGATIVE_F056 负向数据)

# ── KNOWN：框架行为与文档不符（保留用例、不改框架）。键 = 检查项编号 ─────────────
KNOWN: Dict[str, str] = {
    "F027-04": "type 的 Return / execution_summary.json return_value 含 .Password 字段明文",
    "F055-03": "Return 历史不按用例重置：非首个用例中 ${Return[0]} 不是本用例第一步",
}


# ── 基础设施 ────────────────────────────────────────────────────
class Run:
    def __init__(self, proc: subprocess.CompletedProcess, run_dir: Optional[Path]):
        self.code = proc.returncode
        self.out = (proc.stdout or "") + (proc.stderr or "")
        self.run_dir = run_dir

    def results(self) -> Dict[str, Dict[str, str]]:
        if not self.run_dir or not (self.run_dir / "result.xml").is_file():
            return {}
        root = ET.parse(self.run_dir / "result.xml").getroot()
        return {r.get("case_id", ""): {"status": r.get("status", ""), "error": r.get("error_message", ""),
                                       "file": r.get("case_file", "")} for r in root.iter("result")}

    def status(self, case_id: str) -> str:
        return self.results().get(case_id, {}).get("status", "<未执行>")

    def error(self, case_id: str) -> str:
        return self.results().get(case_id, {}).get("error", "")

    def text(self, name: str) -> str:
        p = (self.run_dir / name) if self.run_dir else None
        return p.read_text(encoding="utf-8", errors="replace") if p and p.is_file() else ""


def cli(*args: str, cwd: Path = REPO, timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run([PY, str(CLI), *args], cwd=str(cwd), capture_output=True, text=True, timeout=timeout)


def run_cases(target: Path, module: Path = HERE, *extra: str) -> Run:
    result_dir = module / "result"
    before = set(result_dir.iterdir()) if result_dir.is_dir() else set()
    proc = cli("run", str(target), "--headless", *extra)
    after = set(result_dir.iterdir()) if result_dir.is_dir() else set()
    new_dirs = sorted(p for p in after - before if p.is_dir())
    return Run(proc, new_dirs[-1] if new_dirs else None)


def xmllint(xsd: str, path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["xmllint", "--noout", "--schema", str(SCHEMAS / xsd), str(path)],
                          capture_output=True, text=True)


def expect(cond, msg: str, ctx: str = "") -> None:
    if not cond:
        raise AssertionError(msg + (f"\n      --- 输出末尾 ---\n      {ctx[-1500:]}" if ctx else ""))


def out_of(p: subprocess.CompletedProcess) -> str:
    return (p.stdout or "") + (p.stderr or "")


_TMP_ROOT = Path(tempfile.mkdtemp(prefix="rodski_data_rules_"))


def temp_module(name: str) -> Path:
    """复制本模块到临时目录（不含 result/.runtime），会改 data/case 的检查只动副本。"""
    dst = _TMP_ROOT / name / "data_rules"
    shutil.copytree(HERE, dst, ignore=shutil.ignore_patterns("result", ".runtime", "__pycache__"))
    return dst


def ensure_mock() -> None:
    p = subprocess.run([PY, str(HERE / "fun" / "mock_server.py"), "ensure"], capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit(f"mock 启动失败: {out_of(p)}")


def stop_mock() -> None:
    subprocess.run([PY, str(HERE / "fun" / "mock_server.py"), "stop"], capture_output=True, text=True)


@functools.lru_cache(maxsize=None)
def main_run() -> Run:
    """整目录执行一次 case/，多数检查项共用。"""
    return run_cases(HERE / "case")


def expect_case(run: Run, case_id: str, status: str = "PASS") -> None:
    expect(run.status(case_id) == status,
           f"{case_id} 期望 {status}，实际 {run.status(case_id)}：{run.error(case_id)[:600]}")


def mock_records(tag: str) -> List[dict]:
    log = RUNTIME / "requests.jsonl"
    if not log.is_file():
        return []
    recs = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [r for r in recs if r.get("tag") == tag]


# ── F086 XML Schema ────────────────────────────────────────────
def f086_01():
    """本模块全部 XML 通过 case.xsd / model.xsd / plan.xsd / globalvalue.xsd 校验"""
    targets = [("case.xsd", p) for p in sorted((HERE / "case").rglob("*.xml"))]
    targets += [("case.xsd", HERE / "fun/negative/f056_verify_return_forbidden.xml"),
                ("model.xsd", HERE / "model/model.xml"),
                ("globalvalue.xsd", HERE / "data/globalvalue.xml")]
    targets += [("plan.xsd", p) for p in sorted((HERE / "plan").glob("*.xml"))]
    expect(any(x == "plan.xsd" for x, _ in targets), "plan/ 下应至少有一个计划文件")
    bad = [f"{p.relative_to(HERE)}: {out_of(r).strip()}" for x, p in targets for r in [xmllint(x, p)] if r.returncode]
    expect(not bad, "以下 XML 未通过 Schema 校验:\n      " + "\n      ".join(bad))


def f086_02():
    """负向样例：非法关键字 / 旧版定位器 / 缺必填属性的 plan / metadata 位置错误，xmllint 均失败"""
    neg = HERE / "fun" / "negative"
    for xsd, name in [("case.xsd", "invalid_case.xml"), ("model.xsd", "invalid_model.xml"),
                      ("plan.xsd", "invalid_plan.xml"), ("case.xsd", "metadata_after_pre.xml")]:
        r = xmllint(xsd, neg / name)
        expect(r.returncode != 0 and "fails to validate" in out_of(r), f"{name} 应不通过 {xsd}，实际: {out_of(r)}")


def f086_03():
    """非法 case XML 放进 case/ 时 rodski run 拒绝执行（SKI204 case.xsd），退出码非 0"""
    tmp = temp_module("f086")
    shutil.copy(HERE / "fun/negative/invalid_case.xml", tmp / "case/zz_invalid.xml")
    r = run_cases(tmp / "case/zz_invalid.xml", tmp)
    expect(r.code != 0 and "SKI204" in r.out and "case.xsd" in r.out, f"应报 SKI204 case.xsd，退出码 {r.code}", r.out)


def f086_04():
    """plan/data_rules_smoke.xml 引用有效（rodski plan validate）"""
    p = cli("plan", "validate", "data_rules_smoke", cwd=HERE)
    expect(p.returncode == 0, f"plan validate 退出码 {p.returncode}", out_of(p))


# ── F027 .Password ─────────────────────────────────────────────
@functools.lru_cache(maxsize=None)
def pwd_run() -> Run:
    """单独执行 f027（execution_summary.json 只保留最后一个用例，单独跑才能看到 type 步骤）。"""
    return run_cases(HERE / "case/f027_password_mask.xml")


def f027_01():
    """.Password 后缀在输入前去掉：页面收到 11 位密码，字符码和与明文一致"""
    expect_case(main_run(), "F027_PASSWORD")


def f027_02():
    """日志对密码字段显示 ***"""
    r = pwd_run()
    expect_case(r, "F027_PASSWORD")
    expect(re.search(r"password: id=pwd <- '\*\*\*'", r.text("execution.log")), "execution.log 中 password 输入应显示 ***")


def f027_03():
    """明文不出现在 execution.log / result.xml / 控制台输出"""
    r = pwd_run()
    hits = []
    for name in ("execution.log", "result.xml"):
        lines = [l for l in r.text(name).splitlines() if PASSWORD in l]
        if lines:
            hits.append(f"{name}: {len(lines)} 行，如 {lines[0].replace(PASSWORD, '<明文>')[:220]}")
    if PASSWORD in r.out:
        hits.append("控制台输出")
    expect(not hits, "明文泄露:\n      " + "\n      ".join(hits))


def f027_04():
    """type 步骤的 Return（execution_summary.json return_value）不含明文"""
    r = pwd_run()
    summary = json.loads(r.text("execution_summary.json") or "{}")
    steps = [s for s in summary.get("steps", []) if s.get("action") == "type"]
    expect(steps, "execution_summary.json 中没有 type 步骤")
    rv = json.dumps(steps[0].get("return_value"), ensure_ascii=False)
    expect(PASSWORD not in rv, f"type 的 Return 含明文: {rv.replace(PASSWORD, '<明文>')}")


# ── F026 BLANK / NULL / NONE ───────────────────────────────────
def f026_01():
    """UI type：BLANK / NULL / NONE 字段跳过（预填 keep1~3 不变），普通值正常输入"""
    expect_case(main_run(), "F026_UI_TYPE")


def f026_02():
    """UI type：空值字段跳过（预填 keep5 不变）"""
    expect_case(main_run(), "F026_UI_TYPE_EMPTY")


def f026_03():
    """UI verify：BLANK / NONE 跳过该字段（实际 AAA / BBB 不参与比较）"""
    expect_case(main_run(), "F026_UI_VERIFY")


def f026_04():
    """send：BLANK 发空串、NULL 发 null、NONE 不发送（verify 回显 + mock 原始请求体双重确认）"""
    expect_case(main_run(), "F026_SEND")
    recs = mock_records("special")
    expect(recs, "mock 未收到 /echo/special 请求")
    body = json.loads(recs[-1]["raw"])
    expect(body == {"f_blank": "", "f_null": None, "f_text": "hello"}, f"原始请求体不符: {recs[-1]['raw']}")


def f026_05():
    """接口 verify：BLANK 期望空串、NULL 期望 null"""
    expect_case(main_run(), "F026_API_VERIFY")


def f026_06():
    """接口 verify：NONE 跳过验证（实际 xyz）"""
    expect_case(main_run(), "F026_API_VERIFY_NONE")


def f026_07():
    """接口 verify：BLANK 期望空串，实际 hello 时失败（expect_fail，失败字段为 v_text）"""
    r = main_run()
    expect_case(r, "F026_API_VERIFY_BLANK_NEG")
    err = r.error("F026_API_VERIFY_BLANK_NEG")
    expect("[预期失败]" in err and "v_text(期望=''" in err and "v_other" not in err, f"失败原因不符: {err[:400]}")


def f026_08():
    """DB verify：BLANK 跳过（实际 aaa）、NULL 期望 null"""
    expect_case(main_run(), "F026_DB_VERIFY")


def f026_09():
    """DB verify：NONE 跳过验证（实际 zzz）"""
    expect_case(main_run(), "F026_DB_VERIFY_NONE")


# ── F055 Return / 表名.DataID.字段名 ──────────────────────────
def f055_01():
    """数据表字段值中 ${Return[-2]} / ${Return[-1]} / 表名.DataID.字段名（含前后拼接）解析正确"""
    expect_case(main_run(), "F055_API_REFS")
    recs = mock_records("ref")
    expect(recs and recs[-1]["body"] == {"r_m2": "second", "r_m1": "third", "ref": "alice",
                                         "ref_mixed": "pre-new4-post"},
           f"mock 收到的请求体不符: {recs[-1]['body'] if recs else None}")


def f055_02():
    """UI type 字段值引用 ${Return[-1]}；UI _verify 期望值引用 ${Return[-2]}（跨源比对，允许）"""
    expect_case(main_run(), "F055_UI_CROSS")


def f055_03():
    """${Return[0]} = 本用例第一步返回值（用例不是本次运行的第一个用例时）"""
    expect_case(main_run(), "F055_RETURN0")


def f055_04():
    """${Return[0]}：该用例是本次运行唯一用例时取到第一步返回值"""
    r = run_cases(HERE / "case/f055_return_refs.xml", HERE, "--case-id", "F055_RETURN0")
    expect_case(r, "F055_RETURN0")


# ── F059 生成函数 ──────────────────────────────────────────────
def f059_01():
    """random / date / timestamp / timestamp_ms / timestamp36 / date offset / 拼接 / $${ 转义：格式与范围正确，两次求值不同"""
    expect_case(main_run(), "F059_GENERATORS")


# ── F060 生成函数写在 Case data 属性 ───────────────────────────
def f060_01():
    """set 中纯函数 toUpperCase 允许并得到 ABC"""
    expect_case(main_run(), "F060_PURE_OK")


def f060_02():
    """set 中 $${random(...)} 转义：不报错，值为字面量 ${random(int, 1, 9)}"""
    expect_case(main_run(), "F060_SET_ESCAPE")


def f060_03():
    """set / navigate 的 data 属性中写 random / date / timestamp36 报错（失败原因为生成函数规则）"""
    r = main_run()
    for cid, fn in [("F060_SET_RANDOM", "random"), ("F060_SET_DATE", "date"),
                    ("F060_SET_TS36", "timestamp36"), ("F060_NAVIGATE_RANDOM", "random")]:
        expect_case(r, cid)
        err = r.error(cid)
        expect("[预期失败]" in err and "只能写在 data.sqlite 字段值中" in err and f"${{{fn}(" in err,
               f"{cid} 失败原因不符: {err[:300]}")


# ── F065 metadata ──────────────────────────────────────────────
def f065_01():
    """带 6 个 metadata 属性的用例通过 case.xsd，且 metadata 位于 pre_process 之前"""
    f = HERE / "case/f065_metadata.xml"
    expect(xmllint("case.xsd", f).returncode == 0, "f065_metadata.xml 未通过 case.xsd")
    case = ET.parse(f).getroot().find("case")
    expect([c.tag for c in case][:2] == ["metadata", "pre_process"], "metadata 应位于 pre_process 之前")
    expect(set(case.find("metadata").attrib) == {"created_by", "created_at", "updated_by", "updated_at",
                                                  "success_rate", "last_run"}, "应包含文档列出的 6 个属性")


def f065_02():
    """metadata 只记录元信息：用例正常执行通过，执行后用例文件内容不变"""
    f = HERE / "case/f065_metadata.xml"
    before = hashlib.sha256(f.read_bytes()).hexdigest()
    r = run_cases(f)
    expect_case(r, "F065_METADATA")
    expect(hashlib.sha256(f.read_bytes()).hexdigest() == before, "执行后 f065_metadata.xml 被改写")


def f065_03():
    """metadata 放在 pre_process 之后：xmllint 失败，rodski run 报 SKI204"""
    expect(xmllint("case.xsd", HERE / "fun/negative/metadata_after_pre.xml").returncode != 0, "xmllint 应失败")
    tmp = temp_module("f065")
    shutil.copy(HERE / "fun/negative/metadata_after_pre.xml", tmp / "case/zz_meta.xml")
    r = run_cases(tmp / "case/zz_meta.xml", tmp)
    expect(r.code != 0 and "SKI204" in r.out and "metadata" in r.out, f"应报 SKI204（metadata），退出码 {r.code}", r.out)


# ── F049 rodski data 子命令 ────────────────────────────────────
DOC_DATA_CMDS = ["list", "schema", "show", "query", "validate", "import", "set", "add-row", "delete-row"]


def f049_01():
    """GUIDE §5.3.1 列出的 data 子命令在 CLI 中全部存在"""
    out = out_of(cli("data", "--help"))
    m = re.search(r"\{([a-z,\-]+)\}", out)
    have = set(m.group(1).split(",")) if m else set()
    missing = [c for c in DOC_DATA_CMDS if c not in have]
    expect(not missing, f"文档有而 CLI 无: {missing}（CLI: {sorted(have)}）")


def f049_02():
    """list：列出全部逻辑表及行数"""
    p = cli("data", "list", str(HERE))
    out = out_of(p)
    expect(p.returncode == 0, "data list 失败", out)
    for t, n in [("PwdForm", 1), ("FixedResult_verify", 3), ("BizDB", 3), ("GenAPI", 2)]:
        expect(re.search(rf"^\s*{t}\s+\({n} 行\)", out, re.M), f"应列出 {t}（{n} 行）", out)


def f049_03():
    """schema：列出逻辑表字段"""
    p = cli("data", "schema", str(HERE), "SpecForm")
    fields = re.findall(r"^\s{2}(\S+)\s*$", out_of(p), re.M)
    expect(p.returncode == 0 and set(fields) == {"f1", "f2", "f3", "f4", "f5", "dumpBtn"}, f"字段不符: {fields}", out_of(p))


def f049_04():
    """show：显示指定行（含 BLANK/NULL/NONE 与空值原样）"""
    p = cli("data", "show", str(HERE), "SpecForm", "S001")
    out = out_of(p)
    expect(p.returncode == 0 and "f1: BLANK" in out and "f2: NULL" in out and "f3: NONE" in out and "f4: new4" in out,
           "show 输出不符", out)
    p = cli("data", "show", str(HERE), "SpecForm", "NOPE")
    expect(p.returncode != 0 and "NOPE" in out_of(p), "不存在的 DataID 应报错", out_of(p))


def f049_05():
    """query --limit N：最多列出 N 行"""
    p = cli("data", "query", str(HERE), "FixedResult_verify", "--limit", "2")
    rows = re.findall(r"^\s{2}(V_\w+)\s", out_of(p), re.M)
    expect(p.returncode == 0 and len(rows) == 2, f"应只列 2 行，实际 {rows}", out_of(p))


def f049_06():
    """validate：本模块数据层校验通过"""
    p = cli("data", "validate", str(HERE))
    expect(p.returncode == 0 and "[OK]" in out_of(p), "data validate 应通过", out_of(p))


def f049_07():
    """import：data.xml 迁移入 data.sqlite；默认跳过已存在表，--overwrite 覆盖；data.xml 未删除时 run 报错"""
    tmp = temp_module("f049_import")
    xml = tmp / "data" / "data.xml"
    xml.write_text('<?xml version="1.0" encoding="UTF-8"?>\n<datatables>\n  <datatable name="ImportDemo">\n'
                   '    <row id="I001" remark="导入"><field name="a">v1</field><field name="b">BLANK</field></row>\n'
                   '  </datatable>\n</datatables>\n', encoding="utf-8")
    p = cli("data", "import", str(tmp))
    expect(p.returncode == 0 and "[OK] ImportDemo (1 行)" in out_of(p), "首次 import 应导入 ImportDemo", out_of(p))
    p = cli("data", "import", str(tmp))
    expect(p.returncode == 0 and "[SKIP] ImportDemo" in out_of(p), "再次 import 应跳过已存在表", out_of(p))
    xml.write_text(xml.read_text(encoding="utf-8").replace("v1", "v2"), encoding="utf-8")
    p = cli("data", "import", str(tmp), "--overwrite")
    expect(p.returncode == 0 and "[OK] ImportDemo" in out_of(p), "--overwrite 应覆盖", out_of(p))
    r = run_cases(tmp / "case/f065_metadata.xml", tmp)
    expect(r.code != 0 and "SKI203" in r.out and "data.xml" in r.out, "data.xml 存在时 run 应报 SKI203", r.out)
    xml.unlink()
    p = cli("data", "show", str(tmp), "ImportDemo", "I001")
    expect(p.returncode == 0 and "a: v2" in out_of(p) and "b: BLANK" in out_of(p), "导入值不符", out_of(p))


def f049_08():
    """add-row / set / delete-row 行级编辑直接改 data.sqlite；set 写错字段名报错并列出合法字段"""
    tmp = temp_module("f049_rows")
    m = str(tmp)
    p = cli("data", "add-row", m, "SpecText_verify", "V_NEW", "t1=AAA", "t2=BLANK", "t3=NONE", "--remark", "新增")
    expect(p.returncode == 0, "add-row（完整字段）应成功", out_of(p))
    expect("t1: AAA" in out_of(cli("data", "show", m, "SpecText_verify", "V_NEW")), "add-row 后 show 应可见")
    p = cli("data", "set", m, "SpecText_verify", "V_NEW", "t1=ZZZ")
    expect(p.returncode == 0 and "t1: ZZZ" in out_of(cli("data", "show", m, "SpecText_verify", "V_NEW")),
           "set 应修改字段值", out_of(p))
    p = cli("data", "set", m, "SpecText_verify", "V_NEW", "nope=1")
    expect(p.returncode != 0 and "nope" in out_of(p) and all(f in out_of(p) for f in ("t1", "t2", "t3")),
           "set 未知字段应报错并列出合法字段", out_of(p))
    p = cli("data", "delete-row", m, "SpecText_verify", "V_NEW")
    expect(p.returncode == 0 and cli("data", "show", m, "SpecText_verify", "V_NEW").returncode != 0,
           "delete-row 后该行应不存在", out_of(p))
    expect(cli("data", "validate", m).returncode == 0, "行级编辑后 data validate 应仍通过")


# ── F050 字段集合一致 ──────────────────────────────────────────
def f050_01():
    """add-row 缺字段：报错、列出缺少的字段、提示 BLANK/NULL/NONE，且不写入"""
    tmp = temp_module("f050_add")
    p = cli("data", "add-row", str(tmp), "SpecText_verify", "V_MISS", "t1=AAA")
    out = out_of(p)
    expect(p.returncode != 0 and "t2" in out and "t3" in out and "BLANK" in out and "NULL" in out and "NONE" in out,
           "缺字段应报错并提示 BLANK/NULL/NONE", out)
    expect(cli("data", "show", str(tmp), "SpecText_verify", "V_MISS").returncode != 0, "失败的 add-row 不应写入")


def f050_02():
    """data.sqlite 中某行缺字段：data validate 与 rodski run 均报错并提示 BLANK/NULL/NONE"""
    tmp = temp_module("f050_sqlite")
    with sqlite3.connect(tmp / "data/data.sqlite") as c:
        c.execute("INSERT INTO rs_row(table_name,data_id,remark) VALUES('SpecText_verify','V_BAD','')")
        c.execute("INSERT INTO rs_field VALUES('SpecText_verify','V_BAD','t1','AAA')")
    p = cli("data", "validate", str(tmp))
    expect(p.returncode != 0 and "V_BAD" in out_of(p) and "BLANK/NULL/NONE" in out_of(p), "validate 应报缺字段", out_of(p))
    r = run_cases(tmp / "case/f065_metadata.xml", tmp)
    expect(r.code != 0 and "V_BAD" in r.out and "BLANK/NULL/NONE" in r.out, "run 应因缺字段报错", r.out)


def f050_03():
    """data import 迁移字段不一致的 XML：须统一为固定字段集合（报错提示 BLANK/NULL/NONE，或导入结果通过 validate）"""
    tmp = temp_module("f050_import")
    (tmp / "data/data.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<datatables>\n  <datatable name="Ragged">\n'
        '    <row id="R001"><field name="a">1</field><field name="b">2</field></row>\n'
        '    <row id="R002"><field name="a">3</field></row>\n  </datatable>\n</datatables>\n', encoding="utf-8")
    p = cli("data", "import", str(tmp))
    if p.returncode != 0:
        expect("BLANK" in out_of(p), "import 拒绝时应提示 BLANK/NULL/NONE", out_of(p))
        return
    (tmp / "data/data.xml").unlink()
    v = cli("data", "validate", str(tmp))
    expect(v.returncode == 0, f"import 成功（{out_of(p).strip().splitlines()[0]}）但写出的 data.sqlite 未通过 validate",
           out_of(v))


# ── F056 接口 / DB _verify 中 ${Return[-1]} ────────────────────
@functools.lru_cache(maxsize=None)
def f056_module() -> Path:
    tmp = temp_module("f056")
    init_data.build(tmp / "data/data.sqlite", init_data.NEGATIVE_F056)
    shutil.copy(HERE / "fun/negative/f056_verify_return_forbidden.xml", tmp / "case/f056_verify_return_forbidden.xml")
    return tmp


def f056_01():
    """运行前合规检查拦截：退出码非 0，SKI703 return_ref_self_check 指出两张 _verify 表"""
    tmp = f056_module()
    r = run_cases(tmp / "case/f056_verify_return_forbidden.xml", tmp)
    expect(r.code != 0 and "SKI703" in r.out and "return_ref_self_check" in r.out
           and "EchoSelfRef_verify.V001.tag" in r.out and "BizDBSelf_verify.V_SELFREF.c_id" in r.out,
           f"应被合规检查拦截，退出码 {r.code}", r.out)


def f056_02():
    """--force-compliance 跳过合规检查后，verify 步骤仍硬性失败（接口与 DB 各一例，失败原因为自引用）"""
    tmp = f056_module()
    r = run_cases(tmp / "case/f056_verify_return_forbidden.xml", tmp, "--force-compliance")
    for cid in ("F056_API_SELFREF", "F056_DB_SELFREF"):
        expect_case(r, cid)
        err = r.error(cid)
        expect("[预期失败]" in err and "不能使用 ${Return[-1]}" in err, f"{cid} 失败原因不符: {err[:300]}", r.out)


# ── 调度 ──────────────────────────────────────────────────────
CHECKS: List[Tuple[str, Callable[[], None]]] = [
    ("F086-01", f086_01), ("F086-02", f086_02), ("F086-03", f086_03), ("F086-04", f086_04),
    ("F027-01", f027_01), ("F027-02", f027_02), ("F027-03", f027_03), ("F027-04", f027_04),
    ("F026-01", f026_01), ("F026-02", f026_02), ("F026-03", f026_03), ("F026-04", f026_04),
    ("F026-05", f026_05), ("F026-06", f026_06), ("F026-07", f026_07), ("F026-08", f026_08),
    ("F026-09", f026_09),
    ("F055-01", f055_01), ("F055-02", f055_02), ("F055-03", f055_03), ("F055-04", f055_04),
    ("F059-01", f059_01),
    ("F060-01", f060_01), ("F060-02", f060_02), ("F060-03", f060_03),
    ("F065-01", f065_01), ("F065-02", f065_02), ("F065-03", f065_03),
    ("F049-01", f049_01), ("F049-02", f049_02), ("F049-03", f049_03), ("F049-04", f049_04),
    ("F049-05", f049_05), ("F049-06", f049_06), ("F049-07", f049_07), ("F049-08", f049_08),
    ("F050-01", f050_01), ("F050-02", f050_02), ("F050-03", f050_03),
    ("F056-01", f056_01), ("F056-02", f056_02),
]


def main(argv: List[str]) -> int:
    strict = "--strict" in argv
    wanted = [a for a in argv if not a.startswith("--")]
    todo = [(cid, fn) for cid, fn in CHECKS if not wanted or any(cid.startswith(w) for w in wanted)]
    ensure_mock()
    counts = {"PASS": 0, "KNOWN": 0, "FAIL": 0, "FIXED": 0}
    try:
        for cid, fn in todo:
            doc = (fn.__doc__ or "").strip()
            try:
                fn()
                state, detail = ("FIXED", "登记为 KNOWN 但本次通过，请更新 KNOWN 表") if cid in KNOWN else ("PASS", "")
            except AssertionError as e:
                state, detail = ("KNOWN" if cid in KNOWN else "FAIL"), str(e)
            except Exception as e:  # noqa: BLE001
                state, detail = "FAIL", f"{type(e).__name__}: {e}"
            counts[state] += 1
            print(f"{state:<6} {cid}  {doc}", flush=True)
            if state == "KNOWN":
                print(f"       已登记: {KNOWN[cid]}\n       实际: {' '.join(detail.split())[:400]}", flush=True)
            elif detail:
                print(f"       {detail}", flush=True)
    finally:
        stop_mock()
        shutil.rmtree(_TMP_ROOT, ignore_errors=True)
    print(f"\n汇总: PASS {counts['PASS']}  KNOWN {counts['KNOWN']}  FAIL {counts['FAIL']}  FIXED {counts['FIXED']}"
          f"  （共 {len(todo)} 项）")
    failed = counts["FAIL"] + (counts["KNOWN"] if strict else 0)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
