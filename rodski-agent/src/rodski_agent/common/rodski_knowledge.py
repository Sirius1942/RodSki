"""RodSki 框架约束知识库。

将 rodski 的硬性约束编码为 Python 常量和校验函数，
供 Design Agent / Execution Agent / xml_builder / prompts / fixer 等模块共用。

数据来源：
  - rodski/docs/CORE_DESIGN_CONSTRAINTS.md (v4.0)
  - rodski/docs/TEST_CASE_WRITING_GUIDE.md (v3.3)
"""

from __future__ import annotations

import os
import re
from typing import Optional

# ============================================================
# 1. 关键字约束  (CORE_DESIGN_CONSTRAINTS §5, §1.2)
# ============================================================

SUPPORTED_KEYWORDS: list[str] = [
    "close",
    "type",
    "verify",
    "wait",
    "navigate",
    "launch",
    "assert",
    "upload_file",
    "clear",
    "get_text",
    "get",
    "send",
    "set",
    "DB",
    "run",
]
"""15 个受支持的关键字（case.xsd ActionType 枚举值）。"""

COMPAT_KEYWORDS: list[str] = ["check"]
"""兼容关键字。check 等价于 verify。"""

# screenshot 出现在 case.xsd 枚举中，但不在 SUPPORTED 15 个列表里，
# 以及 evaluate 也出现在 xsd 枚举中。这里额外记录用于校验补充。
ADDITIONAL_ACTION_TYPES: list[str] = ["screenshot", "evaluate"]
"""case.xsd 中存在但不计入「15 个关键字」的额外 action 值。"""

ALL_VALID_ACTIONS: list[str] = (
    SUPPORTED_KEYWORDS + COMPAT_KEYWORDS + ADDITIONAL_ACTION_TYPES
)
"""所有合法的 action 值（含兼容与补充）。"""

UI_ATOMIC_ACTIONS: list[str] = [
    "click",
    "double_click",
    "right_click",
    "hover",
    "select",
    "key_press",
    "drag",
    "scroll",
]
"""UI 原子动作 —— 只能作为数据表 field 值，不可出现在 Case XML action 属性中。"""

# ============================================================
# 2. 定位器约束  (CORE_DESIGN_CONSTRAINTS §2.5)
# ============================================================

TRADITIONAL_LOCATORS: list[str] = [
    "id",
    "class",
    "css",
    "xpath",
    "text",
    "tag",
    "name",
    "static",
    "field",
]
"""9 种传统定位器类型。"""

VISION_LOCATORS: list[str] = [
    "vision",
    "ocr",
    "vision_bbox",
]
"""3 种视觉定位器类型。"""

LOCATOR_TYPES: list[str] = TRADITIONAL_LOCATORS + VISION_LOCATORS
"""全部 12 种定位器类型。"""

DRIVER_TYPES: list[str] = [
    "web",
    "interface",
    "other",
    "windows",
    "macos",
]
"""驱动类型（element type 属性合法值）。"""

# ============================================================
# 3. 目录结构约束  (CORE_DESIGN_CONSTRAINTS §6)
# ============================================================

REQUIRED_DIRS: list[str] = ["case", "model", "data"]
"""测试模块下必须存在的子目录。"""

OPTIONAL_DIRS: list[str] = ["fun", "result"]
"""测试模块下可选的子目录。"""

ALL_MODULE_DIRS: list[str] = REQUIRED_DIRS + OPTIONAL_DIRS
"""测试模块下的全部 5 个固定文件夹。"""

FIXED_FILES: dict[str, str] = {
    "model": "model.xml",
    "data": "data.xml",
    "data_verify": "data_verify.xml",
    "globalvalue": "globalvalue.xml",
}
"""固定文件名映射。model.xml 是唯一的模型文件名；data.xml / data_verify.xml / globalvalue.xml 固定。"""

# ============================================================
# 4. Case XML 约束  (CORE_DESIGN_CONSTRAINTS §7.2)
# ============================================================

CASE_PHASES: list[str] = ["pre_process", "test_case", "post_process"]
"""Case XML 的三个阶段容器，XSD 顺序固定。test_case 必选，其余可选。"""

COMPONENT_TYPES: list[str] = ["界面", "接口", "数据库"]
"""case.component_type 的合法取值。"""

EXECUTE_VALUES: list[str] = ["是", "否"]
"""case.execute 的合法取值。只有「是」才会执行。"""

# ============================================================
# 5. 数据表约束  (CORE_DESIGN_CONSTRAINTS §4, §2)
# ============================================================

SPECIAL_VALUES: list[str] = ["BLANK", "NULL", "NONE"]
"""数据表中的控制值。BLANK=空字符串, NULL=null, NONE=不发送该字段。"""

VERIFY_TABLE_SUFFIX: str = "_verify"
"""验证数据表名后缀。verify 关键字自动在模型名后追加此后缀查找数据表。"""

INTERFACE_RESERVED_ELEMENTS: list[str] = ["_method", "_url"]
"""接口模型的保留元素名（固定名称）。另有 _header_* 前缀模式。"""

INTERFACE_HEADER_PREFIX: str = "_header_"
"""接口模型中请求头元素的命名前缀（如 _header_Authorization）。"""

# ============================================================
# 6. 校验函数
# ============================================================


def validate_action(action: str) -> bool:
    """检查 action 是否在 SUPPORTED_KEYWORDS、COMPAT_KEYWORDS 或 ADDITIONAL_ACTION_TYPES 中。

    Args:
        action: Case XML test_step 的 action 属性值。

    Returns:
        True 表示合法，False 表示非法。
    """
    return action in ALL_VALID_ACTIONS


def validate_locator_type(loc_type: str) -> bool:
    """检查定位器类型是否在 LOCATOR_TYPES 中。

    Args:
        loc_type: location 节点的 type 属性值。

    Returns:
        True 表示合法。
    """
    return loc_type in LOCATOR_TYPES


def validate_directory_structure(path: str) -> list[str]:
    """检查目录下是否有 case / model / data 三个必须子目录。

    Args:
        path: 测试模块目录路径。

    Returns:
        缺失的目录名列表。空列表表示结构完整。
    """
    missing: list[str] = []
    for d in REQUIRED_DIRS:
        if not os.path.isdir(os.path.join(path, d)):
            missing.append(d)
    return missing


def validate_element_data_consistency(
    model_elements: list[str],
    data_fields: list[str],
) -> list[str]:
    """检查模型元素名与数据表字段名一致性。

    逻辑：数据表中出现但模型中不存在的字段名视为不一致
    （模型中多出的元素可能由框架跳过，不算错误）。

    接口保留元素（_method / _url / _header_*）自动排除比较。

    Args:
        model_elements: 模型中所有 element.name 列表。
        data_fields: 数据表中所有 field.name 列表。

    Returns:
        在数据表中出现但模型中缺失的字段名列表。
    """
    model_set = set(model_elements)
    inconsistent: list[str] = []
    for field_name in data_fields:
        # 跳过接口保留元素
        if field_name in INTERFACE_RESERVED_ELEMENTS:
            continue
        if field_name.startswith(INTERFACE_HEADER_PREFIX):
            continue
        if field_name not in model_set:
            inconsistent.append(field_name)
    return inconsistent


def validate_verify_table_name(model_name: str, table_name: str) -> bool:
    """验证验证数据表名是否为 {模型名}_verify。

    Args:
        model_name: 模型名称。
        table_name: 数据表名称。

    Returns:
        True 表示符合命名规范。
    """
    return table_name == f"{model_name}{VERIFY_TABLE_SUFFIX}"


# UI 原子动作的匹配模式：
# click / double_click / right_click / hover 是纯字符串
# select【...】 / key_press【...】 / drag【...】 / scroll / scroll【x,y】
_UI_ACTION_PLAIN = {"click", "double_click", "right_click", "hover", "scroll"}
_UI_ACTION_PATTERN = re.compile(
    r"^(select|key_press|drag|scroll)【.*】$"
)


def is_ui_atomic_action(value: str) -> bool:
    """检查数据表字段值是否是 UI 原子动作。

    UI 原子动作包括：
      - click / double_click / right_click / hover / scroll（纯文本）
      - select【值】 / key_press【按键】 / drag【目标】 / scroll【x,y】

    Args:
        value: 数据表 field 的文本值。

    Returns:
        True 表示该值是 UI 原子动作。
    """
    if not value:
        return False
    stripped = value.strip()
    if stripped in _UI_ACTION_PLAIN:
        return True
    if _UI_ACTION_PATTERN.match(stripped):
        return True
    return False


# ============================================================
# 7. RODSKI_CONSTRAINT_SUMMARY  —  LLM 提示词嵌入用摘要
# ============================================================

RODSKI_CONSTRAINT_SUMMARY: str = """\
=== RodSki 框架约束摘要（供 LLM 提示词嵌入） ===

【关键字规则】
- 框架共 15 个关键字：close, type, verify, wait, navigate, launch, assert, \
upload_file, clear, get_text, get, send, set, DB, run
- 兼容关键字：check（等价于 verify）
- 补充 action：screenshot, evaluate
- navigate 与 launch 功能相同（场景化变体），navigate 用于 Web/Mobile，launch 用于 Desktop
- UI 原子动作（click / double_click / right_click / hover / select / key_press / \
drag / scroll）**不是独立关键字**，只能作为数据表 field 值，由 type 批量模式自动识别执行
- 核心三关键字分工：type 只做 UI 写入，send 只做接口请求，verify 通用验证

【Case XML 格式】
- 根元素 <cases>，子元素 <case>
- case 必须属性：execute（是/否）、id、title
- 可选属性：description、component_type（界面/接口/数据库）
- 每个 case 下固定三阶段容器（XSD 顺序）：
  1. <pre_process>（可选，0~n 个 test_step）
  2. <test_case>（必选且仅 1 个，至少 1 个 test_step）
  3. <post_process>（可选，0~n 个 test_step）
- test_step 属性：action（必填）、model（可选）、data（可选）

【Model XML 格式】
- 根元素 <models>，子元素 <model name="...">
- 每个 model 下 <element name="..." type="驱动类型">
- 定位器唯一格式：<location type="定位类型">值</location>
  - 12 种定位类型：id, class, css, xpath, text, tag, name, static, field, \
vision, ocr, vision_bbox
  - 简化格式（type="定位类型" value="值"）已于 v5.4.0 移除
- 元素可有多个 <location>，按 priority 属性从小到大依次尝试
- 接口模型保留元素：_method, _url, _header_*（前缀模式）
- element name **必须与数据表 field name 完全一致**（区分大小写）

【Data XML 格式】
- 操作数据：data/data.xml（根元素 <datatables> 或 <datatable>）
- 验证数据：data/data_verify.xml（可选，也可放在 data.xml 中）
- datatable@name 必须与模型名一致
- 验证数据表名 = {模型名}_verify
- 每个 <row> 须有唯一 id（DataID）
- field@name 须与 model element name 一致
- Case XML data 属性只写 DataID，不写表名前缀
- 特殊值：BLANK（空字符串）、NULL（null）、NONE（不发送）
- ${Return[-1]} 只能出现在数据表 field 值中，不可写在 Case XML data 属性
- 接口/DB 模型的 _verify 表禁止使用 ${Return[-1]}（自引用=空校验）

【目录结构】
- product/{项目}/{模块}/
  - case/（必须）— 用例 XML
  - model/（必须）— model.xml（唯一文件名）
  - data/（必须）— data.xml + data_verify.xml(可选) + globalvalue.xml
  - fun/（可选）— run 关键字的 Python 工程
  - result/（可选）— 框架自动生成结果 XML
"""

# ============================================================
# 8. RODSKI_KEYWORD_REFERENCE  —  关键字简明参考
# ============================================================

RODSKI_KEYWORD_REFERENCE: str = """\
=== RodSki 关键字简明参考 ===

| 关键字 | model | data | 说明 |
|--------|-------|------|------|
| navigate | — | URL 或 GlobalValue 引用 | 导航到 URL；无浏览器时自动创建（Web/Mobile） |
| launch | — | 应用路径或应用名 | 启动或切换桌面应用（Windows/macOS） |
| close | — | — | 关闭浏览器 |
| type | 模型名 | DataID | UI 批量输入；遍历模型元素，从数据表取值逐一操作 |
| verify | 模型名 | DataID | 批量验证（UI + 接口通用）；自动查 {模型名}_verify 表 |
| send | 接口模型名 | DataID | 发 HTTP 请求；从模型取 _method/_url，从数据表取字段值 |
| assert | — | 断言表达式 | 断言（单条） |
| wait | — | 秒数（如 3） | 等待指定秒数 |
| clear | — | CSS 选择器 | 清空输入框 |
| get | 模型名（可选） | DataID / CSS 选择器 / 变量名 | 三模式取值：模型模式 / UI 选择器 / 命名变量读取 |
| get_text | — | CSS 选择器 | 获取元素文本（已废弃，请用 get） |
| set | — | key=value | 写入命名变量到 context.named |
| DB | GlobalValue 连接组名 | SQL 数据表引用（表名.DataID） | 执行 SQL（query 返回结果集，execute 返回受影响行数） |
| run | 工程名（fun/ 子目录） | 脚本文件路径 | 沙箱执行 Python 脚本，stdout 作为返回值 |
| upload_file | — | 文件路径 | 上传文件 |
| screenshot | — | 文件路径 | 手动截图 |
| evaluate | — | JS 表达式 | 执行 JS（仅 Web，低优先级逃生舱） |
| check | 同 verify | 同 verify | 兼容关键字，等价于 verify |

【UI 原子动作（数据表 field 值，非独立关键字）】
| 动作值 | 说明 | 示例 field 值 |
|--------|------|--------------|
| click | 点击元素 | click |
| double_click | 双击元素 | double_click |
| right_click | 右键点击 | right_click |
| hover | 鼠标悬停 | hover |
| select【值】 | 下拉选择 | select【管理员】 |
| key_press【按键】 | 按键操作 | key_press【Tab】 |
| drag【目标】 | 拖拽到目标 | drag【#drop-zone】 |
| scroll | 默认滚动 | scroll |
| scroll【x,y】 | 自定义滚动 | scroll【0,500】 |

【Return 值产出关键字】
| 关键字 | 返回值 |
|--------|--------|
| type | 本次输入的完整数据行 |
| send | HTTP 响应（status + 响应体字段） |
| verify | 实际值字典 |
| get / get_text | 元素文本 |
| assert | 断言结果 |
| DB | query → 结果集列表；execute → 受影响行数 |
| run | 脚本 stdout（自动 JSON 解析） |
"""
