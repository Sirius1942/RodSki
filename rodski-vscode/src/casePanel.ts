import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import * as crypto from 'crypto';

const panels = new Map<string, vscode.WebviewPanel>();

export function openCase(context: vscode.ExtensionContext, filePath: string): void {
  if (panels.has(filePath)) { panels.get(filePath)!.reveal(); return; }

  const panel = vscode.window.createWebviewPanel(
    'rodskiCase',
    path.basename(filePath),
    vscode.ViewColumn.One,
    {
      enableScripts: true,
      localResourceRoots: [vscode.Uri.joinPath(context.extensionUri, 'dist', 'webview')]
    }
  );
  panels.set(filePath, panel);
  panel.onDidDispose(() => panels.delete(filePath));

  const nonce = crypto.randomBytes(16).toString('base64');
  const jsUri = panel.webview.asWebviewUri(
    vscode.Uri.joinPath(context.extensionUri, 'dist', 'webview', 'case.js')
  );
  const xml = fs.readFileSync(filePath, 'utf8');
  const caseDataJson = JSON.stringify({ xml, filePath });
  const htmlPath = path.join(context.extensionPath, 'dist', 'webview', 'case.html');
  const html = fs.readFileSync(htmlPath, 'utf8');
  panel.webview.html = html
    .replaceAll('{{nonce}}', nonce)
    .replaceAll('{{caseJsUri}}', jsUri.toString())
    .replace('{{CASE_DATA_JSON}}', caseDataJson);

  const watcher = vscode.workspace.createFileSystemWatcher(filePath);
  watcher.onDidChange(() => sendXml(panel, filePath));
  panel.onDidDispose(() => watcher.dispose());

  // result/ directory is sibling to case/
  const resultDir = path.join(path.dirname(path.dirname(filePath)), 'result');
  let logPoller: NodeJS.Timeout | undefined;

  panel.webview.onDidReceiveMessage(msg => {
    if (msg.command === 'ready') {
      sendXml(panel, filePath);
    } else if (msg.command === 'saveXml') {
      fs.writeFileSync(filePath, msg.xml, 'utf8');
    } else if (msg.command === 'runCase') {
      const terminal = vscode.window.createTerminal('RodSki Run');
      terminal.show(false);
      terminal.sendText(`rodski run "${filePath}"`);
      startLogPolling(panel, resultDir);
    }
  });

  function startLogPolling(p: vscode.WebviewPanel, dir: string) {
    if (logPoller) { clearInterval(logPoller); }
    let lastSize = 0;
    let logPath = '';

    logPoller = setInterval(() => {
      if (!logPath) {
        // Find the newest result subdirectory
        const newest = findNewestResultDir(dir);
        if (newest) {
          const candidate = path.join(newest, 'execution.log');
          if (fs.existsSync(candidate)) { logPath = candidate; }
        }
        if (!logPath) { return; }
      }

      try {
        const stat = fs.statSync(logPath);
        if (stat.size > lastSize) {
          const fd = fs.openSync(logPath, 'r');
          const buf = Buffer.alloc(stat.size - lastSize);
          fs.readSync(fd, buf, 0, buf.length, lastSize);
          fs.closeSync(fd);
          lastSize = stat.size;
          p.webview.postMessage({ command: 'appendLog', text: buf.toString('utf8') });
        }
      } catch { /* file may not exist yet */ }
    }, 1000);
  }

  panel.onDidDispose(() => {
    if (logPoller) { clearInterval(logPoller); }
    watcher.dispose();
  });
}

function findNewestResultDir(resultDir: string): string | undefined {
  if (!fs.existsSync(resultDir)) { return undefined; }
  const entries = fs.readdirSync(resultDir, { withFileTypes: true })
    .filter(e => e.isDirectory())
    .map(e => ({ name: e.name, mtime: fs.statSync(path.join(resultDir, e.name)).mtimeMs }))
    .sort((a, b) => b.mtime - a.mtime);
  return entries.length ? path.join(resultDir, entries[0].name) : undefined;
}

function sendXml(panel: vscode.WebviewPanel, filePath: string): void {
  const xml = fs.readFileSync(filePath, 'utf8');
  panel.webview.postMessage({ command: 'loadXml', xml, filePath });
}
