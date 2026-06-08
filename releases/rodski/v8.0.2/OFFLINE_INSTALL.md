# 离线安装指南

## 一键离线安装

将整个目录复制到目标机器，执行：

```bash
pip install --no-index --find-links=deps/ rodski-8.0.2-py3-none-any.whl
```

## 使用虚拟环境

```bash
python3 -m venv rodski-env
source rodski-env/bin/activate
pip install --no-index --find-links=deps/ rodski-8.0.2-py3-none-any.whl
```

## 验证

```bash
python3 -c "import rodski; print(rodski.__version__)"
```

## 平台说明

deps/ 中含平台相关的 C 扩展包（psutil、pyyaml）。
当前包适用于本机平台。如需其他平台，在目标同架构机器上执行：

```bash
pip download --dest deps/ xmlschema pyyaml tqdm psutil requests setuptools wheel
```
