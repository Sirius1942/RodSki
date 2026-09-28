import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import * as crypto from 'crypto';

const panels = new Map<string, vscode.WebviewPanel>();

function jsonForInlineScript(value: unknown): string {
  return JSON.stringify(value)
    .replace(/</g, '\\u003c')
    .replace(/>/g, '\\u003e')
    .replace(/&/g, '\\u0026')
    .replace(/\u2028/g, '\\u2028')
    .replace(/\u2029/g, '\\u2029');
}

export function openBusinessModel(context: vscode.ExtensionContext, filePath: string): void {
  const existing = panels.get(filePath);
  if (existing) {
    existing.reveal();
    return;
  }

  const panel = vscode.window.createWebviewPanel(
    'rodskiBusinessModel',
    `${path.basename(filePath)} · Business Model`,
    vscode.ViewColumn.One,
    {
      enableScripts: true,
      localResourceRoots: [vscode.Uri.joinPath(context.extensionUri, 'dist', 'webview')],
    }
  );
  panels.set(filePath, panel);

  const nonce = crypto.randomBytes(16).toString('base64');
  const jsUri = panel.webview.asWebviewUri(
    vscode.Uri.joinPath(context.extensionUri, 'dist', 'webview', 'business.js')
  );
  const htmlPath = path.join(context.extensionPath, 'dist', 'webview', 'business.html');
  const initialXml = readXml(filePath);
  const initialData = jsonForInlineScript({ xml: initialXml, filePath });
  const html = fs.readFileSync(htmlPath, 'utf8');
  panel.webview.html = html
    .replaceAll('{{nonce}}', nonce)
    .replace('{{businessJsUri}}', () => jsUri.toString())
    .replace('{{BUSINESS_DATA_JSON}}', () => initialData);

  const watcher = vscode.workspace.createFileSystemWatcher(filePath);
  watcher.onDidChange(() => sendXml(panel, filePath));
  watcher.onDidDelete(() => panel.dispose());

  panel.webview.onDidReceiveMessage(async msg => {
    if (msg.command === 'ready') {
      sendXml(panel, filePath);
    } else if (msg.command === 'openSource') {
      const document = await vscode.workspace.openTextDocument(filePath);
      await vscode.window.showTextDocument(document, vscode.ViewColumn.Two);
    }
  });

  panel.onDidDispose(() => {
    panels.delete(filePath);
    watcher.dispose();
  });
}

function readXml(filePath: string): string {
  try {
    return fs.readFileSync(filePath, 'utf8');
  } catch {
    return '';
  }
}

function sendXml(panel: vscode.WebviewPanel, filePath: string): void {
  if (panel.visible || panels.get(filePath) === panel) {
    panel.webview.postMessage({ command: 'loadXml', xml: readXml(filePath), filePath });
  }
}
