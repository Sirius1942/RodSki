"""实用工具函数"""
from pathlib import Path
from typing import Optional


def ensure_dir(path: str) -> Path:
    """确保目录存在"""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def safe_filename(name: str) -> str:
    """生成安全的文件名"""
    return "".join(c if c.isalnum() or c in "._- " else "_" for c in name)


def truncate_text(text: str, max_len: int = 100) -> str:
    """截断文本"""
    return text if len(text) <= max_len else text[:max_len-3] + "..."


def format_duration(seconds: float) -> str:
    """格式化时长"""
    if seconds < 60:
        return f"{seconds:.2f}s"
    mins = int(seconds // 60)
    secs = seconds % 60
    return f"{mins}m {secs:.2f}s"
