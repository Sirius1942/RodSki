"""JSONFormatter 单元测试

测试 core/json_formatter.py 中的 JSON 输出格式化器。
覆盖：format_success（全通过/有失败/有跳过）、format_error（含/不含上下文）、
      _format_step 内部格式化、to_json 序列化。
"""
import json
import pytest
from core.json_formatter import JSONFormatter


class TestFormatSuccess:
    """format_success —— 成功执行结果格式化"""

    def test_all_pass(self):
        """全部用例通过时，status 应为 success，exit_code 为 0"""
        results = [
            {"case_id": "c001", "title": "登录", "status": "PASS", "execution_time": 1.5},
            {"case_id": "c002", "title": "查询", "status": "PASS", "execution_time": 2.0},
        ]
        output = JSONFormatter.format_success(results, duration=3.5)

        assert output["status"] == "success"
        assert output["exit_code"] == 0
        # 摘要统计检查
        assert output["summary"]["total_steps"] == 2
        assert output["summary"]["passed"] == 2
        assert output["summary"]["failed"] == 0
        assert output["summary"]["skipped"] == 0
        assert output["summary"]["duration"] == "3.50s"

    def test_with_failure(self):
        """有失败用例时，status 应为 failed，exit_code 为 1"""
        results = [
            {"case_id": "c001", "status": "PASS", "execution_time": 1.0},
            {"case_id": "c002", "status": "FAIL", "error": "断言失败", "execution_time": 0.5},
        ]
        output = JSONFormatter.format_success(results, duration=1.5)

        assert output["status"] == "failed"
        assert output["exit_code"] == 1
        assert output["summary"]["passed"] == 1
        assert output["summary"]["failed"] == 1

    def test_with_skipped(self):
        """有跳过用例时，executed 应排除 skipped"""
        results = [
            {"case_id": "c001", "status": "PASS", "execution_time": 1.0},
            {"case_id": "c002", "status": "SKIP", "execution_time": 0},
        ]
        output = JSONFormatter.format_success(results, duration=1.0)

        assert output["summary"]["total_steps"] == 2
        assert output["summary"]["executed"] == 1  # total - skipped
        assert output["summary"]["skipped"] == 1

    def test_empty_results(self):
        """空结果列表应返回 success 且 total 为 0"""
        output = JSONFormatter.format_success([], duration=0.0)
        assert output["status"] == "success"
        assert output["summary"]["total_steps"] == 0

    def test_steps_format(self):
        """steps 数组中每个步骤应包含正确字段"""
        results = [{"case_id": "c001", "title": "测试", "status": "PASS",
                     "execution_time": 1.234, "screenshot_path": "/tmp/ss.png",
                     "recording_path": "recordings/c001_01.webm",
                     "recordings": [{"index": 1, "path": "recordings/c001_01.webm", "backend": "playwright"}]}]
        output = JSONFormatter.format_success(results, duration=1.234)

        step = output["steps"][0]
        assert step["index"] == 0
        assert step["case_id"] == "c001"
        assert step["title"] == "测试"
        assert step["status"] == "pass"       # 应转为小写
        assert step["duration"] == "1.23s"
        assert step["screenshot"] == "/tmp/ss.png"
        assert step["recording_path"] == "recordings/c001_01.webm"
        assert step["recordings"] == [{"index": 1, "path": "recordings/c001_01.webm", "backend": "playwright"}]

    def test_step_no_error_is_none(self):
        """步骤没有错误时 error 字段应为 None"""
        results = [{"case_id": "c001", "status": "PASS", "execution_time": 0}]
        output = JSONFormatter.format_success(results, duration=0)
        assert output["steps"][0]["error"] is None

    def test_step_with_error_value_is_passed_through(self):
        """步骤有错误时，error 字段应为原始错误内容（而不是 None 或错误的 key）"""
        results = [{"case_id": "c001", "status": "FAIL", "execution_time": 0,
                     "error": "断言失败：期望 200 实际 500"}]
        output = JSONFormatter.format_success(results, duration=0)
        assert output["steps"][0]["error"] == "断言失败：期望 200 实际 500"

    def test_step_missing_case_id_defaults_to_empty_string(self):
        """result 缺少 case_id 键时，step 的 case_id 应为空字符串而非 None"""
        results = [{"status": "PASS", "execution_time": 0}]
        output = JSONFormatter.format_success(results, duration=0)
        assert output["steps"][0]["case_id"] == ""

    def test_step_missing_title_defaults_to_empty_string(self):
        """result 缺少 title 键时，step 的 title 应为空字符串而非 None"""
        results = [{"case_id": "c001", "status": "PASS", "execution_time": 0}]
        output = JSONFormatter.format_success(results, duration=0)
        assert output["steps"][0]["title"] == ""

    def test_step_missing_status_defaults_to_empty_string(self):
        """result 缺少 status 键时，step 的 status 经 lower() 后应为空字符串"""
        results = [{"case_id": "c001", "execution_time": 0}]
        output = JSONFormatter.format_success(results, duration=0)
        assert output["steps"][0]["status"] == ""

    def test_step_missing_execution_time_defaults_to_zero(self):
        """result 缺少 execution_time 键时，duration 应基于默认值 0 计算为 '0.00s'"""
        results = [{"case_id": "c001", "status": "PASS"}]
        output = JSONFormatter.format_success(results, duration=0)
        assert output["steps"][0]["duration"] == "0.00s"

    def test_missing_status_key_not_counted(self):
        """result 缺少 status 键时不应崩溃，也不应计入任何分类"""
        results = [{"case_id": "c001", "execution_time": 1.0}]
        output = JSONFormatter.format_success(results, duration=1.0)
        assert output["summary"]["passed"] == 0
        assert output["summary"]["failed"] == 0
        assert output["summary"]["skipped"] == 0

    def test_variables_key_present(self):
        """输出应包含 variables 字段（当前始终为空字典）"""
        output = JSONFormatter.format_success([], duration=0.0)
        assert "variables" in output
        assert output["variables"] == {}

    def test_case_diagnosis_is_passed_through(self):
        diagnosis = {
            "failure_reason": "步骤超时",
            "recovery_action": {"action": "refresh", "data": ""},
        }
        output = JSONFormatter.format_success(
            [{
                "case_id": "c001",
                "status": "FAIL",
                "execution_time": 0,
                "case_diagnosis": diagnosis,
            }],
            duration=0,
        )

        assert output["steps"][0]["case_diagnosis"] == diagnosis


class TestFormatError:
    """format_error —— 错误信息格式化"""

    def test_basic_error(self):
        """基础错误格式化：包含 type 和 message"""
        err = ValueError("参数错误")
        output = JSONFormatter.format_error(err)

        assert output["status"] == "failed"
        assert output["exit_code"] == 1
        assert output["error"]["type"] == "ValueError"
        assert output["error"]["message"] == "参数错误"

    def test_error_with_case_and_step(self):
        """指定 case_id 和 step_index 时，应包含 failed_step"""
        err = RuntimeError("执行超时")
        output = JSONFormatter.format_error(err, case_id="c001", step_index=3)

        assert output["failed_step"]["case_id"] == "c001"
        assert output["failed_step"]["index"] == 3

    def test_error_with_context(self):
        """附加 context 信息"""
        err = Exception("未知错误")
        ctx = {"url": "http://test.com", "action": "navigate"}
        output = JSONFormatter.format_error(err, context=ctx)

        assert output["context"]["url"] == "http://test.com"
        assert output["context"]["action"] == "navigate"

    def test_error_no_case_no_step(self):
        """不指定 case_id/step_index 时不包含 failed_step"""
        output = JSONFormatter.format_error(Exception("err"))
        assert "failed_step" not in output

    def test_error_with_case_id_only(self):
        """只指定 case_id（不指定 step_index）时也应包含 failed_step

        用于区分 `case_id or step_index is not None` 与误写成 `and` 的情况：
        只有 case_id 为真时，or 条件仍成立，and 条件则不成立。
        """
        output = JSONFormatter.format_error(Exception("err"), case_id="c001")
        assert "failed_step" in output
        assert output["failed_step"]["case_id"] == "c001"
        assert "index" not in output["failed_step"]

    def test_error_with_step_index_only(self):
        """只指定 step_index（不指定 case_id）时也应包含 failed_step"""
        output = JSONFormatter.format_error(Exception("err"), step_index=0)
        assert "failed_step" in output
        assert output["failed_step"]["index"] == 0
        assert "case_id" not in output["failed_step"]


class TestToJson:
    """to_json —— 字典转 JSON 字符串"""

    def test_compact_json(self):
        """非 pretty 模式输出紧凑 JSON"""
        data = {"status": "success", "count": 1}
        result = JSONFormatter.to_json(data, pretty=False)
        parsed = json.loads(result)
        assert parsed == data
        # 紧凑模式不应有换行（除非值中有）
        assert "\n" not in result

    def test_pretty_json(self):
        """pretty 模式输出带缩进的 JSON"""
        data = {"status": "success"}
        result = JSONFormatter.to_json(data, pretty=True)
        assert "\n" in result  # pretty 模式有换行
        assert json.loads(result) == data

    def test_default_pretty_is_false(self):
        """不传 pretty 参数时，默认应为紧凑模式（无换行）"""
        data = {"status": "success", "count": 1}
        result = JSONFormatter.to_json(data)
        assert "\n" not in result

    def test_pretty_indent_is_two_spaces(self):
        """pretty 模式的缩进应为 2 个空格"""
        data = {"a": {"b": 1}}
        result = JSONFormatter.to_json(data, pretty=True)
        lines = result.split("\n")
        # 嵌套一层的行应以恰好 2 个空格开头
        indented = [l for l in lines if l.startswith("  ") and not l.startswith("   ")]
        assert indented, f"未找到 2 空格缩进行: {lines}"

    def test_chinese_characters(self):
        """JSON 应正确处理中文（ensure_ascii=False）"""
        data = {"message": "测试通过"}
        result = JSONFormatter.to_json(data)
        assert "测试通过" in result  # 中文不应被转义
