"""评测数据集加载器。

数据集目录结构：
    eval_data/
        manifest.yaml       # 数据集元信息 + 任务列表
        images/             # 截图文件
        annotations/        # 标注文件（可选，manifest 内联也行）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class EvalTask:
    """单个评测任务。"""
    image: str  # 相对 dataset_dir 的图片路径
    prompt: str
    expected_bbox: Tuple[int, int, int, int]  # pixel (x1, y1, x2, y2)
    expected_center: Optional[Tuple[int, int]] = None
    element_type: Optional[str] = None
    hints: List[dict] = field(default_factory=list)  # for fused eval


@dataclass
class EvalDataset:
    """评测数据集。"""
    name: str
    tasks: List[EvalTask]
    base_dir: Path


def load_dataset(dataset_dir: Path) -> EvalDataset:
    """加载 manifest.yaml 并返回 EvalDataset。"""
    import yaml  # type: ignore[import-untyped]

    manifest_path = dataset_dir / "manifest.yaml"
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest.yaml not found in {dataset_dir}")

    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    name = data.get("name", dataset_dir.name)
    tasks = []
    for t in data.get("tasks", []):
        bbox = tuple(t["expected_bbox"])
        center = tuple(t["expected_center"]) if "expected_center" in t else None
        tasks.append(EvalTask(
            image=t["image"],
            prompt=t["prompt"],
            expected_bbox=bbox,  # type: ignore
            expected_center=center,  # type: ignore
            element_type=t.get("element_type"),
            hints=t.get("hints", []),
        ))
    return EvalDataset(name=name, tasks=tasks, base_dir=dataset_dir)


__all__ = ["EvalTask", "EvalDataset", "load_dataset"]
