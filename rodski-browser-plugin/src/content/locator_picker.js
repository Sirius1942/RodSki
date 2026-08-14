/**
 * 定位器采集 - 悬停/右键元素采集 RodSki <location> 候选
 */

(function() {
  if (window.__rodski_locator_picker_loaded) return;
  window.__rodski_locator_picker_loaded = true;

  let tooltipEl = null;
  let lastTarget = null;
  let pickerActive = false;

  // ---- 工具提示 UI ----

  function createTooltip() {
    const el = document.createElement('div');
    el.id = '__rodski_locator_tooltip';
    el.style.cssText = `
      position: fixed;
      z-index: 2147483647;
      background: #1a1a2e;
      color: #e0e0e0;
      border: 1.5px solid #4a90d9;
      border-radius: 8px;
      padding: 10px 14px;
      font-family: 'SF Mono', 'Fira Code', monospace;
      font-size: 12px;
      line-height: 1.6;
      max-width: 420px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.5);
      pointer-events: none;
      display: none;
    `;
    document.body.appendChild(el);
    return el;
  }

  function showTooltip(e, el) {
    if (!tooltipEl) tooltipEl = createTooltip();
    const locators = window.__rodski.getLocators(el);
    if (locators.length === 0) return;

    const best = locators[0];
    const xmlSnippet = window.__rodski.toLocationXml(locators, '???');

    const rows = locators.slice(0, 4).map(l =>
      `<div style="color:#aad4f5">  ${l.type.padEnd(14, ' ')}</div>` +
      `<div style="color:#f8f8f2;margin-left:8px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:320px">${escHtml(l.value)}</div>`
    ).join('');

    tooltipEl.innerHTML = `
      <div style="color:#4a90d9;font-weight:bold;margin-bottom:6px">📍 RodSki 定位器候选</div>
      <div style="color:#888;font-size:11px;margin-bottom:4px">${escHtml(window.__rodski.describeElement(el))}</div>
      <div style="display:grid;grid-template-columns:auto 1fr;gap:2px 4px;margin:4px 0">${rows}</div>
      <div style="border-top:1px solid #333;margin:6px 0;padding-top:6px;color:#7ec8a4;font-size:11px">
        按 <kbd style="background:#333;padding:1px 4px;border-radius:3px">Alt+C</kbd> 复制到剪贴板
      </div>
    `;
    tooltipEl.style.display = 'block';

    // 定位：避免超出视口
    const x = Math.min(e.clientX + 14, window.innerWidth - 440);
    const y = Math.min(e.clientY + 14, window.innerHeight - 200);
    tooltipEl.style.left = `${x}px`;
    tooltipEl.style.top = `${y}px`;
  }

  function hideTooltip() {
    if (tooltipEl) tooltipEl.style.display = 'none';
  }

  function escHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  // ---- 高亮框 ----

  let highlightFrame = null;
  function showHighlight(el) {
    if (!pickerActive) return;
    if (!highlightFrame) {
      highlightFrame = document.createElement('div');
      highlightFrame.id = '__rodski_hover_highlight';
      highlightFrame.style.cssText = `
        position: fixed;
        z-index: 2147483646;
        pointer-events: none;
        border: 2px solid #4a90d9;
        background: rgba(74,144,217,0.08);
        border-radius: 3px;
        transition: all 0.1s ease;
        box-shadow: 0 0 0 1px rgba(74,144,217,0.3);
      `;
      document.body.appendChild(highlightFrame);
    }
    const rect = el.getBoundingClientRect();
    Object.assign(highlightFrame.style, {
      display: 'block',
      left: `${rect.left}px`,
      top: `${rect.top}px`,
      width: `${rect.width}px`,
      height: `${rect.height}px`,
    });
  }

  function hideHighlight() {
    if (highlightFrame) highlightFrame.style.display = 'none';
  }

  // ---- 事件处理 ----

  function onMouseMove(e) {
    if (!pickerActive) return;
    const target = e.target;
    if (!target || target === tooltipEl || target === highlightFrame) return;
    if (target.id === '__rodski_locator_tooltip' || target.id === '__rodski_hover_highlight') return;
    lastTarget = target;
    showHighlight(target);
    showTooltip(e, target);
  }

  function onMouseLeave() {
    hideTooltip();
    hideHighlight();
  }

  function onKeyDown(e) {
    // Alt+C: 复制最优定位器
    if (e.altKey && e.key === 'c' && lastTarget) {
      const locators = window.__rodski.getLocators(lastTarget);
      const xml = window.__rodski.toLocationXml(locators, '???');
      navigator.clipboard.writeText(xml).then(() => {
        showCopyFeedback('✅ 已复制 <location> 到剪贴板');
      }).catch(() => {
        // fallback
        const ta = document.createElement('textarea');
        ta.value = xml;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        showCopyFeedback('✅ 已复制');
      });
    }
    // Escape: 退出 picker 模式
    if (e.key === 'Escape') {
      deactivatePicker();
    }
  }

  function showCopyFeedback(msg) {
    const fb = document.createElement('div');
    fb.style.cssText = `
      position:fixed;top:20px;right:20px;z-index:2147483647;
      background:#1e7e34;color:#fff;padding:10px 18px;
      border-radius:6px;font-family:sans-serif;font-size:14px;
      box-shadow:0 4px 12px rgba(0,0,0,0.3);
    `;
    fb.textContent = msg;
    document.body.appendChild(fb);
    setTimeout(() => fb.remove(), 2000);
  }

  // ---- 公开接口 ----

  function activatePicker() {
    pickerActive = true;
    document.addEventListener('mousemove', onMouseMove, true);
    document.addEventListener('mouseleave', onMouseLeave, true);
    document.addEventListener('keydown', onKeyDown, true);
    document.body.style.cursor = 'crosshair';
    console.log('[RodSki] 定位器 Picker 已激活（Esc 退出，Alt+C 复制）');
  }

  function deactivatePicker() {
    pickerActive = false;
    document.removeEventListener('mousemove', onMouseMove, true);
    document.removeEventListener('mouseleave', onMouseLeave, true);
    document.removeEventListener('keydown', onKeyDown, true);
    document.body.style.cursor = '';
    hideTooltip();
    hideHighlight();
    chrome.runtime.sendMessage({ type: 'PICKER_DEACTIVATED' });
    console.log('[RodSki] 定位器 Picker 已停用');
  }

  // 获取当前页面所有可交互元素的摘要（供 AI 使用）
  function getPageSnapshot() {
    const selectors = 'input, button, a, select, textarea, [role="button"], [role="link"], [role="tab"], [onclick]';
    const elements = Array.from(document.querySelectorAll(selectors)).slice(0, 100);
    return {
      url: location.href,
      title: document.title,
      timestamp: new Date().toISOString(),
      interactive_elements: elements.map(el => {
        const locators = window.__rodski.getLocators(el);
        return {
          tag: el.tagName.toLowerCase(),
          id: el.id || null,
          name: el.name || null,
          type: el.type || null,
          text: el.textContent?.trim().slice(0, 50) || null,
          placeholder: el.placeholder || null,
          href: el.href || null,
          locators: locators.slice(0, 3),
        };
      }),
    };
  }

  // 监听 service worker 消息
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.type === 'ACTIVATE_PICKER') {
      activatePicker();
      sendResponse({ ok: true });
    } else if (msg.type === 'DEACTIVATE_PICKER') {
      deactivatePicker();
      sendResponse({ ok: true });
    } else if (msg.type === 'GET_PAGE_SNAPSHOT') {
      sendResponse({ ok: true, data: getPageSnapshot() });
    } else if (msg.type === 'GET_LOCATOR_FOR_ELEMENT') {
      // 用于外部触发：点击后返回定位器
      sendResponse({ ok: true });
    }
    return true;
  });

  window.__rodski.activatePicker = activatePicker;
  window.__rodski.deactivatePicker = deactivatePicker;
  window.__rodski.getPageSnapshot = getPageSnapshot;

  console.log('[RodSki] locator_picker.js 已加载');
})();
