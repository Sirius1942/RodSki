const { test } = require('node:test');
const assert = require('node:assert/strict');
const { JSDOM } = require('jsdom');
const fs = require('fs');
const path = require('path');

const DEMO_XML = fs.readFileSync(
  path.join(__dirname, '../../../rodski-demo/DEMO/demo_full/case/demo_case.xml'), 'utf8'
);

function createDOM(xml) {
  const dom = new JSDOM(`<!DOCTYPE html><html><body>
    <span id="filepath"></span>
    <table><tbody id="tbody"></tbody></table>
  </body></html>`, { runScripts: 'dangerously' });

  const { window } = dom;
  // Mock vscode API
  window.acquireVsCodeApi = () => ({ postMessage: () => {} });
  window.__CASE_DATA__ = { xml, filePath: '/test/demo_case.xml' };

  // Inject case.js
  const script = fs.readFileSync(path.join(__dirname, '../../src/webview/case.js'), 'utf8');
  window.eval(script);
  return window;
}

test('解析 XML 后渲染用例列表', () => {
  const window = createDOM(DEMO_XML);
  const rows = window.document.querySelectorAll('tr.case-row');
  assert.ok(rows.length > 0, `应有用例行，实际: ${rows.length}`);
});

test('用例行包含 ID 和 Title', () => {
  const window = createDOM(DEMO_XML);
  const firstRow = window.document.querySelector('tr.case-row td:nth-child(2)');
  assert.ok(firstRow.textContent.includes('TC001'), '第一行应包含 TC001');
});

test('execute=是 显示 ✓，execute=否 显示 ✗', () => {
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="C1" title="T1" component_type="界面"><test_case/></case>
  <case execute="否" id="C2" title="T2" component_type="界面"><test_case/></case>
</cases>`;
  const window = createDOM(xml);
  const toggles = window.document.querySelectorAll('.toggle');
  assert.equal(toggles[0].textContent, '✓');
  assert.equal(toggles[1].textContent, '✗');
});

test('buildStepsHtml 正确渲染步骤', () => {
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="C1" title="T1" component_type="界面">
    <test_case>
      <test_step action="navigate" model="" data="http://localhost"/>
      <test_step action="type" model="LoginForm" data="L001"/>
    </test_case>
  </case>
</cases>`;
  const window = createDOM(xml);
  const stepsRow = window.document.getElementById('steps-0');
  assert.ok(stepsRow.innerHTML.includes('navigate'), '应包含 navigate');
  assert.ok(stepsRow.innerHTML.includes('LoginForm'), '应包含 LoginForm');
});

test('toggleExecute 切换 execute 属性', () => {
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="C1" title="T1" component_type="界面"><test_case/></case>
</cases>`;
  const window = createDOM(xml);
  const toggle = window.document.querySelector('.toggle');
  assert.equal(toggle.textContent, '✓');

  // simulate click
  const event = new window.MouseEvent('click', { bubbles: true });
  Object.defineProperty(event, 'stopPropagation', { value: () => {} });
  window.toggleExecute(event, 0);

  const toggleAfter = window.document.querySelector('.toggle');
  assert.equal(toggleAfter.textContent, '✗', 'execute 应切换为否');
});
