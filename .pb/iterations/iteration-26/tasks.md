# Iteration 26 任务清单

**版本**: v5.4.0  
**分支**: release/v5.4.0

---

## T26-001: 迁移所有 model XML 到 `<location>` 格式 [1.5h]

> 必须在 T26-002 之前完成，否则 parser 改完后旧 XML 无法解析。

### 任务

1. 扫描所有 `model.xml` 文件，找到使用旧格式的元素
2. 转换 `locator="type:value"` → `<location type="...">value</location>`
3. 转换 `type="id" value="xxx"` → `<location type="id">xxx</location>`
4. 保留 `desc` 属性转为 `<desc>` 子元素

### 改动文件

| 文件 | 旧格式数量 |
|------|-----------|
| `rodski-demo/DEMO/vision_desktop/model/model.xml` | ~15 元素 |
| `rodski-demo/DEMO/vision_web/model/model.xml` | ~3 元素 |
| `rodski-demo/DEMO/demo_full/model/model.xml` | 检查并迁移 |
| `rodski-demo/DEMO/iteration-01-vision/model/model.xml` | 检查并迁移 |
| `cassmall/` 下所有 model.xml | 检查并迁移 |

### 转换规则

```xml
<!-- Before: locator 属性 -->
<element name="textArea" locator="vision:文本编辑区域"/>
<!-- After -->
<element name="textArea">
  <location type="vision">文本编辑区域</location>
</element>

<!-- Before: type+value 简化 -->
<element name="usernameById" type="id" value="userName" desc="用户名输入框"/>
<!-- After -->
<element name="usernameById">
  <location type="id">userName</location>
  <desc>用户名输入框</desc>
</element>

<!-- Before: locator + static -->
<element name="appPath" locator="static:notepad.exe"/>
<!-- After -->
<element name="appPath">
  <location type="static">notepad.exe</location>
</element>
```

### 验证

- 每个转换后的 XML 文件 `python -c "import xml.etree.ElementTree as ET; ET.parse('file.xml')"` 验证格式正确
- 全项目 `grep -r 'locator="' --include="*.xml"` 返回零结果

---

## T26-002: model_parser.py 移除旧定位器格式 [1.5h]

> 依赖 T26-001 完成。

### 任务

1. 删除 `_parse_element()` 中 `locator` 属性解析代码块（lines 143-164）
2. 删除 `_parse_element()` 中 `type+value` 简化格式代码块（lines 195-209）
3. 保留 `<location>` 子元素解析代码块（lines 166-193）
4. 确保 `<element type="web">` 的 `type` 仅用于 driver 类型推断
5. 更新相关单元测试

### 改动文件

| 文件 | 改动 |
|------|------|
| `rodski/core/model_parser.py` | 删除两种旧格式解析 |
| `rodski/tests/unit/test_model_parser.py` | 更新测试用例为 `<location>` 格式 |

### 验证

```bash
pytest rodski/tests/unit/test_model_parser.py -v
```

---

## T26-003: vision/locator.py 移除旧前缀解析 [0.5h]

> 依赖 T26-002 完成。

### 任务

1. `locate_legacy()` 和 `locate_with_driver()` 添加 deprecation warning
2. `is_vision_locator(locator_str)` 前缀检查方法标记废弃
3. 确认 `locate(locator_type, locator_value, screenshot)` 作为唯一公开 API

### 改动文件

| 文件 | 改动 |
|------|------|
| `rodski/vision/locator.py` | 添加 deprecation warning |
| `rodski/tests/unit/test_vision_locator.py` | 更新测试（如有依赖旧 API） |

### 验证

```bash
pytest rodski/tests/unit/test_vision_locator.py -v
```

---

## T26-004: 移除 Excel 相关代码 [0.5h]

### 任务

1. 删除 `rodski/requirements.txt` 中 `openpyxl>=3.1.0`
2. 删除 `rodski/tests/conftest.py` 中 openpyxl warning filter
3. 替换所有代码中 `.xlsx` 引用为 `.xml`
4. 更新代码注释中的 Excel 历史引用

### 改动文件

| 文件 | 改动 |
|------|------|
| `rodski/requirements.txt` | 删除 openpyxl |
| `rodski/tests/conftest.py` line 7 | 删除 warning filter |
| `rodski/rodski_cli/run.py` help text | `.xlsx` → `.xml` |
| `rodski/tests/unit/test_cli_ux.py` | `.xlsx` → `.xml` |
| `rodski/tests/unit/test_keyword_engine.py` | `.xlsx` → `.xml` |
| `rodski/tests/integration/test_cli_commands.py` | `.xlsx` → `.xml` |
| `rodski/core/result_writer.py` line 3 | 更新注释 |
| `rodski/core/ski_executor.py` line 3 | 更新注释 |
| `rodski/core/global_value_parser.py` line 3 | 更新注释 |

### 验证

```bash
grep -r "xlsx\|openpyxl" rodski/ --include="*.py"
# 应返回零结果
```

---

## T26-005: Agent 示例归档 [0.5h]

### 任务

1. 移动 `rodski/examples/agent/` → `.pb/archive/agent_examples/`
2. 检查 `rodski/examples/` 是否还有其他内容，如果为空则删除目录
3. 更新引用这些文件的文档指向归档位置

### 移动文件

```
rodski/examples/agent/multi_agent_example.py → .pb/archive/agent_examples/
rodski/examples/agent/claude_code_integration.py → .pb/archive/agent_examples/
rodski/examples/agent/opencode_integration.py → .pb/archive/agent_examples/
rodski/examples/agent/README.md → .pb/archive/agent_examples/
```

### 验证

```bash
ls rodski/examples/agent/
# 应报错：目录不存在

ls .pb/archive/agent_examples/
# 应包含 4 个文件
```

---

## T26-006: 全量回归测试 [0.5h]

### 任务

1. 运行全量单元测试
2. 运行 grep 审计
3. 确认 rodski-demo 的 model XML 可被正确解析

### 验证

```bash
# 单元测试
pytest rodski/tests/ -v

# 格式审计
grep -r 'locator="' rodski/ --include="*.xml"
grep -r "xlsx\|openpyxl" rodski/ --include="*.py"

# XML 解析验证
python -c "
from rodski.core.model_parser import ModelParser
mp = ModelParser()
# 验证 demo_full model
mp.parse('rodski-demo/DEMO/demo_full/model/model.xml')
print('demo_full: OK')
"
```

---

## 执行顺序

```
T26-001 (XML 迁移)
    ↓
T26-002 (parser 代码改动)
    ↓
T26-003 (vision/locator 更新)
    ↓
T26-004 (Excel 移除)  ← 与 T26-005 并行
T26-005 (Agent 归档)  ← 与 T26-004 并行
    ↓
T26-006 (全量回归)
```

## 工时估算

| 任务 | 预估 |
|------|------|
| T26-001 | 1.5h |
| T26-002 | 1.5h |
| T26-003 | 0.5h |
| T26-004 | 0.5h |
| T26-005 | 0.5h |
| T26-006 | 0.5h |
| **合计** | **5h** |
