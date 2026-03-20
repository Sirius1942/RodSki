"""RodSki 安装配置"""
from setuptools import setup, find_packages

setup(
    name="rodski",
    version="1.0.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "rodski=cli_main:main",
        ],
    },
    python_requires=">=3.8",
    description="RodSki - 关键字驱动测试框架",
)
