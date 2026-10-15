#!/usr/bin/env python3
"""TC_BP_006: 验证 Plugin API 失败诊断接口（上报 + 拉取）"""
import sys
try:
    import requests
except ImportError:
    import subprocess; subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'requests', '-q'])
    import requests

BASE_URL = 'http://localhost:5002'

def assert_eq(a, b, msg=''):
    assert a == b, f'期望 {b!r}, 实际 {a!r}. {msg}'

def assert_true(val, msg=''):
    assert val, msg or f'期望为真, 实际 {val!r}'

errors = []
def check(desc, fn):
    try:
        fn()
        print(f"  ✅ {desc}")
        return True
    except Exception as e:
        print(f"  ❌ {desc}: {e}", file=sys.stderr)
        errors.append(desc)
        return False

# 1. 初始状态：暂无失败记录
r = requests.get(f'{BASE_URL}/api/plugin/last-failure', timeout=3)
check('last-failure 初始返回 200', lambda: assert_eq(r.status_code, 200))
body = r.json()
check('初始状态 ok=True', lambda: assert_eq(body.get('ok'), False))  # ok=False 表示暂无记录

# 2. 上报一个失败
failure_payload = {
    'step_id': 'TC_TEST_001_step_3',
    'element_name': 'loginBtn',
    'model_name': 'LoginPage',
    'locator': {'type': 'id', 'value': 'loginBtn'},
    'tag': 'button',
    'error_message': '元素 loginBtn 在页面中未找到（超时 5s）',
    'url': 'http://localhost:3000/login',
}
r2 = requests.post(f'{BASE_URL}/api/plugin/report-failure', json=failure_payload, timeout=3)
check('report-failure 返回 200', lambda: assert_eq(r2.status_code, 200))
check('report-failure 返回 ok=true', lambda: assert_eq(r2.json().get('ok'), True))

# 3. 拉取失败记录
r3 = requests.get(f'{BASE_URL}/api/plugin/last-failure', timeout=3)
check('上报后 last-failure 返回 200', lambda: assert_eq(r3.status_code, 200))
body3 = r3.json()
check('上报后 ok=true', lambda: assert_eq(body3.get('ok'), True))

failure = body3.get('failure', {})
check('failure 包含 step_id', lambda: assert_eq(failure.get('step_id'), 'TC_TEST_001_step_3'))
check('failure 包含 element_name', lambda: assert_eq(failure.get('element_name'), 'loginBtn'))
check('failure 包含 locator', lambda: assert_true(isinstance(failure.get('locator'), dict)))
check('failure 包含 reported_at 时间戳', lambda: assert_true(isinstance(failure.get('reported_at'), str)))
print(f"  📋 失败记录: step_id={failure.get('step_id')}, element={failure.get('element_name')}")

# 4. 清除失败记录
r4 = requests.post(f'{BASE_URL}/api/plugin/clear-failure', timeout=3)
check('clear-failure 返回 ok', lambda: assert_eq(r4.json().get('ok'), True))

# 5. 确认清除后为空
r5 = requests.get(f'{BASE_URL}/api/plugin/last-failure', timeout=3)
body5 = r5.json()
check('清除后 ok=False（暂无记录）', lambda: assert_eq(body5.get('ok'), False))

if errors:
    print(f"\n❌ {len(errors)} 个检查失败", file=sys.stderr)
    sys.exit(1)
print(f"\n✅ 失败诊断 API 验证通过（上报/拉取/清除 全链路）")
