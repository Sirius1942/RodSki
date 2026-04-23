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
exports.RodSkiTreeProvider = exports.TableItem = exports.DbItem = void 0;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
const dbManager_1 = require("./dbManager");
class DbItem extends vscode.TreeItem {
    constructor(dbPath) {
        super(path.basename(path.dirname(dbPath)) + '/data.sqlite', vscode.TreeItemCollapsibleState.Expanded);
        this.dbPath = dbPath;
        this.tooltip = dbPath;
        this.contextValue = 'rodskiDb';
    }
}
exports.DbItem = DbItem;
class TableItem extends vscode.TreeItem {
    constructor(dbPath, tableName) {
        super(tableName, vscode.TreeItemCollapsibleState.None);
        this.dbPath = dbPath;
        this.tableName = tableName;
        this.contextValue = 'rodskiTable';
        this.command = { command: 'rodski.openTable', title: 'Open', arguments: [dbPath, tableName] };
    }
}
exports.TableItem = TableItem;
class RodSkiTreeProvider {
    constructor() {
        this._onDidChangeTreeData = new vscode.EventEmitter();
        this.onDidChangeTreeData = this._onDidChangeTreeData.event;
        this.dbPaths = [];
        this.watcher = vscode.workspace.createFileSystemWatcher('**/data.sqlite');
        this.watcher.onDidCreate(() => this.refresh());
        this.watcher.onDidDelete(() => this.refresh());
        this.refresh();
    }
    refresh() {
        vscode.workspace.findFiles('**/data.sqlite', '**/node_modules/**').then(uris => {
            this.dbPaths = uris.map(u => u.fsPath);
            this._onDidChangeTreeData.fire();
        });
    }
    dispose() { this.watcher.dispose(); }
    getTreeItem(element) { return element; }
    async getChildren(element) {
        if (!element) {
            return this.dbPaths.map(p => new DbItem(p));
        }
        if (element instanceof DbItem) {
            try {
                const tables = await (0, dbManager_1.listTables)(element.dbPath);
                return tables.map(t => new TableItem(element.dbPath, t));
            }
            catch {
                return [];
            }
        }
        return [];
    }
}
exports.RodSkiTreeProvider = RodSkiTreeProvider;
//# sourceMappingURL=treeProvider.js.map