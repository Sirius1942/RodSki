#!/usr/bin/env python3
"""TC_BP_015: 素材包内部结构深度验证（steps 字段格式、seq 递增、时间戳 ISO8601、locators 格式）"""
import sys, json, re, os
try:
    import requests
except ImportError:
    import subprocess; subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'requests', '-q'])
    import requests

BASE_URL = 'http://localhost:5002'
errors = []
ISO8601_RE = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')
VALID_ACTIONS = {'navigate', 'click', 'input'}

def assert_eq(a, b, msg=''): assert a == b, f'期望 {b!r}, 实际 {a!r}. {msg}'
def assert_true(v, msg=''): assert v, msg or f'期望为真, 实际 {v!r}'
def check(desc, fn):
    try: fn(); print(f'  ✅ {desc}'); return True
    except Exception as e: print(f'  ❌ {desc}: {e}', file=sys.stderr); errors.append(desc); return False

# 上传一个结构完整的素材包
payload = {
    'rodski_plugin_version': '1.0.0',
    'recorded_at': '2026-07-13T10:00:00.000Z',
    'exported_at': '2026-07-13T10:05:30.000Z',
    'base_url': 'http://localhost:3000/login',
    'total_steps': 4,
    'total_screenshots': 2,
    'steps': [
        {'seq': 1, 'action': 'navigate', 'url': 'http://localhost:3000/login', 'timestamp': '2026-07-13T10:00:01.000Z', 'title': '登录'},
        {'seq': 2, 'action': 'input',    'url': 'http://localhost:3000/login', 'timestamp': '2026-07-13T10:00:05.000Z',
         'value': 'admin',
         'target': {'tag': 'input', 'description': '<input#username>', 'locators': [
             {'type': 'id',    'value': 'username', 'priority': 1},
             {'type': 'xpath', 'value': "//input[@id='username']", 'priority': 6},
         ]}},
        {'seq': 3, 'action': 'input',    'url': 'http://localhost:3000/login', 'timestamp': '2026-07-13T10:00:08.000Z',
         'value': '（已过滤-password字段不应出现）',
         'target': {'tag': 'input', 'description': '<input#password>', 'locators': [
             {'type': 'id', 'value': 'password', 'priority': 1},
         ]}},
        {'seq': 4, 'action': 'click',    'url': 'http://localhost:3000/login', 'timestamp': '2026-07-13T10:00:10.000Z',
         'target': {'tag': 'button', 'description': '<button#loginBtn>登录</button>', 'locators': [
             {'type': 'id',   'value': 'loginBtn', 'priority': 1},
             {'type': 'text', 'value': '登录',      'priority': 3},
         ]}},
    ],
    'screenshots': [
        {'label': 'step4', 'seq': 4, 'timestamp': '2026-07-13T10:00:10.000Z', 'url': 'http://localhost:3000/login', 'title': '点击登录'},
        {'label': 'dashboard', 'seq': 4, 'timestamp': '2026-07-13T10:00:15.000Z', 'url': 'http://localhost:3000/dashboard', 'title': 'Dashboard'},
    ],
    'final_page_snapshot': {
        'url': 'http://localhost:3000/dashboard',
        'title': 'Dashboard',
        'timestamp': '2026-07-13T10:00:20.000Z',
        'interactive_elements': [
            {'tag': 'a', 'id': 'logout', 'text': '退出', 'locators': [{'type': 'id', 'value': 'logout', 'priority': 1}]},
        ],
    },
    'ai_hint': '这是一份 RodSki 测试录制素材包。请基于 steps 和 final_page_snapshot 生成符合 RodSki 格式的 case XML。',
}

r = requests.post(f'{BASE_URL}/api/plugin/recording/upload', json=payload, timeout=5)
check('上传结构完整素材包返回 200', lambda: assert_eq(r.status_code, 200))
filename = r.json().get('filename')

# 读取并深度验证
r2 = requests.get(f'{BASE_URL}/api/plugin/recording/{filename}', timeout=3)
check('可读取上传的素材包', lambda: assert_eq(r2.status_code, 200))
data = r2.json().get('data', {})

# ---- 顶层字段验证 ----
check('rodski_plugin_version 格式 x.y.z',
      lambda: assert_true(re.match(r'^\d+\.\d+\.\d+$', data.get('rodski_plugin_version', ''))))
check('recorded_at 为 ISO8601',
      lambda: assert_true(ISO8601_RE.match(data.get('recorded_at', ''))))
check('exported_at 为 ISO8601',
      lambda: assert_true(ISO8601_RE.match(data.get('exported_at', ''))))
check('exported_at >= recorded_at',
      lambda: assert_true(data['exported_at'] >= data['recorded_at']))
check('total_steps = steps 数组长度',
      lambda: assert_eq(data.get('total_steps'), len(data.get('steps', []))))
check('total_screenshots = screenshots 数组长度',
      lambda: assert_eq(data.get('total_screenshots'), len(data.get('screenshots', []))))
check('base_url 非空',
      lambda: assert_true(data.get('base_url')))

# ---- steps 内部结构验证 ----
steps = data.get('steps', [])
check('steps 不为空', lambda: assert_true(len(steps) > 0))

seqs = [s.get('seq') for s in steps]
check('steps.seq 从 1 开始', lambda: assert_eq(seqs[0], 1))
check('steps.seq 递增不重复', lambda: assert_eq(seqs, sorted(set(seqs))))
check('steps 每项 action 合法', lambda: [
    assert_true(s.get('action') in VALID_ACTIONS, f"seq={s.get('seq')} action={s.get('action')!r} 非法")
    for s in steps
])
check('steps 每项有 timestamp（ISO8601）', lambda: [
    assert_true(ISO8601_RE.match(s.get('timestamp', '')), f"seq={s.get('seq')} timestamp 非法")
    for s in steps
])
check('steps 每项有 url', lambda: [
    assert_true(s.get('url'), f"seq={s.get('seq')} url 为空")
    for s in steps
])

# click/input 类步骤必须有 target
for s in steps:
    if s.get('action') in ('click', 'input'):
        check(f"steps seq={s['seq']} ({s['action']}) 有 target",
              lambda ss=s: assert_true(isinstance(ss.get('target'), dict)))
        if isinstance(s.get('target'), dict):
            check(f"steps seq={s['seq']} target.locators 非空",
                  lambda ss=s: assert_true(len(ss['target'].get('locators', [])) > 0))
            for loc in s['target'].get('locators', []):
                check(f"steps seq={s['seq']} locator 有 type 和 value",
                      lambda l=loc: (assert_true(l.get('type')), assert_true(l.get('value') is not None)))

# ---- screenshots 结构验证 ----
for sc in data.get('screenshots', []):
    check(f"screenshot label={sc.get('label')!r} 有 seq",
          lambda s=sc: assert_true(isinstance(s.get('seq'), int)))
    check(f"screenshot label={sc.get('label')!r} 有 timestamp",
          lambda s=sc: assert_true(ISO8601_RE.match(s.get('timestamp', ''))))
    check(f"screenshot label={sc.get('label')!r} 无 dataUrl（已剥离）",
          lambda s=sc: assert_true('dataUrl' not in s))

# ---- final_page_snapshot 结构验证 ----
snap = data.get('final_page_snapshot')
if snap:
    check('final_page_snapshot 有 url', lambda: assert_true(snap.get('url')))
    check('final_page_snapshot 有 title', lambda: assert_true(snap.get('title') is not None))
    check('final_page_snapshot 有 interactive_elements', lambda: assert_true(isinstance(snap.get('interactive_elements'), list)))

print(f'  📋 素材包结构验证完成：{len(steps)} 步, seqs={seqs}')
if errors: print(f'\n❌ {len(errors)} 个检查失败', file=sys.stderr); sys.exit(1)
print('\n✅ 素材包内部结构深度验证通过')
