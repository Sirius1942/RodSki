# Iteration 13: 验收测试

## 设计合规性检查

| 检查项 | 结论 |
|--------|------|
| 不引入新关键字，不改变 case XML 语法 | ✅ |
| 日志输出不影响测试结果判定 | ✅ |
| execution_summary.json 独立于日志文本 | ✅ |
| 复用 iteration-12 的 demo 用例 | ✅ |

---

## AC13-001: Info 模式日志摘要验证

**测试用例名称**: Info 模式每步输出摘要，包含 auto_capture 和 named 写入信息

**case/ac13_info_log.xml**（复用 iteration-12 的 DemoForm 模型和数据）:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="AC13-001" title="Info模式日志摘要" component_type="界面">
    <pre_process>
      <test_step action="navigate" model="" data="http://localhost:8000/form"/>
    </pre_process>
    <test_case>
      <test_step action="type" model="DemoForm" data="F001"/>
      <test_step action="set" model="" data="saved_id=${Return[-1].resultId}"/>
      <test_step action="get" model="" data="saved_id"/>
    </test_case>
    <post_process>
      <test_step action="close" model="" data=""/>
    </post_process>
  </case>
</cases>
```

**运行方式**: `python ski_run.py ... --log-level info`（默认）

**验收条件**:
- 每步输出一行摘要，包含 `action`、`model`、`status`
- type 步骤摘要包含 auto_capture 字段名和值
- set 步骤摘要包含写入的变量名和值
- 不输出内部解析细节

---

## AC13-002: Debug 模式完整链路验证

**测试用例名称**: Debug 模式可看到参数解析链和 history/named 增量

**case XML**: 同 AC13-001

**运行方式**: `python ski_run.py ... --log-level debug`

**验收条件**:
- 可看到模板替换前后的参数值（如 `${Return[-1].resultId}` → 实际值）
- 可看到 auto_capture 触发过程（字段名、locator、读取值）
- 可看到每步后 history/named 的增量变化
- 失败时可区分：动作失败 / AutoCaptureError / 命名读取失败

---

## AC13-003: execution_summary.json 结构验证

**测试用例名称**: 用例执行后生成结构化结果文件

**case XML**: 同 AC13-001

**验收条件**:
- 结果目录存在 `execution_summary.json`
- 每步包含 `return_source` 字段，值为以下之一：`keyword_result` / `auto_capture` / `get_named` / `evaluate`
- type 步骤的 `return_source` 为 `auto_capture`
- set 步骤的 `named_writes` 包含 `saved_id`
- 末尾包含 `context_snapshot.named`

---

## rodski 开发需求

**需要开发**: T13-001 ~ T13-006  
**demo 开发**: 不需要，复用 iteration-12 的 DemoForm 模型和数据
