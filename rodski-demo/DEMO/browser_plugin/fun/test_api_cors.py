#!/usr/bin/env python3
"""TC_BP_016: Plugin API 响应头 CORS 验证"""
import sys
try:
    import requests
except ImportError:
    import subprocess; subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'requests', '-q'])
    import requests

BASE_URL = 'http://localhost:5002'
errors = []

def assert_true(v, msg=''): assert v, msg or f'期望为真, 实际 {v!r}'
def assert_in(a, b, msg=''): assert a in b, msg or f'{a!r} 不在 {b!r} 中'
def check(desc, fn):
    try: fn(); print(f'  ✅ {desc}'); return True
    except Exception as e: print(f'  ❌ {desc}: {e}', file=sys.stderr); errors.append(desc); return False

# 1. 模拟 Chrome Extension 发起带 Origin 的跨域请求
ext_origin = 'chrome-extension://abcdefghijklmnopabcdefghijklmnop'
headers = {'Origin': ext_origin}

# /api/* 路由应有 CORS 头；/health 不在 /api/* 下，按设计无 CORS 头
for path, expect_cors in [
    ('/api/plugin/env/list',    True),
    ('/api/plugin/last-failure', True),
    ('/health',                 False),   # 非 /api/*，CORS 不覆盖
]:
    r = requests.get(f'{BASE_URL}{path}', headers=headers, timeout=3)
    cors_header = r.headers.get('Access-Control-Allow-Origin', '')
    if expect_cors:
        check(f'{path} 有 CORS 响应头（/api/* 路由）',
              lambda h=cors_header, p=path: assert_true(h, f'{p} 无 Access-Control-Allow-Origin 头'))
    else:
        check(f'{path} 无 CORS 响应头（非 /api/* 路由，符合预期）',
              lambda h=cors_header, p=path: assert_true(not h, f'{p} 不应有 CORS 头，实际: {h!r}'))
    print(f'  📋 {path} CORS: {cors_header or "(无)"}')

# 2. Preflight OPTIONS 请求
for path in ['/api/plugin/env/switch', '/api/plugin/report-failure', '/api/plugin/recording/upload']:
    r = requests.options(f'{BASE_URL}{path}',
                         headers={
                             'Origin': ext_origin,
                             'Access-Control-Request-Method': 'POST',
                             'Access-Control-Request-Headers': 'Content-Type',
                         }, timeout=3)
    check(f'{path} OPTIONS preflight 不报 500',
          lambda rr=r, p=path: assert_true(rr.status_code < 500, f'{p} 返回 {rr.status_code}'))
    cors = r.headers.get('Access-Control-Allow-Origin', '')
    print(f'  📋 {path} OPTIONS 状态: {r.status_code}, CORS: {cors or "(无)"}')

# 3. 验证 flask-cors 已安装且配置在 rodski-web
import importlib.util
check('flask-cors 已安装', lambda: assert_true(importlib.util.find_spec('flask_cors') is not None))

if errors: print(f'\n❌ {len(errors)} 个检查失败', file=sys.stderr); sys.exit(1)
print('\n✅ CORS 配置验证通过')
