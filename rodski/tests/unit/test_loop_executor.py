"""LoopExecutor / LoopParser 单元测试

测试 core/loop_executor.py 中的循环解析器和执行器。
覆盖：LoopType 枚举、LoopConfiguration 数据类、LoopParser.parse() 各种格式、
      LoopExecutor 的四种循环模式（fixed / for_each / until / while）。
"""
import pytest
from unittest.mock import MagicMock, patch
from core.loop_executor import LoopType, LoopConfiguration, LoopParser, LoopExecutor


# =====================================================================
# LoopType 枚举
# =====================================================================
class TestLoopType:
    """循环类型枚举值验证"""

    def test_all_types_exist(self):
        """应包含四种循环类型"""
        assert LoopType.FIXED.value == "fixed"
        assert LoopType.FOR_EACH.value == "for_each"
        assert LoopType.UNTIL.value == "until"
        assert LoopType.WHILE.value == "while"


# =====================================================================
# LoopConfiguration 数据类
# =====================================================================
class TestLoopConfiguration:
    """循环配置数据类默认值验证"""

    def test_default_values(self):
        """默认值应符合预期"""
        config = LoopConfiguration(loop_type=LoopType.FIXED)
        assert config.count is None
        assert config.items is None
        assert config.item_var == "item"        # 默认迭代变量名
        assert config.index_var == "index"      # 默认索引变量名
        assert config.condition is None
        assert config.max_iterations == 1000    # 默认最大迭代次数
        assert config.break_on_fail is False    # 默认失败不中断


# =====================================================================
# LoopParser.parse()
# =====================================================================
class TestLoopParser:
    """循环字符串解析 —— 支持四种格式"""

    def test_fixed_count(self):
        """纯数字字符串解析为 FIXED 类型"""
        config = LoopParser.parse("5", {})
        assert config.loop_type == LoopType.FIXED
        assert config.count == 5

    def test_for_each_with_variable(self):
        """for item in ${list} 解析为 FOR_EACH 类型"""
        variables = {"users": ["alice", "bob", "charlie"]}
        config = LoopParser.parse("for user in ${users}", variables)
        assert config.loop_type == LoopType.FOR_EACH
        assert config.item_var == "user"
        assert config.items == ["alice", "bob", "charlie"]

    def test_for_each_non_list_variable(self):
        """for 循环变量不是列表时，应包装为单元素列表"""
        variables = {"name": "alice"}
        config = LoopParser.parse("for item in ${name}", variables)
        assert config.loop_type == LoopType.FOR_EACH
        assert config.items == ["alice"]

    def test_for_each_missing_variable(self):
        """for 循环变量不存在时，items 应为空列表"""
        config = LoopParser.parse("for item in ${missing}", {})
        assert config.loop_type == LoopType.FOR_EACH
        assert config.items == []

    def test_until_with_max(self):
        """until condition max=N 解析"""
        config = LoopParser.parse("until status == 200 max=50", {})
        assert config.loop_type == LoopType.UNTIL
        assert config.condition == "status == 200"
        assert config.max_iterations == 50

    def test_until_without_max(self):
        """until 不指定 max 时默认 1000"""
        config = LoopParser.parse("until done", {})
        assert config.loop_type == LoopType.UNTIL
        assert config.condition == "done"
        assert config.max_iterations == 1000

    def test_while_with_max(self):
        """while condition max=N 解析"""
        config = LoopParser.parse("while running max=100", {})
        assert config.loop_type == LoopType.WHILE
        assert config.condition == "running"
        assert config.max_iterations == 100

    def test_while_without_max(self):
        """while 不指定 max 时默认 1000"""
        config = LoopParser.parse("while active", {})
        assert config.loop_type == LoopType.WHILE
        assert config.condition == "active"
        assert config.max_iterations == 1000

    def test_invalid_format_raises(self):
        """无效格式应抛出 ValueError"""
        with pytest.raises(ValueError, match="Invalid loop format"):
            LoopParser.parse("invalid loop spec", {})

    def test_strip_whitespace(self):
        """应自动去除前后空白"""
        config = LoopParser.parse("  3  ", {})
        assert config.loop_type == LoopType.FIXED
        assert config.count == 3


# =====================================================================
# LoopExecutor —— 四种循环模式
# =====================================================================
class TestLoopExecutorFixed:
    """FIXED 循环 —— 执行固定次数"""

    def test_fixed_loop_success(self):
        """固定次数循环：全部成功时返回 N 个 pass 结果"""
        ski = MagicMock()
        ski._variables = {}
        ski.execute_step.return_value = None  # 执行成功

        executor = LoopExecutor(ski)
        config = LoopConfiguration(loop_type=LoopType.FIXED, count=3)
        step = {"action": "wait", "model": "", "data": "1"}

        results = executor.execute_loop(step, config)
        # 检查执行了 3 次
        assert len(results) == 3
        assert all(r["status"] == "pass" for r in results)
        assert ski.execute_step.call_count == 3

    def test_fixed_loop_with_failure_no_break(self):
        """固定循环失败但 break_on_fail=False 时继续执行"""
        ski = MagicMock()
        ski._variables = {}
        ski.execute_step.side_effect = [None, RuntimeError("fail"), None]

        executor = LoopExecutor(ski)
        config = LoopConfiguration(loop_type=LoopType.FIXED, count=3, break_on_fail=False)
        step = {"action": "wait", "model": "", "data": "1"}

        results = executor.execute_loop(step, config)
        assert len(results) == 3
        assert results[0]["status"] == "pass"
        assert results[1]["status"] == "fail"
        assert results[2]["status"] == "pass"

    def test_fixed_loop_break_on_fail(self):
        """固定循环 break_on_fail=True 时失败立即中断"""
        ski = MagicMock()
        ski._variables = {}
        ski.execute_step.side_effect = [None, RuntimeError("fail"), None]

        executor = LoopExecutor(ski)
        config = LoopConfiguration(loop_type=LoopType.FIXED, count=3, break_on_fail=True)
        step = {"action": "wait", "model": "", "data": "1"}

        results = executor.execute_loop(step, config)
        # 第 2 次失败后应中断，不执行第 3 次
        assert len(results) == 2
        assert results[1]["status"] == "fail"

    def test_fixed_loop_sets_index_var(self):
        """固定循环应在每次迭代中设置 index 变量"""
        ski = MagicMock()
        ski._variables = {}
        captured_indices = []
        def capture_index(step, label):
            captured_indices.append(ski._variables.get("index"))
        ski.execute_step.side_effect = capture_index

        executor = LoopExecutor(ski)
        config = LoopConfiguration(loop_type=LoopType.FIXED, count=3)
        executor.execute_loop({"action": "wait"}, config)
        assert captured_indices == [0, 1, 2]


class TestLoopExecutorForEach:
    """FOR_EACH 循环 —— 遍历列表"""

    def test_for_each_iterates_items(self):
        """for_each 应遍历所有 items"""
        ski = MagicMock()
        ski._variables = {}

        executor = LoopExecutor(ski)
        config = LoopConfiguration(
            loop_type=LoopType.FOR_EACH,
            items=["a", "b", "c"],
            item_var="letter"
        )
        results = executor.execute_loop({"action": "wait"}, config)
        assert len(results) == 3
        # 验证每个结果都记录了 item
        assert results[0]["item"] == "a"
        assert results[1]["item"] == "b"
        assert results[2]["item"] == "c"

    def test_for_each_empty_items(self):
        """items 为空列表时不执行"""
        ski = MagicMock()
        ski._variables = {}

        executor = LoopExecutor(ski)
        config = LoopConfiguration(loop_type=LoopType.FOR_EACH, items=[])
        results = executor.execute_loop({"action": "wait"}, config)
        assert len(results) == 0


class TestLoopExecutorUntil:
    """UNTIL 循环 —— 条件满足时停止"""

    def test_until_stops_when_condition_true(self):
        """until 循环在条件为 True 时停止"""
        ski = MagicMock()
        ski._variables = {"done": False}

        def flip_after_two(step, label):
            if ski.execute_step.call_count >= 2:
                ski._variables["done"] = True

        ski.execute_step.side_effect = flip_after_two

        executor = LoopExecutor(ski)
        config = LoopConfiguration(
            loop_type=LoopType.UNTIL,
            condition="done == True",
            max_iterations=10
        )
        results = executor.execute_loop({"action": "wait"}, config)
        # 条件在第 2 次执行后变为 True，第 3 次循环开头检测到 → 执行了 2 次
        assert len(results) == 2

    def test_until_max_iterations_limit(self):
        """until 循环应受 max_iterations 限制"""
        ski = MagicMock()
        ski._variables = {}
        ski.execute_step.return_value = None

        executor = LoopExecutor(ski)
        config = LoopConfiguration(
            loop_type=LoopType.UNTIL,
            condition="never_true == True",
            max_iterations=5
        )
        results = executor.execute_loop({"action": "wait"}, config)
        assert len(results) == 5  # 达到最大次数后停止


class TestLoopExecutorWhile:
    """WHILE 循环 —— 条件为 True 时继续"""

    def test_while_executes_while_true(self):
        """while 循环在条件为 True 时持续执行"""
        ski = MagicMock()
        ski._variables = {"running": True}
        call_count = [0]

        def stop_after_three(step, label):
            call_count[0] += 1
            if call_count[0] >= 3:
                ski._variables["running"] = False

        ski.execute_step.side_effect = stop_after_three

        executor = LoopExecutor(ski)
        config = LoopConfiguration(
            loop_type=LoopType.WHILE,
            condition="running == True",
            max_iterations=10
        )
        results = executor.execute_loop({"action": "wait"}, config)
        assert len(results) == 3

    def test_while_condition_initially_false(self):
        """while 条件一开始就为 False 时不执行"""
        ski = MagicMock()
        ski._variables = {"running": False}

        executor = LoopExecutor(ski)
        config = LoopConfiguration(
            loop_type=LoopType.WHILE,
            condition="running == True",
            max_iterations=10
        )
        results = executor.execute_loop({"action": "wait"}, config)
        assert len(results) == 0
