#!/usr/bin/env python3
"""TC_BP_007: 验证 Plugin API 录制上传接口"""
import sys, json, os
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

# 构造一个最小素材包
recording_payload = {
    'rodski_plugin_version': '1.0.0',
    'recorded_at': '2026-07-13T10:00:00Z',
    'exported_at': '2026-07-13T10:05:00Z',
    'base_url': 'http://localhost:3000',
    'total_steps': 3,
    'total_screenshots': 1,
    'steps': [
        {'seq': 1, 'action': 'navigate', 'url': 'http://localhost:3000/login', 'timestamp': '2026-07-13T10:00:01Z'},
        {'seq': 2, 'action': 'input', 'url': 'http://localhost:3000/login', 'value': 'admin',
         'target': {'tag': 'input', 'description': '<input#username>', 'locators': [{'type': 'id', 'value': 'username', 'priority': 1}]}},
        {'seq': 3, 'action': 'click', 'url': 'http://localhost:3000/login',
         'target': {'tag': 'button', 'description': '<button#loginBtn>', 'locators': [{'type': 'id', 'value': 'loginBtn', 'priority': 1}]}},
    ],
    'screenshots': [
        {'label': 'step3', 'seq': 3, 'timestamp': '2026-07-13T10:00:05Z', 'url': 'http://localhost:3000/login', 'title': '登录页'},
    ],
    'final_page_snapshot': {
        'url': 'http://localhost:3000/dashboard',
        'title': 'Dashboard',
        'interactive_elements': [{'tag': 'a', 'id': 'logout', 'text': '退出', 'locators': [{'type': 'id', 'value': 'logout'}]}],
    },
}

# 1. 上传录制
r = requests.post(f'{BASE_URL}/api/plugin/recording/upload', json=recording_payload, timeout=5)
check('recording/upload 返回 200', lambda: assert_eq(r.status_code, 200))
body = r.json()
check('upload 返回 ok=true', lambda: assert_eq(body.get('ok'), True))
check('upload 返回 filename', lambda: assert_true(body.get('filename', '').startswith('recording_')))
check('upload 返回 step_count=3', lambda: assert_eq(body.get('step_count'), 3))
check('upload 返回 screenshot_count=1', lambda: assert_eq(body.get('screenshot_count'), 1))
check('upload 返回 saved_at', lambda: assert_true(isinstance(body.get('saved_at'), str)))

saved_filename = body.get('filename')
saved_path = body.get('path')
print(f"  📁 已保存: {saved_filename}")

# 2. 验证文件确实写入了磁盘
if saved_path:
    check('文件已写入磁盘', lambda: assert_true(os.path.exists(saved_path), f'文件不存在: {saved_path}'))
    if os.path.exists(saved_path):
        with open(saved_path, encoding='utf-8') as f:
            saved = json.load(f)
        check('文件内容 total_steps 正确', lambda: assert_eq(saved.get('total_steps'), 3))

# 3. 列出录制文件
r2 = requests.get(f'{BASE_URL}/api/plugin/recording/list', timeout=3)
check('recording/list 返回 200', lambda: assert_eq(r2.status_code, 200))
body2 = r2.json()
check('list 返回 ok=true', lambda: assert_eq(body2.get('ok'), True))
recordings = body2.get('recordings', [])
check('recordings 列表不为空', lambda: assert_true(len(recordings) > 0))
filenames = [r['filename'] for r in recordings]
check('刚上传的文件在列表中', lambda: assert_true(saved_filename in filenames, f'{saved_filename} 未在 {filenames} 中'))

# 4. 获取指定录制文件内容
if saved_filename:
    r3 = requests.get(f'{BASE_URL}/api/plugin/recording/{saved_filename}', timeout=3)
    check(f'recording/{saved_filename} 返回 200', lambda: assert_eq(r3.status_code, 200))
    body3 = r3.json()
    check('get recording ok=true', lambda: assert_eq(body3.get('ok'), True))
    data = body3.get('data', {})
    check('get recording 数据完整', lambda: assert_eq(data.get('total_steps'), 3))

# 5. 非法文件名拒绝
r4 = requests.get(f'{BASE_URL}/api/plugin/recording/../../../etc/passwd', timeout=3)
check('路径穿越攻击被拒绝（非 200）', lambda: assert_true(r4.status_code in (400, 404)))

if errors:
    print(f"\n❌ {len(errors)} 个检查失败", file=sys.stderr)
    sys.exit(1)
print(f"\n✅ 录制上传 API 验证通过（上传/列表/获取/安全校验）")
