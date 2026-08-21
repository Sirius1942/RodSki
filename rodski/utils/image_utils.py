"""图片处理工具模块 - 将图片转换为 base64 data URI"""
import base64
import mimetypes
from pathlib import Path
from typing import Optional


def image_to_base64(image_path: str) -> Optional[str]:
    """将图片文件转换为 base64 data URI

    Args:
        image_path: 图片文件路径

    Returns:
        base64 data URI 字符串，格式: data:image/png;base64,iVBORw0KG...
        如果失败返回 None
    """
    try:
        path = Path(image_path)
        if not path.exists() or not path.is_file():
            return None

        # 检测 MIME 类型
        mime_type, _ = mimetypes.guess_type(str(path))
        if not mime_type or not mime_type.startswith('image/'):
            # 默认为 PNG
            mime_type = 'image/png'

        # 读取图片并转换为 base64
        with open(path, 'rb') as f:
            image_data = f.read()

        b64_data = base64.b64encode(image_data).decode('utf-8')
        return f"data:{mime_type};base64,{b64_data}"

    except Exception as e:
        print(f"警告: 无法转换图片 {image_path}: {e}")
        return None


def convert_img_to_base64(html: str, base_dir: Optional[str] = None) -> str:
    """将 HTML 中的 <img src="..."> 转换为 base64 嵌入

    Args:
        html: HTML 内容
        base_dir: 图片相对路径的基准目录

    Returns:
        转换后的 HTML
    """
    import re

    # 匹配 <img src="path"> 模式
    pattern = r'<img\s+[^>]*src=["\']([^"\']+)["\'][^>]*>'

    def replace_img(match):
        full_tag = match.group(0)
        img_path = match.group(1)

        # 跳过已经是 data URI 的
        if img_path.startswith('data:'):
            return full_tag

        # 跳过 http/https URL
        if img_path.startswith(('http://', 'https://')):
            return full_tag

        # 解析相对路径
        if base_dir:
            full_path = Path(base_dir) / img_path
        else:
            full_path = Path(img_path)

        # 转换为 base64
        b64_uri = image_to_base64(str(full_path))
        if b64_uri:
            # 替换 src 属性
            new_tag = re.sub(
                r'src=["\'][^"\']+["\']',
                f'src="{b64_uri}"',
                full_tag
            )
            return new_tag
        else:
            # 转换失败，保留原标签
            return full_tag

    return re.sub(pattern, replace_img, html)
