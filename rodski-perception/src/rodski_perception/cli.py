"""rodski-perception CLI 入口。

子命令
------

- ``locate``  单 / 多目标定位
- ``parse``   全量元素解析
- ``models``  列出 ollama 已安装的 VL 模型
- ``eval``    占位（54d 实现）

退出码
------

==  ==========================================
0   成功（即使部分目标未找到也算 0）
1   推理失败（模型返回完全无法解析）
2   参数错误
3   ollama 不可达
4   模型未安装
==  ==========================================

stdout 输出 JSON 结果（``--output json``）或 text 摘要（``--output text``），
stderr 输出日志和错误详情。
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__
from .errors import (
    InvalidResponseError,
    ModelNotFoundError,
    OllamaUnreachableError,
)


# 退出码
EXIT_OK = 0
EXIT_INFERENCE_FAILED = 1
EXIT_ARG_ERROR = 2
EXIT_OLLAMA_UNREACHABLE = 3
EXIT_MODEL_NOT_FOUND = 4


# 默认模型 — 与 rodski globalvalue.xml 默认一致
DEFAULT_MODEL = "qwen3-vl:2b"
DEFAULT_OLLAMA_HOST = "http://localhost:11434"


def main(argv: Optional[List[str]] = None) -> int:
    """CLI 入口。返回退出码（也是 ``sys.exit`` 用的值）。"""
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not getattr(args, "_handler", None):
        parser.print_help(sys.stderr)
        return EXIT_ARG_ERROR

    try:
        return args._handler(args)
    except SystemExit:  # argparse 内部用，正常透传
        raise
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return EXIT_ARG_ERROR


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rodski-perception",
        description="GUI 元素感知 CLI — 基于本地 ollama + VLM 的截图定位",
    )
    p.add_argument(
        "--version",
        action="version",
        version=f"rodski-perception {__version__}",
    )
    p.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="启用 DEBUG 日志（输出到 stderr）",
    )
    p.set_defaults(_handler=None)

    sub = p.add_subparsers(dest="command")

    # --- locate -------------------------------------------------------
    locate_p = sub.add_parser(
        "locate",
        help="定位一个或多个 UI 元素",
        description="给定截图 + 一个或多个自然语言描述，返回 bbox + 中心坐标",
    )
    locate_p.add_argument("--image", required=True, help="截图路径")
    locate_p.add_argument(
        "--prompt",
        action="append",
        default=[],
        help="目标描述；可多次提供 → 批量定位",
    )
    locate_p.add_argument(
        "--prompts-file",
        help="目标描述文件，每行一个 prompt（与 --prompt 互斥）",
    )
    locate_p.add_argument(
        "--element-type",
        default=None,
        help="目标控件类型先验：button|input|text|select|icon|...",
    )
    locate_p.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"VLM 模型（默认 {DEFAULT_MODEL}）",
    )
    locate_p.add_argument(
        "--ollama-host",
        default=DEFAULT_OLLAMA_HOST,
        help=f"ollama 服务地址（默认 {DEFAULT_OLLAMA_HOST}）",
    )
    locate_p.add_argument(
        "--output",
        choices=("json", "text"),
        default="json",
        help="输出格式",
    )
    locate_p.set_defaults(_handler=_cmd_locate)

    # --- parse --------------------------------------------------------
    parse_p = sub.add_parser(
        "parse",
        help="解析截图中所有可交互元素",
    )
    parse_p.add_argument("--image", required=True, help="截图路径")
    parse_p.add_argument("--model", default=DEFAULT_MODEL)
    parse_p.add_argument("--ollama-host", default=DEFAULT_OLLAMA_HOST)
    parse_p.add_argument(
        "--output",
        choices=("json", "text"),
        default="json",
    )
    parse_p.set_defaults(_handler=_cmd_parse)

    # --- models -------------------------------------------------------
    models_p = sub.add_parser(
        "models",
        help="列出 ollama 已安装的 VL 模型",
    )
    models_p.add_argument("--ollama-host", default=DEFAULT_OLLAMA_HOST)
    models_p.add_argument(
        "--all",
        action="store_true",
        help="列出全部已安装模型（默认仅筛选名字含 vl / vision 的）",
    )
    models_p.add_argument("--output", choices=("json", "text"), default="text")
    models_p.set_defaults(_handler=_cmd_models)

    # --- locate-fused -------------------------------------------------
    fused_p = sub.add_parser(
        "locate-fused",
        help="融合裁决定位（多 hint 并行 + IoU 聚类）",
    )
    fused_p.add_argument("--image", required=True, help="截图路径")
    fused_p.add_argument(
        "--hint",
        action="append",
        default=[],
        help="格式 type:value，如 --hint \"vision:登录按钮\" --hint \"ocr:登录\"",
    )
    fused_p.add_argument("--element-type", default=None)
    fused_p.add_argument("--model", default=DEFAULT_MODEL)
    fused_p.add_argument("--ollama-host", default=DEFAULT_OLLAMA_HOST)
    fused_p.add_argument("--output", choices=("json", "text"), default="json")
    fused_p.set_defaults(_handler=_cmd_locate_fused)

    # --- eval (占位) --------------------------------------------------
    eval_p = sub.add_parser(
        "eval",
        help="评测子命令 — 跑数据集输出 accuracy/latency 报告",
    )
    eval_p.add_argument("--dataset", required=True, help="评测数据集目录（含 manifest.yaml）")
    eval_p.add_argument("--output", help="报告输出路径（JSON）", default=None)
    eval_p.add_argument("--model", default=DEFAULT_MODEL)
    eval_p.add_argument("--ollama-host", default=DEFAULT_OLLAMA_HOST)
    eval_p.set_defaults(_handler=_cmd_eval)

    return p


# ---------------------------------------------------------------------------
# locate
# ---------------------------------------------------------------------------


def _cmd_locate(args) -> int:
    prompts = _resolve_prompts(args)
    if prompts is None:
        return EXIT_ARG_ERROR
    if not prompts:
        print("error: at least one --prompt or --prompts-file required", file=sys.stderr)
        return EXIT_ARG_ERROR

    image_path = Path(args.image)
    if not image_path.exists():
        print(f"error: image not found: {image_path}", file=sys.stderr)
        return EXIT_ARG_ERROR

    from .agent import VLMAgent  # 延迟 import

    try:
        agent = VLMAgent(
            model=args.model,
            ollama_host=args.ollama_host,
        )
        if len(prompts) == 1:
            result = agent.locate(
                prompt=prompts[0],
                image=image_path,
                element_type=args.element_type,
            )
            _print_locate_single(result, prompts[0], agent, args)
        else:
            results = agent.locate_many(
                prompts=prompts,
                image=image_path,
                element_type=args.element_type,
            )
            _print_locate_many(results, prompts, agent, args, image_path)
    except OllamaUnreachableError as exc:
        print(f"error: ollama unreachable: {exc}", file=sys.stderr)
        return EXIT_OLLAMA_UNREACHABLE
    except ModelNotFoundError as exc:
        print(f"error: model not found: {exc}", file=sys.stderr)
        return EXIT_MODEL_NOT_FOUND
    except InvalidResponseError as exc:
        print(f"error: model returned invalid response: {exc}", file=sys.stderr)
        return EXIT_INFERENCE_FAILED
    except FileNotFoundError as exc:
        print(f"error: file not found: {exc}", file=sys.stderr)
        return EXIT_ARG_ERROR

    return EXIT_OK


def _resolve_prompts(args) -> Optional[List[str]]:
    """合并 --prompt 与 --prompts-file。返回 None 表示参数错误。"""
    prompts: List[str] = list(args.prompt or [])
    if args.prompts_file:
        if prompts:
            print(
                "error: --prompt and --prompts-file are mutually exclusive",
                file=sys.stderr,
            )
            return None
        try:
            content = Path(args.prompts_file).read_text(encoding="utf-8")
        except OSError as exc:
            print(f"error: cannot read prompts file: {exc}", file=sys.stderr)
            return None
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                prompts.append(line)
    return prompts


def _print_locate_single(result, prompt: str, agent, args) -> None:
    """打印单目标 locate 的输出。"""
    if result is None:
        data = {
            "target_description": prompt,
            "bbox": None,
            "coordinates": None,
            "model": args.model,
            "error": "not found",
        }
        if args.output == "json":
            print(json.dumps(data, ensure_ascii=False))
        else:
            print(f"[NOT FOUND] {prompt}")
        return

    data = {
        "target_description": result.target_description,
        "bbox": list(result.bbox),
        "coordinates": list(result.coordinates),
        "image_size": list(result.image_size),
        "label": result.label,
        "confidence": result.confidence,
        "latency_ms": result.latency_ms,
        "model": result.model,
    }
    if args.output == "json":
        print(json.dumps(data, ensure_ascii=False))
    else:
        print(
            f"[OK] {result.target_description}"
            f"  bbox={result.bbox}"
            f"  center={result.coordinates}"
            f"  latency={result.latency_ms}ms"
        )


def _print_locate_many(results, prompts, agent, args, image_path) -> None:
    """打印多目标 locate 的输出。"""
    from .coords import read_image_size

    image_size = read_image_size(image_path)
    items = []
    total_latency = 0
    for prompt, r in zip(prompts, results):
        if r is None:
            items.append(
                {
                    "target_description": prompt,
                    "bbox": None,
                    "coordinates": None,
                    "error": "not found",
                }
            )
            continue
        total_latency = max(total_latency, r.latency_ms)
        items.append(
            {
                "target_description": r.target_description,
                "bbox": list(r.bbox),
                "coordinates": list(r.coordinates),
                "label": r.label,
                "confidence": r.confidence,
            }
        )

    data = {
        "image_size": list(image_size),
        "latency_ms": total_latency,
        "model": args.model,
        "results": items,
    }
    if args.output == "json":
        print(json.dumps(data, ensure_ascii=False))
    else:
        for item in items:
            if item.get("error"):
                print(f"[NOT FOUND] {item['target_description']}")
            else:
                print(
                    f"[OK] {item['target_description']}"
                    f"  bbox={item['bbox']}  center={item['coordinates']}"
                )
        print(f"\nLatency: {total_latency}ms; image_size={image_size}")


# ---------------------------------------------------------------------------
# parse
# ---------------------------------------------------------------------------


def _cmd_parse(args) -> int:
    image_path = Path(args.image)
    if not image_path.exists():
        print(f"error: image not found: {image_path}", file=sys.stderr)
        return EXIT_ARG_ERROR

    from .parser import ImageParser

    try:
        parser = ImageParser(model=args.model, ollama_host=args.ollama_host)
        result = parser.parse(image_path)
    except OllamaUnreachableError as exc:
        print(f"error: ollama unreachable: {exc}", file=sys.stderr)
        return EXIT_OLLAMA_UNREACHABLE
    except ModelNotFoundError as exc:
        print(f"error: model not found: {exc}", file=sys.stderr)
        return EXIT_MODEL_NOT_FOUND
    except InvalidResponseError as exc:
        print(f"error: model returned invalid response: {exc}", file=sys.stderr)
        return EXIT_INFERENCE_FAILED

    data = {
        "image_size": list(result.image_size),
        "latency_ms": result.latency_ms,
        "model": result.model,
        "elements": [
            {
                "bbox": list(e.bbox),
                "coordinates": list(e.coordinates),
                "label": e.label,
                "kind": e.kind,
                "confidence": e.confidence,
            }
            for e in result.elements
        ],
    }
    if args.output == "json":
        print(json.dumps(data, ensure_ascii=False))
    else:
        for e in result.elements:
            print(f"[{e.kind}] {e.label}  bbox={e.bbox}  center={e.coordinates}")
        print(f"\nTotal: {len(result.elements)} elements; latency={result.latency_ms}ms")
    return EXIT_OK


# ---------------------------------------------------------------------------
# models
# ---------------------------------------------------------------------------


def _cmd_models(args) -> int:
    from .ollama_client import OllamaClient

    client = OllamaClient(host=args.ollama_host)
    try:
        names = client.list_models()
    except OllamaUnreachableError as exc:
        print(f"error: ollama unreachable: {exc}", file=sys.stderr)
        return EXIT_OLLAMA_UNREACHABLE

    if args.all:
        filtered = names
    else:
        filtered = [
            n for n in names
            if "vl" in n.lower() or "vision" in n.lower() or "vlm" in n.lower()
        ]

    if args.output == "json":
        print(json.dumps({"models": filtered}, ensure_ascii=False))
    else:
        if not filtered:
            print(
                "(no VL models installed; run e.g. `ollama pull qwen3-vl:2b`)",
                file=sys.stderr,
            )
        for n in filtered:
            print(n)
    return EXIT_OK


# ---------------------------------------------------------------------------
# locate-fused
# ---------------------------------------------------------------------------


def _cmd_locate_fused(args) -> int:
    if not args.hint:
        print("error: at least one --hint required", file=sys.stderr)
        return EXIT_ARG_ERROR

    image_path = Path(args.image)
    if not image_path.exists():
        print(f"error: image not found: {image_path}", file=sys.stderr)
        return EXIT_ARG_ERROR

    # Parse hints: "type:value"
    hints = []
    for h in args.hint:
        if ":" not in h:
            print(f"error: invalid hint format (expected type:value): {h}", file=sys.stderr)
            return EXIT_ARG_ERROR
        h_type, h_value = h.split(":", 1)
        hints.append({"type": h_type.strip(), "value": h_value.strip()})

    from .agent import VLMAgent

    try:
        agent = VLMAgent(model=args.model, ollama_host=args.ollama_host)
        result = agent.locate_fused(
            hints=hints,
            image=image_path,
            element_type=args.element_type,
        )
    except OllamaUnreachableError as exc:
        print(f"error: ollama unreachable: {exc}", file=sys.stderr)
        return EXIT_OLLAMA_UNREACHABLE
    except ModelNotFoundError as exc:
        print(f"error: model not found: {exc}", file=sys.stderr)
        return EXIT_MODEL_NOT_FOUND
    except FileNotFoundError as exc:
        print(f"error: file not found: {exc}", file=sys.stderr)
        return EXIT_ARG_ERROR

    if result is None:
        data = {"bbox": None, "coordinates": None, "confidence": 0, "consensus_count": 0, "hint_results": {}}
        if args.output == "json":
            print(json.dumps(data, ensure_ascii=False))
        else:
            print("[NOT FOUND] all hints failed")
        return EXIT_OK

    data = {
        "bbox": list(result.bbox),
        "coordinates": list(result.coordinates),
        "confidence": result.confidence,
        "consensus_count": result.consensus_count,
        "hint_results": result.hint_results,
        "total_latency_ms": result.latency_ms,
    }
    if args.output == "json":
        print(json.dumps(data, ensure_ascii=False))
    else:
        print(
            f"[OK] confidence={result.confidence:.2f}"
            f"  consensus={result.consensus_count}"
            f"  bbox={result.bbox}"
            f"  center={result.coordinates}"
            f"  latency={result.latency_ms}ms"
        )
    return EXIT_OK


# ---------------------------------------------------------------------------
# eval (54d 实现)
# ---------------------------------------------------------------------------


def _cmd_eval(args) -> int:
    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"error: dataset not found: {dataset_path}", file=sys.stderr)
        return EXIT_ARG_ERROR

    from .eval.runner import run_eval

    try:
        report = run_eval(
            dataset_dir=dataset_path,
            model=args.model,
            ollama_host=args.ollama_host,
        )
    except Exception as exc:
        print(f"error: eval failed: {exc}", file=sys.stderr)
        return EXIT_INFERENCE_FAILED

    report_json = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(report_json, encoding="utf-8")
        print(f"report written to {args.output}", file=sys.stderr)
    else:
        print(report_json)

    # Terminal summary
    print(f"\n--- Eval Summary ---", file=sys.stderr)
    print(f"  accuracy: {report.get('accuracy', 0):.2%}", file=sys.stderr)
    print(f"  latency_p50: {report.get('latency_p50_ms', 0)}ms", file=sys.stderr)
    print(f"  latency_p95: {report.get('latency_p95_ms', 0)}ms", file=sys.stderr)
    print(f"  total_tasks: {report.get('total_tasks', 0)}", file=sys.stderr)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
