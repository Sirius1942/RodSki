#!/usr/bin/env python3
"""TC_BP_001: 验证浏览器插件目录结构和必要文件完整性"""
import os, sys

PLUGIN_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'rodski-browser-plugin')
)

REQUIRED_FILES = [
    'manifest.json',
    'src/background/service_worker.js',
    'src/content/utils.js',
    'src/content/locator_picker.js',
    'src/content/recorder.js',
    'src/content/highlighter.js',
    'src/popup/popup.html',
    'src/popup/popup.js',
    'icons/icon16.png',
    'icons/icon32.png',
    'icons/icon48.png',
    'icons/icon128.png',
]

print(f"插件目录: {PLUGIN_ROOT}")

if not os.path.isdir(PLUGIN_ROOT):
    print(f"❌ 插件目录不存在: {PLUGIN_ROOT}", file=sys.stderr)
    sys.exit(1)

errors = []
for rel_path in REQUIRED_FILES:
    full = os.path.join(PLUGIN_ROOT, rel_path)
    if os.path.exists(full):
        size = os.path.getsize(full)
        print(f"  ✅ {rel_path} ({size} bytes)")
    else:
        print(f"  ❌ 缺少文件: {rel_path}", file=sys.stderr)
        errors.append(rel_path)

if errors:
    print(f"\n共缺少 {len(errors)} 个文件", file=sys.stderr)
    sys.exit(1)

print(f"\n✅ 所有 {len(REQUIRED_FILES)} 个必要文件均存在")
