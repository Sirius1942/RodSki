"""TestCaseExplainer 单元测试

测试 core/test_case_explainer.py 中的测试用例静态解释器。
覆盖：初始化、explain_steps（空/非空）、_explain_keyword（全部关键字类型）、
      _is_sensitive / _mask_sensitive_display（敏感字段脱敏）、
      _parse_phase_steps / _parse_cases（XML 解析）、
      explain_case（text/markdown/html 三种格式输出）、
      _url_to_desc / _step_description（辅助描述方法）。
所有外部解析器均通过 mock 隔离。
"""
import xml.etree.ElementTree as ET
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from core.test_case_explainer import (
    TestCaseExplainer,
    TextFormatter,
    MarkdownFormatter,
    HtmlFormatter,
    SENSITIVE_FIELDS,
)


# =====================================================================
# 初始化
# =====================================================================
class TestExplainerInit:
    """TestCaseExplainer 初始化"""

    def test_default_init(self):
        """无参数初始化：model_parser/data_manager 均为 None"""
        e = TestCaseExplainer()
        assert e.model_parser is None
        assert e.data_manager is None

    def test_custom_init(self):
        """自定义初始化"""
        mp = MagicMock()
        dm = MagicMock()
        e = TestCaseExplainer(model_parser=mp, data_manager=dm)
        assert e.model_parser is mp
        assert e.data_manager is dm


# =====================================================================
# explain_steps
# =====================================================================
class TestExplainSteps:
    """explain_steps —— 步骤列表生成说明"""

    def test_empty_steps(self):
        """空步骤列表应返回提示信息"""
        e = TestCaseExplainer()
        result = e.explain_steps([], phase="test_case")
        assert "无步骤" in result

    def test_single_step(self):
        """单个步骤应包含步骤编号和操作描述"""
        e = TestCaseExplainer()
        steps = [{"action": "navigate", "model": "", "data": "https://example.com"}]
        result = e.explain_steps(steps)
        assert "1/1" in result  # 步骤编号
        assert "navigate" in result

    def test_multiple_steps(self):
        """多个步骤应按顺序输出"""
        e = TestCaseExplainer()
        steps = [
            {"action": "navigate", "model": "", "data": "https://test.com"},
            {"action": "type", "model": "Login", "data": "D001"},
            {"action": "verify", "model": "", "data": "成功"},
        ]
        result = e.explain_steps(steps)
        assert "1/3" in result
        assert "2/3" in result
        assert "3/3" in result


# =====================================================================
# _explain_keyword —— 各关键字解释
# =====================================================================
class TestExplainKeyword:
    """_explain_keyword —— 不同关键字类型的结构化解释"""

    @pytest.fixture
    def explainer(self):
        return TestCaseExplainer()

    def test_navigate(self, explainer):
        """navigate 关键字：应包含 URL"""
        info = explainer._explain_keyword("navigate", "", "https://test.com")
        assert info["action_tag"] == "navigate"
        assert "https://test.com" in info["操作"]

    def test_launch_url(self, explainer):
        """launch 关键字（URL 模式）：打开网页"""
        info = explainer._explain_keyword("launch", "", "https://app.example.com")
        assert "打开网页" in info["操作"]

    def test_launch_app(self, explainer):
        """launch 关键字（应用模式）：启动应用"""
        info = explainer._explain_keyword("launch", "", "MyApp.exe")
        assert "启动应用" in info["操作"]

    def test_type_single(self, explainer):
        """type 关键字（单字段模式）"""
        info = explainer._explain_keyword("type", "username", "")
        assert info["action_tag"] == "type"

    def test_type_batch(self, explainer):
        """type 关键字（批量模式）：有 model 和 data"""
        info = explainer._explain_keyword("type", "Login", "D001")
        assert "批量" in info["action_tag"]
        assert "Login" in info["操作"]

    def test_click(self, explainer):
        """click 关键字：应包含定位器"""
        info = explainer._explain_keyword("click", "#submit-btn", "")
        assert info["action_tag"] == "click"
        assert info["定位器"] == "#submit-btn"

    def test_verify_with_data(self, explainer):
        """verify 关键字（简单模式）：验证页面包含文本"""
        info = explainer._explain_keyword("verify", "", "登录成功")
        assert "验证" in info["操作"]
        assert info["预期"] == '"登录成功"'

    def test_verify_batch(self, explainer):
        """verify 关键字（批量模式）：有 model 和 data"""
        info = explainer._explain_keyword("verify", "Login", "D001")
        assert "批量验证" in info["action_tag"]

    def test_wait(self, explainer):
        """wait 关键字：等待指定秒数"""
        info = explainer._explain_keyword("wait", "", "5")
        assert "5" in info["操作"]
        assert "等待" in info["操作"]

    def test_screenshot(self, explainer):
        """screenshot 关键字：截图保存"""
        info = explainer._explain_keyword("screenshot", "", "login_page.png")
        assert "截图" in info["操作"]
        assert "login_page.png" in info["操作"]

    def test_get_text(self, explainer):
        """get_text 关键字：获取文本"""
        info = explainer._explain_keyword("get_text", "", "#result")
        assert "获取" in info["操作"]
        assert "文本" in info["操作"]

    def test_clear(self, explainer):
        """clear 关键字：清空输入框"""
        info = explainer._explain_keyword("clear", "", "#username")
        assert "清空" in info["操作"]

    def test_upload_file(self, explainer):
        """upload_file 关键字"""
        info = explainer._explain_keyword("upload_file", "#file-input", "test.pdf")
        assert "上传" in info["操作"]

    def test_assert_keyword(self, explainer):
        """assert 关键字"""
        info = explainer._explain_keyword("assert", "#msg", "成功")
        assert "断言" in info["操作"]
        assert info["预期"] == "成功"

    def test_db(self, explainer):
        """db 关键字：数据库操作"""
        info = explainer._explain_keyword("db", "mysql_conn", "SELECT 1")
        assert "数据库" in info["操作"]
        assert "mysql_conn" in info["操作"]

    def test_run(self, explainer):
        """run 关键字：运行代码"""
        info = explainer._explain_keyword("run", "MyProject", "test_script.py")
        assert "运行" in info["操作"]

    def test_send(self, explainer):
        """send 关键字：发送 HTTP 请求"""
        info = explainer._explain_keyword("send", "API_Login", "D001")
        assert "HTTP" in info["操作"] or "请求" in info["操作"]

    def test_close(self, explainer):
        """close 关键字：关闭窗口"""
        info = explainer._explain_keyword("close", "", "")
        assert "关闭" in info["操作"]

    def test_set(self, explainer):
        """set 关键字：设置变量"""
        info = explainer._explain_keyword("set", "token", "abc123")
        assert "设置" in info["操作"]
        assert "token" in info["操作"]

    def test_verify_image(self, explainer):
        """verify_image 关键字：AI 截图验证"""
        info = explainer._explain_keyword("verify_image", "预期描述", "screenshot.png")
        assert "AI" in info["操作"] or "截图" in info["操作"]

    def test_if_keyword(self, explainer):
        """if 关键字：条件判断"""
        info = explainer._explain_keyword("if", "verify_fail", "")
        assert "条件" in info["操作"]

    def test_loop_keyword(self, explainer):
        """loop 关键字：循环执行"""
        info = explainer._explain_keyword("loop", "i", "5")
        assert "循环" in info["操作"]

    def test_unknown_keyword(self, explainer):
        """未知关键字应使用通用兜底格式"""
        info = explainer._explain_keyword("custom_action", "model1", "data1")
        assert info["action_tag"] == "custom_action"
        assert "model1" in info["操作"]


# =====================================================================
# 敏感字段检测与脱敏
# =====================================================================
class TestSensitiveFields:
    """_is_sensitive / _mask_sensitive_display —— 敏感字段脱敏"""

    @pytest.fixture
    def explainer(self):
        return TestCaseExplainer()

    def test_password_is_sensitive(self, explainer):
        """password 字段应被识别为敏感"""
        assert explainer._is_sensitive("password") is True
        assert explainer._is_sensitive("user_password") is True

    def test_token_is_sensitive(self, explainer):
        """token 字段应被识别为敏感"""
        assert explainer._is_sensitive("api_token") is True

    def test_normal_field_not_sensitive(self, explainer):
        """普通字段不应被识别为敏感"""
        assert explainer._is_sensitive("username") is False
        assert explainer._is_sensitive("email") is False

    def test_mask_sensitive_display(self, explainer):
        """敏感字段值应被替换为 ***"""
        assert explainer._mask_sensitive_display("password", "secret123") == "***"

    def test_mask_normal_display(self, explainer):
        """普通字段值应原样展示（带引号）"""
        result = explainer._mask_sensitive_display("username", "admin")
        assert result == '"admin"'


# =====================================================================
# _parse_phase_steps —— XML 阶段步骤解析
# =====================================================================
class TestParsePhaseSteps:
    """_parse_phase_steps —— 从 XML 节点提取步骤"""

    @pytest.fixture
    def explainer(self):
        return TestCaseExplainer()

    def test_none_node(self, explainer):
        """None 节点应返回空列表"""
        assert explainer._parse_phase_steps(None) == []

    def test_valid_steps(self, explainer):
        """有效步骤应被正确提取"""
        xml_str = """
        <test_case>
          <test_step action="type" model="Login" data="D001"/>
          <test_step action="click" model="#submit" data=""/>
          <test_step action="verify" model="" data="成功"/>
        </test_case>
        """
        node = ET.fromstring(xml_str)
        steps = explainer._parse_phase_steps(node)
        assert len(steps) == 3
        assert steps[0]["action"] == "type"
        assert steps[1]["action"] == "click"
        assert steps[2]["data"] == "成功"

    def test_empty_action_filtered(self, explainer):
        """空 action 的步骤应被过滤"""
        xml_str = """
        <test_case>
          <test_step action="" model="" data=""/>
          <test_step action="type" model="" data="test"/>
        </test_case>
        """
        node = ET.fromstring(xml_str)
        steps = explainer._parse_phase_steps(node)
        assert len(steps) == 1


# =====================================================================
# _parse_cases —— 完整用例解析
# =====================================================================
class TestParseCases:
    """_parse_cases —— 从 XML 文件提取启用的用例"""

    @pytest.fixture
    def explainer(self):
        return TestCaseExplainer()

    def test_parse_enabled_case(self, explainer, tmp_path):
        """execute='是' 的用例应被提取"""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case id="c001" title="登录测试" execute="是">
    <test_case>
      <test_step action="navigate" model="" data="https://test.com"/>
    </test_case>
  </case>
</cases>"""
        f = tmp_path / "test.xml"
        f.write_text(xml_content, encoding="utf-8")
        cases = explainer._parse_cases(f)
        assert len(cases) == 1
        assert cases[0]["case_id"] == "c001"

    def test_skip_disabled_case(self, explainer, tmp_path):
        """execute='否' 的用例应被跳过"""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case id="c001" title="禁用用例" execute="否">
    <test_case><test_step action="wait" data="1"/></test_case>
  </case>
</cases>"""
        f = tmp_path / "test.xml"
        f.write_text(xml_content, encoding="utf-8")
        cases = explainer._parse_cases(f)
        assert len(cases) == 0

    def test_invalid_xml(self, explainer, tmp_path):
        """无效 XML 应返回空列表"""
        f = tmp_path / "bad.xml"
        f.write_text("not xml at all", encoding="utf-8")
        cases = explainer._parse_cases(f)
        assert cases == []

    def test_three_phases(self, explainer, tmp_path):
        """三阶段（pre_process / test_case / post_process）均应解析"""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case id="c001" title="三阶段" execute="是">
    <pre_process><test_step action="navigate" model="" data="https://test.com"/></pre_process>
    <test_case><test_step action="type" model="Login" data="D001"/></test_case>
    <post_process><test_step action="close" model="" data=""/></post_process>
  </case>
</cases>"""
        f = tmp_path / "test.xml"
        f.write_text(xml_content, encoding="utf-8")
        cases = explainer._parse_cases(f)
        assert len(cases[0]["pre_process"]) == 1
        assert len(cases[0]["test_case"]) == 1
        assert len(cases[0]["post_process"]) == 1


# =====================================================================
# _url_to_desc —— URL 到描述的映射
# =====================================================================
class TestUrlToDesc:
    """_url_to_desc —— 从 URL 推断页面描述"""

    @pytest.fixture
    def explainer(self):
        return TestCaseExplainer()

    def test_login_url(self, explainer):
        """包含 login 的 URL 应返回 '登录页面'"""
        desc = explainer._url_to_desc("https://example.com/passport/login")
        assert "登录" in desc

    def test_empty_url(self, explainer):
        """空 URL 应返回默认描述"""
        desc = explainer._url_to_desc("")
        assert desc == "指定页面"

    def test_unknown_url(self, explainer):
        """未匹配的 URL 应返回最后一段路径"""
        desc = explainer._url_to_desc("https://example.com/dashboard")
        assert "dashboard" in desc


# =====================================================================
# _step_description —— 步骤描述生成
# =====================================================================
class TestStepDescription:
    """_step_description —— 各关键字的简短描述"""

    @pytest.fixture
    def explainer(self):
        return TestCaseExplainer()

    def test_navigate_description(self, explainer):
        """navigate 描述应包含 '打开'"""
        desc = explainer._step_description({"action": "navigate", "data": "https://test.com"})
        assert "打开" in desc

    def test_wait_description(self, explainer):
        """wait 描述应包含秒数"""
        desc = explainer._step_description({"action": "wait", "data": "3"})
        assert "等待" in desc
        assert "3" in desc

    def test_click_description(self, explainer):
        """click 描述"""
        desc = explainer._step_description({"action": "click", "model": "#btn"})
        assert "点击" in desc

    def test_verify_description(self, explainer):
        """verify 描述"""
        desc = explainer._step_description({"action": "verify", "data": "成功", "model": ""})
        assert "验证" in desc

    def test_unknown_action_description(self, explainer):
        """未知 action 应返回参数信息"""
        desc = explainer._step_description({"action": "custom", "model": "mod1", "data": "dat1"})
        assert "mod1" in desc or "dat1" in desc


# =====================================================================
# explain_case —— 完整用例解释（三种格式）
# =====================================================================
class TestExplainCase:
    """explain_case —— 从 XML 文件生成人类可读说明"""

    @pytest.fixture
    def case_xml(self, tmp_path):
        """创建完整的测试用例 XML"""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case id="c001" title="登录测试" description="验证登录功能" priority="P1" execute="是">
    <metadata>
      <tag>smoke</tag>
      <tag>login</tag>
    </metadata>
    <test_case>
      <test_step action="navigate" model="" data="https://test.com/login"/>
      <test_step action="type" model="" data="admin"/>
      <test_step action="click" model="#submit" data=""/>
      <test_step action="verify" model="" data="登录成功"/>
    </test_case>
  </case>
</cases>"""
        f = tmp_path / "test_case.xml"
        f.write_text(xml_content, encoding="utf-8")
        return str(f)

    def test_text_format(self, case_xml):
        """text 格式输出应包含用例标题和步骤"""
        e = TestCaseExplainer()
        result = e.explain_case(case_xml, format="text")
        assert "登录测试" in result
        assert "c001" in result

    def test_markdown_format(self, case_xml):
        """markdown 格式输出应包含标题标记"""
        e = TestCaseExplainer()
        result = e.explain_case(case_xml, format="markdown")
        assert "# " in result  # markdown 标题
        assert "登录测试" in result

    def test_html_format(self, case_xml):
        """html 格式输出应包含 HTML 标签"""
        e = TestCaseExplainer()
        result = e.explain_case(case_xml, format="html")
        assert "<div" in result
        assert "<h2>" in result
        assert "登录测试" in result

    def test_file_not_found(self):
        """文件不存在应返回错误信息"""
        e = TestCaseExplainer()
        result = e.explain_case("/nonexistent/case.xml")
        assert "错误" in result or "不存在" in result

    def test_no_enabled_cases(self, tmp_path):
        """所有用例都禁用时应返回警告"""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case id="c001" title="禁用" execute="否">
    <test_case><test_step action="wait" data="1"/></test_case>
  </case>
</cases>"""
        f = tmp_path / "disabled.xml"
        f.write_text(xml_content, encoding="utf-8")
        e = TestCaseExplainer()
        result = e.explain_case(str(f))
        assert "未找到" in result or "警告" in result


# =====================================================================
# 格式化器单元测试
# =====================================================================
class TestFormatters:
    """TextFormatter / MarkdownFormatter / HtmlFormatter"""

    @pytest.fixture
    def case_data(self):
        """结构化用例数据"""
        return {
            "case_id": "c001",
            "title": "测试用例",
            "purpose": "验证功能",
            "priority": "P1",
            "tags": ["smoke", "login"],
            "component_type": "界面",
            "steps": [
                {"action": "navigate", "data": "https://test.com", "model": "", "duration": None, "_phase": "test_case"},
                {"action": "click", "data": "", "model": "#btn", "duration": "2", "_phase": "test_case"},
            ],
            "expected_results": ["登录成功"],
        }

    def test_text_formatter(self, case_data):
        """TextFormatter 应生成纯文本"""
        e = TestCaseExplainer()
        fmt = TextFormatter(e)
        result = fmt.format_case(case_data)
        assert "测试用例" in result
        assert "P1" in result
        assert "步骤 1" in result

    def test_markdown_formatter(self, case_data):
        """MarkdownFormatter 应生成 markdown 表格"""
        e = TestCaseExplainer()
        fmt = MarkdownFormatter(e)
        result = fmt.format_case(case_data)
        assert "|" in result  # 表格分隔符
        assert "# 测试用例" in result

    def test_html_formatter(self, case_data):
        """HtmlFormatter 应生成有效 HTML"""
        e = TestCaseExplainer()
        fmt = HtmlFormatter(e)
        result = fmt.format_case(case_data)
        assert '<div class="test-case">' in result
        assert "</div>" in result

    def test_html_escaping(self):
        """HtmlFormatter 应转义 HTML 特殊字符"""
        e = TestCaseExplainer()
        fmt = HtmlFormatter(e)
        escaped = fmt._escape_html('<script>alert("xss")</script>')
        assert "<" not in escaped
        assert "&lt;" in escaped
        assert "&quot;" in escaped
