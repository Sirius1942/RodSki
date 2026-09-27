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
import xml.etree.ElementTree as ET
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from rodski.core.ski_executor import SKIExecutor, resolve_module_dir
    from rodski.core.config_manager import ConfigManager
    from rodski.core.logger import Logger
else:
    from .core.ski_executor import SKIExecutor, resolve_module_dir
    from .core.config_manager import ConfigManager
    from .core.logger import Logger


def create_driver(headless: bool = False, browser: str = "chromium", driver_type: str = "web"):
    if driver_type in ("macos", "windows"):
        if __package__ in (None, ""):
            from rodski.drivers.desktop_driver import DesktopDriver
        else:
            from .drivers.desktop_driver import DesktopDriver
        return DesktopDriver(target_platform=driver_type)
    if __package__ in (None, ""):
        from rodski.drivers.playwright_driver import PlaywrightDriver
    else:
        from .drivers.playwright_driver import PlaywrightDriver
    return PlaywrightDriver(headless=headless, browser=browser)


_BROWSER_ACTIONS = frozenset({
    'navigate', 'click', 'type', 'evaluate', 'hover', 'screenshot',
    'get', 'select', 'upload', 'launch', 'double_click', 'right_click',
    'upload_file', 'clear', 'get_text', 'assert',
})

# Actions that are intrinsically UI/browser operations.  They must trigger a
# browser even when a model.xml entry happens to carry a non-web type; the
# business graph, not model metadata, is the source of the operation kind.
_BUSINESS_UI_ACTIONS = frozenset({
    'navigate', 'click', 'type', 'evaluate', 'hover', 'screenshot',
    'get', 'select', 'upload', 'launch', 'double_click', 'right_click',
    'upload_file', 'clear', 'get_text',
})


def _business_model_driver_types(module_dir: Path) -> dict:
    """读取 business model 步骤用于区分接口模型与 UI 模型的 driver 类型。"""
    model_path = module_dir / "model" / "model.xml"
    try:
        root = ET.parse(model_path).getroot()
    except (ET.ParseError, OSError):
        return {}

    driver_types = {}
    for model in root.findall("model"):
        name = (model.get("name") or "").strip()
        if not name:
            continue
        driver_type = (model.get("driver_type") or "").strip().lower()
        if not driver_type:
            model_type = (model.get("type") or "ui").strip().lower()
            driver_type = model_type if model_type in {"interface", "database"} else "web"
        driver_types[name] = driver_type
    return driver_types


def _business_model_needs_browser(business_model: ET.Element, driver_types: dict) -> bool:
    """判断引用的业务模型是否包含需要浏览器的实际步骤。

    UI 动作本身足以说明需要浏览器，不被 model.xml 中偶然的 driver/type
    元数据覆盖。``assert`` 既可能是接口断言也可能是页面断言，因此只有在
    关联模型是 web/未知类型时才计入浏览器需求。
    """
    non_browser_drivers = {"interface", "database", "android", "ios", "mobile"}
    for step in business_model.iter("test_step"):
        action = (step.get("action") or "").strip().lower()
        if action in _BUSINESS_UI_ACTIONS:
            return True
        if action == "assert":
            model_name = (step.get("model") or "").strip()
            if not model_name or driver_types.get(model_name, "web") not in non_browser_drivers:
                return True
    return False


def _business_call_needs_browser(business_call: ET.Element, module_dir: Path, driver_types: dict) -> bool:
    """按 business/*.xml 中的 business_model@id 查找业务调用。

    一个 business XML 文件可以承载多个业务模型，ref 是模型 id 而不是
    文件名；因此不能只拼接 ``business/{ref}.xml``。
    """
    ref = (business_call.get("ref") or "").strip()
    if not ref or ref in {".", ".."} or "/" in ref or "\\" in ref:
        return False

    business_dir = module_dir / "business"
    if not business_dir.is_dir():
        return False
    for business_path in sorted(business_dir.glob("*.xml")):
        try:
            root = ET.parse(business_path).getroot()
        except (ET.ParseError, OSError):
            # 缺失或无效的业务模型会由执行阶段报告；扫描阶段不应因此中断。
            continue
        if root.tag != "business_models":
            continue
        for business_model in root.findall("business_model"):
            if (business_model.get("id") or "").strip() == ref:
                return _business_model_needs_browser(business_model, driver_types)
    return False


def _needs_browser(case_path: Path) -> bool:
    """扫描 case XML 及 business_call 引用，判断是否有需要浏览器的步骤。"""
    xml_files = list(case_path.glob("*.xml")) if case_path.is_dir() else ([case_path] if case_path.is_file() else [])
    module_dir = resolve_module_dir(case_path)
    driver_types = _business_model_driver_types(module_dir)

    for xml_file in xml_files:
        try:
            root = ET.parse(xml_file).getroot()
        except ET.ParseError:
            continue

        # 普通 test_step 保持原有判断规则。
        for step in root.iter('test_step'):
            action = (step.get('action') or '').strip().lower()
            if action in _BROWSER_ACTIONS:
                return True

        for business_call in root.iter("business_call"):
            if _business_call_needs_browser(business_call, module_dir, driver_types):
                return True
    return False


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


def apply_recording_args(config: ConfigManager, args) -> ConfigManager:
    recording = dict(config.get("recording", {}) or {})
    if args.record:
        recording["enabled"] = True
    if args.record_mode:
        recording["mode"] = args.record_mode
        if args.record_mode == "off":
            recording["enabled"] = False
    if args.record_scope:
        recording["scope"] = args.record_scope
    if args.record_monitor is not None:
        recording["monitor_id"] = args.record_monitor
    config.config["recording"] = recording
    return config


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
    parser.add_argument("--record", action="store_true", help="启用本次执行的视频录制")
    parser.add_argument("--record-mode", choices=["auto", "screen", "playwright", "off"],
                        default=None, help="录制模式 (默认读取配置)")
    parser.add_argument("--record-scope", choices=["target", "full_screen", "all_screens"],
                        default=None, help="屏幕录制范围 (默认读取配置)")
    parser.add_argument("--record-monitor", type=int, default=None,
                        help="屏幕录制 monitor_id，未指定则自动选择目标/主屏")
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
    needs_browser = _needs_browser(case_path)
    if needs_browser:
        print(f"🌐 浏览器: {args.browser}")
    else:
        print(f"⚡ 执行模式: 接口 / 浏览器: 未启用")
    print("-" * 60)

    if not model_file.exists():
        print(f"⚠️  模型文件不存在: {model_file}（将在无模型模式下运行）")

    driver = create_driver(headless=args.headless, browser=args.browser) if needs_browser else None

    config = apply_recording_args(ConfigManager(), args)

    executor = SKIExecutor(
        str(case_path),
        driver,
        config=config,
        driver_factory=(lambda driver_type="web": create_driver(
            headless=args.headless, browser=args.browser, driver_type=driver_type
        )) if needs_browser else None,
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

    # ski_run.py is a test runner.  Propagate the already calculated case
    # result to the shell so CI/scripts can distinguish a failed run from a
    # successful one.  Keep the existing output and success behavior intact.
    return 1 if failed > 0 else 0

if __name__ == "__main__":
    sys.exit(main())
