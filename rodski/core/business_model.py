"""Independent parser, validator and executor for scenario-based business models.

The graph executor is reusable inside a host Case. A caller selects a flow as
an expectation; graph branches are selected only by conditions on actual values
returned from the injected RodSki step runner.
"""
from __future__ import annotations

import ast
import operator
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

from .sqlite_data_source import SQLiteDataSource
from .xml_schema_validator import RodskiXmlValidator


class BusinessModelError(ValueError):
    """Base error for business model parsing, validation, data and execution."""


class BusinessModelParseError(BusinessModelError):
    pass


class BusinessModelValidationError(BusinessModelError):
    pass


class BusinessModelExecutionError(BusinessModelError):
    pass


class BusinessModelAssertionError(BusinessModelExecutionError):
    pass


@dataclass(frozen=True)
class BusinessStep:
    action: str
    model: str = ""
    data: str = ""
    attributes: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class BusinessNode:
    id: str
    title: str = ""
    steps: Tuple[BusinessStep, ...] = ()


@dataclass(frozen=True)
class BusinessEdge:
    source: str
    target: str
    condition: Optional[str] = None
    label: str = ""


@dataclass(frozen=True)
class BusinessFlow:
    id: str
    path: Tuple[str, ...]
    type: str = ""


@dataclass(frozen=True)
class BusinessModel:
    id: str
    name: str
    version: str
    nodes: Mapping[str, BusinessNode]
    edges: Tuple[BusinessEdge, ...]
    flows: Mapping[str, BusinessFlow]

    @property
    def input_table(self) -> str:
        return self.id

    @property
    def verify_table(self) -> str:
        return f"{self.id}_verify"


class BusinessModelParser:
    """Parse the v0.1 ``business_models`` XML shape."""

    def parse_directory(self, business_dir: Union[str, Path]) -> Dict[str, BusinessModel]:
        directory = Path(business_dir)
        models: Dict[str, BusinessModel] = {}
        for path in sorted(directory.glob("*.xml")):
            for model_id, model in self.parse_file(path).items():
                if model_id in models:
                    raise BusinessModelParseError(f"Duplicate business_model id across files: {model_id}")
                models[model_id] = model
        if not models:
            raise BusinessModelParseError(f"No business model XML found in {directory}")
        return models

    def parse_file(self, xml_path: Union[str, Path]) -> Dict[str, BusinessModel]:
        path = Path(xml_path)
        try:
            RodskiXmlValidator.validate_file(path, RodskiXmlValidator.KIND_BUSINESS)
            root = ET.parse(path).getroot()
        except Exception as exc:
            raise BusinessModelParseError(f"Cannot parse/validate business model XML {path}: {exc}") from exc
        return self.parse_element(root)

    def parse_string(self, xml_text: str) -> Dict[str, BusinessModel]:
        try:
            root = ET.fromstring(xml_text)
            RodskiXmlValidator.validate_element(root, RodskiXmlValidator.KIND_BUSINESS)
        except Exception as exc:
            raise BusinessModelParseError(f"Cannot parse/validate business model XML: {exc}") from exc
        return self.parse_element(root)

    def parse_element(self, root: ET.Element) -> Dict[str, BusinessModel]:
        if root.tag != "business_models":
            raise BusinessModelParseError("Root element must be <business_models>")
        models: Dict[str, BusinessModel] = {}
        for element in root.findall("business_model"):
            model_id = (element.get("id") or "").strip()
            if not model_id:
                raise BusinessModelParseError("<business_model> requires id")
            if model_id in models:
                raise BusinessModelParseError(f"Duplicate business_model id: {model_id}")
            nodes: Dict[str, BusinessNode] = {}
            nodes_element = element.find("nodes")
            if nodes_element is not None:
                for node_element in nodes_element.findall("node"):
                    node_id = (node_element.get("id") or "").strip()
                    if not node_id:
                        raise BusinessModelParseError(f"Node in {model_id} requires id")
                    if node_id in nodes:
                        raise BusinessModelParseError(f"Duplicate node id {node_id!r} in {model_id}")
                    steps_element = node_element.find("steps")
                    steps = tuple(self._parse_step(step) for step in steps_element.findall("test_step")) if steps_element is not None else ()
                    nodes[node_id] = BusinessNode(node_id, node_element.get("title", ""), steps)
            edges: List[BusinessEdge] = []
            edges_element = element.find("edges")
            if edges_element is not None:
                for edge_element in edges_element.findall("edge"):
                    edges.append(BusinessEdge(
                        (edge_element.get("from") or "").strip(),
                        (edge_element.get("to") or "").strip(),
                        self._normalize_condition(edge_element.get("condition")),
                        edge_element.get("label", ""),
                    ))
            flows: Dict[str, BusinessFlow] = {}
            flows_element = element.find("flows")
            if flows_element is not None:
                for flow_element in flows_element.findall("flow"):
                    flow_id = (flow_element.get("id") or "").strip()
                    path = tuple(part.strip() for part in (flow_element.get("path") or "").split(">") if part.strip())
                    if not flow_id:
                        raise BusinessModelParseError(f"Flow in {model_id} requires id")
                    if flow_id in flows:
                        raise BusinessModelParseError(f"Duplicate flow id {flow_id} in {model_id}")
                    flows[flow_id] = BusinessFlow(flow_id, path, flow_element.get("type", ""))
            models[model_id] = BusinessModel(
                model_id, element.get("name", model_id), element.get("version", ""),
                nodes, tuple(edges), flows,
            )
        if not models:
            raise BusinessModelParseError("No <business_model> found")
        return models

    @staticmethod
    def _parse_step(element: ET.Element) -> BusinessStep:
        attrs = {key: value for key, value in element.attrib.items()}
        return BusinessStep(
            (element.get("action") or "").strip(),
            (element.get("model") or "").strip(),
            (element.get("data") or "").strip(),
            attrs,
        )

    @staticmethod
    def _normalize_condition(condition: Optional[str]) -> Optional[str]:
        if not condition:
            return None
        # XML sample notation ${Business.Actual.foo} is normalized to a safe
        # Python name chain Business.Actual.foo before AST evaluation.
        return re.sub(r"\$\{([^}]+)\}", r"\1", condition).strip()


class BusinessModelValidator:
    """Validate graph references, deterministic branching and declared flows."""

    @classmethod
    def validate(cls, model: BusinessModel) -> None:
        if not model.nodes:
            raise BusinessModelValidationError(f"{model.id}: no nodes defined")
        if not model.flows:
            raise BusinessModelValidationError(f"{model.id}: no flows defined")
        if len(set(model.nodes)) != len(model.nodes):
            raise BusinessModelValidationError(f"{model.id}: duplicate node id")
        outgoing: Dict[str, List[BusinessEdge]] = {node_id: [] for node_id in model.nodes}
        incoming: Dict[str, List[BusinessEdge]] = {node_id: [] for node_id in model.nodes}
        for edge in model.edges:
            if edge.source not in model.nodes or edge.target not in model.nodes:
                raise BusinessModelValidationError(
                    f"{model.id}: edge {edge.source!r}->{edge.target!r} references unknown node"
                )
            outgoing[edge.source].append(edge)
            incoming[edge.target].append(edge)
            if edge.condition:
                _SafeCondition.validate(edge.condition)
        starts = [node_id for node_id, edges in incoming.items() if not edges]
        if len(starts) != 1:
            raise BusinessModelValidationError(f"{model.id}: graph must have exactly one start node, got {starts}")
        for node_id, edges in outgoing.items():
            unconditional = [edge for edge in edges if not edge.condition]
            if len(unconditional) > 1 or (unconditional and len(edges) > 1):
                raise BusinessModelValidationError(
                    f"{model.id}: node {node_id} has ambiguous unconditional outgoing edge"
                )
            if len(edges) > 1 and any(not edge.condition for edge in edges):
                raise BusinessModelValidationError(f"{model.id}: every branch from {node_id} needs a condition")
        # v0.1 graphs are finite DAGs.  Reject cycles and unreachable nodes at
        # validation time instead of relying on the runtime max_nodes guard.
        reachable = set()
        stack = [starts[0]]
        while stack:
            node_id = stack.pop()
            if node_id in reachable:
                continue
            reachable.add(node_id)
            stack.extend(edge.target for edge in outgoing[node_id])
        unreachable = sorted(set(model.nodes) - reachable)
        if unreachable:
            raise BusinessModelValidationError(f"{model.id}: unreachable nodes {unreachable}")

        visiting = set()
        visited = set()

        def visit(node_id: str) -> None:
            if node_id in visiting:
                raise BusinessModelValidationError(f"{model.id}: graph contains a cycle at {node_id!r}")
            if node_id in visited:
                return
            visiting.add(node_id)
            for edge in outgoing[node_id]:
                visit(edge.target)
            visiting.remove(node_id)
            visited.add(node_id)

        visit(starts[0])
        allowed_types = {"basic", "alternative", "exception", "boundary"}
        if not any(flow.type == "basic" for flow in model.flows.values()):
            raise BusinessModelValidationError(f"{model.id}: at least one basic flow is required")
        for flow in model.flows.values():
            if flow.type not in allowed_types:
                raise BusinessModelValidationError(
                    f"{model.id}.{flow.id}: unsupported flow type {flow.type!r}; "
                    f"expected one of {sorted(allowed_types)}"
                )
            if len(flow.path) < 2:
                raise BusinessModelValidationError(f"{model.id}.{flow.id}: flow path must contain at least two nodes")
            if len(set(flow.path)) != len(flow.path):
                raise BusinessModelValidationError(f"{model.id}.{flow.id}: flow path must not repeat nodes")
            unknown = [node_id for node_id in flow.path if node_id not in model.nodes]
            if unknown:
                raise BusinessModelValidationError(f"{model.id}.{flow.id}: unknown nodes {unknown}")
            if flow.path[0] != starts[0]:
                raise BusinessModelValidationError(f"{model.id}.{flow.id}: path must begin at {starts[0]}")
            for source, target in zip(flow.path, flow.path[1:]):
                matching = [edge for edge in outgoing[source] if edge.target == target]
                if not matching:
                    raise BusinessModelValidationError(f"{model.id}.{flow.id}: {source}->{target} is not an edge")
            if outgoing[flow.path[-1]]:
                raise BusinessModelValidationError(
                    f"{model.id}.{flow.id}: flow path must end at a terminal node {flow.path[-1]!r}"
                )

    @classmethod
    def graph_dict(cls, model: BusinessModel) -> Dict[str, Any]:
        """Return a JSON-serializable static graph projection."""
        cls.validate(model)
        return {
            "id": model.id,
            "name": model.name,
            "version": model.version,
            "input_table": model.input_table,
            "verify_table": model.verify_table,
            "nodes": [
                {"id": node.id, "title": node.title, "steps": [
                    {"action": step.action, "model": step.model, "data": step.data}
                    for step in node.steps
                ]}
                for node in model.nodes.values()
            ],
            "edges": [
                {"from": edge.source, "to": edge.target,
                 "condition": edge.condition, "label": edge.label}
                for edge in model.edges
            ],
            "flows": [
                {"id": flow.id, "type": flow.type, "path": list(flow.path)}
                for flow in model.flows.values()
            ],
        }

    @classmethod
    def mermaid(cls, model: BusinessModel, flow_id: Optional[str] = None) -> str:
        """Render the graph or a selected flow as Mermaid flowchart text."""
        cls.validate(model)
        selected = model.flows.get(flow_id) if flow_id else None
        if flow_id and selected is None:
            raise BusinessModelValidationError(f"{model.id}: unknown flow {flow_id!r}")
        nodes = selected.path if selected else tuple(model.nodes)
        node_set = set(nodes)
        lines = ["flowchart TD"]
        for node_id in nodes:
            node = model.nodes[node_id]
            title = node.title or node_id
            safe = title.replace('"', "'")
            lines.append(f'    {node_id}["{node_id}: {safe}"]')
        for edge in model.edges:
            if edge.source not in node_set or edge.target not in node_set:
                continue
            if selected and not any(a == edge.source and b == edge.target for a, b in zip(selected.path, selected.path[1:])):
                continue
            label = edge.label or edge.condition
            suffix = f'|{label}|' if label else ""
            lines.append(f"    {edge.source} -->{suffix} {edge.target}")
        return "\n".join(lines)


class _SafeCondition:
    """Small, fail-closed expression evaluator for graph edge conditions."""
    OPS = {ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt,
           ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge,
           ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b}

    @classmethod
    def validate(cls, expression: str) -> None:
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as exc:
            raise BusinessModelValidationError(f"Invalid edge condition {expression!r}: {exc}") from exc
        for node in ast.walk(tree):
            if isinstance(node, (ast.Expression, ast.Load, ast.Constant, ast.Name, ast.Attribute,
                                 ast.Compare, ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not,
                                 ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn)):
                continue
            raise BusinessModelValidationError(
                f"Unsupported syntax {type(node).__name__} in edge condition {expression!r}"
            )

    @classmethod
    def evaluate(cls, expression: str, variables: Mapping[str, Any]) -> bool:
        cls.validate(expression)
        return bool(cls._eval(ast.parse(expression, mode="eval").body, variables))

    @classmethod
    def _eval(cls, node: ast.AST, variables: Mapping[str, Any]) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return variables.get(node.id)
        if isinstance(node, ast.Attribute):
            value = cls._eval(node.value, variables)
            return value.get(node.attr) if isinstance(value, Mapping) else getattr(value, node.attr, None)
        if isinstance(node, ast.BoolOp):
            values = [bool(cls._eval(value, variables)) for value in node.values]
            return all(values) if isinstance(node.op, ast.And) else any(values)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not cls._eval(node.operand, variables)
        if isinstance(node, ast.Compare):
            left = cls._eval(node.left, variables)
            for op, comparator in zip(node.ops, node.comparators):
                right = cls._eval(comparator, variables)
                fn = cls.OPS[type(op)]
                try:
                    passed = fn(left, right)
                except (TypeError, ValueError):
                    return False
                if not passed:
                    return False
                left = right
            return True
        raise BusinessModelValidationError(f"Unsupported condition expression node {type(node).__name__}")


StepRunner = Callable[[BusinessStep, Mapping[str, Any]], Optional[Mapping[str, Any]]]


@dataclass
class BusinessModelResult:
    model_id: str
    flow_id: str
    input_data_id: str
    expect_data_id: str
    passed: bool
    actual_path: Tuple[str, ...]
    expected_path: Tuple[str, ...]
    actual: Dict[str, Any]
    expected: Dict[str, Any]
    node_results: List[Dict[str, Any]]
    assertion_errors: List[str] = field(default_factory=list)


class BusinessModelExecutor:
    """Execute actual graph paths with injectable action runner and SQLite data."""

    def __init__(
        self,
        model: BusinessModel,
        data_tables: Optional[Mapping[str, Mapping[str, Mapping[str, Any]]]] = None,
        *,
        data_source: Optional[SQLiteDataSource] = None,
        step_runner: Optional[StepRunner] = None,
        max_nodes: int = 100,
    ):
        BusinessModelValidator.validate(model)
        if data_tables is None:
            if data_source is None:
                raise ValueError("Provide data_tables or data_source")
            data_tables = data_source.load_tables()
        self.model = model
        self.data_tables = data_tables
        self.step_runner = step_runner or self._no_op_runner
        self.max_nodes = max_nodes
        self._validate_data_table_kinds(data_source)

    @staticmethod
    def _no_op_runner(step: BusinessStep, context: Mapping[str, Any]) -> Mapping[str, Any]:
        return {}

    def _validate_data_table_kinds(self, data_source: Optional[SQLiteDataSource]) -> None:
        if data_source is None:
            return
        conn = data_source._connect()
        rows = dict(conn.execute(
            "SELECT table_name, table_kind FROM rs_datatable WHERE table_name IN (?, ?)",
            (self.model.input_table, self.model.verify_table),
        ).fetchall())
        if rows.get(self.model.input_table) != "data":
            raise BusinessModelExecutionError(f"Missing ordinary data table {self.model.input_table!r}")
        if rows.get(self.model.verify_table) != "verify":
            raise BusinessModelExecutionError(f"Missing ordinary verify table {self.model.verify_table!r}")

    def execute(self, flow_id: str, input_data_id: str, expect_data_id: str) -> BusinessModelResult:
        if not flow_id or not input_data_id or not expect_data_id:
            raise BusinessModelExecutionError("flow_id, input_data_id and expect_data_id are required")
        if flow_id not in self.model.flows:
            raise BusinessModelExecutionError(f"Unknown flow {flow_id!r} in model {self.model.id}")
        inputs = self._get_row(self.model.input_table, input_data_id)
        expected = self._get_row(self.model.verify_table, expect_data_id)
        target_flow = self.model.flows[flow_id]
        context: Dict[str, Any] = {
            "Business": {"InputDataID": input_data_id, "ExpectDataID": expect_data_id, "Actual": {}},
            "Input": dict(inputs), "Actual": {}, "Expected": dict(expected),
        }
        current = self._start_node()
        actual_path: List[str] = []
        node_results: List[Dict[str, Any]] = []
        for _ in range(self.max_nodes):
            actual_path.append(current)
            node = self.model.nodes[current]
            step_outputs: List[Dict[str, Any]] = []
            for step in node.steps:
                output = self.step_runner(step, context)
                if output:
                    actual = context["Business"]["Actual"]
                    actual.update(output)
                    context["Actual"].update(output)
                    step_outputs.append(dict(output))
            node_results.append({"node_id": current, "steps": step_outputs})
            edges = [edge for edge in self.model.edges if edge.source == current]
            if not edges:
                break
            candidates = [edge for edge in edges if edge.condition is None or
                          _SafeCondition.evaluate(edge.condition, context)]
            if len(candidates) != 1:
                raise BusinessModelExecutionError(
                    f"At node {current!r}, expected exactly one matching edge, got {len(candidates)}"
                )
            current = candidates[0].target
        else:
            raise BusinessModelExecutionError(f"Graph exceeded max_nodes={self.max_nodes}; cycle suspected")

        actual_tuple = tuple(actual_path)
        expected_tuple = target_flow.path
        assertion_errors: List[str] = []
        if actual_tuple != expected_tuple:
            assertion_errors.append(f"Path mismatch: expected {expected_tuple}, got {actual_tuple}")
        for key, expected_value in expected.items():
            # ``expected_path`` is a standard Verify-table assertion column,
            # not a response field.  Keep it in the ordinary table so the
            # selected scenario and its expected path remain data-driven.
            if key == "expected_path":
                actual_value = ">".join(actual_tuple)
            else:
                actual_value = context["Business"]["Actual"].get(key)
            if str(actual_value) != str(expected_value):
                assertion_errors.append(f"Field {key!r}: expected {expected_value!r}, got {actual_value!r}")
        return BusinessModelResult(
            self.model.id, flow_id, input_data_id, expect_data_id,
            not assertion_errors, actual_tuple, expected_tuple,
            dict(context["Business"]["Actual"]), dict(expected), node_results, assertion_errors,
        )

    def execute_or_raise(self, flow_id: str, input_data_id: str, expect_data_id: str) -> BusinessModelResult:
        result = self.execute(flow_id, input_data_id, expect_data_id)
        if not result.passed:
            raise BusinessModelAssertionError("; ".join(result.assertion_errors))
        return result

    def _get_row(self, table_name: str, data_id: str) -> Dict[str, Any]:
        table = self.data_tables.get(table_name)
        if table is None:
            raise BusinessModelExecutionError(f"Missing data table {table_name!r}")
        row = table.get(data_id)
        if row is None:
            raise BusinessModelExecutionError(f"DataID {data_id!r} not found in {table_name!r}")
        return dict(row)

    def _start_node(self) -> str:
        incoming = {edge.target for edge in self.model.edges}
        starts = [node_id for node_id in self.model.nodes if node_id not in incoming]
        if len(starts) != 1:
            raise BusinessModelExecutionError(f"Expected one graph start node, got {starts}")
        return starts[0]
