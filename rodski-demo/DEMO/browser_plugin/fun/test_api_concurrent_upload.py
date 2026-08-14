#!/usr/bin/env python3
"""TC_BP_017: 并发上传 5 个录制素材包，验证隔离性（文件名唯一，内容不串改）"""
import sys, time, threading
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

results = {}
lock = threading.Lock()

def upload_worker(worker_id):
    payload = {
        'rodski_plugin_version': '1.0.0',
        'recorded_at': f'2026-07-13T{10+worker_id:02d}:00:00Z',
        'exported_at': f'2026-07-13T{10+worker_id:02d}:01:00Z',
        'base_url': f'http://localhost/worker-{worker_id}',
        'total_steps': worker_id + 1,
        'total_screenshots': 0,
        'steps': [
            {'seq': i+1, 'action': 'click', 'url': f'http://localhost/worker-{worker_id}',
             'timestamp': f'2026-07-13T{10+worker_id:02d}:00:{i+1:02d}Z',
             'target': {'tag': 'button', 'locators': [{'type': 'id', 'value': f'btn-w{worker_id}-s{i}', 'priority': 1}]}}
            for i in range(worker_id + 1)
        ],
        'screenshots': [],
        'final_page_snapshot': None,
        '__worker_id': worker_id,  # 标识字段
    }
    try:
        r = requests.post(f'{BASE_URL}/api/plugin/recording/upload', json=payload, timeout=10)
        with lock:
            results[worker_id] = {'status': r.status_code, 'body': r.json(), 'payload_steps': worker_id + 1}
    except Exception as e:
        with lock:
            results[worker_id] = {'status': -1, 'error': str(e)}

# 并发启动 5 个上传线程
threads = [threading.Thread(target=upload_worker, args=(i,)) for i in range(5)]
for t in threads: t.start()
for t in threads: t.join(timeout=15)

print(f'  📋 并发上传结果:')
for i, res in sorted(results.items()):
    print(f'     worker-{i}: HTTP {res.get("status")}, filename={res.get("body", {}).get("filename")}')

# 验证所有上传成功
check('5 个并发上传全部成功', lambda: assert_true(
    all(r.get('status') == 200 for r in results.values()),
    f'失败的: {[i for i, r in results.items() if r.get("status") != 200]}'
))

# 验证文件名唯一（无覆盖）
filenames = [r['body'].get('filename') for r in results.values() if r.get('status') == 200]
check('5 个并发上传的文件名各不相同', lambda: assert_eq(len(filenames), len(set(filenames)),
    f'文件名有重复: {filenames}'))

# 验证每个文件的 step_count 正确（内容未串改）
for i, res in results.items():
    if res.get('status') == 200:
        expected_steps = res['payload_steps']
        actual_steps = res['body'].get('step_count')
        check(f'worker-{i} step_count={expected_steps}', lambda e=expected_steps, a=actual_steps: assert_eq(a, e))

# 验证文件内容互不串改（读取其中一个验证 base_url 正确）
for i, res in results.items():
    if res.get('status') == 200:
        fn = res['body'].get('filename')
        r2 = requests.get(f'{BASE_URL}/api/plugin/recording/{fn}', timeout=3)
        if r2.status_code == 200:
            data = r2.json().get('data', {})
            check(f'worker-{i} 文件内容 base_url 正确',
                  lambda expected=f'http://localhost/worker-{i}', actual=data.get('base_url'):
                  assert_eq(actual, expected))
        break  # 只验证第一个

if errors: print(f'\n❌ {len(errors)} 个检查失败', file=sys.stderr); sys.exit(1)
print('\n✅ 并发上传隔离性验证通过')
