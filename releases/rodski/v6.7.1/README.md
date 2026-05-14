# RodSki v6.7.1 Release

## 安装方式

### 从本目录 wheel 安装

```bash
pip install rodski-6.7.1-py3-none-any.whl
```

### 从 PyPI 安装

```bash
pip install rodski==6.7.1
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `rodski-6.7.1-py3-none-any.whl` | Python wheel 包，推荐安装 |
| `rodski-6.7.1.tar.gz` | 源码包 |
| `SHA256SUMS` | 文件校验和 |

## v6.7.1 修复内容

修复 v6.7.0 wheel 打包配置错误导致 core/data/drivers 等关键模块未包含的问题。

## 校验

```bash
shasum -a 256 -c SHA256SUMS
```
