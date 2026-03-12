/**
 * Migrate Webview — opens the migration UI as a VS Code editor tab.
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { backendServer } from '../common/backendServer';
import { traceVerbose } from '../common/log/logging';
import { createWebviewOptions, getNonce, getWsOrigin } from '../common/webview';
import { renderTemplate, serializeJsonForHtml } from '../common/template';
// @ts-ignore
import * as _migrateTemplateText from './migrate.hbs';
// @ts-ignore
import * as _notBuiltTemplateText from '../providers/webview-not-built.hbs';

const migrateTemplateText: string = (_migrateTemplateText as any).default || _migrateTemplateText;
const notBuiltTemplateText: string = (_notBuiltTemplateText as any).default || _notBuiltTemplateText;

const PROD_LOCAL_RESOURCE_ROOTS = ['resources/webviews', 'webviews/dist'];

let panel: vscode.WebviewPanel | undefined;

export function openMigratePreview(extensionUri: vscode.Uri, projectRoot: string): void {
  const extensionPath = extensionUri.fsPath;

  if (panel) {
    panel.reveal(vscode.ViewColumn.Beside);
    return;
  }

  const webviewOptions = createWebviewOptions({
    extensionPath,
    port: backendServer.port,
    prodLocalResourceRoots: PROD_LOCAL_RESOURCE_ROOTS,
  });

  panel = vscode.window.createWebviewPanel(
    'atopile.migrate',
    'Migrate Project',
    vscode.ViewColumn.Beside,
    webviewOptions,
  );

  panel.webview.html = getProdHtml(panel.webview, extensionPath, projectRoot);

  // Handle messages from the migrate webview
  panel.webview.onDidReceiveMessage((message) => {
    switch (message.type) {
      case 'closeMigrateTab':
        panel?.dispose();
        break;
      default:
        traceVerbose(`[MigrateWebview] Unknown message type: ${message.type}`);
        break;
    }
  });

  panel.onDidDispose(() => {
    panel = undefined;
  });
}

export function closeMigratePreview(): void {
  panel?.dispose();
  panel = undefined;
}

function getProdHtml(webview: vscode.Webview, extensionPath: string, projectRoot: string): string {
  const nonce = getNonce();

  const webviewsDir = path.join(extensionPath, 'resources', 'webviews');
  const jsPath = path.join(webviewsDir, 'migrate.js');
  const cssPath = path.join(webviewsDir, 'migrate.css');
  const baseCssPath = path.join(webviewsDir, 'index.css');

  if (!fs.existsSync(jsPath)) {
    return renderTemplate(notBuiltTemplateText, {
      buildCommand: 'npm run build',
    });
  }

  const jsUri = webview.asWebviewUri(vscode.Uri.file(jsPath));
  const cssUri = fs.existsSync(cssPath)
    ? webview.asWebviewUri(vscode.Uri.file(cssPath))
    : null;
  const baseCssUri = fs.existsSync(baseCssPath)
    ? webview.asWebviewUri(vscode.Uri.file(baseCssPath))
    : null;

  const apiUrl = backendServer.apiUrl;
  const wsUrl = backendServer.wsUrl;
  const wsOrigin = getWsOrigin(wsUrl);

  const csp = [
    "default-src 'none'",
    `style-src ${webview.cspSource} 'unsafe-inline'`,
    `script-src ${webview.cspSource} 'nonce-${nonce}'`,
    `font-src ${webview.cspSource}`,
    `img-src ${webview.cspSource} data: https: http:`,
    `connect-src ${apiUrl} ${wsOrigin}`,
  ].join('; ');

  return renderTemplate(migrateTemplateText, {
    csp,
    nonce,
    baseCssLink: baseCssUri ? `<link rel="stylesheet" href="${baseCssUri}">` : '',
    cssLink: cssUri ? `<link rel="stylesheet" href="${cssUri}">` : '',
    apiUrlJson: serializeJsonForHtml(apiUrl),
    wsOriginJson: serializeJsonForHtml(wsOrigin),
    projectRootJson: serializeJsonForHtml(projectRoot),
    jsUri: jsUri.toString(),
  });
}
