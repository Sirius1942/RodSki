# RodSki v6.7.10 Release

## 安装方式

### 从本目录 wheel 安装

```bash
pip install rodski-6.7.10-py3-none-any.whl
```

### 离线安装（无网络环境）

```bash
pip install --no-index --find-links=deps/ rodski-6.7.10-py3-none-any.whl
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `rodski-6.7.10-py3-none-any.whl` | Python wheel 包，推荐安装 |
| `rodski-6.7.10.tar.gz` | 源码包 |
| `deps/` | 离线依赖包（无网络环境使用） |
| `SHA256SUMS` | 文件校验和 |
| `OFFLINE_INSTALL.md` | 离线安装详细指南 |

## 校验

```bash
shasum -a 256 -c SHA256SUMS
```
