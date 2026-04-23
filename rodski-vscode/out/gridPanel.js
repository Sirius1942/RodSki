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
Object.defineProperty(exports, "__esModule", { value: true });
exports.openDb = openDb;
exports.openTable = openTable;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
const XLSX = __importStar(require("xlsx"));
const db = __importStar(require("./dbManager"));
const panels = new Map();
function openDb(context, dbPath) {
    if (panels.has(dbPath)) {
        panels.get(dbPath).reveal();
        return;
    }
    const panel = vscode.window.createWebviewPanel('rodskiGrid', path.basename(path.dirname(dbPath)) + '/data.sqlite', vscode.ViewColumn.One, {
        enableScripts: true,
        localResourceRoots: [vscode.Uri.file(path.join(context.extensionPath, 'src', 'webview'))]
    });
    panels.set(dbPath, panel);
    panel.onDidDispose(() => panels.delete(dbPath));
    const jsUri = panel.webview.asWebviewUri(vscode.Uri.file(path.join(context.extensionPath, 'src', 'webview', 'grid.js')));
    const html = fs.readFileSync(path.join(context.extensionPath, 'src', 'webview', 'grid.html'), 'utf8');
    panel.webview.html = html.replace('{{gridJsUri}}', jsUri.toString());
    // Send all tables on open
    sendAllTables(panel, dbPath);
    panel.webview.onDidReceiveMessage(msg => handleMessage(panel, dbPath, msg));
}
// Keep openTable for tree view clicks
function openTable(context, dbPath, tableName) {
    openDb(context, dbPath);
    // After panel opens, select the table
    setTimeout(() => {
        const panel = panels.get(dbPath);
        if (panel) {
            panel.webview.postMessage({ command: 'selectTable', payload: { tableName } });
        }
    }, 500);
}
async function sendAllTables(panel, dbPath) {
    const tables = await db.listTables(dbPath);
    panel.webview.postMessage({ command: 'setTables', payload: { tables } });
    if (tables.length > 0) {
        const data = await db.getTableData(dbPath, tables[0]);
        panel.webview.postMessage({ command: 'loadTable', payload: { tableName: tables[0], ...data } });
    }
}
async function sendTableData(panel, dbPath, tableName) {
    const data = await db.getTableData(dbPath, tableName);
    panel.webview.postMessage({ command: 'loadTable', payload: { tableName, ...data } });
}
async function handleMessage(panel, dbPath, msg) {
    switch (msg.command) {
        case 'selectTable':
            await sendTableData(panel, dbPath, msg.tableName);
            break;
        case 'updateCell':
            await db.updateCell(dbPath, msg.tableName, msg.dataId, msg.fieldName, msg.value);
            break;
        case 'addRow': {
            const prefix = msg.tableName.charAt(0).toUpperCase();
            const data = await db.getTableData(dbPath, msg.tableName);
            let maxNum = 0;
            for (const row of data.rows) {
                const m = row[0].match(new RegExp(`^${prefix}(\\d+)$`));
                if (m) {
                    maxNum = Math.max(maxNum, parseInt(m[1]));
                }
            }
            const nextNum = Math.min(maxNum + 1, 5000);
            const dataId = `${prefix}${String(nextNum).padStart(3, '0')}`;
            await db.addRow(dbPath, msg.tableName, dataId);
            await sendTableData(panel, dbPath, msg.tableName);
            break;
        }
        case 'deleteRow':
            await db.deleteRow(dbPath, msg.tableName, msg.dataId);
            await sendTableData(panel, dbPath, msg.tableName);
            break;
        case 'addTable':
            await db.addTable(dbPath, msg.tableName, msg.fields);
            await sendAllTables(panel, dbPath);
            vscode.commands.executeCommand('rodski.refresh');
            break;
        case 'deleteTable':
            await db.deleteTable(dbPath, msg.tableName);
            await sendAllTables(panel, dbPath);
            vscode.commands.executeCommand('rodski.refresh');
            break;
        case 'importTable': {
            const uris = await vscode.window.showOpenDialog({
                filters: { 'Excel/CSV': ['xlsx', 'xls', 'csv'] }, canSelectMany: false
            });
            if (!uris?.length) {
                break;
            }
            const filePath = uris[0].fsPath;
            const wb = XLSX.readFile(filePath);
            const ws = wb.Sheets[wb.SheetNames[0]];
            const records = XLSX.utils.sheet_to_json(ws, { defval: '' });
            await db.importRows(dbPath, msg.tableName, records);
            await sendTableData(panel, dbPath, msg.tableName);
            vscode.window.showInformationMessage(`Imported ${records.length} rows into ${msg.tableName}`);
            break;
        }
        case 'exportTable': {
            const uri = await vscode.window.showSaveDialog({
                defaultUri: vscode.Uri.file(`${msg.tableName}.xlsx`),
                filters: { 'Excel': ['xlsx'], 'CSV': ['csv'] }
            });
            if (!uri) {
                break;
            }
            const rows = await db.exportRows(dbPath, msg.tableName);
            const wb = XLSX.utils.book_new();
            XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(rows), msg.tableName);
            XLSX.writeFile(wb, uri.fsPath);
            vscode.window.showInformationMessage(`Exported ${rows.length} rows to ${path.basename(uri.fsPath)}`);
            break;
        }
    }
}
//# sourceMappingURL=gridPanel.js.map