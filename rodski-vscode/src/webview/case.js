const vscode = acquireVsCodeApi();
let xmlDoc = null;
let currentFilePath = '';

function loadXml(xml, filePath) {
  currentFilePath = filePath;
  document.getElementById('filepath').textContent = filePath;
  xmlDoc = new DOMParser().parseFromString(xml, 'text/xml');
  render();
}

// 从内联 JSON 加载（无时序问题）
if (window.__CASE_DATA__) {
  loadXml(window.__CASE_DATA__.xml, window.__CASE_DATA__.filePath);
}

window.addEventListener('message', e => {
  const msg = e.data;
  if (msg.command === 'loadXml') loadXml(msg.xml, msg.filePath);
  if (msg.command === 'appendLog') appendLog(msg.text);
});

vscode.postMessage({ command: 'ready' });

function render() {
  const tbody = document.getElementById('tbody');
  tbody.innerHTML = '';
  const cases = Array.from(xmlDoc.getElementsByTagName('case'));
  cases.forEach((c, i) => {
    const id = c.getAttribute('id') || '';
    const title = c.getAttribute('title') || '';
    const priority = c.getAttribute('priority') || '';
    const execute = c.getAttribute('execute');
    const isOn = execute === '是';

    const tr = document.createElement('tr');
    tr.className = 'case-row';
    tr.dataset.index = i;
    tr.innerHTML = `
      <td><span class="toggle ${isOn ? 'on' : 'off'}" data-index="${i}" onclick="toggleExecute(event, ${i})">${isOn ? '✓' : '✗'}</span></td>
      <td><span class="arrow" id="arrow-${i}">▸</span> <b>${id}</b>  ${title}</td>
      <td>${priority}</td>
      <td><button onclick="runCase(event, '${id}')">▶ Run</button></td>
    `;
    tr.addEventListener('click', (e) => {
      if (e.target.classList.contains('toggle') || e.target.tagName === 'BUTTON') return;
      toggleSteps(i, c);
    });
    tbody.appendChild(tr);

    const stepsRow = document.createElement('tr');
    stepsRow.className = 'steps-row';
    stepsRow.id = `steps-${i}`;
    stepsRow.style.display = 'none';
    stepsRow.innerHTML = `<td colspan="4">${buildStepsHtml(c)}</td>`;
    tbody.appendChild(stepsRow);
  });
}

function buildStepsHtml(caseEl) {
  const steps = Array.from(caseEl.getElementsByTagName('test_step'));
  if (!steps.length) return '<em>无步骤</em>';
  const rows = steps.map(s => {
    const action = s.getAttribute('action') || '';
    const model = s.getAttribute('model') || '';
    const data = s.getAttribute('data') || '';
    return `<tr><td style="color:var(--vscode-terminal-ansiCyan)">${action}</td><td>${model}</td><td>${data}</td></tr>`;
  }).join('');
  return `<table class="steps-table"><thead><tr><td>action</td><td>model</td><td>data</td></tr></thead><tbody>${rows}</tbody></table>`;
}

function toggleSteps(i, caseEl) {
  const row = document.getElementById(`steps-${i}`);
  const arrow = document.getElementById(`arrow-${i}`);
  if (row.style.display === 'none') {
    row.style.display = '';
    arrow.textContent = '▾';
  } else {
    row.style.display = 'none';
    arrow.textContent = '▸';
  }
}

function toggleExecute(event, i) {
  event.stopPropagation();
  const cases = Array.from(xmlDoc.getElementsByTagName('case'));
  const c = cases[i];
  const current = c.getAttribute('execute');
  c.setAttribute('execute', current === '是' ? '否' : '是');
  saveXml();
  render();
}

function saveXml() {
  const xml = new XMLSerializer().serializeToString(xmlDoc);
  vscode.postMessage({ command: 'saveXml', xml });
}

function runCase(event, caseId) {
  event.stopPropagation();
  clearLog();
  vscode.postMessage({ command: 'runCase', caseId });
}

function runAll() {
  vscode.postMessage({ command: 'runCase', caseId: '' });
  clearLog();
}

function appendLog(text) {
  const el = document.getElementById('log-content');
  el.textContent += text;
  el.scrollTop = el.scrollHeight;
}

function clearLog() {
  document.getElementById('log-content').textContent = '';
}
