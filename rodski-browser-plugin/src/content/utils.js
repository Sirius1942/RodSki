/**
 * 公共工具函数 - 注入到页面，供其他 content scripts 使用
 */

// 命名空间，避免污染页面全局变量
window.__rodski = window.__rodski || {};

/**
 * 生成元素的 XPath
 */
window.__rodski.getXPath = function(el) {
  if (!el || el.nodeType !== Node.ELEMENT_NODE) return '';
  if (el === document.body) return '/html/body';

  let path = '';
  let current = el;
  while (current && current !== document.body) {
    const tag = current.tagName.toLowerCase();
    const siblings = Array.from(current.parentNode?.children || []).filter(c => c.tagName === current.tagName);
    const idx = siblings.indexOf(current) + 1;
    path = `/${tag}${siblings.length > 1 ? `[${idx}]` : ''}` + path;
    current = current.parentNode;
  }
  return '/html/body' + path;
};

/**
 * 获取元素的最优定位器候选列表
 */
window.__rodski.getLocators = function(el) {
  const locators = [];

  // id
  if (el.id) {
    locators.push({ type: 'id', value: el.id, priority: 1 });
  }

  // name
  if (el.name) {
    locators.push({ type: 'name', value: el.name, priority: 2 });
  }

  // text（按钮/链接/标签）
  const text = el.textContent?.trim();
  if (text && text.length > 0 && text.length <= 50 && ['button', 'a', 'label', 'span'].includes(el.tagName.toLowerCase())) {
    locators.push({ type: 'text', value: text, priority: 3 });
  }

  // placeholder
  if (el.placeholder) {
    locators.push({ type: 'placeholder', value: el.placeholder, priority: 4 });
  }

  // data-testid / data-cy / data-qa 等测试友好属性
  const testAttrs = ['data-testid', 'data-cy', 'data-qa', 'data-test', 'aria-label'];
  for (const attr of testAttrs) {
    const val = el.getAttribute(attr);
    if (val) {
      locators.push({ type: attr, value: val, priority: 2 });
    }
  }

  // css class（取最具语义的 class）
  if (el.className && typeof el.className === 'string') {
    const classes = el.className.trim().split(/\s+/).filter(c => c && !c.match(/^(active|selected|focus|hover|disabled)$/));
    if (classes.length > 0) {
      locators.push({ type: 'css', value: `${el.tagName.toLowerCase()}.${classes[0]}`, priority: 5 });
    }
  }

  // xpath（备选）
  const xpath = window.__rodski.getXPath(el);
  if (xpath) {
    locators.push({ type: 'xpath', value: xpath, priority: 6 });
  }

  // 按优先级排序
  locators.sort((a, b) => a.priority - b.priority);
  return locators;
};

/**
 * 生成 RodSki <location> XML 片段
 */
window.__rodski.toLocationXml = function(locators, elementName) {
  if (!locators || locators.length === 0) return '';
  const name = elementName || '???';
  const bestLocator = locators[0];
  return `<element name="${name}" type="web">\n    <location type="${bestLocator.type}">${bestLocator.value}</location>\n</element>`;
};

/**
 * 获取元素简短描述（用于 UI 显示）
 */
window.__rodski.describeElement = function(el) {
  const tag = el.tagName.toLowerCase();
  const id = el.id ? `#${el.id}` : '';
  const cls = el.className && typeof el.className === 'string' ? `.${el.className.trim().split(/\s+/)[0]}` : '';
  const text = el.textContent?.trim().slice(0, 20) || '';
  return `<${tag}${id}${cls}>${text ? text : ''}</${tag}>`;
};

/**
 * 向 service worker 发消息
 */
window.__rodski.sendToBackground = function(type, payload) {
  return chrome.runtime.sendMessage({ type, payload });
};

console.log('[RodSki] utils.js 已加载');
