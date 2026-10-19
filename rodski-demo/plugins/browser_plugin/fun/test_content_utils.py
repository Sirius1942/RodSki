#!/usr/bin/env python3
"""TC_BP_008: 验证 content script 工具函数（Python 模拟 DOM 环境离线测试）
   通过解析 utils.js 源码，验证关键逻辑的正确性（不依赖浏览器）
"""
import os, sys, re

PLUGIN_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'rodski-browser-plugin')
)

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

def assert_true(val, msg=''):
    assert val, msg or f'期望为真，实际 {val!r}'

def assert_in(needle, haystack, msg=''):
    assert needle in haystack, msg or f'{needle!r} 不在 {haystack!r} 中'

# ---- 读取并验证 utils.js ----

utils_path = os.path.join(PLUGIN_ROOT, 'src/content/utils.js')
check('utils.js 文件存在', lambda: assert_true(os.path.exists(utils_path)))

with open(utils_path, encoding='utf-8') as f:
    utils_src = f.read()

# 验证命名空间
check('utils.js 定义 window.__rodski 命名空间', lambda: assert_in('window.__rodski', utils_src))

# 验证 getLocators 函数
check('utils.js 定义 getLocators 函数', lambda: assert_in('window.__rodski.getLocators', utils_src))
check('getLocators 处理 id 定位器', lambda: assert_in("type: 'id'", utils_src))
check('getLocators 处理 xpath 定位器', lambda: assert_in("type: 'xpath'", utils_src))
check('getLocators 处理 text 定位器', lambda: assert_in("type: 'text'", utils_src))
check('getLocators 按 priority 排序', lambda: assert_in('priority', utils_src))

# 验证 toLocationXml 函数
check('utils.js 定义 toLocationXml 函数', lambda: assert_in('window.__rodski.toLocationXml', utils_src))
check('toLocationXml 生成 <element> 标签', lambda: assert_in('<element', utils_src))
check('toLocationXml 生成 <location type=', lambda: assert_in('<location type=', utils_src))

# 验证 getPageSnapshot 函数
check('locator_picker.js 定义 getPageSnapshot', lambda: (
    __import__('builtins').setattr(sys, '_lp',
        open(os.path.join(PLUGIN_ROOT, 'src/content/locator_picker.js'), encoding='utf-8').read()),
    assert_in('getPageSnapshot', sys._lp)
))

# ---- 读取并验证 recorder.js ----

recorder_path = os.path.join(PLUGIN_ROOT, 'src/content/recorder.js')
check('recorder.js 文件存在', lambda: assert_true(os.path.exists(recorder_path)))

with open(recorder_path, encoding='utf-8') as f:
    rec_src = f.read()

check('recorder.js 监听 click 事件', lambda: assert_in("'click'", rec_src))
check('recorder.js 监听 input 事件', lambda: assert_in("'input'", rec_src))
check('recorder.js 不录制 password 字段', lambda: assert_in("password", rec_src))
check('recorder.js 实现防抖逻辑', lambda: assert_in('clearTimeout', rec_src))
check('recorder.js 有 startRecording 函数', lambda: assert_in('startRecording', rec_src))
check('recorder.js 有 stopRecording 函数', lambda: assert_in('stopRecording', rec_src))

# ---- 读取并验证 highlighter.js ----

hl_path = os.path.join(PLUGIN_ROOT, 'src/content/highlighter.js')
check('highlighter.js 文件存在', lambda: assert_true(os.path.exists(hl_path)))

with open(hl_path, encoding='utf-8') as f:
    hl_src = f.read()

check('highlighter.js 有 showDiagnosticPanel 函数', lambda: assert_in('showDiagnosticPanel', hl_src))
check('highlighter.js 支持 success/failure/warning 状态', lambda: (
    assert_in("'success'", hl_src),
    assert_in("'failure'", hl_src),
    assert_in("'warning'", hl_src)
))
check('highlighter.js 有 findSimilarElements 函数', lambda: assert_in('findSimilarElements', hl_src))
check('highlighter.js 支持 SHOW_DIAGNOSTIC 消息', lambda: assert_in('SHOW_DIAGNOSTIC', hl_src))

# ---- 验证 service_worker.js ----

sw_path = os.path.join(PLUGIN_ROOT, 'src/background/service_worker.js')
check('service_worker.js 文件存在', lambda: assert_true(os.path.exists(sw_path)))

with open(sw_path, encoding='utf-8') as f:
    sw_src = f.read()

check('service_worker.js 处理 START_RECORDING', lambda: assert_in('START_RECORDING', sw_src))
check('service_worker.js 处理 STOP_RECORDING', lambda: assert_in('STOP_RECORDING', sw_src))
check('service_worker.js 处理 CAPTURE_SCREENSHOT', lambda: assert_in('CAPTURE_SCREENSHOT', sw_src))
check('service_worker.js 处理 ACTIVATE_PICKER', lambda: assert_in('ACTIVATE_PICKER', sw_src))
check('service_worker.js 处理 FETCH_LAST_FAILURE', lambda: assert_in('FETCH_LAST_FAILURE', sw_src))
check('service_worker.js 处理 SWITCH_ENV', lambda: assert_in('SWITCH_ENV', sw_src))
check('service_worker.js 有 saveRecordingLocally 函数', lambda: assert_in('saveRecordingLocally', sw_src))
check('service_worker.js 有 generateCaseDraft 函数', lambda: assert_in('generateCaseDraft', sw_src))
check('service_worker.js 有 generateModelDraft 函数', lambda: assert_in('generateModelDraft', sw_src))
check('service_worker.js 支持自动截图开关 SET_AUTO_SCREENSHOT', lambda: assert_in('SET_AUTO_SCREENSHOT', sw_src))
check('service_worker.js 支持 EXPORT_NOW 本地下载', lambda: assert_in('EXPORT_NOW', sw_src))
check('service_worker.js 使用 chrome.downloads', lambda: assert_in('chrome.downloads', sw_src))

if errors:
    print(f"\n❌ {len(errors)} 个检查失败", file=sys.stderr)
    sys.exit(1)
print(f"\n✅ 所有 content script / service worker 代码结构验证通过")
