#!/usr/bin/env python3
"""TC_BP_005: 验证 Plugin API 环境切换接口"""
import sys
try:
    import requests
except ImportError:
    import subprocess; subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'requests', '-q'])
    import requests

BASE_URL = 'http://localhost:5002'

def assert_eq(a, b, msg=''):
    assert a == b, f'期望 {b!r}, 实际 {a!r}. {msg}'

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

# POST /api/plugin/env/switch - 切换到 beta
r = requests.post(f'{BASE_URL}/api/plugin/env/switch', json={'env': 'beta'}, timeout=3)
check('env/switch 返回 200', lambda: assert_eq(r.status_code, 200))

body = r.json()
check('切换返回 ok=true', lambda: assert_eq(body.get('ok'), True))
check('切换后返回 env 字段', lambda: assert_eq(body.get('env'), 'beta'))
check('切换后返回 switched_at 字段', lambda: assert_eq(isinstance(body.get('switched_at'), str), True))

print(f"  📋 切换结果: {body}")

# 验证切换后 current env 已更新
r2 = requests.get(f'{BASE_URL}/api/plugin/env/current', timeout=3)
check('env/current 返回 200', lambda: assert_eq(r2.status_code, 200))
body2 = r2.json()
check('current env 已更新为 beta', lambda: assert_eq(body2.get('env'), 'beta'))

# 切换到 local
r3 = requests.post(f'{BASE_URL}/api/plugin/env/switch', json={'env': 'local'}, timeout=3)
check('切换到 local 返回 ok', lambda: assert_eq(r3.json().get('ok'), True))

# 测试缺少参数的错误处理
r4 = requests.post(f'{BASE_URL}/api/plugin/env/switch', json={}, timeout=3)
check('缺少 env 参数返回 400', lambda: assert_eq(r4.status_code, 400))

if errors:
    print(f"\n❌ {len(errors)} 个检查失败", file=sys.stderr)
    sys.exit(1)
print(f"\n✅ 环境切换 API 验证通过")
