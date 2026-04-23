"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.setExtensionPath = setExtensionPath;
exports.closeAll = closeAll;
exports.listTables = listTables;
exports.getTableData = getTableData;
exports.updateCell = updateCell;
exports.addRow = addRow;
exports.deleteRow = deleteRow;
exports.addTable = addTable;
exports.deleteTable = deleteTable;
exports.importRows = importRows;
exports.exportRows = exportRows;
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const sql_js_1 = __importDefault(require("sql.js"));
let SQL = null;
const dbCache = new Map();
let _extensionPath = '';
function setExtensionPath(p) { _extensionPath = p; }
async function getSql() {
    if (!SQL) {
        const wasmPath = path.join(_extensionPath, 'node_modules', 'sql.js', 'dist', 'sql-wasm.wasm');
        SQL = await (0, sql_js_1.default)({ locateFile: () => wasmPath });
    }
    return SQL;
}
async function openDb(dbPath) {
    if (dbCache.has(dbPath)) {
        return dbCache.get(dbPath);
    }
    const sql = await getSql();
    const buf = fs.readFileSync(dbPath);
    const db = new sql.Database(buf);
    dbCache.set(dbPath, db);
    return db;
}
function saveDb(dbPath, db) {
    const data = db.export();
    fs.writeFileSync(dbPath, Buffer.from(data));
}
function closeAll() {
    for (const db of dbCache.values()) {
        db.close();
    }
    dbCache.clear();
}
async function listTables(dbPath) {
    const db = await openDb(dbPath);
    const res = db.exec('SELECT table_name FROM rs_datatable ORDER BY table_name');
    if (!res.length) {
        return [];
    }
    return res[0].values.map((r) => r[0]);
}
async function getTableData(dbPath, tableName) {
    const db = await openDb(dbPath);
    const colRes = db.exec('SELECT field_name FROM rs_datatable_field WHERE table_name=? ORDER BY field_order', [tableName]);
    const columns = colRes.length ? colRes[0].values.map((r) => r[0]) : [];
    const rowRes = db.exec('SELECT data_id FROM rs_row WHERE table_name=? ORDER BY data_id', [tableName]);
    const rowIds = rowRes.length ? rowRes[0].values.map((r) => r[0]) : [];
    const fieldRes = db.exec('SELECT data_id, field_name, field_value FROM rs_field WHERE table_name=?', [tableName]);
    const pivot = new Map();
    if (fieldRes.length) {
        for (const [dataId, fieldName, fieldValue] of fieldRes[0].values) {
            if (!pivot.has(dataId)) {
                pivot.set(dataId, new Map());
            }
            pivot.get(dataId).set(fieldName, fieldValue ?? '');
        }
    }
    const rows = rowIds.map(id => {
        const vals = pivot.get(id) ?? new Map();
        return [id, ...columns.map(c => vals.get(c) ?? '')];
    });
    return { columns, rows };
}
async function updateCell(dbPath, tableName, dataId, fieldName, value) {
    const db = await openDb(dbPath);
    db.run('INSERT OR REPLACE INTO rs_field (table_name,data_id,field_name,field_value) VALUES (?,?,?,?)', [tableName, dataId, fieldName, value]);
    saveDb(dbPath, db);
}
async function addRow(dbPath, tableName, dataId) {
    const db = await openDb(dbPath);
    db.run('INSERT INTO rs_row (table_name,data_id) VALUES (?,?)', [tableName, dataId]);
    const colRes = db.exec('SELECT field_name FROM rs_datatable_field WHERE table_name=?', [tableName]);
    if (colRes.length) {
        for (const [f] of colRes[0].values) {
            db.run('INSERT INTO rs_field (table_name,data_id,field_name,field_value) VALUES (?,?,?,?)', [tableName, dataId, f, '']);
        }
    }
    saveDb(dbPath, db);
}
async function deleteRow(dbPath, tableName, dataId) {
    const db = await openDb(dbPath);
    db.run('DELETE FROM rs_row WHERE table_name=? AND data_id=?', [tableName, dataId]);
    db.run('DELETE FROM rs_field WHERE table_name=? AND data_id=?', [tableName, dataId]);
    saveDb(dbPath, db);
}
async function addTable(dbPath, tableName, fields) {
    const db = await openDb(dbPath);
    db.run('INSERT INTO rs_datatable (table_name,model_name,table_kind,row_mode) VALUES (?,?,?,?)', [tableName, '', 'data', 'single']);
    fields.forEach((f, i) => db.run('INSERT INTO rs_datatable_field (table_name,field_name,field_order) VALUES (?,?,?)', [tableName, f, i]));
    saveDb(dbPath, db);
}
async function deleteTable(dbPath, tableName) {
    const db = await openDb(dbPath);
    for (const tbl of ['rs_field', 'rs_row', 'rs_datatable_field', 'rs_datatable']) {
        db.run(`DELETE FROM ${tbl} WHERE table_name=?`, [tableName]);
    }
    saveDb(dbPath, db);
}
// Import rows from flat records [{id, field1, field2, ...}]
// Supports upsert (update existing id) and new columns
async function importRows(dbPath, tableName, records) {
    if (!records.length) {
        return;
    }
    const db = await openDb(dbPath);
    // Ensure table exists in rs_datatable
    const exists = db.exec('SELECT 1 FROM rs_datatable WHERE table_name=?', [tableName]);
    if (!exists.length) {
        db.run('INSERT INTO rs_datatable (table_name,model_name,table_kind,row_mode) VALUES (?,?,?,?)', [tableName, tableName, 'data', 'single']);
    }
    // Collect all field names (excluding 'id')
    const allFields = new Set();
    for (const rec of records) {
        Object.keys(rec).filter(k => k !== 'id').forEach(k => allFields.add(k));
    }
    // Get existing schema fields
    const schemaRes = db.exec('SELECT field_name FROM rs_datatable_field WHERE table_name=?', [tableName]);
    const schemaFields = new Set(schemaRes[0]?.values.map((r) => r[0]) ?? []);
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
            if (k === 'id') {
                continue;
            }
            db.run('INSERT OR REPLACE INTO rs_field (table_name,data_id,field_name,field_value) VALUES (?,?,?,?)', [tableName, dataId, k, v ?? '']);
        }
    }
    saveDb(dbPath, db);
}
// Export rows as flat records [{id, field1, field2, ...}]
async function exportRows(dbPath, tableName) {
    const data = await getTableData(dbPath, tableName);
    return data.rows.map(row => {
        const rec = { id: row[0] };
        data.columns.forEach((c, i) => { rec[c] = row[i + 1] ?? ''; });
        return rec;
    });
}
//# sourceMappingURL=dbManager.js.map