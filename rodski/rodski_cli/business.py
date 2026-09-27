"""business 子命令 — 业务模型校验、图查看与调试入口。

正式业务模型执行仍必须嵌套在 Case 的 ``business_call`` 中；``debug`` 只
执行一次内存调试调用，不创建 Case 或正式结果。其余子命令均为静态/报告
工具，不会驱动被测系统。
"""
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


def setup_parser(subparsers):
    parser = subparsers.add_parser("business", help="业务模型管理、校验、图查看与调试")
    sub = parser.add_subparsers(dest="business_cmd", required=True)

    listing = sub.add_parser("list", help="列出模块中的业务模型")
    listing.add_argument("module", help="测试模块目录")

    flows = sub.add_parser("flow-list", aliases=["flows"], help="列出业务模型中的业务流")
    flows.add_argument("module", help="测试模块目录")
    flows.add_argument("--id", "--ref", dest="ref", required=True, help="业务模型 id")

    validate = sub.add_parser("validate", help="校验业务模型 XML 与图静态约束")
    validate.add_argument("module", help="测试模块目录")
    validate.add_argument("--id", "--ref", dest="ref", help="只校验指定业务模型")

    graph = sub.add_parser("graph", help="输出业务模型 Mermaid 或 JSON 图")
    graph.add_argument("module", help="测试模块目录")
    graph.add_argument("--id", "--ref", dest="ref", required=True, help="业务模型 id")
    graph.add_argument("--format", choices=("mermaid", "json"), default="mermaid")
    graph.add_argument("--flow", help="只输出指定业务流的路径投影")

    coverage = sub.add_parser("coverage", help="汇总正式结果中的业务节点、边和 flow 覆盖")
    coverage.add_argument("module", help="测试模块目录")
    coverage.add_argument("--id", "--ref", dest="ref", help="只汇总指定业务模型")
    coverage.add_argument("--result", help="result.xml 或包含 result.xml 的目录；默认使用最新结果")
    coverage.add_argument("--format", choices=("text", "json"), default="text")

    debug = sub.add_parser(
        "debug",
        help="调试一次业务模型调用（不计入正式测试结果）",
    )
    debug.add_argument("module", help="测试模块目录，例如 rodski-demo/DEMO/demo_business_model")
    debug.add_argument("--id", "--ref", dest="ref", required=True,
                       help="业务模型 id（business_model@id）")
    debug.add_argument("--flow", required=True, help="本次调试选择的目标流程 id")
    debug.add_argument("--input", required=True, dest="input_data_id",
                       help="业务模型 Data 表中的 DataID")
    debug.add_argument("--expect", required=True, dest="expect_data_id",
                       help="业务模型 Verify 表中的 DataID")


def _load_models(module: str):
    from rodski.core.business_model import BusinessModelParser

    business_dir = Path(module).expanduser().resolve() / "business"
    if not business_dir.is_dir():
        raise ValueError(f"业务模型目录不存在: {business_dir}")
    return BusinessModelParser().parse_directory(business_dir)


def _select(models, ref):
    if not ref:
        return models
    model = models.get(ref)
    if model is None:
        available = ", ".join(sorted(models)) or "<none>"
        raise ValueError(f"找不到业务模型 ref={ref!r}; 可用模型: {available}")
    return {ref: model}


def _result_files(module: str, result_arg: str | None):
    if result_arg:
        path = Path(result_arg).expanduser().resolve()
        if path.is_file():
            return [path]
        if path.is_dir():
            files = sorted(path.rglob("result.xml"))
            if files:
                return files
        raise ValueError(f"结果路径不存在或不包含 result.xml: {path}")
    result_dir = Path(module).expanduser().resolve() / "result"
    files = sorted(result_dir.glob("rodski_*/result.xml"))
    if not files:
        raise ValueError(f"没有找到结果文件: {result_dir}")
    return [files[-1]]


def _coverage(models, result_files):
    reports = []
    for path in result_files:
        try:
            reports.append(ET.parse(path).getroot())
        except (OSError, ET.ParseError) as exc:
            raise ValueError(f"无法读取结果 XML {path}: {exc}") from exc

    output = {}
    for model_id, model in models.items():
        node_hits = Counter()
        edge_hits = Counter()
        flow_hits = Counter()
        case_count = 0
        passed_count = 0
        known_paths = {tuple(flow.path): flow.id for flow in model.flows.values()}
        for root in reports:
            for result in root.findall(".//result"):
                for business in result.findall(".//business_result"):
                    if business.get("ref") != model_id:
                        continue
                    case_count += 1
                    if business.get("passed") == "true":
                        passed_count += 1
                    flow = business.get("flow") or ""
                    if flow in model.flows:
                        flow_hits[flow] += 1
                    path_nodes = [node.get("id") for node in business.findall("./actual_path/node")]
                    if not path_nodes:
                        raw = business.findtext("./actual_path") or ""
                        path_nodes = [part for part in raw.split(">") if part]
                    node_hits.update(path_nodes)
                    edge_hits.update(zip(path_nodes, path_nodes[1:]))
        total_nodes = len(model.nodes)
        total_edges = len(model.edges)
        total_flows = len(model.flows)
        output[model_id] = {
            "cases": case_count,
            "passed_cases": passed_count,
            "nodes": {"covered": len(node_hits), "total": total_nodes,
                      "ratio": (len(node_hits) / total_nodes if total_nodes else 1.0),
                      "hits": dict(node_hits)},
            "edges": {"covered": len(edge_hits), "total": total_edges,
                      "ratio": (len(edge_hits) / total_edges if total_edges else 1.0),
                      "hits": {f"{source}>{target}": count for (source, target), count in edge_hits.items()}},
            "flows": {"covered": len(flow_hits), "total": total_flows,
                      "ratio": (len(flow_hits) / total_flows if total_flows else 1.0),
                      "hits": dict(flow_hits)},
            "uncovered_nodes": sorted(set(model.nodes) - set(node_hits)),
            "uncovered_edges": [f"{edge.source}>{edge.target}" for edge in model.edges
                                if (edge.source, edge.target) not in edge_hits],
            "uncovered_flows": sorted(set(model.flows) - set(flow_hits)),
        }
    return output


def _print_coverage(report, fmt):
    if fmt == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return
    for model_id, data in report.items():
        print(f"[{model_id}] cases={data['cases']} passed={data['passed_cases']}")
        for kind in ("nodes", "edges", "flows"):
            value = data[kind]
            print(f"  {kind}: {value['covered']}/{value['total']} ({value['ratio']:.1%})")
        for kind in ("nodes", "edges", "flows"):
            missing = data[f"uncovered_{kind}"]
            if missing:
                print(f"  uncovered {kind}: {', '.join(missing)}")


def handle(args):
    cmd = getattr(args, "business_cmd", None)
    if not cmd:
        print("用法: rodski business <list|flow-list|validate|graph|coverage|debug> ...", file=sys.stderr)
        return 1
    try:
        if cmd == "debug":
            from rodski.business_debug import main as debug_main
            return debug_main([
                "--module", args.module, "--ref", args.ref, "--flow", args.flow,
                "--input", args.input_data_id, "--expect", args.expect_data_id,
            ])

        models = _load_models(args.module)
        if cmd == "list":
            for model in models.values():
                print(f"{model.id}\t{model.name}\tversion={model.version}\tflows={len(model.flows)}")
            return 0

        if cmd in ("flow-list", "flows"):
            model = _select(models, args.ref)[args.ref]
            for flow in model.flows.values():
                print(f"{flow.id}\t{flow.type}\t{'>'.join(flow.path)}")
            return 0

        if cmd == "validate":
            from rodski.core.business_model import BusinessModelValidator
            selected = _select(models, args.ref)
            for model in selected.values():
                BusinessModelValidator.validate(model)
                print(f"[OK] {model.id}: {len(model.nodes)} nodes, {len(model.edges)} edges, {len(model.flows)} flows")
            return 0

        if cmd == "graph":
            from rodski.core.business_model import BusinessModelValidator
            model = _select(models, args.ref)[args.ref]
            if args.format == "json":
                print(json.dumps(BusinessModelValidator.graph_dict(model), ensure_ascii=False, indent=2))
            else:
                print(BusinessModelValidator.mermaid(model, args.flow))
            return 0

        if cmd == "coverage":
            from rodski.core.business_model import BusinessModelValidator
            selected = _select(models, args.ref)
            for model in selected.values():
                BusinessModelValidator.validate(model)
            report = _coverage(selected, _result_files(args.module, args.result))
            _print_coverage(report, args.format)
            return 0

        print(f"未知 business 子命令: {cmd}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
