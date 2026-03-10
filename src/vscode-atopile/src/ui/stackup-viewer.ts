/**
 * Stackup Viewer Webview — opens the 2D stackup cross-section viewer.
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { getResourcesPath } from '../common/resources';
import { backendServer } from '../common/backendServer';
import { getNonce, getWsOrigin } from '../common/webview';
import { BaseWebview } from './webview-base';

class StackupViewerWebview extends BaseWebview {
  private projectRoot?: string;
  private targetName?: string;

  constructor() {
    super({
      id: 'atopile.stackupViewer',
      title: 'PCB Stackup',
    });
  }

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
    const jsPath = path.join(webviewsDir, 'stackup.js');
    const cssPath = path.join(webviewsDir, 'stackup.css');
    const baseCssPath = path.join(webviewsDir, 'index.css');

    if (!fs.existsSync(jsPath)) {
      return this.getMissingResourceHtml('Stackup Viewer');
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
    const wsOrigin = getWsOrigin(backendServer.wsUrl);

    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <base href="${baseUri}">
  <meta http-equiv="Content-Security-Policy" content="
    default-src 'none';
    style-src ${webview.cspSource} 'unsafe-inline';
    script-src ${webview.cspSource} 'nonce-${nonce}';
    font-src ${webview.cspSource};
    img-src ${webview.cspSource} data:;
    connect-src ${webview.cspSource} ${apiUrl} ${wsOrigin};
  ">
  <title>PCB Stackup</title>
  ${baseCssUri ? `<link rel="stylesheet" href="${baseCssUri}">` : ''}
  ${cssUri ? `<link rel="stylesheet" href="${cssUri}">` : ''}
  <script nonce="${nonce}">
    window.__ATOPILE_API_URL__ = '${apiUrl}';
    window.__ATOPILE_STACKUP_PROJECT_ROOT__ = ${JSON.stringify(this.projectRoot ?? '')};
    window.__ATOPILE_STACKUP_TARGET__ = ${JSON.stringify(this.targetName ?? '')};
  </script>
</head>
<body>
  <div id="root"></div>
  <script nonce="${nonce}" type="module" src="${jsUri}"></script>
</body>
</html>`;
  }
}

let stackupViewer: StackupViewerWebview | undefined;

export function openStackupViewer(
  projectRoot?: string,
  targetName?: string,
): void {
  if (!stackupViewer) {
    stackupViewer = new StackupViewerWebview();
  }
  void stackupViewer.openWithContext(projectRoot, targetName);
}

export function closeStackupViewer(): void {
  stackupViewer?.dispose();
  stackupViewer = undefined;
}
