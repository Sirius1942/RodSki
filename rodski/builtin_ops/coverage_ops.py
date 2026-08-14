"""JS 覆盖率采集 - 开始/停止采集，输出覆盖率统计 JSON

仅在 PlaywrightDriver + Chromium 下可用。非 Chromium 浏览器（Firefox/WebKit）
不支持 Playwright 的 JS Coverage API，start_js_coverage 会返回
{"success": False, "reason": "..."} 而不抛异常，stop_js_coverage 则返回空列表
对应的统计结果（total_files=0）。

通过 _context 参数接收当前驱动实例（driver 挂在 context["driver"] 上，
覆盖率采集方法挂在 driver 实例上，而不是 page 对象上）。
"""
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("rodski.builtins.coverage")


def _get_playwright_driver(context: Optional[dict] = None):
    """从上下文中获取 PlaywrightDriver 实例

    Args:
        context: 运行时上下文，包含 driver 实例

    Returns:
        PlaywrightDriver 实例

    Raises:
        RuntimeError: 驱动不是 PlaywrightDriver 或 context 中无 driver
    """
    if context is None:
        raise RuntimeError(
            "coverage_ops 需要运行时上下文（_context），"
            "请通过 run 关键字在测试用例中调用"
        )

    driver = context.get("driver")
    if driver is None:
        raise RuntimeError("运行时上下文中未找到 driver 实例")

    # 检查是否为 PlaywrightDriver
    driver_class = type(driver).__name__
    if driver_class != "PlaywrightDriver":
        raise RuntimeError(
            f"coverage_ops 仅支持 PlaywrightDriver，"
            f"当前 driver 类型: {driver_class}"
        )

    return driver


def start_js_coverage(_context: Optional[dict] = None) -> dict:
    """开始采集 JS 覆盖率

    仅 PlaywrightDriver + Chromium 支持。非 Chromium 浏览器（Firefox/WebKit）
    不会抛异常，而是返回 success=False 并给出原因。

    通过 run 关键字调用：
        <test_step action="run" model="" data="start_js_coverage()"/>

    Args:
        _context: 运行时上下文（由 keyword_engine 自动注入，含 driver 实例）

    Returns:
        采集是否成功启动：
            {"success": True} —— 已开始采集
            {"success": False, "reason": "..."} —— 非 Chromium，无法采集

    Raises:
        RuntimeError: 驱动不是 PlaywrightDriver，或上下文中无 driver 实例
    """
    driver = _get_playwright_driver(_context)

    started = driver.start_js_coverage()
    if not started:
        reason = "当前浏览器非 Chromium，不支持 JS 覆盖率采集"
        logger.warning(f"start_js_coverage: {reason}")
        return {"success": False, "reason": reason}

    logger.info("start_js_coverage: 已开始采集 JS 覆盖率")
    return {"success": True}


def stop_js_coverage(output: str = "coverage.json", _context: Optional[dict] = None) -> dict:
    """停止采集 JS 覆盖率，并将统计结果写入 JSON 文件

    仅 PlaywrightDriver + Chromium 支持。若未曾调用 start_js_coverage 或当前
    浏览器非 Chromium，driver.stop_js_coverage() 会返回空列表，此时统计结果为
    total_files=0，仍会正常写出一份空统计的 JSON 文件（不抛异常）。

    通过 run 关键字调用：
        <test_step action="run" model="" data="stop_js_coverage(output='coverage.json')"/>

    覆盖率计算方式：
        对每个 entry（对应一个 JS 资源），
            used_bytes = sum(r['end'] - r['start'] for r in entry['ranges'])
            total_bytes = len(entry['source'])（Playwright 原始字段名为 'source'）
            covered_pct = used_bytes / total_bytes * 100
        entry 中缺失 'ranges' 或 'source'/'text' 字段时，跳过该 entry，不计入统计
        （不抛异常）。

    Args:
        output: 输出 JSON 文件路径。相对路径按当前工作目录（cwd）解析，
            不做额外的运行目录推断。默认 "coverage.json"
        _context: 运行时上下文（由 keyword_engine 自动注入，含 driver 实例）

    Returns:
        {
            "success": True,
            "output": "<实际写入的文件路径>",
            "summary": {"total_files": N, "average_coverage_pct": X.X}
        }

    Raises:
        RuntimeError: 驱动不是 PlaywrightDriver，或上下文中无 driver 实例
    """
    driver = _get_playwright_driver(_context)

    raw_entries = driver.stop_js_coverage() or []

    files = []
    for entry in raw_entries:
        ranges = entry.get("ranges")
        source = entry.get("source", entry.get("text"))
        if ranges is None or source is None:
            logger.debug(
                f"stop_js_coverage: 跳过缺失 ranges/source 字段的 entry "
                f"(url={entry.get('url', '<unknown>')})"
            )
            continue

        total_bytes = len(source)
        if total_bytes <= 0:
            continue

        used_bytes = sum(r["end"] - r["start"] for r in ranges)
        covered_pct = used_bytes / total_bytes * 100

        files.append(
            {
                "url": entry.get("url", ""),
                "covered_pct": round(covered_pct, 2),
                "used_bytes": used_bytes,
                "total_bytes": total_bytes,
            }
        )

    total_files = len(files)
    average_coverage_pct = (
        round(sum(f["covered_pct"] for f in files) / total_files, 2)
        if total_files > 0
        else 0.0
    )

    summary = {
        "total_files": total_files,
        "average_coverage_pct": average_coverage_pct,
    }
    result_data = {"summary": summary, "files": files}

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.info(
        f"stop_js_coverage: 已写入覆盖率报告 {output_path} "
        f"(total_files={total_files}, average_coverage_pct={average_coverage_pct})"
    )
    return {"success": True, "output": str(output_path), "summary": summary}
