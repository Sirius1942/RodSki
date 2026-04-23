import * as vscode from 'vscode';
import { RodSkiTreeProvider, TableItem } from './treeProvider';
import { openDb, openTable } from './gridPanel';
import { closeAll, addTable, deleteTable, listTables, setExtensionPath } from './dbManager';

export function activate(context: vscode.ExtensionContext) {
  setExtensionPath(context.extensionPath);
  const tree = new RodSkiTreeProvider();
  context.subscriptions.push(
    vscode.window.registerTreeDataProvider('rodskiTables', tree),
    vscode.commands.registerCommand('rodski.refresh', () => tree.refresh()),
    vscode.commands.registerCommand('rodski.openTable', (dbPath: string, tableName: string) => {
      openTable(context, dbPath, tableName);
    }),
    vscode.commands.registerCommand('rodski.openDb', async (uri: vscode.Uri) => {
      openDb(context, uri.fsPath);
    }),
    vscode.commands.registerCommand('rodski.addTable', async (item?: any) => {
      const dbPath = item?.dbPath;
      if (!dbPath) { return; }
      const name = await vscode.window.showInputBox({ prompt: 'Table name' });
      if (!name) { return; }
      const fieldsStr = await vscode.window.showInputBox({ prompt: 'Fields (comma-separated)' });
      if (!fieldsStr) { return; }
      await addTable(dbPath, name, fieldsStr.split(',').map(f => f.trim()).filter(Boolean));
      tree.refresh();
    }),
    vscode.commands.registerCommand('rodski.deleteTable', async (item?: TableItem) => {
      if (!item) { return; }
      const ok = await vscode.window.showWarningMessage(`Delete table "${item.tableName}"?`, { modal: true }, 'Delete');
      if (ok === 'Delete') { await deleteTable(item.dbPath, item.tableName); tree.refresh(); }
    }),
    tree
  );
}

export function deactivate() { closeAll(); }
