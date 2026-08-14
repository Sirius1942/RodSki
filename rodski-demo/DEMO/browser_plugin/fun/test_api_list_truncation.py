#!/usr/bin/env python3
"""TC_BP_013: recording/list 超过 20 个文件时的截断行为"""
import sys, time
try:
    import requests
except ImportError:
    import subprocess; subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'requests', '-q'])
    import requests

BASE_URL = 'http://localhost:5002'
errors = []

def assert_eq(a, b, msg=''): assert a == b, f'期望 {b!r}, 实际 {a!r}. {msg}'
def assert_true(v, msg=''): assert v, msg or f'期望为真, 实际 {v!r}'
def check(desc, fn):
    try: fn(); print(f'  ✅ {desc}'); return True
    except Exception as e: print(f'  ❌ {desc}: {e}', file=sys.stderr); errors.append(desc); return False

BASE_PAYLOAD = {
    'rodski_plugin_version': '1.0.0',
    'recorded_at': '2026-07-13T10:00:00Z',
    'exported_at': '2026-07-13T10:01:00Z',
    'base_url': 'http://localhost/list-test',
    'total_steps': 1,
    'total_screenshots': 0,
    'steps': [{'seq': 1, 'action': 'navigate', 'url': 'http://localhost/list-test', 'timestamp': '2026-07-13T10:00:01Z'}],
    'screenshots': [],
    'final_page_snapshot': None,
}

# 先查当前文件数
r0 = requests.get(f'{BASE_URL}/api/plugin/recording/list', timeout=3)
current_count = len(r0.json().get('recordings', []))
print(f'  📋 当前已有录制文件: {current_count} 个')

# 上传足够多的文件使总数超过 20
uploads_needed = max(0, 22 - current_count)
print(f'  📋 需要再上传 {uploads_needed} 个文件')

uploaded = []
for i in range(uploads_needed):
    r = requests.post(f'{BASE_URL}/api/plugin/recording/upload', json=BASE_PAYLOAD, timeout=5)
    if r.status_code == 200:
        uploaded.append(r.json().get('filename'))
    time.sleep(0.05)  # 避免同秒文件名冲突

# 查询列表
r_list = requests.get(f'{BASE_URL}/api/plugin/recording/list', timeout=3)
check('list 返回 200', lambda: assert_eq(r_list.status_code, 200))
recordings = r_list.json().get('recordings', [])
check(f'list 最多返回 20 个文件', lambda: assert_true(len(recordings) <= 20, f'返回了 {len(recordings)} 个'))
print(f'  📋 当前 list 返回 {len(recordings)} 个文件（上限 20）')

# 验证每个文件项的字段
if recordings:
    first = recordings[0]
    check('list 每项含 filename', lambda: assert_true(isinstance(first.get('filename'), str)))
    check('list 每项含 size', lambda: assert_true(isinstance(first.get('size'), int)))
    check('list 每项含 created_at', lambda: assert_true(isinstance(first.get('created_at'), str)))
    check('filename 格式为 recording_*.json', lambda: assert_true(
        first['filename'].startswith('recording_') and first['filename'].endswith('.json')
    ))

# 验证返回的是最新 20 个（按文件名倒序）
if len(recordings) >= 2:
    check('list 按时间倒序排列', lambda: assert_true(
        recordings[0]['filename'] >= recordings[1]['filename'],
        f'{recordings[0]["filename"]} 应 >= {recordings[1]["filename"]}'
    ))

if errors: print(f'\n❌ {len(errors)} 个检查失败', file=sys.stderr); sys.exit(1)
print('\n✅ recording/list 截断行为验证通过')
