# rodski-agent 用户使用指南

**版本**: 2.3.0  
**日期**: 2026-05-12

---

## 1. 安装

```bash
pip install rodski-agent
```

验证安装：

```bash
rodski-agent --version
```

---

## 2. 命令概览

| 命令 | 说明 |
|------|------|
| `rodski-agent run` | 执行测试用例，支持失败诊断和自动重试 |
| `rodski-agent design` | 根据需求描述生成测试用例 XML |
| `rodski-agent pipeline` | 串联 design + run，从需求到执行一步完成 |
| `rodski-agent diagnose` | 对已有执行结果进行失败根因分析 |
| `rodski-agent narrate` | 将测试用例转换为人类可读的 Markdown 文档 |
| `rodski-agent config show` | 显示当前配置 |

全局选项：

```bash
rodski-agent --format json <command>   # JSON 格式输出（默认 human）
```

---

## 3. run — 执行测试

```bash
rodski-agent run --case <case_xml_path> [选项]
```

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--case` | 测试用例 XML 文件路径（必填） | — |
| `--max-retry` | 最大重试次数 | 3 |
| `--headless` | 无头模式运行浏览器 | 否 |
| `--browser` | 浏览器类型 | chromium |

示例：

```bash
# 执行用例，失败自动重试最多 2 次
rodski-agent run --case cassmall/login/case/login.xml --max-retry 2 --headless

# JSON 格式输出（供 CI 解析）
rodski-agent --format json run --case cassmall/login/case/login.xml
```

退出码：
- `0` — 全部通过
- `1` — 有用例失败
- `2` — Agent 执行错误

---

## 4. design — 生成测试用例

```bash
rodski-agent design --requirement <需求描述> --output <输出目录> [选项]
```

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--requirement` | 需求描述文本（必填） | — |
| `--output` | 输出目录路径（必填） | — |
| `--url` | 目标页面 URL（可选，启用视觉探索） | — |

示例：

```bash
# 根据需求生成用例
rodski-agent design --requirement "用户登录功能测试" --output cassmall/login/

# 带视觉探索（自动识别页面元素）
rodski-agent design --requirement "订单列表查询" --output cassmall/order/ --url http://localhost:8000/orders
```

生成结果：

```
cassmall/login/
├── case/    ← 测试用例 XML
├── model/   ← 页面模型 XML
└── data/    ← 测试数据
```

---

## 5. pipeline — 从需求到执行

```bash
rodski-agent pipeline --requirement <需求> --output <目录> [选项]
```

串联 design → run，先生成用例再执行：

```bash
rodski-agent pipeline \
  --requirement "登录功能回归测试" \
  --output cassmall/login/ \
  --max-retry 2 \
  --headless
```

---

## 6. diagnose — 失败诊断

```bash
rodski-agent diagnose --result <result_dir_or_json>
```

对已有的执行结果进行 LLM 辅助诊断，输出失败根因分析：

```bash
rodski-agent diagnose --result rodski-demo/DEMO/demo_full/result/rodski_20260423_090801/
```

诊断输出包含：
- `root_cause` — 根因描述
- `category` — 分类（CASE_DEFECT / ENV_DEFECT / PRODUCT_DEFECT / UNKNOWN）
- `confidence` — 置信度
- `suggestion` — 修复建议

---

## 7. narrate — 用例解读

将 XML 测试用例转换为业务人员可读的 Markdown 文档。

```bash
rodski-agent narrate --case <case_xml_path> [选项]
```

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--case` | 测试用例 XML 文件路径（必填） | — |
| `--id` | 指定用例 ID（可多次使用，不指定则全部） | 全部 |
| `--log` | 执行日志路径（可选，增强解读内容） | — |

示例：

```bash
# 解读全部用例
rodski-agent narrate --case rodski-demo/DEMO/demo_full/case/demo_case.xml

# 只解读指定用例
rodski-agent narrate --case rodski-demo/DEMO/demo_full/case/demo_case.xml --id TC001 --id TC004

# 带执行日志增强
rodski-agent narrate --case rodski-demo/DEMO/demo_full/case/demo_case.xml \
  --log rodski-demo/DEMO/demo_full/result/rodski_20260423_090801/execution.log
```

输出目录：`{用例所在模块}/narrative/`，每个用例一个 `.md` 文件。

### 7.1 解读特性

**数据内联**：不显示 DataID，展开为具体字段值

```
# 不会输出：
使用测试数据 L001

# 而是输出：
输入 用户名: admin、密码: 123456，点击登录按钮
```

**动态引用保留**：`${Return[...]}`、`${random(...)}`、`${date(...)}` 等运行时表达式原样保留并附加中文解释

```
# 输出示例：
用户名: ${random(int, 4)}（随机生成 4 位整数）
订单号: ORD_${date(today, %Y%m%d)}_${random(digits, 4)}（"ORD_" + 日期 + 4位随机数）
验证 token: ${Return[-1].token}（获取上一步骤返回的 token 字段）
```

**支持的数据源**：
- SQLite 格式（`data/data.sqlite`）— 自动加载
- XML 格式（`data/data.xml`、`data/data_verify.xml`）— 自动加载

---

## 8. config — 配置管理

```bash
# 显示当前配置
rodski-agent config show
```

### 8.1 配置文件

配置文件位置（按优先级）：
1. 当前目录 `./agent_config.yaml`
2. 项目根目录 `rodski-agent/config/agent_config.yaml`

### 8.2 LLM 配置

rodski-agent 使用 LangChain 调用 LLM，支持 Anthropic 和 OpenAI：

```yaml
llm:
  execution:
    provider: anthropic
    model: claude-sonnet-4-6
    temperature: 0.1
    max_tokens: 4096
  design:
    provider: anthropic
    model: claude-sonnet-4-6
    temperature: 0.7
    max_tokens: 8192
```

环境变量：
- `ANTHROPIC_API_KEY` — Anthropic API 密钥
- `OPENAI_API_KEY` — OpenAI API 密钥

---

## 9. 与 rodski 框架的关系

```
┌─────────────────────────────────────────┐
│  rodski-agent（AI Agent 层）             │
│  - 用例生成、执行编排、诊断、解读        │
│  - 通过 CLI 调用 rodski                  │
└──────────────────┬──────────────────────┘
                   │ subprocess / CLI
┌──────────────────▼──────────────────────┐
│  rodski（测试执行引擎）                  │
│  - 关键字驱动、数据表解析、浏览器控制    │
│  - pip install rodski                    │
└─────────────────────────────────────────┘
```

- rodski-agent 不直接 import rodski，通过 subprocess 调用 `rodski` CLI
- 两者独立安装、独立版本号、独立发布
- rodski-agent 需要 rodski 已安装在 PATH 中

---

## 10. 常见用法

### 日常回归测试

```bash
rodski-agent run --case cassmall/order/case/order_crud.xml --headless --max-retry 2
```

### 新功能快速生成用例

```bash
rodski-agent design --requirement "用户注册：手机号+验证码+密码" --output cassmall/register/
```

### 生成测试报告给业务方

```bash
rodski-agent narrate --case cassmall/order/case/order_crud.xml
# 输出 narrative/*.md 发给产品/业务评审
```

### CI/CD 集成

```bash
rodski-agent --format json run --case cassmall/smoke/case/smoke.xml --headless | jq '.output.summary'
```
