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
        case 'fetchProxy':
          this._handleFetchProxy(message);
          break;
      }
    }, null, this._disposables);

    // Set HTML only after message handlers are attached so early
    // bootstrap wsProxy messages are not dropped.
    this._refreshWebview();
  }

  private _handleFetchProxy(req: { id: number; url: string; method: string; headers: Record<string, string>; body: string | null }): void {
    let url = req.url;
    try {
      const externalBase = backendServer.apiUrl;
      const internalBase = backendServer.internalApiUrl || externalBase;
      if (externalBase && internalBase && url.startsWith(externalBase)) {
        url = internalBase + url.slice(externalBase.length);
      }
    } catch {
      // Use URL as-is
    }

    const init: Record<string, unknown> = {
      method: req.method,
      headers: req.headers,
    };
    if (req.body && req.method !== 'GET' && req.method !== 'HEAD') {
      init.body = req.body;
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (globalThis as any).fetch(url, init)
      .then(async (response: { text: () => Promise<string>; status: number; statusText: string; headers: { forEach: (cb: (v: string, k: string) => void) => void } }) => {
        const body = await response.text();
        const headers: Record<string, string> = {};
        response.headers.forEach((value: string, key: string) => {
          headers[key] = value;
        });
        this._view?.webview.postMessage({
          type: 'fetchProxyResult',
          id: req.id,
          status: response.status,
          statusText: response.statusText,
          headers,
          body,
        });
      })
      .catch((err: Error) => {
        this._view?.webview.postMessage({
          type: 'fetchProxyResult',
          id: req.id,
          error: String(err),
        });
      });
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
      const internalBase = backendServer.internalApiUrl || backendServer.apiUrl;
      if (internalBase) {
        const internal = new URL(internalBase);
        const wsProtocol = internal.protocol === 'https:' ? 'wss:' : 'ws:';
        const port = internal.port ? `:${internal.port}` : '';
        targetUrl = `${wsProtocol}//${internal.hostname}${port}${parsed.pathname}${parsed.search}`;
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

    const cacheVersion = (() => {
      try {
        return Math.floor(fs.statSync(jsPath).mtimeMs).toString();
      } catch {
        return Date.now().toString();
      }
    })();

    const withCacheBust = (uri: vscode.Uri): string =>
      `${uri.toString()}?v=${cacheVersion}`;

    const jsUri = withCacheBust(webview.asWebviewUri(vscode.Uri.file(jsPath)));
    const cssUri = fs.existsSync(cssPath)
      ? withCacheBust(webview.asWebviewUri(vscode.Uri.file(cssPath)))
      : null;
    const baseCssUri = fs.existsSync(baseCssPath)
      ? withCacheBust(webview.asWebviewUri(vscode.Uri.file(baseCssPath)))
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
    // Fetch + WebSocket proxy bridge (same as SidebarProvider)
    // Webviews in OpenVSCode Server run in HTTPS iframes which block ws:// (Mixed Content).
    // This shim routes WebSocket connections through the extension host via postMessage.
    (function() {
      // Cache acquireVsCodeApi — it can only be invoked once per webview session.
      // Without this, send()/close() on the ProxyWebSocket silently fail.
      var originalAcquire = window.acquireVsCodeApi;
      var vsCodeApi = null;
      if (typeof originalAcquire === 'function') {
        window.acquireVsCodeApi = function() {
          if (!vsCodeApi) vsCodeApi = originalAcquire();
          return vsCodeApi;
        };
      }

      function getVsCodeApi() {
        try {
          return vsCodeApi || (window.acquireVsCodeApi ? window.acquireVsCodeApi() : null);
        } catch (err) {
          console.error('[atopile log webview] Failed to acquire VS Code API:', err);
          return null;
        }
      }

      function normalizeHeaders(headers) {
        if (!headers) return {};
        if (typeof Headers !== 'undefined' && headers instanceof Headers) {
          var out = {};
          headers.forEach(function(v, k) { out[k] = v; });
          return out;
        }
        if (Array.isArray(headers)) {
          var outArray = {};
          for (var i = 0; i < headers.length; i++) {
            var entry = headers[i];
            if (Array.isArray(entry) && entry.length >= 2) {
              outArray[String(entry[0])] = String(entry[1]);
            }
          }
          return outArray;
        }
        return headers;
      }

      // Fetch proxy: route HTTP requests through the extension host.
      // Without this, fetch() from the CDN iframe is CORS-blocked.
      var _fpId = 0;
      var _fpPending = new Map();

      window.addEventListener('message', function(event) {
        var msg = event.data;
        if (msg && msg.type === 'fetchProxyResult' && _fpPending.has(msg.id)) {
          var handler = _fpPending.get(msg.id);
          _fpPending.delete(msg.id);
          handler(msg);
        }
      });

      window.__ATOPILE_PROXY_FETCH__ = function(url, init) {
        var id = ++_fpId;
        return new Promise(function(resolve, reject) {
          var timeout = setTimeout(function() {
            _fpPending.delete(id);
            reject(new TypeError('Fetch proxy timeout'));
          }, 30000);

          _fpPending.set(id, function(msg) {
            clearTimeout(timeout);
            if (msg.error) {
              reject(new TypeError(msg.error));
            } else {
              resolve(new Response(msg.body, {
                status: msg.status || 200,
                statusText: msg.statusText || 'OK',
                headers: msg.headers || {},
              }));
            }
          });

          var api = getVsCodeApi();
          if (api) {
            api.postMessage({
              type: 'fetchProxy',
              id: id,
              url: url,
              method: (init && init.method) || 'GET',
              headers: normalizeHeaders(init && init.headers),
              body: (init && init.body) || null,
            });
          } else {
            clearTimeout(timeout);
            _fpPending.delete(id);
            reject(new TypeError('VS Code API not available for fetch proxy'));
          }
        });
      };

      function createCompatEvent(type, init) {
        var evt;
        try {
          if (type === 'message' && typeof MessageEvent === 'function') {
            evt = new MessageEvent('message', { data: init && init.data });
          } else if (type === 'close' && typeof CloseEvent === 'function') {
            evt = new CloseEvent('close', {
              code: (init && init.code) || 1000,
              reason: (init && init.reason) || '',
              wasClean: true,
            });
          } else {
            evt = new Event(type);
          }
        } catch {
          evt = document.createEvent('Event');
          evt.initEvent(type, false, false);
        }
        if (init && init.data !== undefined && evt.data === undefined) evt.data = init.data;
        if (init && init.code !== undefined && evt.code === undefined) evt.code = init.code;
        if (init && init.reason !== undefined && evt.reason === undefined) evt.reason = init.reason;
        return evt;
      }

      function createProxySocket(url, id) {
        var listeners = { open: [], message: [], close: [], error: [] };
        var target = {
          _readyState: 0,
          url: url,
          onopen: null,
          onmessage: null,
          onclose: null,
          onerror: null,
          CONNECTING: 0,
          OPEN: 1,
          CLOSING: 2,
          CLOSED: 3,
          addEventListener: function(type, cb) {
            if (!listeners[type] || typeof cb !== 'function') return;
            listeners[type].push(cb);
          },
          removeEventListener: function(type, cb) {
            if (!listeners[type]) return;
            listeners[type] = listeners[type].filter(function(fn) { return fn !== cb; });
          },
          dispatchEvent: function(evt) {
            var type = evt && evt.type ? evt.type : '';
            var fns = listeners[type] || [];
            for (var i = 0; i < fns.length; i++) {
              try { fns[i](evt); } catch (err) { console.error(err); }
            }
            return true;
          },
          send: function(data) {
            var api = getVsCodeApi();
            if (api) api.postMessage({ type: 'wsProxySend', id: id, data: data });
          },
          close: function(code, reason) {
            target._readyState = 2;
            var api = getVsCodeApi();
            if (api) api.postMessage({ type: 'wsProxyClose', id: id, code: code, reason: reason });
          },
        };
        Object.defineProperty(target, 'readyState', {
          get: function() { return target._readyState; },
        });
        return target;
      }

      var wsProxyId = 0;
      var wsProxyInstances = new Map();
      var NativeWebSocket = window.WebSocket;

      function resolveFallbackWsUrl(url) {
        try {
          var parsed = new URL(url, window.location.href);
          if (parsed.hostname !== 'localhost' && parsed.hostname !== '127.0.0.1') {
            return url;
          }

          var parentOrigin = '';
          try {
            var params = new URLSearchParams(window.location.search);
            parentOrigin = params.get('parentOrigin') || '';
            if (parentOrigin) parentOrigin = decodeURIComponent(parentOrigin);
          } catch {}

          if (!parentOrigin && document.referrer) {
            try {
              parentOrigin = new URL(document.referrer).origin;
            } catch {}
          }

          if (!parentOrigin) {
            return url;
          }

          var parent = new URL(parentOrigin);
          var wsProtocol = parent.protocol === 'https:' ? 'wss:' : 'ws:';
          return wsProtocol + '//' + parent.host + parsed.pathname + parsed.search;
        } catch {
          return url;
        }
      }

      window.addEventListener('message', function(event) {
        var msg = event.data;
        if (!msg || !msg.type) return;
        var instance = msg.id != null ? wsProxyInstances.get(msg.id) : null;
        if (!instance) return;
        switch (msg.type) {
          case 'wsProxyOpen': {
            instance._readyState = 1;
            var openEvt = createCompatEvent('open');
            if (instance.onopen) instance.onopen(openEvt);
            instance.dispatchEvent(openEvt);
            break;
          }
          case 'wsProxyMessage': {
            var msgEvt = createCompatEvent('message', { data: msg.data });
            if (instance.onmessage) instance.onmessage(msgEvt);
            instance.dispatchEvent(msgEvt);
            break;
          }
          case 'wsProxyClose': {
            instance._readyState = 3;
            var closeEvt = createCompatEvent('close', { code: msg.code || 1000, reason: msg.reason || '' });
            if (instance.onclose) instance.onclose(closeEvt);
            instance.dispatchEvent(closeEvt);
            wsProxyInstances.delete(msg.id);
            break;
          }
          case 'wsProxyError': {
            var errEvt = createCompatEvent('error');
            if (instance.onerror) instance.onerror(errEvt);
            instance.dispatchEvent(errEvt);
            break;
          }
        }
      });

      function ProxyWebSocket(url, protocols) {
        var api = getVsCodeApi();
        if (!api && typeof NativeWebSocket === 'function') {
          var fallbackUrl = resolveFallbackWsUrl(url);
          return protocols !== undefined
            ? new NativeWebSocket(fallbackUrl, protocols)
            : new NativeWebSocket(fallbackUrl);
        }

        var id = ++wsProxyId;
        var target = createProxySocket(url, id);
        wsProxyInstances.set(id, target);
        if (api) {
          try {
            api.postMessage({ type: 'wsProxyConnect', id: id, url: url });
          } catch {
            wsProxyInstances.delete(id);
            if (typeof NativeWebSocket === 'function') {
              var fallbackUrl = resolveFallbackWsUrl(url);
              return protocols !== undefined
                ? new NativeWebSocket(fallbackUrl, protocols)
                : new NativeWebSocket(fallbackUrl);
            }
          }
        }
        return target;
      }
      ProxyWebSocket.CONNECTING = 0;
      ProxyWebSocket.OPEN = 1;
      ProxyWebSocket.CLOSING = 2;
      ProxyWebSocket.CLOSED = 3;
      window.WebSocket = ProxyWebSocket;
    })();

    document.addEventListener('DOMContentLoaded', function() {
      var loading = document.getElementById('atopile-log-loading');
      var root = document.getElementById('root');
      function showFailure(message) {
        if (!loading) return;
        loading.textContent = message;
      }
      function maybeHideLoading() {
        if (!loading || !root) return;
        if (root.childNodes.length > 0) {
          loading.style.display = 'none';
        }
      }
      window.addEventListener('error', function(event) {
        if (event && event.message) {
          showFailure('Log viewer failed to load: ' + event.message);
        } else {
          showFailure('Log viewer failed to load.');
        }
      });
      if (root && typeof MutationObserver !== 'undefined') {
        var observer = new MutationObserver(maybeHideLoading);
        observer.observe(root, { childList: true, subtree: true });
      }
      setTimeout(function() {
        if (root && root.childNodes.length === 0) {
          showFailure('Log viewer failed to initialize. If you are on Firefox, disable strict tracking protection for this site or try Chromium.');
        }
      }, 7000);
    });
  </script>
</head>
<body>
  <div id="atopile-log-loading" style="padding: 8px; font-size: 12px; opacity: 0.8;">Loading log viewer...</div>
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
