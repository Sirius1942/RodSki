#!/usr/bin/env python3
"""TC_BP_018: 失败记录幂等性（连续上报3次只保留最新）+ clear-failure 幂等性"""
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

# ---- Part 1: 失败记录幂等性 ----
# 连续上报 3 次，每次不同的 step_id，最终只保留最后一次
for i in range(1, 4):
    r = requests.post(f'{BASE_URL}/api/plugin/report-failure', json={
        'step_id': f'IDEM_STEP_{i:03d}',
        'element_name': f'element_{i}',
        'locator': {'type': 'id', 'value': f'btn_{i}'},
        'error_message': f'第 {i} 次上报',
    }, timeout=3)
    check(f'第 {i} 次上报返回 ok', lambda rr=r: assert_eq(rr.json().get('ok'), True))
    time.sleep(0.05)

r = requests.get(f'{BASE_URL}/api/plugin/last-failure', timeout=3)
failure = r.json().get('failure', {})
check('连续上报后只保留最新（step_id=IDEM_STEP_003）',
      lambda: assert_eq(failure.get('step_id'), 'IDEM_STEP_003'))
check('最新记录 element_name=element_3',
      lambda: assert_eq(failure.get('element_name'), 'element_3'))
print(f'  📋 最新失败记录: step_id={failure.get("step_id")}, element={failure.get("element_name")}')

# ---- Part 2: clear-failure 幂等性 ----
# 第一次清除
r1 = requests.post(f'{BASE_URL}/api/plugin/clear-failure', timeout=3)
check('第一次 clear-failure 返回 ok', lambda: assert_eq(r1.json().get('ok'), True))

# 验证已清空
r_check = requests.get(f'{BASE_URL}/api/plugin/last-failure', timeout=3)
check('清除后 last-failure ok=False', lambda: assert_eq(r_check.json().get('ok'), False))

# 第二次清除（无记录时清除）
r2 = requests.post(f'{BASE_URL}/api/plugin/clear-failure', timeout=3)
check('第二次 clear-failure（空状态）返回 ok（幂等）', lambda: assert_eq(r2.json().get('ok'), True))

# 第三次清除
r3 = requests.post(f'{BASE_URL}/api/plugin/clear-failure', timeout=3)
check('第三次 clear-failure 返回 ok（幂等）', lambda: assert_eq(r3.json().get('ok'), True))

# 验证仍为空
r_check2 = requests.get(f'{BASE_URL}/api/plugin/last-failure', timeout=3)
check('多次 clear 后 last-failure 仍为空', lambda: assert_eq(r_check2.json().get('ok'), False))

if errors: print(f'\n❌ {len(errors)} 个检查失败', file=sys.stderr); sys.exit(1)
print('\n✅ 失败记录幂等性及 clear-failure 幂等性验证通过')
