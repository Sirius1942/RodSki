#!/usr/bin/env python3
"""TC_BP_009: Plugin API 端到端冒烟测试 - 启动 rodski-web，执行全链路验证"""
import sys, os, time, subprocess, signal

try:
    import requests
except ImportError:
    import subprocess as sp; sp.check_call([sys.executable, '-m', 'pip', 'install', 'requests', '-q'])
    import requests

BASE_URL = 'http://localhost:5002'
WEB_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'web')
)

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

def is_web_running():
    try:
        r = requests.get(f'{BASE_URL}/health', timeout=2)
        return r.status_code == 200
    except Exception:
        return False

# ---- 检查 rodski-web 是否已运行 ----
web_proc = None
web_started_by_us = False

if is_web_running():
    print(f"  ℹ️  rodski-web 已在运行 ({BASE_URL})")
else:
    print(f"  🚀 启动 rodski-web...")
    if not os.path.isdir(WEB_DIR):
        print(f"❌ web 目录不存在: {WEB_DIR}", file=sys.stderr)
        sys.exit(1)
    try:
        web_proc = subprocess.Popen(
            [sys.executable, 'src/app.py'],
            cwd=WEB_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        web_started_by_us = True
        # 等待启动（最多 10s）
        for i in range(20):
            time.sleep(0.5)
            if is_web_running():
                print(f"  ✅ rodski-web 已启动（{(i+1)*0.5:.1f}s）")
                break
        else:
            stdout = web_proc.stdout.read(500).decode('utf-8', errors='replace')
            stderr = web_proc.stderr.read(500).decode('utf-8', errors='replace')
            print(f"❌ rodski-web 启动超时\nstdout: {stdout}\nstderr: {stderr}", file=sys.stderr)
            web_proc.terminate()
            sys.exit(1)
    except Exception as e:
        print(f"❌ 无法启动 rodski-web: {e}", file=sys.stderr)
        sys.exit(1)

try:
    # ---- 全链路冒烟测试 ----

    # 1. 健康检查
    r = requests.get(f'{BASE_URL}/health', timeout=3)
    check('1. 健康检查通过', lambda: assert_eq(r.status_code, 200))

    # 2. 环境列表
    r = requests.get(f'{BASE_URL}/api/plugin/env/list', timeout=3)
    check('2. 获取环境列表', lambda: assert_eq(r.status_code, 200))
    envs = r.json().get('envs', [])
    check('   环境列表不为空', lambda: assert_true(len(envs) > 0))
    print(f"     可用环境: {envs}")

    # 3. 环境切换
    r = requests.post(f'{BASE_URL}/api/plugin/env/switch', json={'env': envs[0]}, timeout=3)
    check(f'3. 切换到环境 [{envs[0]}]', lambda: assert_eq(r.json().get('ok'), True))

    # 4. 上报失败
    r = requests.post(f'{BASE_URL}/api/plugin/report-failure', json={
        'step_id': 'E2E_SMOKE_step_1',
        'element_name': 'smokeTestBtn',
        'model_name': 'SmokeTestPage',
        'locator': {'type': 'id', 'value': 'smokeTestBtn'},
        'error_message': '端到端冒烟测试上报',
        'url': 'http://localhost/smoke',
    }, timeout=3)
    check('4. 上报失败信息', lambda: assert_eq(r.json().get('ok'), True))

    # 5. 拉取失败
    r = requests.get(f'{BASE_URL}/api/plugin/last-failure', timeout=3)
    check('5. 拉取失败信息', lambda: assert_eq(r.json().get('ok'), True))
    failure = r.json().get('failure', {})
    check('   失败信息完整', lambda: assert_eq(failure.get('element_name'), 'smokeTestBtn'))

    # 6. 上传录制素材包
    recording = {
        'rodski_plugin_version': '1.0.0',
        'recorded_at': '2026-07-13T00:00:00Z',
        'exported_at': '2026-07-13T00:01:00Z',
        'base_url': 'http://localhost/smoke',
        'total_steps': 2,
        'total_screenshots': 0,
        'steps': [
            {'seq': 1, 'action': 'navigate', 'url': 'http://localhost/smoke', 'timestamp': '2026-07-13T00:00:01Z'},
            {'seq': 2, 'action': 'click', 'url': 'http://localhost/smoke',
             'target': {'tag': 'button', 'locators': [{'type': 'id', 'value': 'smokeTestBtn', 'priority': 1}]}},
        ],
        'screenshots': [],
        'final_page_snapshot': None,
    }
    r = requests.post(f'{BASE_URL}/api/plugin/recording/upload', json=recording, timeout=5)
    check('6. 上传录制素材包', lambda: assert_eq(r.json().get('ok'), True))
    filename = r.json().get('filename')
    print(f"     已保存: {filename}")

    # 7. 确认素材包可读取
    r = requests.get(f'{BASE_URL}/api/plugin/recording/{filename}', timeout=3)
    check('7. 读取录制素材包', lambda: assert_eq(r.json().get('ok'), True))
    check('   素材包 steps 正确', lambda: assert_eq(r.json()['data']['total_steps'], 2))

    # 8. 清除失败记录
    r = requests.post(f'{BASE_URL}/api/plugin/clear-failure', timeout=3)
    check('8. 清除失败记录', lambda: assert_eq(r.json().get('ok'), True))

    print(f"\n{'✅ 端到端冒烟测试全部通过' if not errors else f'❌ {len(errors)} 个步骤失败'}")

finally:
    if web_started_by_us and web_proc:
        web_proc.terminate()
        print("  🛑 rodski-web 已停止（由测试启动的进程）")

if errors:
    sys.exit(1)
