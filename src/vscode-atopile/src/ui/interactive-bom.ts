/**
 * Interactive BOM Webview — opens the interactive BOM UI as a VS Code editor tab.
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { getResourcesPath } from '../common/resources';
import { backendServer } from '../common/backendServer';
import { getNonce, getWsOrigin } from '../common/webview';
import { BaseWebview } from './webview-base';

class InteractiveBomWebview extends BaseWebview {
  private projectRoot?: string;
  private targetName?: string;

  constructor() {
    super({
      id: 'atopile.interactiveBom',
      title: 'Interactive BOM',
    });
  }

  /** Set context before opening. */
  public openWithContext(projectRoot?: string, targetName?: string): Promise<void> {
    this.projectRoot = projectRoot;
    this.targetName = targetName;
    return this.open();
  }

  protected getLocalResourceRoots(): vscode.Uri[] {
    const webviewsDir = path.join(getResourcesPath(), 'webviews');
    return [
      vscode.Uri.file(webviewsDir),
      ...super.getLocalResourceRoots(),
    ];
  }

  protected getHtmlContent(webview: vscode.Webview): string {
    const resourcesPath = getResourcesPath();
    const webviewsDir = path.join(resourcesPath, 'webviews');
    const jsPath = path.join(webviewsDir, 'interactiveBom.js');
    const cssPath = path.join(webviewsDir, 'interactiveBom.css');
    const baseCssPath = path.join(webviewsDir, 'index.css');

    if (!fs.existsSync(jsPath)) {
      return this.getMissingResourceHtml('Interactive BOM');
    }

    const nonce = getNonce();
    const jsUri = webview.asWebviewUri(vscode.Uri.file(jsPath));
    const baseUri = webview.asWebviewUri(vscode.Uri.file(webviewsDir + '/'));
    const cssUri = fs.existsSync(cssPath)
      ? webview.asWebviewUri(vscode.Uri.file(cssPath))
      : null;
    const baseCssUri = fs.existsSync(baseCssPath)
      ? webview.asWebviewUri(vscode.Uri.file(baseCssPath))
      : null;

    const apiUrl = backendServer.apiUrl;
    const wsUrl = backendServer.wsUrl;
    const wsOrigin = getWsOrigin(wsUrl);

    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <base href="${baseUri}">
  <meta http-equiv="Content-Security-Policy" content="
    default-src 'none';
    style-src ${webview.cspSource} 'unsafe-inline';
    script-src ${webview.cspSource} 'nonce-${nonce}' 'wasm-unsafe-eval' 'unsafe-eval';
    font-src ${webview.cspSource};
    img-src ${webview.cspSource} data: https: http:;
    connect-src ${webview.cspSource} ${apiUrl} ${wsOrigin};
  ">
  <title>Interactive BOM</title>
  ${baseCssUri ? `<link rel="stylesheet" href="${baseCssUri}">` : ''}
  ${cssUri ? `<link rel="stylesheet" href="${cssUri}">` : ''}
  <script nonce="${nonce}">
    window.__LAYOUT_BASE_URL__ = '${apiUrl}'.replace(/\\/api$/, '');
    window.__LAYOUT_API_PREFIX__ = '/api/layout';
    window.__LAYOUT_WS_PATH__ = '/ws/layout';
    window.__ATOPILE_API_URL__ = '${apiUrl}';
    window.__ATOPILE_WS_URL__ = '${wsOrigin}';
    window.__IBOM_PROJECT_ROOT__ = ${JSON.stringify(this.projectRoot ?? '')};
    window.__IBOM_TARGET_NAME__ = ${JSON.stringify(this.targetName ?? '')};
  </script>
</head>
<body>
  <div id="root"></div>
  <script nonce="${nonce}" type="module" src="${jsUri}"></script>
</body>
</html>`;
  }
}

let ibomWebview: InteractiveBomWebview | undefined;

export function openInteractiveBomPreview(
  _extensionUri: vscode.Uri,
  projectRoot?: string,
  targetName?: string,
): void {
  if (!ibomWebview) {
    ibomWebview = new InteractiveBomWebview();
  }
  if (ibomWebview.isOpen()) {
    ibomWebview.reveal();
    return;
  }
  void ibomWebview.openWithContext(projectRoot, targetName);
}

export function isInteractiveBomOpen(): boolean {
  return ibomWebview?.isOpen() ?? false;
}

export function closeInteractiveBom(): void {
  ibomWebview?.dispose();
  ibomWebview = undefined;
}
