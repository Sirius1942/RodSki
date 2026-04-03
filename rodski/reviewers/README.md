# LLM 测试结果审查器

基于 LLM 的智能测试结果审查器，可以根据测试用例、执行日志和截图判断测试是否真正成功。

## 配置

编辑 `rodski/llm_config.yaml`：

```yaml
api_key: "your-api-key-here"  # 或设置环境变量 OPENAI_API_KEY
model: "gpt-4o"
```

支持任何符合 OpenAI ChatGPT 接口的服务（OpenAI、Azure、本地部署等）。

## 使用方法

### 命令行

```bash
# 基本用法
python -m rodski.reviewers.cli /path/to/result_dir

# 包含测试用例定义
python -m rodski.reviewers.cli /path/to/result_dir /path/to/case.xml
```

### Python API

```python
from rodski.reviewers import LLMReviewer

reviewer = LLMReviewer()
result = reviewer.review_result(
    result_dir="/path/to/result_dir",
    case_xml="/path/to/case.xml"  # 可选
)

print(result['verdict'])      # PASS/FAIL/SUSPICIOUS
print(result['confidence'])   # 0.0-1.0
print(result['reason'])       # 判断理由
print(result['issues'])       # 发现的问题列表
```

## 工作原理

1. 读取测试结果（XML + 日志 + 截图）
2. 将信息发送给 LLM（支持 vision 模型分析截图）
3. LLM 判断测试是否真正成功
4. 返回结构化审查结果

## 示例

```bash
python -m rodski.reviewers.cli \
  CassMall_examples/inquiry/result/run_20260403_084451 \
  CassMall_examples/inquiry/cases/cassmall_inquiry_xiaoli.xml
```
