#!/usr/bin/env python3
"""TC_BP_002: 验证 manifest.json 合法性（Manifest V3 必要字段）"""
import os, sys, json

PLUGIN_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'rodski-browser-plugin')
)
MANIFEST_PATH = os.path.join(PLUGIN_ROOT, 'manifest.json')

if not os.path.exists(MANIFEST_PATH):
    print(f"❌ manifest.json 不存在: {MANIFEST_PATH}", file=sys.stderr)
    sys.exit(1)

with open(MANIFEST_PATH, encoding='utf-8') as f:
    manifest = json.load(f)

errors = []

# 必要字段检查
def check(field, expected_type=None, expected_value=None, description=''):
    val = manifest.get(field)
    label = description or field
    if val is None:
        errors.append(f"缺少字段: {field}")
        print(f"  ❌ {label}: 缺少", file=sys.stderr)
        return
    if expected_type and not isinstance(val, expected_type):
        errors.append(f"{field} 类型错误")
        print(f"  ❌ {label}: 类型应为 {expected_type.__name__}, 实际为 {type(val).__name__}", file=sys.stderr)
        return
    if expected_value is not None and val != expected_value:
        errors.append(f"{field} 值错误")
        print(f"  ❌ {label}: 期望 {expected_value!r}, 实际 {val!r}", file=sys.stderr)
        return
    print(f"  ✅ {label}: {val!r}")

check('manifest_version', int, 3, 'Manifest 版本（必须为3）')
check('name', str, description='插件名称')
check('version', str, description='插件版本')
check('permissions', list, description='权限列表')
check('background', dict, description='Service Worker 配置')
check('action', dict, description='Popup 配置')
check('content_scripts', list, description='Content Scripts 配置')

# 细项检查
bg = manifest.get('background', {})
if bg.get('service_worker'):
    sw_path = os.path.join(PLUGIN_ROOT, bg['service_worker'])
    if os.path.exists(sw_path):
        print(f"  ✅ service_worker 文件存在: {bg['service_worker']}")
    else:
        errors.append('service_worker 文件不存在')
        print(f"  ❌ service_worker 文件不存在: {bg['service_worker']}", file=sys.stderr)

perms = manifest.get('permissions', [])
required_perms = {'activeTab', 'scripting', 'storage', 'tabs'}
missing_perms = required_perms - set(perms)
if missing_perms:
    errors.append(f"缺少权限: {missing_perms}")
    print(f"  ❌ 缺少必要权限: {missing_perms}", file=sys.stderr)
else:
    print(f"  ✅ 必要权限齐全: {sorted(required_perms)}")

# 检查 content_scripts 是否包含所有必要脚本
cs_list = manifest.get('content_scripts', [])
if cs_list:
    js_files = cs_list[0].get('js', [])
    required_scripts = {'src/content/utils.js', 'src/content/locator_picker.js',
                        'src/content/recorder.js', 'src/content/highlighter.js'}
    missing_scripts = required_scripts - set(js_files)
    if missing_scripts:
        errors.append(f"content_scripts 缺少脚本: {missing_scripts}")
        print(f"  ❌ content_scripts 缺少脚本: {missing_scripts}", file=sys.stderr)
    else:
        print(f"  ✅ content_scripts 包含所有必要脚本")

if errors:
    print(f"\n共 {len(errors)} 个错误", file=sys.stderr)
    sys.exit(1)

print(f"\n✅ manifest.json 验证通过（Manifest V3）")
