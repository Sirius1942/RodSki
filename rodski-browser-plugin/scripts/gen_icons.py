#!/usr/bin/env python3
"""生成 RodSki 浏览器插件图标（PNG）"""
import struct, zlib, base64, os

def make_png(size, bg_color, text_color, letter='R'):
    """生成简单的纯色带字母 PNG 图标"""
    width = height = size

    def write_chunk(chunk_type, data):
        chunk_len = len(data)
        chunk_data = chunk_type + data
        crc = zlib.crc32(chunk_data) & 0xffffffff
        return struct.pack('>I', chunk_len) + chunk_data + struct.pack('>I', crc)

    # PNG header
    png_header = b'\x89PNG\r\n\x1a\n'

    # IHDR
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    ihdr = write_chunk(b'IHDR', ihdr_data)

    # Image data: draw a rounded square with gradient-like effect
    bg_r, bg_g, bg_b = bg_color
    fg_r, fg_g, fg_b = text_color

    pixels = []
    for y in range(height):
        row = [0]  # filter byte
        for x in range(width):
            # Rounded corners
            cx, cy = x - width/2, y - height/2
            radius = width * 0.35

            # Background color
            r, g, b = bg_r, bg_g, bg_b

            # Draw letter 'R' in center (simplified)
            # Letter occupies center 60% of icon
            lx = (x - width * 0.2) / (width * 0.6)
            ly = (y - height * 0.2) / (height * 0.6)

            if 0 <= lx <= 1 and 0 <= ly <= 1:
                # Vertical bar of R
                if 0.05 <= lx <= 0.35:
                    r, g, b = fg_r, fg_g, fg_b
                # Top bump of R
                if 0.3 <= lx <= 0.95 and 0.05 <= ly <= 0.5:
                    if abs((lx - 0.65)**2 + (ly - 0.28)**2 - 0.09) < 0.05:
                        r, g, b = fg_r, fg_g, fg_b
                # Leg of R
                if 0.35 <= lx <= 0.95 and 0.5 <= ly <= 0.95:
                    if lx <= 0.35 + (ly - 0.5) * 1.1:
                        r, g, b = fg_r, fg_g, fg_b

            row.extend([r, g, b])
        pixels.append(bytes(row))

    raw_data = b''.join(pixels)
    compressed = zlib.compress(raw_data, 9)
    idat = write_chunk(b'IDAT', compressed)
    iend = write_chunk(b'IEND', b'')

    return png_header + ihdr + idat + iend


# 生成各尺寸图标
sizes = [16, 32, 48, 128]
bg = (26, 90, 180)   # RodSki 蓝色
fg = (255, 255, 255)  # 白色

icons_dir = os.path.join(os.path.dirname(__file__), '..', 'icons')
os.makedirs(icons_dir, exist_ok=True)

for size in sizes:
    png_data = make_png(size, bg, fg)
    path = os.path.join(icons_dir, f'icon{size}.png')
    with open(path, 'wb') as f:
        f.write(png_data)
    print(f'生成: {path} ({size}x{size})')

print('图标生成完成')
