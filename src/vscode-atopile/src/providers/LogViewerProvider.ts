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
import { WebSocket as NodeWebSocket } from 'ws';

export class LogViewerProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = 'atopile.logViewer';
  private static readonly PROD_LOCAL_RESOURCE_ROOTS = ['resources/webviews', 'webviews/dist'];

  private _view?: vscode.WebviewView;
  private _disposables: vscode.Disposable[] = [];
  private _hasHtml = false;
  private _lastApiUrl: string | null = null;
  private _lastWsUrl: string | null = null;
  private _wsProxies: Map<number, NodeWebSocket> = new Map();

  constructor(private readonly _extensionUri: vscode.Uri) {
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
    for (const ws of this._wsProxies.values()) {
      ws.removeAllListeners();
      ws.close();
    }
    this._wsProxies.clear();
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
    this._refreshWebview();

    // Handle WebSocket proxy messages from the webview
    webviewView.webview.onDidReceiveMessage((message) => {
      if (!message || !message.type) return;
      switch (message.type) {
        case 'wsProxyConnect':
          this._handleWsProxyConnect(message);
          break;
        case 'wsProxySend':
          this._handleWsProxySend(message);
          break;
        case 'wsProxyClose':
          this._handleWsProxyClose(message);
          break;
      }
    }, null, this._disposables);
  }

  private _handleWsProxyConnect(msg: { id: number; url: string }): void {
    const existing = this._wsProxies.get(msg.id);
    if (existing) {
      existing.removeAllListeners();
      existing.close();
      this._wsProxies.delete(msg.id);
    }

    let targetUrl = msg.url;
    try {
      const parsed = new URL(msg.url);
      const internalBase = backendServer.apiUrl;
      if (internalBase) {
        const internal = new URL(internalBase);
        targetUrl = `ws://${internal.hostname}:${internal.port}${parsed.pathname}${parsed.search}`;
      }
    } catch {
      // Use URL as-is
    }

    const ws = new NodeWebSocket(targetUrl);

    ws.on('open', () => {
      this._view?.webview.postMessage({ type: 'wsProxyOpen', id: msg.id });
    });

    ws.on('message', (data: Buffer | string) => {
      const payload = typeof data === 'string' ? data : data.toString('utf-8');
      this._view?.webview.postMessage({ type: 'wsProxyMessage', id: msg.id, data: payload });
    });

    ws.on('close', (code: number, reason: Buffer) => {
      this._wsProxies.delete(msg.id);
      this._view?.webview.postMessage({
        type: 'wsProxyClose',
        id: msg.id,
        code,
        reason: reason.toString('utf-8'),
      });
    });

    ws.on('error', (err: Error) => {
      this._view?.webview.postMessage({ type: 'wsProxyError', id: msg.id, error: err.message });
    });

    this._wsProxies.set(msg.id, ws);
  }

  private _handleWsProxySend(msg: { id: number; data: string }): void {
    const ws = this._wsProxies.get(msg.id);
    if (ws?.readyState === NodeWebSocket.OPEN) {
      ws.send(msg.data);
    }
  }

  private _handleWsProxyClose(msg: { id: number; code?: number; reason?: string }): void {
    const ws = this._wsProxies.get(msg.id);
    if (ws) {
      ws.close(msg.code ?? 1000, msg.reason ?? '');
      this._wsProxies.delete(msg.id);
    }
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

    const jsUri = webview.asWebviewUri(vscode.Uri.file(jsPath));
    const cssUri = fs.existsSync(cssPath)
      ? webview.asWebviewUri(vscode.Uri.file(cssPath))
      : null;
    const baseCssUri = fs.existsSync(baseCssPath)
      ? webview.asWebviewUri(vscode.Uri.file(baseCssPath))
      : null;

    // Get backend URLs from backendServer (uses discovered port or config)
    const apiUrl = backendServer.apiUrl;
    const wsUrl = backendServer.wsUrl;
    const wsOrigin = getWsOrigin(wsUrl);

    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Content-Security-Policy" content="
    default-src 'none';
    style-src ${webview.cspSource} 'unsafe-inline';
    script-src ${webview.cspSource} 'nonce-${nonce}';
    font-src ${webview.cspSource};
    img-src ${webview.cspSource} data: https: http:;
    connect-src ${apiUrl} ${wsOrigin} ws: wss:;
  ">
  <title>atopile Logs</title>
  ${baseCssUri ? `<link rel="stylesheet" href="${baseCssUri}">` : ''}
  ${cssUri ? `<link rel="stylesheet" href="${cssUri}">` : ''}
  <script nonce="${nonce}">
    window.__ATOPILE_API_URL__ = '${apiUrl}';
    window.__ATOPILE_WS_URL__ = '${wsOrigin}';
  </script>
  <script nonce="${nonce}">
    // WebSocket-over-postMessage bridge (same as SidebarProvider)
    // Webviews in OpenVSCode Server run in HTTPS iframes which block ws:// (Mixed Content).
    // This shim routes WebSocket connections through the extension host via postMessage.
    (function() {
      var vsCodeApi = (typeof acquireVsCodeApi === 'function') ? acquireVsCodeApi() : null;
      var wsProxyId = 0;
      var wsProxyInstances = new Map();

      window.addEventListener('message', function(event) {
        var msg = event.data;
        if (!msg || !msg.type) return;
        var instance = msg.id != null ? wsProxyInstances.get(msg.id) : null;
        if (!instance) return;
        switch (msg.type) {
          case 'wsProxyOpen':
            instance._readyState = 1;
            if (instance.onopen) instance.onopen(new Event('open'));
            instance.dispatchEvent(new Event('open'));
            break;
          case 'wsProxyMessage':
            if (instance.onmessage) instance.onmessage(new MessageEvent('message', { data: msg.data }));
            instance.dispatchEvent(new MessageEvent('message', { data: msg.data }));
            break;
          case 'wsProxyClose':
            instance._readyState = 3;
            var closeEvt = new CloseEvent('close', { code: msg.code || 1000, reason: msg.reason || '', wasClean: true });
            if (instance.onclose) instance.onclose(closeEvt);
            instance.dispatchEvent(closeEvt);
            wsProxyInstances.delete(msg.id);
            break;
          case 'wsProxyError':
            var errEvt = new Event('error');
            if (instance.onerror) instance.onerror(errEvt);
            instance.dispatchEvent(errEvt);
            break;
        }
      });

      function ProxyWebSocket(url, protocols) {
        var target = new EventTarget();
        var id = ++wsProxyId;
        target._readyState = 0;
        target.url = url;
        target.onopen = null;
        target.onmessage = null;
        target.onclose = null;
        target.onerror = null;
        target.addEventListener = EventTarget.prototype.addEventListener.bind(target);
        target.removeEventListener = EventTarget.prototype.removeEventListener.bind(target);
        target.dispatchEvent = EventTarget.prototype.dispatchEvent.bind(target);
        Object.defineProperty(target, 'readyState', { get: function() { return target._readyState; } });
        target.send = function(data) {
          var api = vsCodeApi || (window.acquireVsCodeApi ? window.acquireVsCodeApi() : null);
          if (api) api.postMessage({ type: 'wsProxySend', id: id, data: data });
        };
        target.close = function(code, reason) {
          target._readyState = 2;
          var api = vsCodeApi || (window.acquireVsCodeApi ? window.acquireVsCodeApi() : null);
          if (api) api.postMessage({ type: 'wsProxyClose', id: id, code: code, reason: reason });
        };
        target.CONNECTING = 0;
        target.OPEN = 1;
        target.CLOSING = 2;
        target.CLOSED = 3;
        wsProxyInstances.set(id, target);
        var api = vsCodeApi || (window.acquireVsCodeApi ? window.acquireVsCodeApi() : null);
        if (api) api.postMessage({ type: 'wsProxyConnect', id: id, url: url });
        return target;
      }
      ProxyWebSocket.CONNECTING = 0;
      ProxyWebSocket.OPEN = 1;
      ProxyWebSocket.CLOSING = 2;
      ProxyWebSocket.CLOSED = 3;
      window.WebSocket = ProxyWebSocket;
    })();
  </script>
</head>
<body>
  <div id="root"></div>
  <script nonce="${nonce}" type="module" src="${jsUri}"></script>
</body>
</html>`;
  }

  private _getNotBuiltHtml(): string {
    return `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100vh;
      margin: 0;
      background: var(--vscode-sideBar-background);
      color: var(--vscode-foreground);
      font-family: var(--vscode-font-family);
      text-align: center;
      padding: 16px;
    }
    code {
      background: var(--vscode-textCodeBlock-background);
      padding: 2px 6px;
      border-radius: 3px;
      font-size: 12px;
    }
  </style>
</head>
<body>
  <div>
    <p>Webview not built.</p>
    <p>Run <code>npm run build</code> in the webviews directory.</p>
  </div>
</body>
</html>`;
  }
}
