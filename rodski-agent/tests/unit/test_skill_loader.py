"""Unit tests for design/skill_loader.py."""

import textwrap
from pathlib import Path

import pytest

from rodski_agent.design.skill_loader import load_skill_docs

FULL_MD = textwrap.dedent("""\
    # 登录模块 业务文档

    ## 业务术语
    - **工作台**：登录成功后的主页面，URL 包含 /dashboard
    - **账号**：用户登录凭证

    ## 操作流程

    ### 登录
    打开系统首页，输入账号密码，点击"登录"按钮。

    ### 退出
    点击右上角头像，选择退出登录。

    ## 测试约束
    - 每个用例执行完必须退出登录
    - 不允许使用管理员账号
""")


def _write(tmp_path: Path, name: str, content: str) -> None:
    (tmp_path / name).write_text(content, encoding="utf-8")


def test_full_parse(tmp_path):
    _write(tmp_path, "login.md", FULL_MD)
    ctx = load_skill_docs(str(tmp_path))

    assert ctx.terms == {
        "工作台": "登录成功后的主页面，URL 包含 /dashboard",
        "账号": "用户登录凭证",
    }
    assert len(ctx.flows) == 2
    assert ctx.flows[0].name == "登录"
    assert any("打开系统首页" in s for s in ctx.flows[0].steps)
    assert ctx.flows[1].name == "退出"
    assert ctx.constraints == ["每个用例执行完必须退出登录", "不允许使用管理员账号"]


def test_multi_file_merge(tmp_path):
    _write(tmp_path, "a.md", textwrap.dedent("""\
        # A

        ## 业务术语
        - **术语A**：描述A

        ## 测试约束
        - 约束A
    """))
    _write(tmp_path, "b.md", textwrap.dedent("""\
        # B

        ## 业务术语
        - **术语B**：描述B

        ## 操作流程

        ### 流程B
        步骤一。步骤二。
    """))
    ctx = load_skill_docs(str(tmp_path))
    assert "术语A" in ctx.terms
    assert "术语B" in ctx.terms
    assert len(ctx.flows) == 1
    assert ctx.flows[0].name == "流程B"
    assert ctx.constraints == ["约束A"]


def test_missing_sections_graceful(tmp_path):
    _write(tmp_path, "empty.md", "# 模块\n\n只有标题，没有标准区块。\n")
    ctx = load_skill_docs(str(tmp_path))
    assert ctx.terms == {}
    assert ctx.flows == []
    assert ctx.constraints == []


def test_empty_dir(tmp_path):
    ctx = load_skill_docs(str(tmp_path))
    assert ctx.terms == {}
    assert ctx.flows == []
    assert ctx.constraints == []
