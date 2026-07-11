# AI Agent 网站消费指南

> 本文档说明 AI Agent / LLM 如何高效获取 RodSki 官网的技术文档。

## 发现入口

RodSki 官网遵循 [llms.txt 规范](https://llmstxt.org)，提供标准化的 AI 文档发现路径：

| URL | 说明 |
|-----|------|
| `https://rodski.dev/llms.txt` | 索引文件，列出所有可用文档及其 URL |
| `https://rodski.dev/.well-known/llms.txt` | 备用路径（301 重定向到 `/llms.txt`） |
| `https://rodski.dev/llms-full.txt` | 全量合集，所有 v8 文档拼接为单文件 |

## 获取方式

### 方式一：单篇获取（推荐用于按需检索）

```
GET /llms/v8/{slug}.md
Content-Type: text/plain; charset=utf-8
```

可用 slug 列表：

| slug | 内容 | 大小约 |
|------|------|--------|
| `getting-started` | 安装、目录结构、第一个用例 | 4 KB |
| `keywords` | 17 个关键字完整语法 | 5 KB |
| `test-case-guide` | case/model/data 编写规范 | 10 KB |
| `api-reference` | CLI 命令与公开 API | 5 KB |
| `architecture` | 执行引擎架构、核心类 | 5 KB |
| `changelog` | 版本发布记录 | ~2 KB |
| `index` | v8 文档首页 / 导航 | ~1 KB |

示例：

```bash
curl https://rodski.dev/llms/v8/keywords.md
```

### 方式二：全量获取（推荐用于初始化知识库）

```
GET /llms-full.txt
Content-Type: text/plain; charset=utf-8
```

返回所有 v8 文档拼接结果（~30 KB），各篇之间以 `---` 分隔。
frontmatter 已自动去除，直接为可读 Markdown。

```bash
curl https://rodski.dev/llms-full.txt
```

### 方式三：历史版本

```
GET /llms/v7/{slug}.md
```

可用：`index`、`test-case-guide`

## 响应格式

所有 `/llms/*` 路由返回**纯文本 Markdown**：
- `Content-Type: text/plain; charset=utf-8`
- 含标准 Markdown 格式（标题、列表、表格、代码块）
- 单篇文档保留 YAML frontmatter（`title` + `description` 字段）
- 全量合集（`/llms-full.txt`）已去除 frontmatter

## Agent 集成示例

### Python（requests）

```python
import requests

# 获取索引
index = requests.get("https://rodski.dev/llms.txt").text

# 获取单篇
keywords_doc = requests.get("https://rodski.dev/llms/v8/keywords.md").text

# 获取全量
full_docs = requests.get("https://rodski.dev/llms-full.txt").text
```

### Claude MCP / Tool Use

```json
{
  "name": "fetch_rodski_docs",
  "description": "获取 RodSki 框架文档",
  "input_schema": {
    "type": "object",
    "properties": {
      "slug": {
        "type": "string",
        "enum": ["getting-started", "keywords", "test-case-guide", "api-reference", "architecture"],
        "description": "文档 slug"
      }
    }
  }
}
```

Tool 实现只需 `GET https://rodski.dev/llms/v8/{slug}.md` 并返回文本。

### LangChain WebBaseLoader

```python
from langchain_community.document_loaders import WebBaseLoader

loader = WebBaseLoader("https://rodski.dev/llms-full.txt")
docs = loader.load()
```

## 安全与速率

- 所有 `/llms/*` 路由为只读 GET
- 无需认证
- 响应带 `Cache-Control: public, max-age=3600`
- 无速率限制（合理使用）
- `robots.txt` 显式允许 GPTBot / ClaudeBot / Anthropic-AI 访问

## 路由安全校验

防止路径穿越：
- `version` 必须匹配 `/^v\d+$/`（如 `v8`、`v7`）
- `slug` 必须匹配 `/^[a-z0-9-]+$/`
- 不合法请求返回 404

## 内容更新频率

- 文档随 RodSki 版本发布更新
- `/llms-full.txt` 服务端缓存 24 小时
- 建议 Agent 每天最多刷新一次全量文档
