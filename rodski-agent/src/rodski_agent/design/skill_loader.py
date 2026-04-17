"""解析 skills/ 目录下的 md 业务文档，提取术语、操作流程、测试约束。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class Flow:
    name: str
    description: str
    steps: List[str]


@dataclass
class SkillContext:
    terms: Dict[str, str] = field(default_factory=dict)
    flows: List[Flow] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "terms": self.terms,
            "flows": [{"name": f.name, "description": f.description, "steps": f.steps} for f in self.flows],
            "constraints": self.constraints,
        }


def _parse_md(text: str) -> SkillContext:
    ctx = SkillContext()
    # Split into H2 sections
    sections = re.split(r"^##\s+", text, flags=re.MULTILINE)
    for section in sections[1:]:
        lines = section.split("\n")
        header = lines[0].strip()
        body = "\n".join(lines[1:])

        if header == "业务术语":
            for m in re.finditer(r"-\s+\*\*(.+?)\*\*[：:]\s*(.+)", body):
                ctx.terms[m.group(1).strip()] = m.group(2).strip()

        elif header == "操作流程":
            for m in re.finditer(r"^###\s+(.+)\n([\s\S]+?)(?=^###|\Z)", body, re.MULTILINE):
                name = m.group(1).strip()
                desc = m.group(2).strip()
                # Split steps by sentence-ending punctuation or newlines
                raw = re.split(r"[。\n]+", desc)
                steps = [s.strip() for s in raw if s.strip()]
                ctx.flows.append(Flow(name=name, description=desc, steps=steps))

        elif header == "测试约束":
            for m in re.finditer(r"^-\s+(.+)", body, re.MULTILINE):
                ctx.constraints.append(m.group(1).strip())

    return ctx


def load_skill_docs(skills_dir: str) -> SkillContext:
    merged = SkillContext()
    for md_file in sorted(Path(skills_dir).glob("*.md")):
        ctx = _parse_md(md_file.read_text(encoding="utf-8"))
        merged.terms.update(ctx.terms)
        merged.flows.extend(ctx.flows)
        merged.constraints.extend(ctx.constraints)
    return merged
