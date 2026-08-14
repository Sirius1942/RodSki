#!/usr/bin/env python3
"""轻量 CDP 客户端 - 供 browser_plugin_baidu 各验收脚本复用
通过 websocket 直连 Chrome DevTools Protocol，不依赖 AppleScript / Selenium。

关键点 1（诊断记录）：content script 运行在 Chrome 的"隔离世界"
(isolated world)，与页面主世界的 window 是两个不同对象。CDP 的
Runtime.evaluate 默认只能访问主世界，看不到 content script 挂载在
隔离世界 window 上的 __rodski 命名空间。必须先通过
Runtime.executionContextCreated 事件找到 name 与插件名匹配、
auxData.type === 'isolated' 的 context，再用其 contextId 求值。

关键点 2（本客户端自身的一个坑，记录避免再犯）：早期实现里 send()
在等待命令响应时用简单循环 ws.recv()，会把期间收到的事件通知（比如
executionContextCreated）直接丢弃、不缓存，导致"先发 Page.reload
再去找 context 创建事件"必然漏事件。修复方式：所有收到的消息统一进
一个队列，send() 和事件监听都从队列里取，不直接抢占 socket。
"""
import json, time, base64
import websocket
import urllib.request

DEBUG_PORT = 9333
EXTENSION_NAME = "RodSki 测试助手"


def get_page_ws_url(port=DEBUG_PORT, url_contains="baidu"):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=3) as r:
        tabs = json.loads(r.read())
    for t in tabs:
        if t.get("type") == "page" and url_contains in t.get("url", "").lower():
            return t["webSocketDebuggerUrl"], t["id"]
    raise RuntimeError(f"未找到包含 {url_contains!r} 的页面标签")


class CDPSession:
    """极简 CDP 会话：发命令、收响应，同步阻塞风格。
    所有收到的消息（无论是命令响应还是事件通知）先进 self._pending 队列，
    再按需要分发，避免等响应时把并发到达的事件通知丢掉。
    """

    def __init__(self, ws_url, timeout=10):
        self.ws = websocket.create_connection(ws_url, timeout=timeout)
        self._id = 0
        self._pending = []  # 收到但还没被消费的消息（主要是事件通知）
        self._isolated_context_id = None
        self.send("Page.enable")
        self.send("Runtime.enable")

    def _recv_one(self):
        raw = self.ws.recv()
        return json.loads(raw)

    def send(self, method, params=None):
        self._id += 1
        msg_id = self._id
        self.ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
        while True:
            data = self._recv_one()
            if data.get("id") == msg_id:
                if "error" in data:
                    raise RuntimeError(f"CDP 错误 [{method}]: {data['error']}")
                return data.get("result", {})
            # 不是本次命令的响应，是事件通知（或其它命令的响应），存队列供后续消费
            self._pending.append(data)

    def wait_for_event(self, method_name, predicate=None, timeout=6):
        """从队列里找已缓存的事件，找不到再继续从 socket 读，直到超时"""
        # 先看队列里有没有已经缓存的
        remaining = []
        found = None
        for data in self._pending:
            if found is None and data.get("method") == method_name and (predicate is None or predicate(data)):
                found = data
            else:
                remaining.append(data)
        self._pending = remaining
        if found is not None:
            return found

        old_timeout = self.ws.gettimeout()
        self.ws.settimeout(timeout)
        deadline = time.time() + timeout
        try:
            while time.time() < deadline:
                try:
                    data = self._recv_one()
                except Exception:
                    break
                if data.get("method") == method_name and (predicate is None or predicate(data)):
                    return data
                self._pending.append(data)  # 不是目标事件，留着给别人用
        finally:
            self.ws.settimeout(old_timeout)
        return None

    def get_isolated_context_id(self, reload_if_missing=True):
        """获取 RodSki content script 的隔离世界 contextId，缓存复用。
        如果尚未观察到该 context（比如连接建立前页面已经加载完，或事件
        在建立监听前就已发生），触发一次 reload 重新走完整注入生命周期。
        """
        if self._isolated_context_id is not None:
            return self._isolated_context_id

        def is_rodski_isolated(data):
            ctx = data["params"]["context"]
            return ctx.get("name") == EXTENSION_NAME and ctx.get("auxData", {}).get("type") == "isolated"

        evt = self.wait_for_event("Runtime.executionContextCreated", is_rodski_isolated, timeout=1.5)
        if evt is None and reload_if_missing:
            self.send("Page.reload")
            evt = self.wait_for_event("Runtime.executionContextCreated", is_rodski_isolated, timeout=8)
        if evt is None:
            raise RuntimeError("未能观察到 RodSki content script 的隔离世界 context，插件可能未注入此页面")
        self._isolated_context_id = evt["params"]["context"]["id"]
        return self._isolated_context_id

    def evaluate(self, expression, await_promise=False, return_by_value=True, isolated=False):
        """isolated=True 时在 content script 的隔离世界里求值（用于检查 window.__rodski）；
        isolated=False（默认）在页面主世界求值（用于检查 location.href 等页面自身状态）。
        """
        params = {
            "expression": expression,
            "awaitPromise": await_promise,
            "returnByValue": return_by_value,
        }
        if isolated:
            params["contextId"] = self.get_isolated_context_id()
        result = self.send("Runtime.evaluate", params)
        if result.get("exceptionDetails"):
            raise RuntimeError(f"JS 执行异常: {result['exceptionDetails']}")
        return result.get("result", {}).get("value")

    def screenshot_png_bytes(self):
        result = self.send("Page.captureScreenshot", {"format": "png"})
        return base64.b64decode(result["data"])

    def navigate(self, url):
        self.send("Page.navigate", {"url": url})
        time.sleep(1.5)
        self._isolated_context_id = None
        # 导航会销毁旧页面的所有 execution context，_pending 队列里任何残留的
        # 旧 Runtime.executionContextCreated 事件都已失效（对应 context 已销毁）。
        # 不清空的话 get_isolated_context_id() 可能优先命中这些死 context id，
        # 导致后续 Runtime.evaluate 报 "Cannot find context with specified id"。
        self._pending = [d for d in self._pending if d.get("method") != "Runtime.executionContextCreated"]

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass
