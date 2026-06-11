# RodSki v8.0.3 Release

## 更新内容

### Bug Fix

- **evaluate 关键字捕获浏览器 console.warn/error**：执行期间注册 `page.on('console')` 监听器，warning/error 级别消息自动输出到执行日志。解决了脚本内部性能告警（如 `[rs-perf]`）被静默丢弃的问题。

- **慢步骤检测**：关键字执行完成后自动检测耗时，超过阈值输出 `[SLOW] action=xxx 耗时 Ns（阈值 5.0s）`。
  - 默认阈值 5 秒
  - 支持代码设置：`engine.slow_step_threshold = N`
  - 支持 case XML 覆盖：`slow_threshold` 属性

## 安装方式

### 从本目录 wheel 安装

```bash
pip install rodski-8.0.3-py3-none-any.whl
```

### 离线安装（无网络环境）

```bash
pip install --no-index --find-links=deps/ rodski-8.0.3-py3-none-any.whl
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `rodski-8.0.3-py3-none-any.whl` | Python wheel 包，推荐安装 |
| `rodski-8.0.3.tar.gz` | 源码包 |
| `SHA256SUMS` | 文件校验和 |

## 校验

```bash
shasum -a 256 -c SHA256SUMS
```
