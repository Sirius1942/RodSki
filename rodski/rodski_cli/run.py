"""run 子命令 - 通过 SKIExecutor 执行测试用例（Case Sheet + model.xml + 数据表）"""
import sys
import logging
from pathlib import Path

logger = logging.getLogger("rodski")


def setup_parser(subparsers):
    parser = subparsers.add_parser("run", help="执行测试用例")
    parser.add_argument("case", help="用例文件路径 (Excel)")
    parser.add_argument("--model", help="模型文件路径 (model.xml)，不指定则自动推断")
    parser.add_argument("--browser", choices=["chromium", "firefox", "webkit"],
                        default="chromium", help="浏览器类型 (默认: chromium)")
    parser.add_argument("--headless", action="store_true", help="无头模式")
    parser.add_argument("--verbose", action="store_true", help="详细输出模式")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run",
                        help="验证用例但不实际执行")
    parser.add_argument("--output", help="报告输出路径")


def _infer_model_path(case_path: Path) -> Path:
    """从用例文件路径推断 model.xml 位置
    
    约定: case 文件在 .../case/ 目录下，model 在 .../model/model.xml
    即 case_path.parent.parent / "model" / "model.xml"
    """
    model_path = case_path.parent.parent / "model" / "model.xml"
    return model_path


def handle(args):
    verbose = getattr(args, "verbose", False)
    dry_run = getattr(args, "dry_run", False)

    case_path = Path(args.case)
    if not case_path.exists():
        print(f"错误: 用例文件不存在: {args.case}", file=sys.stderr)
        return 1

    if case_path.suffix.lower() not in (".xlsx", ".xls", ".xlsm"):
        print(f"错误: 不支持的文件格式: {case_path.suffix}", file=sys.stderr)
        return 1

    # 确定 model.xml 路径
    if args.model:
        model_path = Path(args.model)
    else:
        model_path = _infer_model_path(case_path)

    if not model_path.exists():
        print(f"错误: 模型文件不存在: {model_path}", file=sys.stderr)
        print(f"提示: 使用 --model 参数指定模型文件路径", file=sys.stderr)
        return 1

    if verbose:
        logging.basicConfig(level=logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    print(f"用例文件: {case_path}")
    print(f"模型文件: {model_path}")
    print(f"浏览器: {args.browser}")

    # dry-run 模式：只解析不执行
    if dry_run:
        return _handle_dry_run(case_path, model_path, verbose)

    return _handle_execute(case_path, model_path, args)


def _handle_dry_run(case_path: Path, model_path: Path, verbose: bool) -> int:
    """验证用例可执行性但不实际执行"""
    from core.case_parser import CaseParser
    from core.model_parser import ModelParser

    try:
        model_parser = ModelParser(str(model_path))
        case_parser = CaseParser(str(case_path))
        cases = case_parser.parse_cases()
        case_parser.close()
    except Exception as e:
        print(f"解析失败: {e}", file=sys.stderr)
        return 1

    print(f"\n[Dry Run] 用例验证结果:")
    print(f"  模型数: {len(model_parser.models)}")
    print(f"  用例数: {len(cases)}")

    for i, case in enumerate(cases, 1):
        print(f"\n  用例 {i}: {case['case_id']} - {case['title']}")
        for phase in ['pre_process', 'test_step', 'expected_result', 'post_process']:
            action = case[phase].get('action', '')
            if action:
                model = case[phase].get('model', '')
                data = case[phase].get('data', '')
                print(f"    {phase}: action={action}, model={model}, data={data}")
                if verbose and model:
                    model_info = model_parser.get_model(model)
                    if model_info:
                        print(f"      模型元素: {list(model_info.keys())}")
                    else:
                        print(f"      [警告] 模型 '{model}' 不存在")

    print(f"\n验证通过: {len(cases)} 个用例可执行")
    return 0


def _handle_execute(case_path: Path, model_path: Path, args) -> int:
    """实际执行测试用例"""
    from core.ski_executor import SKIExecutor
    from drivers.playwright_driver import PlaywrightDriver

    headless = getattr(args, "headless", False)
    browser = getattr(args, "browser", "chromium")

    def create_driver():
        return PlaywrightDriver(headless=headless, browser=browser)

    driver = create_driver()
    executor = None

    try:
        executor = SKIExecutor(
            str(case_path),
            str(model_path),
            driver,
            driver_factory=lambda: create_driver()
        )

        print("-" * 60)
        results = executor.execute_all_cases()
        print("-" * 60)

        # 汇总结果
        total = len(results)
        passed = sum(1 for r in results if r.get('status', '').upper() == 'PASS')
        failed = total - passed

        print(f"执行完成: {passed}/{total} 通过, {failed} 失败")

        if failed > 0:
            print(f"\n失败用例:")
            for r in results:
                if r.get('status', '').upper() == 'FAIL':
                    print(f"  - {r.get('case_id')}: {r.get('error', '未知错误')}")

        if args.output:
            import json
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps({
                "summary": {"total": total, "passed": passed, "failed": failed},
                "results": results,
            }, indent=2, ensure_ascii=False))
            print(f"报告已保存: {args.output}")

        return 0 if failed == 0 else 1

    except Exception as e:
        print(f"执行错误: {e}", file=sys.stderr)
        if getattr(args, "verbose", False):
            import traceback
            traceback.print_exc()
        return 1
    finally:
        if executor:
            executor.close()
        elif driver:
            try:
                driver.close()
            except Exception:
                pass
