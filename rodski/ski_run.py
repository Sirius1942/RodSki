#!/usr/bin/env python3
"""RodSki CLI - 运行测试用例（XML 版本）

用法:
    python ski_run.py <case_path> [--browser chromium] [--headless]

case_path 支持:
    1. case XML 文件路径  → 执行该文件中的用例
    2. case/ 目录路径     → 执行目录下所有 XML 用例
    3. 测试模块目录路径   → 自动查找 case/ 子目录

目录结构约束:
    product/{测试项目}/{测试模块}/
    ├── case/       ← case XML 文件
    ├── model/      ← model.xml
    ├── fun/        ← 代码工程目录
    ├── data/       ← 数据 XML + globalvalue.xml
    └── result/     ← 测试结果 XML（自动生成）
"""
import sys
import argparse
from pathlib import Path
from .core.ski_executor import SKIExecutor, resolve_module_dir
from .core.logger import Logger


def create_driver(headless: bool = False, browser: str = "chromium", driver_type: str = "web"):
    if driver_type in ("macos", "windows"):
        from .drivers.desktop_driver import DesktopDriver
        return DesktopDriver(target_platform=driver_type)
    from .drivers.playwright_driver import PlaywrightDriver
    return PlaywrightDriver(headless=headless, browser=browser)


def resolve_case_path(input_path: Path) -> Path:
    """智能解析用例路径：支持文件、case目录、模块目录"""
    if input_path.is_file() and input_path.suffix == '.xml':
        return input_path

    if input_path.is_dir():
        if input_path.name == 'case':
            return input_path
        case_dir = input_path / 'case'
        if case_dir.is_dir():
            return case_dir

    return input_path


def main():
    parser = argparse.ArgumentParser(description="RodSki 测试运行器（XML 版本）")
    parser.add_argument("case_path", help="用例 XML 文件路径、case/ 目录路径或测试模块目录路径")
    parser.add_argument("--browser", choices=["chromium", "firefox", "webkit"],
                        default="chromium", help="浏览器类型 (默认: chromium)")
    parser.add_argument("--headless", action="store_true", help="无头模式")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        default="INFO", help="日志等级 (默认: INFO)")
    parser.add_argument("--verbose", action="store_true", help="详细模式（等同 DEBUG）")
    parser.add_argument("--quiet", action="store_true", help="静默模式（仅 ERROR）")
    args = parser.parse_args()

    # 确定日志等级
    if args.verbose:
        log_level = "DEBUG"
    elif args.quiet:
        log_level = "ERROR"
    else:
        log_level = args.log_level

    # 初始化 Logger
    Logger(name="rodski", level=log_level, console=True)

    case_path = resolve_case_path(Path(args.case_path))

    if not case_path.exists():
        print(f"错误: 路径不存在: {case_path}")
        sys.exit(1)

    module_dir = resolve_module_dir(case_path)
    model_file = module_dir / "model" / "model.xml"

    print(f"🚀 RodSki 框架启动（XML 模式）")
    print(f"📋 用例路径: {case_path}")
    print(f"📁 测试模块: {module_dir}")
    print(f"🏗️  模型文件: {model_file}")
    print(f"🌐 浏览器: {args.browser}")
    print("-" * 60)

    if not model_file.exists():
        print(f"⚠️  模型文件不存在: {model_file}（将在无模型模式下运行）")

    driver = create_driver(headless=args.headless, browser=args.browser)

    executor = SKIExecutor(
        str(case_path),
        driver,
        driver_factory=lambda driver_type="web": create_driver(
            headless=args.headless, browser=args.browser, driver_type=driver_type
        ),
        module_dir=str(module_dir),
    )
    results = executor.execute_all_cases()

    executor.close()

    print("-" * 60)
    print(f"✅ 执行完成")
    print(f"📊 总用例数: {len(results)}")

    passed = sum(1 for r in results if r.get('status', '').upper() == 'PASS')
    failed = sum(1 for r in results if r.get('status', '').upper() == 'FAIL')

    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")

    if results:
        print("\n📋 用例执行详情:")
        for r in results:
            status_icon = "✅" if r.get('status', '').upper() == 'PASS' else "❌"
            print(f"  {status_icon} {r.get('case_id', 'N/A')}: {r.get('title', 'N/A')} ({r.get('execution_time', 0)}s)")
            if r.get('error'):
                print(f"      错误: {r.get('error')}")

    print(f"\n📄 结果已保存到: {module_dir / 'result'}/")

if __name__ == "__main__":
    main()
