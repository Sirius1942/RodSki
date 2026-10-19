#!/usr/bin/env python3
"""TC_BP_024: 验证跨页面录制两个 bug 的修复
   Bug1: 切换页面后动作丢失 -> 需要 webNavigation 监听 + RESUME_RECORDING 恢复机制
   Bug2: 停止保存报错       -> 需要 background 步骤序列为唯一权威来源 + tabId 锁定
"""
import os, sys

PLUGIN_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'rodski-browser-plugin')
)

errors = []
def check(desc, fn):
    try:
        fn(); print(f"  ✅ {desc}"); return True
    except Exception as e:
        print(f"  ❌ {desc}: {e}", file=sys.stderr); errors.append(desc); return False

def assert_true(v, msg=''): assert v, msg or f'期望为真，实际 {v!r}'
def assert_in(a, b, msg=''): assert a in b, msg or f'{a!r} 不在源码中'
def assert_not_in(a, b, msg=''): assert a not in b, msg or f'{a!r} 不应再出现在源码中'

sw_path = os.path.join(PLUGIN_ROOT, 'src/background/service_worker.js')
rec_path = os.path.join(PLUGIN_ROOT, 'src/content/recorder.js')
manifest_path = os.path.join(PLUGIN_ROOT, 'manifest.json')

with open(sw_path, encoding='utf-8') as f:
    sw_src = f.read()
with open(rec_path, encoding='utf-8') as f:
    rec_src = f.read()
with open(manifest_path, encoding='utf-8') as f:
    manifest_src = f.read()

# ---- Bug1 修复验证：导航监听 + 恢复录制机制 ----

check('manifest.json 声明 webNavigation 权限',
      lambda: assert_in('webNavigation', manifest_src))
check('service_worker.js 监听 webNavigation.onCompleted（整页导航）',
      lambda: assert_in('webNavigation.onCompleted', sw_src))
check('service_worker.js 监听 webNavigation.onHistoryStateUpdated（SPA 导航）',
      lambda: assert_in('webNavigation.onHistoryStateUpdated', sw_src))
check('service_worker.js 导航后发送 RESUME_RECORDING 恢复新页面录制状态',
      lambda: assert_in('RESUME_RECORDING', sw_src))
check('recorder.js 监听并处理 RESUME_RECORDING 消息',
      lambda: assert_in('RESUME_RECORDING', rec_src))
check('recorder.js 实现 resumeRecording 函数',
      lambda: assert_in('resumeRecording', rec_src))
check('service_worker.js 导航回调校验 tabId 匹配录制标签页',
      lambda: assert_in('details.tabId !== recordingState.tabId', sw_src))
check('service_worker.js 导航回调校验 frameId===0（只关心主 frame）',
      lambda: assert_in('details.frameId !== 0', sw_src))

# ---- Bug2 修复验证：background 步骤序列唯一权威 + tabId 锁定 ----

check('service_worker.js 定义 addStep 作为步骤序列唯一写入口',
      lambda: assert_in('function addStep', sw_src))
check('recordingState 持有 tabId 字段（锁定录制标签页）',
      lambda: assert_in('tabId: null', sw_src))
check('service_worker.js 定义 sendToRecordingTab 按 tabId 而非动态查询发消息',
      lambda: assert_in('function sendToRecordingTab', sw_src))
check('STOP_RECORDING 不再从 content script payload 覆盖 steps（无 payload.steps 解构）',
      lambda: assert_not_in('const { steps, finalSnapshot } = msg.payload', sw_src))
check('STOP_RECORDING 使用 recordingState.steps 作为唯一数据源',
      lambda: assert_in('saveRecordingLocally(recordingState.steps', sw_src))
check('RECORD_STEP 校验 sender.tab.id 与录制 tabId 一致，拒绝非录制标签页步骤',
      lambda: assert_in('sender.tab.id !== recordingState.tabId', sw_src))
check('recorder.js 不再本地维护权威 steps 数组（无 let steps = []）',
      lambda: assert_not_in('let steps = [];', rec_src))
check('captureTab 校验标签页是否为当前活动标签，避免截错标签页',
      lambda: assert_in('tab.active', sw_src))
check('录制标签页关闭时自动停止并保存，避免状态卡死',
      lambda: assert_in('tabs.onRemoved', sw_src))

if errors:
    print(f"\n❌ {len(errors)} 个检查失败", file=sys.stderr)
    sys.exit(1)
print("\n✅ 跨页面录制 Bug1 / Bug2 修复点全部验证通过")
