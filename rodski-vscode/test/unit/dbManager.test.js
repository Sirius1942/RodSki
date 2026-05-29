const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const os = require('os');

const DB_MOD = path.join(__dirname, '../../src/dbManager.ts');

// We test via the compiled JS — require the source after building
// For CI this runs after `npm run compile`, so dist/ exists
// For local dev, we use a lightweight approach: create a temp db and test sql.js directly

const initSqlJs = require('sql.js');

function createSchema(db) {
  db.run(`CREATE TABLE rs_datatable (table_name TEXT PRIMARY KEY, model_name TEXT, table_kind TEXT, row_mode TEXT)`);
  db.run(`CREATE TABLE rs_datatable_field (table_name TEXT, field_name TEXT, field_order INTEGER)`);
  db.run(`CREATE TABLE rs_row (table_name TEXT, data_id TEXT, PRIMARY KEY(table_name, data_id))`);
  db.run(`CREATE TABLE rs_field (table_name TEXT, data_id TEXT, field_name TEXT, field_value TEXT, PRIMARY KEY(table_name, data_id, field_name))`);
}

let SQL;
test('setup', async () => {
  const wasmPath = path.join(__dirname, '../../node_modules/sql.js/dist/sql-wasm.wasm');
  SQL = await initSqlJs({ locateFile: () => wasmPath });
});

test('listTables returns table names from rs_datatable', () => {
  const db = new SQL.Database();
  createSchema(db);
  db.run(`INSERT INTO rs_datatable VALUES ('login','login','data','single')`);
  db.run(`INSERT INTO rs_datatable VALUES ('users','users','data','single')`);
  const res = db.exec('SELECT table_name FROM rs_datatable ORDER BY table_name');
  const tables = res[0].values.map(r => r[0]);
  assert.deepEqual(tables, ['login', 'users']);
  db.close();
});

test('getTableData pivots fields into rows', () => {
  const db = new SQL.Database();
  createSchema(db);
  db.run(`INSERT INTO rs_datatable VALUES ('t1','t1','data','single')`);
  db.run(`INSERT INTO rs_datatable_field VALUES ('t1','name',0)`);
  db.run(`INSERT INTO rs_datatable_field VALUES ('t1','age',1)`);
  db.run(`INSERT INTO rs_row VALUES ('t1','R001')`);
  db.run(`INSERT INTO rs_field VALUES ('t1','R001','name','Alice')`);
  db.run(`INSERT INTO rs_field VALUES ('t1','R001','age','30')`);

  const colRes = db.exec('SELECT field_name FROM rs_datatable_field WHERE table_name=? ORDER BY field_order', ['t1']);
  const columns = colRes[0].values.map(r => r[0]);
  assert.deepEqual(columns, ['name', 'age']);

  const fieldRes = db.exec('SELECT data_id, field_name, field_value FROM rs_field WHERE table_name=?', ['t1']);
  const pivot = new Map();
  for (const [dataId, fieldName, fieldValue] of fieldRes[0].values) {
    if (!pivot.has(dataId)) pivot.set(dataId, new Map());
    pivot.get(dataId).set(fieldName, fieldValue ?? '');
  }
  const row = ['R001', ...columns.map(c => pivot.get('R001')?.get(c) ?? '')];
  assert.deepEqual(row, ['R001', 'Alice', '30']);
  db.close();
});

test('updateCell inserts or replaces field value', () => {
  const db = new SQL.Database();
  createSchema(db);
  db.run(`INSERT INTO rs_datatable VALUES ('t1','t1','data','single')`);
  db.run(`INSERT INTO rs_row VALUES ('t1','R001')`);
  db.run(`INSERT INTO rs_field VALUES ('t1','R001','name','Alice')`);

  db.run('INSERT OR REPLACE INTO rs_field (table_name,data_id,field_name,field_value) VALUES (?,?,?,?)', ['t1', 'R001', 'name', 'Bob']);
  const res = db.exec('SELECT field_value FROM rs_field WHERE table_name=? AND data_id=? AND field_name=?', ['t1', 'R001', 'name']);
  assert.equal(res[0].values[0][0], 'Bob');
  db.close();
});

test('addRow creates row and empty fields', () => {
  const db = new SQL.Database();
  createSchema(db);
  db.run(`INSERT INTO rs_datatable VALUES ('t1','t1','data','single')`);
  db.run(`INSERT INTO rs_datatable_field VALUES ('t1','name',0)`);
  db.run(`INSERT INTO rs_datatable_field VALUES ('t1','age',1)`);

  db.run('INSERT INTO rs_row (table_name,data_id) VALUES (?,?)', ['t1', 'R001']);
  const colRes = db.exec('SELECT field_name FROM rs_datatable_field WHERE table_name=?', ['t1']);
  for (const [f] of colRes[0].values) {
    db.run('INSERT INTO rs_field (table_name,data_id,field_name,field_value) VALUES (?,?,?,?)', ['t1', 'R001', f, '']);
  }

  const rowRes = db.exec('SELECT data_id FROM rs_row WHERE table_name=?', ['t1']);
  assert.equal(rowRes[0].values.length, 1);
  const fieldRes = db.exec('SELECT field_name FROM rs_field WHERE table_name=? AND data_id=?', ['t1', 'R001']);
  assert.equal(fieldRes[0].values.length, 2);
  db.close();
});

test('deleteRow removes row and its fields', () => {
  const db = new SQL.Database();
  createSchema(db);
  db.run(`INSERT INTO rs_datatable VALUES ('t1','t1','data','single')`);
  db.run(`INSERT INTO rs_row VALUES ('t1','R001')`);
  db.run(`INSERT INTO rs_field VALUES ('t1','R001','name','Alice')`);

  db.run('DELETE FROM rs_row WHERE table_name=? AND data_id=?', ['t1', 'R001']);
  db.run('DELETE FROM rs_field WHERE table_name=? AND data_id=?', ['t1', 'R001']);

  const rowRes = db.exec('SELECT * FROM rs_row WHERE table_name=?', ['t1']);
  assert.equal(rowRes.length, 0);
  const fieldRes = db.exec('SELECT * FROM rs_field WHERE table_name=?', ['t1']);
  assert.equal(fieldRes.length, 0);
  db.close();
});

test('deleteTable removes all related data', () => {
  const db = new SQL.Database();
  createSchema(db);
  db.run(`INSERT INTO rs_datatable VALUES ('t1','t1','data','single')`);
  db.run(`INSERT INTO rs_datatable_field VALUES ('t1','name',0)`);
  db.run(`INSERT INTO rs_row VALUES ('t1','R001')`);
  db.run(`INSERT INTO rs_field VALUES ('t1','R001','name','Alice')`);

  for (const tbl of ['rs_field', 'rs_row', 'rs_datatable_field', 'rs_datatable']) {
    db.run(`DELETE FROM ${tbl} WHERE table_name=?`, ['t1']);
  }

  const res = db.exec('SELECT * FROM rs_datatable');
  assert.equal(res.length, 0);
  db.close();
});
