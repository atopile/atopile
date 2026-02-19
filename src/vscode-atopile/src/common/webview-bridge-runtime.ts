/**
 * Generates the injected JavaScript IIFE for webview proxy bridges.
 *
 * This code runs *inside* the webview iframe.  It intercepts fetch() and
 * WebSocket connections and routes them through postMessage so the
 * extension host can proxy them to the local backend.
 */

export interface WebviewBridgeRuntimeOptions {
  /** The browser-visible backend API URL (used by the 'override' fetch mode). */
  apiUrl: string;
  /** Enable diagnostic telemetry (only used by SidebarProvider). Default false. */
  diagnostics?: boolean;
  /**
   * How the fetch proxy is exposed:
   *  - `'global'`   – sets `window.__ATOPILE_PROXY_FETCH__` (Sidebar, LogViewer)
   *  - `'override'` – overrides `window.fetch` for backend URLs (LayoutEditor)
   */
  fetchMode?: 'global' | 'override';
}

/**
 * Return a self-contained IIFE string that can be embedded in a `<script>` tag.
 */
export function generateBridgeRuntime(options: WebviewBridgeRuntimeOptions): string {
  const { apiUrl, diagnostics = false, fetchMode = 'global' } = options;

  // ── acquireVsCodeApi cache + getVsCodeApi helper ─────────────────
  const acquireBlock = `
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
          console.error('[atopile webview] Failed to acquire VS Code API:', err);
          return null;
        }
      }`;

  // ── Diagnostics (optional) ───────────────────────────────────────
  const diagnosticsBlock = diagnostics
    ? `
      function postWebviewDiagnostic(phase, detail) {
        var payload = {
          type: 'webviewDiagnostic',
          phase: String(phase || ''),
          detail: detail == null ? undefined : String(detail),
        };
        if (!window.__ATOPILE_DIAG_QUEUE__) {
          window.__ATOPILE_DIAG_QUEUE__ = [];
        }
        window.__ATOPILE_DIAG_QUEUE__.push(payload);
        var attempts = 0;
        var flush = function() {
          var api = getVsCodeApi();
          if (!api) {
            attempts += 1;
            if (attempts < 40) {
              setTimeout(flush, 250);
            }
            return;
          }
          while (window.__ATOPILE_DIAG_QUEUE__.length > 0) {
            var msg = window.__ATOPILE_DIAG_QUEUE__.shift();
            try {
              api.postMessage(msg);
            } catch (err) {
              console.error('[atopile webview] Failed to post diagnostic:', err);
              break;
            }
          }
        };
        try {
          flush();
        } catch (err) {
          console.error('[atopile webview] Diagnostic flush failed:', err);
        }
      }

      window.__ATOPILE_POST_DIAG__ = postWebviewDiagnostic;
      postWebviewDiagnostic('inline-bootstrap-start');
      window.addEventListener('error', function(event) {
        var msg = (event && event.message) ? event.message : 'unknown error';
        postWebviewDiagnostic('window-error', msg);
      });
      window.addEventListener('unhandledrejection', function(event) {
        var reason = event && event.reason;
        var msg = reason && reason.message ? reason.message : String(reason);
        postWebviewDiagnostic('unhandled-rejection', msg);
      });`
    : '';

  // ── Shared helpers ───────────────────────────────────────────────
  const helpersBlock = `
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
      }`;

  // ── Fetch proxy ──────────────────────────────────────────────────
  let fetchBlock: string;

  if (fetchMode === 'override') {
    // Layout editor: override window.fetch for backend URLs only
    fetchBlock = `
      var backendBase = '${apiUrl}';
      var originalFetch = window.fetch;
      var fetchId = 0;
      var pendingFetch = new Map();

      window.addEventListener('message', function(event) {
        var msg = event.data;
        if (!msg || !msg.type) return;
        if (msg.type === 'fetchProxyResult' && pendingFetch.has(msg.id)) {
          var handler = pendingFetch.get(msg.id);
          pendingFetch.delete(msg.id);
          handler(msg);
        }
      });

      window.fetch = function(input, init) {
        var url = typeof input === 'string' ? input : (input instanceof Request ? input.url : String(input));
        if (!url.startsWith(backendBase)) {
          return originalFetch.apply(this, arguments);
        }

        return new Promise(function(resolve, reject) {
          var id = ++fetchId;
          var timeout = setTimeout(function() {
            pendingFetch.delete(id);
            reject(new TypeError('Fetch proxy timeout'));
          }, 30000);

          pendingFetch.set(id, function(msg) {
            clearTimeout(timeout);
            if (msg.error) {
              reject(new TypeError(msg.error));
              return;
            }
            resolve(new Response(msg.body, {
              status: msg.status || 200,
              statusText: msg.statusText || 'OK',
              headers: msg.headers || {},
            }));
          });

          var api = getVsCodeApi();
          if (!api) {
            clearTimeout(timeout);
            pendingFetch.delete(id);
            originalFetch.apply(window, [input, init]).then(resolve, reject);
            return;
          }

          try {
            api.postMessage({
              type: 'fetchProxy',
              id: id,
              url: url,
              method: (init && init.method) || 'GET',
              headers: normalizeHeaders(init && init.headers),
              body: (init && init.body) || null,
            });
          } catch {
            clearTimeout(timeout);
            pendingFetch.delete(id);
            originalFetch.apply(window, [input, init]).then(resolve, reject);
          }
        });
      };`;
  } else {
    // Sidebar / LogViewer: expose as explicit global
    fetchBlock = `
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
      };`;
  }

  // ── WebSocket proxy ──────────────────────────────────────────────
  const wsBlock = `
      var wsProxyId = 0;
      var wsProxyInstances = new Map();
      var NativeWebSocket = window.WebSocket;

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
      window.WebSocket = ProxyWebSocket;`;

  // ── Assemble IIFE ────────────────────────────────────────────────
  return `(function() {${acquireBlock}${diagnosticsBlock}${helpersBlock}${fetchBlock}${wsBlock}
    })();`;
}
