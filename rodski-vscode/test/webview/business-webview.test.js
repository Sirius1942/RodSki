const { test } = require('node:test');
const assert = require('node:assert/strict');
const { JSDOM } = require('jsdom');
const fs = require('fs');
const path = require('path');

const DEMO_XML = fs.readFileSync(
  path.join(__dirname, '../../../rodski-demo/DEMO/demo_business_model/business/business.xml'),
  'utf8'
);

function createDOM(xml) {
  const html = fs.readFileSync(path.join(__dirname, '../../src/webview/business.html'), 'utf8')
    .replace(/\{\{nonce\}\}/g, 'test-nonce')
    .replace(/<script nonce="test-nonce" src="\{\{businessJsUri\}\}"><\/script>/, '')
    .replace('{{BUSINESS_DATA_JSON}}', JSON.stringify({ xml, filePath: '/test/business/business.xml' }));
  const dom = new JSDOM(html, { runScripts: 'dangerously' });
  const { window } = dom;
  const messages = [];
  window.acquireVsCodeApi = () => ({ postMessage: message => messages.push(message) });
  const script = fs.readFileSync(path.join(__dirname, '../../src/webview/business.js'), 'utf8');
  window.eval(script);
  return { window, messages };
}

test('business webview 初始化并渲染业务模型图', () => {
  const { window, messages } = createDOM(DEMO_XML);
  assert.equal(messages[0].command, 'ready');
  assert.equal(window.document.querySelectorAll('g.business-node').length, 6);
  assert.equal(window.document.querySelectorAll('path.business-edge').length, 5);
  assert.ok(window.document.getElementById('model-meta').textContent.includes('login_flow'));
  assert.ok(window.document.getElementById('model-meta').textContent.includes('input: login_flow'));
});

test('flow 选择高亮对应节点和边，不改变图模型数据', () => {
  const { window } = createDOM(DEMO_XML);
  const flowSelect = window.document.getElementById('flow-select');
  assert.equal(flowSelect.options.length, 4);
  flowSelect.value = 'F_LOGIN_INVALID';
  flowSelect.dispatchEvent(new window.Event('change', { bubbles: true }));

  assert.equal(window.document.querySelectorAll('path.business-edge.active').length, 3);
  assert.equal(window.document.querySelectorAll('g.business-node.active').length, 4);
  assert.equal(window.document.querySelectorAll('g.business-node.dimmed').length, 2);
  assert.match(window.document.getElementById('status').textContent, /F_LOGIN_INVALID/);
  assert.equal(window.parseBusinessXml(DEMO_XML).models[0].flows.length, 3);
});

test('点击节点展示步骤和节点信息', () => {
  const { window } = createDOM(DEMO_XML);
  const submit = window.document.querySelector('g[data-node-id="submit_login"]');
  submit.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  const details = window.document.getElementById('details').textContent;
  assert.match(details, /submit_login/);
  assert.match(details, /send/);
  assert.match(details, /LoginAPI/);
  assert.match(details, /Business\.InputDataID/);
});

test('点击条件边展示来源、目标和条件', () => {
  const { window } = createDOM(DEMO_XML);
  const edge = window.document.querySelector('path[data-source="validate_login"][data-target="error"]');
  edge.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  const details = window.document.getElementById('details').textContent;
  assert.match(details, /validate_login/);
  assert.match(details, /error/);
  assert.match(details, /invalid_credentials/);
  const selectedEdge = window.document.querySelector('path.business-edge.selected');
  assert.ok(selectedEdge, '选中的边应高亮');
});

test('支持同一 XML 中多个业务模型切换', () => {
  const xml = `<?xml version="1.0"?>
<business_models version="0.1">
  <business_model id="a" name="A" version="1">
    <nodes><node id="start" title="Start"/><node id="end" title="End"/></nodes>
    <edges><edge from="start" to="end"/></edges>
    <flows><flow id="F_A" type="basic" path="start&gt;end"/></flows>
  </business_model>
  <business_model id="b" name="B" version="1">
    <nodes><node id="open" title="Open"/><node id="close" title="Close"/></nodes>
    <edges><edge from="open" to="close"/></edges>
    <flows><flow id="F_B" type="alternative" path="open&gt;close"/></flows>
  </business_model>
</business_models>`;
  const { window } = createDOM(xml);
  const select = window.document.getElementById('model-select');
  assert.equal(select.options.length, 2);
  select.value = '1';
  select.dispatchEvent(new window.Event('change', { bubbles: true }));
  assert.equal(window.document.querySelectorAll('g.business-node').length, 2);
  assert.match(window.document.getElementById('model-meta').textContent, /\[b\]/);
  assert.equal(window.document.getElementById('flow-select').options[1].value, 'F_B');
});

test('缩放控制和打开源文件按钮发送正确交互', () => {
  const { window, messages } = createDOM(DEMO_XML);
  window.document.getElementById('zoom-in').click();
  assert.equal(window.document.getElementById('zoom-label').textContent, '115%');
  window.document.getElementById('zoom-out').click();
  assert.equal(window.document.getElementById('zoom-label').textContent, '100%');
  window.document.getElementById('open-source').click();
  assert.equal(messages.at(-1).command, 'openSource');
});

test('非法 XML 显示错误，不抛出到 Webview', () => {
  const { window } = createDOM('<business_models>');
  assert.match(window.document.getElementById('status').textContent, /XML 解析失败|根节点|business_model/);
  assert.equal(window.document.querySelectorAll('g.business-node').length, 0);
});
