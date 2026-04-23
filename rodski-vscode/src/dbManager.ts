import * as fs from 'fs';
import * as path from 'path';
import initSqlJs, { Database } from 'sql.js';

let SQL: Awaited<ReturnType<typeof initSqlJs>> | null = null;
const dbCache = new Map<string, Database>();

let _extensionPath = '';
export function setExtensionPath(p: string) { _extensionPath = p; }

async function getSql() {
  if (!SQL) {
    const wasmPath = path.join(_extensionPath, 'node_modules', 'sql.js', 'dist', 'sql-wasm.wasm');
    SQL = await initSqlJs({ locateFile: () => wasmPath });
  }
  return SQL;
}

async function openDb(dbPath: string): Promise<Database> {
  if (dbCache.has(dbPath)) { return dbCache.get(dbPath)!; }
  const sql = await getSql();
  const buf = fs.readFileSync(dbPath);
  const db = new sql.Database(buf);
  dbCache.set(dbPath, db);
  return db;
}

function saveDb(dbPath: string, db: Database): void {
  const data = db.export();
  fs.writeFileSync(dbPath, Buffer.from(data));
}

export function closeAll(): void {
  for (const db of dbCache.values()) { db.close(); }
  dbCache.clear();
}

export async function listTables(dbPath: string): Promise<string[]> {
  const db = await openDb(dbPath);
  const res = db.exec('SELECT table_name FROM rs_datatable ORDER BY table_name');
  if (!res.length) { return []; }
  return res[0].values.map((r: any) => r[0] as string);
}

export interface TableData {
  columns: string[];
  rows: string[][];
}

export async function getTableData(dbPath: string, tableName: string): Promise<TableData> {
  const db = await openDb(dbPath);

  const colRes = db.exec('SELECT field_name FROM rs_datatable_field WHERE table_name=? ORDER BY field_order', [tableName]);
  const columns: string[] = colRes.length ? colRes[0].values.map((r: any) => r[0] as string) : [];

  const rowRes = db.exec('SELECT data_id FROM rs_row WHERE table_name=? ORDER BY data_id', [tableName]);
  const rowIds: string[] = rowRes.length ? rowRes[0].values.map((r: any) => r[0] as string) : [];

  const fieldRes = db.exec('SELECT data_id, field_name, field_value FROM rs_field WHERE table_name=?', [tableName]);
  const pivot = new Map<string, Map<string, string>>();
  if (fieldRes.length) {
    for (const [dataId, fieldName, fieldValue] of fieldRes[0].values as any[]) {
      if (!pivot.has(dataId)) { pivot.set(dataId, new Map()); }
      pivot.get(dataId)!.set(fieldName, fieldValue ?? '');
    }
  }

  const rows = rowIds.map(id => {
    const vals = pivot.get(id) ?? new Map();
    return [id, ...columns.map(c => vals.get(c) ?? '')];
  });

  return { columns, rows };
}

export async function updateCell(dbPath: string, tableName: string, dataId: string, fieldName: string, value: string): Promise<void> {
  const db = await openDb(dbPath);
  db.run('INSERT OR REPLACE INTO rs_field (table_name,data_id,field_name,field_value) VALUES (?,?,?,?)', [tableName, dataId, fieldName, value]);
  saveDb(dbPath, db);
}

export async function addRow(dbPath: string, tableName: string, dataId: string): Promise<void> {
  const db = await openDb(dbPath);
  db.run('INSERT INTO rs_row (table_name,data_id) VALUES (?,?)', [tableName, dataId]);
  const colRes = db.exec('SELECT field_name FROM rs_datatable_field WHERE table_name=?', [tableName]);
  if (colRes.length) {
    for (const [f] of colRes[0].values as any[]) {
      db.run('INSERT INTO rs_field (table_name,data_id,field_name,field_value) VALUES (?,?,?,?)', [tableName, dataId, f, '']);
    }
  }
  saveDb(dbPath, db);
}

export async function deleteRow(dbPath: string, tableName: string, dataId: string): Promise<void> {
  const db = await openDb(dbPath);
  db.run('DELETE FROM rs_row WHERE table_name=? AND data_id=?', [tableName, dataId]);
  db.run('DELETE FROM rs_field WHERE table_name=? AND data_id=?', [tableName, dataId]);
  saveDb(dbPath, db);
}

export async function addTable(dbPath: string, tableName: string, fields: string[]): Promise<void> {
  const db = await openDb(dbPath);
  db.run('INSERT INTO rs_datatable (table_name,model_name,table_kind,row_mode) VALUES (?,?,?,?)', [tableName, '', 'data', 'single']);
  fields.forEach((f, i) => db.run('INSERT INTO rs_datatable_field (table_name,field_name,field_order) VALUES (?,?,?)', [tableName, f, i]));
  saveDb(dbPath, db);
}

export async function deleteTable(dbPath: string, tableName: string): Promise<void> {
  const db = await openDb(dbPath);
  for (const tbl of ['rs_field', 'rs_row', 'rs_datatable_field', 'rs_datatable']) {
    db.run(`DELETE FROM ${tbl} WHERE table_name=?`, [tableName]);
  }
  saveDb(dbPath, db);
}

// Import rows from flat records [{id, field1, field2, ...}]
// Supports upsert (update existing id) and new columns
export async function importRows(dbPath: string, tableName: string, records: Record<string, string>[]): Promise<void> {
  if (!records.length) { return; }
  const db = await openDb(dbPath);

  // Ensure table exists in rs_datatable
  const exists = db.exec('SELECT 1 FROM rs_datatable WHERE table_name=?', [tableName]);
  if (!exists.length) {
    db.run('INSERT INTO rs_datatable (table_name,model_name,table_kind,row_mode) VALUES (?,?,?,?)', [tableName, tableName, 'data', 'single']);
  }

  // Collect all field names (excluding 'id')
  const allFields = new Set<string>();
  for (const rec of records) { Object.keys(rec).filter(k => k !== 'id').forEach(k => allFields.add(k)); }

  // Get existing schema fields
  const schemaRes = db.exec('SELECT field_name FROM rs_datatable_field WHERE table_name=?', [tableName]);
  const schemaFields = new Set<string>(schemaRes[0]?.values.map((r: any) => r[0] as string) ?? []);

  // Add new columns to schema
  let maxOrder = schemaFields.size;
  for (const f of allFields) {
    if (!schemaFields.has(f)) {
      db.run('INSERT INTO rs_datatable_field (table_name,field_name,field_order) VALUES (?,?,?)', [tableName, f, maxOrder++]);
      schemaFields.add(f);
    }
  }

  // Upsert rows
  for (const rec of records) {
    const dataId = rec['id'] || `row_${Date.now()}_${Math.random().toString(36).slice(2)}`;
    // Ensure row exists
    db.run('INSERT OR IGNORE INTO rs_row (table_name,data_id) VALUES (?,?)', [tableName, dataId]);
    // Upsert each field
    for (const [k, v] of Object.entries(rec)) {
      if (k === 'id') { continue; }
      db.run('INSERT OR REPLACE INTO rs_field (table_name,data_id,field_name,field_value) VALUES (?,?,?,?)', [tableName, dataId, k, v ?? '']);
    }
  }

  saveDb(dbPath, db);
}

// Export rows as flat records [{id, field1, field2, ...}]
export async function exportRows(dbPath: string, tableName: string): Promise<Record<string, string>[]> {
  const data = await getTableData(dbPath, tableName);
  return data.rows.map(row => {
    const rec: Record<string, string> = { id: row[0] };
    data.columns.forEach((c, i) => { rec[c] = row[i + 1] ?? ''; });
    return rec;
  });
}
