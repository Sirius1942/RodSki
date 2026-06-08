"""LoadCompiler — 将 SharedLoadContext + plan dict 编译为 Locust locustfile.py。

产物写入 perf/{plan_id}.py + perf/{plan_id}.py.meta
"""
from __future__ import annotations

import ast
import hashlib
import json
import logging
import os
import re
import textwrap
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .context import SharedLoadContext

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 占位符/正则
# ---------------------------------------------------------------------------

_RE_GLOBALVALUE = re.compile(r'\$\{GlobalValue\.([^}]+)\}')
_RE_RETURN       = re.compile(r'\$\{Return\[(-?\d+)\](?:\.([^}]+))?\}')
_RE_RANDOM       = re.compile(r'\$\{(random\([^}]*\))\}')
_RE_DATE         = re.compile(r'\$\{(date\([^}]*\))\}')


def _safe_identifier(text: str) -> str:
    """将字符串转换为合法 Python 标识符片段（去掉非法字符）。"""
    return re.sub(r'[^a-zA-Z0-9_]', '_', text)


class LoadCompiler:
    """将 SharedLoadContext + plan dict 编译为可独立运行的 Locust locustfile.py。"""

    def __init__(
        self,
        shared_ctx: "SharedLoadContext",
        plan: dict,
        perf_dir: Path,
    ):
        self.shared_ctx = shared_ctx
        self.plan = plan
        self.perf_dir = Path(perf_dir)
        self._plan_id: str = plan.get("plan_id") or plan.get("id", "unnamed")
        # 收集编译期生成的模块级常量 {const_name: value_repr}
        self._constants: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compile(self) -> Path:
        """强制重编译，生成 perf/{plan_id}.py 并写入 .meta。"""
        self.perf_dir.mkdir(parents=True, exist_ok=True)
        self._constants = {}

        code = "\n".join([
            self._render_header(),
            self._render_imports(),
            "",
            "# --- module-level constants (inlined literals) ---",
            self._render_constants(),
            "",
            self._render_user_class(),
        ])

        # 语法自检
        try:
            ast.parse(code)
        except SyntaxError as exc:
            raise SyntaxError(
                f"LoadCompiler 生成的 locustfile 语法错误: {exc}"
            ) from exc

        out_path = self.perf_dir / f"{self._plan_id}.py"
        out_path.write_text(code, encoding="utf-8")

        meta = {
            "plan_hash": "",   # compile() 不提供 hash，由 compile_if_needed() 填写
            "compiled_at": datetime.utcnow().isoformat(),
            "source": "auto",
        }
        meta_path = self.perf_dir / f"{self._plan_id}.py.meta"
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        return out_path

    def compile_if_needed(
        self,
        plan_path: Optional[Path] = None,
        case_paths: Optional[List[Path]] = None,
        model_path: Optional[Path] = None,
        data_path: Optional[Path] = None,
    ) -> Path:
        """缓存策略：hash 命中则复用产物；source=manual 时打印 WARN 并跳过覆盖。"""
        self.perf_dir.mkdir(parents=True, exist_ok=True)
        out_path  = self.perf_dir / f"{self._plan_id}.py"
        meta_path = self.perf_dir / f"{self._plan_id}.py.meta"

        current_hash = self._compute_hash(plan_path, case_paths, model_path, data_path)

        if meta_path.exists() and out_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                meta = {}

            if meta.get("source") == "manual":
                warnings.warn(
                    f"[LoadCompiler] {out_path.name} source=manual，跳过自动覆盖。",
                    UserWarning,
                    stacklevel=2,
                )
                return out_path

            if meta.get("plan_hash") == current_hash:
                # 缓存命中
                return out_path

        # 需要重新编译
        self._constants = {}
        code = "\n".join([
            self._render_header(),
            self._render_imports(),
            "",
            "# --- module-level constants (inlined literals) ---",
            self._render_constants(),
            "",
            self._render_user_class(),
        ])

        try:
            ast.parse(code)
        except SyntaxError as exc:
            raise SyntaxError(
                f"LoadCompiler 生成的 locustfile 语法错误: {exc}"
            ) from exc

        out_path.write_text(code, encoding="utf-8")

        meta = {
            "plan_hash": current_hash,
            "compiled_at": datetime.utcnow().isoformat(),
            "source": "auto",
        }
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        return out_path

    # ------------------------------------------------------------------
    # Render helpers
    # ------------------------------------------------------------------

    def _render_header(self) -> str:
        profile = self.plan.get("load_profile", {})
        host = profile.get("host", "http://localhost")
        concurrency = profile.get("concurrency", 1)
        duration    = profile.get("duration_seconds", 30)
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        return textwrap.dedent(f"""\
            # ============================================================
            # RodSki LoadCompiler — plan_id: {self._plan_id}
            # Generated: {now}
            # Run: locust -f <this_file> --host {host} --users {concurrency} --run-time {duration}s
            # ============================================================
        """).rstrip()

    def _render_imports(self) -> str:
        return textwrap.dedent("""\
            import random as _random
            from datetime import datetime as _datetime
            from locust import FastHttpUser, task, between
        """).rstrip()

    def _render_constants(self) -> str:
        """先触发所有 task 方法的常量收集，再输出模块级常量块。"""
        # 预先执行 _render_task_method 以填充 self._constants
        plan_cases = [c for c in self.plan.get("cases", []) if c.get("execute") == "是"]
        for case_cfg in plan_cases:
            case_id = case_cfg["id"]
            weight  = int(case_cfg.get("weight", 1))
            self._render_task_method(case_id, weight)

        if not self._constants:
            return "# (no constants)"
        lines = []
        for const_name, value_repr in self._constants.items():
            lines.append(f"{const_name} = {value_repr}")
        return "\n".join(lines)

    def _render_user_class(self) -> str:
        profile   = self.plan.get("load_profile", {})
        host      = profile.get("host") or self._resolve_host()
        think_min = int(profile.get("think_time_ms", {}).get("min", 500)) / 1000
        think_max = int(profile.get("think_time_ms", {}).get("max", 1500)) / 1000
        if think_max <= think_min:
            think_max = think_min + 0.001

        plan_cases = [c for c in self.plan.get("cases", []) if c.get("execute") == "是"]

        task_blocks = []
        for case_cfg in plan_cases:
            case_id = case_cfg["id"]
            weight  = int(case_cfg.get("weight", 1))
            task_blocks.append(self._render_task_method(case_id, weight))

        tasks_code = "\n\n".join(task_blocks) if task_blocks else "    pass"

        return textwrap.dedent(f"""\
            class CompiledRodskiUser(FastHttpUser):
                host = {host!r}
                wait_time = between({think_min!r}, {think_max!r})

                def on_start(self):
                    self._returns = []

        """) + tasks_code + "\n"

    def _render_task_method(self, case_id: str, weight: int) -> str:
        """生成单个 @task(weight) 方法；同时填充 self._constants。"""
        case_def = self.shared_ctx.case_registry.get(case_id, {})
        steps = list(case_def.get("pre_process", []) + case_def.get("test_case", []))

        method_lines: List[str] = []
        method_lines.append(f"    @task({weight})")
        safe_id = _safe_identifier(case_id)
        method_lines.append(f"    def task_{safe_id}(self):")
        method_lines.append("        self._returns = []")

        if not steps:
            method_lines.append("        pass")
            return "\n".join(method_lines)

        for step_idx, step in enumerate(steps):
            action = step.get("action", "").lower()
            model  = step.get("model", "")
            data   = step.get("data", "")

            if action == "send":
                model_def = self.shared_ctx.model_registry.get(model, {})
                data_row  = self._resolve_data_row(case_id, step, step_idx)
                body      = self._build_body(model_def, data_row)

                method_expr = self._extract_method(model_def, data_row)
                url_expr    = self._extract_url(model_def, data_row)
                body_repr   = self._build_body_repr(
                    case_id, step_idx, model_def, data_row
                )
                headers_repr = self._build_headers_repr(
                    case_id, step_idx, model_def, data_row
                )

                prefix = f"_TC_{_safe_identifier(case_id)}_STEP{step_idx}"

                method_const  = f"{prefix}_METHOD"
                url_const     = f"{prefix}_URL"
                self._constants[method_const] = repr(method_expr)
                self._constants[url_const]    = repr(url_expr)

                method_lines.append(
                    f"        _resp = self.client.request("
                    f"{method_const}, {url_const}, "
                    f"name={repr(method_expr + ' ' + url_expr)}, "
                    f"json={body_repr}, headers={headers_repr})"
                )
                method_lines.append(
                    f"        self._returns.append({{"
                    f"'status_code': _resp.status_code, "
                    f"'text': _resp.text}})"
                )

            elif action in ("get", "assert", "verify", "check"):
                # 断言步骤：跳过，压测中不验证响应
                method_lines.append(f"        # step {step_idx}: {action} skipped in load mode")

            else:
                # 其他 action：以注释记录
                method_lines.append(
                    f"        # step {step_idx}: action={action!r} model={model!r} skipped"
                )

        return "\n".join(method_lines)

    def _build_body(self, model_def: dict, data_row: dict) -> dict:
        """将 model_def + data_row 合并为请求 body dict（纯字面量，用于 meta 分析）。"""
        body = {}
        for field_name, field_meta in model_def.items():
            if not isinstance(field_meta, dict):
                continue
            elem_type = field_meta.get("element_type", "")
            # 只取 type=field 的元素（排除 http_method/_url/header 等）
            if elem_type == "field":
                raw = data_row.get(field_name, "")
                body[field_name] = self._resolve_literal(raw)
        return body

    def _compute_hash(
        self,
        plan_path: Optional[Path],
        case_paths: Optional[List[Path]],
        model_path: Optional[Path],
        data_path: Optional[Path],
    ) -> str:
        """SHA-256(plan_xml_content + case_xmls_content + model_xml_content + data_sqlite_mtime)。"""
        h = hashlib.sha256()

        def _feed_file(p: Optional[Path]):
            if p and Path(p).exists():
                h.update(Path(p).read_bytes())

        def _feed_mtime(p: Optional[Path]):
            if p and Path(p).exists():
                mtime = os.path.getmtime(str(p))
                h.update(str(mtime).encode())

        _feed_file(plan_path)
        for cp in (case_paths or []):
            _feed_file(cp)
        _feed_file(model_path)
        _feed_mtime(data_path)

        return h.hexdigest()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_host(self) -> str:
        gv = self.shared_ctx.global_values
        return gv.get("DefaultValue", {}).get("URL", "http://localhost")

    def _resolve_data_row(self, case_id: str, step: dict, step_idx: int) -> dict:
        """从 data_store 取数据行；若找不到则返回 step 内嵌 data dict。

        优先级：
        1. data_store.get_data(model_name, data_id) — 标准 SQLite 数据行
        2. 非空 dict 形式的内嵌 data 属性
        3. 空 dict
        """
        data_store = self.shared_ctx.data_store
        model_name = step.get("model", "")
        data_id = step.get("data", "")

        # 优先从 get_data(model, data_id) 取
        if hasattr(data_store, "get_data") and model_name and data_id:
            try:
                row = data_store.get_data(model_name, data_id)
                if row and isinstance(row, dict):
                    return row
            except Exception:
                pass

        # 旧 get_table 兼容（mock/测试 DataTableParser）
        if hasattr(data_store, "get_table"):
            try:
                table = data_store.get_table(case_id)
                if table:
                    return table[0]
            except Exception:
                pass

        data_attr = step.get("data", "")
        if isinstance(data_attr, dict) and data_attr:
            return data_attr
        return {}

    def _extract_method(self, model_def: dict, data_row: dict) -> str:
        # 优先从 model 的 _method 元素取（element_type=http_method）
        raw = self._get_model_element_value(model_def, "http_method", "_method")
        if not raw:
            raw = model_def.get("method", data_row.get("method", "POST"))
        return self._resolve_literal(raw) or "POST"

    def _extract_url(self, model_def: dict, data_row: dict) -> str:
        # 优先从 model 的 _url 元素取（element_type=http_url）
        raw = self._get_model_element_value(model_def, "http_url", "_url")
        if not raw:
            raw = model_def.get("url", data_row.get("url", "/"))
        # 如果是完整 URL，FastHttpUser 需要的是相对路径（host 已由 class 属性提供）
        # 但压测场景下直接传完整 URL 也可兼容；保持原样即可
        return self._resolve_literal(raw) or "/"

    def _get_model_element_value(
        self, model_def: dict, element_type: str, fallback_key: str
    ) -> str:
        """从 model_registry 元素字典中按 element_type 或 fallback_key 取 value。"""
        # 先按 element_type 搜索
        for key, elem in model_def.items():
            if isinstance(elem, dict) and elem.get("element_type") == element_type:
                return elem.get("value", "")
        # 再按 fallback_key 取
        elem = model_def.get(fallback_key, {})
        if isinstance(elem, dict):
            return elem.get("value", "")
        return ""

    def _resolve_literal(self, raw: Any) -> Any:
        """将 ${GlobalValue.xxx} 展开；其他占位符返回原始字符串（编译期无法求值的）。"""
        if not isinstance(raw, str):
            return raw
        # GlobalValue 展开
        def _gv_replace(m):
            key = m.group(1)
            parts = key.split(".", 1)
            gv = self.shared_ctx.global_values
            if len(parts) == 2:
                val = gv.get(parts[0], {}).get(parts[1])
            else:
                # 搜索所有 group
                val = None
                for group in gv.values():
                    if isinstance(group, dict) and parts[0] in group:
                        val = group[parts[0]]
                        break
            return str(val) if val is not None else m.group(0)

        return _RE_GLOBALVALUE.sub(_gv_replace, raw)

    def _build_body_repr(
        self, case_id: str, step_idx: int, model_def: dict, data_row: dict
    ) -> str:
        """返回 Python 表达式字符串，表示请求 body（可含 lambda）。"""
        parts = []
        for field_name, field_meta in model_def.items():
            if not isinstance(field_meta, dict):
                continue
            elem_type = field_meta.get("element_type", "")
            locator_type = field_meta.get("locator_type", "")
            # 只取 element_type=field 且 locator_type=field 的元素作为 body 字段
            # 排除 http_method、http_url、header 等
            if elem_type != "field" or locator_type == "header":
                continue
            raw = data_row.get(field_name, "")
            expr = self._value_expr(raw, case_id, step_idx, field_name)
            parts.append(f"    {field_name!r}: {expr}")

        if not parts:
            # 尝试用 data_row 直接组装 body（对于无 model fields 的简单接口）
            for k, v in data_row.items():
                if k.startswith("_") or k in ("method", "url"):
                    continue
                expr = self._value_expr(str(v), case_id, step_idx, k)
                parts.append(f"    {k!r}: {expr}")

        if not parts:
            return "{}"
        return "{\n" + ",\n".join(parts) + "\n    }"

    def _build_headers_repr(
        self, case_id: str, step_idx: int, model_def: dict, data_row: dict
    ) -> str:
        """返回 headers dict Python 表达式字符串。"""
        parts = []
        for field_name, field_meta in model_def.items():
            if isinstance(field_meta, dict) and field_meta.get("locator_type") == "header":
                raw = data_row.get(field_name, "")
                expr = self._value_expr(raw, case_id, step_idx, field_name)
                parts.append(f"    {field_name!r}: {expr}")
        if not parts:
            return "{}"
        return "{\n" + ",\n".join(parts) + "\n    }"

    def _value_expr(self, raw: str, case_id: str, step_idx: int, field_name: str) -> str:
        """
        将单个字段值转换为 Python 表达式字符串：
        - 字面量 → repr(值)（先展开 GlobalValue）
        - ${random(...)} → lambda 表达式
        - ${date(...)}   → lambda 表达式
        - ${Return[-N].field} → self._returns[-N].get('field')
        - 多层 Return 链（嵌套/多个 Return 引用）→ WARN + repr('')
        """
        if not isinstance(raw, str):
            return repr(raw)

        # 先展开 GlobalValue
        raw = self._resolve_literal(raw)

        # 检查 Return 引用数量
        return_matches = _RE_RETURN.findall(raw)
        if len(return_matches) > 1:
            warnings.warn(
                f"[LoadCompiler] case={case_id} step={step_idx} field={field_name}: "
                f"多层 Return 链不支持，跳过该字段（使用空字符串）。",
                UserWarning,
                stacklevel=4,
            )
            return repr("")

        # 单个 Return 引用
        if len(return_matches) == 1:
            idx_str, field = return_matches[0]
            idx = int(idx_str)
            if field:
                return f"self._returns[{idx}].get({field!r}, '') if self._returns else ''"
            else:
                return f"self._returns[{idx}] if self._returns else ''"

        # random(...)
        m = _RE_RANDOM.search(raw)
        if m:
            call = m.group(1)  # e.g. random(1, 100)
            return f"(lambda: _random.{call})()"

        # date(...)
        m = _RE_DATE.search(raw)
        if m:
            fmt_call = m.group(1)  # e.g. date(%Y-%m-%d)
            # 提取格式字符串
            inner = re.match(r'date\(([^)]*)\)', fmt_call)
            fmt = inner.group(1) if inner else "%Y-%m-%d"
            return f"(lambda: _datetime.now().strftime({fmt!r}))()"

        # 纯字面量
        return repr(raw)
