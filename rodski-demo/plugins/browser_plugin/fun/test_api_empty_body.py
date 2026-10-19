#!/usr/bin/env python3
"""TC_BP_010: report-failure 空 body 边界处理"""
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

# 1. 完全空 body（Content-Type: application/json 但 body 为 null）
r = requests.post(f'{BASE_URL}/api/plugin/report-failure', json=None, timeout=3)
check('空 body 不报 500（返回 200）', lambda: assert_eq(r.status_code, 200))
body = r.json()
check('空 body 返回 ok=true', lambda: assert_eq(body.get('ok'), True))

# 2. 验证全 None 字段的记录被正确存储
r2 = requests.get(f'{BASE_URL}/api/plugin/last-failure', timeout=3)
failure = r2.json().get('failure', {})
check('空 body 上报后可读取（ok=true）', lambda: assert_eq(r2.json().get('ok'), True))
check('空 body 上报后 reported_at 存在', lambda: assert_true(isinstance(failure.get('reported_at'), str)))
check('空 body 上报后字段均为 None', lambda: (
    assert_eq(failure.get('step_id'), None),
    assert_eq(failure.get('element_name'), None),
    assert_eq(failure.get('locator'), None),
))
print(f'  📋 空 body 上报的失败记录: {failure}')

# 3. 非 JSON 内容（Content-Type: text/plain）
r3 = requests.post(f'{BASE_URL}/api/plugin/report-failure',
                   data='not json', headers={'Content-Type': 'text/plain'}, timeout=3)
check('非 JSON 内容不报 500', lambda: assert_true(r3.status_code < 500))

# 清理
requests.post(f'{BASE_URL}/api/plugin/clear-failure', timeout=3)

if errors: print(f'\n❌ {len(errors)} 个检查失败', file=sys.stderr); sys.exit(1)
print('\n✅ report-failure 空 body 边界验证通过')
