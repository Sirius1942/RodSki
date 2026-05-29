#!/usr/bin/env python3
"""验证插件文件完整性：CSP 占位符已被替换，webview 文件存在"""
import os, sys, glob

# 支持 Cursor (~/.cursor) 和 VSCode (~/.vscode)
for base in ['~/.vscode/extensions', '~/.cursor/extensions']:
    rodski_dirs = glob.glob(os.path.expanduser(os.path.join(base, 'undefined_publisher.rodski-vscode-*')))
    if rodski_dirs:
        break

if not rodski_dirs:
    print("未找到已安装的 rodski-vscode 插件目录", file=sys.stderr)
    sys.exit(1)

ext_dir = sorted(rodski_dirs)[-1]
print(f"插件目录: {ext_dir}")

for fname in ['case.html', 'case.js', 'grid.html', 'grid.js']:
    fpath = os.path.join(ext_dir, 'src', 'webview', fname)
    if not os.path.exists(fpath):
        print(f"缺少文件: {fpath}", file=sys.stderr)
        sys.exit(1)

case_html = open(os.path.join(ext_dir, 'src', 'webview', 'case.html'), encoding='utf-8').read()
count = case_html.count('{{caseJsUri}}')
print(f"case.html 中 {{{{caseJsUri}}}} 占位符数量: {count}")

panel_js = open(os.path.join(ext_dir, 'out', 'casePanel.js'), encoding='utf-8').read()
if 'replaceAll' not in panel_js:
    print("casePanel.js 未使用 replaceAll，CSP 占位符将无法全部替换", file=sys.stderr)
    sys.exit(1)

print("插件文件完整性验证通过")
