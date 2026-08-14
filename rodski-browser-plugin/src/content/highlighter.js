/**
 * 失败诊断高亮 - 在页面上标注测试失败的元素
 */

(function() {
  if (window.__rodski_highlighter_loaded) return;
  window.__rodski_highlighter_loaded = true;

  const overlays = [];
  let diagnosticPanel = null;

  function clearOverlays() {
    overlays.forEach(el => el.remove());
    overlays.length = 0;
    if (diagnosticPanel) {
      diagnosticPanel.remove();
      diagnosticPanel = null;
    }
  }

  /**
   * 根据定位器找到页面元素
   */
  function findElement(locator) {
    try {
      if (locator.type === 'id') return document.getElementById(locator.value);
      if (locator.type === 'xpath') {
        const r = document.evaluate(locator.value, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
        return r.singleNodeValue;
      }
      if (locator.type === 'css') return document.querySelector(locator.value);
      if (locator.type === 'name') return document.querySelector(`[name="${CSS.escape(locator.value)}"]`);
      if (locator.type === 'text') {
        // 按文本内容查找
        const all = document.querySelectorAll('button, a, label, span, div');
        for (const el of all) {
          if (el.textContent?.trim() === locator.value) return el;
        }
      }
    } catch (e) {}
    return null;
  }

  /**
   * 在元素上绘制高亮框
   * @param {Element} el
   * @param {'success'|'failure'|'warning'} status
   * @param {string} label
   */
  function highlightElement(el, status, label) {
    if (!el) return;
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0) return;

    const colors = {
      success: { border: '#27ae60', bg: 'rgba(39,174,96,0.1)', badge: '#27ae60' },
      failure: { border: '#e74c3c', bg: 'rgba(231,76,60,0.12)', badge: '#e74c3c' },
      warning: { border: '#f39c12', bg: 'rgba(243,156,18,0.1)', badge: '#f39c12' },
    };
    const c = colors[status] || colors.failure;

    const overlay = document.createElement('div');
    overlay.style.cssText = `
      position: fixed;
      left: ${rect.left - 2}px;
      top: ${rect.top - 2}px;
      width: ${rect.width + 4}px;
      height: ${rect.height + 4}px;
      border: 2px solid ${c.border};
      background: ${c.bg};
      z-index: 2147483640;
      pointer-events: none;
      border-radius: 3px;
    `;

    if (label) {
      const badge = document.createElement('div');
      badge.style.cssText = `
        position: absolute;
        top: -20px;
        left: 0;
        background: ${c.badge};
        color: #fff;
        font-size: 10px;
        font-family: 'SF Mono', monospace;
        padding: 2px 6px;
        border-radius: 3px 3px 0 0;
        white-space: nowrap;
        max-width: 200px;
        overflow: hidden;
        text-overflow: ellipsis;
      `;
      badge.textContent = label;
      overlay.appendChild(badge);
    }

    document.body.appendChild(overlay);
    overlays.push(overlay);
    return overlay;
  }

  /**
   * 寻找页面中与失败定位器"相近"的元素
   */
  function findSimilarElements(locator) {
    const candidates = [];
    const tag = locator.tag || '*';

    if (locator.type === 'id') {
      // 部分匹配 id
      const partial = locator.value.toLowerCase();
      document.querySelectorAll(`[id]`).forEach(el => {
        const id = el.id.toLowerCase();
        if (id.includes(partial) || partial.includes(id)) {
          candidates.push({ el, similarity: 'id 相近', suggestion: { type: 'id', value: el.id } });
        }
      });
    } else if (locator.type === 'text') {
      // 部分文本匹配
      const partial = locator.value.toLowerCase();
      document.querySelectorAll('button, a, label').forEach(el => {
        const text = el.textContent?.trim().toLowerCase();
        if (text && (text.includes(partial) || partial.includes(text))) {
          candidates.push({ el, similarity: '文本相近', suggestion: { type: 'text', value: el.textContent?.trim() } });
        }
      });
    }

    return candidates.slice(0, 3);
  }

  /**
   * 显示失败诊断面板
   */
  function showDiagnosticPanel(failureInfo) {
    clearOverlays();

    const { locator, element_name, model_name, step_id } = failureInfo;

    // 尝试找到失败元素
    const foundEl = locator ? findElement(locator) : null;

    if (foundEl) {
      // 元素存在但可能有其他问题
      highlightElement(foundEl, 'warning', `⚠️ ${element_name || '元素'}`);
    } else if (locator) {
      // 完全找不到 - 找相近元素
      const similars = findSimilarElements(locator);
      similars.forEach(({ el, similarity, suggestion }) => {
        highlightElement(el, 'warning', `${similarity}: ${suggestion.value}`);
      });
    }

    // 创建诊断面板
    diagnosticPanel = document.createElement('div');
    diagnosticPanel.id = '__rodski_diagnostic_panel';
    diagnosticPanel.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      z-index: 2147483647;
      background: #1a1a2e;
      border: 1.5px solid #e74c3c;
      border-radius: 10px;
      padding: 14px 16px;
      font-family: 'SF Mono', monospace;
      font-size: 12px;
      color: #e0e0e0;
      max-width: 380px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.5);
      line-height: 1.6;
    `;

    const similars = locator ? findSimilarElements(locator) : [];
    const similarHtml = similars.length > 0
      ? `<div style="margin-top:8px;color:#888;font-size:11px">页面中相近元素：</div>` +
        similars.map(s => `<div style="color:#f39c12;margin-left:8px">• ${s.similarity}: <span style="color:#f8f8f2">${s.suggestion.value}</span></div>`).join('')
      : '<div style="color:#888;font-size:11px;margin-top:4px">（未找到相近元素）</div>';

    diagnosticPanel.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
        <span style="color:#e74c3c;font-weight:bold">❌ 元素定位失败</span>
        <button id="__rodski_diag_close" style="
          background:transparent;border:1px solid #555;color:#888;
          padding:2px 6px;border-radius:4px;cursor:pointer;font-size:10px;
        ">✕</button>
      </div>
      ${step_id ? `<div style="color:#888;font-size:11px">步骤: ${step_id}</div>` : ''}
      ${model_name ? `<div style="color:#888;font-size:11px">模型: ${model_name} → ${element_name || ''}</div>` : ''}
      ${locator ? `
        <div style="margin-top:6px">
          <span style="color:#888">定位器: </span>
          <span style="color:#aad4f5">${locator.type}</span>=<span style="color:#f8f8f2">"${locator.value}"</span>
        </div>
        <div style="color:${foundEl ? '#f39c12' : '#e74c3c'};margin-top:4px;font-size:11px">
          ${foundEl ? '⚠️ 元素存在但可能有问题' : '🔍 当前页面未找到此元素'}
        </div>
        ${similarHtml}
      ` : ''}
      <div style="margin-top:10px;border-top:1px solid #333;padding-top:8px;display:flex;gap:8px">
        <button id="__rodski_diag_copy" style="
          background:#2c3e50;border:1px solid #4a90d9;color:#4a90d9;
          padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px;
        ">复制修复建议</button>
        <button id="__rodski_diag_clear" style="
          background:#2c3e50;border:1px solid #555;color:#888;
          padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px;
        ">清除高亮</button>
      </div>
    `;

    document.body.appendChild(diagnosticPanel);

    document.getElementById('__rodski_diag_close')?.addEventListener('click', clearOverlays);
    document.getElementById('__rodski_diag_clear')?.addEventListener('click', clearOverlays);
    document.getElementById('__rodski_diag_copy')?.addEventListener('click', () => {
      const suggestion = similars[0]?.suggestion;
      if (suggestion) {
        const xml = window.__rodski.toLocationXml([suggestion], element_name || '???');
        navigator.clipboard.writeText(xml).catch(() => {});
        showCopyFeedback('✅ 已复制修复建议');
      }
    });
  }

  function showCopyFeedback(msg) {
    const fb = document.createElement('div');
    fb.style.cssText = `
      position:fixed;top:20px;left:50%;transform:translateX(-50%);
      z-index:2147483647;background:#1e7e34;color:#fff;
      padding:8px 16px;border-radius:6px;font-family:sans-serif;font-size:13px;
    `;
    fb.textContent = msg;
    document.body.appendChild(fb);
    setTimeout(() => fb.remove(), 2000);
  }

  // ---- 监听 service worker 消息 ----

  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.type === 'SHOW_DIAGNOSTIC') {
      showDiagnosticPanel(msg.payload);
      sendResponse({ ok: true });
    } else if (msg.type === 'CLEAR_HIGHLIGHTS') {
      clearOverlays();
      sendResponse({ ok: true });
    } else if (msg.type === 'HIGHLIGHT_ELEMENTS') {
      clearOverlays();
      const { elements } = msg.payload;
      elements.forEach(({ locator, element_name, status }) => {
        const el = findElement(locator);
        if (el) highlightElement(el, status || 'failure', element_name);
      });
      sendResponse({ ok: true });
    }
    return true;
  });

  window.__rodski.showDiagnosticPanel = showDiagnosticPanel;
  window.__rodski.clearHighlights = clearOverlays;

  console.log('[RodSki] highlighter.js 已加载');
})();
