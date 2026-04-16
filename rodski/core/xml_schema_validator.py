"""RodSki XML 与 XSD Schema 对照校验（公共模块）

用例执行时读取的 case / data / globalvalue / model 等 XML 均应对应
``rodski/schemas/*.xsd``。本模块提供统一校验入口；不符合约束时抛出
:class:`core.exceptions.XmlSchemaValidationError`。

依赖: ``pip install xmlschema``（已写入 requirements.txt）
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Union

try:
    import xmlschema
    from xmlschema.validators.exceptions import XMLSchemaValidationError as _XsdValidationError
except ImportError:  # pragma: no cover
    xmlschema = None  # type: ignore
    _XsdValidationError = Exception  # type: ignore

from .exceptions import XmlSchemaValidationError

# 文档类型 -> XSD 文件名（位于 rodski/schemas/）
SCHEMA_FILES: Dict[str, str] = {
    "case": "case.xsd",
    "data": "data.xsd",
    "globalvalue": "globalvalue.xsd",
    "model": "model.xsd",
    "result": "result.xsd",
}

_schema_cache: Dict[str, "xmlschema.XMLSchema"] = {}


def schemas_directory() -> Path:
    """返回 ``rodski/schemas`` 目录绝对路径。"""
    return Path(__file__).resolve().parent.parent / "schemas"


def _ensure_xmlschema() -> None:
    if xmlschema is None:
        raise ImportError(
            "缺少依赖 xmlschema，无法进行 XSD 校验。请执行: pip install xmlschema"
        )


def _get_xsd_path(kind: str) -> Path:
    if kind not in SCHEMA_FILES:
        raise ValueError(
            f"不支持的 document_kind: {kind!r}，可选: {', '.join(sorted(SCHEMA_FILES))}"
        )
    path = schemas_directory() / SCHEMA_FILES[kind]
    if not path.is_file():
        raise FileNotFoundError(f"XSD 文件不存在: {path}")
    return path


def _load_schema(kind: str) -> "xmlschema.XMLSchema":
    _ensure_xmlschema()
    if kind not in _schema_cache:
        xsd = _get_xsd_path(kind)
        _schema_cache[kind] = xmlschema.XMLSchema(str(xsd))
    return _schema_cache[kind]


def _format_validation_errors(schema: "xmlschema.XMLSchema", instance) -> List[str]:
    """收集详细校验错误信息（最多 40 条）。"""
    errors: List[str] = []
    try:
        for err in schema.iter_errors(instance):
            errors.append(str(err).strip())
            if len(errors) >= 40:
                break
    except Exception:
        pass
    return errors


class RodskiXmlValidator:
    """RodSki 测试 XML 的公共 XSD 校验类。

    在执行路径中读取 XML 时调用，例如::

        RodskiXmlValidator.validate_file(path, RodskiXmlValidator.KIND_CASE)

    校验失败抛出 :class:`core.exceptions.XmlSchemaValidationError`。
    """

    KIND_CASE = "case"
    KIND_DATA = "data"
    KIND_GLOBALVALUE = "globalvalue"
    KIND_MODEL = "model"
    KIND_RESULT = "result"

    @classmethod
    def validate_file(cls, xml_path: Union[str, Path], kind: str) -> None:
        """校验 XML 文件是否符合 ``kind`` 对应的 XSD。

        Args:
            xml_path: 实例 XML 文件路径
            kind: :attr:`KIND_CASE` / :attr:`KIND_DATA` / :attr:`KIND_GLOBALVALUE` /
                :attr:`KIND_MODEL` / :attr:`KIND_RESULT`

        Raises:
            FileNotFoundError: 文件不存在
            XmlSchemaValidationError: 不符合 Schema
        """
        _ensure_xmlschema()
        path = Path(xml_path).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"XML 文件不存在: {path}")

        schema = _load_schema(kind)
        xsd_path = _get_xsd_path(kind)

        try:
            schema.validate(str(path))
        except _XsdValidationError as e:
            errs = _format_validation_errors(schema, str(path))
            if not errs:
                errs = [str(e)]
            msg = (
                f"XML 不符合 Schema 约束 ({SCHEMA_FILES[kind]}): {path}\n"
                + "\n".join(f"  - {line}" for line in errs[:40])
            )
            raise XmlSchemaValidationError(
                msg,
                xml_path=str(path),
                document_kind=kind,
                schema_path=str(xsd_path),
                validation_errors=errs,
            ) from e

    @classmethod
    def validate_element_tree(
        cls,
        tree: ET.ElementTree,
        kind: str,
        source_path: Optional[Union[str, Path]] = None,
    ) -> None:
        """校验内存中的 ElementTree（写入 result 前使用）。"""
        _ensure_xmlschema()
        schema = _load_schema(kind)
        xsd_path = _get_xsd_path(kind)
        label = str(source_path) if source_path else "<in-memory>"

        try:
            schema.validate(tree)
        except _XsdValidationError as e:
            errs = _format_validation_errors(schema, tree)
            if not errs:
                errs = [str(e)]
            msg = (
                f"XML 不符合 Schema 约束 ({SCHEMA_FILES[kind]}): {label}\n"
                + "\n".join(f"  - {line}" for line in errs[:40])
            )
            raise XmlSchemaValidationError(
                msg,
                xml_path=label,
                document_kind=kind,
                schema_path=str(xsd_path),
                validation_errors=errs,
            ) from e

    @classmethod
    def validate_element(
        cls,
        root: ET.Element,
        kind: str,
        source_path: Optional[Union[str, Path]] = None,
    ) -> None:
        """校验根元素（封装 :meth:`validate_element_tree`）。"""
        cls.validate_element_tree(ET.ElementTree(root), kind, source_path=source_path)

    @classmethod
    def clear_schema_cache(cls) -> None:
        """单元测试或热重载 XSD 时可清空缓存。"""
        _schema_cache.clear()
