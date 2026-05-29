import * as esbuild from 'esbuild';
import { cpSync, mkdirSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const watch = process.argv.includes('--watch');
const minify = process.argv.includes('--minify');

mkdirSync(resolve(__dirname, 'dist/webview'), { recursive: true });

// Copy static assets
cpSync(resolve(__dirname, 'src/webview/grid.html'), resolve(__dirname, 'dist/webview/grid.html'));
cpSync(resolve(__dirname, 'src/webview/case.html'), resolve(__dirname, 'dist/webview/case.html'));
cpSync(resolve(__dirname, 'node_modules/sql.js/dist/sql-wasm.wasm'), resolve(__dirname, 'dist/sql-wasm.wasm'));

const shared = { bundle: true, minify, sourcemap: !minify };

// Extension host (Node.js, CJS)
const extCtx = await esbuild.context({
  ...shared,
  entryPoints: [resolve(__dirname, 'src/extension.ts')],
  outfile: resolve(__dirname, 'dist/extension.js'),
  format: 'cjs',
  platform: 'node',
  external: ['vscode'],
});

// Webview scripts (browser, IIFE)
const webviewCtx = await esbuild.context({
  ...shared,
  entryPoints: [
    resolve(__dirname, 'src/webview/grid.js'),
    resolve(__dirname, 'src/webview/case.js'),
  ],
  outdir: resolve(__dirname, 'dist/webview'),
  format: 'iife',
  platform: 'browser',
});

if (watch) {
  await extCtx.watch();
  await webviewCtx.watch();
  console.log('Watching...');
} else {
  await extCtx.rebuild();
  await webviewCtx.rebuild();
  await extCtx.dispose();
  await webviewCtx.dispose();
}
