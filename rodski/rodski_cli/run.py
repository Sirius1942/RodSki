"""run 子命令 - 执行测试用例"""
import sys
import time
from pathlib import Path


def setup_parser(subparsers):
    parser = subparsers.add_parser("run", help="执行测试用例")
    parser.add_argument("case", help="用例文件路径 (Excel)")
    parser.add_argument("--driver", choices=["web", "desktop"], default="web", help="驱动类型")
    parser.add_argument("--sheet", help="工作表名称")
    parser.add_argument("--headless", action="store_true", help="无头模式")
    parser.add_argument("--retry", type=int, default=0, help="失败重试次数")
    parser.add_argument("--output", help="报告输出路径")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run",
                        help="验证用例但不实际执行")
    parser.add_argument("--verbose", action="store_true", help="详细输出模式")
    parser.add_argument("--performance", action="store_true", help="显示性能统计数据")
    parser.add_argument("--step-by-step", action="store_true", dest="step_by_step",
                        help="单步执行模式，每步执行前等待确认")
    parser.add_argument("--pause-on-error", action="store_true", dest="pause_on_error",
                        help="错误时暂停，等待用户决定是否继续")
    parser.add_argument("--interactive", action="store_true",
                        help="交互模式，支持单步/跳过/退出等操作")


def _print_verbose(msg, verbose=False):
    """在 verbose 模式下打印额外信息"""
    if verbose:
        print(f"  [详细] {msg}")


def _print_step_detail(step, index, total, verbose=False):
    """打印步骤详细信息"""
    keyword = step.get("keyword", "")
    name = step.get("name", f"Step {index + 1}")
    params = step.get("params", {})
    print(f"  步骤 {index + 1}/{total}: {name} ({keyword})")
    if verbose and params:
        for k, v in params.items():
            print(f"    参数: {k} = {v}")


def _format_run_error(error_type, message):
    """格式化运行时错误信息"""
    error_icons = {
        "file": "文件错误",
        "parse": "解析错误",
        "driver": "驱动错误",
        "execute": "执行错误",
        "validate": "验证错误",
    }
    prefix = error_icons.get(error_type, "错误")
    return f"{prefix}: {message}"


def _interactive_prompt(prompt_msg, options):
    """显示交互提示并等待用户输入，返回用户选择"""
    while True:
        try:
            choice = input(prompt_msg).strip().lower()
            if choice in options:
                return choice
            print(f"  无效输入，请输入: {'/'.join(options)}")
        except (EOFError, KeyboardInterrupt):
            return "q"


def _prompt_before_step(step_name, keyword, index, total, mode):
    """单步/交互模式下执行前提示，返回 'c'继续 's'跳过 'q'退出"""
    print(f"\n>>> 步骤 {index + 1}/{total}: {step_name} ({keyword})")
    if mode == "step_by_step":
        return _interactive_prompt("  按 Enter 继续, s 跳过, q 退出: ",
                                   ["", "c", "s", "q"])
    elif mode == "interactive":
        return _interactive_prompt("  c 继续, s 跳过, q 退出: ",
                                   ["c", "s", "q"])
    return "c"


def _prompt_on_error(step_name, error_msg, mode):
    """错误时提示，返回 'c'继续 'q'退出"""
    print(f"\n  [错误] {step_name}: {error_msg}")
    if mode in ("pause_on_error", "interactive"):
        return _interactive_prompt("  c 继续下一步, q 退出: ", ["c", "q"])
    return "q"


def handle(args):
    from data.excel_parser import ExcelParser
    from core.task_executor import TaskExecutor
    from core.keyword_engine import KeywordEngine
    from core.logger import Logger
    from core.profiler import Profiler
    from core.performance import set_profiler

    verbose = getattr(args, "verbose", False)
    dry_run = getattr(args, "dry_run", False)
    show_performance = getattr(args, "performance", False)

    # 探索式测试模式
    step_by_step = getattr(args, "step_by_step", False)
    pause_on_error = getattr(args, "pause_on_error", False)
    interactive = getattr(args, "interactive", False)

    # 确定执行模式（interactive 优先级最高）
    if interactive:
        exec_mode = "interactive"
    elif step_by_step:
        exec_mode = "step_by_step"
    elif pause_on_error:
        exec_mode = "pause_on_error"
    else:
        exec_mode = "normal"

    case_path = Path(args.case)
    if not case_path.exists():
        print(_format_run_error("file", f"用例文件不存在: {args.case}"), file=sys.stderr)
        print("提示: 请检查文件路径是否正确，支持 .xlsx 格式", file=sys.stderr)
        return 1

    if not case_path.suffix.lower() in (".xlsx", ".xls"):
        print(_format_run_error("file", f"不支持的文件格式: {case_path.suffix}"), file=sys.stderr)
        print("提示: 仅支持 .xlsx 和 .xls 格式的 Excel 文件", file=sys.stderr)
        return 1

    logger = Logger(console=True)
    _print_verbose(f"用例文件: {case_path.absolute()}", verbose)

    # 解析阶段
    print(f"解析用例: {args.case}")
    try:
        parser = ExcelParser(str(case_path))
        errors = parser.validate()
    except Exception as e:
        print(_format_run_error("parse", f"无法加载用例文件: {e}"), file=sys.stderr)
        print("提示: 请确认文件格式正确且未被占用", file=sys.stderr)
        return 1

    if errors:
        print(_format_run_error("validate", f"用例文件验证失败 (共 {len(errors)} 个错误):"), file=sys.stderr)
        for i, e in enumerate(errors, 1):
            print(f"  {i}. {e}", file=sys.stderr)
        return 1

    _print_verbose("用例文件验证通过", verbose)

    try:
        raw_data = parser.parse(args.sheet)
    except KeyError:
        available = parser.get_sheet_names()
        print(_format_run_error("parse", f"工作表 '{args.sheet}' 不存在"), file=sys.stderr)
        print(f"提示: 可用的工作表: {', '.join(available)}", file=sys.stderr)
        parser.close()
        return 1
    except Exception as e:
        print(_format_run_error("parse", f"解析工作表失败: {e}"), file=sys.stderr)
        parser.close()
        return 1

    _print_verbose(f"解析到 {len(raw_data)} 行数据", verbose)

    # dry-run 模式：只验证不执行
    if dry_run:
        # 构造 steps 做验证
        steps = []
        for row in raw_data:
            keyword = row.get("keyword") or row.get("Keyword") or ""
            if not keyword:
                continue
            params = {}
            for k, v in row.items():
                if k.lower() not in ("keyword", "name", "step", "continue_on_fail") and v is not None:
                    params[k.lower()] = v
            steps.append({
                "keyword": keyword.strip(),
                "params": params,
                "name": row.get("name") or row.get("Name") or row.get("step") or keyword,
            })

        print(f"\n[Dry Run] 用例验证结果:")
        print(f"  文件: {args.case}")
        print(f"  驱动: {args.driver}")
        print(f"  步骤数: {len(steps)}")
        if args.sheet:
            print(f"  工作表: {args.sheet}")
        print(f"  重试次数: {args.retry}")
        print(f"\n  步骤列表:")
        for i, step in enumerate(steps):
            _print_step_detail(step, i, len(steps), verbose)
        print(f"\n验证通过: 用例可以正常执行 (共 {len(steps)} 个步骤)")
        parser.close()
        return 0

    # 实际执行
    if args.driver == "desktop":
        print(_format_run_error("driver", "桌面驱动需要 pywinauto (仅 Windows)"), file=sys.stderr)
        print("提示: 桌面自动化仅在 Windows 平台支持", file=sys.stderr)
        parser.close()
        return 1

    try:
        from drivers.playwright_driver import PlaywrightDriver
    except ImportError:
        print(_format_run_error("driver", "未安装 playwright 驱动"), file=sys.stderr)
        print("提示: 请运行 pip install playwright && playwright install", file=sys.stderr)
        parser.close()
        return 1

    _print_verbose(f"初始化驱动: {args.driver} (headless={args.headless})", verbose)
    driver = PlaywrightDriver(headless=args.headless)

    profiler = None
    if show_performance:
        profiler = Profiler()
        set_profiler(profiler)

    try:
        engine = KeywordEngine(driver)
        executor = TaskExecutor(engine, max_retries=args.retry, logger=logger)
        steps = executor.load_case(raw_data)

        step_count = len(steps)
        mode_label = {"normal": "", "step_by_step": " [单步模式]",
                      "pause_on_error": " [错误暂停]", "interactive": " [交互模式]"}
        print(f"执行用例 (驱动: {args.driver}, 步骤: {step_count}){mode_label[exec_mode]}")

        if verbose:
            print(f"\n步骤详情:")
            for i, step in enumerate(steps):
                _print_step_detail(step, i, step_count, verbose)
            print()

        # 使用 tqdm 进度条
        try:
            from tqdm import tqdm
            progress = tqdm(total=step_count, desc="执行进度", unit="步骤",
                            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]")
        except ImportError:
            progress = None
            _print_verbose("tqdm 未安装，跳过进度条显示", verbose)

        # 使用回调方式执行以支持进度条
        original_execute = executor.execute_steps

        def execute_with_progress(steps_list):
            executor.results = []
            executor.start_time = time.time()
            all_passed = True

            for i, step in enumerate(steps_list):
                keyword = step.get("keyword", "")
                params = step.get("params", {})
                step_name = step.get("name", f"Step {i + 1}")

                # 单步/交互模式：执行前提示
                if exec_mode in ("step_by_step", "interactive"):
                    choice = _prompt_before_step(step_name, keyword, i, len(steps_list), exec_mode)
                    if choice == "" or choice == "c":
                        pass  # 继续执行
                    elif choice == "s":
                        _print_verbose(f"跳过步骤: {step_name}", True)
                        continue
                    elif choice == "q":
                        print("  用户退出执行")
                        break

                success, error_msg = executor._execute_with_retry(keyword, params)
                from datetime import datetime
                result = {
                    "step": step_name,
                    "keyword": keyword,
                    "params": params,
                    "success": success,
                    "timestamp": datetime.now().isoformat(),
                }
                if error_msg:
                    result["error"] = error_msg
                executor.results.append(result)

                if executor.logger:
                    status = "PASS" if success else "FAIL"
                    log_msg = f"[{status}] {step_name}: {keyword}"
                    if error_msg:
                        log_msg += f" - {error_msg}"
                    if success:
                        executor.logger.info(log_msg)
                    else:
                        executor.logger.error(log_msg)

                if progress:
                    progress.update(1)
                    if not success:
                        progress.set_postfix_str(f"失败: {step_name}")

                if verbose:
                    status = "PASS" if success else "FAIL"
                    _print_verbose(f"[{status}] {step_name}: {keyword}", True)
                    if error_msg:
                        _print_verbose(f"  错误: {error_msg}", True)

                if not success:
                    all_passed = False
                    if exec_mode in ("pause_on_error", "interactive"):
                        # 错误时暂停等待用户决定
                        if progress:
                            progress.clear()
                        choice = _prompt_on_error(step_name, error_msg, exec_mode)
                        if choice == "q":
                            break
                        # choice == "c": 继续下一步（忽略 continue_on_fail 设置）
                    elif not step.get("continue_on_fail", False):
                        break

            executor.end_time = time.time()
            if progress:
                progress.close()
            return all_passed

        success = execute_with_progress(steps)

        summary = executor.get_summary()
        status_icon = "通过" if success else "失败"
        print(f"\n结果: [{status_icon}] {summary['passed']}/{summary['total']} 通过 "
              f"(失败: {summary['failed']}, 通过率: {summary['pass_rate']}%, "
              f"耗时: {summary['duration']}s)")

        if verbose and summary['failed'] > 0:
            print("\n失败步骤详情:")
            for r in executor.results:
                if not r["success"]:
                    print(f"  - {r['step']}: {r['keyword']}")
                    if r.get("error"):
                        print(f"    原因: {r['error']}")

        executor.save_results()

        if args.output:
            executor.save_results(args.output)
            print(f"报告已保存: {args.output}")

        if show_performance and profiler:
            stats = profiler.get_stats()
            print(f"\n性能统计:")
            print(f"  总操作数: {stats.get('total_operations', 0)}")
            print(f"  总耗时: {stats.get('total_time', 0):.2f}s")
            print(f"  平均耗时: {stats.get('avg_time', 0):.3f}s")
            print(f"  最慢操作: {stats.get('max_time', 0):.2f}s")
            print(f"  内存峰值: {stats.get('memory_peak_mb', 0):.1f} MB")
            print(f"  平均内存: {stats.get('memory_avg_mb', 0):.1f} MB")
            if verbose:
                print(f"\n关键字性能:")
                for kw, kw_stats in stats.get('keyword_stats', {}).items():
                    print(f"  {kw}: {kw_stats['count']}次, 平均{kw_stats['avg_time']:.3f}s, {kw_stats.get('avg_memory_mb', 0):.1f}MB")

        return 0 if success else 1
    except Exception as e:
        print(_format_run_error("execute", str(e)), file=sys.stderr)
        if verbose:
            import traceback
            traceback.print_exc()
        return 1
    finally:
        driver.close()
        parser.close()
