"""浏览器异常监控模块 (v0.1)

通过 Playwright add_init_script 注入监控脚本到被测页面，
捕获 JS 异常、console.error、未处理 Promise rejection、
DOM 瞬态告警（Element UI / Ant Design / 通用 Toast）。

适用场景：
- 面向 AI Agent 的测试执行：step 失败时提供精确语义原因
- 无头浏览器与有界面浏览器均兼容（不依赖 Chrome 扩展）
- 零侵入：PlaywrightDriver 懒加载注入，不影响未使用监控的场景

使用方式：
    monitor = BrowserMonitor(driver)
    monitor.inject()                          # 页面加载后自动生效
    monitor.set_step(step_id)                 # 每个 step 前调用
    errors = monitor.collect()                # step 后收集并清空
"""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, List, Dict, Any

if TYPE_CHECKING:
    from rodski.drivers.playwright_driver import PlaywrightDriver

logger = logging.getLogger("rodski")

# 注入到页面 window 的监控脚本（在 document_start 运行）
_MONITOR_JS = r"""
(function() {
  if (window.__rodski_monitor_installed) return;
  window.__rodski_monitor_installed = true;
  window.__rodski_errors = [];
  window.__rodski_step_id = null;

  function _push(obj) {
    window.__rodski_errors.push(Object.assign({ ts: Date.now(), step: window.__rodski_step_id }, obj));
  }

  // JS 运行时异常
  window.addEventListener('error', function(e) {
    _push({ type: 'js_error', message: e.message, source: e.filename, line: e.lineno });
  });

  // 未处理 Promise rejection
  window.addEventListener('unhandledrejection', function(e) {
    _push({ type: 'promise_rejection', message: String(e.reason) });
  });

  // console.error
  var _ce = console.error;
  console.error = function() {
    var msg = Array.prototype.join.call(arguments, ' ');
    _push({ type: 'console_error', message: msg });
    _ce.apply(console, arguments);
  };

  // DOM 瞬态告警（重复名称/校验失败等）
  var _domObs = new MutationObserver(function(mutations) {
    for (var i = 0; i < mutations.length; i++) {
      var added = mutations[i].addedNodes;
      for (var j = 0; j < added.length; j++) {
        var node = added[j];
        if (node.nodeType !== 1) continue;
        var text = (node.innerText || node.textContent || '').trim().slice(0, 300);
        if (!text) continue;
        var cls = (node.className || '').toString();
        var isAlert = (
          /error|warning|danger|重复|已存在|不能|无法|失败|异常|不允许/i.test(text) && (
            /message|alert|toast|notification|tip|error|warning/i.test(cls) ||
            node.getAttribute('role') === 'alert'
          )
        );
        if (isAlert) {
          _push({ type: 'dom_alert', text: text, cls: cls.slice(0, 100) });
        }
      }
    }
  });
  _domObs.observe(document.documentElement, { childList: true, subtree: true });
})();
"""


class BrowserMonitor:
    """PlaywrightDriver 的页面异常监控器。

    生命周期：
        monitor = BrowserMonitor(driver)
        monitor.inject()          # 新页面建立后调用一次（或通过 add_init_script 全局注入）
        monitor.set_step(id)      # 每个 test_step 执行前
        errors = monitor.collect()  # 每个 test_step 执行后；清空缓冲区并返回
    """

    # 错误分类规则（v9.2.3+）
    ERROR_CATEGORIES = {
        'js_error': ['ReferenceError', 'TypeError', 'SyntaxError', 'RangeError'],
        'network_error': ['Failed to fetch', 'NetworkError', 'net::ERR_', 'ECONNREFUSED'],
        'resource_error': ['404', '403', '500', '502', '503', 'Failed to load resource'],
        'security_error': ['CORS', 'Mixed Content', 'CSP', 'blocked by CORS'],
    }

    def __init__(self, driver: "PlaywrightDriver"):
        self._driver = driver
        self._injected = False

    def classify_error(self, error_message: str, error_type: str = "") -> str:
        """将浏览器错误分类（v9.2.3+）

        Args:
            error_message: 错误消息
            error_type: 错误类型（monitor 内部的 type 字段）

        Returns:
            错误类别：js_error, network_error, resource_error, security_error, unknown
        """
        # 先根据 monitor 类型快速分类
        if error_type in ['js_error', 'promise_rejection']:
            return 'js_error'
        elif error_type == 'console_error':
            # console.error 需要进一步分析消息内容
            pass
        elif error_type == 'dom_alert':
            return 'ui_error'

        # 基于消息内容分类
        for category, patterns in self.ERROR_CATEGORIES.items():
            if any(pattern in error_message for pattern in patterns):
                return category

        return 'unknown'

    # ------------------------------------------------------------------
    # 注入
    # ------------------------------------------------------------------

    def inject(self) -> None:
        """将监控脚本注入到当前页面，并注册 add_init_script 使后续导航自动重注入。

        幂等：重复调用无副作用。
        对 page 为 None（浏览器未启动）时静默跳过。
        """
        page = getattr(self._driver, "page", None)
        if page is None:
            return
        try:
            # add_init_script：对本 context 内所有后续页面/导航自动执行
            page.add_init_script(_MONITOR_JS)
            # 立即在当前页面执行（已加载的页面不会自动触发 init_script）
            page.evaluate(_MONITOR_JS)
            self._injected = True
            logger.debug("[BrowserMonitor] 监控脚本已注入")
        except Exception as e:
            logger.debug("[BrowserMonitor] 注入失败（非致命）: %s", e)

    # ------------------------------------------------------------------
    # 步骤标记
    # ------------------------------------------------------------------

    def set_step(self, step_id: str) -> None:
        """在页面设置当前步骤 ID，后续捕获的异常会带上这个标记。"""
        page = getattr(self._driver, "page", None)
        if page is None or not self._injected:
            return
        try:
            page.evaluate("(id) => { window.__rodski_step_id = id; }", step_id)
        except Exception as e:
            logger.debug("[BrowserMonitor] set_step 失败: %s", e)

    # ------------------------------------------------------------------
    # 收集
    # ------------------------------------------------------------------

    def collect(self) -> List[Dict[str, Any]]:
        """读取并清空页面缓冲区，返回本 step 内捕获的异常列表。

        每条记录格式::

            {
                "type":    "dom_alert" | "js_error" | "console_error" | "promise_rejection",
                "category": "js_error" | "network_error" | "resource_error" | "security_error" | "unknown",  # v9.2.3+
                "step":    "<case_id>_<step_index>",   # set_step 时注入
                "ts":      1723507200123,               # 毫秒时间戳
                "text":    "...",                       # dom_alert 专属
                "message": "...",                       # 其余类型
                "source":  "...",                       # js_error 专属（文件名）
                "line":    42,                          # js_error 专属
            }

        返回空列表代表本 step 无异常。
        """
        page = getattr(self._driver, "page", None)
        if page is None or not self._injected:
            return []
        try:
            errors: List[Dict[str, Any]] = page.evaluate(
                "() => { var e = window.__rodski_errors || []; "
                "window.__rodski_errors = []; return e; }"
            )
            # v9.2.3+: 为每个错误添加分类
            if errors:
                for error in errors:
                    error['category'] = self.classify_error(
                        error.get('message') or error.get('text', ''),
                        error.get('type', '')
                    )
                logger.debug("[BrowserMonitor] 本 step 捕获 %d 条异常", len(errors))
            return errors or []
        except Exception as e:
            logger.debug("[BrowserMonitor] collect 失败: %s", e)
            return []
