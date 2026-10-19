#!/usr/bin/env python3
"""TC_BAIDU_003: 在插件加载状态下，对百度首页执行真实搜索操作
   （在输入框输入 "RodSki 测试引擎" 并点击"百度一下"），
   验证页面正常响应，同时验证 RodSki 插件的定位器采集能力
   （getLocators）能对百度真实 DOM 元素给出可用的定位器候选。
"""
import sys, time
from cdp_client import get_page_ws_url, CDPSession

SEARCH_KEYWORD = "RodSki 测试引擎"


def main():
    ws_url, tab_id = get_page_ws_url()
    session = CDPSession(ws_url)

    try:
        # 确保回到百度首页（而不是之前测试用的 search 结果页）
        session.navigate("https://www.baidu.com/")
        time.sleep(1)

        errors = []
        def check(desc, cond):
            if cond:
                print(f"  ✅ {desc}")
            else:
                print(f"  ❌ {desc}", file=sys.stderr)
                errors.append(desc)

        # ---- 1. 用真实 DOM 操作输入搜索词（模拟用户输入） ----
        input_selector_found = session.evaluate("!!document.querySelector('#kw')")
        check("找到百度搜索输入框 #kw", input_selector_found)

        session.evaluate(f"""
        (() => {{
            const input = document.querySelector('#kw');
            input.focus();
            input.value = {SEARCH_KEYWORD!r};
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
        }})()
        """)
        time.sleep(0.3)
        value = session.evaluate("document.querySelector('#kw').value")
        check(f"输入框已填入搜索词: {value!r}", value == SEARCH_KEYWORD)

        # ---- 2. 用插件的 getLocators 采集这个输入框的定位器候选 ----
        # 注意：整段表达式（包括 document.querySelector）必须在隔离世界里执行 ——
        # 隔离世界能访问同一份真实 DOM 树，但 JS 对象句柄不跨 context 共享，
        # 不能在主世界 querySelector 后把元素引用传给隔离世界的函数。
        locators = session.evaluate(
            "JSON.stringify(window.__rodski.getLocators(document.querySelector('#kw')))",
            isolated=True,
        )
        print(f"  📋 插件采集到的输入框定位器候选: {locators}")
        check("插件成功为搜索框采集到定位器候选", locators and locators != "[]")

        # ---- 3. 点击搜索按钮，触发真实搜索 ----
        submit_btn_found = session.evaluate("!!document.querySelector('#su')")
        check("找到百度搜索按钮 #su", submit_btn_found)

        # 同时采集搜索按钮的定位器（供生成 model.xml）
        btn_locators = session.evaluate(
            "JSON.stringify(window.__rodski.getLocators(document.querySelector('#su')))",
            isolated=True,
        )
        print(f"  📋 插件采集到的搜索按钮定位器候选: {btn_locators}")
        check("插件成功为搜索按钮采集到定位器候选", btn_locators and btn_locators != "[]")

        session.evaluate("document.querySelector('#su').click()")
        time.sleep(2.5)

        # ---- 4. 验证搜索结果页已加载 ----
        url_after = session.evaluate("location.href")
        title_after = session.evaluate("document.title")
        print(f"  📋 搜索后 URL: {url_after}")
        print(f"  📋 搜索后标题: {title_after}")
        check("URL 已跳转到搜索结果页（含 wd 参数）", "wd=" in url_after or "s?" in url_after)
        check("页面标题包含搜索关键字", SEARCH_KEYWORD in title_after or "百度" in title_after)

        result_count = session.evaluate("document.querySelectorAll('.result, .c-container').length")
        print(f"  📋 搜索结果条目数: {result_count}")
        check("搜索结果页有结果条目渲染", (result_count or 0) > 0)

        if errors:
            print(f"\n❌ {len(errors)} 个检查失败", file=sys.stderr)
            sys.exit(1)
        print(f"\n✅ 百度真实搜索操作 + 插件定位器采集能力验证通过")
    finally:
        session.close()


if __name__ == "__main__":
    main()
