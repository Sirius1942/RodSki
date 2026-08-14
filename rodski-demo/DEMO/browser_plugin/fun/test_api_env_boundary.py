#!/usr/bin/env python3
"""TC_BP_011: env/switch 切换到不在 env/list 中的任意字符串"""
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

# 1. 切换到合法 env
r = requests.post(f'{BASE_URL}/api/plugin/env/switch', json={'env': 'beta'}, timeout=3)
check('切换到 beta（合法）成功', lambda: assert_eq(r.json().get('ok'), True))

# 2. 切换到任意字符串（不在 list 中）
r2 = requests.post(f'{BASE_URL}/api/plugin/env/switch', json={'env': 'my-custom-env-xyz'}, timeout=3)
check('切换到任意字符串返回 200', lambda: assert_eq(r2.status_code, 200))
check('任意字符串切换后 ok=true', lambda: assert_eq(r2.json().get('ok'), True))
check('任意字符串切换后 env 字段正确', lambda: assert_eq(r2.json().get('env'), 'my-custom-env-xyz'))

# 3. /env/current 反映新值
r3 = requests.get(f'{BASE_URL}/api/plugin/env/current', timeout=3)
check('/env/current 已更新为任意字符串', lambda: assert_eq(r3.json().get('env'), 'my-custom-env-xyz'))
print(f'  📋 当前 env: {r3.json()}')

# 4. 特殊字符（空格、中文、路径分隔符）
for special in ['env with space', '测试环境', 'env/slash', '']:
    r4 = requests.post(f'{BASE_URL}/api/plugin/env/switch', json={'env': special}, timeout=3)
    if special == '':
        check(f'空字符串 env 返回 400', lambda sp=special: assert_eq(
            requests.post(f'{BASE_URL}/api/plugin/env/switch', json={'env': sp}, timeout=3).status_code, 400
        ))
    else:
        check(f'特殊字符 env "{special[:10]}" 不报 500',
              lambda sp=special: assert_true(r4.status_code < 500))

# 恢复
requests.post(f'{BASE_URL}/api/plugin/env/switch', json={'env': 'beta'}, timeout=3)

if errors: print(f'\n❌ {len(errors)} 个检查失败', file=sys.stderr); sys.exit(1)
print('\n✅ env/switch 边界验证通过')
