const { test } = require('node:test');
const assert = require('node:assert/strict');
const { JSDOM } = require('jsdom');
const fs = require('fs');
const path = require('path');

function createDOM() {
  const html = fs.readFileSync(path.join(__dirname, '../../src/webview/grid.html'), 'utf8')
    .replace(/\{\{nonce\}\}/g, 'test-nonce')
    .replace('{{gridJsUri}}', '');
  const dom = new JSDOM(html, { runScripts: 'dangerously' });
  const { window } = dom;
  const messages = [];
  window.acquireVsCodeApi = () => ({ postMessage: msg => messages.push(msg) });
  window.confirm = () => true;
  const script = fs.readFileSync(path.join(__dirname, '../../src/webview/grid.js'), 'utf8');
  window.eval(script);
  return { window, messages };
}

test('grid.js sends ready message on init', () => {
  const { messages } = createDOM();
  assert.equal(messages[0].command, 'ready');
});

test('setTables renders sidebar items', () => {
  const { window } = createDOM();
  const event = new window.MessageEvent('message', {
    data: { command: 'setTables', payload: { tables: ['login', 'users'] } }
  });
  window.dispatchEvent(event);
  const items = window.document.querySelectorAll('.table-item');
  assert.equal(items.length, 2);
  assert.equal(items[0].textContent, 'login');
});

test('loadTable renders grid with columns and rows', () => {
  const { window } = createDOM();
  window.dispatchEvent(new window.MessageEvent('message', {
    data: { command: 'loadTable', payload: { tableName: 't1', columns: ['name', 'age'], rows: [['R001', 'Alice', '30']] } }
  }));
  const ths = window.document.querySelectorAll('th');
  assert.ok(ths.length >= 3);
  const tds = window.document.querySelectorAll('tbody td');
  assert.ok(tds[0].textContent === 'R001');
  assert.ok(tds[1].textContent === 'Alice');
});

test('search filters sidebar', () => {
  const { window } = createDOM();
  window.dispatchEvent(new window.MessageEvent('message', {
    data: { command: 'setTables', payload: { tables: ['login', 'users', 'logout'] } }
  }));
  const input = window.document.getElementById('search');
  input.value = 'log';
  input.dispatchEvent(new window.Event('input'));
  const items = window.document.querySelectorAll('.table-item');
  assert.equal(items.length, 2);
});
