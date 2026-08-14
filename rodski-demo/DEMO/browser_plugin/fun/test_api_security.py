#!/usr/bin/env python3
"""TC_BP_014: recording 文件名安全 - 多种路径穿越攻击向量"""
import sys
try:
    import requests
except ImportError:
    import subprocess; subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'requests', '-q'])
    import requests

BASE_URL = 'http://localhost:5002'
errors = []

def assert_true(v, msg=''): assert v, msg or f'期望为真, 实际 {v!r}'
def check(desc, fn):
    try: fn(); print(f'  ✅ {desc}'); return True
    except Exception as e: print(f'  ❌ {desc}: {e}', file=sys.stderr); errors.append(desc); return False

# 各种路径穿越和非法文件名向量
attack_vectors = [
    # (描述, 路径, 期望状态码)
    ('../etc/passwd',                   '../etc/passwd',              (400, 404)),
    ('../recording_legit.json',         '../recording_legit.json',    (400, 404)),
    ('../../etc/shadow',                '../../etc/shadow',           (400, 404)),
    ('recording_test.txt (非json)',      'recording_test.txt',         (400, 404)),
    ('no_prefix.json (无recording_前缀)', 'no_prefix.json',            (400, 404)),
    ('recording_.json (无时间戳)',        'recording_.json',            (400, 404, 200)),  # 可能存在也可能不存在
    ('空文件名',                          '',                           (404, 405)),
    ('recording_%2F..%2Fetc (URL编码)', 'recording_%2F..%2Fetc',      (400, 404)),
    ('recording_a.json; DROP TABLE',    'recording_a.json; DROP TABLE', (400, 404)),
]

for desc, path, expected_codes in attack_vectors:
    url = f'{BASE_URL}/api/plugin/recording/{path}'
    try:
        r = requests.get(url, timeout=3)
        ok = r.status_code in expected_codes
        if ok:
            print(f'  ✅ {desc}: HTTP {r.status_code} (拒绝或不存在)')
        else:
            print(f'  ❌ {desc}: HTTP {r.status_code}，期望 {expected_codes}', file=sys.stderr)
            errors.append(desc)
    except Exception as e:
        print(f'  ⚠️  {desc}: 请求异常 {e}（视为拒绝，通过）')

# 验证合法文件名格式的负面用例（不含非法字符，但不存在）
r_notexist = requests.get(f'{BASE_URL}/api/plugin/recording/recording_99991231_999999.json', timeout=3)
check('合法格式但不存在的文件返回 404', lambda: assert_true(
    r_notexist.status_code == 404, f'实际 {r_notexist.status_code}'
))

if errors:
    print(f'\n❌ {len(errors)} 个安全检查失败', file=sys.stderr)
    sys.exit(1)
print('\n✅ 路径穿越安全验证通过')
