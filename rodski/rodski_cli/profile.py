"""性能分析命令"""
import sys
from pathlib import Path
from ..core.profiler import Profiler
from ..core.performance import set_profiler
from ..core.task_executor import TaskExecutor


def setup_parser(subparsers):
    parser = subparsers.add_parser("profile", help="执行用例并生成性能报告")
    parser.add_argument("case_file", help="用例文件路径")
    parser.add_argument("--output", default="logs/performance", help="报告输出目录")


def handle(args):
    """执行性能分析"""
    case_file = Path(args.case_file)
    if not case_file.exists():
        print(f"错误: 用例文件不存在: {case_file}", file=sys.stderr)
        return 1
    
    # 创建 Profiler
    profiler = Profiler()
    set_profiler(profiler)
    
    print(f"🔍 开始性能分析: {case_file}")
    
    # 执行用例
    executor = TaskExecutor()
    try:
        result = executor.run_case(str(case_file))
        
        # 生成报告
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        json_path = output_dir / "profile.json"
        html_path = output_dir / "profile.html"
        
        profiler.save_json(str(json_path))
        profiler.save_html(str(html_path))
        
        stats = profiler.get_stats()
        print(f"\n✅ 性能分析完成")
        print(f"   总操作: {stats.get('total_operations', 0)}")
        print(f"   总耗时: {stats.get('total_time', 0):.2f}s")
        print(f"   平均耗时: {stats.get('avg_time', 0):.3f}s")
        print(f"   慢操作: {stats.get('slow_operations', 0)}")
        print(f"\n📊 报告已生成:")
        print(f"   JSON: {json_path}")
        print(f"   HTML: {html_path}")
        
        return 0 if result else 1
        
    except Exception as e:
        print(f"❌ 执行失败: {e}", file=sys.stderr)
        return 1
