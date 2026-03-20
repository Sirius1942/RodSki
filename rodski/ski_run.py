#!/usr/bin/env python3
"""RodSki CLI - 运行测试用例"""
import sys
import argparse
from pathlib import Path
from core.ski_executor import SKIExecutor
from drivers.playwright_driver import PlaywrightDriver


def create_driver(headless: bool = False, browser: str = "chromium"):
    """驱动工厂函数：创建新的 Playwright 驱动"""
    return PlaywrightDriver(headless=headless, browser=browser)


def main():
    parser = argparse.ArgumentParser(description="RodSki 测试运行器")
    parser.add_argument("case_file", help="用例Excel路径")
    parser.add_argument("--browser", choices=["chromium", "firefox", "webkit"],
                        default="chromium", help="浏览器类型 (默认: chromium)")
    parser.add_argument("--headless", action="store_true", help="无头模式")
    args = parser.parse_args()

    case_file = Path(args.case_file)
    if not case_file.exists():
        print(f"错误: 用例文件不存在: {case_file}")
        sys.exit(1)

    # 推断 model.xml 路径
    model_file = case_file.parent.parent / "model" / "model.xml"
    if not model_file.exists():
        print(f"错误: 模型文件不存在: {model_file}")
        sys.exit(1)

    print(f"🚀 RodSki 框架启动")
    print(f"📋 用例文件: {case_file}")
    print(f"🏗️  模型文件: {model_file}")
    print(f"🌐 浏览器: {args.browser}")
    print("-" * 60)

    # 初始化驱动
    driver = create_driver(headless=args.headless, browser=args.browser)

    # 执行测试（传入 driver_factory 支持驱动自动重建）
    executor = SKIExecutor(
        str(case_file),
        str(model_file),
        driver,
        driver_factory=lambda: create_driver(headless=args.headless, browser=args.browser)
    )
    results = executor.execute_all_cases()
    
    # 关闭执行器（内部会关闭驱动）
    executor.close()
    
    print("-" * 60)
    print(f"✅ 执行完成")
    print(f"📊 总用例数: {len(results)}")
    
    # 状态统计 - 兼容大小写
    passed = sum(1 for r in results if r.get('status', '').upper() == 'PASS')
    failed = sum(1 for r in results if r.get('status', '').upper() == 'FAIL')
    
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    
    # 打印每个用例的执行结果
    if results:
        print("\n📋 用例执行详情:")
        for r in results:
            status_icon = "✅" if r.get('status', '').upper() == 'PASS' else "❌"
            print(f"  {status_icon} {r.get('case_id', 'N/A')}: {r.get('title', 'N/A')} ({r.get('execution_time', 0)}s)")
            if r.get('error'):
                print(f"      错误: {r.get('error')}")

if __name__ == "__main__":
    main()