# 错误处理最佳实践

**版本**: v1.0
**日期**: 2026-03-29
**目标读者**: AI Agent

---

## 1. 错误分类

### 1.1 定位错误

**症状**: 元素未找到

**原因**:
- vision 描述不准确
- vision_bbox 坐标偏移
- 元素尚未加载

**Agent 处理策略**:
```python
if error_type == "element_not_found":
    # 1. 重新探索页面
    screenshot = capture_screen()
    elements = agent.analyze_screenshot(screenshot)

    # 2. 更新定位器
    update_model_xml(element_name, new_locator)

    # 3. 重试
    retry_execution()
```

---

### 1.2 超时错误

**症状**: 操作超时

**原因**:
- 页面加载慢
- 网络延迟
- 元素动态加载

**Agent 处理策略**:
```python
if error_type == "timeout":
    # 添加等待步骤
    add_wait_step_before(failed_step, wait_seconds=5)
    retry_execution()
```

---

### 1.3 验证错误

**症状**: 验证失败

**原因**:
- 期望值不匹配
- 元素状态变化
- 数据错误

**Agent 处理策略**:
```python
if error_type == "verification_failed":
    # 1. 获取实际值
    actual_value = get_element_text(element_name)

    # 2. 分析差异
    if actual_value != expected_value:
        # 更新期望值或调整测试逻辑
        update_data_xml(row_id, field_name, actual_value)
```

---

### 1.4 XML 格式错误

**症状**: XML 解析失败

**原因**:
- 标签未闭合
- 属性缺失
- 特殊字符未转义

**Agent 处理策略**:
```python
def validate_xml(xml_string):
    try:
        ET.fromstring(xml_string)
        return True
    except ET.ParseError as e:
        # 修复 XML 格式
        fix_xml_format(xml_string, e)
        return False
```

---

## 2. 重试机制

### 2.1 简单重试

```python
def execute_with_retry(case_xml, max_retries=3):
    for attempt in range(max_retries):
        result = subprocess.run(
            ["python", "rodski/ski_run.py", case_xml],
            capture_output=True
        )

        if result.returncode == 0:
            return result

        time.sleep(2)  # 等待后重试

    return result
```

### 2.2 智能重试

```python
def smart_retry(case_xml, max_retries=3):
    for attempt in range(max_retries):
        result = subprocess.run(
            ["python", "rodski/ski_run.py", case_xml],
            capture_output=True
        )

        if result.returncode == 0:
            return result

        # 分析错误并调整
        error = parse_error(result.stderr)

        if error["type"] == "element_not_found":
            re_explore_and_update(error["element"])
        elif error["type"] == "timeout":
            increase_wait_time(case_xml)
        elif error["type"] == "verification_failed":
            update_expected_value(error["field"])
        else:
            break  # 未知错误，停止重试

    return result
```

---

## 3. 错误恢复策略

### 3.1 定位器降级

```python
def fallback_locator(element_name):
    """从精确定位器降级到模糊定位器"""
    locators = [
        f"xpath://[@id='{element_name}']",  # 最精确
        f"vision_bbox:x,y,w,h",              # 精确坐标
        f"vision:{element_name}",            # 模糊描述
    ]

    for locator in locators:
        if try_locate(locator):
            return locator

    return None
```

### 3.2 步骤跳过

```python
def skip_failed_step(case_xml, failed_step_index):
    """跳过失败步骤，继续执行"""
    tree = ET.parse(case_xml)
    root = tree.getroot()

    steps = root.findall(".//test_step")
    steps[failed_step_index].set("execute", "否")

    tree.write(case_xml)
```

### 3.3 环境重置

```python
def reset_environment():
    """重置测试环境"""
    # 关闭所有浏览器
    subprocess.run(["pkill", "chrome"])

    # 清理临时文件
    shutil.rmtree("result/screenshots", ignore_errors=True)

    # 等待环境稳定
    time.sleep(3)
```

---

## 4. 日志与调试

### 4.1 启用详细日志

```python
result = subprocess.run(
    ["python", "rodski/ski_run.py", "case/test.xml", "--verbose"],
    capture_output=True,
    text=True
)

# 保存日志
Path("logs/execution.log").write_text(result.stdout)
```

### 4.2 截图分析

```python
def analyze_failure_screenshot(case_id):
    """分析失败时的截图"""
    screenshot_path = f"result/screenshots/{case_id}_fail.png"

    if Path(screenshot_path).exists():
        # Agent 分析截图
        analysis = agent.analyze_image(screenshot_path)
        return analysis

    return None
```

### 4.3 错误上下文

```python
def collect_error_context(result):
    """收集错误上下文信息"""
    context = {
        "returncode": result.returncode,
        "stderr": result.stderr,
        "stdout": result.stdout,
        "timestamp": datetime.now().isoformat(),
        "screenshot": find_latest_screenshot(),
        "xml_files": list_xml_files(),
    }

    return context
```

---

## 5. 常见问题解决

### 5.1 元素定位失败

**问题**: vision 定位器找不到元素

**解决方案**:
```python
# 1. 重新探索
screenshot = capture_screen()
elements = agent.analyze_screenshot(screenshot)

# 2. 使用更详细的描述
locator = f"vision:蓝色背景的登录按钮，位于页面右上角"

# 3. 或使用精确坐标
locator = f"vision_bbox:1850,50,100,40"
```

### 5.2 坐标偏移

**问题**: vision_bbox 坐标不准确

**解决方案**:
```python
# 切换到 vision 描述
old_locator = "vision_bbox:100,200,50,30"
new_locator = "vision:提交按钮"

update_model_xml(element_name, new_locator)
```

### 5.3 动态内容

**问题**: 页面内容动态变化

**解决方案**:
```python
# 添加等待步骤
<test_step action="wait" model="" data="3"/>

# 或使用灵活的 vision 定位器
<element name="dynamicBtn" locator="vision:确认按钮"/>
```

### 5.4 多语言页面

**问题**: 页面语言变化导致定位失败

**解决方案**:
```python
# 使用视觉特征而非文本
locator = "vision:绿色的提交按钮"  # 而非 "vision:Submit按钮"
```

---

## 6. 错误预防

### 6.1 XML 验证

```python
def validate_before_execution(xml_file):
    """执行前验证 XML"""
    try:
        tree = ET.parse(xml_file)

        # 检查必需属性
        for case in tree.findall(".//case"):
            assert case.get("id"), "缺少 case id"
            assert case.get("title"), "缺少 case title"

        return True
    except Exception as e:
        print(f"XML 验证失败: {e}")
        return False
```

### 6.2 定位器测试

```python
def test_locators(model_xml):
    """测试所有定位器是否有效"""
    tree = ET.parse(model_xml)

    for element in tree.findall(".//element"):
        name = element.get("name")
        locator = element.get("locator")

        if not test_single_locator(locator):
            print(f"定位器失败: {name} - {locator}")
```

### 6.3 环境检查

```python
def check_environment():
    """检查执行环境"""
    checks = {
        "浏览器驱动": check_driver_installed(),
        "网络连接": check_network(),
        "文件权限": check_file_permissions(),
    }

    for check, result in checks.items():
        if not result:
            print(f"环境检查失败: {check}")
```

---

**文档版本**: v1.0
**最后更新**: 2026-03-29
