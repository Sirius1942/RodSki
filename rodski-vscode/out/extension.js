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
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const treeProvider_1 = require("./treeProvider");
const gridPanel_1 = require("./gridPanel");
const dbManager_1 = require("./dbManager");
function activate(context) {
    (0, dbManager_1.setExtensionPath)(context.extensionPath);
    const tree = new treeProvider_1.RodSkiTreeProvider();
    context.subscriptions.push(vscode.window.registerTreeDataProvider('rodskiTables', tree), vscode.commands.registerCommand('rodski.refresh', () => tree.refresh()), vscode.commands.registerCommand('rodski.openTable', (dbPath, tableName) => {
        (0, gridPanel_1.openTable)(context, dbPath, tableName);
    }), vscode.commands.registerCommand('rodski.openDb', async (uri) => {
        (0, gridPanel_1.openDb)(context, uri.fsPath);
    }), vscode.commands.registerCommand('rodski.addTable', async (item) => {
        const dbPath = item?.dbPath;
        if (!dbPath) {
            return;
        }
        const name = await vscode.window.showInputBox({ prompt: 'Table name' });
        if (!name) {
            return;
        }
        const fieldsStr = await vscode.window.showInputBox({ prompt: 'Fields (comma-separated)' });
        if (!fieldsStr) {
            return;
        }
        await (0, dbManager_1.addTable)(dbPath, name, fieldsStr.split(',').map(f => f.trim()).filter(Boolean));
        tree.refresh();
    }), vscode.commands.registerCommand('rodski.deleteTable', async (item) => {
        if (!item) {
            return;
        }
        const ok = await vscode.window.showWarningMessage(`Delete table "${item.tableName}"?`, { modal: true }, 'Delete');
        if (ok === 'Delete') {
            await (0, dbManager_1.deleteTable)(item.dbPath, item.tableName);
            tree.refresh();
        }
    }), tree);
}
function deactivate() { (0, dbManager_1.closeAll)(); }
//# sourceMappingURL=extension.js.map