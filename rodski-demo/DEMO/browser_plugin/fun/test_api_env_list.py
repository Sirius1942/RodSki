#!/usr/bin/env python3
"""TC_BP_004: 验证 Plugin API 环境列表接口"""
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

# GET /api/plugin/env/list
r = requests.get(f'{BASE_URL}/api/plugin/env/list', timeout=3)
check('env/list 返回 200', lambda: assert_eq(r.status_code, 200))

body = r.json()
check('返回 ok=true', lambda: assert_eq(body.get('ok'), True))
check('包含 envs 列表', lambda: assert_eq(isinstance(body.get('envs'), list), True))
check('envs 不为空', lambda: assert_eq(len(body.get('envs', [])) > 0, True))

envs = body.get('envs', [])
print(f"  📋 可用环境: {envs}")
check('envs 每项为字符串', lambda: [assert_eq(isinstance(e, str), True, f'env {e!r} 不是字符串') for e in envs])

if errors:
    print(f"\n❌ {len(errors)} 个检查失败", file=sys.stderr)
    sys.exit(1)
print(f"\n✅ 环境列表 API 验证通过（共 {len(envs)} 个环境）")
