"""Iteration 05 活文档增强 - 使用示例

演示如何使用新的元数据和增强结果功能
"""
from pathlib import Path
from core.case_parser import CaseParser
from core.result_writer import ResultWriter
from core.metadata_writer import MetadataWriter
from core.execution_stats import ExecutionStats


def example_parse_case_with_metadata():
    """示例：解析带元数据的用例"""
    parser = CaseParser("data/case/example_with_metadata.xml")
    cases = parser.parse_cases()

    for case in cases:
        print(f"用例: {case['case_id']} - {case['title']}")
        metadata = case.get('metadata', {})
        if metadata:
            print(f"  创建者: {metadata.get('created_by')}")
            print(f"  成功率: {metadata.get('success_rate')}")


def example_write_enhanced_result():
    """示例：写入增强的结果（包含步骤详情和变量）"""
    writer = ResultWriter("data/result")

    result = {
        "case_id": "TC001",
        "title": "登录测试",
        "status": "PASS",
        "execution_time": "3.45s",
        "start_time": "2026-03-28 15:30:00",
        "end_time": "2026-03-28 15:30:03",
        "steps": [
            {"phase": "test_case", "index": 0, "action": "navigate",
             "data": "https://example.com", "status": "PASS", "execution_time": "1.2s"},
            {"phase": "test_case", "index": 1, "action": "type",
             "model": "username", "data": "testuser", "status": "PASS", "execution_time": "0.5s"}
        ],
        "variables": {"username": "testuser", "url": "https://example.com"}
    }

    writer.write_results([result])
    print(f"结果已写入: {writer.current_run_dir}")


def example_update_metadata():
    """示例：更新用例元数据"""
    case_file = Path("data/case/example_with_metadata.xml")

    MetadataWriter.update_metadata(case_file, "TC001", {
        "updated_by": "李四",
        "updated_at": "2026-03-29 10:00:00"
    })
    print("元数据已更新")


def example_calculate_stats():
    """示例：计算执行统计"""
    result_dir = Path("data/result")

    # 计算单个用例成功率
    success_rate = ExecutionStats.calculate_case_success_rate(result_dir, "TC001")
    if success_rate is not None:
        print(f"TC001 成功率: {success_rate:.1f}%")

    # 获取所有用例统计
    all_stats = ExecutionStats.get_all_case_stats(result_dir)
    for case_id, stats in all_stats.items():
        print(f"{case_id}: {stats['success_rate']:.1f}% ({stats['total_runs']} 次)")


if __name__ == "__main__":
    print("=== Iteration 05 功能演示 ===\n")

    print("1. 解析带元数据的用例")
    example_parse_case_with_metadata()

    print("\n2. 写入增强结果")
    example_write_enhanced_result()

    print("\n3. 更新元数据")
    example_update_metadata()

    print("\n4. 计算统计数据")
    example_calculate_stats()
