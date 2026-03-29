#!/usr/bin/env python3
"""
test_recorder.py — RodSki 测试录像生成器

功能：
  1. 从测试结果目录读取截图，合成带时间戳的视频
  2. 在视频上叠加操作标注（ACTION / STATUS / 时间）
  3. 输出 .mp4 文件，便于 vision_perception 分析

用法：
  python3 test_recorder.py /path/to/test_result_dir [--output video.mp4] [--fps 2]

依赖：
  pip install opencv-python imageio
"""

import argparse
import os
import sys
import time
import re
from pathlib import Path
from datetime import datetime
from typing import Optional

import cv2
import numpy as np

try:
    import imageio
    HAS_IMAGEIO = True
except ImportError:
    HAS_IMAGEIO = False


# ═══════════════════════════════════════════════════════════
# 截图排序：按文件名中的时间戳提取
# ═══════════════════════════════════════════════════════════

def extract_timestamp(filename: str) -> float:
    """从截图文件名中提取时间戳，返回秒数"""
    # 匹配格式: ..._20260328_170728.png
    match = re.search(r'(\d{8})_(\d{6})', filename)
    if match:
        date_str = match.group(1)
        time_str = match.group(2)
        try:
            dt = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
            return dt.timestamp()
        except ValueError:
            pass
    return 0.0


def natural_sort_key(s: str) -> tuple:
    """自然排序：文件名中的数字参与排序"""
    return [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', s)]


def collect_screenshots(result_dir: Path) -> list[Path]:
    """收集所有截图并按时间排序"""
    if not result_dir.exists():
        return []

    screenshots_dir = result_dir / "screenshots"
    if not screenshots_dir.exists():
        return []

    all_files = []
    for ext in ['*.png', '*.jpg', '*.jpeg']:
        all_files.extend(screenshots_dir.glob(ext))

    # 过滤掉 _raw.png 文件（中间文件）
    files = [f for f in all_files if '_raw' not in f.name]

    # 按时间戳排序
    files.sort(key=lambda f: extract_timestamp(f.name))

    return files


# ═══════════════════════════════════════════════════════════
# 帧处理：添加时间戳水印
# ═══════════════════════════════════════════════════════════

def extract_info_from_filename(filename: str) -> dict:
    """从文件名提取操作信息"""
    info = {
        'case_id': '',
        'step': '',
        'phase': '',
        'timestamp': '',
        'status': '',
    }

    # 匹配 case_id: EC_HOME_001
    case_match = re.match(r'^([A-Z_]+)', filename)
    if case_match:
        info['case_id'] = case_match.group(1)

    # 匹配步骤号: 01, 02
    step_match = re.search(r'_(\d{2})_', filename)
    if step_match:
        info['step'] = step_match.group(1)

    # 匹配阶段: 预处理, 用例, 00_操作前, failure
    for phase in ['预处理', '用例', '00_操作前', 'failure']:
        if phase in filename:
            info['phase'] = phase
            break

    # 匹配状态
    if 'failure' in filename:
        info['status'] = 'FAIL'
    elif '00_操作前' in filename:
        info['status'] = 'PENDING'
    else:
        info['status'] = 'RUNNING'

    # 提取时间戳
    ts_match = re.search(r'(\d{8})_(\d{6})', filename)
    if ts_match:
        info['timestamp'] = f"{ts_match.group(1)} {ts_match.group(2)}"

    return info


def add_timestamp_watermark(frame: np.ndarray, filename: str) -> np.ndarray:
    """为帧添加时间戳水印（OpenCV 绘制）"""
    h, w = frame.shape[:2]
    img = frame.copy()

    # 字体
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = max(0.4, min(0.8, w / 800))

    # 颜色
    if 'failure' in filename:
        border_color = (0, 0, 255)  # 红色
        status_color = (0, 0, 255)
    elif '00_操作前' in filename:
        border_color = (0, 255, 255)  # 黄色
        status_color = (0, 255, 255)
    else:
        border_color = (0, 200, 0)  # 绿色
        status_color = (0, 200, 0)

    # 画边框
    thickness = max(2, int(w / 200))
    cv2.rectangle(img, (0, 0), (w-1, h-1), border_color, thickness)

    # 顶部信息栏背景
    bar_h = int(h * 0.06)
    cv2.rectangle(img, (0, 0), (w, bar_h), (0, 0, 0), -1)

    # 提取信息
    info = extract_info_from_filename(filename)

    # 左上角：用例信息
    case_text = info['case_id'] or 'Test'
    step_text = f"Step {info['step']}" if info['step'] else ""
    phase_text = info['phase'] or ""

    y_text = bar_h // 2 + 5
    if info['case_id']:
        cv2.putText(img, case_text, (10, y_text), font, font_scale, (255, 255, 255), 1)
    if step_text:
        cv2.putText(img, f" | {step_text}", (10 + len(case_text) * 15, y_text),
                   font, font_scale, (200, 200, 200), 1)
    if phase_text:
        cv2.putText(img, f" | {phase_text}", (10 + (len(case_text) + len(step_text) + 3) * 15, y_text),
                   font, font_scale, (200, 200, 200), 1)

    # 右上角：状态
    status_text = f"[{info['status']}]"
    (sw, sh), _ = cv2.getTextSize(status_text, font, font_scale * 1.2, 2)
    cv2.putText(img, status_text, (w - sw - 10, y_text),
               font, font_scale * 1.2, status_color, 2)

    # 底部：时间戳
    if info['timestamp']:
        ts_parts = info['timestamp'].split(' ')
        ts_text = f"{ts_parts[0]} {ts_parts[1]}" if len(ts_parts) >= 2 else info['timestamp']
    else:
        ts_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    bar_bottom_h = int(h * 0.04)
    cv2.rectangle(img, (0, h - bar_bottom_h), (w, h), (30, 30, 30), -1)
    cv2.putText(img, ts_text, (10, h - 8),
               font, font_scale * 0.8, (180, 180, 180), 1)

    return img


# ═══════════════════════════════════════════════════════════
# 视频生成
# ═══════════════════════════════════════════════════════════

def create_video_from_screenshots(
    screenshots: list[Path],
    output_path: Path,
    fps: float = 2,
    resize_width: int = 1280,
) -> bool:
    """从截图列表生成视频"""
    if not screenshots:
        print("❌ 没有找到截图文件", file=sys.stderr)
        return False

    if not HAS_IMAGEIO:
        print("❌ 需要安装 imageio: pip install imageio", file=sys.stderr)
        return False

    print(f"📹 正在生成视频: {output_path}")
    print(f"   截图数量: {len(screenshots)}")
    print(f"   输出帧率: {fps} fps")
    print(f"   输出分辨率: {resize_width}px")

    # 读取第一张图确定尺寸
    first_img = cv2.imread(str(screenshots[0]))
    if first_img is None:
        print(f"❌ 无法读取图片: {screenshots[0]}", file=sys.stderr)
        return False

    h, w = first_img.shape[:2]
    ratio = resize_width / w
    resize_h = int(h * ratio)
    target_size = (resize_width, resize_h)

    print(f"   原始尺寸: {w}x{h} → 输出尺寸: {resize_width}x{resize_h}")

    # 收集所有帧
    frames = []
    for i, screenshot in enumerate(screenshots):
        img = cv2.imread(str(screenshot))
        if img is None:
            print(f"   ⚠️ 跳过无法读取的文件: {screenshot.name}")
            continue

        # 调整大小
        img = cv2.resize(img, target_size, interpolation=cv2.INTER_LINEAR)

        # 添加水印
        img = add_timestamp_watermark(img, screenshot.name)

        # BGR → RGB (imageio 需要 RGB)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        frames.append(img_rgb)

        if (i + 1) % 10 == 0:
            print(f"   已处理 {i+1}/{len(screenshots)} 张截图...")

    if not frames:
        print("❌ 没有有效的帧可以生成视频", file=sys.stderr)
        return False

    print(f"   正在写入视频 ({len(frames)} 帧)...")

    # 使用 imageio 生成视频
    writer = imageio.get_writer(
        output_path,
        fps=fps,
        codec='libx264',
        quality=8,
        pixelformat='yuv420p',
    )

    for frame in frames:
        writer.append_data(frame)

    writer.close()

    # 获取文件大小
    size_mb = output_path.stat().st_size / (1024 * 1024)
    duration = len(frames) / fps

    print(f"✅ 视频生成完成!")
    print(f"   文件: {output_path}")
    print(f"   时长: {duration:.1f}s")
    print(f"   大小: {size_mb:.1f} MB")

    return True


def create_video_with_ffmpeg(
    screenshots: list[Path],
    output_path: Path,
    fps: float = 2,
    resize_width: int = 1280,
) -> bool:
    """使用 ffmpeg 从截图生成视频（备选方案）"""
    if not screenshots:
        return False

    import subprocess

    # 创建临时目录链接
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        # 复制截图到临时目录（带序号前缀）
        for i, screenshot in enumerate(screenshots):
            dest = Path(tmpdir) / f"{i:05d}_{screenshot.name}"
            import shutil
            shutil.copy(screenshot, dest)

        # 使用 ffmpeg 生成视频
        pattern = Path(tmpdir) / "%05d_*.png"
        cmd = [
            'ffmpeg', '-y',
            '-framerate', str(fps),
            '-pattern_type', 'glob',
            '-i', str(pattern),
            '-vf', f'scale={resize_width}:-1:flags=lanczos',
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-pix_fmt', 'yuv420p',
            str(output_path)
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                size_mb = output_path.stat().st_size / (1024 * 1024)
                duration = len(screenshots) / fps
                print(f"✅ 视频生成完成! 时长: {duration:.1f}s, 大小: {size_mb:.1f} MB")
                return True
            else:
                print(f"❌ ffmpeg 失败: {result.stderr[-200:]}")
        except Exception as e:
            print(f"❌ ffmpeg 执行出错: {e}")

    return False


# ═══════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="RodSki 测试录像生成器 - 从截图合成测试执行视频",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 test_recorder.py ./result/20260328_170728_ae90f01b
  python3 test_recorder.py ./result/20260328_170728_ae90f01b --output test_video.mp4 --fps 3
        """
    )
    parser.add_argument('result_dir', help='测试结果目录路径')
    parser.add_argument('--output', '-o', help='输出视频路径（默认: result_dir/video.mp4）')
    parser.add_argument('--fps', type=float, default=2, help='视频帧率（默认: 2）')
    parser.add_argument('--width', type=int, default=1280, help='输出视频宽度（默认: 1280）')
    parser.add_argument('--method', choices=['opencv', 'ffmpeg'], default='opencv',
                       help='视频生成方式（默认: opencv）')

    args = parser.parse_args()

    result_dir = Path(args.result_dir).resolve()
    if not result_dir.exists():
        print(f"❌ 目录不存在: {result_dir}", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output) if args.output else (result_dir / "test_video.mp4")

    print("")
    print("╔══════════════════════════════════════════╗")
    print("║  🚗 RodSki 测试录像生成器                 ║")
    print("╚══════════════════════════════════════════╝")
    print(f"  结果目录: {result_dir}")
    print(f"  输出路径: {output_path}")
    print(f"  帧率: {args.fps} fps")
    print(f"  方法: {args.method}")
    print("")

    screenshots = collect_screenshots(result_dir)
    if not screenshots:
        print(f"❌ 在 {result_dir / 'screenshots'} 中没有找到截图")
        sys.exit(1)

    success = False
    if args.method == 'opencv' and HAS_IMAGEIO:
        success = create_video_from_screenshots(
            screenshots, output_path, args.fps, args.width
        )
    elif args.method == 'ffmpeg':
        success = create_video_with_ffmpeg(
            screenshots, output_path, args.fps, args.width
        )
    else:
        print("❌ 请安装 imageio: pip install imageio", file=sys.stderr)
        sys.exit(1)

    if success:
        print(f"\n📹 视频已生成: {output_path}")
        print("   可用 vision_perception 分析视频内容:")
        print(f"   python3 vision_perception.py --video {output_path} \"描述测试执行过程\"")
    else:
        print("\n❌ 视频生成失败", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
