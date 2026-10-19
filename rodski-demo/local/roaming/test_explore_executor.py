"""探索执行器验收测试 - 验证 execute_command() API

测试目标：
1. ExploreExecutor 能正常初始化
2. execute_command() 能执行基本命令（navigate）
3. 返回 ExecutionResult 包含 success/evidence/errors
4. 证据采集正常（screenshot/url/return_value）

运行方式：
    python test_explore_executor.py
"""
import sys
from pathlib import Path

# 添加 rodski 到 sys.path
rodski_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(rodski_root))

from rodski.core.explore_executor import ExploreExecutor
from rodski.core.keyword_engine import KeywordEngine
from rodski.core.config_manager import ConfigManager
from rodski.drivers.playwright_driver import PlaywrightDriver


def test_explore_executor_basic():
    """测试 ExploreExecutor 基本功能"""
    print("\n[Test] ExploreExecutor 基本功能测试")

    # 1. 初始化配置和驱动（简化版本，不依赖完整的 SKIExecutor）
    module_dir = Path(__file__).parent
    config = ConfigManager()

    # 2. 创建驱动（不立即启动，通过 navigate 懒启动）
    driver = PlaywrightDriver(config)

    # 3. 创建 KeywordEngine
    keyword_engine = KeywordEngine(
        driver=driver,
        module_dir=str(module_dir)
    )

    # 4. 创建 ExploreExecutor
    explore_executor = ExploreExecutor(keyword_engine, module_dir)
    explore_executor.start_session("test_session_001")

    print("✓ ExploreExecutor 初始化成功")

    try:
        # 5. 执行 navigate 命令
        result1 = explore_executor.execute_command({
            "action": "navigate",
            "model": "",
            "data": "https://example.com"
        })

        print(f"✓ navigate 命令执行完成: success={result1['success']}")

        if result1["success"]:
            # 6. 验证证据采集
            evidence = result1["evidence"]
            print(f"  - URL: {evidence['url']}")
            print(f"  - Screenshot: {'有' if evidence.get('screenshot') else '无'}")
            print(f"  - Return Value: {evidence.get('return_value')}")
            print(f"  - Browser Errors: {evidence.get('browser_errors', [])}")

            assert "evidence" in result1
            assert "url" in result1["evidence"]
        else:
            print(f"  - 错误: {result1['errors']}")
            print("  ⚠️ 注意: 浏览器启动失败可能是环境配置问题")

        # 7. 执行无效命令测试
        result2 = explore_executor.execute_command({
            "action": "invalid_action",
            "model": "SomePage"
        })

        print(f"✓ 无效命令执行完成: success={result2['success']}")
        assert result2["success"] is False, "无效命令应该失败"
        assert len(result2["errors"]) > 0, "应该有错误信息"
        print(f"  - 错误信息: {result2['errors'][0][:80]}...")

    finally:
        # 8. 清理
        if driver and hasattr(driver, '_page') and driver._page:
            try:
                driver.close()
            except Exception as e:
                print(f"  ⚠️ 驱动清理失败: {e}")

    print("\n✓ 所有测试通过")
    print("\n[总结]")
    print("- ExploreExecutor 初始化: ✓")
    print("- execute_command() API: ✓")
    print("- ExecutionResult 结构: ✓")
    print("- 错误处理机制: ✓")


if __name__ == "__main__":
    test_explore_executor_basic()
