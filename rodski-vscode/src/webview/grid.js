const vscode = acquireVsCodeApi();
let allTables = [];
let current = { tableName: '', columns: [], rows: [] };

window.addEventListener('message', e => {
  const { command, payload } = e.data;
  if (command === 'setTables') { allTables = payload.tables; renderSidebar(); }
  if (command === 'loadTable') { current = payload; renderGrid(); }
  if (command === 'selectTable') { selectTable(payload.tableName); }
});

// Sidebar
function renderSidebar(filter = '') {
  const list = document.getElementById('table-list');
  const q = filter.toLowerCase();
  list.innerHTML = '';
  allTables.filter(t => t.toLowerCase().includes(q)).forEach(t => {
    const div = document.createElement('div');
    div.className = 'table-item' + (t === current.tableName ? ' active' : '');
    div.textContent = t;
    div.addEventListener('click', () => selectTable(t));
    list.appendChild(div);
  });
}

function selectTable(name) {
  vscode.postMessage({ command: 'selectTable', tableName: name });
}

document.getElementById('search').addEventListener('input', e => renderSidebar(e.target.value));

// Grid
function renderGrid() {
  document.getElementById('table-title').textContent = current.tableName;
  document.querySelectorAll('.table-item').forEach(el => {
    el.classList.toggle('active', el.textContent === current.tableName);
  });

  const wrap = document.getElementById('grid-wrap');
  if (!current.rows.length && !current.columns.length) {
    wrap.innerHTML = '<div id="empty">No data.</div>';
    return;
  }

  const table = document.createElement('table');
  const thead = document.createElement('thead');
  const tr = document.createElement('tr');
  tr.innerHTML = '<th>id</th>' + current.columns.map(c => `<th>${esc(c)}</th>`).join('') + '<th></th>';
  thead.appendChild(tr);
  table.appendChild(thead);

  const tbody = document.createElement('tbody');
  current.rows.forEach(row => tbody.appendChild(makeRow(row)));
  table.appendChild(tbody);

  wrap.innerHTML = '';
  wrap.appendChild(table);
}

function makeRow(row) {
  const tr = document.createElement('tr');
  const idTd = document.createElement('td');
  idTd.className = 'id-col';
  idTd.textContent = row[0];
  tr.appendChild(idTd);

  current.columns.forEach((col, i) => {
    const td = document.createElement('td');
    td.textContent = row[i + 1] ?? '';
    td.dataset.id = row[0];
    td.dataset.field = col;
    td.addEventListener('dblclick', startEdit);
    tr.appendChild(td);
  });

  const delTd = document.createElement('td');
  const btn = document.createElement('button');
  btn.className = 'del-btn';
  btn.textContent = '✕';
  btn.addEventListener('click', () => vscode.postMessage({ command: 'deleteRow', tableName: current.tableName, dataId: row[0] }));
  delTd.appendChild(btn);
  tr.appendChild(delTd);
  return tr;
}

function startEdit(e) {
  const td = e.currentTarget;
  if (td.querySelector('input')) { return; }
  const original = td.textContent;
  td.className = 'editing';
  const input = document.createElement('input');
  input.value = original;
  td.textContent = '';
  td.appendChild(input);
  input.focus(); input.select();

  function commit() {
    const val = input.value;
    td.className = '';
    td.textContent = val;
    if (val !== original) {
      vscode.postMessage({ command: 'updateCell', tableName: current.tableName, dataId: td.dataset.id, fieldName: td.dataset.field, value: val });
    }
  }
  input.addEventListener('blur', commit);
  input.addEventListener('keydown', ev => {
    if (ev.key === 'Enter') { input.blur(); }
    else if (ev.key === 'Escape') { input.value = original; input.blur(); }
    else if (ev.key === 'Tab') {
      ev.preventDefault(); input.blur();
      const tds = [...td.closest('tr').querySelectorAll('td[data-field]')];
      const next = tds[tds.indexOf(td) + 1];
      if (next) { next.dispatchEvent(new MouseEvent('dblclick')); }
    }
  });
}

document.getElementById('btn-add-row').addEventListener('click', () => {
  if (!current.tableName) { return; }
  vscode.postMessage({ command: 'addRow', tableName: current.tableName });
});

document.getElementById('btn-import').addEventListener('click', () => {
  if (!current.tableName) { return; }
  vscode.postMessage({ command: 'importTable', tableName: current.tableName });
});

document.getElementById('btn-export').addEventListener('click', () => {
  if (!current.tableName) { return; }
  vscode.postMessage({ command: 'exportTable', tableName: current.tableName });
});

document.getElementById('btn-delete-table').addEventListener('click', () => {
  if (!current.tableName) { return; }
  if (confirm(`Delete table "${current.tableName}"?`)) {
    vscode.postMessage({ command: 'deleteTable', tableName: current.tableName });
  }
});

function esc(s) { return s.replace(/&/g, '&amp;').replace(/</g, '&lt;'); }
