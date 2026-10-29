"""执行能力推导（v11.11.0，CORE §7.9.3）。

全框架唯一的能力推导实现：``plan compile`` 清单、``rodski run`` 的浏览器 / 设备预检、
``device_scheduler`` 的队列预检都调用这里。

能力词表（粗分类）：

- ``web``：driver_type=web、接口模型、数据库模型、无 model 的 navigate / launch 网页地址
- ``android`` / ``ios``：对应 driver_type；driver_type=mobile 按 Mobile.Platform 解析；
  无 model 的 ``navigate app://android/...`` / ``app://ios/...``
- ``desktop``：driver_type=windows / macos / other；windows / macos 另生成 ``os:windows`` / ``os:macos`` 标签

用例能力 = 全部步骤（三阶段、scenario / if / loop 内部、business_call 引用的业务模型路径节点）能力的并集。
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

WEB = "web"
ANDROID = "android"
IOS = "ios"
DESKTOP = "desktop"
CAPABILITIES = (WEB, ANDROID, IOS, DESKTOP)
MOBILE_CAPABILITIES = frozenset({ANDROID, IOS})

_DESKTOP_OS_TAG = {"windows": "os:windows", "macos": "os:macos"}


class CapabilityError(ValueError):
    """能力无法推导（如 driver_type=mobile 但 Mobile.Platform 未配置）。"""


def model_driver_types(model_path: Optional[Path]) -> Dict[str, str]:
    """读 model.xml 的 name → driver_type 映射（未写 driver_type 的 ui 模型视为 web）。"""
    if not model_path or not Path(model_path).exists():
        return {}
    try:
        root = ET.parse(model_path).getroot()
    except ET.ParseError:
        return {}
    result: Dict[str, str] = {}
    for model in root.findall("model"):
        name = (model.get("name") or "").strip()
        if not name:
            continue
        model_type = (model.get("type") or "ui").strip()
        driver_type = (model.get("driver_type") or "").strip()
        if driver_type:
            result[name] = driver_type
        elif model_type in {"interface", "database"}:
            result[name] = model_type
        else:
            result[name] = "web"
    return result


def read_globalvalue(module_dir: Path, group_name: str, var_name: str) -> str:
    path = Path(module_dir) / "data" / "globalvalue.xml"
    if not path.exists():
        return ""
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return ""
    for group in root.findall("group"):
        if group.get("name") != group_name:
            continue
        for var in group.findall("var"):
            if var.get("name") == var_name:
                return (var.get("value") or "").strip()
    return ""


def resolve_mobile_platform(module_dir: Path, platform: Optional[str] = None) -> str:
    """driver_type=mobile 的目标平台：显式参数 → Mobile.Platform → DefaultValue.Platform。"""
    value = (platform or "").strip().lower()
    if not value:
        value = (read_globalvalue(module_dir, "Mobile", "Platform")
                 or read_globalvalue(module_dir, "DefaultValue", "Platform")).strip().lower()
    return value if value in MOBILE_CAPABILITIES else ""


def resolve_globalvalue_ref(module_dir: Path, value: str) -> str:
    """``GlobalValue.组.变量`` → 变量值；其他原样返回。"""
    if not isinstance(value, str) or not value.startswith("GlobalValue."):
        return value
    parts = value.split(".", 2)
    if len(parts) != 3:
        return value
    return read_globalvalue(module_dir, parts[1], parts[2]) or value


def navigate_target_capability(target: str) -> Optional[str]:
    lower = (target or "").strip().lower()
    if lower.startswith("app://android/"):
        return ANDROID
    if lower.startswith("app://ios/"):
        return IOS
    return WEB if lower else None


@dataclass
class BusinessIndex:
    """business/*.xml 中业务模型 id → (所在文件, flow id → 路径节点步骤)。"""

    models: Dict[str, Dict[str, object]] = field(default_factory=dict)

    @classmethod
    def load(cls, module_dir: Path) -> "BusinessIndex":
        index = cls()
        business_dir = Path(module_dir) / "business"
        if not business_dir.is_dir():
            return index
        for path in sorted(business_dir.rglob("*.xml")):
            try:
                root = ET.parse(path).getroot()
            except ET.ParseError:
                continue
            for bm in root.iter("business_model"):
                bm_id = (bm.get("id") or "").strip()
                if not bm_id:
                    continue
                nodes: Dict[str, List[ET.Element]] = {}
                for node in bm.iter("node"):
                    nodes[(node.get("id") or "").strip()] = list(node.iter("test_step"))
                flows: Dict[str, List[ET.Element]] = {}
                for flow in bm.iter("flow"):
                    steps: List[ET.Element] = []
                    for node_id in (flow.get("path") or "").split(">"):
                        steps.extend(nodes.get(node_id.strip(), []))
                    flows[(flow.get("id") or "").strip()] = steps
                all_steps = [s for steps in nodes.values() for s in steps]
                index.models[bm_id] = {"file": path, "flows": flows, "all": all_steps}
        return index

    def steps_for(self, ref: str, flow: str) -> Optional[List[ET.Element]]:
        model = self.models.get(ref)
        if model is None:
            return None
        flows = model["flows"]  # type: ignore[index]
        if flow and flow in flows:  # type: ignore[operator]
            return flows[flow]  # type: ignore[index]
        return model["all"]  # type: ignore[return-value]

    def file_of(self, ref: str) -> Optional[Path]:
        model = self.models.get(ref)
        return model["file"] if model else None  # type: ignore[return-value]


class CapabilityResolver:
    """按模块解析步骤 / 用例的能力需求。"""

    def __init__(self, module_dir: Path, platform: Optional[str] = None):
        self.module_dir = Path(module_dir)
        self.model_map = model_driver_types(self.module_dir / "model" / "model.xml")
        self.platform = platform
        self._mobile_platform: Optional[str] = None
        self._business: Optional[BusinessIndex] = None

    @property
    def business(self) -> BusinessIndex:
        if self._business is None:
            self._business = BusinessIndex.load(self.module_dir)
        return self._business

    def mobile_platform(self) -> str:
        if self._mobile_platform is None:
            self._mobile_platform = resolve_mobile_platform(self.module_dir, self.platform)
        return self._mobile_platform

    def driver_type_capability(self, driver_type: str, where: str = "") -> Optional[str]:
        dt = (driver_type or "").strip().lower()
        if dt in {"web", "interface", "database", ""}:
            return WEB
        if dt in {"android", "ios"}:
            return dt
        if dt == "mobile":
            platform = self.mobile_platform()
            if not platform:
                raise CapabilityError(
                    f"{where}使用 driver_type=\"mobile\" 的模型，但无法确定平台：请在 data/globalvalue.xml 的 "
                    f"Mobile 组配置 Platform（android / ios），即 Mobile.Platform"
                )
            return platform
        if dt in {"windows", "macos", "other"}:
            return DESKTOP
        return WEB

    def step_capability(self, step: ET.Element, where: str = "") -> Optional[str]:
        action = (step.get("action") or "").strip()
        model = (step.get("model") or "").strip()
        if action == "run":
            # run 的 model 是 fun/ 下的脚本工程名（或空=内置函数），不是模型，不贡献执行能力
            return None
        if model:
            return self.driver_type_capability(self.model_map.get(model, "web"), where)
        if action in {"navigate", "launch"}:
            target = resolve_globalvalue_ref(self.module_dir, (step.get("data") or "").strip())
            return navigate_target_capability(target)
        return None

    def desktop_os_tags(self, steps: Iterable[ET.Element]) -> Set[str]:
        tags: Set[str] = set()
        for step in steps:
            model = (step.get("model") or "").strip()
            tag = _DESKTOP_OS_TAG.get(self.model_map.get(model, "").lower()) if model else None
            if tag:
                tags.add(tag)
        return tags

    def case_steps(self, case_elem: ET.Element, business_refs: Optional[Set[str]] = None) -> List[ET.Element]:
        """用例全部步骤：三阶段（含 scenario / if / loop 内部）+ business_call 引用的业务模型步骤。"""
        steps: List[ET.Element] = list(case_elem.iter("test_step"))
        for call in case_elem.iter("business_call"):
            ref = (call.get("ref") or "").strip()
            flow = (call.get("flow") or "").strip()
            if business_refs is not None and ref:
                business_refs.add(ref)
            biz_steps = self.business.steps_for(ref, flow)
            if biz_steps is None:
                raise CapabilityError(
                    f"用例 {case_elem.get('id', '')} 的 business_call 引用了不存在的业务模型 {ref!r}"
                )
            steps.extend(biz_steps)
        return steps

    def case_requires(self, case_elem: ET.Element, case_file: str = "",
                      business_refs: Optional[Set[str]] = None) -> Dict[str, object]:
        """返回 {"requires": 有序能力列表, "os_tags": set, "steps": test_step 数}。"""
        where = f"用例 {case_file}::{case_elem.get('id', '')} "
        steps = self.case_steps(case_elem, business_refs)
        caps: Set[str] = set()
        for step in steps:
            cap = self.step_capability(step, where)
            if cap:
                caps.add(cap)
        return {
            "requires": sorted(caps),
            "os_tags": self.desktop_os_tags(steps),
            "steps": sum(1 for _ in case_elem.iter("test_step")),
        }

    def driver_types_of_steps(self, steps: Iterable[ET.Element]) -> Set[str]:
        """步骤用到的原始 driver_type 集合（兼容旧预检接口）。"""
        result: Set[str] = set()
        for step in steps:
            model = (step.get("model") or "").strip()
            if model:
                result.add(self.model_map.get(model, "web"))
        return result
