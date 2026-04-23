import * as vscode from 'vscode';
import * as path from 'path';
import { listTables } from './dbManager';

export class DbItem extends vscode.TreeItem {
  constructor(public readonly dbPath: string) {
    super(path.basename(path.dirname(dbPath)) + '/data.sqlite', vscode.TreeItemCollapsibleState.Expanded);
    this.tooltip = dbPath;
    this.contextValue = 'rodskiDb';
  }
}

export class TableItem extends vscode.TreeItem {
  constructor(public readonly dbPath: string, public readonly tableName: string) {
    super(tableName, vscode.TreeItemCollapsibleState.None);
    this.contextValue = 'rodskiTable';
    this.command = { command: 'rodski.openTable', title: 'Open', arguments: [dbPath, tableName] };
  }
}

type TreeNode = DbItem | TableItem;

export class RodSkiTreeProvider implements vscode.TreeDataProvider<TreeNode> {
  private _onDidChangeTreeData = new vscode.EventEmitter<TreeNode | undefined | void>();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

  private dbPaths: string[] = [];
  private watcher: vscode.FileSystemWatcher;

  constructor() {
    this.watcher = vscode.workspace.createFileSystemWatcher('**/data.sqlite');
    this.watcher.onDidCreate(() => this.refresh());
    this.watcher.onDidDelete(() => this.refresh());
    this.refresh();
  }

  refresh(): void {
    vscode.workspace.findFiles('**/data.sqlite', '**/node_modules/**').then(uris => {
      this.dbPaths = uris.map(u => u.fsPath);
      this._onDidChangeTreeData.fire();
    });
  }

  dispose(): void { this.watcher.dispose(); }

  getTreeItem(element: TreeNode): vscode.TreeItem { return element; }

  async getChildren(element?: TreeNode): Promise<TreeNode[]> {
    if (!element) {
      return this.dbPaths.map(p => new DbItem(p));
    }
    if (element instanceof DbItem) {
      try {
        const tables = await listTables(element.dbPath);
        return tables.map(t => new TableItem(element.dbPath, t));
      } catch { return []; }
    }
    return [];
  }
}
