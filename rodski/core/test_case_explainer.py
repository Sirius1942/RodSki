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

from core.xml_schema_validator import RodskiXmlValidator


# 敏感字段名（自动脱敏）
SENSITIVE_FIELDS = {
    'password', 'pwd', 'passwd', 'secret', 'token', 'apikey',
    'api_key', 'auth', 'authorization', 'credential',
}


class TestCaseExplainer:
    """测试用例静态解释器

    将 XML 测试用例解析为人类可读的步骤说明。
    支持三阶段（pre_process / test_case / post_process）。
    """

    def __init__(self, model_parser=None, data_manager=None):
        """
        Args:
            model_parser: ModelParser 实例，用于解析模型定位器
            data_manager: DataTableParser 实例，用于解析数据表
        """
        self.model_parser = model_parser
        self.data_manager = data_manager

    # ── 公共 API ─────────────────────────────────────────────────

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

        # 获取结构化解释
        info = self._explain_keyword(action, model, data)

        lines = []
        # 步骤头：带类型标注（如 "type (批量输入)"）
        action_tag = info.get('action_tag', action)
        lines.append(f"  步骤 {index}/{total}: {action_tag}")

        # → 操作:
        op = info.get('操作', '')
        lines.append(f"    → 操作: {op}")

        # → 定位器: (click 等操作有)
        locator = info.get('定位器', '(无)')
        if locator != '(无)':
            lines.append(f"    → 定位器: {locator}")

        # → 预期: (verify 有)
        expected = info.get('预期', '')
        if expected:
            lines.append(f"    → 预期: {expected}")

        # → 模型:
        model_disp = info.get('模型', '')
        lines.append(f"    → 模型: {model_disp if model_disp else '(无)'}")

        # → 数据:
        data_disp = info.get('数据', '')
        lines.append(f"    → 数据: {data_disp if data_disp else '(无)'}")

        # → 字段解析: (type 批量有)
        fields = info.get('字段解析', [])
        if fields:
            lines.append("    → 字段解析:")
            for f in fields:
                lines.append(f"      - {f}")

        return "\n".join(lines)

    def _explain_keyword(
        self, action: str, model: str, data: str
    ) -> Dict[str, Any]:
        """根据关键字生成结构化解释

        Returns:
            Dict with keys:
              - action_tag: str, 步骤标签，如 "type (批量输入)" 或 "click"
              - 操作: str, 人类可读操作描述
              - 模型: str, 模型名称
              - 数据: str, 数据值或 DataID
              - 定位器: str, 定位器信息
              - 预期: str, verify 预期值
              - 字段解析: list[str], 字段级解析列表
        """
        action = action.lower()
        handler_map = {
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
            'close': self._explain_close,
            'set': self._explain_set,
            'verify_image': self._explain_verify_image,
            'if': self._explain_if,
            'loop': self._explain_loop,
        }

        handler = handler_map.get(action)
        if handler:
            return handler(model, data)

        # 通用兜底
        parts = []
        if model:
            parts.append(f"模型={model}")
        if data:
            parts.append(f"数据={data}")
        hint = ", ".join(parts) if parts else "(无参数)"
        return {
            'action_tag': action,
            '操作': hint,
            '模型': model,
            '数据': data,
            '定位器': '',
            '预期': '',
            '字段解析': [],
        }

    # ── 各关键字解释 ─────────────────────────────────────────────

    def _explain_navigate(self, model: str, data: str) -> Dict[str, Any]:
        url = data or "（URL 未指定）"
        return {
            'action_tag': 'navigate',
            '操作': f"导航到网址 {url}",
            '模型': '',
            '数据': data,
            '定位器': '',
            '预期': '',
            '字段解析': [],
        }

    def _explain_launch(self, model: str, data: str) -> Dict[str, Any]:
        if model and data:
            op = f"启动应用或打开页面（模型={model}, 数据={data}）"
        elif data:
            if data.startswith(('http://', 'https://')):
                op = f"打开网页: {data}"
            else:
                op = f"启动应用: {data}"
        else:
            op = "启动应用或打开页面（参数不完整）"
        return {
            'action_tag': 'launch',
            '操作': op,
            '模型': model,
            '数据': data,
            '定位器': '',
            '预期': '',
            '字段解析': [],
        }

    def _explain_type(self, model: str, data: str) -> Dict[str, Any]:
        """type 关键字解释，支持批量和单字段"""
        if model and data:
            return self._explain_type_batch(model, data)
        return self._explain_type_single(model, data)

    def _explain_type_batch(self, model_name: str, data_id: str) -> Dict[str, Any]:
        """批量输入解释"""
        resolved = self._resolve_fields(model_name, data_id)

        fields = []
        if resolved:
            for field_name, (locator, value) in resolved.items():
                display = self._mask_sensitive_display(field_name, value)
                is_masked = self._is_sensitive(field_name)
                suffix = " (已脱敏)" if is_masked else ""
                fields.append(f'{field_name}: {display} → 输入到 [{locator}]{suffix}')
        else:
            fields.append(f"  ⚠️  未找到模型 '{model_name}' 或数据 '{data_id}'")

        return {
            'action_tag': 'type (批量输入)',
            '操作': f"使用模型 {model_name} 从数据 {data_id} 批量输入",
            '模型': f"{model_name} (定位器列表)",
            '数据': f"DataID={data_id}",
            '定位器': '',
            '预期': '',
            '字段解析': fields,
        }

    def _explain_type_single(self, model: str, data: str) -> Dict[str, Any]:
        if model:
            op = f"向 {model} 输入 '{self._mask_or_value(data)}'"
        else:
            op = f"向定位器输入 '{self._mask_or_value(data)}'"
        return {
            'action_tag': 'type',
            '操作': op,
            '模型': model,
            '数据': data,
            '定位器': '',
            '预期': '',
            '字段解析': [],
        }

    def _explain_click(self, model: str, data: str) -> Dict[str, Any]:
        locator = model or data or "（定位器未指定）"
        op = f"点击元素"
        return {
            'action_tag': 'click',
            '操作': op,
            '模型': '',
            '数据': '',
            '定位器': locator,
            '预期': '',
            '字段解析': [],
        }

    def _explain_verify(self, model: str, data: str) -> Dict[str, Any]:
        if model and data:
            return self._explain_verify_batch(model, data)
        if data:
            return {
                'action_tag': 'verify',
                '操作': f"验证页面包含文本 '{self._mask_or_value(data)}'",
                '模型': '',
                '数据': '',
                '定位器': '',
                '预期': f'"{data}"',
                '字段解析': [],
            }
        return {
            'action_tag': 'verify',
            '操作': "验证页面内容（参数不完整）",
            '模型': '',
            '数据': '',
            '定位器': '',
            '预期': '',
            '字段解析': [],
        }

    def _explain_verify_batch(self, model_name: str, data_id: str) -> Dict[str, Any]:
        """批量验证解释"""
        verify_table = f"{model_name}_verify"
        fields = []

        if not self.data_manager:
            fields.append("  ⚠️  未提供 data_manager，跳过字段详情")
        else:
            data_row = self.data_manager.get_data(verify_table, data_id)
            if not data_row:
                fields.append(f"  ⚠️  未找到数据: 表={verify_table}, DataID={data_id}")
            else:
                model = self.model_parser.get_model(model_name) if self.model_parser else {}
                for field_name, expected in data_row.items():
                    loc = ""
                    if model and field_name in model:
                        elem = model[field_name]
                        loc = f"[{elem.get('type', '?')}={elem.get('value', '?')}]"
                    display = self._mask_sensitive_display(field_name, expected)
                    fields.append(f"    - {field_name} {loc}: 期望 {display}")

        return {
            'action_tag': 'verify (批量验证)',
            '操作': f"批量验证模型 {model_name}，期望数据={data_id}",
            '模型': model_name,
            '数据': f"DataID={data_id}",
            '定位器': '',
            '预期': '',
            '字段解析': fields,
        }

    def _explain_wait(self, model: str, data: str) -> Dict[str, Any]:
        secs = data or model or "?"
        return {
            'action_tag': 'wait',
            '操作': f"等待 {secs} 秒",
            '模型': '',
            '数据': data,
            '定位器': '',
            '预期': '',
            '字段解析': [],
        }

    def _explain_screenshot(self, model: str, data: str) -> Dict[str, Any]:
        path = data or "（未指定）"
        return {
            'action_tag': 'screenshot',
            '操作': f"截图保存为: {path}",
            '模型': '',
            '数据': data,
            '定位器': '',
            '预期': '',
            '字段解析': [],
        }

    def _explain_get_text(self, model: str, data: str) -> Dict[str, Any]:
        if data:
            op = f"获取 {data} 的文本内容"
        elif model:
            op = f"获取模型 {model} 的文本内容"
        else:
            op = "获取文本内容"
        return {
            'action_tag': 'get_text',
            '操作': op,
            '模型': model,
            '数据': data,
            '定位器': '',
            '预期': '',
            '字段解析': [],
        }

    def _explain_get(self, model: str, data: str) -> Dict[str, Any]:
        return self._explain_get_text(model, data)

    def _explain_clear(self, model: str, data: str) -> Dict[str, Any]:
        target = data or model or "（未指定）"
        return {
            'action_tag': 'clear',
            '操作': f"清空输入框: {target}",
            '模型': model,
            '数据': data,
            '定位器': '',
            '预期': '',
            '字段解析': [],
        }

    def _explain_upload_file(self, model: str, data: str) -> Dict[str, Any]:
        if data and model:
            op = f"上传文件: {data} → {model}"
        elif data:
            op = f"上传文件: {data}"
        else:
            op = "上传文件"
        return {
            'action_tag': 'upload_file',
            '操作': op,
            '模型': model,
            '数据': data,
            '定位器': '',
            '预期': '',
            '字段解析': [],
        }

    def _explain_assert(self, model: str, data: str) -> Dict[str, Any]:
        parts = []
        if model:
            parts.append(f"定位器={model}")
        if data:
            parts.append(f"预期内容='{self._mask_or_value(data)}'")
        hint = "断言: " + ", ".join(parts) if parts else "执行断言"
        return {
            'action_tag': 'assert',
            '操作': hint,
            '模型': model,
            '数据': data,
            '定位器': '',
            '预期': data,
            '字段解析': [],
        }

    def _explain_db(self, model: str, data: str) -> Dict[str, Any]:
        parts = []
        if model:
            parts.append(f"连接={model}")
        if data:
            parts.append(f"SQL={data}")
        hint = "数据库操作: " + ", ".join(parts) if parts else "执行数据库操作"
        return {
            'action_tag': 'db',
            '操作': hint,
            '模型': model,
            '数据': data,
            '定位器': '',
            '预期': '',
            '字段解析': [],
        }

    def _explain_run(self, model: str, data: str) -> Dict[str, Any]:
        if model and data:
            op = f"运行代码模块: 项目={model}, 脚本={data}"
        elif data:
            op = f"运行代码: {data}"
        else:
            op = "执行代码"
        return {
            'action_tag': 'run',
            '操作': op,
            '模型': model,
            '数据': data,
            '定位器': '',
            '预期': '',
            '字段解析': [],
        }

    def _explain_send(self, model: str, data: str) -> Dict[str, Any]:
        if model and data:
            op = f"发送 HTTP 请求: 模型={model}, DataID={data}"
        elif model:
            op = f"发送 HTTP 请求: 模型={model}"
        else:
            op = "发送 HTTP 请求"
        return {
            'action_tag': 'send',
            '操作': op,
            '模型': model,
            '数据': data,
            '定位器': '',
            '预期': '',
            '字段解析': [],
        }

    def _explain_close(self, model: str, data: str) -> Dict[str, Any]:
        return {
            'action_tag': 'close',
            '操作': "关闭当前浏览器窗口",
            '模型': '',
            '数据': '',
            '定位器': '',
            '预期': '',
            '字段解析': [],
        }

    def _explain_set(self, model: str, data: str) -> Dict[str, Any]:
        if model and data:
            op = f"设置变量: {model} = '{self._mask_or_value(data)}'"
        else:
            op = "设置变量"
        return {
            'action_tag': 'set',
            '操作': op,
            '模型': model,
            '数据': data,
            '定位器': '',
            '预期': '',
            '字段解析': [],
        }

    def _explain_verify_image(self, model: str, data: str) -> Dict[str, Any]:
        if data and model:
            op = f"AI 截图验证: 截图={data}, 预期描述={model}"
        elif data:
            op = f"AI 截图验证: 截图={data}"
        else:
            op = "AI 截图验证"
        return {
            'action_tag': 'verify_image',
            '操作': op,
            '模型': model,
            '数据': data,
            '定位器': '',
            '预期': '',
            '字段解析': [],
        }

    def _explain_if(self, model: str, data: str) -> Dict[str, Any]:
        if model and data:
            op = f"条件判断: {model} = {data}"
        elif model:
            op = f"条件判断: {model}"
        else:
            op = "条件判断"
        return {
            'action_tag': 'if',
            '操作': op,
            '模型': model,
            '数据': data,
            '定位器': '',
            '预期': '',
            '字段解析': [],
        }

    def _explain_loop(self, model: str, data: str) -> Dict[str, Any]:
        if model and data:
            op = f"循环执行 {data} 次，变量为 {model}"
        elif data:
            op = f"循环执行 {data} 次"
        else:
            op = "循环执行"
        return {
            'action_tag': 'loop',
            '操作': op,
            '模型': model,
            '数据': data,
            '定位器': '',
            '预期': '',
            '字段解析': [],
        }

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

    def _is_sensitive(self, field_name: str) -> bool:
        """判断字段名是否为敏感字段"""
        lower_name = field_name.lower()
        return any(s in lower_name for s in SENSITIVE_FIELDS)

    def _mask_sensitive_display(self, field_name: str, value: str) -> str:
        """对敏感字段脱敏并返回带引号的显示值"""
        if self._is_sensitive(field_name):
            return "***"
        return f'"{value}"'

    def _mask_or_value(self, value: str) -> str:
        """对可能是敏感数据的值脱敏"""
        if not value:
            return ""
        lower_val = value.lower()
        if any(s in lower_val for s in SENSITIVE_FIELDS):
            return "***"
        if len(value) < 30 and not value.startswith(('http', '/', '.')):
            return f'"{value}"'
        return f'"{value}"'

    # ── 格式化器 ─────────────────────────────────────────────────

    def explain_case(self, case_xml_path: str, format: str = "text") -> str:
        """对单个测试用例文件生成人类可读说明

        Args:
            case_xml_path: case XML 文件路径
            format: 输出格式 (text/markdown/html)

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

        structured_cases = self._parse_cases_structured(path)
        if not structured_cases:
            return f"警告: 未找到任何启用的用例 → {case_xml_path}"

        formatter_map = {
            "text": TextFormatter(self),
            "markdown": MarkdownFormatter(self),
            "html": HtmlFormatter(self),
        }
        formatter = formatter_map.get(format, formatter_map["text"])

        outputs = []
        for case in structured_cases:
            outputs.append(formatter.format_case(case))

        return "\n".join(outputs).rstrip()

    # ── 解析为结构化数据 ──────────────────────────────────────────

    def _parse_cases_structured(self, xml_path: Path) -> List[Dict[str, Any]]:
        """解析用例文件，返回结构化数据列表"""
        try:
            tree = ET.parse(xml_path)
        except ET.ParseError:
            return []
        root = tree.getroot()
        cases = []
        for case_node in root.findall('case'):
            execute = case_node.get('execute', '否').strip()
            if execute != '是':
                continue

            case_id = case_node.get('id', '')
            title = case_node.get('title', '')
            description = case_node.get('description', '')
            priority = case_node.get('priority', '')
            component_type = case_node.get('component_type', '')

            # 解析 metadata 中的标签
            tags = []
            metadata_node = case_node.find('metadata')
            if metadata_node is not None:
                for tag_node in metadata_node.findall('tag'):
                    tag_text = (tag_node.text or '').strip()
                    if tag_text:
                        tags.append(tag_text)

            # 解析所有步骤（带时长推断）
            all_steps = []
            for phase_key in ('pre_process', 'test_case', 'post_process'):
                phase_steps = self._parse_steps_structured(case_node.find(phase_key))
                for step in phase_steps:
                    step['_phase'] = phase_key
                all_steps.extend(phase_steps)

            # 从 verify 步骤推断预期结果
            expected_results = []
            for step in all_steps:
                if step['action'] == 'verify' and step.get('data'):
                    expected_results.append(step['data'])
                elif step['action'] == 'verify' and step.get('model'):
                    # 批量验证
                    expected_results.append(f"验证 {step['model']}/{step['data']}")

            cases.append({
                'case_id': case_id,
                'title': title,
                'purpose': description,
                'priority': priority,
                'tags': tags,
                'component_type': component_type,
                'steps': all_steps,
                'expected_results': expected_results,
            })
        return cases

    def _parse_steps_structured(self, phase_node) -> List[Dict[str, Any]]:
        """解析阶段节点下的步骤，返回结构化步骤列表"""
        if phase_node is None:
            return []
        raw_steps = []
        for el in phase_node.findall('test_step'):
            action = str(el.get('action', '') or '').strip()
            if not action:
                continue
            raw_steps.append({
                'action': action,
                'model': str(el.get('model', '') or '').strip(),
                'data': str(el.get('data', '') or '').strip(),
            })

        # 推断每步时长（wait 紧跟的步骤吸收其时长，但 wait 步骤保留自身显示）
        steps = []
        i = 0
        while i < len(raw_steps):
            step = raw_steps[i]
            duration = None
            # 如果下一步是 wait，吸收其时长
            if i + 1 < len(raw_steps) and raw_steps[i + 1]['action'] == 'wait':
                duration = raw_steps[i + 1].get('data', '')
                i += 2  # 跳过 wait（wait 步骤会被单独处理）
            elif step['action'] == 'wait':
                # 独立的 wait 步骤，保留
                steps.append({
                    'action': 'wait',
                    'model': '',
                    'data': step.get('data', ''),
                    'duration': step.get('data', ''),
                })
                i += 1
                continue
            else:
                i += 1

            steps.append({
                'action': step['action'],
                'model': step.get('model', ''),
                'data': step.get('data', ''),
                'duration': duration,
            })
        return steps

    # URL → 描述映射（部分匹配）
    _URL_HINTS = {
        'passport/login': '登录页面',
        'login': '登录页面',
        'market/portal': '市场门户页',
        'market/inquirys': '询价列表页',
        'inquirys': '询价列表页',
        'agentbuy': '采购页面',
        'agentbuy/': '采购页面',
        'inquiry': '询价页面',
        '/inquiry': '询价页面',
    }

    def _url_to_desc(self, url: str) -> str:
        """从 URL 推断页面描述"""
        if not url:
            return '指定页面'
        url_lower = url.lower()
        for hint, desc in self._URL_HINTS.items():
            if hint in url_lower:
                return desc
        # 去掉 https:// 和路径，清理末尾斜杠
        path = url_lower.split('://')[-1].rstrip('/')
        # 取最后一段路径
        segments = path.split('/')
        last = segments[-1] if segments else path
        if last and last not in ('http', 'https'):
            return last
        return path

    def _step_description(self, step: Dict[str, Any]) -> str:
        """生成单步的人类可读描述"""
        action = step['action']
        model = step.get('model', '')
        data = step.get('data', '')

        if action == 'navigate':
            return f"打开{self._url_to_desc(data)}"
        elif action == 'wait':
            return f"等待 {data}s"
        elif action == 'type' and model and data:
            return f"输入内容"
        elif action == 'type' and model:
            return f"输入内容到 {model}"
        elif action == 'type':
            return f"输入内容"
        elif action == 'click' and model:
            return f"点击 {model}"
        elif action == 'click':
            return f"点击"
        elif action == 'verify' and model and data:
            return f"验证 {model}/{data}"
        elif action == 'verify' and data:
            return f"验证包含 '{data}'"
        elif action == 'verify':
            return f"验证"
        elif action == 'screenshot':
            return f"截图记录"
        elif action == 'close':
            return f"关闭页面"
        elif action == 'clear':
            return f"清空 {model or data}"
        elif action == 'launch':
            return f"启动应用"
        elif action == 'get_text':
            return f"获取文本 {model or data}"
        elif action == 'upload_file':
            return f"上传文件"
        elif action == 'assert':
            return f"断言 {data}"
        elif action == 'db':
            return f"数据库操作"
        elif action == 'run':
            return f"运行脚本"
        elif action == 'send':
            return f"发送请求"
        elif action == 'set':
            return f"设置变量"
        elif action == 'verify_image':
            return f"AI 截图验证"
        elif action == 'if':
            return f"条件判断"
        elif action == 'loop':
            return f"循环 {data}次"
        else:
            parts = []
            if model:
                parts.append(model)
            if data:
                parts.append(data)
            hint = " ".join(parts) if parts else action
            return hint


# ══════════════════════════════════════════════════════════════════
#  格式化器
# ══════════════════════════════════════════════════════════════════


class TextFormatter:
    """纯文本格式化器"""

    def __init__(self, explainer: TestCaseExplainer):
        self.explainer = explainer

    def format_case(self, case: Dict[str, Any]) -> str:
        lines = []
        # 用例头
        lines.append(f"用例：{case['title']}")
        lines.append(f"ID：{case['case_id']}")
        if case.get('priority'):
            lines.append(f"优先级：{case['priority']}")
        if case.get('tags'):
            lines.append(f"标签：{', '.join(case['tags'])}")

        # 显示全部步骤（pre_process + test_case + post_process 合并）
        all_steps = case['steps']

        if all_steps:
            lines.append("")
            lines.append("测试步骤：")
            for i, step in enumerate(all_steps, 1):
                desc = self.explainer._step_description(step)
                duration = step.get('duration', '')
                suffix = f" ({duration}s)" if duration else ""
                model = step.get('model', '')
                data = step.get('data', '')
                # 带模型/数据信息的简明格式: - ModelName/DataID
                if model and data:
                    extra = f" - {model}/{data}"
                elif model:
                    extra = f" - {model}"
                else:
                    extra = ""
                lines.append(f"  步骤 {i}: {desc}{extra}{suffix}")

        # 预期结果
        if case.get('expected_results'):
            lines.append("")
            lines.append("预期结果：")
            for result in case['expected_results']:
                lines.append(f"  ✓ {result}")

        return "\n".join(lines)


class MarkdownFormatter:
    """Markdown 格式化器"""

    def __init__(self, explainer: TestCaseExplainer):
        self.explainer = explainer

    def format_case(self, case: Dict[str, Any]) -> str:
        lines = []
        lines.append(f"# {case['title']}")
        lines.append("")
        lines.append(f"**用例 ID**: `{case['case_id']}`")
        if case.get('purpose'):
            lines.append(f"**目的**: {case['purpose']}")
        if case.get('priority'):
            lines.append(f"**优先级**: {case['priority']}")
        if case.get('tags'):
            lines.append(f"**标签**: {' | '.join(case['tags'])}")

        # 显示全部步骤
        all_steps = case['steps']

        if all_steps:
            lines.append("")
            lines.append("## 测试步骤")
            lines.append("")
            lines.append("| 步骤 | 操作 | 模型 | 数据 | 耗时 |")
            lines.append("|------|------|------|------|------|")
            for i, step in enumerate(all_steps, 1):
                action = step['action']
                model = step.get('model', '—')
                data = step.get('data', '—')
                duration = step.get('duration') or '—'
                if duration not in ('—', 'None', ''):
                    duration = f"{duration}s"
                desc = self.explainer._step_description(step)
                lines.append(f"| {i} | {desc} | {model} | {data} | {duration} |")

        if case.get('expected_results'):
            lines.append("")
            lines.append("## 预期结果")
            for result in case['expected_results']:
                lines.append(f"- [x] {result}")

        return "\n".join(lines)


class HtmlFormatter:
    """HTML 格式化器"""

    def __init__(self, explainer: TestCaseExplainer):
        self.explainer = explainer

    def format_case(self, case: Dict[str, Any]) -> str:
        lines = []
        lines.append('<div class="test-case">')
        lines.append('  <div class="case-header">')
        lines.append(f'    <h2>{self._escape_html(case["title"])}</h2>')
        lines.append(f'    <span class="case-id">{self._escape_html(case["case_id"])}</span>')
        if case.get('priority'):
            lines.append(f'    <span class="priority priority-{case["priority"].lower()}">{case["priority"]}</span>')
        lines.append('  </div>')

        if case.get('tags'):
            lines.append('  <div class="tags">')
            for tag in case['tags']:
                lines.append(f'    <span class="tag">{self._escape_html(tag)}</span>')
            lines.append('  </div>')

        # 显示全部步骤
        all_steps = case['steps']

        if all_steps:
            lines.append('  <div class="steps">')
            lines.append('    <h3>测试步骤</h3>')
            lines.append('    <ol>')
            for i, step in enumerate(all_steps, 1):
                desc = self.explainer._step_description(step)
                duration = step.get('duration', '')
                suffix = f' <span class="duration">({duration}s)</span>' if duration else ''
                model = step.get('model', '')
                data = step.get('data', '')
                extra = ''
                if model and data:
                    extra = f' <span class="model-data">{model}/{data}</span>'
                elif model:
                    extra = f' <span class="model-data">{model}</span>'
                lines.append(f'      <li>{self._escape_html(desc)}{extra}{suffix}</li>')
            lines.append('    </ol>')
            lines.append('  </div>')

        if case.get('expected_results'):
            lines.append('  <div class="expected-results">')
            lines.append('    <h3>预期结果</h3>')
            lines.append('    <ul>')
            for result in case['expected_results']:
                lines.append(f'      <li class="pass">✓ {self._escape_html(result)}</li>')
            lines.append('    </ul>')
            lines.append('  </div>')

        lines.append('</div>')
        return "\n".join(lines)

    def _escape_html(self, text: str) -> str:
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;'))
