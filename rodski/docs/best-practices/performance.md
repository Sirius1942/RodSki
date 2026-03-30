# Performance Best Practices

RodSki 性能优化指南，涵盖浏览器复用、元素定位优化、等待策略、并行执行和内存管理。

---

## 1. 浏览器复用策略

### 1.1 共享 vs 独立模式

| 模式 | 适用场景 | 优点 | 缺点 |
|-----|---------|------|------|
| **共享模式** | 多个用例使用相同登录状态 | 启动快，资源共享 | 状态可能污染 |
| **独立模式** | 用例间状态独立 | 隔离性好，无干扰 | 启动慢，资源占用高 |

```yaml
# 共享模式配置
browser:
  reuse: true
  max_reuse_count: 10  # 最大复用次数

# 独立模式配置
browser:
  reuse: false
  driver_type: "playwright"
```

### 1.2 浏览器定期回收

防止内存泄漏，定期重启浏览器：

```yaml
execution:
  browser_restart_interval: 50  # 每 50 步重启
  browser_restart_on_error: true  # 错误后也重启
```

**实现原理**：
- SKIExecutor 维护步数计数器 `self._step_count`
- 每执行一步计数器 +1
- 达到阈值时触发 `driver.restart()`
- 重启前保存当前 URL，重启后通过 navigate 恢复
- 重新绑定元素引用，避免 StaleElementError

```python
# 内部实现概要
class SKIExecutor:
    def __init__(self, keyword_engine, config):
        self._step_count = 0
        self._restart_interval = config.get("browser_restart_interval", 50)

    def _execute_step(self, step):
        self._step_count += 1
        result = self._do_execute_step(step)

        if self._step_count % self._restart_interval == 0:
            self._recycle_browser()

        return result

    def _recycle_browser(self):
        # 保存状态
        current_url = self.driver.current_url
        # 重启
        self.driver.restart()
        # 恢复
        if current_url:
            self.driver.navigate(current_url)
```

---

## 2. 元素定位优化

### 2.1 定位器优先级

按性能排序（推荐优先使用）：

| 优先级 | 定位器类型 | 示例 | 速度 |
|-------|----------|------|-----|
| 1 | ID | `id=login-btn` | 最快 |
| 2 | NAME | `name=username` | 快 |
| 3 | CSS Selector | `css=#form > button.primary` | 快 |
| 4 | Link Text | `link=登录` | 快 |
| 5 | XPath (绝对) | `xpath=/html/body/div[2]/form/button` | 慢 |
| 6 | XPath (函数) | `xpath=//button[contains(text(),'登录')]` | 最慢 |

### 2.2 定位器最佳实践

**✅ 推荐写法**:
```xml
<!-- 直接 ID -->
<element id="submit" type="id" value="submit-btn"/>

<!-- CSS 类名 -->
<element id="search" type="css" value="button.search-btn"/>

<!-- 相对 XPath (包含 @id 或 @name) -->
<element id="username" type="xpath" value="//input[@id='username']"/>
```

**❌ 避免写法**:
```xml
<!-- 通配符 XPath -->
<element id="slow" type="xpath" value="//div[@class='container']//span[contains(text(),'Login')]"/>

<!-- 绝对 XPath -->
<element id="brittle" type="xpath" value="/html/body/div[1]/div[2]/form/div[3]/button"/>

<!-- 链式兄弟 XPath -->
<element id="brittle2" type="xpath" value="//label[contains(text(),'Name')]/following-sibling::input"/>
```

### 2.3 动态元素定位

```python
# 使用模糊匹配处理动态 ID
def dynamic_locator(base_locator, suffix):
    return f"{base_locator}_{suffix}"

# 使用父元素定位
def parent_based_locator(parent_id, child_css):
    return f"#{parent_id} {child_css}"
```

---

## 3. 等待策略最佳实践

### 3.1 等待类型对比

| 类型 | 说明 | 适用场景 | 性能 |
|-----|------|---------|-----|
| **固定等待** | `wait N` | 已知稳定的延迟 | 最差 |
| **隐式等待** | 全局配置 | 元素加载 | 一般 |
| **显式等待** | 条件满足为止 | 动态内容 | 最佳 |
| **智能等待** | AI 判断 | 复杂场景 | 最优 |

### 3.2 显式等待配置

```yaml
# 全局等待配置
execution:
  default_wait: 10        # 默认等待秒数
  poll_frequency: 0.5     # 轮询间隔
  explicit_wait_until: "element_visible"  # 等待条件
```

### 3.3 自定义等待条件

```python
from core.keyword_engine import KeywordEngine

def wait_for_text(driver, params, context):
    """等待元素包含指定文本"""
    locator = params["locator"]
    expected_text = params["text"]
    timeout = int(params.get("timeout", 30))

    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    element = WebDriverWait(driver, timeout).until(
        EC.text_to_be_present_in_element((By.CSS_SELECTOR, locator), expected_text)
    )
    return {"status": "PASS", "element": element}

engine = KeywordEngine(driver_factory)
engine.register_keyword("wait_for_text", wait_for_text)
```

### 3.4 等待策略配置示例

```yaml
# 全局等待时间 (globalvalue.xml)
globalvalue:
  default_wait: 5000  # 毫秒

# 用例级等待 (case.xml)
<case step_wait="3000">  <!-- 毫秒 -->
```

---

## 4. 并行执行配置

### 4.1 基本配置

```yaml
execution:
  parallel_enabled: true
  max_workers: 4          # 最大并行数
  load_balance: "round_robin"  # 负载均衡策略
```

### 4.2 并行执行器

```python
from core.parallel_executor import ParallelExecutor

executor = ParallelExecutor(
    max_workers=4,
    strategy="load_balance",  # round_robin | random | by_duration
)

results = executor.execute_suite(
    case_patterns=["cases/*.xml"],
    variables={"env": "staging"},
)
```

### 4.3 并行注意事项

1. **浏览器隔离**: 每个 worker 使用独立浏览器实例
2. **端口冲突**: 不同浏览器实例使用不同端口
3. **状态共享**: 避免使用共享变量或文件
4. **资源限制**: 根据 CPU 核心数设置 `max_workers`

**推荐配置**:
- CPU 4 核: `max_workers = 2~3`
- CPU 8 核: `max_workers = 4~6`
- 内存 16GB: `max_workers <= 4`

### 4.4 用例分组策略

将可并行的用例分组，减少资源冲突：

```python
# 按组件分组并行
groups = {
    "auth": ["login.xml", "logout.xml", "reset_pwd.xml"],
    "catalog": ["search.xml", "filter.xml", "sort.xml"],
    "cart": ["add_cart.xml", "remove_cart.xml", "checkout.xml"],
}

# 组内串行，组间并行
for group_name, cases in groups.items():
    parallel_executor.execute(cases)  # 组内并行
```

---

## 5. 内存管理

### 5.1 内存泄漏监控

RodSki 内置内存监控：

```yaml
execution:
  memory_check_interval: 10    # 每 N 步检查一次
  memory_gc_threshold_mb: 100   # 增长阈值 (MB)
  gc_aggressive_mode: false     # 激进 GC 模式
```

**监控输出示例**:
```
[MemoryMonitor] step=10, current=45MB, delta=+5MB
[MemoryMonitor] step=20, current=52MB, delta=+7MB
[MemoryMonitor] step=30, current=95MB, delta=+43MB ⚠️ 触发 GC
[GC] 回收内存: 释放约 30MB
[MemoryMonitor] step=30, current=65MB, delta=-30MB
```

### 5.2 手动 GC 触发

```python
import gc
import tracemalloc

# 手动触发垃圾回收
def force_garbage_collection():
    gc.collect()
    print(f"GC completed: {gc.get_stats()}")

# 追踪内存
tracemalloc.start()
snapshot1 = tracemalloc.take_snapshot()
# ... 执行步骤 ...
snapshot2 = tracemalloc.take_snapshot()

# 对比内存增长
top_stats = snapshot2.compare_to(snapshot1, 'lineno')
for stat in top_stats[:10]:
    print(stat)
```

### 5.3 快照管理

控制快照保存频率，避免占用过多磁盘：

```yaml
execution:
  snapshot_enabled: true
  snapshot_interval: 10       # 每 N 步保存一次
  snapshot_max_count: 100     # 最多保留快照数
  snapshot_compress: true     # 压缩快照
```

**快照内容**:
```json
{
  "case_id": "TC001",
  "step_index": 15,
  "variables": {"count": 15, "user": "admin"},
  "url": "https://example.com/page3",
  "dom_summary": "form:1, input:5, button:2",
  "timestamp": "2026-03-30T10:30:00"
}
```

---

## 6. 网络优化

### 6.1 请求优化

```yaml
network:
  request_timeout: 30
  retry_on_network_error: 3
  mock_local_resources: true  # 本地模拟静态资源
```

### 6.2 资源预加载

对于多步骤流程，预加载下一个页面资源：

```python
# 在步骤之间预加载
def preload_next_page(driver, current_step, next_url):
    """预加载下一页"""
    # 执行当前步骤
    result = execute_step(driver, current_step)
    # 预加载下一个 URL（不等待完成）
    driver.preload(next_url)
    return result
```

---

## 7. 性能调优检查清单

### 7.1 启动优化
- [ ] 使用 `browser.reuse = true` 减少浏览器启动
- [ ] 使用 headless 模式 `browser.headless = true`
- [ ] 禁用图片加载 `browser.block_images = true`
- [ ] 禁用 CSS `browser.disable_css = true`

### 7.2 执行优化
- [ ] 使用显式等待代替固定等待
- [ ] 优先使用 ID/Name 定位器
- [ ] 避免过深的 XPath
- [ ] 配置合理的 `browser_restart_interval`

### 7.3 资源优化
- [ ] 启用内存监控和 GC
- [ ] 定期清理截图和日志
- [ ] 使用快照压缩
- [ ] 配置快照最大保留数

### 7.4 并行优化
- [ ] 根据 CPU/内存设置 `max_workers`
- [ ] 按组件分组用例
- [ ] 避免并行用例间的状态共享
- [ ] 使用独立的浏览器配置文件

---

## 8. 性能基准测试

建议定期运行基准测试，监控性能变化：

```bash
# 运行基准测试
ski run benchmarks/login_benchmark.xml --output-format json

# 对比结果
ski stats output/benchmarks --from 2026-03-01 --to 2026-03-30 --format json
```

**关注指标**:
- 平均执行时间 (avg_duration)
- P50/P95/P99 响应时间
- 内存使用峰值
- 浏览器重启次数
- 失败率

---

## 9. 常见性能问题与解决方案

| 问题 | 原因 | 解决方案 |
|-----|------|---------|
| 执行慢 (>5min/case) | 等待时间过长 | 优化等待策略，使用显式等待 |
| 内存持续增长 | 浏览器未回收 | 配置 `browser_restart_interval` |
| 并行执行失败率高 | 资源竞争 | 降低 `max_workers`，隔离浏览器 |
| CPU 占用 100% | 轮询过于频繁 | 调整 `poll_frequency` |
| 磁盘空间快速耗尽 | 截图过多 | 配置快照压缩和最大数量 |
| 网络请求慢 | 未禁用无用资源 | 启用 `block_images`, `disable_css` |
