"""评测 runner — 跑数据集，输出 JSON 报告。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .dataset import load_dataset
from .metrics import accuracy, center_in_bbox, latency_percentile


def run_eval(
    dataset_dir: Path,
    model: str = "qwen3-vl:2b",
    ollama_host: str = "http://localhost:11434",
) -> Dict[str, Any]:
    """跑评测数据集，返回报告 dict。"""
    from ..agent import VLMAgent
    from ..coords import bbox_to_pixels, read_image_size

    dataset = load_dataset(dataset_dir)
    agent = VLMAgent(model=model, ollama_host=ollama_host)

    predictions = []
    latencies = []

    for task in dataset.tasks:
        image_path = dataset.base_dir / task.image
        if not image_path.exists():
            predictions.append({"hit": False, "error": "image not found"})
            continue

        try:
            result = agent.locate(
                prompt=task.prompt,
                image=image_path,
                element_type=task.element_type,
            )
        except Exception as exc:
            predictions.append({"hit": False, "error": str(exc)})
            continue

        if result is None:
            predictions.append({"hit": False, "error": "not found"})
            continue

        image_size = read_image_size(image_path)
        px_bbox = bbox_to_pixels(result.bbox, image_size)
        center = ((px_bbox[0] + px_bbox[2]) // 2, (px_bbox[1] + px_bbox[3]) // 2)
        hit = center_in_bbox(center, task.expected_bbox)
        latencies.append(result.latency_ms)
        predictions.append({
            "hit": hit,
            "predicted_center": list(center),
            "predicted_bbox": list(px_bbox),
            "expected_bbox": list(task.expected_bbox),
            "latency_ms": result.latency_ms,
            "prompt": task.prompt,
        })

    return {
        "dataset": dataset.name,
        "model": model,
        "total_tasks": len(dataset.tasks),
        "accuracy": accuracy(predictions),
        "latency_p50_ms": latency_percentile(latencies, 50),
        "latency_p95_ms": latency_percentile(latencies, 95),
        "predictions": predictions,
    }


__all__ = ["run_eval"]
