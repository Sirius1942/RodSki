"""测试用例静态解释器 - 将 XML 测试用例解析为人类可读的步骤说明

支持三阶段（pre_process / test_case / post_process）。
支持关键字：navigate, launch, type, click, verify, wait, screenshot,
           get_text, clear, upload_file, assert, DB, run, send, if, loop 等。

使用方式:
    python3 cli_main.py explain examples/product/DEMO/demo_site/case/demo_case_form.xml

Python API:
    from core.test_case_explainer import TestCaseExplainer
    explainer = TestCaseExplainer(model_parser=mp, data_manager=dm)
    print(explainer.explain_case("path/to/case.xml"))
"""
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional

from core.case_parser import CaseParser
from core.xml_schema_validator import RodskiXmlValidator


# 敏感字段名（自动脱敏）
SENSITIVE_FIELDS = {
    'password', 'pwd', 'passwd', 'secret', 'token', 'apikey',
    'api_key', 'auth', 'authorization', 'credential',
}


class TestCaseExplainer:
    """测试用例静态解释器"""

    def __init__(self, model_parser=None, data_manager=None):
        """
        Args:
            model_parser: ModelParser 实例，用于解析模型定位器
            data_manager: DataTableParser 实例，用于解析数据表
        """
        self.model_parser = model_parser
        self.data_manager = data_manager

    # ── 公共 API ─────────────────────────────────────────────────

    def explain_case(self, case_xml_path: str) -> str:
        """对单个测试用例文件生成人类可读说明

        Args:
            case_xml_path: case XML 文件路径

        Returns:
            格式化的可读文本
        """
        path = Path(case_xml_path)
        if not path.exists():
            return f"错误: 文件不存在 → {case_xml_path}"

        try:
            validator = RodskiXmlValidator()
            validator.validate_file(path, validator.KIND_CASE)
        except Exception:
            pass  # 允许未注册文件，尝试直接解析

        cases = self._parse_cases(path)
        if not cases:
            return f"警告: 未找到任何启用的用例 → {case_xml_path}"

        lines = []
        for case in cases:
            lines.append(self._explain_case_struct(case))
            lines.append("")  # 空行分隔

        return "\n".join(lines).rstrip()

    def explain_steps(self, steps: List[Dict[str, str]], phase: str = "test_case") -> str:
        """对步骤列表生成说明（无需解析文件）"""
        if not steps:
            return f"[{phase}] 无步骤"
        lines = []
        for i, step in enumerate(steps, 1):
            total = len(steps)
            lines.append(self._explain_single_step(step, i, total))
        return "\n".join(lines)

    # ── 核心解析 ─────────────────────────────────────────────────

    def _parse_cases(self, xml_path: Path) -> List[Dict[str, Any]]:
        """解析用例文件（不依赖完整 CaseParser，保持自包含）"""
        try:
            tree = ET.parse(xml_path)
        except ET.ParseError as e:
            return []
        root = tree.getroot()
        cases = []
        for case_node in root.findall('case'):
            execute = case_node.get('execute', '否').strip()
            if execute != '是':
                continue
            cases.append({
                'case_id': case_node.get('id', ''),
                'title': case_node.get('title', ''),
                'description': case_node.get('description', ''),
                'pre_process': self._parse_phase_steps(case_node.find('pre_process')),
                'test_case': self._parse_phase_steps(case_node.find('test_case')),
                'post_process': self._parse_phase_steps(case_node.find('post_process')),
            })
        return cases

    def _parse_phase_steps(self, phase_node) -> List[Dict[str, str]]:
        if phase_node is None:
            return []
        steps = []
        for el in phase_node.findall('test_step'):
            steps.append({
                'action': str(el.get('action', '') or '').strip(),
                'model': str(el.get('model', '') or '').strip(),
                'data': str(el.get('data', '') or '').strip(),
            })
        return [s for s in steps if s['action']]

    # ── 格式化 ───────────────────────────────────────────────────

    def _explain_case_struct(self, case: Dict) -> str:
        lines = []
        lines.append(f"用例: {case['case_id']} - {case['title']}")
        if case.get('description'):
            lines.append(f"描述: {case['description']}")

        for phase_key, phase_label in (
            ('pre_process', 'pre_process（前置）'),
            ('test_case', 'test_case（主体）'),
            ('post_process', 'post_process（后置）'),
        ):
            steps = case.get(phase_key) or []
            if not steps:
                continue
            lines.append(f"\n阶段: {phase_label}")
            for i, step in enumerate(steps, 1):
                lines.append(self._explain_single_step(step, i, len(steps)))

        return "\n".join(lines)

    def _explain_single_step(
        self, step: Dict[str, str], index: int, total: int
    ) -> str:
        action = step.get('action', '')
        model = step.get('model', '')
        data = step.get('data', '')

        lines = []
        lines.append(f"  步骤 {index}/{total}: {action}")

        text = self._explain_keyword(action, model, data)
        for line in text.split('\n'):
            lines.append(f"    → {line}")

        return "\n".join(lines)

    def _explain_keyword(
        self, action: str, model: str, data: str
    ) -> str:
        """根据关键字生成人类可读描述"""
        action = action.lower()
        handler = {
            'navigate': self._explain_navigate,
            'launch': self._explain_launch,
            'type': self._explain_type,
            'click': self._explain_click,
            'verify': self._explain_verify,
            'wait': self._explain_wait,
            'screenshot': self._explain_screenshot,
            'get_text': self._explain_get_text,
            'get': self._explain_get,
            'clear': self._explain_clear,
            'upload_file': self._explain_upload_file,
            'assert': self._explain_assert,
            'db': self._explain_db,
            'run': self._explain_run,
            'send': self._explain_send,
            'close': lambda m, d: "关闭当前浏览器窗口",
            'set': self._explain_set,
            'verify_image': self._explain_verify_image,
            'if': self._explain_if,
            'loop': self._explain_loop,
        }.get(action)

        if handler:
            return handler(model, data)

        # 通用兜底
        parts = []
        if model:
            parts.append(f"模型={model}")
        if data:
            parts.append(f"数据={data}")
        if not parts:
            return "(无参数)"
        return ", ".join(parts)

    # ── 各关键字解释 ─────────────────────────────────────────────

    def _explain_navigate(self, model: str, data: str) -> str:
        if data:
            return f"导航到网址 {data}"
        return "导航到网址（URL 未指定）"

    def _explain_launch(self, model: str, data: str) -> str:
        if model and data:
            return f"启动应用或打开页面（模型={model}, 数据={data}）"
        if data:
            if data.startswith(('http://', 'https://')):
                return f"打开网页: {data}"
            return f"启动应用: {data}"
        return "启动应用或打开页面（参数不完整）"

    def _explain_type(self, model: str, data: str) -> str:
        """type 关键字解释，支持批量和单字段"""
        if model and data:
            # 批量模式：从模型 + 数据表解析
            return self._explain_type_batch(model, data)
        return self._explain_type_single(model, data)

    def _explain_type_batch(self, model_name: str, data_id: str) -> str:
        """批量输入解释"""
        lines = [f"使用模型 {model_name} 从数据 {data_id} 批量输入"]

        resolved = self._resolve_fields(model_name, data_id)
        if not resolved:
            lines.append(f"  ⚠️  未找到模型 '{model_name}' 或数据 '{data_id}'")
            return "\n".join(lines)

        model = self.model_parser.get_model(model_name) if self.model_parser else {}
        lines.append(f"  模型: {model_name} (定位器列表)")
        lines.append(f"  数据: DataID={data_id}")
        lines.append("  字段解析:")

        for field_name, (locator, value) in resolved.items():
            display = self._mask_sensitive(field_name, value)
            lines.append(f"    - {field_name}: {display} → 输入到 [{locator}]")

        return "\n".join(lines)

    def _explain_type_single(self, model: str, data: str) -> str:
        if model:
            return f"向 {model} 输入 '{self._mask_or_value(data)}'"
        return f"向定位器输入 '{self._mask_or_value(data)}'"

    def _explain_click(self, model: str, data: str) -> str:
        if model:
            return f"点击元素: {model}"
        if data:
            return f"点击定位器: {data}"
        return "点击元素（定位器未指定）"

    def _explain_verify(self, model: str, data: str) -> str:
        if model and data:
            return self._explain_verify_batch(model, data)
        if data:
            return f"验证页面包含文本: '{self._mask_or_value(data)}'"
        return "验证页面内容（参数不完整）"

    def _explain_verify_batch(self, model_name: str, data_id: str) -> str:
        """批量验证解释"""
        verify_table = f"{model_name}_verify"
        lines = [f"批量验证模型 {model_name}，期望数据={data_id}"]
        lines.append(f"  验证数据表: {verify_table}")

        if not self.data_manager:
            lines.append("  ⚠️  未提供 data_manager，跳过字段详情")
            return "\n".join(lines)

        data_row = self.data_manager.get_data(verify_table, data_id)
        if not data_row:
            lines.append(f"  ⚠️  未找到数据: 表={verify_table}, DataID={data_id}")
            return "\n".join(lines)

        model = self.model_parser.get_model(model_name) if self.model_parser else {}
        lines.append("  字段验证:")
        for field_name, expected in data_row.items():
            loc = ""
            if model and field_name in model:
                elem = model[field_name]
                loc = f"[{elem.get('type', '?')}={elem.get('value', '?')}]"
            display = self._mask_sensitive(field_name, expected)
            lines.append(f"    - {field_name} {loc}: 期望 '{display}'")

        return "\n".join(lines)

    def _explain_wait(self, model: str, data: str) -> str:
        secs = data or model or "?"
        return f"等待 {secs} 秒"

    def _explain_screenshot(self, model: str, data: str) -> str:
        if data:
            return f"截图保存为: {data}"
        return "截图"

    def _explain_get_text(self, model: str, data: str) -> str:
        if data:
            return f"获取 {data} 的文本内容"
        if model:
            return f"获取模型 {model} 的文本内容"
        return "获取文本内容"

    def _explain_get(self, model: str, data: str) -> str:
        return self._explain_get_text(model, data)

    def _explain_clear(self, model: str, data: str) -> str:
        if data:
            return f"清空输入框: {data}"
        if model:
            return f"清空输入框: {model}"
        return "清空输入框"

    def _explain_upload_file(self, model: str, data: str) -> str:
        if data and model:
            return f"上传文件: {data} → {model}"
        if data:
            return f"上传文件: {data}"
        return "上传文件"

    def _explain_assert(self, model: str, data: str) -> str:
        parts = []
        if model:
            parts.append(f"定位器={model}")
        if data:
            parts.append(f"预期内容='{self._mask_or_value(data)}'")
        if parts:
            return "断言: " + ", ".join(parts)
        return "执行断言"

    def _explain_db(self, model: str, data: str) -> str:
        parts = []
        if model:
            parts.append(f"连接={model}")
        if data:
            parts.append(f"SQL={data}")
        if parts:
            return "数据库操作: " + ", ".join(parts)
        return "执行数据库操作"

    def _explain_run(self, model: str, data: str) -> str:
        if model and data:
            return f"运行代码模块: 项目={model}, 脚本={data}"
        if data:
            return f"运行代码: {data}"
        return "执行代码"

    def _explain_send(self, model: str, data: str) -> str:
        if model and data:
            return f"发送 HTTP 请求: 模型={model}, DataID={data}"
        if model:
            return f"发送 HTTP 请求: 模型={model}"
        return "发送 HTTP 请求"

    def _explain_set(self, model: str, data: str) -> str:
        if model and data:
            return f"设置变量: {model} = '{self._mask_or_value(data)}'"
        return "设置变量"

    def _explain_verify_image(self, model: str, data: str) -> str:
        if data and model:
            return f"AI 截图验证: 截图={data}, 预期描述={model}"
        if data:
            return f"AI 截图验证: 截图={data}"
        return "AI 截图验证"

    def _explain_if(self, model: str, data: str) -> str:
        if model and data:
            return f"条件判断: {model} = {data}"
        if model:
            return f"条件判断: {model}"
        return "条件判断"

    def _explain_loop(self, model: str, data: str) -> str:
        if model and data:
            return f"循环执行 {data} 次，变量为 {model}"
        if data:
            return f"循环执行 {data} 次"
        return "循环执行"

    # ── 数据解析 ─────────────────────────────────────────────────

    def _resolve_fields(
        self, model_name: str, data_id: str
    ) -> Dict[str, tuple]:
        """解析模型字段 + 数据表值，返回 {字段名: (locator_str, value)}"""
        if not self.model_parser or not self.data_manager:
            return {}

        model = self.model_parser.get_model(model_name)
        if not model:
            return {}

        table_name = model_name
        data_row = self.data_manager.get_data(table_name, data_id)
        if not data_row:
            return {}

        result = {}
        for field_name, value in data_row.items():
            if field_name not in model:
                continue
            elem = model[field_name]
            loc_type = elem.get('type', '')
            loc_value = elem.get('value', '')
            locator_str = f"{loc_type}={loc_value}"
            result[field_name] = (locator_str, str(value))

        return result

    def _mask_sensitive(self, field_name: str, value: str) -> str:
        """对敏感字段脱敏"""
        lower_name = field_name.lower()
        if any(s in lower_name for s in SENSITIVE_FIELDS):
            return "***"
        return f'"{value}"'

    def _mask_or_value(self, value: str) -> str:
        """对可能是敏感数据的值脱敏"""
        if not value:
            return ""
        lower_val = value.lower()
        if any(s in lower_val for s in SENSITIVE_FIELDS):
            return "***"
        # 检查是否像密码（短字符串，非 URL）
        if len(value) < 30 and not value.startswith(('http', '/', '.')):
            return f'"{value}"'
        return f'"{value}"'
