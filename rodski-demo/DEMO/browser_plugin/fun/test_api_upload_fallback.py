#!/usr/bin/env python3
"""TC_BP_012: recording/upload 缺少 total_steps 字段时的 fallback 计算"""
import sys
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

# 1. 缺少 total_steps，框架应从 steps 数组长度推算
payload_no_total = {
    'rodski_plugin_version': '1.0.0',
    'recorded_at': '2026-07-13T10:00:00Z',
    'exported_at': '2026-07-13T10:01:00Z',
    'base_url': 'http://localhost/test',
    # total_steps 故意省略
    'total_screenshots': 0,
    'steps': [
        {'seq': 1, 'action': 'navigate', 'url': 'http://localhost/test', 'timestamp': '2026-07-13T10:00:01Z'},
        {'seq': 2, 'action': 'click', 'url': 'http://localhost/test', 'timestamp': '2026-07-13T10:00:02Z',
         'target': {'tag': 'button', 'locators': [{'type': 'id', 'value': 'btn1', 'priority': 1}]}},
        {'seq': 3, 'action': 'click', 'url': 'http://localhost/test', 'timestamp': '2026-07-13T10:00:03Z',
         'target': {'tag': 'a', 'locators': [{'type': 'text', 'value': '提交', 'priority': 3}]}},
    ],
    'screenshots': [],
    'final_page_snapshot': None,
}
r = requests.post(f'{BASE_URL}/api/plugin/recording/upload', json=payload_no_total, timeout=5)
check('缺少 total_steps 上传返回 200', lambda: assert_eq(r.status_code, 200))
body = r.json()
check('缺少 total_steps 返回 ok=true', lambda: assert_eq(body.get('ok'), True))
check('fallback 自动计算 step_count=3', lambda: assert_eq(body.get('step_count'), 3))
print(f'  📋 step_count fallback: {body.get("step_count")} (steps 数组长度: 3)')

# 2. total_steps 为 0 但 steps 有 2 项（不一致场景）
payload_mismatch = {
    'rodski_plugin_version': '1.0.0',
    'recorded_at': '2026-07-13T10:00:00Z',
    'exported_at': '2026-07-13T10:01:00Z',
    'base_url': 'http://localhost/test',
    'total_steps': 0,      # 与 steps 不一致
    'total_screenshots': 0,
    'steps': [
        {'seq': 1, 'action': 'navigate', 'url': 'http://localhost/test', 'timestamp': '2026-07-13T10:00:01Z'},
        {'seq': 2, 'action': 'click',    'url': 'http://localhost/test', 'timestamp': '2026-07-13T10:00:02Z',
         'target': {'tag': 'button', 'locators': [{'type': 'id', 'value': 'btn', 'priority': 1}]}},
    ],
    'screenshots': [],
    'final_page_snapshot': None,
}
r2 = requests.post(f'{BASE_URL}/api/plugin/recording/upload', json=payload_mismatch, timeout=5)
check('total_steps 不一致上传返回 200', lambda: assert_eq(r2.status_code, 200))
body2 = r2.json()
check('不一致时 step_count 以 total_steps 字段为准（0）', lambda: assert_eq(body2.get('step_count'), 0))
print(f'  📋 total_steps 不一致: total_steps=0, 实际 steps={2}, 接口返回 step_count={body2.get("step_count")}')

# 3. 空 steps 列表
payload_empty = {
    'rodski_plugin_version': '1.0.0',
    'recorded_at': '2026-07-13T10:00:00Z',
    'exported_at': '2026-07-13T10:01:00Z',
    'base_url': '',
    'total_screenshots': 0,
    'steps': [],
    'screenshots': [],
    'final_page_snapshot': None,
}
r3 = requests.post(f'{BASE_URL}/api/plugin/recording/upload', json=payload_empty, timeout=5)
check('空 steps 上传返回 200', lambda: assert_eq(r3.status_code, 200))
check('空 steps step_count=0', lambda: assert_eq(r3.json().get('step_count'), 0))

if errors: print(f'\n❌ {len(errors)} 个检查失败', file=sys.stderr); sys.exit(1)
print('\n✅ recording/upload 字段 fallback 验证通过')
