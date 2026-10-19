#!/usr/bin/env python3
"""F059 断言：读取 mock 记录的最近两次 /echo/gen1、/echo/gen2 请求体，逐字段校验生成值格式 / 范围。

依据 TEST_CASE_WRITING_GUIDE.md §7.7 与 CORE_DESIGN_CONSTRAINTS.md §4.4.1~4.4.3。
基准时间取 mock 收到请求的时刻（服务端本地时间），时间类允许 ±120 秒误差。
通过：stdout 输出 JSON 摘要；失败：stderr 逐项列出，退出码 1（run 关键字据此判定步骤失败）。
"""
from __future__ import annotations

import json
import re
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

LOG = Path(__file__).resolve().parent.parent / ".runtime" / "requests.jsonl"
TOL = 120  # 秒


def latest(tag: str) -> dict:
    recs = [json.loads(l) for l in LOG.read_text(encoding="utf-8").splitlines() if l.strip()]
    recs = [r for r in recs if r.get("tag") == tag]
    if not recs:
        raise SystemExit(f"mock 未收到 /echo/{tag} 请求: {LOG}")
    return recs[-1]


def check(rec: dict) -> list:
    b = {k: str(v) for k, v in rec["body"].items()}
    t = datetime.fromtimestamp(rec["ts"])
    errs = []

    def ok(cond, field, why):
        if not cond:
            errs.append(f"{rec['tag']}.{field}={b.get(field)!r}: {why}")

    def near(dt: datetime, ref: datetime) -> bool:
        return abs((dt - ref).total_seconds()) <= TOL

    def parse(field, fmt):
        try:
            return datetime.strptime(b[field], fmt)
        except (KeyError, ValueError):
            return None

    def num(field):
        try:
            return float(b[field])
        except (KeyError, ValueError):
            return None

    v = num("r_int_range"); ok(re.fullmatch(r"\d+", b.get("r_int_range", "")) and 1000 <= v <= 9999, "r_int_range", "应为 1000~9999 整数")
    ok(re.fullmatch(r"[1-9]\d{3}", b.get("r_int_len", "")), "r_int_len", "应为 4 位整数")
    v = num("r_float"); ok(v is not None and 10.0 <= v <= 999.99 and re.fullmatch(r"\d+(\.\d{1,2})?", b["r_float"]), "r_float", "应为 10.00~999.99、最多 2 位小数")
    ok(re.fullmatch(r"[A-Za-z0-9]{6}", b.get("r_str", "")), "r_str", "应为 6 位字母数字")
    ok(re.fullmatch(r"\d{8}", b.get("r_digits", "")), "r_digits", "应为 8 位纯数字")
    ok(re.fullmatch(r"1[3-9]\d{9}", b.get("r_phone", "")), "r_phone", "应为 11 位中国手机号")
    ok(re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", b.get("r_email", "")), "r_email", "应为邮箱格式")
    ok(b.get("r_choice") in ("A", "B", "C"), "r_choice", "应为 A/B/C 之一")
    try:
        u = uuid.UUID(b.get("r_uuid", ""))
        ok(u.version == 4 and str(u) == b["r_uuid"], "r_uuid", "应为小写带连字符的 UUID v4")
    except ValueError:
        ok(False, "r_uuid", "不是 UUID")

    d = parse("d_now", "%Y-%m-%d %H:%M:%S"); ok(d and near(d, t), "d_now", "应为 YYYY-MM-DD HH:MM:SS 的当前时间")
    d = parse("d_now_fmt", "%Y%m%d_%H%M%S"); ok(d and near(d, t), "d_now_fmt", "应为 %Y%m%d_%H%M%S 的当前时间")
    ok(b.get("d_today") == t.strftime("%Y-%m-%d"), "d_today", f"应为 {t:%Y-%m-%d}")
    ok(b.get("d_today_fmt") == t.strftime("%Y%m%d"), "d_today_fmt", f"应为 {t:%Y%m%d}")
    d = parse("d_time", "%H:%M:%S")
    ok(d and near(datetime.combine(t.date(), d.time()), t), "d_time", "应为 HH:MM:SS 的当前时间")
    v = num("d_ts"); ok(re.fullmatch(r"\d{10}", b.get("d_ts", "")) and abs(v - rec["ts"]) <= TOL, "d_ts", "应为当前 Unix 秒级时间戳（10 位）")
    v = num("d_ts_ms"); ok(re.fullmatch(r"\d{13}", b.get("d_ts_ms", "")) and abs(v / 1000 - rec["ts"]) <= TOL, "d_ts_ms", "应为当前毫秒时间戳（13 位）")
    ok(b.get("d_off_p30") == (t + timedelta(days=30)).strftime("%Y-%m-%d"), "d_off_p30", f"应为 30 天后 {(t + timedelta(days=30)):%Y-%m-%d}")
    ok(b.get("d_off_m7") == (t - timedelta(days=7)).strftime("%Y-%m-%d"), "d_off_m7", f"应为 7 天前 {(t - timedelta(days=7)):%Y-%m-%d}")
    d = parse("d_off_m2h", "%Y-%m-%d %H:%M:%S"); ok(d and near(d, t - timedelta(hours=2)), "d_off_m2h", "应为 2 小时前 YYYY-MM-DD HH:MM:SS")
    d = parse("d_off_m2h_fmt", "%H:%M")
    ok(d and near(datetime.combine((t - timedelta(hours=2)).date(), d.time()), t - timedelta(hours=2)), "d_off_m2h_fmt", "应为 2 小时前 HH:MM")
    v = num("ts"); ok(re.fullmatch(r"\d{10}", b.get("ts", "")) and abs(v - rec["ts"]) <= TOL, "ts", "timestamp() 应为当前秒级时间戳")
    v = num("ts_ms"); ok(re.fullmatch(r"\d{13}", b.get("ts_ms", "")) and abs(v / 1000 - rec["ts"]) <= TOL, "ts_ms", "timestamp_ms() 应为当前毫秒时间戳")
    s36 = b.get("ts36", "")
    ok(re.fullmatch(r"[0-9A-Z]+", s36) and abs(int(s36, 36) / 1000 - rec["ts"]) <= TOL, "ts36",
       "timestamp36() 应为当前毫秒时间戳的 36 进制大写")
    ok(re.fullmatch(rf"ORD_{t:%Y%m%d}_\d{{4}}", b.get("order_no", "")), "order_no", f"应为 ORD_{t:%Y%m%d}_四位数字（字符串拼接）")
    ok(b.get("escaped") == "${random(int, 1, 9)}", "escaped", "$${ 转义应得到字面量 ${random(int, 1, 9)}")
    return errs


def main() -> int:
    g1, g2 = latest("gen1"), latest("gen2")
    errs = check(g1) + check(g2)
    # 每次执行重新计算、不缓存（§7.7 注意事项 / §4.4.6 规则 4）
    for f in ("r_uuid", "r_str", "r_email"):
        if g1["body"].get(f) == g2["body"].get(f):
            errs.append(f"{f}: 两次求值相同 {g1['body'].get(f)!r}，应每次重新计算")
    if errs:
        print("F059 生成值断言失败:\n  " + "\n  ".join(errs), file=sys.stderr)
        return 1
    print(json.dumps({"checked": len(g1["body"]), "gen1_uuid": g1["body"]["r_uuid"], "gen2_uuid": g2["body"]["r_uuid"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
