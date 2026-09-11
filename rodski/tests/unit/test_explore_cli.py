"""explore-step CLI 引擎装配测试

回归背景（v11.1.x）：`rodski explore-step` 发布后一直不可用——`_init_keyword_engine`
做的是 `ConfigManager.load(str(module_path))`（把实例方法当类方法调用）、给
`PlaywrightDriver` 传了不存在的 `browser_type=` / `record_video=`、给 `KeywordEngine`
传了不存在的 `config=`，且没有装配 model_parser / data_manager / data_resolver。
结果每次都在第一行抛 `'str' object has no attribute 'config_path'`，返回
`{"success": false}`。

这些用例锁定装配契约：没有 model_parser + data_manager + data_resolver，
`type ModelName DataID` 这类批量关键字会被当成单字段模式而报参数错误。
"""
from pathlib import Path

import pytest

try:
    from rodski_cli.explore import _init_keyword_engine
except ImportError:
    from rodski.explore import _init_keyword_engine  # type: ignore


MODEL_XML = """<?xml version="1.0" encoding="UTF-8"?>
<models>
  <model name="LoginForm" type="ui" servicename="">
    <element name="username" type="input">
      <location type="id">loginUsername</location>
    </element>
  </model>
</models>
"""

GLOBALVALUE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<globalvalue>
  <group name="DefaultValue">
    <var name="WaitTime" value="0"/>
  </group>
</globalvalue>
"""


@pytest.fixture
def module_dir(tmp_path: Path) -> Path:
    module = tmp_path / "demo_module"
    (module / "model").mkdir(parents=True)
    (module / "data").mkdir(parents=True)
    (module / "model" / "model.xml").write_text(MODEL_XML, encoding="utf-8")
    (module / "data" / "globalvalue.xml").write_text(GLOBALVALUE_XML, encoding="utf-8")
    return module


def test_init_keyword_engine_wires_parsers_and_resolver(module_dir):
    """引擎必须装配齐 model_parser / data_manager / data_resolver。

    缺 data_resolver 时批量关键字的字段值不会解析 ${Return[-1]} / 内置函数；
    缺 model_parser / data_manager 时 `type Model DataID` 直接退化为单字段模式。
    """
    engine = _init_keyword_engine(module_dir)

    assert engine.model_parser is not None
    assert engine.data_manager is not None
    assert engine.data_resolver is not None
    assert engine.data_resolver.return_provider == engine.get_return
    # 模型确实从模块目录加载进来了（而不是空壳 parser）
    assert engine.model_parser.get_model("LoginForm")


def test_init_keyword_engine_without_cdp_does_not_attach(module_dir):
    """不带 --cdp 时驱动为非附加模式（首个关键字触发懒启动）。"""
    engine = _init_keyword_engine(module_dir)

    assert engine.driver.attached is False
    assert engine.driver.browser is None, "不应在装配阶段就启动浏览器"


def test_init_keyword_engine_normalizes_cdp_endpoint(module_dir):
    """--cdp :9333 归一为 http://127.0.0.1:9333 并进入附加模式。

    端点不归一的话 connect_over_cdp 会直接失败（`Unexpected status 400 when
    connecting to :9333/json/version/.`）——实测踩过。
    """
    engine = _init_keyword_engine(module_dir, cdp_endpoint=":9333")

    assert engine.driver.attached is True
    assert engine.driver._cdp_endpoint == "http://127.0.0.1:9333"
    assert engine.driver.browser is None, "附加是懒加载的，装配阶段不连浏览器"


def test_init_keyword_engine_keeps_explicit_cdp_url(module_dir):
    engine = _init_keyword_engine(module_dir, cdp_endpoint="http://127.0.0.1:9333")

    assert engine.driver._cdp_endpoint == "http://127.0.0.1:9333"
