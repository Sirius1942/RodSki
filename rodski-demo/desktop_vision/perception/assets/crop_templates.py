#!/usr/bin/env python3
"""crop_templates.py — 从一张登录页/Dashboard 截图裁出 vision_image 参考图。

用法：
    # 1) 交互式：在图上拖框选区域，按 's' 保存
    python3 crop_templates.py interactive --image login.png --out-dir ../assets/

    # 2) 配置式：根据 manifest.yaml 中的 bbox 批量裁剪
    python3 crop_templates.py batch --manifest manifest.yaml --out-dir ../assets/

manifest.yaml 格式:
    source_images:
      login:   path/to/login_screen.png
      after:   path/to/after_login.png
    crops:
      - name: username_input
        source: login
        bbox: [1580, 780, 2260, 880]   # [x1, y1, x2, y2] 像素坐标（原图尺度）
      - name: password_input
        source: login
        bbox: [1580, 900, 2260, 1000]
      - name: login_btn
        source: login
        bbox: [1580, 1060, 2260, 1160]
      - name: welcome_msg
        source: after
        bbox: [3080, 20, 3220, 70]
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("ERROR: 需要 Pillow，pip install Pillow", file=sys.stderr)
    sys.exit(2)


def crop_one(src_path: Path, bbox: tuple[int, int, int, int], out_path: Path) -> None:
    img = Image.open(src_path)
    x1, y1, x2, y2 = bbox
    if not (0 <= x1 < x2 <= img.width and 0 <= y1 < y2 <= img.height):
        raise ValueError(f"bbox {bbox} 超出图片范围 {img.size}")
    crop = img.crop(bbox)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    crop.save(out_path)
    print(f"  ✓ {out_path.name}  {crop.size}  <- {src_path.name}{list(bbox)}")


def batch(manifest_path: Path, out_dir: Path) -> None:
    import yaml  # 延迟导入，可选依赖
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)

    base = manifest_path.parent
    sources = {k: (base / v).resolve() for k, v in manifest["source_images"].items()}
    for k, p in sources.items():
        if not p.exists():
            print(f"ERROR: source '{k}' 文件不存在: {p}", file=sys.stderr)
            sys.exit(1)

    for crop_def in manifest["crops"]:
        src = sources[crop_def["source"]]
        bbox = tuple(crop_def["bbox"])
        out = out_dir / f"{crop_def['name']}.png"
        crop_one(src, bbox, out)


def interactive(image_path: Path, out_dir: Path) -> None:
    """简化交互：通过命令行参数指定 name 和 bbox，方便脚本化调用。"""
    print("ERROR: interactive 模式留待后续实现（需要 GUI）", file=sys.stderr)
    print("当前请使用 batch 模式 + manifest.yaml", file=sys.stderr)
    sys.exit(2)


def main() -> int:
    parser = argparse.ArgumentParser(description="vision_image 参考图裁剪工具")
    sub = parser.add_subparsers(dest="mode", required=True)

    p_batch = sub.add_parser("batch", help="从 manifest.yaml 批量裁剪")
    p_batch.add_argument("--manifest", type=Path, required=True)
    p_batch.add_argument("--out-dir", type=Path, required=True)

    p_inter = sub.add_parser("interactive", help="交互式（占位）")
    p_inter.add_argument("--image", type=Path, required=True)
    p_inter.add_argument("--out-dir", type=Path, required=True)

    args = parser.parse_args()

    if args.mode == "batch":
        batch(args.manifest, args.out_dir)
    elif args.mode == "interactive":
        interactive(args.image, args.out_dir)

    return 0


if __name__ == "__main__":
    sys.exit(main())
