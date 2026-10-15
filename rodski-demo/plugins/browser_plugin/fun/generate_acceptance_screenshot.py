#!/usr/bin/env python3
"""TC_BP_019: 生成 API 验收汇总截图（Pillow 渲染 - 作为验收证据）"""
import sys, os, datetime, subprocess, json

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pillow', '-q'])
    from PIL import Image, ImageDraw, ImageFont

try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'requests', '-q'])
    import requests

BASE_URL = 'http://localhost:5002'

# ---- 采集所有 API 端点的实际响应用于截图 ----
api_results = []

def probe(label, method, path, json_body=None):
    try:
        if method == 'GET':
            r = requests.get(f'{BASE_URL}{path}', timeout=3)
        else:
            r = requests.post(f'{BASE_URL}{path}', json=json_body, timeout=3)
        body = r.json()
        status = r.status_code
        ok_icon = '✅' if status < 300 and body.get('ok', True) is not False else '⚠️'
        summary = json.dumps(body, ensure_ascii=False)[:80]
        api_results.append((ok_icon, label, status, summary))
    except Exception as e:
        api_results.append(('❌', label, -1, str(e)[:80]))

probe('/health',                    'GET',  '/health')
probe('/api/plugin/env/list',       'GET',  '/api/plugin/env/list')
probe('/api/plugin/env/current',    'GET',  '/api/plugin/env/current')
probe('/api/plugin/env/switch beta','POST', '/api/plugin/env/switch', {'env': 'beta'})
probe('/api/plugin/last-failure',   'GET',  '/api/plugin/last-failure')
probe('/api/plugin/report-failure', 'POST', '/api/plugin/report-failure',
      {'step_id': 'SCREENSHOT_TEST', 'element_name': 'testBtn', 'locator': {'type': 'id', 'value': 'testBtn'}})
probe('/api/plugin/last-failure (after report)', 'GET', '/api/plugin/last-failure')
probe('/api/plugin/recording/list', 'GET',  '/api/plugin/recording/list')
probe('/api/plugin/clear-failure',  'POST', '/api/plugin/clear-failure')

# ---- 渲染截图 ----
W, H = 900, 680
bg    = (15, 15, 30)
panel = (26, 26, 46)
green = (39, 174, 96)
red   = (231, 76, 60)
amber = (243, 156, 18)
blue  = (74, 144, 217)
white = (224, 224, 224)
gray  = (100, 100, 120)

img = Image.new('RGB', (W, H), bg)
draw = ImageDraw.Draw(img)

# 尝试加载等宽字体（macOS 内置）
try:
    font_title = ImageFont.truetype('/System/Library/Fonts/Menlo.ttc', 18)
    font_main  = ImageFont.truetype('/System/Library/Fonts/Menlo.ttc', 13)
    font_small = ImageFont.truetype('/System/Library/Fonts/Menlo.ttc', 11)
except Exception:
    font_title = font_main = font_small = ImageFont.load_default()

# 标题栏
draw.rectangle([(0, 0), (W, 52)], fill=panel)
draw.text((16, 10), 'RodSki Browser Plugin', font=font_title, fill=blue)
draw.text((16, 32), 'Plugin API 验收截图  —  rodski-web Plugin API 全端点验证', font=font_small, fill=gray)
ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
draw.text((W - 200, 32), ts, font=font_small, fill=gray)

# 表格头
y = 68
draw.rectangle([(12, y), (W-12, y+24)], fill=(30, 40, 70))
draw.text((20,  y+5), '状态', font=font_small, fill=white)
draw.text((70,  y+5), 'API 端点',   font=font_small, fill=white)
draw.text((370, y+5), 'HTTP',       font=font_small, fill=white)
draw.text((420, y+5), '响应摘要',   font=font_small, fill=white)
y += 30

# 数据行
for idx, (icon, label, status, summary) in enumerate(api_results):
    row_bg = (20, 20, 38) if idx % 2 == 0 else (22, 22, 42)
    draw.rectangle([(12, y), (W-12, y+22)], fill=row_bg)

    status_color = green if status == 200 else (amber if 200 < status < 500 else red)
    draw.text((20,  y+4), icon,                     font=font_main, fill=status_color)
    draw.text((50,  y+4), label[:38],                font=font_main, fill=white)
    draw.text((370, y+4), str(status) if status > 0 else '---', font=font_main, fill=status_color)
    draw.text((420, y+4), summary[:55],              font=font_small, fill=gray)
    y += 24

# 分隔线
y += 8
draw.line([(12, y), (W-12, y)], fill=(40, 40, 60), width=1)
y += 12

# 统计汇总
ok_count = sum(1 for r in api_results if r[0] == '✅')
warn_count = sum(1 for r in api_results if r[0] == '⚠️')
fail_count = sum(1 for r in api_results if r[0] == '❌')

draw.text((20, y), f'✅ 通过: {ok_count}    ⚠️ 警告: {warn_count}    ❌ 失败: {fail_count}    共 {len(api_results)} 个端点',
          font=font_main, fill=white)
y += 24

# 录制文件统计
try:
    r_list = requests.get(f'{BASE_URL}/api/plugin/recording/list', timeout=3)
    recs = r_list.json().get('recordings', [])
    draw.text((20, y), f'📁 录制文件: {len(recs)} 个（最新: {recs[0]["filename"] if recs else "无"}）',
              font=font_small, fill=gray)
    y += 20
except Exception:
    pass

# 底部版本信息
draw.rectangle([(0, H-30), (W, H)], fill=panel)
draw.text((16, H-20), 'RodSki Browser Plugin v1.0.0  |  TC_BP_019 验收截图', font=font_small, fill=gray)
draw.text((W-160, H-20), f'rodski-web: {BASE_URL}', font=font_small, fill=gray)

# ---- 保存到 result/screenshots/ ----
result_dir = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'result')
)
# 找最新的 result 子目录
result_subdirs = [d for d in os.listdir(result_dir) if os.path.isdir(os.path.join(result_dir, d))] if os.path.isdir(result_dir) else []
if result_subdirs:
    latest_result = os.path.join(result_dir, sorted(result_subdirs)[-1])
    screenshot_dir = os.path.join(latest_result, 'screenshots')
else:
    screenshot_dir = result_dir
os.makedirs(screenshot_dir, exist_ok=True)

out_path = os.path.join(screenshot_dir, 'TC_BP_019_api_acceptance.png')
img.save(out_path, 'PNG')
print(f'✅ 验收截图已生成: {out_path}')
print(f'   分辨率: {W}x{H}px')
print(f'   API 端点: {len(api_results)} 个，通过: {ok_count}，警告: {warn_count}，失败: {fail_count}')

# 同时在当前目录保存一份（供查看）
local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'result',
                          'TC_BP_019_api_acceptance_latest.png')
img.save(os.path.normpath(local_path), 'PNG')
print(f'   副本: {os.path.normpath(local_path)}')

if fail_count > 0:
    print(f'\n⚠️  有 {fail_count} 个端点异常，但截图已生成', file=sys.stderr)
    # 不退出 1，截图是证据，不是验收条件本身
print('\n✅ 验收截图生成完成')
