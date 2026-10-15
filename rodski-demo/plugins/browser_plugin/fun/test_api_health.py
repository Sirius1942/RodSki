#!/usr/bin/env python3
"""TC_BP_003: 验证 rodski-web Plugin API 健康检查端点"""
import sys
try:
    import requests
except ImportError:
    print("requests 未安装，尝试 pip install requests")
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'requests', '-q'])
    import requests

BASE_URL = 'http://localhost:5002'

def check(desc, fn):
    try:
        fn()
        print(f"  ✅ {desc}")
    except AssertionError as e:
        print(f"  ❌ {desc}: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"  ❌ {desc}: {type(e).__name__}: {e}", file=sys.stderr)
        return False
    return True

# rodski-web 需要提前运行
try:
    r = requests.get(f'{BASE_URL}/health', timeout=3)
except Exception as e:
    print(f"❌ 无法连接到 rodski-web ({BASE_URL})，请先启动: cd web && python3 src/app.py", file=sys.stderr)
    print(f"   错误: {e}", file=sys.stderr)
    sys.exit(1)

def assert_equal(a, b, msg=''):
    assert a == b, f'期望 {b!r}, 实际 {a!r}. {msg}'

ok = True
r = requests.get(f'{BASE_URL}/health', timeout=3)
ok &= check('/health 返回 200', lambda: assert_equal(r.status_code, 200))

body = r.json()
ok &= check('/health 返回 status=ok', lambda: assert_equal(body.get('status'), 'ok'))
ok &= check('/health 包含 service 字段', lambda: assert_equal(body.get('service'), 'rodski-web'))

# Plugin API 端点存在性检查
r2 = requests.get(f'{BASE_URL}/api/plugin/env/list', timeout=3)
ok &= check('/api/plugin/env/list 返回 200', lambda: assert_equal(r2.status_code, 200))

body2 = r2.json()
ok &= check('/api/plugin/env/list 返回 ok=true', lambda: assert_equal(body2.get('ok'), True))
ok &= check('/api/plugin/env/list 包含 envs 列表', lambda: (
    assert_equal(isinstance(body2.get('envs'), list), True),
    assert_equal(len(body2['envs']) > 0, True)
))

print(f"\n{'✅ 所有检查通过' if ok else '❌ 部分检查失败'}")
if not ok:
    sys.exit(1)
