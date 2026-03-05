/**
 * Stateless Log Viewer Webview Provider.
 *
 * This provider is minimal - it just opens the webview and loads the UI.
 * All state management and backend communication happens in the React app.
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { backendServer } from '../common/backendServer';
import { createWebviewOptions, getNonce, getWsOrigin } from '../common/webview';
import { WebviewProxyBridge } from '../common/webview-bridge';
import {
  getWebviewBridgeRuntimePath,
  serializeWebviewBridgeConfig,
  WEBVIEW_BRIDGE_CONFIG_ELEMENT_ID,
} from '../common/webview-bridge-runtime';
import { renderTemplate, serializeJsonForHtml } from '../common/template';
// @ts-ignore
import * as _logViewerTemplateText from './log-viewer.hbs';
// @ts-ignore
import * as _notBuiltTemplateText from './webview-not-built.hbs';

const logViewerTemplateText: string = (_logViewerTemplateText as any).default || _logViewerTemplateText;
const notBuiltTemplateText: string = (_notBuiltTemplateText as any).default || _notBuiltTemplateText;

export class LogViewerProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = 'atopile.logViewer';
  private static readonly PROD_LOCAL_RESOURCE_ROOTS = ['resources', 'resources/webviews', 'webviews/dist'];

  private _view?: vscode.WebviewView;
  private _disposables: vscode.Disposable[] = [];
  private _hasHtml = false;
  private _lastApiUrl: string | null = null;
  private _lastWsUrl: string | null = null;
  private _bridge: WebviewProxyBridge;

  constructor(private readonly _extensionUri: vscode.Uri) {
    this._bridge = new WebviewProxyBridge({
      postToWebview: (msg) => this._view?.webview.postMessage(msg),
      logTag: 'LogViewer',
    });
    this._disposables.push(
      backendServer.onStatusChange((connected) => {
        if (connected) {
          this._refreshWebview();
        }
      })
    );
  }

  dispose(): void {
    for (const d of this._disposables) {
      d.dispose();
    }
    this._disposables = [];
    this._bridge.dispose();
  }

  private _refreshWebview(): void {
    if (!this._view) {
      return;
    }

    const extensionPath = this._extensionUri.fsPath;
    const apiUrl = backendServer.apiUrl;
    const wsUrl = backendServer.wsUrl;

    // Port changes are always reflected in apiUrl/wsUrl (see backendServer._setPort)
    if (this._hasHtml && this._lastApiUrl === apiUrl && this._lastWsUrl === wsUrl) {
      return;
    }

    this._view.webview.options = createWebviewOptions({
      extensionPath,
      port: backendServer.port,
      prodLocalResourceRoots: LogViewerProvider.PROD_LOCAL_RESOURCE_ROOTS,
    });
    this._view.webview.html = this._getProdHtml(this._view.webview);
    this._hasHtml = true;
    this._lastApiUrl = apiUrl;
    this._lastWsUrl = wsUrl;
  }

  public resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken
  ): void {
    this._view = webviewView;

    // Handle proxy messages from the webview via the shared bridge
    webviewView.webview.onDidReceiveMessage((message) => {
      if (!message || !message.type) return;
      this._bridge.handleMessage(message);
    }, null, this._disposables);

    // Set HTML only after message handlers are attached so early
    // bootstrap wsProxy messages are not dropped.
    this._refreshWebview();
  }

  /**
   * Get the webview HTML - loads from compiled assets.
   */
  private _getProdHtml(webview: vscode.Webview): string {
    const extensionPath = this._extensionUri.fsPath;
    const nonce = getNonce();

    const webviewsDir = path.join(extensionPath, 'resources', 'webviews');
    const jsPath = path.join(webviewsDir, 'logViewer.js');
    const cssPath = path.join(webviewsDir, 'LogViewer.css');
    const baseCssPath = path.join(webviewsDir, 'index.css');

    if (!fs.existsSync(jsPath)) {
      return this._getNotBuiltHtml();
    }

    const jsUri = webview.asWebviewUri(vscode.Uri.file(jsPath)).toString();
    const bridgeRuntimeUri = webview.asWebviewUri(
      vscode.Uri.file(getWebviewBridgeRuntimePath(extensionPath))
    ).toString();
    const cssUri = fs.existsSync(cssPath)
      ? webview.asWebviewUri(vscode.Uri.file(cssPath)).toString()
      : null;
    const baseCssUri = fs.existsSync(baseCssPath)
      ? webview.asWebviewUri(vscode.Uri.file(baseCssPath)).toString()
      : null;

    // Get backend URLs from backendServer (uses discovered port or config)
    const apiUrl = backendServer.apiUrl;
    const wsUrl = backendServer.wsUrl;
    const wsOrigin = getWsOrigin(wsUrl);
    const bridgeConfigJson = serializeWebviewBridgeConfig({
      apiUrl,
      fetchMode: 'global',
    });

    const csp = [
      "default-src 'none'",
      `style-src ${webview.cspSource} 'unsafe-inline'`,
      `script-src ${webview.cspSource} 'nonce-${nonce}'`,
      `font-src ${webview.cspSource}`,
      `img-src ${webview.cspSource} data: https: http:`,
      `connect-src ${apiUrl} ${wsOrigin} ws: wss:`,
    ].join('; ');

    return renderTemplate(logViewerTemplateText, {
      csp,
      nonce,
      baseCssLink: baseCssUri ? `<link rel="stylesheet" href="${baseCssUri}">` : '',
      cssLink: cssUri ? `<link rel="stylesheet" href="${cssUri}">` : '',
      apiUrlJson: serializeJsonForHtml(apiUrl),
      wsOriginJson: serializeJsonForHtml(wsOrigin),
      bridgeConfigElementId: WEBVIEW_BRIDGE_CONFIG_ELEMENT_ID,
      bridgeConfigJson,
      bridgeRuntimeUri,
      jsUri,
    });
  }

  private _getNotBuiltHtml(): string {
    return renderTemplate(notBuiltTemplateText, {
      buildCommand: 'npm run build',
    });
  }
}
