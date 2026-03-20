"""百度 UI 自动化测试 - 使用 RodSki 框架"""
import sys
from pathlib import Path

# 添加项目根目录到 sys.path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from data.excel_parser import ExcelParser
from core.task_executor import TaskExecutor
from core.keyword_engine import KeywordEngine
from core.logger import Logger
from drivers.playwright_driver import PlaywrightDriver


def run_test(sheet_name=None, headless=False):
    case_file = Path(__file__).parent / "baidu_test_case.xlsx"

    logger = Logger(console=True)
    logger.info(f"加载测试用例: {case_file}")

    # 解析 Excel
    parser = ExcelParser(str(case_file))
    errors = parser.validate()
    if errors:
        for e in errors:
            logger.error(f"用例校验失败: {e}")
        return False

    sheets = parser.get_sheet_names()
    logger.info(f"可用工作表: {sheets}")

    raw_data = parser.parse(sheet_name)
    logger.info(f"解析到 {len(raw_data)} 条步骤")

    # 初始化驱动
    driver = PlaywrightDriver(headless=headless)

    try:
        engine = KeywordEngine(driver)
        executor = TaskExecutor(engine, max_retries=1, logger=logger)
        steps = executor.load_case(raw_data)

        logger.info(f"开始执行测试 (共 {len(steps)} 步)")
        success = executor.execute_steps(steps)

        summary = executor.get_summary()
        logger.info(
            f"测试完成: {summary['passed']}/{summary['total']} 通过, "
            f"通过率: {summary['pass_rate']}%, "
            f"耗时: {summary['duration']}s"
        )

        # 保存结果
        result_path = str(Path(__file__).parent / "test_results.json")
        executor.save_results(result_path)
        logger.info(f"结果已保存: {result_path}")

        return success
    finally:
        driver.close()
        parser.close()


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="百度 UI 自动化测试")
    ap.add_argument("--sheet", default=None, help="指定工作表 (默认第一个)")
    ap.add_argument("--headless", action="store_true", help="无头模式运行")
    args = ap.parse_args()

    ok = run_test(sheet_name=args.sheet, headless=args.headless)
    sys.exit(0 if ok else 1)
