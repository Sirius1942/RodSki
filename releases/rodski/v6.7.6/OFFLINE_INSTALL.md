# RodSki v6.7.6 离线安装指南

## 适用场景

目标机器无法访问 PyPI（无网络或受限网络环境），需要完全离线安装 RodSki 及其依赖。

## 目录结构

```
releases/rodski/v6.7.6/
├── rodski-6.7.6-py3-none-any.whl   # RodSki 主包
├── rodski-6.7.6.tar.gz             # RodSki 源码包
├── deps/                           # 离线依赖包（预编译 wheel）
│   ├── xmlschema-4.2.0-py3-none-any.whl
│   ├── elementpath-5.0.4-py3-none-any.whl
│   ├── pyyaml-6.0.3-cp39-cp39-macosx_11_0_arm64.whl
│   ├── tqdm-4.67.3-py3-none-any.whl
│   ├── psutil-7.2.2-cp36-abi3-macosx_11_0_arm64.whl
│   ├── requests-2.32.5-py3-none-any.whl
│   ├── charset_normalizer-3.4.7-cp39-cp39-macosx_10_9_universal2.whl
│   ├── idna-3.15-py3-none-any.whl
│   ├── urllib3-2.6.3-py3-none-any.whl
│   ├── certifi-2026.4.22-py3-none-any.whl
│   ├── setuptools-82.0.1-py3-none-any.whl
│   ├── wheel-0.47.0-py3-none-any.whl
│   └── packaging-26.2-py3-none-any.whl
├── SHA256SUMS
├── README.md
└── OFFLINE_INSTALL.md              # 本文件
```

## 离线安装步骤

### 前提条件

- 目标机器已安装 Python 3.9+
- 目标机器已有 pip（Python 自带）

### 一键安装（推荐）

将整个 `v6.7.6/` 目录复制到目标机器，然后执行：

```bash
pip install --no-index --find-links=deps/ rodski-6.7.6-py3-none-any.whl
```

pip 会自动从 `deps/` 目录查找并安装所有依赖。

### 使用虚拟环境安装

```bash
python3 -m venv rodski-env
source rodski-env/bin/activate  # Linux/macOS
# rodski-env\Scripts\activate   # Windows

pip install --no-index --find-links=deps/ rodski-6.7.6-py3-none-any.whl
```

## 验证安装

```bash
python3 -c "import rodski; print(rodski.__version__)"
# 输出: 6.7.6
```

## 平台兼容性

当前 `deps/` 中的 wheel 适用于 **macOS arm64 + Python 3.9**。

如需为其他平台准备离线包，在有网络的同架构机器上执行：

```bash
# Linux x86_64
pip download --dest deps/ --python-version 39 xmlschema pyyaml tqdm psutil requests setuptools wheel

# Windows
pip download --dest deps/ --platform win_amd64 --python-version 39 --only-binary :all: xmlschema pyyaml tqdm psutil requests setuptools wheel
```

或使用通用方式（在目标机器上有网时预下载）：

```bash
pip download --dest deps/ xmlschema pyyaml tqdm psutil requests setuptools wheel
```

## 依赖清单

| 包名 | 版本 | 类型 | 说明 |
|------|------|------|------|
| xmlschema | 4.2.0 | pure-python | XML Schema 校验 |
| elementpath | 5.0.4 | pure-python | xmlschema 的依赖 |
| pyyaml | 6.0.3 | C 扩展 | YAML 解析 |
| tqdm | 4.67.3 | pure-python | 进度条 |
| psutil | 7.2.2 | C 扩展 | 系统进程管理 |
| requests | 2.32.5 | pure-python | HTTP 客户端 |
| charset_normalizer | 3.4.7 | C 扩展 | requests 的依赖 |
| idna | 3.15 | pure-python | requests 的依赖 |
| urllib3 | 2.6.3 | pure-python | requests 的依赖 |
| certifi | 2026.4.22 | pure-python | requests 的依赖 |
| setuptools | 82.0.1 | pure-python | 构建工具 |
| wheel | 0.47.0 | pure-python | wheel 格式支持 |
| packaging | 26.2 | pure-python | setuptools 的依赖 |

> 标记为 "C 扩展" 的包是平台相关的，需要匹配目标机器的 OS + CPU 架构 + Python 版本。
