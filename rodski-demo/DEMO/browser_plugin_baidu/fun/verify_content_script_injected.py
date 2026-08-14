#!/usr/bin/env python3
"""TC_BAIDU_002: 验证 RodSki 插件的 content script 已真实注入百度页面
通过 CDP 找到插件的隔离世界（isolated world）execution context，
检查 window.__rodski 命名空间及其挂载的函数是否存在。

注意：content script 运行在隔离世界，与页面主世界的 window 是两个不同对象，
必须在隔离世界的 context 里求值才能看到 __rodski，否则会得到误报的"未注入"。
"""
import sys
from cdp_client import get_page_ws_url, CDPSession


def main():
    ws_url, tab_id = get_page_ws_url()
    print(f"连接到标签页: {tab_id}")
    session = CDPSession(ws_url)

    try:
        # 先触发一次 reload，确保能捕获到 content script 注入时创建的隔离世界 context
        # （如果 CDP 连接是在页面加载完成之后才建立的，之前的 executionContextCreated
        # 事件已经错过，需要重新走一次注入生命周期）
        ctx_id = session.get_isolated_context_id()
        print(f"  📋 RodSki 隔离世界 contextId: {ctx_id}")

        checks = [
            ("window.__rodski 命名空间存在", "typeof window.__rodski !== 'undefined'"),
            ("__rodski.getLocators 函数存在", "typeof window.__rodski?.getLocators === 'function'"),
            ("__rodski.getPageSnapshot 函数存在", "typeof window.__rodski?.getPageSnapshot === 'function'"),
            ("__rodski.startRecording 函数存在", "typeof window.__rodski?.startRecording === 'function'"),
            ("__rodski.stopRecording 函数存在", "typeof window.__rodski?.stopRecording === 'function'"),
            ("__rodski.isRecording 函数存在", "typeof window.__rodski?.isRecording === 'function'"),
            ("__rodski.showDiagnosticPanel 函数存在", "typeof window.__rodski?.showDiagnosticPanel === 'function'"),
            ("recorder.js 加载标记存在", "window.__rodski_recorder_loaded === true"),
            ("locator_picker.js 加载标记存在", "window.__rodski_locator_picker_loaded === true"),
            ("highlighter.js 加载标记存在", "window.__rodski_highlighter_loaded === true"),
        ]

        errors = []
        for desc, expr in checks:
            try:
                val = session.evaluate(expr, isolated=True)
                if val:
                    print(f"  ✅ {desc}")
                else:
                    print(f"  ❌ {desc}: 实际值 {val!r}", file=sys.stderr)
                    errors.append(desc)
            except Exception as e:
                print(f"  ❌ {desc}: 执行异常 {e}", file=sys.stderr)
                errors.append(desc)

        # 页面 URL 校验放在主世界求值（isolated=False，默认）
        url = session.evaluate("location.href")
        print(f"  📋 当前页面: {url}")
        if "baidu.com" not in url:
            errors.append("当前页面不是百度")
            print(f"  ❌ 当前页面不是百度: {url}", file=sys.stderr)
        else:
            print(f"  ✅ 当前页面确认为百度")

        if errors:
            print(f"\n❌ {len(errors)} 个检查失败", file=sys.stderr)
            sys.exit(1)
        print(f"\n✅ content script 已确认真实注入百度页面（{len(checks)} 项检查全部通过，隔离世界 contextId={ctx_id}）")
    finally:
        session.close()


if __name__ == "__main__":
    main()
